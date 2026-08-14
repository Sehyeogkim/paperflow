"""Deterministic graph audit used after every interview turn and before confirmation."""
from __future__ import annotations

from ..schemas.claim import ClaimGraph, GNode
from .models import GraphAuditFinding, GraphAuditReport

_TACIT_KINDS = {"threshold", "pitfall", "decision"}


def _cycles(graph: ClaimGraph, relations: set[str]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.rel in relations:
            adjacency.setdefault(edge.src, []).append(edge.dst)
    color: dict[str, int] = {}
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node_id: str) -> None:
        color[node_id] = 1
        stack.append(node_id)
        for nxt in adjacency.get(node_id, []):
            if color.get(nxt, 0) == 0:
                visit(nxt)
            elif color.get(nxt) == 1:
                start = stack.index(nxt)
                cycle = stack[start:] + [nxt]
                if cycle not in found:
                    found.append(cycle)
        stack.pop()
        color[node_id] = 2

    for node_id in sorted(adjacency):
        if color.get(node_id, 0) == 0:
            visit(node_id)
    return found


def _node_has_real_origin(node: GNode | None) -> bool:
    if node is None:
        return False
    provenance = str(node.provenance or "").strip()
    if provenance and provenance not in {"[DATA_NEEDED]", "[ASK_AUTHOR]"}:
        return True
    return any(
        ref.source_type in {"file", "author", "external"}
        and ref.verification_status in {"verified", "author_attested"}
        for ref in node.provenance_refs
    )


def _method_has_origin(graph: ClaimGraph, method_id: str, seen: set[str] | None = None) -> bool:
    seen = set(seen or ())
    if method_id in seen:
        return False
    seen.add(method_id)
    method = graph.node(method_id)
    if _node_has_real_origin(method):
        return True
    for edge in graph.edges_out(method_id):
        if edge.grounding_status != "grounded":
            continue
        target = graph.node(edge.dst)
        if edge.rel == "uses" and target and target.kind == "data" and _node_has_real_origin(target):
            return True
        if edge.rel == "produces" and target and target.kind == "data" and _node_has_real_origin(target):
            return True
        if edge.rel == "part_of" and target and target.kind == "method" \
                and _method_has_origin(graph, target.id, seen):
            return True
    return False


def _evidence_has_origin(graph: ClaimGraph, evidence_id: str,
                         seen: set[str] | None = None) -> bool:
    seen = set(seen or ())
    if evidence_id in seen:
        return False
    seen.add(evidence_id)
    node = graph.node(evidence_id)
    if _node_has_real_origin(node):
        return True
    for edge in graph.edges:
        if edge.grounding_status != "grounded":
            continue
        if edge.dst == evidence_id and edge.rel == "produces":
            method = graph.node(edge.src)
            if method and method.kind == "method" and _method_has_origin(graph, method.id):
                return True
        if edge.src == evidence_id and edge.rel == "derived_from":
            origin = graph.node(edge.dst)
            if origin and origin.kind in {"data", "evidence"}:
                if origin.kind == "data" and _node_has_real_origin(origin):
                    return True
                if origin.kind == "evidence" and _evidence_has_origin(graph, origin.id, seen):
                    return True
    return False


def _claim_has_evidence(graph: ClaimGraph, claim_id: str, seen: set[str] | None = None) -> bool:
    seen = set(seen or ())
    if claim_id in seen:
        return False
    seen.add(claim_id)
    for edge in graph.edges_into(claim_id):
        if edge.rel != "supports" or edge.grounding_status != "grounded":
            continue
        src = graph.node(edge.src)
        if src is None:
            continue
        if src.kind == "evidence" and _evidence_has_origin(graph, src.id):
            return True
        if src.kind == "claim" and _claim_has_evidence(graph, src.id, seen):
            return True
    return False


def _has_author_provenance(node: GNode) -> bool:
    return node.provenance == "user_statement" or any(
        ref.source_type == "author" for ref in node.provenance_refs
    )


def audit_graph(graph: ClaimGraph) -> GraphAuditReport:
    """Return reproducible findings without asking an LLM to judge graph validity."""
    findings: list[GraphAuditFinding] = []
    tacit = [n for n in graph.nodes if n.kind in _TACIT_KINDS]

    for node in tacit:
        if node.knowledge_status in {"missing", "unknown", "unverified"}:
            severity = "blocking" if node.risk == "high" else "warning"
            findings.append(GraphAuditFinding(
                code="tacit.unresolved",
                message=f"Tacit knowledge slot {node.id} is {node.knowledge_status}",
                severity=severity, node_ids=[node.id],
            ))
        elif node.knowledge_status == "partial":
            findings.append(GraphAuditFinding(
                code="tacit.partial", message=f"Tacit knowledge slot {node.id} is only partial",
                severity="warning", node_ids=[node.id],
            ))
        elif node.knowledge_status == "author_attested" and not _has_author_provenance(node):
            findings.append(GraphAuditFinding(
                code="provenance.author_missing",
                message=f"Author-attested node {node.id} lacks author provenance",
                severity="blocking", node_ids=[node.id],
            ))
        elif node.knowledge_status == "verified" and not any(
            ref.verification_status == "verified" for ref in node.provenance_refs
        ):
            findings.append(GraphAuditFinding(
                code="provenance.verification_missing",
                message=f"Verified node {node.id} lacks a verified provenance reference",
                severity="blocking", node_ids=[node.id],
            ))

    main_claims = [n for n in graph.claims if not n.parent_id]
    for claim in main_claims:
        if not _claim_has_evidence(graph, claim.id):
            findings.append(GraphAuditFinding(
                code="claim.no_grounded_evidence",
                message=f"Main claim {claim.id} has no grounded path to evidence and its origin",
                severity="blocking", node_ids=[claim.id],
            ))

    for cycle in _cycles(graph, {"feeds"}):
        findings.append(GraphAuditFinding(
            code="pipeline.cycle", message="Method feed graph contains a cycle: " + " -> ".join(cycle),
            severity="blocking", node_ids=cycle,
        ))
    for cycle in _cycles(graph, {"part_of"}):
        findings.append(GraphAuditFinding(
            code="hierarchy.cycle", message="part_of hierarchy contains a cycle: " + " -> ".join(cycle),
            severity="blocking", node_ids=cycle,
        ))

    contradictions = [e for e in graph.edges if e.rel == "contradicts"]
    for edge in contradictions:
        findings.append(GraphAuditFinding(
            code="claim.contradiction_present",
            message=f"Contradiction {edge.id} requires an explicit author/reviewer resolution",
            severity="warning", node_ids=[edge.src, edge.dst], edge_ids=[edge.id],
        ))

    blocking = sum(f.severity == "blocking" for f in findings)
    return GraphAuditReport(
        graph_revision=graph.revision,
        ok=blocking == 0,
        findings=findings,
        metrics={
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "main_claims": len(main_claims),
            "tacit_slots": len(tacit),
            "unresolved_tacit": sum(n.knowledge_status in {"missing", "unknown", "unverified", "partial"}
                                    for n in tacit),
            "blocking_findings": blocking,
        },
    )
