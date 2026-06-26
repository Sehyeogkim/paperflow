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
from ..reconstruct import build_state
from ..requirement import detect
from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.eval import RunManifest
from ..schemas.project_state import FoundRef, ProjectState

# main (grounded in what was done) first, then sub (reference the results' story)
_GEN_ORDER = ["method", "result", "discussion", "introduction", "conclusion", "abstract"]
_ALIAS = {"intro": "introduction", "concl": "conclusion"}

# stable step lists for the UI workflow trees (id, label)
RECONSTRUCT_STEPS = [
    ("ingest", "입력 수집"), ("reconstruct", "연구 상태 복원"),
    ("prelim_graph", "잠정 logic graph"),
]
PLAN_STEPS = [
    ("ingest", "입력 수집"), ("reconstruct", "연구 상태 복원"),
    ("guideline", "저널 가이드라인"), ("litsearch", "선행연구조사"),
    ("requirement", "누락정보 진단"), ("claim_graph", "Claim graph"),
    ("figure_plan", "Figure 설계"), ("structure", "섹션 구조·소제목"),
]
GEN_STEPS = [
    ("write", "본문 작성"), ("validate", "논리 검증"),
    ("citation", "Citation 채우기"), ("output", "출력"),
]
STEPS = PLAN_STEPS + GEN_STEPS  # full pipeline (CLI / back-compat)

_PLAN_FILE = "_plan.json"
_PRELIM_GRAPH_FILE = "_prelim_graph.json"


def prelim_graph_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / _PRELIM_GRAPH_FILE


def load_prelim_graph(project_dir: str) -> ClaimGraph | None:
    p = prelim_graph_path(project_dir)
    if p.is_file():
        try:
            return ClaimGraph.model_validate_json(p.read_text())
        except Exception:
            return None
    return None


def _attach_reconstruction(project_dir: str, ps: ProjectState) -> ProjectState:
    """Load saved reconstruction or build it; attach to ps so the claim graph consumes it."""
    rs, inv = build_state.load(project_dir)
    if rs is None or inv is None:
        rs, inv = build_state.reconstruct(project_dir, ps)
        build_state.save(project_dir, rs, inv)
    ps.research_state, ps.evidence_inventory = rs, inv
    return ps


def preliminary(project_dir: str, progress=lambda m: None) -> dict:
    """Reconstruct study state + build the PRELIMINARY logic graph used to find question
    gaps. The graph build needs an LLM; if unavailable it is skipped (questions then come
    from reconstruction gaps only). Always persists research_state / evidence_inventory."""
    manifest = RunManifest(project_dir=project_dir)
    client.set_manifest(manifest)
    progress("[ingest] 입력 수집")
    ps = ingest(project_dir)
    progress("[reconstruct] 연구 상태 복원")
    rs, inv = build_state.reconstruct(project_dir, ps)
    build_state.save(project_dir, rs, inv)
    ps.research_state, ps.evidence_inventory = rs, inv
    has_graph = False
    try:
        progress("[prelim_graph] 잠정 logic graph 생성")
        graph = claim_graph.build(ps)
        prelim_graph_path(project_dir).write_text(graph.model_dump_json(indent=2))
        has_graph = True
    except Exception as e:
        progress(f"[prelim_graph] 건너뜀 ({str(e)[:80]})")
    return {"research_state": rs.model_dump(), "evidence_inventory": inv.model_dump(),
            "has_graph": has_graph,
            "tokens": {"input": manifest.total_input, "output": manifest.total_output}}


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
    progress("[reconstruct] 연구 상태 복원")
    ps = _attach_reconstruction(project_dir, ps)
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


_DEFAULT_GEN_SECTIONS = ["method", "result", "discussion", "introduction", "conclusion", "abstract"]

# UI workflow trees for the two-stage flow
ADVANCE_STEPS = [("reconstruct", "답변 반영·연구상태 재구성"),
                 ("prelim_graph", "잠정 logic graph"), ("gap_check", "논리 빈틈 검사")]
COMPILE_STEPS = [("finalize", "최종 logic graph"), ("guideline", "저널 가이드라인"),
                 ("litsearch", "선행연구조사"), ("figure_plan", "Figure 설계"),
                 ("structure", "섹션 구조"), ("write", "본문 작성"),
                 ("validate", "논리 검증"), ("citation", "Citation"), ("output", "출력")]


def preliminary_logic_graph_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / "preliminary_logic_graph.json"


def final_logic_graph_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / "final_logic_graph.json"


def graph_gap_report_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / "graph_gap_report.json"


def _load_json(p: Path):
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def _load_requirement_answers(project_dir: str) -> dict:
    """Stage-1 answers (separate store), falling back to the merged answer.json."""
    main = Path(project_dir) / "main"
    d = _load_json(main / "answers_requirement.json")
    if isinstance(d, dict) and d:
        return {str(k): str(v) for k, v in d.items()}
    from ..question import loop as qloop
    return qloop.load_answers(project_dir)


def _load_logic_answers(project_dir: str) -> dict:
    d = _load_json(Path(project_dir) / "main" / "answers_logic.json")
    return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}


def advance_after_requirement_answers(project_dir: str, progress=lambda m: None) -> dict:
    """Stage-1 → rebuild Research State v2, build the Preliminary Logic Graph, validate gaps,
    and decide whether Stage-2 logic questions are needed. (TWO_STAGE_QUESTIONS §11.2)"""
    from ..compile import claim_graph
    from ..graph import logic_questions, validate_gaps
    manifest = RunManifest(project_dir=project_dir)
    client.set_manifest(manifest)

    progress("[reconstruct] 답변 반영해 연구 상태 재구성")
    ps = ingest(project_dir)
    req_answers = _load_requirement_answers(project_dir)
    rs_v2, inv = build_state.reconstruct_after_requirement_answers(project_dir, ps, req_answers)
    ps.research_state, ps.evidence_inventory = rs_v2, inv

    progress("[prelim_graph] 잠정 logic graph 생성")
    graph = claim_graph.build_preliminary(ps)
    graph_json = graph.model_dump_json(indent=2)
    preliminary_logic_graph_path(project_dir).write_text(graph_json)
    prelim_graph_path(project_dir).write_text(graph_json)  # keep legacy /questions endpoint working

    progress("[gap_check] 논리적 빈틈 검사")
    report = validate_gaps.validate(graph)
    graph_gap_report_path(project_dir).write_text(report.model_dump_json(indent=2))

    if report.needs_stage2():
        qs = logic_questions.generate(report, graph)
        (Path(project_dir) / "main" / "questions_logic.json").write_text(
            json.dumps([q.model_dump() for q in qs], ensure_ascii=False, indent=2))
        progress(f"[gap_check] load-bearing gap {len(report.load_bearing_gaps)}개 → 2차 질문")
        return {"next": "logic_questions", "questions": [q.model_dump() for q in qs],
                "gap_report": report.model_dump(),
                "tokens": {"input": manifest.total_input, "output": manifest.total_output}}
    progress("[gap_check] load-bearing gap 없음 → 바로 생성")
    return {"next": "generation", "questions": [], "gap_report": report.model_dump(),
            "tokens": {"input": manifest.total_input, "output": manifest.total_output}}


def auto_plan_from_final_graph(project_dir: str, ps: ProjectState, graph: ClaimGraph,
                               sections: list[str] | None = None, progress=lambda m: None,
                               litsearch: bool = True) -> dict:
    """Build figure plan + section structure from an ALREADY-FINAL graph and persist _plan.json
    (no graph build, no user confirmation). (TWO_STAGE_QUESTIONS §10.3)"""
    sections = _order(sections or _DEFAULT_GEN_SECTIONS)
    progress("[guideline] 저널 가이드라인 확인")
    ps.journal_constraints = journal_guideline.fetch(ps.journal_info)
    literature_md = ""
    if litsearch:
        progress("[litsearch] 선행연구조사 (OpenAlex)")
        from ..litsearch import run as litrun
        literature_md, found = litrun.run(ps, progress=lambda m: progress(f"[litsearch] {m}"))
        ps.found_references = found
    progress("[figure_plan] Figure 설계")
    fig_spec = figure_sketch.attach_sketches(figure_plan.plan(project_dir, graph))
    progress("[structure] 섹션 구조·소제목")
    section_structure = structure.propose(ps, graph, sections)
    out = {
        "sections": sections, "classification": None,
        "main_contribution": graph.main_contribution,
        "claim_graph": graph.model_dump(), "figures": fig_spec,
        "structure": section_structure,
        "found_references": [r.model_dump() for r in ps.found_references],
        "literature_md": literature_md, "auto": True,
    }
    save_plan(project_dir, out)
    return out


def compile_from_final_graph(project_dir: str, out_dir: Path, graph: ClaimGraph,
                             progress=lambda m: None, litsearch: bool = True) -> RunManifest:
    """Auto-plan from the final graph, then draft → validate → cite → export, with NO
    plan-confirmation gate. (TWO_STAGE_QUESTIONS §10)"""
    ps = _attach_reconstruction(project_dir, ingest(project_dir))
    auto_plan_from_final_graph(project_dir, ps, graph, progress=progress, litsearch=litsearch)
    return generate_from_plan(project_dir, out_dir, progress=progress)


def finalize_and_compile(project_dir: str, out_dir: Path, progress=lambda m: None,
                         litsearch: bool = True) -> RunManifest:
    """Stage-2 (or skip) → Final Research State + Final Logic Graph + immediate compilation.
    (TWO_STAGE_QUESTIONS §9-10)"""
    from ..compile import claim_graph
    from ..graph import validate_gaps
    from ..schemas.claim import ClaimGraph as _CG
    from ..schemas.question import Question

    prelim_json = _load_json(preliminary_logic_graph_path(project_dir))
    if prelim_json is None:
        raise RuntimeError("no preliminary logic graph — run advance_after_requirement_answers first")
    prelim = _CG.model_validate(prelim_json)
    logic_qs = [Question.model_validate(q) for q in
                (_load_json(Path(project_dir) / "main" / "questions_logic.json") or [])]
    logic_answers = _load_logic_answers(project_dir)

    progress("[finalize] 최종 logic graph 구성 (답변 반영·미응답 약화)")
    final = claim_graph.build_final(prelim, logic_qs, logic_answers)
    final_logic_graph_path(project_dir).write_text(final.model_dump_json(indent=2))

    rs_v2, _ = build_state.load(project_dir)
    if rs_v2 is not None:
        build_state.finalize_after_logic_answers(project_dir, rs_v2, logic_answers)

    final_validation = validate_gaps.validate(final)
    (Path(project_dir) / "main" / "final_graph_validation.json").write_text(
        final_validation.model_dump_json(indent=2))

    progress("[compile] 논문 생성 시작")
    return compile_from_final_graph(project_dir, out_dir, final, progress=progress,
                                    litsearch=litsearch)


def generate_from_plan(project_dir: str, out_dir: Path, progress=lambda m: None) -> RunManifest:
    """Phase 2 — draft + validate + cite + output, using the CONFIRMED plan (main/_plan.json)."""
    pl = load_plan(project_dir)
    if pl is None:
        raise RuntimeError("no confirmed plan — run plan() first")
    sections = pl["sections"]
    manifest = RunManifest(project_dir=project_dir, sections=sections)
    client.set_manifest(manifest)

    ps = ingest(project_dir)  # cheap, no LLM
    ps = _attach_reconstruction(project_dir, ps)
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

    # build each section's contract (honoring confirmed subheadings) then draft it. Sections are
    # independent, so run them CONCURRENTLY — wall-clock = slowest section, not the sum of 6.
    from concurrent.futures import ThreadPoolExecutor
    section_contracts: dict[str, SectionContract] = {}
    section_md: dict[str, str] = {}

    def _write_one(sec: str):
        try:
            hint = (struct.get(sec) or {}).get("subheadings") or []
            sc = contracts.build(ps, graph, sec, structure_hint=hint)
            md = writer.write_section(ps, graph, sc)
            progress(f"[write] {sec}")
            return sec, sc, md
        except Exception as e:
            progress(f"[write] {sec} 실패: {str(e)[:120]}")
            return sec, None, f"<!-- generation failed: {str(e)[:200]} -->\n"

    with ThreadPoolExecutor(max_workers=min(6, len(sections))) as ex:
        for sec, sc, md in ex.map(_write_one, sections):
            if sc is not None:
                section_contracts[sec] = sc
            section_md[sec] = md

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
    # load-bearing gaps still open at generation time -> recorded as warnings (never a gate)
    from ..question import loop as qloop
    warnings = qloop.warnings_for(load_prelim_graph(project_dir) or graph,
                                  ps.research_state, ps.evidence_inventory,
                                  answered=qloop.load_answers(project_dir))
    write_all(out_dir, sections=section_md, graph=graph, contracts=section_contracts,
              requirement=report, figure_spec=pl.get("figures", {}), manifest=manifest,
              literature_md=pl.get("literature_md", ""), found_references=ps.found_references,
              reference_table=reference_table, validation_report=validation_report,
              paper_meta=_paper_meta(ps), warnings=warnings,
              research_state=ps.research_state, evidence_inventory=ps.evidence_inventory)
    return manifest


def run(project_dir: str, sections: list[str], out_dir: Path,
        progress=lambda msg: None, litsearch: bool = True) -> RunManifest:
    """One-shot (CLI): plan then generate, no confirmation pause."""
    plan(project_dir, sections, progress=progress, litsearch=litsearch)
    return generate_from_plan(project_dir, out_dir, progress=progress)
