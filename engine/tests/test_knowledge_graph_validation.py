import json
from pathlib import Path

from paperflow.compile.claim_graph import validate, validate_strict
from paperflow.schemas.claim import ClaimGraph


def test_unknown_kind_is_reported_and_never_becomes_claim():
    raw = {
        "nodes": [
            {"id": "C1", "kind": "claim", "text": "supported claim"},
            {"id": "X1", "kind": "mystery", "text": "must not become a claim"},
        ],
        "edges": [{"src": "X1", "dst": "C1", "rel": "supports"}],
    }

    result = validate_strict(raw)

    assert result.ok is False
    assert [node["id"] for node in result.graph["nodes"]] == ["C1"]
    assert result.graph["edges"] == []
    assert {issue.code for issue in result.issues} == {
        "node.unknown_kind", "edge.dangling_endpoint",
    }
    assert raw["nodes"][1]["kind"] == "mystery"  # validation is non-mutating


def test_tacit_kinds_and_relations_validate_with_backward_compatible_defaults():
    raw = {
        "main_contribution": "one contribution",
        "nodes": [
            {"id": "M1", "kind": "method", "text": "train"},
            {"id": "M2", "kind": "method", "text": "measure"},
            {"id": "D1", "kind": "data", "text": "parameter"},
            {"id": "TH1", "kind": "threshold", "text": "parameter rule"},
            {"id": "PF1", "kind": "pitfall", "text": "failure check"},
            {"id": "DC1", "kind": "decision", "text": "method choice"},
            {"id": "K1", "kind": "code", "text": "repository"},
        ],
        "edges": [
            {"src": "M1", "dst": "M2", "rel": "feeds"},
            {"src": "TH1", "dst": "D1", "rel": "governs"},
            {"src": "PF1", "dst": "M1", "rel": "warns_about"},
            {"src": "DC1", "dst": "M2", "rel": "governs"},
            {"src": "M1", "dst": "K1", "rel": "uses"},
        ],
    }

    result = validate_strict(raw)
    graph = ClaimGraph.model_validate(result.graph)

    assert result.ok is True
    assert graph.schema_version == "1.0"
    assert graph.revision == 0
    assert graph.node("TH1").layer == "tacit"
    assert graph.node("TH1").knowledge_status == "missing"
    assert graph.node("K1").kind == "data"
    assert len(graph.edges) == 5
    assert [i.code for i in result.issues] == ["node.kind_alias"]


def test_compatibility_validate_returns_clean_dict_and_unique_generated_edge_ids():
    raw = {
        "nodes": [
            {"id": "E1", "kind": "finding", "text": "result"},
            {"id": "C1", "kind": "claim", "text": "claim"},
        ],
        "edges": [
            {"id": "L1", "src": "E1", "dst": "C1", "rel": "supports"},
            {"src": "E1", "dst": "C1", "rel": "supports"},
        ],
    }

    clean = validate(raw)

    assert clean["nodes"][0]["kind"] == "evidence"
    assert [edge["id"] for edge in clean["edges"]] == ["L1", "L2"]


def test_demo_tacit_graph_is_preserved_by_unified_schema():
    path = Path(__file__).resolve().parents[2] / "demo_interview" / "graph.json"
    raw = json.loads(path.read_text())

    result = validate_strict(raw)
    graph = ClaimGraph.model_validate(result.graph)

    assert result.ok is True
    assert len(graph.nodes) == 27
    assert len(graph.edges) == 28
    assert {n.kind for n in graph.nodes} >= {"threshold", "pitfall", "decision"}
    assert {e.rel for e in graph.edges} >= {"feeds", "governs", "warns_about"}
    assert {i.code for i in result.issues} == {"node.kind_alias", "node.layer_alias"}
    assert all(i.severity == "warning" for i in result.issues)
