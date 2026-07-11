"""Step 2 — deterministic profiling + research-state / evidence-inventory reconstruction."""
from pathlib import Path

import openpyxl

from paperflow.ingest.parse_inputs import ingest
from paperflow.reconstruct import build_state, profile_data


def test_profile_csv_dtypes_and_ranges(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("group,S1,ST\nmaterial,0.61,0.72\nhemo,0.21,0.28\n")
    prof = profile_data.profile_csv(p)
    assert prof["rows"] == 2
    assert prof["columns"] == {"group": "text", "S1": "float", "ST": "float"}
    assert prof["numeric_ranges"]["S1"] == [0.21, 0.61]
    assert prof["sample_row"]["group"] == "material"


def test_profile_xlsx(tmp_path):
    p = tmp_path / "y.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["a", "b"])
    ws.append([1, 2])
    ws.append([3, 4])
    wb.save(p)
    prof = profile_data.profile_xlsx(p)
    assert "Sheet1" in prof["sheets"]
    assert prof["sheets"]["Sheet1"]["rows"] == 2
    assert prof["sheets"]["Sheet1"]["columns"] == {"a": "int", "b": "int"}


def test_profile_file_dispatch(tmp_path):
    (tmp_path / "a.csv").write_text("c\n1\n")
    (tmp_path / "b.md").write_text("# hi\nbody\n")
    assert profile_data.profile_file(tmp_path / "a.csv")["kind"] == "csv"
    assert profile_data.profile_file(tmp_path / "b.md")["kind"] == "text"
    assert profile_data.profile_file(tmp_path / "missing.pdf")["error"] == "not_found"


def test_evidence_inventory_roles_and_columns(mini_project):
    ps = ingest(mini_project)
    inv = build_state.build_evidence_inventory(mini_project, ps)
    sobol = inv.by_path("data/sobol/sobol_grp_LAP.csv")
    assert sobol is not None
    assert sobol.user_description == "group-level Sobol sensitivity result"
    assert sobol.inferred_role == "global sensitivity result"
    assert sobol.unit_of_analysis == "input-variable group"
    assert sobol.columns == {"group": "text", "S1": "float", "ST": "float"}
    inp = inv.by_path("data/input_parameter/input.csv")
    assert inp.inferred_role == "input design space"


def test_research_state_skeleton_offline(mini_project):
    ps = ingest(mini_project)
    rs, inv = build_state.reconstruct(mini_project, ps, use_llm=False)
    assert rs.source == "skeleton"
    assert rs.primary_message == "Material properties dominate rupture risk."
    assert "Material > Hemo > Morpho" in rs.possible_claims
    # outline skeleton claims also become candidate claims
    assert any("Material factors dominate" in c for c in rs.possible_claims)
    assert rs.known_references == []
    # input variables lifted from the input-design-space file columns
    assert "E_vessel" in rs.input_variables and "SBP" in rs.input_variables
    # datasets recorded with role
    assert any(d.role == "global sensitivity result" for d in rs.datasets)
    # inferential fields the skeleton couldn't fill are flagged as unknowns
    assert "study_type" in rs.unknowns and "study_design" in rs.unknowns


def test_save_and_load_roundtrip(mini_project):
    ps = ingest(mini_project)
    rs, inv = build_state.reconstruct(mini_project, ps, use_llm=False)
    build_state.save(mini_project, rs, inv)
    assert (Path(mini_project) / "main" / "research_state.json").is_file()
    rs2, inv2 = build_state.load(mini_project)
    assert rs2 == rs
    assert inv2 == inv


def test_ingest_tolerates_missing_optional_outline(mini_project):
    """Minimal-input mode: removing the optional outline must not break ingest/reconstruct."""
    from pathlib import Path as _P
    (_P(mini_project) / "main" / "3_outline.md").unlink()
    ps = ingest(mini_project)               # must not raise
    assert ps.outline.skeleton == []
    assert ps.core_message.one_sentence     # core message still parsed
    rs, inv = build_state.reconstruct(mini_project, ps, use_llm=False)
    assert rs.primary_message               # research state still built from data + core msg
    assert len(inv.assets) == 2


def test_reconstruct_demo_project(demo_dir):
    """The real demo (9 CSVs) reconstructs without error, fully offline."""
    rs, inv = build_state.reconstruct(demo_dir, use_llm=False)
    assert len(inv.assets) >= 9
    # demo's sobol group files get the group unit of analysis
    grp = [a for a in inv.assets if "sobol_grp" in a.path]
    assert grp and all(a.unit_of_analysis == "input-variable group" for a in grp)
    assert rs.primary_message  # core message lifted
