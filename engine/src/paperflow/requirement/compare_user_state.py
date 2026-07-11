"""Stage 10+11 merged: in ONE gpt-5 (low effort) call, judge per-requirement coverage AND
write the grounded question for the high-value gaps — avoiding a second model round-trip."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

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
_BATCH = 13          # requirements per call — judging is independent per requirement, so batch
_MAX_WORKERS = 6     # and run the batches concurrently (wall-clock = slowest batch)


def _answered(ps: ProjectState) -> set[str]:
    return {k for k, v in (ps.answers or {}).items() if str(v).strip()}


def _judge_batch(reqs: list[RequirementKey], context: str, by_key: dict[str, RequirementKey],
                 answered: set[str]) -> tuple[list[RequirementStatus], list[GroundedQuestion]]:
    """One LLM call over a SUBSET of requirements. `context` = inputs_block + prior answers."""
    keys = [{"key": r.key, "category": r.category, "requirement_level": r.requirement_level,
             "required_when": r.applicability.required_when, "prevalence": r.prevalence,
             "sources": r.evidence_sources} for r in reqs]
    user = f"{context}\n\n## REQUIREMENTS\n{json.dumps(keys, ensure_ascii=False)}"
    try:
        raw = client.call_json("reasoning", prompt("compare_and_question"), user,
                               step="lit.compare_question", max_tokens=4000, effort="low")
    except Exception:
        return [], []
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
    return statuses, questions


def compare_and_question(schema: OverallSchema, ps: ProjectState
                         ) -> tuple[list[RequirementStatus], list[GroundedQuestion]]:
    """Judge coverage + write questions, BATCHED IN PARALLEL. Each requirement's verdict is
    independent, so the ~50 requirements are split into batches judged concurrently — wall-clock
    is the slowest batch, not one giant call. Questions only for unanswered missing/partial
    mandatory|strongly_expected items."""
    reqs = schema.requirements
    if not reqs:
        return [], []
    by_key: dict[str, RequirementKey] = {r.key: r for r in reqs}
    answered = _answered(ps)
    context = (f"{inputs_block(ps)}\n\n## PRIOR ANSWERS\n"
               f"{json.dumps(ps.answers or {}, ensure_ascii=False)}")
    batches = [reqs[i:i + _BATCH] for i in range(0, len(reqs), _BATCH)]

    statuses: list[RequirementStatus] = []
    questions: list[GroundedQuestion] = []
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(batches))) as ex:
        for st, qs in ex.map(lambda b: _judge_batch(b, context, by_key, answered), batches):
            statuses.extend(st)
            questions.extend(qs)
    questions.sort(key=lambda q: q.priority, reverse=True)
    return statuses, questions


def compare(schema: OverallSchema, ps: ProjectState) -> list[RequirementStatus]:
    """Backward-compatible: statuses only."""
    return compare_and_question(schema, ps)[0]
