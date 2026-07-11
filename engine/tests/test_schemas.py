"""Step 1 — new canonical-state schemas round-trip with safe defaults."""
from paperflow.schemas.research_state import Dataset, ResearchState
from paperflow.schemas.evidence_inventory import EvidenceAsset, EvidenceInventory


def test_research_state_defaults_and_roundtrip():
    rs = ResearchState()
    assert rs.study_type == ""
    assert rs.methods == [] and rs.datasets == []
    assert rs.source == "skeleton"
    # round-trip through JSON keeps structure
    rs2 = ResearchState.model_validate_json(rs.model_dump_json())
    assert rs2 == rs


def test_research_state_populated():
    rs = ResearchState(
        study_type="computational_biomechanics",
        primary_message="material properties dominate rupture risk",
        datasets=[Dataset(name="sobol", path="data/sobol/x.csv", role="sensitivity result")],
        possible_claims=["Material > Hemo > Morpho"],
        source="llm_enriched",
    )
    assert rs.datasets[0].path == "data/sobol/x.csv"
    assert rs.source == "llm_enriched"
    assert ResearchState.model_validate(rs.model_dump()) == rs


def test_evidence_inventory_by_path():
    inv = EvidenceInventory(assets=[
        EvidenceAsset(path="data/a.csv", kind="csv", user_description="design space",
                      columns={"E_fc": "float"}),
        EvidenceAsset(path="data/b.csv", kind="csv"),
    ])
    assert inv.by_path("data/a.csv").user_description == "design space"
    assert inv.by_path("data/a.csv").columns == {"E_fc": "float"}
    assert inv.by_path("missing") is None
    assert EvidenceInventory.model_validate(inv.model_dump()) == inv
