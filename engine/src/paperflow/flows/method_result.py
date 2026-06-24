"""Orchestrate the manuscript pipeline (v2 — reordered):
ingest -> journal guideline -> litsearch -> requirement -> claim graph (typed) ->
figure plan (figure-first) -> draft all sections -> section-level validate ->
reference-hunter (citation fill) -> output.

Each progress() message is prefixed with [step_id] so the web UI can map it to the
workflow tree; the CLI just prints the whole string.
"""
from __future__ import annotations

from pathlib import Path

from ..citation import fill as citation_fill
from ..compile import claim_graph, contracts, validator, writer
from ..figures import plan as figure_plan
from ..ingest import journal_guideline
from ..ingest.parse_inputs import ingest
from ..llm import client
from ..output.write_fs import write_all
from ..requirement import detect
from ..schemas.claim import SectionContract
from ..schemas.eval import RunManifest

# main (grounded in what was done) first, then sub (reference the results' story)
_GEN_ORDER = ["method", "result", "discussion", "introduction", "conclusion", "abstract"]
_ALIAS = {"intro": "introduction", "concl": "conclusion"}

# stable step list for the UI workflow tree (id, label)
STEPS = [
    ("ingest", "입력 수집"),
    ("guideline", "저널 가이드라인"),
    ("litsearch", "선행연구조사"),
    ("requirement", "누락정보 진단"),
    ("claim_graph", "Claim graph"),
    ("figure_plan", "Figure 설계"),
    ("write", "본문 작성"),
    ("validate", "논리 검증"),
    ("citation", "Citation 채우기"),
    ("output", "출력"),
]


def _order(sections: list[str]) -> list[str]:
    norm = [_ALIAS.get(s, s) for s in sections]
    return [s for s in _GEN_ORDER if s in norm] + [s for s in norm if s not in _GEN_ORDER]


def run(project_dir: str, sections: list[str], out_dir: Path,
        progress=lambda msg: None, litsearch: bool = True) -> RunManifest:
    sections = _order(sections)
    manifest = RunManifest(project_dir=project_dir, sections=sections)
    client.set_manifest(manifest)

    progress("[ingest] 입력 수집")
    ps = ingest(project_dir)

    progress("[guideline] 저널 가이드라인 확인")
    ps.journal_constraints = journal_guideline.fetch(ps.journal_info)

    literature_md = ""
    if litsearch:
        progress("[litsearch] 선행연구조사 (OpenAlex)")
        from ..litsearch import run as litrun
        literature_md, found = litrun.run(ps, progress=lambda m: progress(f"[litsearch] {m}"))
        ps.found_references = found
        progress(f"[litsearch] 찾은 논문 {len(found)}편")

    # reuse the diagnose result if the UI already computed it (no second LLM call)
    cached = detect.load_report(project_dir)
    if cached is not None:
        progress("[requirement] 진단 결과 재사용")
        report = cached
    else:
        progress("[requirement] 누락정보 진단 (완성가능성 분류)")
        report = detect.detect(ps)
    manifest.classification = report.classification

    progress("[claim_graph] Claim graph (typed)")
    graph = claim_graph.build(ps)

    progress("[figure_plan] Figure 설계 (figure-first)")
    fig_spec = figure_plan.plan(project_dir, graph)

    # draft every section (no inline validation)
    section_contracts: dict[str, SectionContract] = {}
    section_md: dict[str, str] = {}
    for sec in sections:
        try:
            progress(f"[write] {sec}")
            sc = contracts.build(ps, graph, sec)
            section_contracts[sec] = sc
            section_md[sec] = writer.write_section(ps, graph, sc)
        except Exception as e:  # one section failing must not lose the others
            progress(f"[write] {sec} 실패: {str(e)[:120]}")
            section_md[sec] = f"<!-- generation failed: {str(e)[:200]} -->\n"

    progress("[validate] 섹션별 논리 검증")
    section_md, validation_report = validator.validate_sections(
        graph, section_contracts, section_md, progress=lambda m: progress(f"[validate] {m}"))

    progress("[citation] 누락 citation 채우기 (reference-hunter)")
    section_md, reference_table = citation_fill.fill(
        section_md, progress=lambda m: progress(f"[citation] {m}"))

    progress("[output] 출력 기록")
    paper_meta = {
        "title": ps.journal_info.working_title,
        "authors": ps.journal_info.extra.get("authors", ""),
        "field": ps.journal_info.author_field,
    }
    write_all(out_dir, sections=section_md, graph=graph, contracts=section_contracts,
              requirement=report, figure_spec=fig_spec, manifest=manifest,
              literature_md=literature_md, found_references=ps.found_references,
              reference_table=reference_table, validation_report=validation_report,
              paper_meta=paper_meta)
    return manifest
