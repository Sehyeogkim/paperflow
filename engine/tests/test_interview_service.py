import pytest

from paperflow.interview import answer_question, audit_graph, start_interview
from paperflow.schemas.claim import ClaimGraph


def graph_fixture() -> ClaimGraph:
    return ClaimGraph.model_validate({
        "revision": 2,
        "main_contribution": "A grounded contribution",
        "nodes": [
            {"id": "C1", "kind": "claim", "text": "main claim"},
            {"id": "E1", "kind": "evidence", "text": "measured improvement"},
            {"id": "M1", "kind": "method", "text": "analysis"},
            {"id": "D1", "kind": "data", "text": "parameter file", "provenance": "data/x.csv"},
            {"id": "TH1", "kind": "threshold", "text": "parameter value",
             "layer": "tacit", "knowledge_status": "missing", "risk": "high",
             "question": "Why this value?", "must_capture": ["decision_rule", "signal"]},
            {"id": "PF1", "kind": "pitfall", "text": "analysis failure",
             "layer": "tacit", "knowledge_status": "missing", "risk": "medium",
             "question": "How do you detect failure?"},
        ],
        "edges": [
            {"id": "L1", "src": "M1", "dst": "E1", "rel": "produces",
             "grounding_status": "grounded"},
            {"id": "L2", "src": "E1", "dst": "C1", "rel": "supports",
             "grounding_status": "grounded"},
            {"id": "L3", "src": "M1", "dst": "D1", "rel": "uses",
             "grounding_status": "grounded"},
            {"id": "L4", "src": "TH1", "dst": "D1", "rel": "governs",
             "grounding_status": "missing"},
            {"id": "L5", "src": "PF1", "dst": "M1", "rel": "warns_about",
             "grounding_status": "missing"},
        ],
    })


def test_complete_answer_is_append_only_and_localizes_patch():
    graph = graph_fixture()
    state = start_interview(graph)
    assert [q.id for q in state.pending_questions()] == ["Q-TH1", "Q-PF1"]

    result = answer_question(
        graph, state, question_id="Q-TH1",
        answer="We compare the measured peak width; drift is the failure signal.",
        captured_fields={"decision_rule": "compare measured peak width", "signal": "drift"},
        completion="complete", base_revision=2,
    )

    assert result.graph.revision == 3
    assert graph.revision == 2  # original graph remains unchanged
    assert state.answers == []  # original state remains append-only/unchanged
    assert result.answer_event.id == "ANS-0001"
    assert result.state.answers == [result.answer_event]
    assert result.graph.node("TH1").knowledge_status == "author_attested"
    assert result.graph.node("TH1").last_modified_revision == 3
    assert result.graph.node("PF1").knowledge_status == "missing"
    assert result.graph.node("TH1").provenance_refs[0].source_type == "author"
    assert result.graph.edges_out("TH1")[0].grounding_status == "grounded"
    assert result.graph.edges_out("PF1")[0].grounding_status == "missing"
    assert result.next_question.id == "Q-PF1"
    assert result.audit.ok is True  # remaining medium-risk gap is a warning, not a blocker


def test_partial_answer_creates_targeted_followup_and_keeps_graph_partial():
    graph = graph_fixture()
    state = start_interview(graph)

    result = answer_question(
        graph, state, question_id="Q-TH1", answer="We compare peak width.",
        captured_fields={"decision_rule": "compare peak width"},
        completion="partial", base_revision=2,
    )

    followup = result.next_question
    assert result.graph.node("TH1").knowledge_status == "partial"
    assert result.graph.edges_out("TH1")[0].grounding_status == "partial"
    assert followup.followup_of == "Q-TH1"
    assert followup.must_capture == ["signal"]
    assert "signal" in followup.text


def test_stale_revision_and_double_answer_are_rejected():
    graph = graph_fixture()
    state = start_interview(graph)

    with pytest.raises(ValueError, match="stale interview turn"):
        answer_question(graph, state, question_id="Q-TH1", answer="x",
                        completion="complete", base_revision=1)

    first = answer_question(graph, state, question_id="Q-TH1", answer="first",
                            completion="complete", base_revision=2)
    with pytest.raises(ValueError, match="already answered"):
        answer_question(first.graph, first.state, question_id="Q-TH1", answer="overwrite",
                        completion="complete", base_revision=3)

    corrected = answer_question(
        first.graph, first.state, question_id="Q-TH1", answer="corrected canonical answer",
        completion="complete", base_revision=3,
        supersedes_answer_id=first.answer_event.id,
    )
    assert len(corrected.state.answers) == 2
    assert corrected.state.answers[0].text == "first"
    assert corrected.answer_event.supersedes_answer_id == "ANS-0001"
    assert corrected.graph.node("TH1").detail == "corrected canonical answer"


def test_audit_blocks_unknown_high_risk_and_feed_cycle():
    raw = graph_fixture().model_dump()
    raw["nodes"].append({"id": "M2", "kind": "method", "text": "second"})
    raw["edges"].extend([
        {"id": "L6", "src": "M1", "dst": "M2", "rel": "feeds"},
        {"id": "L7", "src": "M2", "dst": "M1", "rel": "feeds"},
    ])
    graph = ClaimGraph.model_validate(raw)

    report = audit_graph(graph)

    assert report.ok is False
    codes = [finding.code for finding in report.findings]
    assert "tacit.unresolved" in codes
    assert "pipeline.cycle" in codes


def test_audit_rejects_unverified_or_disconnected_evidence_origin():
    graph = ClaimGraph.model_validate({
        "nodes": [
            {"id": "C1", "kind": "claim", "text": "claim"},
            {"id": "E1", "kind": "evidence", "text": "result"},
            {"id": "M1", "kind": "method", "text": "analysis"},
            {"id": "D1", "kind": "data", "text": "missing data",
             "provenance": "[DATA_NEEDED]"},
        ],
        "edges": [
            {"id": "L1", "src": "M1", "dst": "E1", "rel": "produces",
             "grounding_status": "unverified"},
            {"id": "L2", "src": "E1", "dst": "C1", "rel": "supports",
             "grounding_status": "unverified"},
        ],
    })
    report = audit_graph(graph)
    assert report.ok is False
    assert "claim.no_grounded_evidence" in [f.code for f in report.findings]
