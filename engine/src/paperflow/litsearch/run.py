"""Literature search step (workflow §0): generate queries -> OpenAlex -> dedupe ->
synthesize a related-work survey -> return FoundRefs (real papers the writer may cite).

Grounded: every found paper is a real OpenAlex record with a DOI. The survey is written
ONLY from the found abstracts (no invented papers/findings).
"""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.project_state import FoundRef, ProjectState
from ..util import inputs_block, prompt
from . import openalex


def _dedupe_and_key(works: list[dict]) -> list[dict]:
    seen_doi: set[str] = set()
    seen_key: set[str] = set()
    out: list[dict] = []
    for w in sorted(works, key=lambda w: w.get("cited_by", 0), reverse=True):
        doi = w.get("doi", "")
        if doi and doi in seen_doi:
            continue
        seen_doi.add(doi)
        key = w["key"] or "ref"
        base, i = key, 1
        while key in seen_key:
            key = f"{base}{chr(ord('a') + i)}"  # firstauthor2020 -> ...2020b
            i += 1
        seen_key.add(key)
        w["key"] = key
        out.append(w)
    return out


def run(ps: ProjectState, max_papers: int = 15, progress=lambda m: None) -> tuple[str, list[FoundRef]]:
    """Returns (literature_md, found_refs). Never raises — search/LLM failures degrade to empty."""
    progress("queries")
    try:
        qres = client.call_json("fast", prompt("litsearch_queries"), inputs_block(ps),
                                step="litsearch.queries", max_tokens=400)
        queries = qres.get("queries", [])[:6]
    except Exception:
        queries = []
    if not queries:
        return "", []

    progress(f"OpenAlex 검색 ({len(queries)} queries)")
    works: list[dict] = []
    for q in queries:
        works.extend(openalex.search(q, n=5))
    works = _dedupe_and_key(works)[:max_papers]
    if not works:
        return "", []

    papers_block = "\n".join(
        f"{i+1}. key={w['key']} | {w['year']} | {', '.join(w['authors'][:3])} | "
        f"{w['title']}\n   abstract: {w['abstract'][:500]}"
        for i, w in enumerate(works)
    )
    progress("survey 합성")
    try:
        sres = client.call_json("writer", prompt("literature_survey"),
                                f"## CORE MESSAGE\n{ps.core_message.one_sentence}\n\n"
                                f"## FOUND PAPERS\n{papers_block}",
                                step="litsearch.survey", max_tokens=4000)
    except Exception:
        sres = {"survey_md": "", "roles": []}

    roles = {r.get("key"): r.get("topic", "") for r in sres.get("roles", [])}
    found = [
        FoundRef(key=w["key"], title=w["title"], authors=", ".join(w["authors"]),
                 year=w["year"], doi=w["doi"], abstract=w["abstract"][:600],
                 topic=roles.get(w["key"], ""))
        for w in works if w["key"] in roles  # keep only papers the survey deemed relevant
    ] or [
        FoundRef(key=w["key"], title=w["title"], authors=", ".join(w["authors"]),
                 year=w["year"], doi=w["doi"], abstract=w["abstract"][:600])
        for w in works[:8]
    ]
    return sres.get("survey_md", ""), found
