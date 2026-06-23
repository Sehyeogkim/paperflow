"""Journal guideline scraping (the 'A' constraint source: journal formatting limits).

If the author put a guidelines URL in 0_journal_info.md (any http(s) link in the journal
info), fetch it and have the fast tier extract the hard limits (abstract word count, figure
count, section structure). No URL -> no-op (returns {}). similar-journal inference is phase 2.
"""
from __future__ import annotations

import re

import httpx

from ..llm import client
from ..llm.client import LLMError
from ..schemas.project_state import JournalInfo
from ..util import prompt

_URL_RE = re.compile(r"https?://[^\s)>\]]+")


def _find_url(ji: JournalInfo) -> str:
    for hay in (ji.raw, ji.target_journals, *ji.extra.values()):
        m = _URL_RE.search(hay or "")
        if m:
            return m.group(0)
    return ""


def fetch(ji: JournalInfo) -> dict:
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
