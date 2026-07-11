"""Data UX — optional description, AI-first role inference, confidence, global asset,
low-confidence files become questions."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from paperflow.ingest.parse_inputs import ingest
from paperflow.reconstruct import build_state
from paperflow.schemas.claim import ClaimGraph
from paperflow.schemas.evidence_inventory import EvidenceAsset, EvidenceInventory
from paperflow.question import gaps as gaps_mod
from paperflow.server.app import app

client = TestClient(app)


def _project_with_files(tmp_path: Path, notes: dict | None = None) -> str:
    main = tmp_path / "main"; main.mkdir(parents=True)
    (main / "0_journal_info.md").write_text("## Working title\nX\n## Author's field\nbio\n")
    (main / "1_coremessage.md").write_text("## One sentence\nMaterial dominates.\n")
    data = tmp_path / "data"; (data / "sobol").mkdir(parents=True)
    (data / "sobol" / "sobol_grp.csv").write_text("group,S1,ST\nmat,0.6,0.7\n")
    (data / "mystery_v3.csv").write_text("a,b,c\n1,2,3\n")          # opaque name, no description
    if notes:
        (main / "data_notes.json").write_text(json.dumps(notes, ensure_ascii=False))
    return str(tmp_path)


def test_description_optional_and_role_inferred(tmp_path):
    """No descriptions at all -> still profiled + roles inferred (AI-first)."""
    pd = _project_with_files(tmp_path, notes=None)
    ps = ingest(pd)
    inv = build_state.build_evidence_inventory(pd, ps)
    sobol = inv.by_path("data/sobol/sobol_grp.csv")
    assert sobol.user_description == ""                       # optional, absent
    assert sobol.inferred_role == "global sensitivity result"  # inferred from filename
    assert sobol.confidence == "high"                        # filename+rule match
    assert "result" in sobol.related_sections                # global hint, many-to-many
    assert sobol.inferred_description                         # AI/heuristic description filled


def test_confidence_levels(tmp_path):
    pd = _project_with_files(tmp_path, notes={"data/sobol/sobol_grp.csv": "user says: sobol"})
    ps = ingest(pd)
    inv = build_state.build_evidence_inventory(pd, ps)
    described = inv.by_path("data/sobol/sobol_grp.csv")
    mystery = inv.by_path("data/mystery_v3.csv")
    assert described.confidence == "high"                    # user description present
    assert described.user_description == "user says: sobol"
    # generic csv, opaque name, no description -> medium at best (kind-based csv has no rule)
    assert mystery.confidence in ("medium", "low")
    assert mystery.inferred_role in ("unknown", "structured record", "")


def test_low_or_unknown_files_become_questions(tmp_path):
    pd = _project_with_files(tmp_path, notes=None)
    ps = ingest(pd)
    inv = build_state.build_evidence_inventory(pd, ps)
    found = gaps_mod.detect(ClaimGraph(), evidence_inventory=inv)
    asked = {g.target_id for g in found if g.kind == "data_meaning_unknown"}
    # confidently-inferred sobol file is NOT asked about; opaque mystery file IS
    assert "data/sobol/sobol_grp.csv" not in asked
    assert "data/mystery_v3.csv" in asked


def test_described_high_confidence_not_asked(tmp_path):
    pd = _project_with_files(tmp_path, notes={"data/mystery_v3.csv": "calibration table"})
    ps = ingest(pd)
    inv = build_state.build_evidence_inventory(pd, ps)
    found = gaps_mod.detect(ClaimGraph(), evidence_inventory=inv)
    asked = {g.target_id for g in found if g.kind == "data_meaning_unknown"}
    assert "data/mystery_v3.csv" not in asked                # described -> not asked


def test_global_asset_not_section_bound(tmp_path):
    pd = _project_with_files(tmp_path, notes=None)
    ps = ingest(pd)
    inv = build_state.build_evidence_inventory(pd, ps)
    sobol = inv.by_path("data/sobol/sobol_grp.csv")
    # a sensitivity result is reusable across sections (many-to-many hint), not owned by one
    assert set(sobol.related_sections) >= {"method", "result"}
    assert "figure" in sobol.artifact_usage


def test_upload_without_description(tmp_path):
    """Server: files upload fine with no description (description endpoint is separate/optional)."""
    pd = _project_with_files(tmp_path, notes=None)
    files = [("files", ("extra.csv", b"x,y\n1,2\n", "text/csv"))]
    r = client.post("/api/projects/upload", data={"project_dir": pd}, files=files)
    assert r.status_code == 200
    saved = [f["name"] for f in r.json()["files"]]
    assert "extra.csv" in saved
    # uploaded file has empty note (optional) yet is listed
    extra = next(f for f in r.json()["files"] if f["name"] == "extra.csv")
    assert extra["note"] == ""
