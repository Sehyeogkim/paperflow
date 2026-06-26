"""Static-pack fallback: used ONLY when literature discovery fails (no OpenAlex results /
not enough papers / pipeline error). Wraps the legacy `detect.detect` so the same downstream
shapes (grounded questions, overall schema, statuses, RequirementReport) are produced."""
from __future__ import annotations

from . import detect
from ..schemas.overall_schema import Applicability, OverallSchema, RequirementKey
from ..schemas.project_state import ProjectState
from ..schemas.requirement import RequirementReport
from ..schemas.requirement_status import GroundedQuestion, RequirementStatus

_RISK_TO_LEVEL = {"high": "strongly_expected", "medium": "common", "low": "optional"}


def run(ps: ProjectState, reason: str = "") -> dict:
    """Return the same result shape as the literature pipeline, sourced from the static pack."""
    pack = detect.load_pack()
    report: RequirementReport = detect.detect(ps, pack)

    # overall schema view (so the report/HTML can render a fallback schema)
    reqs: list[RequirementKey] = []
    for f in report.present:
        reqs.append(RequirementKey(key=f, category="reported_items",
                                   requirement_level="strongly_expected", reason="static pack"))
    for m in report.missing:
        reqs.append(RequirementKey(
            key=m.field, category="reported_items",
            requirement_level=_RISK_TO_LEVEL.get(m.reviewer_risk, "common"),
            reason=m.why_it_matters,
            applicability=Applicability(required_when=[]),
        ))
    schema = OverallSchema(project_id="", study_archetype=pack.study_type,
                           source_papers=0, requirement_source="static_fallback",
                           requirements=reqs)

    statuses = [RequirementStatus(key=f, status="present",
                                  source_requirements=[f"static_pack:{f}"]) for f in report.present]
    statuses += [RequirementStatus(key=m.field, status="missing", reason=m.why_it_matters,
                                   source_requirements=[f"static_pack:{m.field}"])
                 for m in report.missing]

    questions = [GroundedQuestion(
        id=m.field, question=m.question, why_asked=m.why_it_matters,
        expected_answer=m.example, requirement_level=_RISK_TO_LEVEL.get(m.reviewer_risk, "common"),
        reviewer_risk=m.reviewer_risk, sources=["static_pack"],
        applicability_reason="static requirement pack (literature search unavailable)",
        not_found_reason=m.why_it_matters, allow_unknown=True, priority=m.priority,
    ) for m in report.missing if m.question]

    return {
        "requirement_source": "static_fallback",
        "fallback_reason": reason,
        "study_archetype": pack.study_type,
        "papers": [],
        "overall_schema": schema,
        "statuses": statuses,
        "questions": questions,
        "report": report,
        "classification": report.classification.value,
        "present": report.present,
        "notes": report.notes,
    }
