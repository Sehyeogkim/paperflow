from paperflow.compile import manuscript_quality


def _codes(report):
    return {finding["code"] for finding in report["findings"]}


def test_quality_gate_blocks_internal_ids_placeholders_failed_sections_and_dangling_artifacts():
    sections = {
        "abstract": "Result follows M1, C1.1, and F1 (Tables 1 and 2; Fig. 3).",
        "method": "Kernel choice (DEC_GPR_HYPERPARAMS). [DATA_NEEDED: sample count]",
        "result": "<!-- generation failed: timeout -->",
    }
    latex_text = r"\begin{longtable}{ll} A & B\\\end{longtable}"

    report = manuscript_quality.inspect(sections, latex_text)

    assert not report["ok"]
    assert report["blocking_count"] == len(report["findings"])
    assert {
        "internal_graph_id", "unresolved_placeholder", "failed_section",
        "dangling_table_reference", "dangling_figure_reference",
    }.issubset(_codes(report))
    dangling = next(f for f in report["findings"]
                    if f["code"] == "dangling_table_reference")
    assert dangling["matches"] == ["Table 2"]


def test_quality_gate_blocks_citations_without_bibliography_or_specific_entry():
    sections = {"introduction": "Established previously [cite: alpha2020, beta2021]."}

    no_bib = manuscript_quality.validate_manuscript(sections, "")
    partial_bib = manuscript_quality.inspect(
        sections,
        r"\cite{alpha2020,beta2021}\begin{thebibliography}{9}"
        r"\bibitem{alpha2020} Alpha.\end{thebibliography}",
    )

    assert "citation_without_bibliography" in _codes(no_bib)
    assert "citation_without_entry" in _codes(partial_bib)
    missing = next(f for f in partial_bib["findings"] if f["code"] == "citation_without_entry")
    assert missing["matches"] == ["beta2021"]


def test_quality_gate_accepts_resolved_tables_figures_and_citations():
    sections = {
        "result": "Values are reported in Table 2 and Figure 1 [cite: alpha2020].",
        "discussion": "The evidence supports the interpretation [cite: alpha2020].",
    }
    latex_text = "\n".join([
        r"\begin{longtable}{ll}\end{longtable}",
        r"\begin{table}\end{table}",
        r"\begin{figure}\end{figure}",
        r"\cite{alpha2020}",
        r"\begin{thebibliography}{9}\bibitem{alpha2020} Alpha.\end{thebibliography}",
    ])

    report = manuscript_quality.inspect(sections, latex_text)

    assert report["ok"]
    assert report["findings"] == []
    assert report["metrics"] == {
        "sections": 2,
        "materialized_tables": 2,
        "materialized_figures": 1,
        "citations": 1,
        "bibliography_entries": 1,
    }


def test_quality_gate_requires_resolved_citations_in_intro_and_discussion():
    sections = {
        "introduction": "Prior work motivates this study.",
        "discussion": "The findings should be interpreted cautiously.",
    }

    report = manuscript_quality.inspect(sections, "")

    findings = [f for f in report["findings"] if f["code"] == "missing_section_citations"]
    assert {f["section"] for f in findings} == {"introduction", "discussion"}
