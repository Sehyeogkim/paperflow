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


def load_pack(study_type: str = "computational_biomechanics") -> RequirementPack:
    data = yaml.safe_load((_PACKS / f"{study_type}.yaml").read_text())
    return RequirementPack.model_validate(data)


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
