"""Journal guideline scraping (the 'A' constraint source: journal formatting limits).

If the author put a guidelines URL in 0_journal_info.md (any http(s) link in the journal
info), fetch it and have the fast tier extract the hard limits (abstract word count, figure
count, section structure). No URL -> no-op (returns {}). similar-journal inference is phase 2.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from ..llm import client
from ..llm.client import LLMError
from ..schemas.project_state import JournalInfo
from ..util import prompt

_URL_RE = re.compile(r"https?://[^\s)>\]]+")
# pre-fetched guideline cache (one JSON per journal; fetched offline, before a run)
_GUIDELINES_DIR = Path(__file__).resolve().parent / "guidelines"


def _find_url(ji: JournalInfo) -> str:
    for hay in (ji.raw, ji.target_journals, *ji.extra.values()):
        m = _URL_RE.search(hay or "")
        if m:
            return m.group(0)
    return ""


def _from_cache(ji: JournalInfo) -> dict:
    """Match the target journal name against pre-fetched guideline files (no network/LLM).
    Aliases tolerate spelling drift (e.g. the demo's 'bology' typo)."""
    target = (ji.target_journals or ji.raw or "").lower()
    if not target or not _GUIDELINES_DIR.is_dir():
        return {}
    for p in sorted(_GUIDELINES_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        aliases = [a.lower() for a in data.get("aliases", [])] or [p.stem.replace("_", " ")]
        if any(a in target for a in aliases):
            return data.get("constraints", {}) or {}
    return {}


def fetch(ji: JournalInfo) -> dict:
    cached = _from_cache(ji)  # pre-fetched guideline wins — cheap, deterministic
    if cached:
        return cached
    url = _find_url(ji)
    if not url:
        return {}
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 paperflow"})
        r.raise_for_status()
    except Exception:
        return {}
    # crude HTML -> text, capped (the guideline limits are usually near the top)
    text = re.sub(r"<[^>]+>", " ", r.text)
    text = re.sub(r"\s+", " ", text)[:8000]
    try:
        out = client.call_json("fast", prompt("journal_guideline"),
                               f"## TARGET JOURNAL\n{ji.target_journals}\n\n## GUIDELINE PAGE\n{text}",
                               step="journal_guideline", max_tokens=1200)
    except LLMError:
        return {}
    return out if isinstance(out, dict) else {}
