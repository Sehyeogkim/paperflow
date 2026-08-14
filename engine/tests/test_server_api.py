import base64

from fastapi.testclient import TestClient

from paperflow.server import app as server_app
from paperflow.server import storage


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path.resolve())
    monkeypatch.setattr(server_app, "_WORKSPACE", tmp_path.resolve())
    monkeypatch.setattr(server_app, "_ACCESS_TOKEN", "")
    return TestClient(server_app.app)


def test_create_profile_and_reopen(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    created = client.post("/api/projects/create", json={"name": "My Study"}).json()
    project_id = created["project_id"]

    response = client.post("/api/projects/profile", json={
        "project_id": project_id,
        "field": "Computational science",
        "objective": "Determine which inputs govern the observed response.",
        "results_summary": "Material parameters dominate the response.",
    })
    assert response.status_code == 200
    assert response.json()["ok"] is True

    project = tmp_path / project_id
    assert (project / "main" / "profile.json").is_file()
    assert (project / "main" / "0_journal_info.md").is_file()
    assert (project / "main" / "1_coremessage.md").is_file()
    assert (project / "main" / "3_outline.md").is_file()

    state = client.get("/api/projects/state", params={"project_id": project_id}).json()
    assert state["workflow"]["stage"] == "sources_ready"


def test_upload_is_renamed_and_constrained_to_project(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    project_id = client.post("/api/projects/create", json={"name": "Upload"}).json()["project_id"]
    response = client.post(
        "/api/projects/upload",
        data={"project_id": project_id},
        files={"files": ("result.csv", b"x,y\n1,2\n", "text/csv")},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["saved"][0]["name"] == "result.csv"
    assert payload["saved"][0]["stored_name"].endswith("_result.csv")
    assert (tmp_path / project_id / "data" / "uploads" / payload["saved"][0]["stored_name"]).is_file()

    extracted = client.post("/api/projects/extract", json={"project_id": project_id}).json()
    assert extracted["ok"] is True
    assert extracted["summary"]["artifacts"] == 1
    assert extracted["summary"]["chunks"] == 1


def test_interview_answer_revises_graph_then_allows_confirmation(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    project_id = client.post("/api/projects/create", json={"name": "Interview"}).json()["project_id"]
    project = tmp_path / project_id
    graph = {
        "revision": 1,
        "nodes": [
            {"id": "C1", "kind": "claim", "text": "The response is governed by x."},
            {"id": "E1", "kind": "evidence", "text": "Observed response", "provenance": "data/x.csv"},
            {"id": "D1", "kind": "data", "text": "x", "provenance": "data/x.csv"},
            {"id": "TH1", "kind": "threshold", "text": "cutoff", "risk": "high",
             "knowledge_status": "missing", "question": "How is the cutoff selected?",
             "must_capture": ["decision_rule"]},
        ],
        "edges": [
            {"id": "L1", "src": "E1", "dst": "C1", "rel": "supports", "grounding_status": "grounded"},
            {"id": "L2", "src": "TH1", "dst": "D1", "rel": "governs", "grounding_status": "missing"},
        ],
    }
    storage.write_json(project / "main" / "knowledge_graph.json", graph)
    storage.update_workflow(project, graph_revision=1, stage="questioning")

    questions = client.get("/api/projects/questions", params={"project_id": project_id}).json()
    assert questions["next_question"]["id"] == "Q-TH1"
    assert questions["audit"]["ok"] is False

    answered = client.post("/api/projects/questions/answer", json={
        "project_id": project_id,
        "question_id": "Q-TH1",
        "answer": "Use the first stable plateau.",
        "completion": "complete",
        "captured_fields": {"decision_rule": "first stable plateau"},
        "base_revision": 1,
    }).json()
    assert answered["ok"] is True
    assert answered["graph"]["revision"] == 2
    assert answered["audit"]["ok"] is True

    confirmed = client.post("/api/projects/graph/confirm", json={
        "project_id": project_id, "graph_revision": 2,
    }).json()
    assert confirmed["ok"] is True
    assert confirmed["workflow"]["confirmed_graph_revision"] == 2

    client.post("/api/projects/profile", json={
        "project_id": project_id, "field": "Science", "objective": "Changed objective",
    })
    stale = client.post("/api/projects/graph/confirm", json={
        "project_id": project_id, "graph_revision": 2,
    }).json()
    assert stale["error"] == "source_revision_changed"


def test_shared_access_token_guard(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(server_app, "_ACCESS_TOKEN", "alpha-secret")
    assert client.get("/").status_code == 401
    encoded = base64.b64encode(b"researcher:alpha-secret").decode()
    allowed = client.get("/", headers={"Authorization": f"Basic {encoded}"})
    assert allowed.status_code == 200
    assert allowed.headers["x-frame-options"] == "DENY"
    assert "object-src 'none'" in allowed.headers["content-security-policy"]
    assert client.get("/healthz").status_code == 200
