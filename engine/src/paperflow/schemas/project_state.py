"""Central state object. Built from the 3 input files; everything else reads/writes it."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .evidence_inventory import EvidenceInventory
from .research_state import ResearchState


class JournalInfo(BaseModel):
    working_title: str = ""
    author_field: str = ""
    target_journals: str = ""
    extra: dict[str, str] = Field(default_factory=dict)  # affiliation, lab, advisor, authors...
    raw: str = ""


class CoreMessage(BaseModel):
    one_sentence: str = ""
    one_paragraph: str = ""
    summary_bullets: list[str] = Field(default_factory=list)  # novelty / key claims (-> claim graph)
    keywords: list[str] = Field(default_factory=list)         # optional, strengthens lit search
    out_of_scope: list[str] = Field(default_factory=list)
    raw: str = ""


class OutlineParagraph(BaseModel):
    """One Phase-A skeleton claim sentence."""
    n: int
    section_label: str = ""   # [Intro] / [Methods1] / [Results] ...
    claim_sentence: str = ""


class Outline(BaseModel):
    skeleton: list[OutlineParagraph] = Field(default_factory=list)  # Phase A
    structured_raw: str = ""  # Phase B (kept as text for now)
    raw: str = ""


class DataAsset(BaseModel):
    """A file found under <project>/data — surfaced so writer/validator can ground claims."""
    path: str
    kind: str = ""        # csv | md | other
    columns: list[str] = Field(default_factory=list)
    note: str = ""


class FoundRef(BaseModel):
    """A real paper found by literature search (OpenAlex), usable as a citation."""
    key: str                 # firstauthorYYYY
    title: str = ""
    authors: str = ""
    year: int | None = None
    doi: str = ""
    abstract: str = ""
    topic: str = ""          # why it's relevant / what claim it supports


class ProjectState(BaseModel):
    project_dir: str
    journal_info: JournalInfo = Field(default_factory=JournalInfo)
    core_message: CoreMessage = Field(default_factory=CoreMessage)
    outline: Outline = Field(default_factory=Outline)
    data_assets: list[DataAsset] = Field(default_factory=list)
    reference_keys: list[str] = Field(default_factory=list)  # keys already in reference/references.json
    found_references: list[FoundRef] = Field(default_factory=list)  # from literature search
    answers: dict[str, str] = Field(default_factory=dict)   # Gate A: main/answer.json (field -> answer)
    style: str = ""                                         # main/style.md (D constraint: author's style)
    journal_constraints: dict = Field(default_factory=dict)  # scraped journal guideline limits
    # reconstructed canonical state (minimal-input mode) — None in pure legacy mode
    research_state: ResearchState | None = None
    evidence_inventory: EvidenceInventory | None = None

    @property
    def all_citation_keys(self) -> list[str]:
        return self.reference_keys + [r.key for r in self.found_references]
