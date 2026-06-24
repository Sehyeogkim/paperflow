"""Orchestrate the manuscript pipeline (v3 — split into PLAN and GENERATE around a human
confirmation checkpoint):

  PLAN     : ingest -> guideline -> litsearch -> requirement -> claim graph (typed) ->
             figure plan (figure-first) -> contracts (per-section, with subheadings).
             Saves main/_plan.json. The user reviews/edits this via chat (Stage 3).
  GENERATE : load the confirmed plan -> draft sections -> section-level validate ->
             reference-hunter -> output (elsarticle .tex + PDF).

run() = plan() + generate_from_plan() for CLI / one-shot use.
Each progress() message is prefixed with [step_id] so the web UI maps it to the workflow tree.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..citation import fill as citation_fill
from ..compile import claim_graph, contracts, structure, validator, writer
from ..figures import plan as figure_plan
from ..figures import sketch as figure_sketch
from ..ingest import journal_guideline
from ..ingest.parse_inputs import ingest
from ..llm import client
from ..output.write_fs import write_all
from ..requirement import detect
from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.eval import RunManifest
from ..schemas.project_state import FoundRef, ProjectState

# main (grounded in what was done) first, then sub (reference the results' story)
_GEN_ORDER = ["method", "result", "discussion", "introduction", "conclusion", "abstract"]
_ALIAS = {"intro": "introduction", "concl": "conclusion"}

# stable step lists for the UI workflow trees (id, label)
PLAN_STEPS = [
    ("ingest", "입력 수집"), ("guideline", "저널 가이드라인"), ("litsearch", "선행연구조사"),
    ("requirement", "누락정보 진단"), ("claim_graph", "Claim graph"),
    ("figure_plan", "Figure 설계"), ("structure", "섹션 구조·소제목"),
]
GEN_STEPS = [
    ("write", "본문 작성"), ("validate", "논리 검증"),
    ("citation", "Citation 채우기"), ("output", "출력"),
]
STEPS = PLAN_STEPS + GEN_STEPS  # full pipeline (CLI / back-compat)

_PLAN_FILE = "_plan.json"


def _order(sections: list[str]) -> list[str]:
    norm = [_ALIAS.get(s, s) for s in sections]
    return [s for s in _GEN_ORDER if s in norm] + [s for s in norm if s not in _GEN_ORDER]


def _plan_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / _PLAN_FILE


def load_plan(project_dir: str) -> dict | None:
    p = _plan_path(project_dir)
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def save_plan(project_dir: str, plan: dict) -> None:
    p = _plan_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=2))


def _paper_meta(ps: ProjectState) -> dict:
    ji = ps.journal_info
    jline = (ji.target_journals.splitlines() or [""])[0]
    jname = jline.lstrip("0123456789. )").split(" — ")[0].split(" http")[0].strip()
    return {
        "title": ji.working_title,
        "authors": ji.extra.get("authors", ""),
        "corresponding": ji.extra.get("corresponding author", "") or ji.extra.get("corresponding", ""),
        "affiliation": ji.extra.get("affiliation", "") or ji.author_field,
        "field": ji.author_field,
        "journal": jname,
        "keywords": ps.core_message.keywords,
    }


def plan(project_dir: str, sections: list[str], progress=lambda m: None,
         litsearch: bool = True) -> dict:
    """Phase 1 — build the structure the user confirms: claim graph + figures + per-section
    contracts (with inferred subheadings). Persists main/_plan.json and returns it."""
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

    cached = detect.load_report(project_dir)
    if cached is not None:
        progress("[requirement] 진단 결과 재사용")
        report = cached
    else:
        progress("[requirement] 누락정보 진단 (완성가능성 분류)")
        report = detect.detect(ps)
        detect.save_report(project_dir, report)

    progress("[claim_graph] Claim graph (typed)")
    graph = claim_graph.build(ps)
    progress("[figure_plan] Figure 설계 (figure-first)")
    fig_spec = figure_plan.plan(project_dir, graph)
    fig_spec = figure_sketch.attach_sketches(fig_spec)  # SVG previews for the confirm step

    progress("[structure] 섹션 구조·소제목 제안")
    section_structure = structure.propose(ps, graph, sections)

    out = {
        "sections": sections,
        "classification": report.classification.value if report.classification else None,
        "main_contribution": graph.main_contribution,
        "claim_graph": graph.model_dump(),
        "figures": fig_spec,
        "structure": section_structure,          # {section: {summary, subheadings}} — user-editable
        "found_references": [r.model_dump() for r in ps.found_references],
        "literature_md": literature_md,
        "plan_tokens": {"input": manifest.total_input, "output": manifest.total_output,
                        "cached": manifest.total_cached},
    }
    save_plan(project_dir, out)
    return out


def generate_from_plan(project_dir: str, out_dir: Path, progress=lambda m: None) -> RunManifest:
    """Phase 2 — draft + validate + cite + output, using the CONFIRMED plan (main/_plan.json)."""
    pl = load_plan(project_dir)
    if pl is None:
        raise RuntimeError("no confirmed plan — run plan() first")
    sections = pl["sections"]
    manifest = RunManifest(project_dir=project_dir, sections=sections)
    client.set_manifest(manifest)

    ps = ingest(project_dir)  # cheap, no LLM
    ps.journal_constraints = journal_guideline.fetch(ps.journal_info)
    ps.found_references = [FoundRef(**r) for r in pl.get("found_references", [])]
    graph = ClaimGraph.model_validate(pl["claim_graph"])
    struct = pl.get("structure", {})
    if pl.get("classification"):
        from ..schemas.requirement import CompletionClass
        try:
            manifest.classification = CompletionClass(pl["classification"])
        except ValueError:
            pass

    # build each section's contract honoring the CONFIRMED subheadings, then draft it
    section_contracts: dict[str, SectionContract] = {}
    section_md: dict[str, str] = {}
    for sec in sections:
        try:
            progress(f"[write] {sec}")
            hint = (struct.get(sec) or {}).get("subheadings") or []
            sc = contracts.build(ps, graph, sec, structure_hint=hint)
            section_contracts[sec] = sc
            section_md[sec] = writer.write_section(ps, graph, sc)
        except Exception as e:
            progress(f"[write] {sec} 실패: {str(e)[:120]}")
            section_md[sec] = f"<!-- generation failed: {str(e)[:200]} -->\n"

    progress("[validate] 섹션별 논리 검증")
    section_md, validation_report = validator.validate_sections(
        graph, section_contracts, section_md, progress=lambda m: progress(f"[validate] {m}"))

    progress("[citation] 누락 citation 채우기 (reference-hunter)")
    section_md, reference_table = citation_fill.fill(
        section_md, progress=lambda m: progress(f"[citation] {m}"))

    progress("[output] 출력 기록")
    from ..schemas.requirement import RequirementReport
    report = detect.load_report(project_dir) or RequirementReport(
        study_type="", classification=manifest.classification)
    write_all(out_dir, sections=section_md, graph=graph, contracts=section_contracts,
              requirement=report, figure_spec=pl.get("figures", {}), manifest=manifest,
              literature_md=pl.get("literature_md", ""), found_references=ps.found_references,
              reference_table=reference_table, validation_report=validation_report,
              paper_meta=_paper_meta(ps))
    return manifest


def run(project_dir: str, sections: list[str], out_dir: Path,
        progress=lambda msg: None, litsearch: bool = True) -> RunManifest:
    """One-shot (CLI): plan then generate, no confirmation pause."""
    plan(project_dir, sections, progress=progress, litsearch=litsearch)
    return generate_from_plan(project_dir, out_dir, progress=progress)
