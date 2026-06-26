"""Stage 7: per-paper open-ended item extraction (parallel).

One LLM call per paper. Top-level category is fixed (universal); item names are free.
Abstract-only papers are restricted to high-level items (the prompt enforces this)."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from ..llm import client
from ..schemas.literature import LiteraturePaper, PaperExtraction, ReportedItem
from ..util import prompt

_MAX_ITEMS_PER_PAPER = 6   # abstract-based discovery doesn't need more; bounds normalize payload


def _paper_block(p: LiteraturePaper) -> str:
    return json.dumps({
        "paper_id": p.paper_id, "content_level": p.content_level, "title": p.title,
        "doi": p.doi, "year": p.year, "authors": p.authors,
        "available_text": p.abstract or "(no abstract available)",
    }, ensure_ascii=False)


def extract_one(p: LiteraturePaper) -> PaperExtraction:
    """Extract reported items from one paper. Never raises — returns an empty extraction on error."""
    try:
        raw = client.call_json("fast", prompt("extract_reported_items"), _paper_block(p),
                               step="lit.extract", max_tokens=1600, effort="minimal")
    except Exception:
        return PaperExtraction(paper_id=p.paper_id, content_level=p.content_level)
    items: list[ReportedItem] = []
    for it in (raw.get("reported_items") or [])[:_MAX_ITEMS_PER_PAPER]:   # cap to bound payload
        if not isinstance(it, dict) or not it.get("raw_name") or not it.get("category"):
            continue
        try:
            items.append(ReportedItem(**it))
        except Exception:
            continue
    return PaperExtraction(
        paper_id=p.paper_id,
        study_archetype=str(raw.get("study_archetype", "")).strip(),
        content_level=p.content_level, reported_items=items,
    )


def extract_all(papers: list[LiteraturePaper], progress=lambda m: None,
                max_workers: int = 10) -> list[PaperExtraction]:
    """Extract every paper concurrently (LLM calls are I/O-bound). 10 workers = the default
    ~10-paper set extracts in a single wave instead of two."""
    if not papers:
        return []
    progress(f"논문 {len(papers)}편 항목 추출 (병렬)")
    results: dict[str, PaperExtraction] = {}

    def _work(p: LiteraturePaper) -> tuple[str, PaperExtraction]:
        ex = extract_one(p)
        progress(f"extract: {p.paper_id} ({len(ex.reported_items)} items)")
        return p.paper_id, ex

    with ThreadPoolExecutor(max_workers=min(max_workers, len(papers))) as ex:
        for pid, res in ex.map(_work, papers):
            results[pid] = res
    # preserve input order
    return [results[p.paper_id] for p in papers if p.paper_id in results]
