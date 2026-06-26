"""Stage 1–2: derive search queries from the user's research state, then search OpenAlex and
select 10–20 related papers (deduped, intent-diverse)."""
from __future__ import annotations

import json

from ..litsearch import openalex
from ..llm import client
from ..schemas.literature import LiteraturePaper
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt

_MIN_PAPERS = 6
_MAX_PAPERS = 10


def derive_queries(ps: ProjectState) -> tuple[str, str, list[str]]:
    """Return (study_archetype, field, queries). Falls back to keyword heuristics on error."""
    try:
        raw = client.call_json("fast", prompt("derive_search_queries"), inputs_block(ps),
                               step="lit.queries", max_tokens=900, effort="minimal")
        archetype = str(raw.get("study_archetype", "")).strip()
        field = str(raw.get("field", "")).strip() or ps.journal_info.author_field
        queries = [str(q).strip() for q in (raw.get("queries") or []) if str(q).strip()]
        if queries:
            return archetype, field, queries[:8]
    except Exception:
        pass
    # heuristic fallback: field + core keywords
    kws = list(getattr(ps.core_message, "keywords", []) or [])
    field = ps.journal_info.author_field or ""
    base = [k for k in kws if k][:6] or [field]
    return "", field, [f"{field} {k}".strip() for k in base][:6]


def _content_level(abstract: str) -> str:
    return "abstract_only"   # OpenAlex gives abstracts; full text attached later if available


def search_and_select(queries: list[str], per_query: int = 6,
                      max_papers: int = _MAX_PAPERS) -> list[LiteraturePaper]:
    """Search each query, round-robin interleave for intent diversity, dedup by DOI/title,
    cap at max_papers. Returns [] if OpenAlex yields nothing (caller falls back)."""
    buckets: list[list[dict]] = []
    for q in queries:
        try:
            buckets.append(openalex.search(q, n=per_query) or [])
        except Exception:
            buckets.append([])

    seen: set[str] = set()
    picked: list[dict] = []
    # round-robin across queries keeps the set diverse rather than top-heavy on one query
    depth = max((len(b) for b in buckets), default=0)
    for rank in range(depth):
        for b in buckets:
            if rank >= len(b):
                continue
            w = b[rank]
            ident = (w.get("doi") or w.get("title", "")).strip().lower()
            if not ident or ident in seen:
                continue
            seen.add(ident)
            picked.append(w)
            if len(picked) >= max_papers:
                break
        if len(picked) >= max_papers:
            break

    papers: list[LiteraturePaper] = []
    for i, w in enumerate(picked, 1):
        abstract = (w.get("abstract") or "").strip()
        papers.append(LiteraturePaper(
            paper_id=f"paper_{i:03d}", title=w.get("title", ""), doi=w.get("doi", ""),
            year=w.get("year"), authors=", ".join(w.get("authors", []) or []),
            abstract=abstract, content_level=_content_level(abstract),
            source="openalex", cited_by=int(w.get("cited_by", 0) or 0),
        ))
    return papers


def have_enough(papers: list[LiteraturePaper]) -> bool:
    return len(papers) >= _MIN_PAPERS
