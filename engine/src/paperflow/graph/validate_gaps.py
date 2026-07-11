"""Deterministic load-bearing graph-gap validation (TWO_STAGE_QUESTIONS §7).

Identifies only defects that prevent defensible writing — missing claim evidence, missing
comparison basis for superiority claims, untraceable numeric evidence, missing method/result
links, and integrity violations. Non-critical issues (missing qualifier, minor integrity) are
returned as non_blocking_warnings and do NOT trigger Stage 2.
"""
from __future__ import annotations

import re

from ..schemas.claim import ClaimGraph, GNode
from ..schemas.graph_gap import GraphGapReport, LoadBearingGap

# claim wordings that assert a comparison and therefore need a comparison basis
_COMPARATIVE = [
    "지배", "우세", "더 중요", "가장", "더 적합", "더 높", "예측", "개선", "능가", "보다",
    "dominate", "dominant", "superior", "better", "more important", "highest", "higher",
    "most", "predict", "outperform", "improve", "exceed", "greater than", " vs",
]
# markers that an evidence text actually carries a comparison
_COMPARISON_MARKER = [
    "vs", "versus", "than", "compared", "comparison", "대비", "보다", "baseline",
    "control", "relative to", ">", "<", "ranking", "순위", "기존",
]
# precise numeric pattern (a real measured value, not a small count)
_NUMERIC = re.compile(r"\d+\.\d+|\d{2,}\s*%|p\s*[<=]\s*0?\.\d+")


def _main_claims(graph: ClaimGraph) -> list[GNode]:
    claims = graph.claims
    return [c for c in claims if not c.parent_id] or claims


def _supporting_evidence(graph: ClaimGraph, claim_id: str) -> list[GNode]:
    out = []
    for e in graph.edges_into(claim_id):
        if e.rel == "supports":
            n = graph.node(e.src)
            if n and n.kind == "evidence":
                out.append(n)
    return out


def _has_provenance(graph: ClaimGraph, ev: GNode) -> bool:
    """Evidence is traceable if it has explicit provenance, a derived_from data edge, a
    producing method, or an author-answer reference."""
    prov = ev.provenance
    if prov and "[DATA_NEEDED]" not in prov and prov not in ("user_statement",):
        return True
    if prov and prov.startswith(("author_answer", "REQ_", "LOGIC_")):
        return True
    for e in graph.edges_out(ev.id):
        d = graph.node(e.dst)
        if e.rel == "derived_from" and d and d.kind == "data":
            return True
    for e in graph.edges_into(ev.id):
        m = graph.node(e.src)
        if e.rel == "produces" and m and m.kind == "method":
            return True
    return False


def validate(graph: ClaimGraph) -> GraphGapReport:
    rep = GraphGapReport()
    if graph is None:
        return rep

    for c in _main_claims(graph):
        ev = _supporting_evidence(graph, c.id)
        # (1) claim with no supporting evidence — load-bearing
        if not ev:
            rep.load_bearing_gaps.append(LoadBearingGap(
                id=f"GAP_{c.id}_EVIDENCE", type="missing_evidence_to_claim", severity="high",
                claim_ids=[c.id], description=f"Claim '{c.text[:60]}' has no supporting evidence.",
                information_needed="The result metric/value that supports this claim.",
                can_degrade_to_qualifier=False))
            continue  # no point checking comparator/trace if there is no evidence at all

        # (2) comparative claim with no comparison basis — load-bearing
        low = c.text.lower()
        if any(k in c.text or k in low for k in _COMPARATIVE):
            has_qual = any(e.rel in ("qualifies", "contradicts") for e in graph.edges_into(c.id))
            ev_has_cmp = any(any(m in (n.text.lower()) for m in _COMPARISON_MARKER) for n in ev)
            if not (has_qual or ev_has_cmp):
                rep.load_bearing_gaps.append(LoadBearingGap(
                    id=f"GAP_{c.id}_COMPARATOR", type="missing_comparator", severity="high",
                    claim_ids=[c.id],
                    description=f"Comparative claim '{c.text[:60]}' has no explicit comparison basis.",
                    information_needed="The metric and comparator establishing the comparison.",
                    can_degrade_to_qualifier=True))

        # (3) evidence supporting a main claim but untraceable — load-bearing
        for n in ev:
            if _NUMERIC.search(n.text) and not _has_provenance(graph, n):
                rep.load_bearing_gaps.append(LoadBearingGap(
                    id=f"GAP_{n.id}_TRACE", type="untraceable_evidence", severity="high",
                    claim_ids=[c.id], related_node_ids=[n.id],
                    description=f"Evidence '{n.text[:60]}' states a value with no traceable source.",
                    information_needed="Which data file/column or answer this value comes from.",
                    can_degrade_to_qualifier=False))

        # (4) qualifier check — NON-blocking warning (does not trigger Stage 2)
        has_qual = any(e.rel == "qualifies" for e in graph.edges_into(c.id))
        if not has_qual:
            rep.non_blocking_warnings.append(
                f"{c.id}: claim has no scope/limitation qualifier")

    # (5) integrity — dangling edges (claim_graph.validate usually drops these) -> warnings
    ids = {n.id for n in graph.nodes}
    for e in graph.edges:
        if e.src not in ids or e.dst not in ids:
            rep.non_blocking_warnings.append(f"dangling edge {e.src}->{e.dst}")

    rep.ready_for_finalization = not rep.load_bearing_gaps
    return rep
