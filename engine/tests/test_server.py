"""Step 3 integration — server question/answer endpoints, adaptive + no hard gate (offline)."""
from fastapi.testclient import TestClient

from paperflow.ingest.parse_inputs import ingest
from paperflow.reconstruct import build_state
from paperflow.flows import method_result as mr
from paperflow.schemas.claim import ClaimGraph, GEdge, GNode
from paperflow.server.app import app

client = TestClient(app)


def _seed_reconstruction(project_dir: str):
    ps = ingest(project_dir)
    rs, inv = build_state.reconstruct(project_dir, ps, use_llm=False)
    build_state.save(project_dir, rs, inv)


def test_questions_offline_without_graph(mini_project):
    _seed_reconstruction(mini_project)
    r = client.post("/api/projects/questions", json={"project_dir": mini_project})
    assert r.status_code == 200
    data = r.json()
    assert data["has_graph"] is False
    # no graph yet -> primary claim is the first load-bearing gap
    assert any(q["gap_kind"] == "missing_primary_claim" for q in data["questions"])
    assert data["terminated"] is False
    assert data["warnings"]              # load-bearing, surfaced not blocked


def test_answers_merge_endpoint(mini_project):
    _seed_reconstruction(mini_project)
    client.post("/api/projects/answers", json={"project_dir": mini_project,
                                               "answers": {"q1": "a"}})
    r = client.post("/api/projects/answers", json={"project_dir": mini_project,
                                                   "answers": {"q2": "b"}})
    assert r.json()["count"] == 2        # merged, not overwritten


def test_questions_with_prelim_graph(mini_project):
    _seed_reconstruction(mini_project)
    # a preliminary graph with one bare main claim
    graph = ClaimGraph(nodes=[GNode(id="C1", kind="claim", text="bare claim")], edges=[])
    mr.prelim_graph_path(mini_project).write_text(graph.model_dump_json())
    r = client.post("/api/projects/questions", json={"project_dir": mini_project,
                                                     "batch_size": 10})
    data = r.json()
    assert data["has_graph"] is True
    kinds = {q["gap_kind"] for q in data["questions"]}
    assert "claim_without_evidence" in kinds
    # answer the load-bearing question -> terminates
    lb = [q for q in data["questions"] if q["load_bearing"]]
    client.post("/api/projects/answers", json={
        "project_dir": mini_project, "answers": {q["id"]: "x" for q in lb}})
    r2 = client.post("/api/projects/questions", json={"project_dir": mini_project,
                                                      "batch_size": 10})
    assert r2.json()["terminated"] is True


def test_generate_requires_plan_not_answers(mini_project):
    """No hard gate on answers: generate fails only because there is no confirmed plan."""
    _seed_reconstruction(mini_project)
    r = client.post("/api/projects/generate", json={"project_dir": mini_project})
    assert r.json().get("error") == "no_plan"      # NOT "unanswered_questions"
