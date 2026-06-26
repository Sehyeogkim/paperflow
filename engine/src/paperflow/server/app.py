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
from ..compile import plan_chat
from ..flows import method_result as mr
from ..flows.method_result import GEN_STEPS, PLAN_STEPS, RECONSTRUCT_STEPS
from ..ingest import normalize_outline as no_mod
from ..ingest.parse_inputs import ingest
from ..question import loop as qloop
from ..reconstruct import build_state
from ..requirement import detect
from ..schemas.outline_state import NormalizedOutline

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


@app.post("/api/projects/outline")
def save_outline(body: dict) -> dict:
    """Normalize either outline mode into ONE schema, preserving the user's raw text.
      mode=quick      -> Outline Normalizer LLM (deterministic heuristic fallback w/o key)
      mode=structured -> deterministic per-section split
    Persists main/outline_state.json (source of truth) + main/3_outline.md (legacy/CLI view)."""
    project_dir = body["project_dir"]
    main = Path(project_dir) / "main"
    main.mkdir(parents=True, exist_ok=True)
    mode = (body.get("mode") or "structured").lower()
    if mode == "quick":
        ps = ingest(project_dir)  # context (core message, plan) helps the normalizer
        from ..util import inputs_block
        no = no_mod.normalize_quick(body.get("raw", "") or "", context=inputs_block(ps))
    else:
        no = no_mod.normalize_structured(body.get("sections", {}) or {})
    (main / "outline_state.json").write_text(no.model_dump_json(indent=2))
    (main / "3_outline.md").write_text(no_mod.render_md(no))  # keep legacy/CLI working
    return {"ok": True, "outline": no.model_dump()}


@app.get("/api/projects/outline")
def get_outline(project_dir: str) -> dict:
    p = Path(project_dir) / "main" / "outline_state.json"
    if p.is_file():
        try:
            return {"outline": NormalizedOutline.model_validate_json(p.read_text()).model_dump()}
        except Exception:
            pass
    # derive from legacy 3_outline.md if present
    ps = ingest(project_dir)
    return {"outline": ps.normalized_outline.model_dump() if ps.normalized_outline else None}


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
    """MERGE answers into main/answer.json (adaptive loop: each batch adds, never overwrites).
    Answering is never a gate — generation can proceed with answers still pending."""
    project_dir = body["project_dir"]
    merged = qloop.save_answers(project_dir, body.get("answers", {}))
    return {"ok": True, "count": len(merged)}


@app.post("/api/projects/questions")
def questions(body: dict) -> dict:
    """Adaptive question batch from the CURRENT preliminary graph + reconstruction state.
    No fixed count, no hard gate. Works offline (graph absent -> reconstruction gaps only)."""
    project_dir = body["project_dir"]
    graph = mr.load_prelim_graph(project_dir)
    rs, inv = build_state.load(project_dir)
    answered = qloop.load_answers(project_dir)
    batch_size = int(body.get("batch_size", qloop.DEFAULT_BATCH))
    batch = qloop.next_batch(graph, rs, inv, answered=answered, batch_size=batch_size)
    return {**batch.model_dump(), "has_graph": graph is not None,
            "answered_count": len(answered)}


def _reconstruct_job(job_id: str, project_dir: str) -> None:
    q = _JOBS[job_id]
    try:
        summary = mr.preliminary(project_dir, progress=_progress_fn(q))
        rs, inv = build_state.load(project_dir)
        graph = mr.load_prelim_graph(project_dir)
        batch = qloop.next_batch(graph, rs, inv, answered=qloop.load_answers(project_dir))
        q.put({"type": "reconstruct_ready",
               "research_state": summary.get("research_state"),
               "has_graph": summary.get("has_graph"),
               "questions": batch.model_dump()})
    except Exception as e:
        q.put({"type": "error", "error": str(e)[:400]})
    finally:
        q.put(None)


@app.post("/api/projects/reconstruct")
def start_reconstruct(body: dict) -> dict:
    """Phase R — reconstruct research state + build the preliminary logic graph (background
    job with SSE), then surface the first adaptive question batch."""
    project_dir = body["project_dir"]
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = queue.Queue()
    threading.Thread(target=_reconstruct_job, args=(job_id, project_dir), daemon=True).start()
    return {"job_id": job_id, "steps": [{"id": s, "label": label} for s, label in RECONSTRUCT_STEPS]}


@app.get("/api/projects/reconstruct/{job_id}/stream")
def reconstruct_stream(job_id: str) -> StreamingResponse:
    return _sse(job_id)


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


# --- generated output files (right-side read-only preview) ---
_OUT_DIR = "_paperflow_out"
_PREVIEW_KINDS = {"md", "json", "html", "tex", "txt"}


def _safe_in_out(project_dir: str, rel: str) -> Path | None:
    """Resolve rel within <project>/_paperflow_out, refusing traversal."""
    out = (Path(project_dir) / _OUT_DIR).resolve()
    target = (Path(project_dir) / rel).resolve()
    if out != target and out not in target.parents:
        return None
    return target


@app.get("/api/projects/output/list")
def list_output(project_dir: str) -> dict:
    """Generated files (the centre column the user clicks to preview)."""
    out = Path(project_dir) / _OUT_DIR
    files: list[dict] = []
    if out.is_dir():
        for p in sorted(out.rglob("*")):
            if not p.is_file() or p.name.startswith("."):
                continue
            kind = p.suffix.lower().lstrip(".") or "file"
            files.append({"name": p.name, "rel": str(p.relative_to(project_dir)),
                          "kind": kind, "size": p.stat().st_size,
                          "previewable": kind in _PREVIEW_KINDS or kind in ("pdf", "docx")})
    return {"files": files}


@app.get("/api/projects/output/preview")
def preview_output(project_dir: str, rel: str) -> dict:
    """Render a generated file as read-only HTML for the right pane."""
    target = _safe_in_out(project_dir, rel)
    if target is None or not target.is_file():
        return {"error": "not_found"}
    kind = target.suffix.lower().lstrip(".")
    if kind in ("pdf", "docx"):
        # binary — the UI embeds/links these via the download endpoint instead
        return {"kind": kind, "html": "", "download": True}
    text = target.read_text(errors="replace")
    from ..output import manuscript_state as ms_mod
    if target.name == "manuscript.json":
        try:
            ms = ms_mod.ManuscriptState.model_validate_json(text)
            return {"kind": "manuscript", "html": ms_mod.to_html(ms)}
        except Exception:
            pass
    if kind == "html":
        return {"kind": "html", "html": text}
    if kind == "md":
        return {"kind": "md", "html": f'<div class="pf-preview">{ms_mod._md_block_to_html(text)}</div>'}
    # json / tex / txt -> escaped monospace block
    import html as _html
    return {"kind": kind, "html": f"<pre class='pf-pre'>{_html.escape(text)}</pre>"}


@app.get("/api/projects/output/file")
def get_output_file(project_dir: str, rel: str):
    """Raw download/serve of a generated file (used for .docx / .pdf)."""
    target = _safe_in_out(project_dir, rel)
    if target is None or not target.is_file():
        return JSONResponse({"error": "not_found"}, status_code=404)
    media = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf", "json": "application/json",
    }.get(target.suffix.lower().lstrip("."), "application/octet-stream")
    return FileResponse(target, media_type=media, filename=target.name)


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


def _progress_fn(q: "queue.Queue"):
    def progress(msg: str) -> None:
        m = _STEP_RE.match(msg)
        step_id, label = (m.group(1), m.group(2)) if m else ("", msg)
        q.put({"type": "progress", "step_id": step_id, "label": label, "raw": msg})
    return progress


def _proposal(project_dir: str) -> dict | None:
    """The plan the user reviews/edits in Stage 3 — claims, subheadings, figure sketches."""
    pl = mr.load_plan(project_dir)
    if pl is None:
        return None
    nodes = (pl.get("claim_graph") or {}).get("nodes") or []
    edges = (pl.get("claim_graph") or {}).get("edges") or []
    claims = [{"id": n.get("id"), "text": n.get("text", "")}
              for n in nodes if n.get("kind") == "claim"][:10]
    figs = [{"id": f.get("id"), "kind": f.get("kind"), "message": f.get("message"),
             "section": f.get("section"), "svg": f.get("svg", "")}
            for f in (pl.get("figures") or {}).get("figures") or []]
    return {
        "classification": pl.get("classification"),
        "main_contribution": pl.get("main_contribution", ""),
        "claims": claims, "structure": pl.get("structure", {}),
        "figures": figs, "sections": pl.get("sections", []),
        "graph": _graph_view(nodes, edges),
    }


def _graph_view(nodes: list, edges: list) -> list:
    """Per-MAIN-claim grouped view of the claim graph for the Stage-3 UI. For each claim
    (main + its subclaims) attach the directly-connected supporting nodes by kind."""
    by_id = {n.get("id"): n for n in nodes if isinstance(n, dict) and n.get("id")}
    claims = [n for n in nodes if isinstance(n, dict) and n.get("kind") == "claim" and n.get("id")]
    subs_of: dict = {}
    for c in claims:
        pid = c.get("parent_id")
        if pid:
            subs_of.setdefault(pid, []).append(c)
    mains = [c for c in claims if not c.get("parent_id")] or claims

    def support(claim_id):
        ev, methods, data, figures, refs = [], [], [], [], []
        for e in edges:
            if not isinstance(e, dict) or e.get("dst") != claim_id:
                continue
            src = by_id.get(e.get("src"))
            if not src:
                continue
            rel, kind = e.get("rel"), src.get("kind")
            item = {"id": src.get("id"), "text": src.get("text", "")}
            if rel == "supports" and kind == "evidence":
                ev.append(item)
            elif rel == "justifies" and kind in ("warrant", "source"):
                refs.append(item)
        # for each supporting evidence, pull its method/data/artifact via edges
        ev_ids = {x["id"] for x in ev}
        for e in edges:
            if not isinstance(e, dict):
                continue
            src, dst = by_id.get(e.get("src")), by_id.get(e.get("dst"))
            rel = e.get("rel")
            if not src or not dst:
                continue
            item_src = {"id": src.get("id"), "text": src.get("text", "")}
            # method produces evidence/data ; evidence derived_from data ; method uses data
            if dst.get("id") in ev_ids and rel == "produces" and src.get("kind") == "method":
                methods.append(item_src)
            if src.get("id") in ev_ids and rel == "derived_from" and dst.get("kind") == "data":
                data.append({"id": dst.get("id"), "text": dst.get("text", "")})
            if rel == "produces" and src.get("kind") == "method" and dst.get("kind") == "data" \
                    and dst.get("id") in {d["id"] for d in data}:
                methods.append(item_src)
            # artifact visualizes evidence
            if rel == "visualizes" and src.get("kind") == "artifact" and dst.get("id") in ev_ids:
                figures.append(item_src)

        def dedup(xs):
            seen, out = set(), []
            for x in xs:
                if x["id"] not in seen:
                    seen.add(x["id"]); out.append(x)
            return out
        return {"evidence": dedup(ev), "methods": dedup(methods), "data": dedup(data),
                "figures": dedup(figures), "refs": dedup(refs)}

    out = []
    for m in mains:
        subclaims = []
        for c in [m, *subs_of.get(m.get("id"), [])]:
            subclaims.append({"id": c.get("id"), "text": c.get("text", ""), **support(c.get("id"))})
        out.append({"claim": {"id": m.get("id"), "text": m.get("text", "")},
                    "subclaims": subclaims})
    return out


def _plan_job(job_id: str, project_dir: str, sections: list[str], litsearch: bool) -> None:
    q = _JOBS[job_id]
    try:
        mr.plan(project_dir, sections, progress=_progress_fn(q), litsearch=litsearch)
        q.put({"type": "plan_ready", "proposal": _proposal(project_dir)})
    except Exception as e:
        q.put({"type": "error", "error": str(e)[:400]})
    finally:
        q.put(None)


def _run_job(job_id: str, project_dir: str) -> None:
    q = _JOBS[job_id]
    try:
        out_dir = Path(project_dir) / "_paperflow_out"
        manifest = mr.generate_from_plan(project_dir, out_dir, progress=_progress_fn(q))
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


def _load_bearing_warnings(project_dir: str) -> list[str]:
    """Adaptive-loop replacement for the old hard gate: load-bearing graph gaps that are
    still unanswered. These are WARNINGS — they never block planning/generation."""
    graph = mr.load_prelim_graph(project_dir)
    rs, inv = build_state.load(project_dir)
    return qloop.warnings_for(graph, rs, inv, answered=qloop.load_answers(project_dir))


_DEFAULT_SECTIONS = ["method", "result", "discussion", "introduction", "conclusion", "abstract"]


@app.post("/api/projects/plan")
def start_plan(body: dict) -> dict:
    """Phase 1 — build the plan (claim graph + structure + figures) for the user to confirm.
    No hard gate: unanswered load-bearing gaps are returned as warnings, not blockers."""
    project_dir = body["project_dir"]
    sections = body.get("sections") or _DEFAULT_SECTIONS
    litsearch = bool(body.get("litsearch", True))
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = queue.Queue()
    threading.Thread(target=_plan_job, args=(job_id, project_dir, sections, litsearch),
                     daemon=True).start()
    return {"job_id": job_id, "steps": [{"id": s, "label": label} for s, label in PLAN_STEPS],
            "warnings": _load_bearing_warnings(project_dir)}


@app.get("/api/projects/plan/state")
def plan_state(project_dir: str) -> dict:
    return {"proposal": _proposal(project_dir)}


@app.post("/api/projects/chat")
def chat(body: dict) -> dict:
    """Stage-3 chat — refine the plan (subheadings / figure intent / contribution)."""
    project_dir = body["project_dir"]
    pl = mr.load_plan(project_dir)
    if pl is None:
        return {"error": "no_plan"}
    reply, pl = plan_chat.revise(pl, body.get("history", []), body.get("message", ""))
    mr.save_plan(project_dir, pl)
    return {"reply": reply, "proposal": _proposal(project_dir)}


@app.post("/api/projects/generate")
def generate(body: dict) -> dict:
    """Phase 2 — draft + validate + cite + output, from the CONFIRMED plan.
    No hard gate: load-bearing gaps still open are returned as warnings."""
    project_dir = body["project_dir"]
    if mr.load_plan(project_dir) is None:  # must plan + confirm first
        return {"error": "no_plan"}
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = queue.Queue()
    threading.Thread(target=_run_job, args=(job_id, project_dir), daemon=True).start()
    return {"job_id": job_id, "steps": [{"id": s, "label": label} for s, label in GEN_STEPS],
            "warnings": _load_bearing_warnings(project_dir)}


def _sse(job_id: str) -> StreamingResponse:
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


@app.get("/api/projects/plan/{job_id}/stream")
def plan_stream(job_id: str) -> StreamingResponse:
    return _sse(job_id)


@app.get("/api/projects/generate/{job_id}/stream")
def stream(job_id: str) -> StreamingResponse:
    return _sse(job_id)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)
