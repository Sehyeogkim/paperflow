"""Server-owned project storage and small durable workflow state helpers.

The original local prototype trusted arbitrary ``project_dir`` values from the browser.
The product server instead resolves every project underneath one configured storage root.
Legacy absolute paths are accepted only when they still resolve under that same root.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any


_DEFAULT_ROOT = Path(__file__).resolve().parents[4] / "projects"
STORAGE_ROOT = Path(os.getenv("PAPERFLOW_STORAGE_ROOT", str(_DEFAULT_ROOT))).expanduser().resolve()
_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")


def slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip()).strip("_").lower()
    return clean[:48] or "untitled"


def new_project_id(name: str) -> str:
    return f"{slug(name)}-{uuid.uuid4().hex[:10]}"


def project_path(project_id: str) -> Path:
    if not _SAFE_ID.fullmatch(project_id or ""):
        raise ValueError("invalid project_id")
    target = (STORAGE_ROOT / project_id).resolve()
    if target.parent != STORAGE_ROOT:
        raise ValueError("project escapes storage root")
    return target


def resolve_project(*, project_id: str = "", project_dir: str = "", must_exist: bool = True) -> Path:
    """Resolve a client project reference without ever escaping ``STORAGE_ROOT``."""
    if project_id:
        target = project_path(project_id)
    elif project_dir:
        candidate = Path(project_dir).expanduser()
        target = candidate.resolve() if candidate.is_absolute() else (STORAGE_ROOT / candidate).resolve()
        if target != STORAGE_ROOT and STORAGE_ROOT not in target.parents:
            raise ValueError("project_dir must be under the configured storage root")
    else:
        raise ValueError("project_id is required")
    if must_exist and not target.is_dir():
        raise FileNotFoundError(str(target))
    return target


def ref_from_body(body: dict, *, must_exist: bool = True) -> Path:
    return resolve_project(
        project_id=str(body.get("project_id", "")),
        project_dir=str(body.get("project_dir", "")),
        must_exist=must_exist,
    )


def public_ref(project: Path) -> dict[str, str]:
    return {"project_id": project.name, "project_dir": str(project)}


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text()) if path.is_file() else default
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    """Atomic-enough JSON replacement for a single-instance product server."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    tmp.replace(path)


def workflow_path(project: Path) -> Path:
    return project / "main" / "workflow_state.json"


def default_workflow() -> dict:
    return {
        "stage": "draft",
        "source_revision": 0,
        "graph_revision": 0,
        "confirmed_graph_revision": None,
        "active_job_id": None,
        "last_event_id": 0,
        "blocking_items": [],
        "artifacts": [],
        "last_error": None,
    }


def read_workflow(project: Path) -> dict:
    state = default_workflow()
    loaded = read_json(workflow_path(project), {})
    if isinstance(loaded, dict):
        state.update(loaded)
    return state


def update_workflow(project: Path, **changes) -> dict:
    state = read_workflow(project)
    state.update(changes)
    write_json(workflow_path(project), state)
    return state


def invalidate_graph_confirmation(project: Path, *, stage: str | None = None) -> dict:
    state = read_workflow(project)
    state["confirmed_graph_revision"] = None
    if stage:
        state["stage"] = stage
    write_json(workflow_path(project), state)
    return state
