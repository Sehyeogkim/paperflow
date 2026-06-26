"""Stage 10+11 merged: in ONE gpt-5 (low effort) call, judge per-requirement coverage AND
write the grounded question for the high-value gaps — avoiding a second model round-trip."""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.overall_schema import OverallSchema, RequirementKey
from ..schemas.project_state import ProjectState
from ..schemas.requirement_status import GroundedQuestion, RequirementStatus
from ..util import inputs_block, prompt

_VALID = {"present", "partial", "missing", "not_applicable", "uncertain"}
_ASKABLE_STATUS = {"missing", "partial"}
_ASKABLE_LEVELS = {"mandatory", "strongly_expected"}
_RISK = {"mandatory": "high", "strongly_expected": "high", "common": "medium",
         "optional": "low", "unsupported": "low"}
_LEVEL_PRIORITY = {"mandatory": 3.0, "strongly_expected": 2.0, "common": 1.0}


def _answered(ps: ProjectState) -> set[str]:
    return {k for k, v in (ps.answers or {}).items() if str(v).strip()}


def compare_and_question(schema: OverallSchema, ps: ProjectState
                         ) -> tuple[list[RequirementStatus], list[GroundedQuestion]]:
    """Single call: returns (statuses, grounded_questions). Questions are emitted only for
    missing/partial requirements at mandatory/strongly_expected level that aren't answered."""
    if not schema.requirements:
        return [], []
    by_key: dict[str, RequirementKey] = {r.key: r for r in schema.requirements}
    keys = [{"key": r.key, "category": r.category, "requirement_level": r.requirement_level,
             "required_when": r.applicability.required_when, "prevalence": r.prevalence,
             "sources": r.evidence_sources} for r in schema.requirements]
    answers = ps.answers or {}
    user = (f"{inputs_block(ps)}\n\n## PRIOR ANSWERS\n{json.dumps(answers, ensure_ascii=False)}"
            f"\n\n## REQUIREMENTS\n{json.dumps(keys, ensure_ascii=False)}")
    # gpt-5 (smart, consistent) at LOW reasoning effort: fast AND not over-generous like mini.
    try:
        raw = client.call_json("reasoning", prompt("compare_and_question"), user,
                               step="lit.compare_question", max_tokens=5000, effort="low")
    except Exception:
        return [], []

    answered = _answered(ps)
    statuses: list[RequirementStatus] = []
    questions: list[GroundedQuestion] = []
    for r in (raw.get("results") or []):
        if not isinstance(r, dict) or not r.get("key"):
            continue
        key = str(r["key"])
        status = str(r.get("status", "uncertain"))
        if status not in _VALID:
            status = "uncertain"
        statuses.append(RequirementStatus(
            key=key, status=status,
            found_evidence=[str(e) for e in (r.get("found_evidence") or [])],
            reason=str(r.get("reason", "")), source_requirements=[f"overall_schema:{key}"]))

        req = by_key.get(key)
        ask = bool(r.get("ask")) and status in _ASKABLE_STATUS and key not in answered
        if ask and req and req.requirement_level in _ASKABLE_LEVELS and str(r.get("question", "")).strip():
            questions.append(GroundedQuestion(
                id=key, question=str(r["question"]).strip(),
                why_asked=str(r.get("why_asked", req.reason)).strip(),
                expected_answer=str(r.get("expected_answer", "")).strip(),
                requirement_level=req.requirement_level,
                reviewer_risk=_RISK.get(req.requirement_level, "medium"),
                sources=req.evidence_sources, not_found_reason=str(r.get("reason", "")).strip(),
                allow_unknown=True,
                priority=_LEVEL_PRIORITY.get(req.requirement_level, 1.0) + req.prevalence))
    questions.sort(key=lambda q: q.priority, reverse=True)
    return statuses, questions


def compare(schema: OverallSchema, ps: ProjectState) -> list[RequirementStatus]:
    """Backward-compatible: statuses only."""
    return compare_and_question(schema, ps)[0]
