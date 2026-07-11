"""Literature-grounded requirement derivation — orchestrator.

Stages (each persisted under main/literature/):
  1 derive search queries          -> search_queries.json
  2 OpenAlex search + select       -> selected_papers.json
  3 attach content level           (in selected_papers.json)
  4 per-paper extraction (parallel)-> paper_XXX.json
  5 normalize/cluster              -> normalized_items.json
  6 synthesize overall schema      -> overall_schema.json
  7 compare against user materials -> requirement_status.json
  8 generate grounded questions    -> grounded_questions.json

Any failure, or too few papers, falls back to the static pack (`fallback.run`). The result
ALWAYS contains a compatible RequirementReport so the generate flow keeps working unchanged.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from ..schemas.literature import LiteraturePaper

from . import (
    compare_user_state, content_retrieval, detect, fallback,
    literature_search, normalize_items, paper_extract, synthesize_schema,
)
from ..schemas.overall_schema import OverallSchema
from ..schemas.project_state import ProjectState
from ..schemas.requirement import CompletionClass, MissingItem, RequirementReport
from ..schemas.requirement_status import GroundedQuestion, RequirementStatus
from ..util import inputs_block


def _litdir(project_dir: str) -> Path:
    d = Path(project_dir) / "main" / "literature"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _dump(project_dir: str, name: str, obj) -> None:
    try:
        (_litdir(project_dir) / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    except Exception:
        pass


def _load_json(path: Path):
    try:
        return json.loads(path.read_text()) if path.is_file() else None
    except Exception:
        return None


def _to_report(study_type: str, questions: list[GroundedQuestion],
               statuses: list[RequirementStatus]) -> tuple[RequirementReport, str, list[str]]:
    """Map grounded questions/statuses to the legacy RequirementReport the generate flow reuses."""
    present = [s.key for s in statuses if s.status == "present"]
    missing = [MissingItem(
        field=q.id, why_it_matters=q.why_asked, reviewer_risk=q.reviewer_risk,
        question=q.question, example=q.expected_answer, priority=q.priority,
    ) for q in questions]
    has_mandatory = any(q.requirement_level == "mandatory" for q in questions)
    if has_mandatory:
        cls = CompletionClass.MISSING_CRITICAL_INFORMATION
    elif questions:
        cls = CompletionClass.EXPERT_REVIEW_REQUIRED
    else:
        cls = CompletionClass.SUBMISSION_READY_DRAFT
    notes = (f"{len(questions)} high-value gaps from {len(statuses)} literature-derived "
             f"requirements; {len(present)} already covered.")
    report = RequirementReport(study_type=study_type, classification=cls,
                               present=present, missing=missing, notes=notes)
    return report, cls.value, present


def _fingerprint(ps: ProjectState) -> str:
    """Hash of the inputs that determine the literature analysis (NOT outline/answers — those
    only affect compare). Same fingerprint -> reuse papers/extraction/normalize/schema."""
    ji, cm = ps.journal_info, ps.core_message
    parts = [
        getattr(ji, "author_field", ""), " ".join(getattr(ji, "target_journals", []) or []),
        getattr(cm, "one_sentence", ""), getattr(cm, "one_paragraph", ""),
        " ".join(getattr(cm, "keywords", []) or []),
        " ".join(getattr(cm, "summary_bullets", []) or []),
        " ".join(ps.reference_keys or []),
    ]
    return hashlib.sha256("\x01".join(parts).encode("utf-8")).hexdigest()[:16]


def _load_lit_cache(project_dir: str, fp: str):
    """Return (schema, archetype, field, papers) if the saved literature analysis matches the
    fingerprint, else None."""
    d = _litdir(project_dir)
    meta = _load_json(d / "_fingerprint.json")
    if not meta or meta.get("fingerprint") != fp:
        return None
    sc_raw = _load_json(d / "overall_schema.json")
    if not sc_raw or not sc_raw.get("requirements"):
        return None
    try:
        schema = OverallSchema.model_validate(sc_raw)
    except Exception:
        return None
    papers = [LiteraturePaper.model_validate(p) for p in (_load_json(d / "selected_papers.json") or [])]
    field = (_load_json(d / "search_queries.json") or {}).get("field", "")
    return schema, schema.study_archetype, field, papers


def run(project_dir: str, ps: ProjectState, progress=lambda m: None) -> dict:
    """Run the literature-grounded pipeline; reuse cached literature analysis when the core
    inputs are unchanged; fall back to the static pack on any failure."""
    project_id = Path(project_dir).name
    try:
        fp = _fingerprint(ps)
        queries: list[str] = []
        cached = _load_lit_cache(project_dir, fp)
        if cached is not None:
            schema, archetype, field, papers = cached
            queries = (_load_json(_litdir(project_dir) / "search_queries.json") or {}).get("queries", [])
            progress(f"[cache] 문헌 분석 재사용 (핵심 입력 동일, 논문 {len(papers)}편)")
        else:
            progress("[field] 연구 분야·archetype 분석")
            archetype, field, queries = literature_search.derive_queries(ps)
            _dump(project_dir, "search_queries.json",
                  {"study_archetype": archetype, "field": field, "queries": queries})

            progress("[search] 관련 문헌 검색 (OpenAlex)")
            papers = literature_search.search_and_select(queries)
            papers = content_retrieval.attach_content(papers, ps)
            if not literature_search.have_enough(papers):
                progress(f"[search] 문헌 부족({len(papers)}편) → static fallback")
                return _finish_fallback(project_dir, ps, f"only {len(papers)} papers found")
            _dump(project_dir, "selected_papers.json", [p.model_dump() for p in papers])
            progress(f"[search] 논문 {len(papers)}편 선정")

            progress("[extract] 논문별 항목 추출")
            extractions = paper_extract.extract_all(papers, progress=lambda m: progress(f"[extract] {m}"))
            for ex in extractions:
                _dump(project_dir, f"{ex.paper_id}.json", ex.model_dump())

            progress("[normalize] 개념 통합 + 레벨 판단 (category별 병렬)")
            clusters = normalize_items.normalize(extractions, inputs_block(ps))
            _dump(project_dir, "normalized_items.json", clusters)
            if not clusters:
                progress("[normalize] 클러스터 없음 → static fallback")
                return _finish_fallback(project_dir, ps, "no clusters from extraction")

            progress("[schema] 프로젝트 schema 합성 (결정적)")
            schema = synthesize_schema.synthesize(clusters, ps, papers, project_id, archetype)
            _dump(project_dir, "overall_schema.json", schema.model_dump())
            _dump(project_dir, "_fingerprint.json", {"fingerprint": fp})

        progress("[compare] 사용자 입력 비교 + 질문 생성 (단일 호출)")
        statuses, questions = compare_user_state.compare_and_question(schema, ps)
        _dump(project_dir, "requirement_status.json", [s.model_dump() for s in statuses])
        _dump(project_dir, "grounded_questions.json", [q.model_dump() for q in questions])

        report, classification, present = _to_report(archetype or field or "research",
                                                      questions, statuses)
        return {
            "requirement_source": "literature_derived",
            "study_archetype": archetype, "field": field, "queries": queries,
            "papers": [p.model_dump() for p in papers],
            "overall_schema": schema, "statuses": statuses, "questions": questions,
            "report": report, "classification": classification,
            "present": present, "notes": report.notes,
        }
    except Exception as e:  # any stage blew up -> never break diagnose; use the static pack
        progress(f"[fallback] literature pipeline 오류 → static ({str(e)[:80]})")
        return _finish_fallback(project_dir, ps, f"pipeline error: {str(e)[:120]}")


def _finish_fallback(project_dir: str, ps: ProjectState, reason: str) -> dict:
    # NEVER fall back silently — record WHY so the literature path can be debugged.
    print(f"[req_pipeline] STATIC FALLBACK for {Path(project_dir).name}: {reason}", file=sys.stderr)
    _dump(project_dir, "_fallback.json", {"requirement_source": "static_fallback", "reason": reason})
    res = fallback.run(ps, reason=reason)
    _dump(project_dir, "overall_schema.json", res["overall_schema"].model_dump())
    _dump(project_dir, "grounded_questions.json", [q.model_dump() for q in res["questions"]])
    _dump(project_dir, "requirement_status.json", [s.model_dump() for s in res["statuses"]])
    return res
