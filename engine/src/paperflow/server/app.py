"""FastAPI backend for the paperflow web UI (single local user).

Flow is two-phase to avoid pausing mid-pipeline:
  1) create project -> diagnose (ingest + requirement.detect) -> return questions
  2) submit answers (answer.json) -> generate (rest of pipeline) with live SSE progress

Reuses the engine as-is: ingest, detect.detect, flows.method_result.run, config.
Progress is streamed via SSE (one-way server->client; native EventSource in the browser).
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import queue
import re
import secrets
import threading
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .. import config
from ..compile import plan_chat
from ..flows import method_result as mr
from ..flows.method_result import GEN_STEPS, PLAN_STEPS
from ..ingest import build_artifact_manifest
from ..ingest.parse_inputs import ingest
from ..interview import (
    InterviewState,
    answer_question,
    audit_graph,
    start_interview,
)
from ..llm import client as llm_client
from ..requirement import detect
from ..schemas.claim import ClaimGraph
from ..util import prompt
from . import storage

app = FastAPI(title="paperflow")

_STATIC = Path(__file__).resolve().parent / "static"
# Server-owned storage root. Every client project reference is constrained underneath it.
_WORKSPACE = storage.STORAGE_ROOT
_ACCESS_TOKEN = os.getenv("PAPERFLOW_ACCESS_TOKEN", "").strip()
_REQUIRE_AUTH = os.getenv("PAPERFLOW_REQUIRE_AUTH", "0").strip().lower() in {"1", "true", "yes"}
if _REQUIRE_AUTH and not _ACCESS_TOKEN:
    raise RuntimeError("PAPERFLOW_ACCESS_TOKEN is required when PAPERFLOW_REQUIRE_AUTH=1")
if _REQUIRE_AUTH and not (os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")):
    raise RuntimeError("OPENAI_API_KEY or DEEPSEEK_API_KEY is required for the hosted alpha")

# job_id -> Queue of SSE event dicts (live runs only)
_JOBS: dict[str, "queue.Queue[dict | None]"] = {}
_ACTIVE_JOB_LOCK = threading.Lock()
_ACTIVE_JOB_ID: str | None = None

_STEP_RE = re.compile(r"^\[(\w+)\]\s*(.*)")


class ProjectBusyError(RuntimeError):
    pass


@app.exception_handler(FileNotFoundError)
async def not_found_handler(_request: Request, exc: FileNotFoundError):
    return JSONResponse({"error": "project_not_found", "detail": Path(str(exc)).name},
                        status_code=404)


@app.exception_handler(ValueError)
async def invalid_request_handler(_request: Request, exc: ValueError):
    return JSONResponse({"error": "invalid_request", "detail": str(exc)[:240]}, status_code=400)


@app.exception_handler(ProjectBusyError)
async def project_busy_handler(_request: Request, _exc: ProjectBusyError):
    return JSONResponse({"error": "server_busy", "active_job_id": _ACTIVE_JOB_ID}, status_code=409)


def _assert_mutable() -> None:
    with _ACTIVE_JOB_LOCK:
        if _ACTIVE_JOB_ID is not None:
            raise ProjectBusyError("a model job is currently active")


def _claim_global_job(job_id: str) -> bool:
    """The alpha runs one LLM pipeline at a time to keep cost and manifests isolated."""
    global _ACTIVE_JOB_ID
    with _ACTIVE_JOB_LOCK:
        if _ACTIVE_JOB_ID is not None:
            return False
        _ACTIVE_JOB_ID = job_id
        return True


def _release_global_job(job_id: str) -> None:
    global _ACTIVE_JOB_ID
    with _ACTIVE_JOB_LOCK:
        if _ACTIVE_JOB_ID == job_id:
            _ACTIVE_JOB_ID = None


def _slug(name: str) -> str:
    return storage.slug(name)


def _project(body: dict, *, must_exist: bool = True) -> Path:
    return storage.ref_from_body(body, must_exist=must_exist)


def _query_project(project_id: str = "", project_dir: str = "") -> Path:
    return storage.resolve_project(project_id=project_id, project_dir=project_dir)


def _canonical_graph_path(project: Path) -> Path:
    return project / "main" / "knowledge_graph.json"


def _interview_path(project: Path) -> Path:
    return project / "main" / "interview.json"


def _audit_path(project: Path) -> Path:
    return project / "main" / "logic_audit.json"


def _load_graph(project: Path) -> ClaimGraph | None:
    raw = storage.read_json(_canonical_graph_path(project), None)
    if raw is None:
        plan = mr.load_plan(str(project))
        raw = (plan or {}).get("claim_graph")
    if not raw:
        return None
    return ClaimGraph.model_validate(raw)


def _save_graph(project: Path, graph: ClaimGraph) -> None:
    raw = graph.model_dump(mode="json")
    storage.write_json(_canonical_graph_path(project), raw)
    plan = mr.load_plan(str(project))
    if plan is not None:
        plan["claim_graph"] = raw
        mr.save_plan(str(project), plan)


def _load_interview(project: Path, graph: ClaimGraph) -> InterviewState:
    raw = storage.read_json(_interview_path(project), None)
    state = InterviewState.model_validate(raw) if raw else None
    return start_interview(graph, state)


def _persist_interview(project: Path, state: InterviewState, audit) -> None:
    storage.write_json(_interview_path(project), state.model_dump(mode="json"))
    storage.write_json(_audit_path(project), audit.model_dump(mode="json"))


@app.middleware("http")
async def access_guard(request: Request, call_next):
    """Optional shared access-code guard for a controlled public alpha.

    Configure ``PAPERFLOW_ACCESS_TOKEN`` in the hosting secret store. Browsers receive
    a standard Basic-auth challenge; API clients may alternatively send a Bearer token.
    """
    response = None
    if _ACCESS_TOKEN and request.url.path != "/healthz":
        auth = request.headers.get("authorization", "")
        supplied = ""
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
        elif auth.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth[6:].strip()).decode("utf-8")
                supplied = decoded.partition(":")[2]
            except Exception:
                supplied = ""
        if not supplied or not secrets.compare_digest(supplied, _ACCESS_TOKEN):
            response = JSONResponse(
            {"error": "authentication_required"}, status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="PaperFlow Alpha"'},
        )
    if response is None:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "frame-src 'self'; object-src 'none'; base-uri 'self'"
    )
    return response


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "paperflow"}


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


def _write_profile_inputs(project: Path, body: dict) -> dict:
    """Persist the product profile and synthesize the legacy three-file input contract.

    This lets a researcher start with an objective and files instead of first authoring a
    polished core message and outline. The interview/graph stages refine these candidates.
    """
    profile = {
        "name": str(body.get("name", "")).strip(),
        "field": str(body.get("field", "")).strip(),
        "document_type": str(body.get("document_type", "journal_paper")).strip(),
        "target_journal": str(body.get("target_journal", "")).strip(),
        "objective": str(body.get("objective", "")).strip(),
        "methods_summary": str(body.get("methods_summary", "")).strip(),
        "results_summary": str(body.get("results_summary", "")).strip(),
    }
    main = project / "main"
    main.mkdir(parents=True, exist_ok=True)
    storage.write_json(main / "profile.json", profile)

    target = profile["target_journal"] or "To be selected"
    title = profile["name"] or "Untitled manuscript"
    objective = profile["objective"] or "Research objective to be refined through interview"
    novelty = profile["results_summary"] or objective
    method = profile["methods_summary"] or "Methods to be extracted from the uploaded sources"
    result = profile["results_summary"] or "Results and supporting evidence to be extracted from files"
    (main / "0_journal_info.md").write_text(
        f"## Working title\n{title}\n\n## Author's field\n{profile['field']}\n\n"
        f"## Target journals\n1. {target}\n"
    )
    (main / "1_coremessage.md").write_text(
        f"## One paragraph\n{objective}\n\n## Novelty\n- {novelty}\n"
    )
    (main / "3_outline.md").write_text(
        f"[Method]\n1. {method}\n\n[Result]\n2. {result}\n\n"
        f"## Phase B (structure)\n### Method\n{method}\n\n### Result\n{result}\n"
    )
    return profile


@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/api/providers")
def providers() -> dict:
    return {"providers": config.available_providers()}


@app.post("/api/projects")
def create_project(body: dict) -> dict:
    """Attach an existing project (body.project_dir) or create one from the 3 inputs."""
    if body.get("project_id") or body.get("project_dir"):
        project_dir = _project(body)
    else:
        project_dir = storage.project_path(storage.new_project_id(body.get("name", "untitled")))
        project_dir.mkdir(parents=True, exist_ok=False)
        _write_inputs(project_dir, body)
    return {**storage.public_ref(project_dir), "providers": config.available_providers()}


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
        "project_id": pdir.name, "project_dir": str(pdir), "name": meta.get("name") or pdir.name,
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
    project = storage.project_path(storage.new_project_id(body.get("name", "untitled")))
    main = project / "main"
    main.mkdir(parents=True, exist_ok=True)
    meta = {"name": body.get("name", "untitled"), "deadline": body.get("deadline", ""),
            "created": body.get("created", "")}
    storage.write_json(main / "project.json", meta)
    storage.write_json(storage.workflow_path(project), storage.default_workflow())
    if body.get("objective") or body.get("field"):
        _write_profile_inputs(project, body)
    return storage.public_ref(project)


@app.post("/api/projects/save")
def save_inputs(body: dict) -> dict:
    """Persist the 3 input files + the structured UI state (for lossless reopen)."""
    _assert_mutable()
    project = _project(body)
    main = project / "main"
    main.mkdir(parents=True, exist_ok=True)
    for fn, c in {"0_journal_info.md": body.get("journal_info_md", ""),
                  "1_coremessage.md": body.get("coremessage_md", ""),
                  "3_outline.md": body.get("outline_md", "")}.items():
        if c:
            (main / fn).write_text(c)
    if body.get("ui_state") is not None:
        storage.write_json(main / "_ui_state.json", body["ui_state"])
    state = storage.read_workflow(project)
    storage.update_workflow(
        project, stage="sources_ready", source_revision=int(state["source_revision"]) + 1,
        confirmed_graph_revision=None,
    )
    return {"ok": True, **storage.public_ref(project)}


@app.post("/api/projects/profile")
def save_profile(body: dict) -> dict:
    _assert_mutable()
    project = _project(body)
    if not str(body.get("field", "")).strip() or not str(body.get("objective", "")).strip():
        return {"error": "field_and_objective_required"}
    profile = _write_profile_inputs(project, body)
    state = storage.read_workflow(project)
    storage.update_workflow(
        project, stage="sources_ready", source_revision=int(state["source_revision"]) + 1,
        confirmed_graph_revision=None,
    )
    return {"ok": True, "profile": profile, **storage.public_ref(project)}


@app.get("/api/projects/state")
def get_state(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    out = project / "_paperflow_out"
    paper_ready = (out / "paper.pdf").is_file() or (out / "paper.tex").is_file()
    p = project / "main" / "_ui_state.json"
    if p.is_file():
        try:
            return {"ui_state": json.loads(p.read_text()), "paper_ready": paper_ready,
                    "workflow": storage.read_workflow(project), **storage.public_ref(project)}
        except Exception:
            pass
    return {"ui_state": None, "paper_ready": paper_ready,
            "workflow": storage.read_workflow(project), **storage.public_ref(project)}


@app.post("/api/projects/diagnose")
def diagnose(body: dict) -> dict:
    """Ingest + detect missing info -> questions (each with an example placeholder)."""
    project = _project(body)
    project_dir = str(project)
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
    project = _project(body)
    main = project / "main"
    main.mkdir(parents=True, exist_ok=True)
    answers = body.get("answers", {})
    storage.write_json(main / "answer.json", answers)
    storage.invalidate_graph_confirmation(project, stage="questioning")
    return {"ok": True, "count": len(answers), **storage.public_ref(project)}


# --- data files (experiment data / references the writer grounds claims on) ---
_UPLOAD_SUBDIR = "data/uploads"
_ALLOWED_EXT = {".csv", ".txt", ".dat", ".md", ".pdf", ".png", ".jpg", ".jpeg",
                ".xlsx", ".xls", ".json", ".bib"}
_MAX_FILE_BYTES = int(os.getenv("PAPERFLOW_MAX_FILE_BYTES", str(20 * 1024 * 1024)))
_MAX_PROJECT_BYTES = int(os.getenv("PAPERFLOW_MAX_PROJECT_BYTES", str(100 * 1024 * 1024)))
_MAX_STORAGE_BYTES = int(os.getenv("PAPERFLOW_MAX_STORAGE_BYTES", str(800 * 1024 * 1024)))
_ALLOWED_MIME = {
    "text/plain", "text/csv", "text/markdown", "application/json", "application/pdf",
    "image/png", "image/jpeg", "application/octet-stream",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


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
def list_files(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    return {"files": _list_data_files(project), **storage.public_ref(project)}


@app.get("/api/projects/paper")
def get_paper(project_id: str = "", project_dir: str = "", kind: str = "pdf"):
    """Serve the assembled manuscript — kind=pdf (compiled) or tex (source)."""
    project = _query_project(project_id, project_dir)
    allowed = {"pdf": "paper.pdf", "tex": "paper.tex"}
    if kind not in allowed:
        return JSONResponse({"error": "unsupported_output", "kind": kind}, status_code=400)
    f = project / "_paperflow_out" / allowed[kind]
    if not f.is_file():
        return JSONResponse({"error": "not_found", "kind": kind}, status_code=404)
    media = "application/pdf" if kind == "pdf" else "text/plain; charset=utf-8"
    return FileResponse(f, media_type=media)


def _output_items(project: Path) -> list[dict]:
    out = project / "_paperflow_out"
    if not out.is_dir():
        return []
    items = []
    for p in sorted(out.iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        items.append({"name": p.name, "size": p.stat().st_size, "sha256": digest})
    return items


@app.get("/api/projects/outputs")
def outputs(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    return {"outputs": _output_items(project), "workflow": storage.read_workflow(project),
            **storage.public_ref(project)}


@app.get("/api/projects/download")
def download(project_id: str = "", project_dir: str = "", kind: str = "zip"):
    project = _query_project(project_id, project_dir)
    out = project / "_paperflow_out"
    names = {"pdf": "paper.pdf", "tex": "paper.tex", "graph": "knowledge_graph.json",
             "audit": "logic_audit.json"}
    if kind == "zip":
        if not out.is_dir():
            return JSONResponse({"error": "not_found", "kind": kind}, status_code=404)
        archive = out / "paperflow-output.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out.iterdir()):
                if p.is_file() and p != archive and not p.name.startswith("."):
                    zf.write(p, arcname=p.name)
        return FileResponse(archive, media_type="application/zip", filename=archive.name)
    name = names.get(kind)
    if not name:
        return JSONResponse({"error": "unsupported_output", "kind": kind}, status_code=400)
    target = out / name
    if not target.is_file():
        return JSONResponse({"error": "not_found", "kind": kind}, status_code=404)
    return FileResponse(target, filename=target.name)


@app.post("/api/projects/upload")
async def upload_files(project_id: str = Form(""), project_dir: str = Form(""),
                       files: list[UploadFile] = None) -> dict:
    _assert_mutable()
    project = _query_project(project_id, project_dir)
    dest = project / _UPLOAD_SUBDIR
    dest.mkdir(parents=True, exist_ok=True)
    used = sum(p.stat().st_size for p in project.rglob("*") if p.is_file())
    storage_used = sum(p.stat().st_size for p in _WORKSPACE.rglob("*") if p.is_file())
    saved, rejected = [], []
    for uf in files or []:
        name = Path(uf.filename or "").name  # strip any path components
        ext = Path(name).suffix.lower()
        mime = (uf.content_type or "application/octet-stream").lower()
        if not name or ext not in _ALLOWED_EXT or mime not in _ALLOWED_MIME:
            rejected.append({"name": name, "reason": "unsupported_type"})
            continue
        stored_name = f"{uuid.uuid4().hex[:12]}_{_slug(Path(name).stem)}{ext}"
        target = dest / stored_name
        size = 0
        try:
            with target.open("wb") as out:
                while True:
                    chunk = await uf.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > _MAX_FILE_BYTES or used + size > _MAX_PROJECT_BYTES \
                            or storage_used + size > _MAX_STORAGE_BYTES:
                        raise ValueError("upload_limit_exceeded")
                    out.write(chunk)
        except Exception as exc:
            target.unlink(missing_ok=True)
            rejected.append({"name": name, "reason": str(exc)[:80]})
            continue
        used += size
        storage_used += size
        saved.append({"name": name, "stored_name": stored_name, "size": size, "mime": mime})
    if saved:
        state = storage.read_workflow(project)
        storage.update_workflow(
            project, stage="sources_ready", source_revision=int(state["source_revision"]) + 1,
            confirmed_graph_revision=None,
        )
    return {"ok": not rejected, "saved": saved, "rejected": rejected,
            "files": _list_data_files(project), **storage.public_ref(project)}


@app.post("/api/projects/extract")
def extract_sources(body: dict) -> dict:
    """Build the bounded, provenance-addressable source manifest for this revision."""
    _assert_mutable()
    project = _project(body)
    manifest = build_artifact_manifest(project)
    payload = manifest.to_dict()
    storage.write_json(project / "main" / "artifact_manifest.json", payload)
    state = storage.update_workflow(
        project, stage="sources_extracted", confirmed_graph_revision=None, last_error=None,
    )
    extracted = sum(a["status"] == "extracted" for a in payload["artifacts"])
    return {
        "ok": extracted > 0 or not payload["artifacts"],
        "summary": {
            "artifacts": len(payload["artifacts"]),
            "extracted": extracted,
            "chunks": sum(len(a.get("chunks") or []) for a in payload["artifacts"]),
            "warnings": payload.get("warnings") or [],
        },
        "workflow": state,
        **storage.public_ref(project),
    }


@app.post("/api/projects/files/delete")
def delete_file(body: dict) -> dict:
    _assert_mutable()
    project = _project(body)
    rel = body.get("rel", "")
    target = _safe_under(project, rel)
    if target and target.is_file():
        target.unlink()
    notes = _read_notes(project)  # drop any orphaned note
    if notes.pop(rel, None) is not None:
        storage.write_json(_notes_path(project), notes)
    state = storage.read_workflow(project)
    storage.update_workflow(
        project, stage="sources_ready", source_revision=int(state["source_revision"]) + 1,
        confirmed_graph_revision=None,
    )
    return {"ok": True, "files": _list_data_files(project), **storage.public_ref(project)}


@app.post("/api/projects/files/note")
def set_file_note(body: dict) -> dict:
    """One free-text description per file — surfaced to the writer as grounding context."""
    _assert_mutable()
    project = _project(body)
    rel = body.get("rel", "")
    note = str(body.get("note", "")).strip()
    notes = _read_notes(project)
    if note:
        notes[rel] = note
    else:
        notes.pop(rel, None)
    p = _notes_path(project)
    p.parent.mkdir(parents=True, exist_ok=True)
    storage.write_json(p, notes)
    state = storage.read_workflow(project)
    storage.update_workflow(
        project, stage="sources_ready", source_revision=int(state["source_revision"]) + 1,
        confirmed_graph_revision=None,
    )
    return {"ok": True}


def _append_job_event(project: Path, event: dict) -> dict:
    state = storage.read_workflow(project)
    event_id = int(state.get("last_event_id") or 0) + 1
    row = {"event_id": event_id, **event}
    path = project / "main" / "job_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    storage.update_workflow(project, last_event_id=event_id)
    return row


def _progress_fn(q: "queue.Queue", project: Path | None = None):
    def progress(msg: str) -> None:
        m = _STEP_RE.match(msg)
        step_id, label = (m.group(1), m.group(2)) if m else ("", msg)
        event = {"type": "progress", "step_id": step_id, "label": label, "raw": msg}
        q.put(_append_job_event(project, event) if project is not None else event)
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
    project = Path(project_dir)
    try:
        mr.plan(project_dir, sections, progress=_progress_fn(q, project), litsearch=litsearch)
        state = storage.read_workflow(project)
        revision = int(state.get("graph_revision") or 0) + 1
        plan = mr.load_plan(project_dir)
        graph = ClaimGraph.model_validate((plan or {})["claim_graph"])
        graph.revision = revision
        graph.built_from_source_revision = int(state.get("source_revision") or 0)
        _save_graph(project, graph)
        interview = start_interview(graph)
        audit = audit_graph(graph)
        _persist_interview(project, interview, audit)
        storage.update_workflow(
            project, stage="questioning" if interview.pending_questions() else "graph_review",
            active_job_id=None, graph_revision=revision, confirmed_graph_revision=None,
            blocking_items=[f.model_dump(mode="json") for f in audit.findings
                            if f.severity == "blocking"],
            last_error=None,
        )
        q.put({
            "type": "plan_ready", "proposal": _proposal(project_dir),
            "graph_revision": revision,
            "question_count": len(interview.pending_questions()),
            "next_question": (
                interview.pending_questions()[0].model_dump(mode="json")
                if interview.pending_questions() else None
            ),
            "audit": audit.model_dump(mode="json"),
        })
    except Exception as e:
        storage.update_workflow(project, stage="failed", active_job_id=None, last_error=str(e)[:400])
        q.put({"type": "error", "error": str(e)[:400]})
    finally:
        _release_global_job(job_id)
        q.put(None)


def _run_job(job_id: str, project_dir: str) -> None:
    q = _JOBS[job_id]
    project = Path(project_dir)
    try:
        out_dir = project / "_paperflow_out"
        manifest = mr.generate_from_plan(project_dir, out_dir, progress=_progress_fn(q, project))
        graph = _load_graph(project)
        audit = audit_graph(graph) if graph is not None else None
        if graph is not None:
            storage.write_json(out_dir / "knowledge_graph.json", graph.model_dump(mode="json"))
        if audit is not None:
            storage.write_json(out_dir / "logic_audit.json", audit.model_dump(mode="json"))
        workflow_snapshot = storage.read_workflow(project)
        storage.write_json(out_dir / "paperflow_run.json", {
            "graph_revision": workflow_snapshot.get("graph_revision"),
            "confirmed_graph_revision": workflow_snapshot.get("confirmed_graph_revision"),
            "source_revision": workflow_snapshot.get("source_revision"),
            "input_tokens": manifest.total_input,
            "output_tokens": manifest.total_output,
            "cached_tokens": manifest.total_cached,
        })
        output_files = [
            {"name": p.name, "size": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(out_dir.iterdir()) if p.is_file()
        ] if out_dir.is_dir() else []
        storage.update_workflow(
            project, stage="complete", active_job_id=None, artifacts=output_files, last_error=None,
        )
        q.put({"type": "done",
               "classification": manifest.classification.value if manifest.classification else None,
               "input_tokens": manifest.total_input, "output_tokens": manifest.total_output,
               "cached_tokens": manifest.total_cached,
               "cache_hit_rate": round(manifest.cache_hit_rate, 4),
               "outputs": output_files,
               "pdf_ready": any(item["name"] == "paper.pdf" for item in output_files),
               "out_dir": str(out_dir)})
    except Exception as e:  # surface the failure to the client instead of hanging
        storage.update_workflow(project, stage="failed", active_job_id=None, last_error=str(e)[:400])
        q.put({"type": "error", "error": str(e)[:400]})
    finally:
        _release_global_job(job_id)
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


_DEFAULT_SECTIONS = ["method", "result", "discussion", "introduction", "conclusion", "abstract"]


@app.post("/api/projects/plan")
def start_plan(body: dict) -> dict:
    """Phase 1 — build the plan (claim graph + structure + figures) for the user to confirm."""
    project = _project(body)
    project_dir = str(project)
    pending = _unanswered(project_dir)
    if pending:  # hard gate — must answer the questions before planning
        return {"error": "unanswered_questions", "pending": pending}
    sections = body.get("sections") or _DEFAULT_SECTIONS
    litsearch = bool(body.get("litsearch", True))
    job_id = uuid.uuid4().hex[:12]
    if not _claim_global_job(job_id):
        return {"error": "server_busy", "active_job_id": _ACTIVE_JOB_ID}
    _JOBS[job_id] = queue.Queue()
    storage.update_workflow(project, stage="extracting", active_job_id=job_id, last_error=None)
    threading.Thread(target=_plan_job, args=(job_id, project_dir, sections, litsearch),
                     daemon=True).start()
    return {"job_id": job_id, "steps": [{"id": s, "label": label} for s, label in PLAN_STEPS]}


@app.get("/api/projects/plan/state")
def plan_state(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    return {"proposal": _proposal(str(project)), "workflow": storage.read_workflow(project),
            **storage.public_ref(project)}


@app.post("/api/projects/chat")
def chat(body: dict) -> dict:
    """Stage-3 chat — refine the plan (subheadings / figure intent / contribution)."""
    _assert_mutable()
    project = _project(body)
    project_dir = str(project)
    pl = mr.load_plan(project_dir)
    if pl is None:
        return {"error": "no_plan"}
    reply, pl = plan_chat.revise(pl, body.get("history", []), body.get("message", ""))
    state = storage.read_workflow(project)
    revision = int(state.get("graph_revision") or 0) + 1
    graph = ClaimGraph.model_validate(pl["claim_graph"])
    graph.revision = revision
    graph.built_from_source_revision = int(state.get("source_revision") or 0)
    pl["claim_graph"] = graph.model_dump(mode="json")
    mr.save_plan(project_dir, pl)
    _save_graph(project, graph)
    interview = _load_interview(project, graph)
    audit = audit_graph(graph)
    _persist_interview(project, interview, audit)
    storage.update_workflow(
        project, stage="questioning" if interview.pending_questions() else "graph_review",
        graph_revision=revision, confirmed_graph_revision=None,
        blocking_items=[f.model_dump(mode="json") for f in audit.findings
                        if f.severity == "blocking"],
    )
    return {
        "reply": reply, "proposal": _proposal(project_dir), "graph_revision": revision,
        "next_question": (
            interview.pending_questions()[0].model_dump(mode="json")
            if interview.pending_questions() else None
        ),
        "audit": audit.model_dump(mode="json"),
    }


@app.get("/api/projects/workflow/state")
def workflow_state(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    state = storage.read_workflow(project)
    active = state.get("active_job_id")
    if active and active not in _JOBS:
        state = storage.update_workflow(
            project, stage="interrupted", active_job_id=None,
            last_error="The server restarted while this job was running. Retry the last stage.",
        )
    return {"workflow": state, **storage.public_ref(project)}


@app.get("/api/projects/graph")
def graph_state(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    graph = _load_graph(project)
    if graph is None:
        return {"error": "no_graph", "workflow": storage.read_workflow(project)}
    state = storage.read_workflow(project)
    if graph.built_from_source_revision != int(state.get("source_revision") or 0):
        return {"error": "stale_graph", "workflow": state, **storage.public_ref(project)}
    return {
        "graph": graph.model_dump(mode="json"), "proposal": _proposal(str(project)),
        "graph_revision": state.get("graph_revision"),
        "confirmed_graph_revision": state.get("confirmed_graph_revision"),
        **storage.public_ref(project),
    }


@app.get("/api/projects/questions")
def interview_questions(project_id: str = "", project_dir: str = "") -> dict:
    project = _query_project(project_id, project_dir)
    graph = _load_graph(project)
    if graph is None:
        return {"error": "no_graph", **storage.public_ref(project)}
    workflow = storage.read_workflow(project)
    if graph.built_from_source_revision != int(workflow.get("source_revision") or 0):
        return {"error": "stale_graph", "workflow": workflow, **storage.public_ref(project)}
    state = _load_interview(project, graph)
    audit = audit_graph(graph)
    _persist_interview(project, state, audit)
    pending = state.pending_questions()
    latest_answer = {}
    for answer in state.answers:
        latest_answer[answer.question_id] = answer
    questions = []
    for question in state.questions:
        row = question.model_dump(mode="json")
        answer = latest_answer.get(question.id)
        row["status"] = answer.completion if answer else "pending"
        row["answer_event_id"] = answer.id if answer else None
        row["answer"] = answer.text if answer else ""
        questions.append(row)
    return {
        "questions": questions,
        "next_question": pending[0].model_dump(mode="json") if pending else None,
        "pending_count": len(pending),
        "answers": [a.model_dump(mode="json") for a in state.answers],
        "graph_revision": graph.revision,
        "audit": audit.model_dump(mode="json"),
        **storage.public_ref(project),
    }


def _answer_interview(project: Path, body: dict, *, force_unknown: bool = False) -> dict:
    _assert_mutable()
    graph = _load_graph(project)
    if graph is None:
        return {"error": "no_graph"}
    if "base_revision" not in body:
        return {"error": "base_revision_required", "graph_revision": graph.revision}
    state = _load_interview(project, graph)
    completion = "unknown" if force_unknown else body.get("completion")
    captured_fields = {} if force_unknown else (body.get("captured_fields") or {})
    answer = "" if force_unknown else str(body.get("answer", ""))
    if not force_unknown and completion is None:
        question = next((q for q in state.questions
                         if q.id == str(body.get("question_id", ""))), None)
        if question is None:
            return {"error": "invalid_interview_turn", "detail": "unknown question",
                    "graph_revision": graph.revision}
        try:
            analysis = llm_client.call_json(
                "reasoning", prompt("interview_answer_patch"),
                json.dumps({
                    "question": question.model_dump(mode="json"),
                    "verbatim_answer": answer,
                }, ensure_ascii=False),
                step="interview.answer_analysis", max_tokens=1200,
            )
            completion = analysis.get("completion")
            captured_fields = analysis.get("captured_fields") or {}
        except Exception as exc:
            return {"error": "answer_analysis_failed", "detail": str(exc)[:300],
                    "graph_revision": graph.revision, "retryable": True}
    try:
        turn = answer_question(
            graph, state,
            question_id=str(body.get("question_id", "")),
            answer=answer,
            completion=completion,
            captured_fields=captured_fields,
            base_revision=int(body["base_revision"]),
            supersedes_answer_id=body.get("supersedes_answer_id"),
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return {"error": "invalid_interview_turn", "detail": str(exc)[:300],
                "graph_revision": graph.revision}
    _save_graph(project, turn.graph)
    _persist_interview(project, turn.state, turn.audit)
    workflow = storage.update_workflow(
        project,
        stage="questioning" if turn.next_question else "graph_review",
        graph_revision=turn.graph.revision,
        confirmed_graph_revision=None,
        blocking_items=[f.model_dump(mode="json") for f in turn.audit.findings
                        if f.severity == "blocking"],
    )
    return {
        "ok": True,
        "answer_event": turn.answer_event.model_dump(mode="json"),
        "patch": turn.patch.model_dump(mode="json"),
        "graph": turn.graph.model_dump(mode="json"),
        "next_question": turn.next_question.model_dump(mode="json") if turn.next_question else None,
        "audit": turn.audit.model_dump(mode="json"),
        "workflow": workflow,
        **storage.public_ref(project),
    }


@app.post("/api/projects/questions/answer")
def interview_answer(body: dict) -> dict:
    return _answer_interview(_project(body), body)


@app.post("/api/projects/questions/resolve")
def interview_resolve_unknown(body: dict) -> dict:
    """Record an explicit unknown without turning it into an author-provided fact."""
    return _answer_interview(_project(body), body, force_unknown=True)


@app.post("/api/projects/graph/confirm")
def confirm_graph(body: dict) -> dict:
    project = _project(body)
    state = storage.read_workflow(project)
    revision = int(state.get("graph_revision") or 0)
    requested = int(body.get("graph_revision", revision))
    graph = _load_graph(project)
    if revision <= 0 or requested != revision or graph is None or graph.revision != revision:
        return {"error": "stale_or_missing_graph", "graph_revision": revision}
    if graph.built_from_source_revision != int(state.get("source_revision") or 0):
        return {"error": "source_revision_changed", "graph_revision": revision,
                "source_revision": state.get("source_revision")}
    audit = audit_graph(graph)
    interview = _load_interview(project, graph)
    _persist_interview(project, interview, audit)
    if interview.pending_questions():
        return {
            "error": "pending_questions", "graph_revision": revision,
            "pending_questions": [q.model_dump(mode="json")
                                  for q in interview.pending_questions()],
            "audit": audit.model_dump(mode="json"),
        }
    if not audit.ok:
        return {
            "error": "graph_audit_blocked", "graph_revision": revision,
            "audit": audit.model_dump(mode="json"),
            "pending_questions": [q.model_dump(mode="json")
                                  for q in interview.pending_questions()],
        }
    state = storage.update_workflow(
        project, stage="ready", confirmed_graph_revision=revision,
        blocking_items=[], last_error=None,
    )
    return {"ok": True, "graph_revision": revision, "workflow": state,
            "audit": audit.model_dump(mode="json")}


@app.post("/api/projects/generate")
def generate(body: dict) -> dict:
    """Phase 2 — draft + validate + cite + output, from the CONFIRMED plan."""
    project = _project(body)
    project_dir = str(project)
    storage_used = sum(p.stat().st_size for p in _WORKSPACE.rglob("*") if p.is_file())
    if storage_used >= _MAX_STORAGE_BYTES:
        return {"error": "storage_full"}
    pending = _unanswered(project_dir)
    if pending:
        return {"error": "unanswered_questions", "pending": pending}
    if mr.load_plan(project_dir) is None:  # must plan + confirm first
        return {"error": "no_plan"}
    state = storage.read_workflow(project)
    graph = _load_graph(project)
    if graph is None or graph.built_from_source_revision != int(state.get("source_revision") or 0):
        return {"error": "source_revision_changed", "source_revision": state.get("source_revision")}
    if not state.get("confirmed_graph_revision") \
            or state.get("confirmed_graph_revision") != state.get("graph_revision"):
        return {"error": "graph_not_confirmed", "graph_revision": state.get("graph_revision")}
    job_id = uuid.uuid4().hex[:12]
    if not _claim_global_job(job_id):
        return {"error": "server_busy", "active_job_id": _ACTIVE_JOB_ID}
    _JOBS[job_id] = queue.Queue()
    storage.update_workflow(project, stage="generating", active_job_id=job_id, last_error=None)
    threading.Thread(target=_run_job, args=(job_id, project_dir), daemon=True).start()
    return {"job_id": job_id, "steps": [{"id": s, "label": label} for s, label in GEN_STEPS]}


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
