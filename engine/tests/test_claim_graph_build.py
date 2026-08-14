from paperflow.compile import claim_graph
from paperflow.schemas.project_state import ProjectState
from paperflow.server import storage


def test_build_uses_extracted_chunks_and_creates_tacit_questions(tmp_path, monkeypatch):
    manifest = {
        "artifacts": [{
            "logical_id": "result-abc",
            "relative_path": "data/result.csv",
            "status": "extracted",
            "classification": "csv",
            "sha256": "a" * 64,
            "chunks": [{"chunk_id": "result-abc:c0001", "text": "cutoff,result\n0.5,12",
                        "locator": {"relative_path": "data/result.csv", "locator_type": "csv"}}],
        }],
    }
    storage.write_json(tmp_path / "main" / "artifact_manifest.json", manifest)
    seen_users = []

    def fake_call_json(_tier, _system, user, *, step, max_tokens):
        seen_users.append((step, user))
        if step == "claim_graph.a":
            return {"main_contribution": "Measured cutoff response",
                    "claims": [{"id": "C1", "text": "The cutoff governs the response."}],
                    "claim_edges": []}
        if step == "claim_graph.b":
            return {
                "nodes": [
                    {"id": "D1", "kind": "data", "text": "result table",
                     "provenance": "data/result.csv"},
                    {"id": "E1", "kind": "evidence", "text": "observed response"},
                ],
                "edges": [
                    {"src": "E1", "dst": "D1", "rel": "derived_from"},
                    {"src": "E1", "dst": "C1", "rel": "supports",
                     "grounding_status": "grounded"},
                ],
            }
        assert step == "claim_graph.tacit"
        return {
            "nodes": [{"id": "TH1", "kind": "threshold", "text": "cutoff selection",
                       "question": "How is the cutoff selected?", "risk": "high",
                       "must_capture": ["decision_rule"], "knowledge_status": "missing"}],
            "edges": [{"src": "TH1", "dst": "D1", "rel": "governs",
                       "grounding_status": "missing"}],
        }

    monkeypatch.setattr(claim_graph.client, "call_json", fake_call_json)
    graph = claim_graph.build(ProjectState(project_dir=str(tmp_path)))

    assert any("cutoff,result" in user for _, user in seen_users[:2])
    assert graph.node("TH1").question == "How is the cutoff selected?"
    assert graph.node("D1").provenance_refs[0].asset_id == "result-abc"
