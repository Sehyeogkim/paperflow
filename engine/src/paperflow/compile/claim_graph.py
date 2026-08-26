"""core message + outline -> ClaimGraph (reasoning tier), built in TWO passes:
  Pass A — claim skeleton (main claims + subclaims).
  Pass B — grounding (evidence / method / data / warrant / source / artifact + edges).

A typed validator then runs. ``validate_strict`` returns both a clean graph and explicit
issues: known aliases may be normalized with a warning, but unknown kinds/relations,
wrong edge directions, duplicates, and dangling links are errors. ``validate`` remains
as the backward-compatible clean-dict adapter used by the existing pipeline.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from ..llm import client
from ..schemas.claim import ClaimGraph, GraphValidationIssue, GraphValidationResult, ProvenanceRef
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt

_VALID_NODE = {"claim", "evidence", "method", "data", "warrant", "source", "artifact",
               "threshold", "pitfall", "decision"}
_VALID_EDGE = {"supports", "produces", "uses", "derived_from", "part_of",
               "visualizes", "justifies", "qualifies", "contradicts",
               "feeds", "governs", "warns_about"}

_NODE_MAP = {**{k: k for k in _VALID_NODE},
             "assertion": "claim", "contribution": "claim", "hypothesis": "claim",
             "conclusion": "claim", "subclaim": "claim", "objective": "claim",
             "result": "evidence", "finding": "evidence", "observation": "evidence",
             "measurement": "evidence", "datum": "evidence",
             "dataset": "data", "file": "data", "csv": "data", "output": "data",
             # A repository is a real input object. Normalizing it to data lets the
             # existing method-uses-data relation represent executable source without
             # adding a one-off `code` node kind.
             "code": "data", "repository": "data", "code_repository": "data",
             "procedure": "method", "technique": "method", "approach": "method",
             "protocol": "method", "submethod": "method", "step": "method",
             "assumption": "warrant", "principle": "warrant", "background": "warrant",
             "rationale": "warrant", "premise": "warrant",
             "reference": "source", "citation": "source", "paper": "source", "prior_work": "source",
             "figure": "artifact", "table": "artifact", "chart": "artifact",
             "plot": "artifact", "equation": "artifact", "panel": "artifact",
             "rule": "threshold", "decision_rule": "threshold", "parameter_rule": "threshold",
             "failure": "pitfall", "failure_mode": "pitfall", "risk": "pitfall",
             "choice": "decision", "selection": "decision", "tradeoff": "decision"}
# known synonyms -> canonical relation. UNKNOWN relations are intentionally absent:
# they get dropped, not mapped to 'supports'.
_EDGE_MAP = {**{r: r for r in _VALID_EDGE},
             "support": "supports", "demonstrates": "supports", "confirms": "supports",
             "shows_that": "supports", "evidences": "supports",
             "generates": "produces", "yields": "produces", "outputs": "produces",
             "computes": "produces",
             "consumes": "uses", "takes": "uses", "requires": "uses", "requires_input": "uses",
             "computed_from": "derived_from", "based_on": "derived_from", "from": "derived_from",
             "calculated_from": "derived_from",
             "subprocess_of": "part_of", "component_of": "part_of", "belongs_to": "part_of",
             "step_of": "part_of",
             "shows": "visualizes", "displays": "visualizes", "illustrates": "visualizes",
             "depicts": "visualizes", "presents": "visualizes",
             "licenses": "justifies", "grounds": "justifies", "motivates": "justifies",
             "limits": "qualifies", "caveats": "qualifies", "restricts": "qualifies",
             "weakens": "qualifies",
             "refutes": "contradicts", "conflicts": "contradicts", "disagrees": "contradicts",
             "flows_to": "feeds", "passes_to": "feeds", "input_to": "feeds",
             "controls": "governs", "determines": "governs", "sets": "governs",
             "warns": "warns_about", "risks": "warns_about", "can_fail_at": "warns_about"}

# allowed (src_kind, dst_kind) per relation — directional
_ALLOWED_EDGE: dict[str, set[tuple[str, str]]] = {
    "supports": {("evidence", "claim"), ("claim", "claim")},
    "produces": {("method", "data"), ("method", "evidence")},
    "uses": {("method", "data")},
    "derived_from": {("evidence", "data"), ("evidence", "evidence"), ("data", "data"),
                     ("data", "method")},
    "part_of": {("method", "method"), ("claim", "claim")},
    "visualizes": {("artifact", "evidence"), ("artifact", "method"), ("artifact", "data")},
    "justifies": {("warrant", "claim"), ("source", "warrant"), ("warrant", "method"),
                  ("source", "claim")},
    "qualifies": {("warrant", "claim"), ("claim", "claim")},
    "contradicts": {("evidence", "claim"), ("claim", "claim")},
    "feeds": {("method", "method")},
    "governs": {("threshold", "data"), ("threshold", "method"),
                ("decision", "data"), ("decision", "method")},
    "warns_about": {("pitfall", "method"), ("pitfall", "data")},
}


def _normalized(value) -> str:
    return str(value or "").strip().lower()


def _coerce_kind(k) -> str | None:
    """Return a known canonical kind; never turn an unknown kind into a claim."""
    return _NODE_MAP.get(_normalized(k))


def _issue(code: str, message: str, *, location: str = "", item_id: str = "",
           severity: str = "error", value=None) -> GraphValidationIssue:
    return GraphValidationIssue(code=code, message=message, location=location,
                                item_id=item_id, severity=severity, value=value)


def _normalize_provenance_refs(item: dict, *, location: str, item_id: str,
                               issues: list[GraphValidationIssue]) -> None:
    """Preserve structured model locators while satisfying the string contract.

    Artifact manifests expose locators as objects (for example a relative path plus
    row range), and Gemini can faithfully echo that object. The public graph schema
    intentionally keeps ``locator`` portable as a string, so encode structured
    values deterministically instead of rejecting an otherwise valid graph.
    """
    refs = item.get("provenance_refs")
    if refs is None:
        return
    if not isinstance(refs, list):
        issues.append(_issue(
            "provenance_refs.not_array", "provenance_refs must be an array",
            location=f"{location}.provenance_refs", item_id=item_id, value=refs,
        ))
        item["provenance_refs"] = []
        return
    for ref_idx, ref in enumerate(refs):
        if not isinstance(ref, dict):
            continue
        locator = ref.get("locator")
        if locator is not None and not isinstance(locator, str):
            ref["locator"] = json.dumps(locator, ensure_ascii=False, sort_keys=True)
            issues.append(_issue(
                "provenance_ref.locator_encoded",
                "Encoded a structured provenance locator as JSON text",
                location=f"{location}.provenance_refs[{ref_idx}].locator",
                item_id=item_id, severity="warning", value=locator,
            ))


def validate_strict(raw: dict) -> GraphValidationResult:
    """Validate raw graph data without silently inventing semantics.

    Invalid records are excluded from the returned clean graph so it remains safe to
    pass to ``ClaimGraph.model_validate``. Every exclusion and every known-alias
    normalization is reported in ``issues``. The input object is never mutated.
    """
    if not isinstance(raw, dict):
        issue = _issue("graph.not_object", "Graph must be a JSON object", value=raw)
        return GraphValidationResult(ok=False, graph={"schema_version": "1.0", "revision": 0,
                                     "main_contribution": "", "nodes": [], "edges": []},
                                     issues=[issue])

    clean = deepcopy(raw)
    clean.setdefault("schema_version", "1.0")
    clean.setdefault("revision", 0)
    clean.setdefault("main_contribution", "")
    issues: list[GraphValidationIssue] = []

    raw_nodes = raw.get("nodes") or []
    if not isinstance(raw_nodes, list):
        issues.append(_issue("nodes.not_array", "nodes must be an array", location="nodes",
                             value=raw_nodes))
        raw_nodes = []

    nodes: list[dict] = []
    kind_of: dict[str, str] = {}
    for idx, candidate in enumerate(raw_nodes):
        loc = f"nodes[{idx}]"
        if not isinstance(candidate, dict):
            issues.append(_issue("node.not_object", "Node must be an object", location=loc,
                                 value=candidate))
            continue
        node = deepcopy(candidate)
        nid = str(node.get("id") or "").strip()
        if not nid:
            issues.append(_issue("node.missing_id", "Node id is required", location=loc,
                                 value=candidate))
            continue
        if nid in kind_of:
            issues.append(_issue("node.duplicate_id", f"Duplicate node id: {nid}", location=loc,
                                 item_id=nid))
            continue
        raw_kind = _normalized(node.get("kind"))
        kind = _coerce_kind(raw_kind)
        if kind is None:
            issues.append(_issue("node.unknown_kind", f"Unknown node kind: {raw_kind or '(empty)'}",
                                 location=f"{loc}.kind", item_id=nid, value=node.get("kind")))
            continue
        if raw_kind != kind:
            issues.append(_issue("node.kind_alias", f"Normalized node kind {raw_kind!r} to {kind!r}",
                                 location=f"{loc}.kind", item_id=nid, severity="warning",
                                 value=node.get("kind")))
        node["id"] = nid
        node["kind"] = kind
        node.setdefault("text", "")
        raw_layer = node.get("layer")
        if raw_layer in (1, 2):
            layer = "documented" if raw_layer == 1 else "tacit"
            node["layer"] = layer
            issues.append(_issue("node.layer_alias", f"Normalized numeric layer {raw_layer} to {layer!r}",
                                 location=f"{loc}.layer", item_id=nid, severity="warning",
                                 value=raw_layer))
        elif raw_layer not in (None, "documented", "tacit"):
            issues.append(_issue("node.invalid_layer", f"Unknown knowledge layer: {raw_layer!r}",
                                 location=f"{loc}.layer", item_id=nid, value=raw_layer))
            node.pop("layer", None)
        _normalize_provenance_refs(node, location=loc, item_id=nid, issues=issues)
        if kind in {"threshold", "pitfall", "decision"}:
            node.setdefault("layer", "tacit")
            node.setdefault("knowledge_status", "missing")
        nodes.append(node)
        kind_of[nid] = kind

    # Parent references are semantic links too. Keep the node but report the bad
    # reference; the graph can be displayed and repaired without losing its content.
    for idx, node in enumerate(nodes):
        parent = node.get("parent_id")
        if parent and parent not in kind_of:
            issues.append(_issue("node.dangling_parent", f"Unknown parent node: {parent}",
                                 location=f"nodes[{idx}].parent_id", item_id=node["id"], value=parent))
    clean["nodes"] = nodes

    raw_edges = raw.get("edges") or []
    if not isinstance(raw_edges, list):
        issues.append(_issue("edges.not_array", "edges must be an array", location="edges",
                             value=raw_edges))
        raw_edges = []
    explicit_ids = {str(e.get("id")) for e in raw_edges
                    if isinstance(e, dict) and e.get("id")}
    next_id = 1

    def generated_edge_id() -> str:
        nonlocal next_id
        while f"L{next_id}" in explicit_ids:
            next_id += 1
        value = f"L{next_id}"
        explicit_ids.add(value)
        next_id += 1
        return value

    edges: list[dict] = []
    used_edge_ids: set[str] = set()
    for idx, candidate in enumerate(raw_edges):
        loc = f"edges[{idx}]"
        if not isinstance(candidate, dict):
            issues.append(_issue("edge.not_object", "Edge must be an object", location=loc,
                                 value=candidate))
            continue
        edge = deepcopy(candidate)
        src, dst = str(edge.get("src") or "").strip(), str(edge.get("dst") or "").strip()
        eid = str(edge.get("id") or "").strip()
        if eid and eid in used_edge_ids:
            issues.append(_issue("edge.duplicate_id", f"Duplicate edge id: {eid}", location=loc,
                                 item_id=eid))
            continue
        if src not in kind_of or dst not in kind_of:
            issues.append(_issue("edge.dangling_endpoint",
                                 f"Edge endpoint is missing: {src or '(empty)'} -> {dst or '(empty)'}",
                                 location=loc, item_id=eid, value={"src": src, "dst": dst}))
            continue
        raw_rel = _normalized(edge.get("rel"))
        rel = _EDGE_MAP.get(raw_rel)
        if rel is None:
            issues.append(_issue("edge.unknown_relation",
                                 f"Unknown edge relation: {raw_rel or '(empty)'}",
                                 location=f"{loc}.rel", item_id=eid, value=edge.get("rel")))
            continue
        if raw_rel != rel:
            issues.append(_issue("edge.relation_alias",
                                 f"Normalized edge relation {raw_rel!r} to {rel!r}",
                                 location=f"{loc}.rel", item_id=eid, severity="warning",
                                 value=edge.get("rel")))
        pair = (kind_of[src], kind_of[dst])
        if pair not in _ALLOWED_EDGE.get(rel, set()):
            issues.append(_issue("edge.invalid_direction",
                                 f"{rel} does not allow {pair[0]} -> {pair[1]}",
                                 location=loc, item_id=eid,
                                 value={"src": src, "dst": dst, "rel": rel}))
            continue
        if not eid:
            eid = generated_edge_id()
        used_edge_ids.add(eid)
        edge.update({"id": eid, "src": src, "dst": dst, "rel": rel})
        _normalize_provenance_refs(edge, location=loc, item_id=eid, issues=issues)
        edges.append(edge)
    clean["edges"] = edges

    ok = not any(i.severity == "error" for i in issues)
    return GraphValidationResult(ok=ok, graph=clean, issues=issues)


def validate(raw: dict) -> dict:
    """Backward-compatible adapter returning only the clean graph dictionary."""
    return validate_strict(raw).graph


def _artifact_context(project_dir: str) -> str:
    """Render a bounded subset of extracted source chunks for graph construction."""
    manifest_path = Path(project_dir) / "main" / "artifact_manifest.json"
    if not manifest_path.is_file():
        return "(artifact manifest not built)"
    try:
        manifest = json.loads(manifest_path.read_text())
        compact = {
            "artifacts": [
                {
                    "logical_id": item.get("logical_id"),
                    "relative_path": item.get("relative_path"),
                    "status": item.get("status"),
                    "chunks": (item.get("chunks") or [])[:6],
                }
                for item in (manifest.get("artifacts") or [])[:30]
            ]
        }
        return json.dumps(compact, ensure_ascii=False)[:24_000]
    except Exception:
        return "(artifact manifest unreadable)"


def _attach_file_provenance(graph: ClaimGraph, project_dir: str) -> ClaimGraph:
    manifest_path = Path(project_dir) / "main" / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        return graph
    by_path = {str(a.get("relative_path", "")).lstrip("./"): a
               for a in (manifest.get("artifacts") or []) if a.get("relative_path")}
    for node in graph.nodes:
        source_path = str(node.provenance or "").lstrip("./")
        artifact = by_path.get(source_path)
        if artifact is None or any(ref.asset_id == artifact.get("logical_id")
                                   for ref in node.provenance_refs):
            continue
        node.provenance_refs.append(ProvenanceRef(
            source_type="file",
            asset_id=str(artifact.get("logical_id", "")),
            locator=str(artifact.get("relative_path", "")),
            verification_status="verified" if artifact.get("status") == "extracted" else "unverified",
            metadata={"sha256": artifact.get("sha256", ""),
                      "classification": artifact.get("classification", "")},
        ))
    return ground_verified_file_paths(graph)


def ground_verified_file_paths(graph: ClaimGraph) -> ClaimGraph:
    """Mark only deterministic file-backed origin links as grounded.

    The grounding prompt historically required an explicit status only for
    ``supports``/``justifies`` links, while the audit also requires origin links such
    as ``derived_from`` and ``produces`` to be grounded. A verified artifact proves
    the target data object exists; from there a method that produced that data can
    ground evidence produced by the same method. Missing/partial links are never
    promoted.
    """
    verified_data = {
        node.id for node in graph.nodes
        if node.kind == "data" and (
            str(node.provenance or "").strip() not in {"", "[DATA_NEEDED]", "[ASK_AUTHOR]"}
            or any(ref.source_type == "file" and ref.verification_status == "verified"
                   for ref in node.provenance_refs)
        )
    }
    for edge in graph.edges:
        if edge.grounding_status == "unverified" and edge.dst in verified_data \
                and edge.rel in {"derived_from", "uses", "produces"}:
            edge.grounding_status = "grounded"

    grounded_methods = {
        edge.src for edge in graph.edges
        if edge.grounding_status == "grounded" and edge.dst in verified_data
        and edge.rel in {"uses", "produces"}
    }
    for edge in graph.edges:
        target = graph.node(edge.dst)
        if edge.grounding_status == "unverified" and edge.rel == "produces" \
                and edge.src in grounded_methods and target and target.kind == "evidence":
            edge.grounding_status = "grounded"
    return graph


def build(ps: ProjectState) -> ClaimGraph:
    source_context = _artifact_context(ps.project_dir)
    ib = inputs_block(ps) + "\n\n## EXTRACTED SOURCE CHUNKS\n" + source_context
    # Pass A — claim skeleton
    a = client.call_json("reasoning", prompt("claim_graph_a"), ib, step="claim_graph.a", max_tokens=4096)
    claims = [c for c in (a.get("claims") or []) if isinstance(c, dict) and c.get("id")]
    for c in claims:
        c["kind"] = "claim"
    claim_block = "\n".join(f"- {c['id']} [{c.get('section', '')}] {c.get('text', '')}" for c in claims)

    # Pass B — grounding for the given claims
    b = client.call_json("reasoning", prompt("claim_graph_b"),
                         f"{ib}\n\n## CLAIM SKELETON (do not restate these)\n{claim_block}",
                         step="claim_graph.b", max_tokens=8192)

    merged = {
        "main_contribution": a.get("main_contribution", ""),
        "nodes": claims + [n for n in (b.get("nodes") or []) if isinstance(n, dict)],
        "edges": (a.get("claim_edges") or []) + (b.get("edges") or []),
    }
    documented = ClaimGraph.model_validate(validate(merged))

    # Pass C — ask only for unresolved, author-specific reasoning slots. Source chunks
    # are bounded by the artifact extractor; this pass creates questions, never answers.
    tacit = client.call_json(
        "reasoning", prompt("tacit_questions"),
        "## DOCUMENTED GRAPH\n" + documented.model_dump_json() +
        "\n\n## EXTRACTED SOURCE CHUNKS\n" + source_context,
        step="claim_graph.tacit", max_tokens=6000,
    )
    enriched = documented.model_dump()
    enriched["nodes"] += [n for n in (tacit.get("nodes") or []) if isinstance(n, dict)]
    enriched["edges"] += [e for e in (tacit.get("edges") or []) if isinstance(e, dict)]
    strict = validate_strict(enriched)
    if not strict.ok:
        errors = ", ".join(i.code for i in strict.issues if i.severity == "error")
        raise ValueError(f"tacit graph augmentation failed strict validation: {errors}")
    return _attach_file_provenance(ClaimGraph.model_validate(strict.graph), ps.project_dir)
