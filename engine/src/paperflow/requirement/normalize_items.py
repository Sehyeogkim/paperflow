"""Stage 8: cluster reported items across papers into canonical requirement keys (one call)."""
from __future__ import annotations

import json

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
    try:
        raw = client.call_json("reasoning", prompt("normalize_reported_items"), user,
                               step="lit.normalize", max_tokens=4000)
    except Exception:
        return []
    clusters: list[dict] = []
    valid_refs = {f["ref"] for f in flat}
    for c in (raw.get("clusters") or []):
        if not isinstance(c, dict) or not c.get("canonical_key"):
            continue
        src = [s for s in (c.get("source_items") or []) if s in valid_refs]
        if not src:
            continue
        clusters.append({
            "canonical_key": str(c["canonical_key"]).strip(),
            "category": str(c.get("category", "reported_items")).strip(),
            "aliases": [str(a).strip() for a in (c.get("aliases") or []) if str(a).strip()],
            "applicable_to": [str(a).strip() for a in (c.get("applicable_to") or []) if str(a).strip()],
            "source_items": src,
        })
    return clusters
