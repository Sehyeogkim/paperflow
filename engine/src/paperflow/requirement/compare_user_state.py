"""Stage 10: compare the overall_schema against the user's materials → per-key status."""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.overall_schema import OverallSchema
from ..schemas.project_state import ProjectState
from ..schemas.requirement_status import RequirementStatus
from ..util import inputs_block, prompt

_VALID = {"present", "partial", "missing", "not_applicable", "uncertain"}


def compare(schema: OverallSchema, ps: ProjectState) -> list[RequirementStatus]:
    """Judge each requirement against journal info / core message / outline / research state /
    evidence inventory / answers. Returns [] on error (caller treats as uncertain coverage)."""
    if not schema.requirements:
        return []
    keys = [{"key": r.key, "category": r.category, "aliases": r.aliases,
             "requirement_level": r.requirement_level,
             "applicability": r.applicability.model_dump()} for r in schema.requirements]
    answers = ps.answers or {}
    user = (f"{inputs_block(ps)}\n\n## PRIOR ANSWERS\n{json.dumps(answers, ensure_ascii=False)}"
            f"\n\n## REQUIREMENTS TO CHECK\n{json.dumps(keys, ensure_ascii=False)}")
    # coverage judgement is subtle ("a related data file exists" is NOT "the method is
    # described") and must be consistent run-to-run -> use the full reasoning model, not mini.
    try:
        raw = client.call_json("reasoning", prompt("compare_requirement_to_user"), user,
                               step="lit.compare", max_tokens=4000)
    except Exception:
        return []
    out: list[RequirementStatus] = []
    for s in (raw.get("statuses") or []):
        if not isinstance(s, dict) or not s.get("key"):
            continue
        status = str(s.get("status", "uncertain"))
        if status not in _VALID:
            status = "uncertain"
        out.append(RequirementStatus(
            key=str(s["key"]), status=status,
            found_evidence=[str(e) for e in (s.get("found_evidence") or [])],
            reason=str(s.get("reason", "")),
            source_requirements=[f"overall_schema:{s['key']}"],
        ))
    return out
