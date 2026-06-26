"""Literature-grounded requirement pipeline — paper + per-paper extraction schemas.

A `LiteraturePaper` is a candidate prior study found via OpenAlex (or supplied by the
user). `PaperExtraction` is the open-ended set of reported items extracted from ONE paper:
the top-level `category` is fixed (universal schema), but `raw_name`/`sub_category` are free.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ContentLevel = Literal["full_text", "partial_text", "abstract_only"]
PaperSource = Literal["user_pdf", "repository", "open_access_url", "exa", "openalex"]


class LiteraturePaper(BaseModel):
    paper_id: str                       # stable id, e.g. "paper_001" (DOI kept in `doi`)
    title: str = ""
    doi: str = ""
    year: int | None = None
    authors: str = ""                   # comma-separated
    abstract: str = ""
    content_level: ContentLevel = "abstract_only"
    source: PaperSource = "openalex"
    selection_role: str = ""            # why selected: most_similar | journal_match | method | recent
    cited_by: int = 0


class ReportedItem(BaseModel):
    raw_name: str                       # free-form item name as the paper expresses it
    category: str                       # FIXED top-level (universal schema key)
    sub_category: str = ""              # free-form
    description: str = ""
    section: str = ""                   # where in the paper (Methods, Results, ...)
    evidence_text: str = ""             # short supporting passage / extracted statement
    importance_to_main_claim: str = "unknown"   # high | medium | low | unknown
    explicitly_reported: bool = True
    applies_to: list[str] = Field(default_factory=list)   # study archetypes/claim types
    source_location: str = ""


class PaperExtraction(BaseModel):
    paper_id: str
    study_archetype: str = ""
    content_level: ContentLevel = "abstract_only"
    reported_items: list[ReportedItem] = Field(default_factory=list)
