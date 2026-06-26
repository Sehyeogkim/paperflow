"""Turn gaps into ranked questions.

question_value (workflow_design §5) =
    impact_on_primary_claim + impact_on_method_correctness + impact_on_result_interpretation
    + reviewer_risk - inferability_from_existing_files - user_answering_cost

Each gap kind carries a fixed component profile; the score is deterministic so ranking is
stable and testable. Question text is templated from the gap's subject (LLM phrasing is a
later refinement — not needed to drive the loop).
"""
from __future__ import annotations

from ..schemas.question import GraphGap, Question

# kind -> (primary, method, interpretation, reviewer_risk, inferability, answering_cost)
_PROFILE: dict[str, tuple[float, float, float, float, float, float]] = {
    "missing_primary_claim":       (3.0, 0.0, 1.0, 3.0, 0.0, 1.0),
    "claim_without_evidence":      (3.0, 1.0, 2.0, 3.0, 0.5, 1.0),
    "evidence_without_provenance": (1.0, 3.0, 1.0, 2.0, 0.5, 1.0),
    "claim_without_warrant":       (1.0, 1.0, 1.0, 2.0, 1.0, 1.0),
    "claim_without_qualifier":     (1.0, 0.0, 2.0, 1.0, 0.5, 0.5),
    "data_meaning_unknown":        (1.0, 2.0, 1.0, 1.0, 0.0, 0.5),
    "research_unknown":            (1.0, 1.0, 1.0, 1.0, 0.0, 0.5),
}


def value(gap: GraphGap) -> float:
    p, m, i, r, inf, cost = _PROFILE.get(gap.kind, (1, 1, 1, 1, 1, 1))
    return p + m + i + r - inf - cost


def _phrase(gap: GraphGap) -> tuple[str, str]:
    """(question, example) templated from the gap subject."""
    t = (gap.target_text or "this item").strip()
    short = (t[:80] + "…") if len(t) > 80 else t
    return {
        "missing_primary_claim": (
            "이 논문의 primary finding(가장 핵심적인 주장)은 무엇인가요?",
            "예: 재료물성이 혈류역학·형태보다 파열 위험을 지배한다"),
        "claim_without_evidence": (
            f"\"{short}\" 주장을 뒷받침하는 이번 연구의 결과(수치·그래프·관찰)는 무엇인가요?",
            "예: 그룹별 Sobol 분석에서 Material 그룹 ST=0.72로 최댓값"),
        "evidence_without_provenance": (
            f"\"{short}\" 결과는 어떤 방법/데이터로 생성되었나요? (분석 절차·입력 파일)",
            "예: 1000-sample 입력으로 GPR 대리모델 학습 후 Sobol 분석"),
        "claim_without_warrant": (
            f"\"{short}\" 주장을 정당화하는 과학적 근거나 선행연구가 있나요?",
            "예: 섬유막 응력이 파열의 직접 원인이라는 Loree et al. 1992"),
        "claim_without_qualifier": (
            f"\"{short}\" 주장의 적용 범위·조건·한계는 무엇인가요?",
            "예: 이상화 모델 기준이며 환자별 형상에는 일반화 제한"),
        "data_meaning_unknown": (
            f"업로드한 '{short}' 파일은 무엇이며 어떤 분석에서 나온 결과인가요?",
            "예: LAP 플라크의 그룹별 Sobol 민감도 결과"),
        "research_unknown": (
            f"연구 정보 '{short}'을(를) 알려주세요.",
            ""),
    }.get(gap.kind, (f"{short}에 대해 알려주세요.", ""))


def to_question(gap: GraphGap) -> Question:
    q, ex = _phrase(gap)
    qid = f"{gap.kind}:{gap.target_id or gap.target_text[:40]}"
    return Question(id=qid, gap_kind=gap.kind, target_id=gap.target_id,
                    question=q, example=ex, value=value(gap), load_bearing=gap.load_bearing)


def rank(gaps: list[GraphGap]) -> list[Question]:
    """All gaps as questions, highest value first (stable for ties by id)."""
    qs = [to_question(g) for g in gaps]
    qs.sort(key=lambda q: (-q.value, q.id))
    return qs
