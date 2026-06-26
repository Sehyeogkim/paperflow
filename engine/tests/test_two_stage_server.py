"""Two-stage server endpoints — Stage-1/Stage-2 answer submission, job routing, SSE (offline,
heavy steps stubbed)."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from paperflow.flows import method_result as mr
from paperflow.schemas.eval import RunManifest
from paperflow.server.app import app

client = TestClient(app)


def _events(body: str) -> list[dict]:
    out = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if chunk.startswith("data:"):
            out.append(json.loads(chunk[len("data:"):].strip()))
    return out


def _project(tmp_path: Path) -> str:
    (tmp_path / "main").mkdir(parents=True)
    (tmp_path / "main" / "1_coremessage.md").write_text("## One sentence\nX dominates Y.\n")
    return str(tmp_path)


def test_requirement_endpoint_persists_and_routes_to_generation(tmp_path, monkeypatch):
    pd = _project(tmp_path)
    monkeypatch.setattr(mr, "advance_after_requirement_answers",
                        lambda project_dir, progress=lambda m: None: {
                            "next": "generation", "questions": [], "gap_report": {}})
    monkeypatch.setattr(mr, "finalize_and_compile",
                        lambda pd_, out, progress=lambda m: None: RunManifest(project_dir=pd_))
    r = client.post("/api/projects/answers/requirement",
                    json={"project_dir": pd, "answers": {"mesh_independence": "yes, <2%"}})
    assert "job_id" in r.json()
    # answers persisted separately
    saved = json.loads((Path(pd) / "main" / "answers_requirement.json").read_text())
    assert saved["mesh_independence"] == "yes, <2%"
    # stream routes straight to generation -> done
    body = client.get(f"/api/projects/answers/{r.json()['job_id']}/stream").text
    types = [e["type"] for e in _events(body)]
    assert "generating" in types and "done" in types


def test_requirement_endpoint_routes_to_logic_questions(tmp_path, monkeypatch):
    pd = _project(tmp_path)
    monkeypatch.setattr(mr, "advance_after_requirement_answers",
                        lambda project_dir, progress=lambda m: None: {
                            "next": "logic_questions",
                            "questions": [{"id": "LOGIC_GAP_C1_EVIDENCE", "stage": "logic",
                                           "question": "근거?", "claim_ids": ["C1"],
                                           "gap_id": "GAP_C1_EVIDENCE"}],
                            "gap_report": {"load_bearing_gaps": [{"id": "GAP_C1_EVIDENCE"}]}})
    r = client.post("/api/projects/answers/requirement",
                    json={"project_dir": pd, "answers": {}})
    body = client.get(f"/api/projects/answers/{r.json()['job_id']}/stream").text
    evs = _events(body)
    lq = next(e for e in evs if e["type"] == "logic_questions")
    assert lq["questions"][0]["stage"] == "logic"
    assert "done" not in [e["type"] for e in evs]      # stops to ask, does not generate yet


def test_logic_endpoint_generates(tmp_path, monkeypatch):
    pd = _project(tmp_path)
    monkeypatch.setattr(mr, "finalize_and_compile",
                        lambda pd_, out, progress=lambda m: None: RunManifest(project_dir=pd_))
    r = client.post("/api/projects/answers/logic",
                    json={"project_dir": pd, "answers": {"LOGIC_GAP_C1_EVIDENCE": "모름"}})
    assert "job_id" in r.json()
    assert json.loads((Path(pd) / "main" / "answers_logic.json").read_text())[
        "LOGIC_GAP_C1_EVIDENCE"] == "모름"
    body = client.get(f"/api/projects/answers/{r.json()['job_id']}/stream").text
    assert "done" in [e["type"] for e in _events(body)]
