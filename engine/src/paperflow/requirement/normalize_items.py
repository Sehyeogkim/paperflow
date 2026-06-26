"""Stage 8: cluster reported items into canonical requirement keys.

The top-level `category` is FIXED, and items in different categories can never merge. So we
split the flat item list BY category and cluster each category in PARALLEL (one small mini
call per category) instead of one big serial call. Wall-clock = slowest category, not the sum.
Tiny categories (<3 items) are clustered trivially in code — no LLM call needed.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from ..llm import client
from ..schemas.literature import PaperExtraction
from ..util import prompt

_LLM_THRESHOLD = 3   # categories with >= this many items get an LLM clustering call


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


def _canon(ref: str) -> str:
    """Tolerant ref key: 'paper_1:item_1' ~ 'paper_001:item_01' (pad differences)."""
    m = re.match(r"\s*paper[_\s]*0*(\d+)\s*:\s*item[_\s]*0*(\d+)", str(ref), re.I)
    return f"paper_{int(m.group(1)):03d}:item_{int(m.group(2)):02d}" if m else str(ref).strip()


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_") or "item"


def _trivial_clusters(flat: list[dict], category: str) -> list[dict]:
    """No-LLM clustering for tiny categories: group by normalized raw_name."""
    groups: dict[str, dict] = {}
    for f in flat:
        key = _slug(f["raw_name"])
        g = groups.setdefault(key, {"canonical_key": key, "category": category,
                                    "aliases": [], "applicable_to": [], "source_items": []})
        g["source_items"].append(f["ref"])
        if f["raw_name"] not in g["aliases"]:
            g["aliases"].append(f["raw_name"])
    return list(groups.values())


def _cluster_batch(flat: list[dict], category: str) -> list[dict]:
    """LLM-cluster one category's items. Falls back to trivial clusters on error."""
    user = f"## REPORTED ITEMS (category: {category})\n" + json.dumps(flat, ensure_ascii=False)
    try:
        raw = client.call_json("fast", prompt("normalize_reported_items"), user,
                               step=f"lit.normalize:{category}", max_tokens=2000, effort="low")
    except Exception as e:
        print(f"[normalize:{category}] LLM failed ({len(flat)} items): {type(e).__name__}: "
              f"{str(e)[:120]}", file=sys.stderr)
        return _trivial_clusters(flat, category)
    valid_refs = {_canon(f["ref"]): f["ref"] for f in flat}
    clusters: list[dict] = []
    for c in (raw.get("clusters") or []):
        if not isinstance(c, dict) or not c.get("canonical_key"):
            continue
        src = [valid_refs[_canon(s)] for s in (c.get("source_items") or []) if _canon(s) in valid_refs]
        if not src:
            continue
        clusters.append({
            "canonical_key": str(c["canonical_key"]).strip(),
            "category": str(c.get("category", category)).strip() or category,
            "aliases": [str(a).strip() for a in (c.get("aliases") or []) if str(a).strip()],
            "applicable_to": [str(a).strip() for a in (c.get("applicable_to") or []) if str(a).strip()],
            "source_items": src,
        })
    return clusters or _trivial_clusters(flat, category)   # never lose a category to a bad response


def normalize(extractions: list[PaperExtraction]) -> list[dict]:
    """Cluster items into canonical keys, per-category in parallel. Returns [] only when there
    are no items at all (caller treats that as a fallback trigger)."""
    flat = _flatten(extractions)
    if not flat:
        return []
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for f in flat:
        by_cat[f["category"] or "reported_items"].append(f)

    def _work(item: tuple[str, list[dict]]) -> list[dict]:
        cat, items = item
        return _cluster_batch(items, cat) if len(items) >= _LLM_THRESHOLD else _trivial_clusters(items, cat)

    clusters: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(8, len(by_cat))) as ex:
        for res in ex.map(_work, list(by_cat.items())):
            clusters.extend(res)
    return clusters
