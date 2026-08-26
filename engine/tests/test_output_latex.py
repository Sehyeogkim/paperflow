import csv

from paperflow.output import data_artifacts, latex
from paperflow.output.write_fs import _compile_pdf, write_all
from paperflow.schemas.claim import ClaimGraph
from paperflow.schemas.eval import RunManifest
from paperflow.schemas.requirement import CompletionClass, RequirementReport


def _csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_materialize_combines_homomorphic_sobol_csvs_into_two_numbered_tables(tmp_path):
    data = tmp_path / "data" / "uploads"
    _csv(data / "aaaaaaaa_sobol_grp_lap_vi1.csv", ["group", "S1", "ST"], [
        {"group": "Material", "S1": "0.50", "ST": "0.60"},
    ])
    _csv(data / "bbbbbbbb_sobol_grp_cp_vi2.csv", ["group", "S1", "ST"], [
        {"group": "Material", "S1": "0.80", "ST": "0.84"},
    ])
    _csv(data / "cccccccc_sobol_ind_lap_vi1.csv",
         ["parameter", "display_name", "S1", "ST"], [
             {"parameter": "E_fc", "display_name": "$E_{fc}$", "S1": "0.09", "ST": "0.14"},
         ])
    _csv(data / "dddddddd_sobol_ind_cp_vi2.csv",
         ["parameter", "display_name", "S1", "ST"], [
             {"parameter": "E_fc", "display_name": "$E_{fc}$", "S1": "0.63", "ST": "0.64"},
         ])

    artifacts = data_artifacts.materialize(tmp_path)

    assert [artifact.key for artifact in artifacts] == ["sobol_group", "sobol_individual"]
    assert artifacts[0].total_rows == 2
    assert artifacts[1].total_rows == 2
    assert artifacts[0].source_paths == (
        "data/uploads/aaaaaaaa_sobol_grp_lap_vi1.csv",
        "data/uploads/bbbbbbbb_sobol_grp_cp_vi2.csv",
    )
    assert r"\label{tab:sobol-group}" in artifacts[0].latex
    assert r"\label{tab:sobol-individual}" in artifacts[1].latex
    assert "$E_{fc}$" in artifacts[1].latex
    assert "LAP & VI1 & Material & 0.5000 & 0.6000 & 0.1000" in artifacts[0].latex


def test_materialize_groups_generic_csvs_when_column_order_differs(tmp_path):
    data = tmp_path / "data"
    _csv(data / "first.csv", ["sample", "value"], [{"sample": "A_1", "value": "3"}])
    _csv(data / "second.csv", ["value", "sample"], [{"sample": "B&2", "value": "4"}])

    artifacts = data_artifacts.materialize(tmp_path)

    assert len(artifacts) == 1
    assert artifacts[0].key == "csv_schema_1"
    assert artifacts[0].source_paths == ("data/first.csv", "data/second.csv")
    assert artifacts[0].total_rows == 2
    assert r"A\_1" in artifacts[0].latex
    assert r"B\&2" in artifacts[0].latex


def test_assemble_places_materialized_tables_after_results_and_keeps_old_api():
    sections = {
        "abstract": "Summary.",
        "result": "Measured response (Table 1).",
        "discussion": "Interpretation.",
    }
    table = r"\begin{longtable}{lr}\caption{Measured data}\\ A & 1\\\end{longtable}"

    without_data = latex.assemble(sections)
    with_data = latex.assemble(sections, data_artifacts=table)

    assert table not in without_data
    assert with_data.index(r"\section{Results}") < with_data.index(table)
    assert with_data.index(table) < with_data.index(r"\section{Discussion}")
    assert r"\usepackage{longtable}" in with_data


def test_write_all_persists_table_manifest_and_returns_quality_report(tmp_path, monkeypatch):
    _csv(tmp_path / "data" / "sobol_grp_lap_vi1.csv", ["group", "S1", "ST"], [
        {"group": "Material", "S1": "0.5", "ST": "0.6"},
    ])
    out = tmp_path / "out"
    monkeypatch.setattr("paperflow.output.write_fs._compile_pdf", lambda *_args, **_kwargs: False)

    report = write_all(
        out,
        sections={"result": "The sensitivity estimates are reported in Table 1."},
        graph=ClaimGraph(), contracts={},
        requirement=RequirementReport(
            study_type="test", classification=CompletionClass.SUBMISSION_READY_DRAFT),
        figure_spec={}, manifest=RunManifest(project_dir=str(tmp_path)),
    )

    assert report["ok"]
    assert (out / "data_tables.tex").is_file()
    assert (out / "data_artifact_manifest.json").is_file()
    assert (out / "manuscript_quality.json").is_file()
    assert r"\begin{longtable}" in (out / "paper.tex").read_text()


def test_compile_pdf_removes_stale_pdf_when_no_engine_is_available(tmp_path, monkeypatch):
    (tmp_path / "paper.tex").write_text("new manuscript")
    stale = tmp_path / "paper.pdf"
    stale.write_bytes(b"old pdf")
    monkeypatch.setattr("paperflow.output.write_fs.shutil.which", lambda _name: None)

    assert _compile_pdf(tmp_path) is False
    assert not stale.exists()
