"""Generate a RequirementPack from a reporting standard's text (reasoning tier).

This proves the mechanism "codified reporting standard -> auto-generated requirement
rubric pack": instead of hand-authoring each pack YAML, feed the text/checklist of a
standard (ASME V&V 40, FDA guidance, CONSORT, ARRIVE, ...) to an LLM and have it
distill the reusable rubric, validated against the `RequirementPack` schema.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..llm import client
from ..schemas.requirement import RequirementPack
from ..util import prompt


def generate_pack(study_type: str, standard_text: str) -> RequirementPack:
    """Distill a reporting standard's text into a validated `RequirementPack`.

    Builds the user message from `study_type` plus the standard text, calls the
    reasoning tier, and validates the raw dict. Tolerant of a model that omits
    `study_type` (the given label is filled in).
    """
    user = (
        f"study_type: {study_type}\n\n"
        "## REPORTING STANDARD / CHECKLIST TEXT\n"
        f"{standard_text}"
    )
    raw = client.call_json(
        "reasoning", prompt("pack_from_standard"), user, step="pack_gen"
    )
    raw.setdefault("study_type", study_type)
    if not raw.get("study_type"):
        raw["study_type"] = study_type
    return RequirementPack.model_validate(raw)


def write_pack(pack: RequirementPack, path: Path) -> None:
    """Dump a `RequirementPack` to YAML in the same shape as the hand-written packs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            pack.model_dump(), allow_unicode=True, sort_keys=False
        )
    )
