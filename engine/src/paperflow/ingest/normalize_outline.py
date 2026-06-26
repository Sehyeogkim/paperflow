"""Normalize either outline input mode into one NormalizedOutline, and render back to the
legacy Outline / 3_outline.md the existing pipeline + CLI consume.

  Quick input (free text) -> LLM normalizer (deterministic heuristic fallback if no key)
  Structured outline (per-section text) -> deterministic split
  Legacy 3_outline.md (parsed Outline) -> deterministic bucketing

The user's verbatim text is always kept in raw_outline; unclassifiable lines go to
unclassified_notes (never dropped).  (MVP_INPUT_UX_CHANGES_2026-06-26 §1)
"""
from __future__ import annotations

import re

from ..schemas.outline_state import OUTLINE_SECTIONS, NormalizedOutline
from ..schemas.project_state import Outline, OutlineParagraph

# keyword -> canonical section (longest/first match wins)
_SECTION_KEYS: list[tuple[str, str]] = [
    ("introduction", "introduction"), ("intro", "introduction"), ("background", "introduction"),
    ("method", "method"), ("methods", "method"), ("material", "method"),
    ("result", "result"), ("results", "result"), ("finding", "result"),
    ("discussion", "discussion"), ("discuss", "discussion"),
    ("conclusion", "conclusion"), ("conclu", "conclusion"),
    ("abstract", "abstract"), ("summary", "abstract"),
]


def canon_section(label: str) -> str | None:
    low = (label or "").strip().lower()
    if not low:
        return None
    for key, sec in _SECTION_KEYS:
        if low.startswith(key) or key in low:
            return sec
    return None


def _bullets(text: str) -> list[str]:
    """Split a block into clean bullet lines (drop list/number markers, blanks, headings)."""
    out: list[str] = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s or re.match(r"^#{1,6}\s", s):   # skip blank + markdown headings
            continue
        s = re.sub(r"^[-*•]\s+", "", s)           # bullet marker
        s = re.sub(r"^\d+[.)]\s+", "", s)         # numbering
        if s:
            out.append(s)
    return out


def normalize_structured(sections: dict[str, str]) -> NormalizedOutline:
    """Per-section textareas -> normalized schema (no LLM)."""
    raw_parts, secs = [], {s: [] for s in OUTLINE_SECTIONS}
    for sec in OUTLINE_SECTIONS:
        txt = (sections or {}).get(sec, "") or ""
        if txt.strip():
            raw_parts.append(f"## {sec.capitalize()}\n{txt.strip()}")
            secs[sec] = _bullets(txt)
    no = NormalizedOutline(input_mode="structured", raw_outline="\n\n".join(raw_parts),
                           sections=secs)
    no.claim_candidates = list(secs.get("result", [])) + list(secs.get("introduction", []))
    no.method_notes = list(secs.get("method", []))
    no.result_notes = list(secs.get("result", []))
    return no


def normalize_legacy(outline: Outline) -> NormalizedOutline:
    """Parsed legacy 3_outline.md (Outline.skeleton) -> normalized schema (no LLM)."""
    secs = {s: [] for s in OUTLINE_SECTIONS}
    unclassified: list[str] = []
    for p in outline.skeleton:
        sec = canon_section(p.section_label)
        (secs[sec] if sec else unclassified).append(p.claim_sentence)
    no = NormalizedOutline(input_mode="legacy", raw_outline=outline.raw or "",
                           sections=secs, unclassified_notes=unclassified)
    no.claim_candidates = list(secs.get("result", [])) + list(secs.get("introduction", []))
    no.method_notes = list(secs.get("method", []))
    no.result_notes = list(secs.get("result", []))
    return no


_HEADING_RE = re.compile(r"^\s*#{0,6}\s*([A-Za-z가-힣 /]+?)\s*[:：]?\s*$")


def _heuristic_quick(raw: str) -> NormalizedOutline:
    """Deterministic fallback for Quick input when no LLM is available: bucket lines under
    any recognizable section heading; everything before the first heading -> unclassified."""
    secs = {s: [] for s in OUTLINE_SECTIONS}
    unclassified: list[str] = []
    current: str | None = None
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        hm = _HEADING_RE.match(s)
        sec = canon_section(hm.group(1)) if hm else None
        if sec and len(s) <= 40:                   # short line that names a section = heading
            current = sec
            continue
        item = re.sub(r"^[-*•]\s+|^\d+[.)]\s+", "", s)
        (secs[current] if current else unclassified).append(item)
    no = NormalizedOutline(input_mode="quick", raw_outline=raw, sections=secs,
                           unclassified_notes=unclassified)
    no.claim_candidates = list(secs.get("result", [])) + list(secs.get("introduction", []))
    no.method_notes = list(secs.get("method", []))
    no.result_notes = list(secs.get("result", []))
    return no


def normalize_quick(raw: str, context: str = "", use_llm: bool | None = None) -> NormalizedOutline:
    """Quick free-text -> normalized schema via the Outline Normalizer LLM.
    raw is always preserved; on no-key / failure, fall back to the deterministic heuristic."""
    from .. import config
    if use_llm is None:
        use_llm = bool(config.available_providers())
    if not raw.strip():
        return NormalizedOutline(input_mode="quick", raw_outline=raw)
    if not use_llm:
        return _heuristic_quick(raw)
    from ..llm import client
    from ..util import prompt
    try:
        sys = prompt("normalize_outline")
    except Exception:
        return _heuristic_quick(raw)
    user = (f"{context}\n\n## RAW OUTLINE (classify every line; preserve meaning)\n{raw}"
            if context else f"## RAW OUTLINE (classify every line; preserve meaning)\n{raw}")
    try:
        rawj = client.call_json("reasoning", sys, user, step="normalize_outline", max_tokens=3000)
    except Exception:
        return _heuristic_quick(raw)
    secs = {s: [] for s in OUTLINE_SECTIONS}
    src = rawj.get("sections") or {}
    for sec in OUTLINE_SECTIONS:
        secs[sec] = [str(x).strip() for x in (src.get(sec) or []) if str(x).strip()]
    no = NormalizedOutline(
        input_mode="quick", raw_outline=raw, sections=secs,
        claim_candidates=[str(x).strip() for x in (rawj.get("claim_candidates") or []) if str(x).strip()],
        method_notes=[str(x).strip() for x in (rawj.get("method_notes") or []) if str(x).strip()],
        result_notes=[str(x).strip() for x in (rawj.get("result_notes") or []) if str(x).strip()],
        unclassified_notes=[str(x).strip() for x in (rawj.get("unclassified_notes") or []) if str(x).strip()],
    )
    if no.is_empty():           # LLM returned nothing usable -> keep raw via heuristic
        return _heuristic_quick(raw)
    return no


# ---------- render back to the legacy Outline / 3_outline.md the pipeline consumes ----------

_SEC_LABEL = {"introduction": "Intro", "method": "Method", "result": "Result",
              "discussion": "Discussion", "conclusion": "Conclusion", "abstract": "Abstract"}


def to_outline(no: NormalizedOutline) -> Outline:
    """Build the legacy Outline (skeleton) so inputs_block + writer keep working unchanged."""
    skeleton: list[OutlineParagraph] = []
    n = 0
    for sec in OUTLINE_SECTIONS:
        for claim in no.sections.get(sec, []):
            n += 1
            skeleton.append(OutlineParagraph(n=n, section_label=_SEC_LABEL[sec], claim_sentence=claim))
    for claim in no.unclassified_notes:   # keep unclassified so nothing is lost downstream
        n += 1
        skeleton.append(OutlineParagraph(n=n, section_label="", claim_sentence=claim))
    return Outline(skeleton=skeleton, structured_raw="", raw=no.raw_outline)


def render_md(no: NormalizedOutline) -> str:
    """Render a 3_outline.md (legacy format) from the normalized outline (for CLI / fallback)."""
    lines: list[str] = []
    n = 0
    for sec in OUTLINE_SECTIONS:
        items = no.sections.get(sec, [])
        if not items:
            continue
        lines.append(f"[{_SEC_LABEL[sec]}]")
        for it in items:
            n += 1
            lines.append(f"{n}. {it}")
    if no.unclassified_notes:
        lines.append("[Unclassified]")
        for it in no.unclassified_notes:
            n += 1
            lines.append(f"{n}. {it}")
    return "\n".join(lines) + "\n"
