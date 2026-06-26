"""Stage 11: turn high-value missing/partial requirements into grounded questions."""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.overall_schema import OverallSchema, RequirementKey
from ..schemas.project_state import ProjectState
from ..schemas.requirement_status import GroundedQuestion, RequirementStatus
from ..util import prompt

_ASKABLE_LEVELS = {"mandatory", "strongly_expected"}
_ASKABLE_STATUS = {"missing", "partial"}
_RISK = {"mandatory": "high", "strongly_expected": "high", "common": "medium",
         "optional": "low", "unsupported": "low"}
_LEVEL_PRIORITY = {"mandatory": 3.0, "strongly_expected": 2.0, "common": 1.0}


def _answered(ps: ProjectState) -> set[str]:
    return {k for k, v in (ps.answers or {}).items() if str(v).strip()}


def select_gaps(schema: OverallSchema, statuses: list[RequirementStatus],
                ps: ProjectState) -> list[tuple[RequirementKey, RequirementStatus]]:
    by_key = {r.key: r for r in schema.requirements}
    status_by = {s.key: s for s in statuses}
    answered = _answered(ps)
    gaps: list[tuple[RequirementKey, RequirementStatus]] = []
    for key, req in by_key.items():
        st = status_by.get(key)
        if st is None or st.status not in _ASKABLE_STATUS:
            continue
        if req.requirement_level not in _ASKABLE_LEVELS:
            continue
        if key in answered:
            continue
        gaps.append((req, st))
    # most-expected, most-prevalent first
    gaps.sort(key=lambda rs: (_LEVEL_PRIORITY.get(rs[0].requirement_level, 0), rs[0].prevalence),
              reverse=True)
    return gaps


def generate(schema: OverallSchema, statuses: list[RequirementStatus],
             ps: ProjectState) -> list[GroundedQuestion]:
    """Generate grounded questions for askable gaps. Returns [] if there are no gaps."""
    gaps = select_gaps(schema, statuses, ps)
    if not gaps:
        return []
    ask = [{
        "id": req.key, "category": req.category, "requirement_level": req.requirement_level,
        "applicability_required_when": req.applicability.required_when,
        "schema_reason": req.reason, "status": st.status, "not_found_reason": st.reason,
        "observed_in": req.observed_in, "applicable_papers": req.applicable_papers,
        "sources": req.evidence_sources,
    } for req, st in gaps]
    try:
        raw = client.call_json("reasoning", prompt("generate_grounded_questions"),
                               "## REQUIREMENT GAPS TO ASK\n" + json.dumps(ask, ensure_ascii=False),
                               step="lit.questions", max_tokens=4500)
    except Exception:
        raw = {"questions": []}
    gen_by_id = {str(q.get("id")): q for q in (raw.get("questions") or []) if q.get("id")}

    out: list[GroundedQuestion] = []
    for req, st in gaps:
        g = gen_by_id.get(req.key, {})
        question = str(g.get("question", "")).strip()
        if not question:   # LLM dropped it (e.g. judged not worth asking) — skip
            continue
        out.append(GroundedQuestion(
            id=req.key, question=question,
            why_asked=str(g.get("why_asked", req.reason)).strip(),
            expected_answer=str(g.get("expected_answer", "")).strip(),
            requirement_level=req.requirement_level,
            reviewer_risk=_RISK.get(req.requirement_level, "medium"),
            sources=req.evidence_sources,
            applicability_reason=str(g.get("applicability_reason", "")).strip(),
            not_found_reason=str(g.get("not_found_reason", st.reason)).strip(),
            allow_unknown=True,
            priority=_LEVEL_PRIORITY.get(req.requirement_level, 1.0) + req.prevalence,
        ))
    out.sort(key=lambda q: q.priority, reverse=True)
    return out
