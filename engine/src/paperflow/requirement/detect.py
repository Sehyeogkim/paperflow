"""Missing-information detection + completion classification (reasoning tier)."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..llm import client
from ..schemas.project_state import ProjectState
from ..schemas.requirement import (
    CompletionClass, MissingItem, RequirementPack, RequirementReport,
)
from ..util import inputs_block, prompt

_PACKS = Path(__file__).resolve().parent / "packs"


def report_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / "requirement_report.json"


def save_report(project_dir: str, report: RequirementReport) -> None:
    """Persist the diagnose result so the generate run reuses it (no second LLM call)."""
    p = report_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report.model_dump_json(indent=2))


def load_report(project_dir: str) -> RequirementReport | None:
    p = report_path(project_dir)
    if p.is_file():
        try:
            return RequirementReport.model_validate_json(p.read_text())
        except Exception:
            return None
    return None


def load_pack(study_type: str = "computational_biomechanics") -> RequirementPack:
    """Load a domain pack if present, else degrade to the universal base requirements.

    The literature-grounded pipeline is the primary requirement source; a domain YAML is an
    optional fallback. When no YAML exists on disk, return a minimal universal pack (the six
    base requirements every empirical paper needs) so the fallback path never crashes."""
    p = _PACKS / f"{study_type}.yaml"
    if p.is_file():
        return RequirementPack.model_validate(yaml.safe_load(p.read_text()))
    from .universal import UNIVERSAL_BASE_REQUIREMENTS
    return RequirementPack(study_type=study_type,
                           required=[r["key"] for r in UNIVERSAL_BASE_REQUIREMENTS],
                           conditional=[])


def _priority(m: MissingItem) -> float:
    risk = {"low": 1.0, "medium": 2.0, "high": 3.0}.get(m.reviewer_risk, 2.0)
    return risk  # simple for v1: reviewer risk dominates; refine later


def detect(ps: ProjectState, pack: RequirementPack | None = None) -> RequirementReport:
    pack = pack or load_pack()
    pack_block = (
        f"study_type: {pack.study_type}\n"
        f"required: {pack.required}\n"
        "conditional:\n"
        + "\n".join(f"  - {c.name} (required_when: {c.required_when})" for c in pack.conditional)
    )
    user = f"{inputs_block(ps)}\n\n## REQUIREMENT PACK\n{pack_block}"
    raw = client.call_json("reasoning", prompt("missing_info"), user, step="requirement.detect")

    missing = [MissingItem(**m) for m in raw.get("missing", [])]
    for m in missing:
        m.priority = _priority(m)
    missing.sort(key=lambda m: m.priority, reverse=True)

    try:
        cls = CompletionClass(raw.get("classification", "EXPERT_REVIEW_REQUIRED"))
    except ValueError:
        cls = CompletionClass.EXPERT_REVIEW_REQUIRED

    return RequirementReport(
        study_type=pack.study_type, classification=cls,
        present=raw.get("present", []), missing=missing, notes=raw.get("notes", ""),
    )
