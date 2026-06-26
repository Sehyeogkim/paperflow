"""Deterministic Final Logic Graph construction (TWO_STAGE_QUESTIONS §9).

Applies Stage-2 logic answers to the preliminary graph:
  - a real answer adds a provenance-tagged author-answer Evidence node supporting the claim
  - an "모름 / unknown" answer NEVER fabricates evidence; it downgrades, qualifies, or removes
    the affected claim per the question's fallback policy
and rejects any numeric Evidence node that has no traceable source.
"""
from __future__ import annotations

from ..schemas.claim import ClaimGraph, GEdge, GNode
from ..schemas.question import Question
from .validate_gaps import _NUMERIC, _has_provenance

_UNKNOWN_TOKENS = (
    "모름", "나중에", "잘 모르", "확실하지 않", "unknown", "n/a", "na", "dont know",
    "don't know", "do not know", "not sure", "later",
)


def is_unknown(answer: str) -> bool:
    a = (answer or "").strip().lower()
    if not a:
        return True
    return any(tok in a for tok in _UNKNOWN_TOKENS)


def _drop_claim(graph: ClaimGraph, claim_id: str) -> None:
    graph.nodes = [n for n in graph.nodes if n.id != claim_id]
    graph.edges = [e for e in graph.edges if e.src != claim_id and e.dst != claim_id]


def _next_id(graph: ClaimGraph, prefix: str) -> str:
    i = 1
    existing = {n.id for n in graph.nodes}
    while f"{prefix}{i}" in existing:
        i += 1
    return f"{prefix}{i}"


def apply_logic_answers(graph: ClaimGraph, questions: list[Question],
                        answers: dict[str, str]) -> ClaimGraph:
    """Return a NEW graph with Stage-2 answers applied. Unknown answers downgrade/qualify/
    remove the claim (never fabricate); real answers attach a traceable author-answer evidence."""
    g = graph.model_copy(deep=True)
    for q in questions:
        ans = (answers or {}).get(q.id, "")
        claim_id = q.claim_ids[0] if q.claim_ids else ""
        claim = g.node(claim_id) if claim_id else None
        if is_unknown(ans):
            policy = q.fallback_if_unknown or "qualify_claim"
            if not claim:
                continue
            if policy == "remove_claim":
                _drop_claim(g, claim_id)
            elif policy == "downgrade_claim":
                claim.role = "downgraded"
                claim.text = f"{claim.text} (직접 근거 미확보로 약화된 주장 — 외부 검증 필요)"
            else:  # qualify_claim
                claim.role = claim.role or "qualified"
                wid = _next_id(g, "W")
                g.nodes.append(GNode(id=wid, kind="warrant",
                                     text="적용 범위·조건이 제한되며 정식 비교/검증은 향후 과제",
                                     role="qualifier"))
                g.edges.append(GEdge(id=_next_id(g, "L"), src=wid, dst=claim_id,
                                     rel="qualifies", rationale="unknown logic answer → qualified"))
        elif ans.strip() and claim:
            # real author answer -> traceable evidence node supporting the claim
            eid = _next_id(g, "E")
            g.nodes.append(GNode(id=eid, kind="evidence", text=ans.strip()[:300],
                                 provenance=f"author_answer:{q.id}"))
            g.edges.append(GEdge(id=_next_id(g, "L"), src=eid, dst=claim_id, rel="supports",
                                 rationale="author-provided in Stage-2 logic answer",
                                 grounding_status="grounded"))
    return g


def reject_untraceable_numeric_evidence(graph: ClaimGraph) -> ClaimGraph:
    """Remove Evidence nodes that assert a precise numeric value with no traceable source
    (no provenance/data/method/author-answer). Returns a NEW graph."""
    g = graph.model_copy(deep=True)
    drop = {n.id for n in g.nodes
            if n.kind == "evidence" and _NUMERIC.search(n.text) and not _has_provenance(g, n)}
    if drop:
        g.nodes = [n for n in g.nodes if n.id not in drop]
        g.edges = [e for e in g.edges if e.src not in drop and e.dst not in drop]
    return g


def finalize(graph: ClaimGraph, questions: list[Question],
             answers: dict[str, str]) -> ClaimGraph:
    """Full finalization: apply logic answers, then reject untraceable numeric evidence."""
    g = apply_logic_answers(graph, questions, answers)
    return reject_untraceable_numeric_evidence(g)
