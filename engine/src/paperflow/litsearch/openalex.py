"""OpenAlex literature search (free, no API key). Returns structured works."""
from __future__ import annotations

import re

import httpx

_BASE = "https://api.openalex.org/works"
_MAILTO = "paperflow@example.com"  # polite pool


def _reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)[:1200]


def _key_for(authors: list[str], year: int | None) -> str:
    first = (authors[0].split()[-1] if authors else "anon").lower()
    first = re.sub(r"[^a-z]", "", first) or "anon"
    return f"{first}{year or ''}"


def search(query: str, n: int = 5) -> list[dict]:
    try:
        r = httpx.get(_BASE, params={"search": query, "per_page": n, "mailto": _MAILTO},
                      timeout=30)
        r.raise_for_status()
    except Exception:
        return []
    out: list[dict] = []
    for w in r.json().get("results", []):
        authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
        out.append({
            "title": w.get("title") or "",
            "authors": authors,
            "year": w.get("publication_year"),
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
            "cited_by": w.get("cited_by_count", 0),
            "key": _key_for(authors, w.get("publication_year")),
        })
    return out
