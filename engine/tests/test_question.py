"""Step 3 — graph-gap detection, ranking, adaptive batching, no hard gate."""
from paperflow.schemas.claim import ClaimGraph, GEdge, GNode
from paperflow.schemas.evidence_inventory import EvidenceAsset, EvidenceInventory
from paperflow.schemas.research_state import ResearchState
from paperflow.question import gaps as gaps_mod
from paperflow.question import loop, rank


def _graph() -> ClaimGraph:
    """C1 fully grounded; C2 bare; E1 has provenance; E2 has none."""
    nodes = [
        GNode(id="C1", kind="claim", text="Material dominates rupture risk"),
        GNode(id="C2", kind="claim", text="Amplitude stress is clinically better"),
        GNode(id="E1", kind="evidence", text="Material group ST=0.72"),
        GNode(id="E2", kind="evidence", text="orphan observation"),
        GNode(id="M1", kind="method", text="Sobol analysis"),
        GNode(id="W1", kind="warrant", text="stress causes rupture"),
        GNode(id="W2", kind="warrant", text="idealized-model scope"),
    ]
    edges = [
        GEdge(id="L1", src="E1", dst="C1", rel="supports"),
        GEdge(id="L2", src="M1", dst="E1", rel="produces"),
        GEdge(id="L3", src="W1", dst="C1", rel="justifies"),
        GEdge(id="L4", src="W2", dst="C1", rel="qualifies"),
    ]
    return ClaimGraph(nodes=nodes, edges=edges)


def test_detect_graph_gaps():
    found = gaps_mod.detect(_graph())
    kinds = sorted((g.kind, g.target_id) for g in found)
    assert ("claim_without_evidence", "C2") in kinds
    assert ("claim_without_warrant", "C2") in kinds
    assert ("claim_without_qualifier", "C2") in kinds
    assert ("evidence_without_provenance", "E2") in kinds
    # C1 is fully grounded -> no C1 gaps
    assert not any(g.target_id == "C1" for g in found)
    # load-bearing flagged correctly
    lb = {g.kind for g in found if g.load_bearing}
    assert lb == {"claim_without_evidence", "evidence_without_provenance"}


def test_missing_primary_claim_when_no_graph():
    found = gaps_mod.detect(None, ResearchState(primary_message="X"))
    assert found[0].kind == "missing_primary_claim"
    assert found[0].load_bearing


def test_ranking_order():
    ranked = rank.rank(gaps_mod.detect(_graph()))
    # claim_without_evidence (7.5) outranks evidence_without_provenance (5.5) outranks the rest
    assert ranked[0].gap_kind == "claim_without_evidence"
    assert ranked[1].gap_kind == "evidence_without_provenance"
    assert ranked[0].value > ranked[1].value


def test_next_batch_is_variable_and_adaptive():
    g = _graph()
    b1 = loop.next_batch(g, batch_size=2)
    assert len(b1.questions) == 2
    assert b1.remaining == 2
    assert b1.terminated is False           # load-bearing gaps still open
    assert b1.warnings                       # surfaced, not blocking

    # answer ONLY the load-bearing questions -> loop terminates even with non-LB gaps left
    answered = {q.id: "answered" for q in b1.questions if q.load_bearing}
    b2 = loop.next_batch(g, answered=answered, batch_size=2)
    assert b2.terminated is True
    assert b2.warnings == []
    # non-load-bearing questions still offered (variable count, not forced)
    assert all(not q.load_bearing for q in b2.questions)


def test_data_meaning_and_research_unknown_gaps():
    inv = EvidenceInventory(assets=[
        EvidenceAsset(path="data/x.csv", kind="csv", user_description=""),     # undescribed
        EvidenceAsset(path="data/y.csv", kind="csv", user_description="known"),
    ])
    rs = ResearchState(unknowns=["study_design"])
    found = gaps_mod.detect(_graph(), rs, inv)
    assert any(g.kind == "data_meaning_unknown" and g.target_id == "data/x.csv" for g in found)
    assert not any(g.target_id == "data/y.csv" for g in found)
    assert any(g.kind == "research_unknown" and g.target_id == "study_design" for g in found)


def test_answers_merge_and_warnings(tmp_path):
    pdir = str(tmp_path)
    (tmp_path / "main").mkdir()
    loop.save_answers(pdir, {"a": "1", "b": ""})       # empty dropped
    merged = loop.save_answers(pdir, {"c": "3"})        # merges, not overwrites
    assert merged == {"a": "1", "c": "3"}
    assert loop.load_answers(pdir) == {"a": "1", "c": "3"}

    g = _graph()
    warn = loop.warnings_for(g)
    assert any("claim_without_evidence" in w for w in warn)
    # answering the load-bearing ids clears the warnings
    ids = {q.id: "x" for q in rank.rank(gaps_mod.detect(g)) if q.load_bearing}
    assert loop.warnings_for(g, answered=ids) == []
