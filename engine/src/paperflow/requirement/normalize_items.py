"""Stage 8: cluster reported items across papers into canonical requirement keys (one call)."""
from __future__ import annotations

import json
import sys

from ..llm import client
from ..schemas.literature import PaperExtraction
from ..util import prompt


def _flatten(extractions: list[PaperExtraction]) -> list[dict]:
    flat: list[dict] = []
    for ex in extractions:
        for idx, it in enumerate(ex.reported_items, 1):
            flat.append({
                "ref": f"{ex.paper_id}:item_{idx:02d}",
                "paper_id": ex.paper_id,
                "content_level": ex.content_level,
                "raw_name": it.raw_name, "category": it.category,
                "sub_category": it.sub_category,
                "explicitly_reported": it.explicitly_reported,
            })
    return flat


def normalize(extractions: list[PaperExtraction]) -> list[dict]:
    """Return a list of clusters: {canonical_key, category, aliases, applicable_to, source_items}.
    Returns [] on error (caller treats thin clustering as a fallback trigger)."""
    flat = _flatten(extractions)
    if not flat:
        return []
    user = "## REPORTED ITEMS (across all papers)\n" + json.dumps(flat, ensure_ascii=False)
    # clustering is pattern-matching, not deep reasoning -> use the fast tier (much quicker than
    # a full reasoning model on a large item list, which otherwise times out and forces fallback).
    try:
        raw = client.call_json("fast", prompt("normalize_reported_items"), user,
                               step="lit.normalize", max_tokens=4000)
    except Exception as e:
        print(f"[normalize] LLM call failed ({len(flat)} items): {type(e).__name__}: "
              f"{str(e)[:160]}", file=sys.stderr)
        return []
    clusters: list[dict] = []
    # tolerant ref matching: accept "paper_1:item_1" ~ "paper_001:item_01" (pad differences)
    def _canon(ref: str) -> str:
        import re
        m = re.match(r"\s*paper[_\s]*0*(\d+)\s*:\s*item[_\s]*0*(\d+)", str(ref), re.I)
        return f"paper_{int(m.group(1)):03d}:item_{int(m.group(2)):02d}" if m else str(ref).strip()
    valid_refs = {_canon(f["ref"]): f["ref"] for f in flat}
    raw_clusters = raw.get("clusters") or []
    for c in raw_clusters:
        if not isinstance(c, dict) or not c.get("canonical_key"):
            continue
        src = [valid_refs[_canon(s)] for s in (c.get("source_items") or []) if _canon(s) in valid_refs]
        if not src:
            continue
        clusters.append({
            "canonical_key": str(c["canonical_key"]).strip(),
            "category": str(c.get("category", "reported_items")).strip(),
            "aliases": [str(a).strip() for a in (c.get("aliases") or []) if str(a).strip()],
            "applicable_to": [str(a).strip() for a in (c.get("applicable_to") or []) if str(a).strip()],
            "source_items": src,
        })
    if raw_clusters and not clusters:
        print(f"[normalize] LLM returned {len(raw_clusters)} clusters but none had matching "
              f"source_items ({len(flat)} items) — check ref format", file=sys.stderr)
    return clusters
