"""Local subgraph extraction — give the writer/validator ONLY the grounding chain of the
claims a paragraph realizes, not the whole graph. This is what turns the claim graph from
a typed outline into the engine that actually controls writing.

slice_for_claim() walks backward (along grounding edges) from the focus claims: the
evidence that supports them, the methods/data that produced that evidence, the warrants/
sources that license it, and the artifacts that visualize it.
"""
from __future__ import annotations

from ..schemas.claim import ClaimGraph, GEdge, GNode

_KIND_LABEL = {"claim": "CLAIM", "evidence": "SUPPORTING EVIDENCE", "method": "METHOD TRACE",
               "data": "DATA", "warrant": "WARRANT", "source": "REFERENCES",
               "artifact": "ARTIFACTS (figure/table)"}
_ORDER = ["claim", "evidence", "method", "data", "warrant", "source", "artifact"]


def slice_for_claim(graph: ClaimGraph, claim_ids: list[str], depth: int = 3,
                    max_nodes: int = 40) -> dict:
    """The focus claims' local grounding subgraph. Grounding runs in mixed directions
    (evidence->data via derived_from is outgoing; method->evidence is incoming), so we take
    the depth-limited UNDIRECTED neighborhood, capped to avoid pulling the whole graph."""
    keep = set(i for i in claim_ids if graph.node(i))
    frontier = set(keep)
    for _ in range(max(1, depth)):
        nxt: set = set()
        for e in graph.edges:
            if e.src in frontier and e.dst not in keep and len(keep) < max_nodes:
                keep.add(e.dst); nxt.add(e.dst)
            if e.dst in frontier and e.src not in keep and len(keep) < max_nodes:
                keep.add(e.src); nxt.add(e.src)
        if not nxt:
            break
        frontier = nxt
    edges = [e for e in graph.edges if e.src in keep and e.dst in keep]
    nodes = [n for n in graph.nodes if n.id in keep]
    return {"focus_claims": list(claim_ids), "nodes": nodes, "edges": edges}


def _node_line(n: GNode) -> str:
    extra = ""
    if n.kind == "method" and n.subtype:
        extra = f" ({n.subtype})"
    if n.kind == "data" and n.provenance:
        extra = f"  [{n.provenance}]"
    if n.kind == "artifact" and n.represented_as:
        extra = f" ({n.represented_as})"
    if n.kind == "source" and n.provenance:
        extra = f"  [cite:{n.provenance}]"
    return f"  - {n.id}{extra}: {n.text}"


def context_text(graph: ClaimGraph, claim_ids: list[str], extra_node_ids: list[str] | None = None,
                 depth: int = 3) -> str:
    """Render the focus claims' local subgraph as a compact context block for the writer."""
    sl = slice_for_claim(graph, claim_ids, depth=depth)
    nodes = {n.id: n for n in sl["nodes"]}
    for nid in extra_node_ids or []:  # pull in explicitly-requested context nodes too
        n = graph.node(nid)
        if n and nid not in nodes:
            nodes[nid] = n
    by_kind: dict[str, list[GNode]] = {}
    for n in nodes.values():
        by_kind.setdefault(n.kind, []).append(n)

    lines: list[str] = []
    for kind in _ORDER:
        group = by_kind.get(kind)
        if not group:
            continue
        lines.append(f"## {_KIND_LABEL[kind]}")
        lines += [_node_line(n) for n in group]
    rationales = [e for e in sl["edges"] if e.rationale and e.rel in ("supports", "justifies", "qualifies", "contradicts")]
    if rationales:
        lines.append("## EDGE RATIONALES (the logic this paragraph must respect)")
        for e in rationales:
            lines.append(f"  - {e.src} {e.rel} {e.dst}: {e.rationale}  [{e.grounding_status}]")
    return "\n".join(lines)
