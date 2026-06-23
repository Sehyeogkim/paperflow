"""Reference-hunter: fill citations AFTER writing (post-hoc).

The writer leaves [cite:what_I_need — <what is needed>] markers wherever it knows a citation
is required but the author gave none. This module collects those needs, searches OpenAlex for
a real paper per need, writes reference_table.json, and replaces each marker with [cite:key].
Anything it cannot resolve is left as a marker (never fabricate a citation)."""
from __future__ import annotations

import re

from ..litsearch import openalex

# matches [cite:what_I_need — needed text] (em-dash or hyphen), capturing the need
_NEED_RE = re.compile(r"\[cite:what_i_need\s*[—\-]\s*([^\]]+)\]", re.IGNORECASE)


def _collect_needs(section_md: dict[str, str]) -> list[str]:
    needs: list[str] = []
    seen: set[str] = set()
    for md in section_md.values():
        for m in _NEED_RE.finditer(md):
            need = m.group(1).strip()
            low = need.lower()
            if low not in seen:
                seen.add(low)
                needs.append(need)
    return needs


def _resolve(need: str) -> dict | None:
    """Find one real paper for a citation need. Returns a reference row or None."""
    hits = openalex.search(need, n=3)
    if not hits:
        return None
    h = hits[0]
    if not h.get("title"):
        return None
    return {
        "key": h["key"],
        "title": h["title"],
        "authors": ", ".join(h.get("authors", [])[:6]),
        "year": h.get("year"),
        "doi": h.get("doi", ""),
        "used_for": need,
        "verification_status": "auto_openalex",
    }


def fill(section_md: dict[str, str], progress=lambda m: None
         ) -> tuple[dict[str, str], list[dict]]:
    """Resolve [cite:what_I_need — ...] markers to real references.
    Returns (updated section_md, reference_table rows)."""
    needs = _collect_needs(section_md)
    if not needs:
        return section_md, []

    resolved: dict[str, dict] = {}   # need(lower) -> reference row
    for need in needs:
        progress(f"hunt: {need[:48]}")
        row = _resolve(need)
        if row:
            resolved[need.lower()] = row

    def repl(m: re.Match) -> str:
        row = resolved.get(m.group(1).strip().lower())
        return f"[cite:{row['key']}]" if row else m.group(0)

    updated = {sec: _NEED_RE.sub(repl, md) for sec, md in section_md.items()}
    table = list({r["key"]: r for r in resolved.values()}.values())  # dedupe by key
    return updated, table
