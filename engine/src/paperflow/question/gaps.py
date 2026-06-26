"""Detect gaps in the preliminary logic graph (+ reconstruction unknowns).

A gap is a place where a claim cannot yet be written defensibly: a claim with no evidence,
evidence with no provenance, a main claim with no warrant/qualifier, an undescribed data
file, or a research-state field the reconstruction couldn't infer. Pure/deterministic so it
is fully testable offline and re-runnable after every answer.
"""
from __future__ import annotations

from ..schemas.claim import ClaimGraph
from ..schemas.evidence_inventory import EvidenceInventory
from ..schemas.question import LOAD_BEARING, GraphGap
from ..schemas.research_state import ResearchState


def _main_claims(graph: ClaimGraph) -> list:
    claims = graph.claims
    mains = [c for c in claims if not c.parent_id]
    return mains or claims


def detect(graph: ClaimGraph | None,
           research_state: ResearchState | None = None,
           evidence_inventory: EvidenceInventory | None = None) -> list[GraphGap]:
    """Return all gaps, in a stable order (graph gaps first, then data/research unknowns)."""
    gaps: list[GraphGap] = []

    if graph is not None and graph.claims:
        for c in _main_claims(graph):
            ev = [e for e in graph.edges_into(c.id)
                  if e.rel == "supports" and (n := graph.node(e.src)) and n.kind == "evidence"]
            if not ev:
                gaps.append(GraphGap(kind="claim_without_evidence", target_id=c.id,
                                     target_text=c.text, load_bearing=True))
            warr = [e for e in graph.edges_into(c.id)
                    if e.rel in ("justifies", "qualifies")
                    and (n := graph.node(e.src)) and n.kind in ("warrant", "source")]
            if not warr:
                gaps.append(GraphGap(kind="claim_without_warrant", target_id=c.id,
                                     target_text=c.text))
            qual = [e for e in graph.edges_into(c.id) if e.rel == "qualifies"]
            if not qual:
                gaps.append(GraphGap(kind="claim_without_qualifier", target_id=c.id,
                                     target_text=c.text))
        # evidence nodes lacking a producing method OR source data
        for n in graph.nodes:
            if n.kind != "evidence":
                continue
            has_method = any(e.rel == "produces" and (m := graph.node(e.src)) and m.kind == "method"
                             for e in graph.edges_into(n.id))
            has_data = any(e.rel == "derived_from" and (d := graph.node(e.dst)) and d.kind == "data"
                           for e in graph.edges_out(n.id))
            if not (has_method or has_data):
                gaps.append(GraphGap(kind="evidence_without_provenance", target_id=n.id,
                                     target_text=n.text, load_bearing=True))
    else:
        # no graph / no claims yet — the primary claim itself is the first thing to settle
        gaps.append(GraphGap(kind="missing_primary_claim",
                             target_text=(research_state.primary_message if research_state else ""),
                             load_bearing=True))

    if evidence_inventory is not None:
        for a in evidence_inventory.assets:
            if a.kind in ("csv", "xlsx", "xls", "dat") and not a.user_description.strip():
                gaps.append(GraphGap(kind="data_meaning_unknown", target_id=a.path,
                                     target_text=a.path,
                                     detail=f"role guessed as '{a.inferred_role}'"))

    if research_state is not None:
        for field in research_state.unknowns:
            gaps.append(GraphGap(kind="research_unknown", target_id=field, target_text=field))

    for g in gaps:  # normalize the load-bearing flag from the canonical set
        g.load_bearing = g.kind in LOAD_BEARING
    return gaps
