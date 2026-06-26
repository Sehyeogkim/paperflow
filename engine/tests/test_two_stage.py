"""Two-stage workflow (TWO_STAGE_QUESTIONS_FINAL_GRAPH_WORKFLOW.md §17).

Graph-gap validation, Stage-2 question generation, finalization, and the orchestration
state machine — all offline (LLM-dependent steps are injected/stubbed)."""
import json
from pathlib import Path

import pytest

from paperflow.compile import claim_graph
from paperflow.flows import method_result as mr
from paperflow.graph import finalize, logic_questions, validate_gaps
from paperflow.reconstruct import build_state
from paperflow.schemas.claim import ClaimGraph, GEdge, GNode
from paperflow.schemas.question import Question


# ---------- graph fixtures ----------

def _grounded_graph() -> ClaimGraph:
    """A defensible claim: evidence (traceable) + method + data + comparison + qualifier."""
    return ClaimGraph(nodes=[
        GNode(id="C1", kind="claim", text="The method reduces cost"),
        GNode(id="E1", kind="evidence", text="cost dropped 0.42 compared to baseline",
              provenance="data/r.csv"),
        GNode(id="M1", kind="method", text="benchmark"),
        GNode(id="D1", kind="data", text="r.csv", provenance="data/r.csv"),
        GNode(id="W1", kind="warrant", text="scope: idealized setting"),
    ], edges=[
        GEdge(src="E1", dst="C1", rel="supports"),
        GEdge(src="M1", dst="E1", rel="produces"),
        GEdge(src="E1", dst="D1", rel="derived_from"),
        GEdge(src="W1", dst="C1", rel="qualifies"),
    ])


def _bare_claim_graph() -> ClaimGraph:
    return ClaimGraph(nodes=[GNode(id="C1", kind="claim", text="Material dominates rupture risk")],
                      edges=[])


# ---------- unit: graph-gap validation ----------

def test_graph_gap_missing_evidence_detected():
    rep = validate_gaps.validate(_bare_claim_graph())
    assert rep.needs_stage2()
    g = rep.load_bearing_gaps[0]
    assert g.type == "missing_evidence_to_claim" and g.claim_ids == ["C1"]


def test_graph_gap_missing_comparator_detected():
    # comparative claim WITH evidence but no comparison basis / qualifier
    g = ClaimGraph(nodes=[
        GNode(id="C1", kind="claim", text="Material is more important than hemodynamics"),
        GNode(id="E1", kind="evidence", text="material ST index was 0.72", provenance="data/x.csv"),
    ], edges=[GEdge(src="E1", dst="C1", rel="supports")])
    rep = validate_gaps.validate(g)
    types = {x.type for x in rep.load_bearing_gaps}
    assert "missing_comparator" in types


def test_graph_gap_noncritical_warning_does_not_trigger_stage2():
    # fully grounded but no qualifier on... actually grounded graph HAS a qualifier; remove it
    g = _grounded_graph()
    g.edges = [e for e in g.edges if e.rel != "qualifies"]   # drop the qualifier
    g.nodes = [n for n in g.nodes if n.id != "W1"]
    rep = validate_gaps.validate(g)
    assert not rep.needs_stage2()                 # missing qualifier is a warning, not a gap
    assert any("qualifier" in w for w in rep.non_blocking_warnings)


def test_fully_grounded_graph_has_no_gaps():
    rep = validate_gaps.validate(_grounded_graph())
    assert rep.load_bearing_gaps == []
    assert rep.ready_for_finalization is True


# ---------- unit: logic questions ----------

def test_logic_question_contains_claim_and_gap_ids():
    rep = validate_gaps.validate(_bare_claim_graph())
    qs = logic_questions.generate(rep, _bare_claim_graph())
    assert qs and qs[0].stage == "logic"
    assert qs[0].claim_ids == ["C1"]
    assert qs[0].gap_id == rep.load_bearing_gaps[0].id
    assert qs[0].fallback_if_unknown  # declares what to do on "모름"


def test_logic_questions_capped_at_max():
    nodes = [GNode(id=f"C{i}", kind="claim", text=f"bare claim {i}") for i in range(8)]
    rep = validate_gaps.validate(ClaimGraph(nodes=nodes, edges=[]))
    qs = logic_questions.generate(rep, ClaimGraph(nodes=nodes, edges=[]), max_questions=5)
    assert len(qs) == 5


# ---------- unit: finalization ----------

def test_unknown_logic_answer_downgrades_claim():
    g = _bare_claim_graph()
    rep = validate_gaps.validate(g)
    qs = logic_questions.generate(rep, g)
    q = qs[0]
    final = claim_graph.build_final(g, [q], {q.id: "모름"})
    c = final.node("C1")
    assert c is not None                          # not removed (policy=downgrade)
    assert c.role == "downgraded"
    assert "약화" in c.text
    # NO fabricated evidence was created
    assert not [n for n in final.nodes if n.kind == "evidence"]


def test_real_logic_answer_adds_traceable_evidence():
    g = _bare_claim_graph()
    rep = validate_gaps.validate(g)
    qs = logic_questions.generate(rep, g)
    q = qs[0]
    final = claim_graph.build_final(g, [q], {q.id: "그룹별 Sobol ST=0.72, material 그룹 최댓값"})
    ev = [n for n in final.nodes if n.kind == "evidence"]
    assert ev and ev[0].provenance.startswith("author_answer:")
    assert any(e.rel == "supports" and e.dst == "C1" for e in final.edges)


def test_final_graph_rejects_untraceable_numeric_evidence():
    g = ClaimGraph(nodes=[
        GNode(id="C1", kind="claim", text="X holds"),
        GNode(id="E1", kind="evidence", text="value was 0.873", provenance="[DATA_NEEDED]"),
        GNode(id="E2", kind="evidence", text="value was 0.5 per file", provenance="data/x.csv"),
    ], edges=[GEdge(src="E1", dst="C1", rel="supports"),
              GEdge(src="E2", dst="C1", rel="supports")])
    out = finalize.reject_untraceable_numeric_evidence(g)
    ids = {n.id for n in out.nodes}
    assert "E1" not in ids          # untraceable numeric -> dropped
    assert "E2" in ids              # traceable -> kept
    assert not any(e.src == "E1" for e in out.edges)


# ---------- unit + integration: state rebuild & orchestration (LLM stubbed) ----------

@pytest.fixture
def offline(monkeypatch):
    """Force deterministic skeleton reconstruction (no provider calls)."""
    monkeypatch.setattr("paperflow.reconstruct.build_state.config.available_providers",
                        lambda: [])
    return monkeypatch


def test_requirement_answer_rebuilds_state(mini_project, offline):
    (Path(mini_project) / "main" / "answers_requirement.json").write_text(
        json.dumps({"mesh_independence": "compared 3 mesh sizes, <2% diff"}))
    from paperflow.ingest.parse_inputs import ingest
    ps = ingest(mini_project)
    rs_v2, inv = build_state.reconstruct_after_requirement_answers(
        mini_project, ps, {"mesh_independence": "compared 3 mesh sizes, <2% diff"})
    assert rs_v2.source == "v2"
    assert (Path(mini_project) / "main" / "research_state_v1.json").is_file()
    assert (Path(mini_project) / "main" / "research_state_v2.json").is_file()
    # answer recorded WITH provenance, distinguishable from inferred facts
    assert any(p["field"] == "mesh_independence" and p["source"] == "author_answer_requirement"
               for p in rs_v2.answer_provenance)
    assert any("mesh_independence" in o for o in rs_v2.key_observations)


def test_advance_path_a_no_stage2(mini_project, offline, monkeypatch):
    monkeypatch.setattr(claim_graph, "build_preliminary", lambda ps: _grounded_graph())
    (Path(mini_project) / "main" / "answers_requirement.json").write_text("{}")
    res = mr.advance_after_requirement_answers(mini_project)
    assert res["next"] == "generation"
    assert res["questions"] == []
    assert mr.preliminary_logic_graph_path(mini_project).is_file()
    assert (Path(mini_project) / "main" / "research_state_v2.json").is_file()


def test_advance_path_b_stage2_then_finalize(mini_project, offline, monkeypatch):
    monkeypatch.setattr(claim_graph, "build_preliminary", lambda ps: _bare_claim_graph())
    (Path(mini_project) / "main" / "answers_requirement.json").write_text("{}")
    res = mr.advance_after_requirement_answers(mini_project)
    assert res["next"] == "logic_questions"
    assert res["questions"] and res["questions"][0]["stage"] == "logic"
    qid = res["questions"][0]["id"]

    # stub the heavy compile; answer the logic question with a real value
    compiled = {}
    def _stub(pd, out_dir, graph, progress=lambda m: None, litsearch=True):
        compiled["graph"] = graph
        from paperflow.schemas.eval import RunManifest
        return RunManifest(project_dir=pd)
    monkeypatch.setattr(mr, "compile_from_final_graph", _stub)
    (Path(mini_project) / "main" / "answers_logic.json").write_text(
        json.dumps({qid: "material group ST=0.72, highest vs hemo/morpho (data/sobol.csv)"}))
    mr.finalize_and_compile(mini_project, Path(mini_project) / "_out")
    assert mr.final_logic_graph_path(mini_project).is_file()
    # the answered claim now has supporting evidence in the FINAL graph
    fg = compiled["graph"]
    assert any(n.kind == "evidence" for n in fg.nodes)


def test_advance_path_c_unknown_downgrades(mini_project, offline, monkeypatch):
    monkeypatch.setattr(claim_graph, "build_preliminary", lambda ps: _bare_claim_graph())
    (Path(mini_project) / "main" / "answers_requirement.json").write_text("{}")
    res = mr.advance_after_requirement_answers(mini_project)
    qid = res["questions"][0]["id"]

    compiled = {}
    def _stub(pd, out_dir, graph, progress=lambda m: None, litsearch=True):
        compiled["graph"] = graph
        from paperflow.schemas.eval import RunManifest
        return RunManifest(project_dir=pd)
    monkeypatch.setattr(mr, "compile_from_final_graph", _stub)
    (Path(mini_project) / "main" / "answers_logic.json").write_text(json.dumps({qid: "모름"}))
    mr.finalize_and_compile(mini_project, Path(mini_project) / "_out")
    fg = compiled["graph"]
    c = fg.node("C1")
    assert c.role == "downgraded"                    # claim qualified/weakened, not fabricated
    assert not [n for n in fg.nodes if n.kind == "evidence"]  # no invented evidence
    assert (Path(mini_project) / "main" / "research_state_final.json").is_file()
