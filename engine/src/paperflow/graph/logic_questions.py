"""Stage-2 logic questions from the load-bearing graph-gap report (TWO_STAGE_QUESTIONS §8).

These are NOT another reporting checklist — each asks for the specific missing relationship
that blocks a claim, references the gap + claim ids, and declares what to do if the user
answers "모름" (downgrade / qualify / remove the claim).
"""
from __future__ import annotations

from ..schemas.claim import ClaimGraph
from ..schemas.graph_gap import GraphGapReport, LoadBearingGap
from ..schemas.question import Question

MAX_STAGE2 = 5

# gap type -> (question template, expected answer, fallback-if-unknown policy)
_TEMPLATES: dict[str, tuple[str, str, str]] = {
    "missing_evidence_to_claim": (
        "\"{claim}\" 주장을 직접 지지하는 결과값(지표·수치)은 무엇인가요?",
        "지표, 값/순위, 출처 파일 또는 표", "downgrade_claim"),
    "missing_comparator": (
        "\"{claim}\" 비교 주장의 근거(무엇과 비교했고 어떤 지표로 우위인지)는 무엇인가요?",
        "비교 대상, 지표, 관측된 차이", "qualify_claim"),
    "untraceable_evidence": (
        "\"{claim}\"의 근거 수치는 어떤 데이터 파일/컬럼 또는 분석에서 나온 값인가요?",
        "파일·컬럼 또는 산출 절차", "downgrade_claim"),
    "missing_method_for_evidence": (
        "이 결과는 어떤 방법/분석 절차로 생성되었나요?",
        "분석 방법·입력·절차", "qualify_claim"),
}


def _claim_text(graph: ClaimGraph | None, gap: LoadBearingGap) -> str:
    if graph and gap.claim_ids:
        n = graph.node(gap.claim_ids[0])
        if n:
            return n.text
    return gap.description or "이 주장"


def generate(report: GraphGapReport, graph: ClaimGraph | None = None,
             max_questions: int = MAX_STAGE2) -> list[Question]:
    """Only high-value load-bearing gaps become questions, capped at max_questions."""
    gaps = sorted(report.load_bearing_gaps,
                  key=lambda g: 0 if g.severity == "high" else 1)
    out: list[Question] = []
    for gap in gaps[:max(0, max_questions)]:
        tmpl, expected, fallback = _TEMPLATES.get(
            gap.type, ("{claim}에 대해 보완 정보를 알려주세요.", "", "qualify_claim"))
        claim = _claim_text(graph, gap)
        short = (claim[:80] + "…") if len(claim) > 80 else claim
        out.append(Question(
            id=f"LOGIC_{gap.id}", gap_kind="claim_without_evidence",  # legacy enum (display only)
            stage="logic", question=tmpl.format(claim=short),
            example=expected, why_asked=gap.description,
            gap_id=gap.id, claim_ids=list(gap.claim_ids),
            sources=list(gap.related_node_ids),
            fallback_if_unknown=fallback, load_bearing=True, value=10.0))
    return out
