"""FastAPI backend for the paperflow web UI (single local user).

Flow is two-phase to avoid pausing mid-pipeline:
  1) create project -> diagnose (ingest + requirement.detect) -> return questions
  2) submit answers (answer.json) -> generate (rest of pipeline) with live SSE progress

Reuses the engine as-is: ingest, detect.detect, flows.method_result.run, config.
Progress is streamed via SSE (one-way server->client; native EventSource in the browser).
"""
from __future__ import annotations

import csv
import io
import json
import queue
import re
import shutil
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .. import config
from ..flows.method_result import STEPS, run
from ..ingest.parse_inputs import ingest
from ..requirement import detect

app = FastAPI(title="paperflow")

_STATIC = Path(__file__).resolve().parent / "static"
# new projects created from the form land here (sibling of engine/)
_WORKSPACE = Path(__file__).resolve().parents[3].parent / "projects"

# job_id -> Queue of SSE event dicts (live runs only)
_JOBS: dict[str, "queue.Queue[dict | None]"] = {}

_STEP_RE = re.compile(r"^\[(\w+)\]\s*(.*)")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_").lower()
    return s or "untitled"


def _write_inputs(project_dir: Path, body: dict) -> None:
    main = project_dir / "main"
    main.mkdir(parents=True, exist_ok=True)
    files = {
        "0_journal_info.md": body.get("journal_info_md", ""),
        "1_coremessage.md": body.get("coremessage_md", ""),
        "3_outline.md": body.get("outline_md", ""),
    }
    for fname, content in files.items():
        if content:
            (main / fname).write_text(content)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/api/providers")
def providers() -> dict:
    return {"providers": config.available_providers()}


@app.post("/api/projects")
def create_project(body: dict) -> dict:
    """Attach an existing project (body.project_dir) or create one from the 3 inputs."""
    if body.get("project_dir"):
        project_dir = Path(body["project_dir"]).expanduser()
    else:
        project_dir = _WORKSPACE / _slug(body.get("name", "untitled"))
        _write_inputs(project_dir, body)
    return {"project_dir": str(project_dir), "providers": config.available_providers()}


def _txt(p: Path) -> str:
    return p.read_text() if p.is_file() else ""


def _project_meta(pdir: Path) -> dict:
    """Dashboard card data: title, progress %, current step, deadline, status."""
    main = pdir / "main"
    meta = {}
    mp = main / "project.json"
    if mp.is_file():
        try:
            meta = json.loads(mp.read_text())
        except Exception:
            meta = {}
    ji_raw = _txt(main / "0_journal_info.md")
    title, field = "", ""
    if ji_raw.strip():
        from ..ingest.parse_inputs import parse_journal_info
        ji = parse_journal_info(ji_raw)
        title, field = ji.working_title, ji.author_field
    has_j = bool(ji_raw.strip())
    has_c = bool(_txt(main / "1_coremessage.md").strip())
    has_o = bool(_txt(main / "3_outline.md").strip())
    has_ans = (main / "answer.json").is_file()
    out = pdir / "_paperflow_out"
    has_out = out.is_dir() and any(out.glob("*.md"))
    pct = (15 if has_j else 0) + (15 if has_c else 0) + (20 if has_o else 0) \
        + (15 if has_ans else 0) + (35 if has_out else 0)
    if has_out:
        step, status = "생성 완료", "done"
    elif has_ans:
        step, status = "생성 대기", "active"
    elif has_j and has_c and has_o:
        step, status = "진단 / 질문", "active"
    elif pct > 0:
        step, status = "입력 작성 중", "active"
    else:
        step, status = "STEP 0 · 입력", "new"
    return {
        "project_dir": str(pdir), "name": meta.get("name") or pdir.name,
        "title": title or meta.get("name") or pdir.name, "field": field,
        "progress": pct, "step": step, "status": status,
        "deadline": meta.get("deadline", ""), "created": meta.get("created", ""),
    }


@app.get("/api/projects/list")
def list_projects() -> dict:
    items = []
    if _WORKSPACE.is_dir():
        for d in sorted(_WORKSPACE.iterdir()):
            if d.is_dir() and (d / "main").is_dir():
                items.append(_project_meta(d))
    return {"projects": items, "providers": config.available_providers()}


@app.post("/api/projects/create")
def create_new(body: dict) -> dict:
    """Create an empty project (from the dashboard) with name + deadline metadata."""
    main = _WORKSPACE / _slug(body.get("name", "untitled")) / "main"
    main.mkdir(parents=True, exist_ok=True)
    meta = {"name": body.get("name", "untitled"), "deadline": body.get("deadline", ""),
            "created": body.get("created", "")}
    (main / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return {"project_dir": str(main.parent)}


@app.post("/api/projects/save")
def save_inputs(body: dict) -> dict:
    """Persist the 3 input files + the structured UI state (for lossless reopen)."""
    main = Path(body["project_dir"]) / "main"
    main.mkdir(parents=True, exist_ok=True)
    for fn, c in {"0_journal_info.md": body.get("journal_info_md", ""),
                  "1_coremessage.md": body.get("coremessage_md", ""),
                  "3_outline.md": body.get("outline_md", "")}.items():
        if c:
            (main / fn).write_text(c)
    if body.get("ui_state") is not None:
        (main / "_ui_state.json").write_text(json.dumps(body["ui_state"], ensure_ascii=False, indent=2))
    return {"ok": True}


@app.get("/api/projects/state")
def get_state(project_dir: str) -> dict:
    paper_ready = (Path(project_dir) / "_paperflow_out" / "paper.pdf").is_file()
    p = Path(project_dir) / "main" / "_ui_state.json"
    if p.is_file():
        try:
            return {"ui_state": json.loads(p.read_text()), "paper_ready": paper_ready}
        except Exception:
            pass
    return {"ui_state": None, "paper_ready": paper_ready}


@app.post("/api/projects/diagnose")
def diagnose(body: dict) -> dict:
    """Ingest + detect missing info -> questions (each with an example placeholder)."""
    project_dir = body["project_dir"]
    ps = ingest(project_dir)
    report = detect.detect(ps)
    detect.save_report(project_dir, report)  # reused by the generate run (no 2nd LLM call)
    questions = [
        {"id": m.field, "field": m.field, "question": m.question,
         "example": m.example, "reviewer_risk": m.reviewer_risk}
        for m in report.missing if m.question
    ]
    return {
        "classification": report.classification.value if report.classification else None,
        "present": report.present, "questions": questions, "notes": report.notes,
    }


@app.post("/api/projects/answers")
def save_answers(body: dict) -> dict:
    """Persist Gate A answers to main/answer.json."""
    main = Path(body["project_dir"]) / "main"
    main.mkdir(parents=True, exist_ok=True)
    answers = body.get("answers", {})
    (main / "answer.json").write_text(json.dumps(answers, ensure_ascii=False, indent=2))
    return {"ok": True, "count": len(answers)}


# --- data files (experiment data / references the writer grounds claims on) ---
_UPLOAD_SUBDIR = "data/uploads"
_ALLOWED_EXT = {".csv", ".txt", ".dat", ".md", ".pdf", ".png", ".jpg", ".jpeg",
                ".xlsx", ".xls", ".json", ".bib"}


def _csv_columns(p: Path) -> list[str]:
    try:
        with p.open(newline="") as f:
            return next(csv.reader(io.StringIO(f.readline())), [])
    except Exception:
        return []


def _notes_path(project: Path) -> Path:
    # kept outside data/ and reference/ so it never shows up as a data file itself
    return project / "main" / "data_notes.json"


def _read_notes(project: Path) -> dict:
    p = _notes_path(project)
    if p.is_file():
        try:
            d = json.loads(p.read_text())
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    return {}


def _list_data_files(project: Path) -> list[dict]:
    """Files under data/ and reference/ — what the engine will see when grounding claims."""
    notes = _read_notes(project)
    out: list[dict] = []
    for sub in ("data", "reference"):
        base = project / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.name.startswith(".") or ":" in p.name:
                continue  # skip dotfiles + Windows ADS (e.g. ...pdf:Zone.Identifier)
            kind = p.suffix.lower().lstrip(".") or "file"
            rel = str(p.relative_to(project))
            item = {"name": p.name, "rel": rel, "kind": kind,
                    "size": p.stat().st_size, "note": notes.get(rel, "")}
            if kind == "csv":
                item["columns"] = _csv_columns(p)
            out.append(item)
    return out


def _safe_under(project: Path, rel: str) -> Path | None:
    """Resolve rel against project, refusing path traversal outside the project."""
    target = (project / rel).resolve()
    if project.resolve() not in target.parents and target != project.resolve():
        return None
    return target


@app.get("/api/projects/files")
def list_files(project_dir: str) -> dict:
    return {"files": _list_data_files(Path(project_dir))}


@app.get("/api/projects/paper")
def get_paper(project_dir: str, kind: str = "pdf"):
    """Serve the assembled manuscript — kind=pdf (compiled) or tex (source)."""
    f = Path(project_dir) / "_paperflow_out" / ("paper.pdf" if kind == "pdf" else "paper.tex")
    if not f.is_file():
        return JSONResponse({"error": "not_found", "kind": kind}, status_code=404)
    media = "application/pdf" if kind == "pdf" else "text/plain; charset=utf-8"
    return FileResponse(f, media_type=media)


@app.post("/api/projects/upload")
async def upload_files(project_dir: str = Form(...),
                       files: list[UploadFile] = None) -> dict:
    project = Path(project_dir)
    dest = project / _UPLOAD_SUBDIR
    dest.mkdir(parents=True, exist_ok=True)
    saved = []
    for uf in files or []:
        name = Path(uf.filename or "").name  # strip any path components
        if not name or Path(name).suffix.lower() not in _ALLOWED_EXT:
            continue
        with (dest / name).open("wb") as out:
            shutil.copyfileobj(uf.file, out)
        saved.append(name)
    return {"ok": True, "saved": saved, "files": _list_data_files(project)}


@app.post("/api/projects/files/delete")
def delete_file(body: dict) -> dict:
    project = Path(body["project_dir"])
    rel = body.get("rel", "")
    target = _safe_under(project, rel)
    if target and target.is_file():
        target.unlink()
    notes = _read_notes(project)  # drop any orphaned note
    if notes.pop(rel, None) is not None:
        _notes_path(project).write_text(json.dumps(notes, ensure_ascii=False, indent=2))
    return {"ok": True, "files": _list_data_files(project)}


@app.post("/api/projects/files/note")
def set_file_note(body: dict) -> dict:
    """One free-text description per file — surfaced to the writer as grounding context."""
    project = Path(body["project_dir"])
    rel = body.get("rel", "")
    note = str(body.get("note", "")).strip()
    notes = _read_notes(project)
    if note:
        notes[rel] = note
    else:
        notes.pop(rel, None)
    p = _notes_path(project)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(notes, ensure_ascii=False, indent=2))
    return {"ok": True}


def _run_job(job_id: str, project_dir: str, sections: list[str], litsearch: bool) -> None:
    q = _JOBS[job_id]

    def progress(msg: str) -> None:
        m = _STEP_RE.match(msg)
        step_id, label = (m.group(1), m.group(2)) if m else ("", msg)
        q.put({"type": "progress", "step_id": step_id, "label": label, "raw": msg})

    try:
        out_dir = Path(project_dir) / "_paperflow_out"
        manifest = run(project_dir, sections, out_dir, progress=progress, litsearch=litsearch)
        q.put({"type": "done",
               "classification": manifest.classification.value if manifest.classification else None,
               "input_tokens": manifest.total_input, "output_tokens": manifest.total_output,
               "cached_tokens": manifest.total_cached,
               "cache_hit_rate": round(manifest.cache_hit_rate, 4),
               "out_dir": str(out_dir)})
    except Exception as e:  # surface the failure to the client instead of hanging
        q.put({"type": "error", "error": str(e)[:400]})
    finally:
        q.put(None)  # sentinel: stream ends


def _unanswered(project_dir: str) -> list[str]:
    """Hard gate: every diagnosed question must have a response (an answer or an
    explicit '모름'). Returns the question fields still missing a response."""
    report = detect.load_report(project_dir)
    if report is None:
        return []  # no diagnose on record (e.g. CLI) -> nothing to gate
    answered = set()
    ap = Path(project_dir) / "main" / "answer.json"
    if ap.is_file():
        try:
            data = json.loads(ap.read_text())
            answered = {k for k, v in data.items() if str(v).strip()}
        except Exception:
            answered = set()
    return [m.field for m in report.missing if m.question and m.field not in answered]


@app.post("/api/projects/generate")
def generate(body: dict) -> dict:
    """Kick off the pipeline on a worker thread; return the job id + the step list."""
    project_dir = body["project_dir"]
    pending = _unanswered(project_dir)
    if pending:  # hard gate — refuse to generate with unanswered questions
        return {"error": "unanswered_questions", "pending": pending}
    sections = body.get("sections") or ["method", "result", "discussion",
                                        "introduction", "conclusion", "abstract"]
    litsearch = bool(body.get("litsearch", True))
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = queue.Queue()
    threading.Thread(target=_run_job, args=(job_id, project_dir, sections, litsearch),
                     daemon=True).start()
    return {"job_id": job_id, "steps": [{"id": s, "label": label} for s, label in STEPS]}


@app.get("/api/projects/generate/{job_id}/stream")
def stream(job_id: str) -> StreamingResponse:
    q = _JOBS.get(job_id)

    def gen():
        if q is None:
            yield f"data: {json.dumps({'type': 'error', 'error': 'unknown job'})}\n\n"
            return
        while True:
            ev = q.get()
            if ev is None:
                break
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        _JOBS.pop(job_id, None)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)
