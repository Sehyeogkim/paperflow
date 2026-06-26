"""Step 4 — research_state + evidence_inventory flow into inputs_block (the LLM prefix),
and legacy mode (no reconstruction) is byte-for-byte unchanged."""
from paperflow.ingest.parse_inputs import ingest
from paperflow.reconstruct import build_state
from paperflow.util import inputs_block


def test_legacy_inputs_block_unchanged(mini_project):
    """With no reconstruction state on disk, inputs_block must not render the new blocks."""
    ps = ingest(mini_project)
    assert ps.research_state is None and ps.evidence_inventory is None
    block = inputs_block(ps)
    assert "RESEARCH STATE" not in block
    assert "EVIDENCE INVENTORY" not in block
    assert "## CORE MESSAGE" in block  # legacy content intact


def test_inputs_block_includes_reconstruction(mini_project):
    ps = ingest(mini_project)
    rs, inv = build_state.reconstruct(mini_project, ps, use_llm=False)
    ps.research_state, ps.evidence_inventory = rs, inv
    block = inputs_block(ps)
    assert "RESEARCH STATE (reconstructed" in block
    assert "EVIDENCE INVENTORY" in block
    assert "Material properties dominate rupture risk." in block
    assert "global sensitivity result" in block
    # column hints surfaced for grounding
    assert "E_vessel" in block


def test_ingest_loads_saved_reconstruction(mini_project):
    """After build_state.save(), a fresh ingest() picks the reconstruction up (no LLM)."""
    ps = ingest(mini_project)
    rs, inv = build_state.reconstruct(mini_project, ps, use_llm=False)
    build_state.save(mini_project, rs, inv)
    ps2 = ingest(mini_project)
    assert ps2.research_state is not None
    assert ps2.evidence_inventory is not None
    assert ps2.research_state.primary_message == rs.primary_message
