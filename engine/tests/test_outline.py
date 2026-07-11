"""Outline UX — Quick/Structured/legacy all normalize to ONE schema; raw text preserved."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from paperflow.ingest import normalize_outline as no_mod
from paperflow.ingest.parse_inputs import ingest
from paperflow.schemas.outline_state import NormalizedOutline
from paperflow.schemas.project_state import Outline, OutlineParagraph
from paperflow.server.app import app

client = TestClient(app)


def test_structured_normalization_deterministic():
    no = no_mod.normalize_structured({
        "introduction": "- rupture is a major cause\n- prior work fixes strength",
        "result": "1. Material dominates\n2. Amplitude is better",
        "method": "FSI simulation",
    })
    assert no.input_mode == "structured"
    assert no.sections["introduction"] == ["rupture is a major cause", "prior work fixes strength"]
    assert no.sections["result"] == ["Material dominates", "Amplitude is better"]
    assert no.sections["method"] == ["FSI simulation"]
    assert "Material dominates" in no.claim_candidates
    assert "FSI simulation" in no.method_notes
    # raw preserved
    assert "Material dominates" in no.raw_outline


def test_quick_heuristic_no_llm_preserves_and_buckets():
    raw = ("some stray note before any section\n"
           "Introduction\nRupture is a major cause.\n"
           "Method\nWe ran FSI simulation.\n"
           "Results\nMaterial dominates the ranking.")
    no = no_mod.normalize_quick(raw, use_llm=False)
    assert no.input_mode == "quick"
    assert no.raw_outline == raw                      # verbatim preserved
    assert "Rupture is a major cause." in no.sections["introduction"]
    assert "We ran FSI simulation." in no.sections["method"]
    assert "Material dominates the ranking." in no.sections["result"]
    # a line before any heading is kept, never dropped
    assert "some stray note before any section" in no.unclassified_notes


def test_legacy_outline_normalizes():
    legacy = Outline(skeleton=[
        OutlineParagraph(n=1, section_label="Intro", claim_sentence="Rupture matters"),
        OutlineParagraph(n=2, section_label="Results", claim_sentence="Material dominates"),
        OutlineParagraph(n=3, section_label="", claim_sentence="loose note"),
    ], raw="raw text")
    no = no_mod.normalize_legacy(legacy)
    assert no.input_mode == "legacy"
    assert no.sections["introduction"] == ["Rupture matters"]
    assert no.sections["result"] == ["Material dominates"]
    assert no.unclassified_notes == ["loose note"]    # unlabeled kept


def test_to_outline_and_render_md_roundtrip_into_pipeline():
    no = no_mod.normalize_structured({"method": "step A\nstep B", "result": "finding X"})
    ol = no_mod.to_outline(no)
    # produces the legacy skeleton the writer/inputs_block consume
    assert [p.claim_sentence for p in ol.skeleton] == ["finding X", "step A", "step B"] or \
           {"step A", "step B", "finding X"} <= {p.claim_sentence for p in ol.skeleton}
    md = no_mod.render_md(no)
    assert "[Method]" in md and "step A" in md and "[Result]" in md


def test_ingest_prefers_outline_state(tmp_path):
    main = tmp_path / "main"; main.mkdir(parents=True)
    (main / "0_journal_info.md").write_text("## Working title\nX\n")
    (main / "1_coremessage.md").write_text("## One sentence\nY\n")
    no = no_mod.normalize_quick("Method\nWe did Z.", use_llm=False)
    (main / "outline_state.json").write_text(no.model_dump_json())
    ps = ingest(str(tmp_path))
    assert ps.normalized_outline is not None
    assert ps.normalized_outline.input_mode == "quick"
    # legacy Outline built from it so the pipeline still has a skeleton
    assert any("We did Z." in p.claim_sentence for p in ps.outline.skeleton)


def test_ingest_legacy_3outline_still_works(mini_project):
    """Backward compat: a project with only 3_outline.md yields a legacy normalized outline."""
    ps = ingest(mini_project)
    assert ps.normalized_outline is not None
    assert ps.normalized_outline.input_mode == "legacy"
    assert ps.outline.skeleton                       # original skeleton intact


def test_outline_endpoint_quick_and_structured(tmp_path):
    main = tmp_path / "main"; main.mkdir(parents=True)
    (main / "0_journal_info.md").write_text("## Working title\nX\n")
    (main / "1_coremessage.md").write_text("## One sentence\nY\n")
    pd = str(tmp_path)
    # structured
    r = client.post("/api/projects/outline", json={
        "project_dir": pd, "mode": "structured",
        "sections": {"method": "did A", "result": "found B"}})
    assert r.json()["ok"] is True
    assert (main / "outline_state.json").is_file()
    assert (main / "3_outline.md").is_file()          # legacy view written
    # quick (no key in test env -> heuristic)
    r2 = client.post("/api/projects/outline", json={
        "project_dir": pd, "mode": "quick", "raw": "Method\nran sim\nResults\ngot X"})
    out = r2.json()["outline"]
    assert out["input_mode"] == "quick"
    assert out["raw_outline"] == "Method\nran sim\nResults\ngot X"
    g = client.get("/api/projects/outline", params={"project_dir": pd}).json()
    assert g["outline"]["input_mode"] == "quick"
