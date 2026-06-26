"""Normalized outline state — one schema for both input modes (Quick / Structured) + legacy.

UX offers two ways to give an outline (free-text "Quick input" or per-section "Structured
outline"), but the backend always holds ONE normalized structure. The user's verbatim text
is preserved in `raw_outline`; nothing the normalizer can't classify is dropped — it goes to
`unclassified_notes`. (MVP_INPUT_UX_CHANGES_2026-06-26 §1.2-1.3)
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# canonical section buckets the writer pipeline understands
OUTLINE_SECTIONS = ["introduction", "method", "result", "discussion", "conclusion", "abstract"]


def _empty_sections() -> dict[str, list[str]]:
    return {s: [] for s in OUTLINE_SECTIONS}


class NormalizedOutline(BaseModel):
    input_mode: str = "structured"          # "quick" | "structured" | "legacy"
    raw_outline: str = ""                   # the user's verbatim text — ALWAYS preserved
    sections: dict[str, list[str]] = Field(default_factory=_empty_sections)
    claim_candidates: list[str] = Field(default_factory=list)
    method_notes: list[str] = Field(default_factory=list)
    result_notes: list[str] = Field(default_factory=list)
    unclassified_notes: list[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return (not self.raw_outline.strip()
                and not any(self.sections.values())
                and not self.claim_candidates and not self.unclassified_notes)
