"""Acceptance tests for the literature-grounded requirement pipeline (LLM + OpenAlex mocked)."""
import json
from pathlib import Path

import pytest

from paperflow.ingest.parse_inputs import ingest
from paperflow.requirement import (
    compare_user_state, detect, fallback, literature_search,
    normalize_items, paper_extract, pipeline, synthesize_schema,
)
from paperflow.llm import client
from paperflow.litsearch import openalex


# ---------- fakes ----------
def _fake_papers(n=8):
    return [{
        "title": f"Coronary plaque FSI study {i}", "authors": ["Author X", "Author Y"],
        "year": 2020 + (i % 5), "doi": f"10.1000/p{i}",
        "abstract": "We simulate coronary plaque stress with FSI and report sensitivity.",
        "cited_by": 50 - i, "key": f"author{i}",
    } for i in range(1, n + 1)]


def _dispatch(tier, system, user, *, step="", max_tokens=4096, effort=""):
    """Deterministic LLM responses keyed by pipeline step."""
    if step == "lit.queries":
        return {"study_archetype": "computational plaque biomechanics sensitivity study",
                "field": "computational biomechanics",
                "queries": ["coronary plaque FSI stress", "Sobol sensitivity plaque",
                            "mesh independence cardiovascular FEM"]}
    if step == "lit.extract":
        try:
            pid = json.loads(user).get("paper_id", "paper_001")
        except Exception:
            pid = "paper_001"
        return {"paper_id": pid, "study_archetype": "computational plaque biomechanics",
                "content_level": "abstract_only",
                "reported_items": [
                    {"raw_name": "mesh convergence study", "category": "validation",
                     "sub_category": "grid", "description": "checked mesh", "explicitly_reported": True},
                    {"raw_name": "Mooney-Rivlin material model", "category": "models_and_equations",
                     "sub_category": "constitutive", "description": "vessel wall", "explicitly_reported": True},
                ]}
    if step.startswith("lit.normalize"):   # now per-category: "lit.normalize:<category>"
        if "validation" in step:
            return {"clusters": [
                {"canonical_key": "mesh_independence", "category": "validation",
                 "aliases": ["mesh convergence study", "grid independence test"],
                 "applicable_to": ["quantitative_numerical_simulation", "peak_field_value_claim"],
                 "source_items": ["paper_001:item_01", "paper_003:item_01", "paper_005:item_01"]}]}
        if "models_and_equations" in step:
            return {"clusters": [
                {"canonical_key": "material_constitutive_model", "category": "models_and_equations",
                 "aliases": ["Mooney-Rivlin material model", "hyperelastic law"],
                 "applicable_to": ["finite_element_simulation"],
                 "source_items": ["paper_001:item_02", "paper_002:item_02"]}]}
        return {"clusters": []}
    if step == "lit.synthesize":
        return {"study_archetype": "computational plaque biomechanics sensitivity study",
                "requirements": [
                    {"key": "mesh_independence",
                     "applicability": {"required_when": ["peak_stress_claim"], "not_applicable_when": []},
                     "applicable_papers": 5, "requirement_level": "strongly_expected",
                     "reason": "Peak stress is mesh-sensitive."},
                    {"key": "material_constitutive_model",
                     "applicability": {"required_when": ["fem_simulation"], "not_applicable_when": []},
                     "applicable_papers": 4, "requirement_level": "mandatory",
                     "reason": "Constitutive law governs stress outputs."},
                ]}
    if step == "lit.compare_question":   # merged compare + question (single call)
        return {"results": [
            {"key": "mesh_independence", "status": "missing", "found_evidence": [],
             "reason": "No mesh comparison found in materials.", "ask": True,
             "question": "주요 결과인 peak plaque stress에 대해 mesh-independence test를 수행했나요?",
             "why_asked": "Peak stress is mesh-sensitive; 3 of 5 applicable papers reported it.",
             "expected_answer": "비교한 mesh 크기와 변화율"},
            {"key": "material_constitutive_model", "status": "present",
             "found_evidence": ["core_message"], "reason": "Material model stated.", "ask": False},
        ]}
    if step == "requirement.detect":   # static fallback path
        return {"study_type": "computational_biomechanics",
                "classification": "MISSING_CRITICAL_INFORMATION",
                "present": ["research_objective"],
                "missing": [{"field": "governing_equations", "why_it_matters": "needed",
                             "reviewer_risk": "high", "question": "지배방정식은?", "example": "Navier-Stokes"}],
                "notes": "static fallback"}
    return {}


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(openalex, "search", lambda q, n=5: _fake_papers(8))
    monkeypatch.setattr(client, "call_json", _dispatch)
    return True


# ---------- Literature discovery ----------
def test_search_dedup_and_select(patched, mini_project):
    _, _, queries = literature_search.derive_queries(ingest(mini_project))
    papers = literature_search.search_and_select(queries)
    assert 8 <= len(papers) <= 16
    dois = [p.doi for p in papers]
    assert len(dois) == len(set(dois))                 # deduped
    assert all(p.content_level == "abstract_only" for p in papers)
    assert all(p.doi and p.title for p in papers)


# ---------- Per-paper extraction ----------
def test_extraction_fixed_category_free_item(patched):
    papers = literature_search.search_and_select(["q"])
    exts = paper_extract.extract_all(papers)
    assert len(exts) == len(papers)
    item = exts[0].reported_items[0]
    assert item.category == "validation"               # fixed top-level
    assert item.raw_name == "mesh convergence study"   # free name
    assert exts[0].content_level == "abstract_only"     # abstract restriction recorded


# ---------- Schema synthesis ----------
def test_schema_separates_observed_and_applicable(patched, mini_project):
    ps = ingest(mini_project)
    papers = literature_search.search_and_select(["q"])
    exts = paper_extract.extract_all(papers)
    clusters = normalize_items.normalize(exts)
    assert {c["canonical_key"] for c in clusters} == {"mesh_independence", "material_constitutive_model"}
    schema = synthesize_schema.synthesize(clusters, ps, papers, "proj", "archetype")
    mesh = next(r for r in schema.requirements if r.key == "mesh_independence")
    # observed_in (papers reporting it) is distinct from applicable_papers (all selected papers,
    # computed deterministically in code so prevalence has real variance, not a trivial 1.0)
    assert mesh.observed_in == 3 and mesh.applicable_papers == len(papers)
    assert mesh.prevalence == round(3 / len(papers), 3)
    assert mesh.requirement_level == "strongly_expected"
    assert mesh.evidence_sources == ["paper_001", "paper_003", "paper_005"]
    assert "grid independence test" in mesh.aliases                   # alias merged


# ---------- User comparison ----------
def test_compare_statuses(patched, mini_project):
    ps = ingest(mini_project)
    papers = literature_search.search_and_select(["q"])
    exts = paper_extract.extract_all(papers)
    schema = synthesize_schema.synthesize(normalize_items.normalize(exts), ps, papers, "p", "a")
    statuses = compare_user_state.compare(schema, ps)
    by = {s.key: s for s in statuses}
    assert by["mesh_independence"].status == "missing"
    assert by["material_constitutive_model"].status == "present"
    assert by["mesh_independence"].source_requirements == ["overall_schema:mesh_independence"]


# ---------- Questions ----------
def test_questions_only_high_value_with_grounding(patched, mini_project):
    ps = ingest(mini_project)
    papers = literature_search.search_and_select(["q"])
    exts = paper_extract.extract_all(papers)
    schema = synthesize_schema.synthesize(normalize_items.normalize(exts), ps, papers, "p", "a")
    statuses, qs = compare_user_state.compare_and_question(schema, ps)
    # only the missing strongly_expected/mandatory is asked (present one skipped)
    assert [q.id for q in qs] == ["mesh_independence"]
    q = qs[0]
    assert q.why_asked and q.sources == ["paper_001", "paper_003", "paper_005"]
    assert q.reviewer_risk == "high" and q.allow_unknown


# ---------- End-to-end + persistence ----------
def test_pipeline_persists_and_report(patched, mini_project):
    ps = ingest(mini_project)
    res = pipeline.run(mini_project, ps)
    assert res["requirement_source"] == "literature_derived"
    assert any(q.id == "mesh_independence" for q in res["questions"])
    # compatible RequirementReport for the generate flow
    assert res["report"].missing and res["report"].classification
    litdir = Path(mini_project) / "main" / "literature"
    for f in ["search_queries.json", "selected_papers.json", "overall_schema.json",
              "requirement_status.json", "grounded_questions.json"]:
        assert (litdir / f).is_file(), f
    assert (litdir / "paper_001.json").is_file()
    assert (litdir / "_fingerprint.json").is_file()


def test_fingerprint_cache_reuses_literature(patched, monkeypatch, mini_project):
    ps = ingest(mini_project)
    pipeline.run(mini_project, ps)                       # 1st run: full pipeline + fingerprint
    # 2nd run with OpenAlex DEAD: if it re-searched it would fall back; cache must avoid that
    monkeypatch.setattr(openalex, "search", lambda q, n=5: (_ for _ in ()).throw(RuntimeError("down")))
    res = pipeline.run(mini_project, ingest(mini_project))
    assert res["requirement_source"] == "literature_derived"   # reused, did NOT re-search
    assert any(q.id == "mesh_independence" for q in res["questions"])


# ---------- Regression: OpenAlex failure -> static fallback ----------
def test_fallback_on_no_papers(monkeypatch, mini_project):
    monkeypatch.setattr(openalex, "search", lambda q, n=5: [])     # OpenAlex returns nothing
    monkeypatch.setattr(client, "call_json", _dispatch)
    ps = ingest(mini_project)
    res = pipeline.run(mini_project, ps)
    assert res["requirement_source"] == "static_fallback"
    assert res["report"].classification.value == "MISSING_CRITICAL_INFORMATION"
    assert res["questions"][0].id == "governing_equations"
    # report still saveable/loadable so generate reuse + answer save are unaffected
    detect.save_report(mini_project, res["report"])
    loaded = detect.load_report(mini_project)
    assert loaded is not None and loaded.missing[0].field == "governing_equations"
