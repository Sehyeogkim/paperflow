"""Adaptive-question + graph-gap schema.

The question loop is driven by GAPS in the preliminary logic graph (+ reconstruction
unknowns), not by a fixed checklist. Each gap becomes a ranked Question. Nothing here is a
hard gate: load-bearing gaps that stay unanswered surface as warnings at generation time.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GapKind = Literal[
    "missing_primary_claim",        # no main claim selected at all
    "claim_without_evidence",       # claim has no supporting evidence
    "evidence_without_provenance",  # evidence has no producing method / source data
    "claim_without_warrant",        # claim has no warrant/reference justifying it
    "claim_without_qualifier",      # main claim has no qualifier/limitation
    "data_meaning_unknown",         # an uploaded file has no description / unclear meaning
    "research_unknown",             # a reconstruction field could not be inferred
]

# gaps that block defensible writing of a main claim — left unanswered, they become warnings
LOAD_BEARING: set[str] = {
    "missing_primary_claim", "claim_without_evidence", "evidence_without_provenance",
}


class GraphGap(BaseModel):
    kind: GapKind
    target_id: str = ""          # node id (claim/evidence) or asset path / field name
    target_text: str = ""        # human-readable subject of the gap
    detail: str = ""             # extra context for the question/warning
    load_bearing: bool = False


class Question(BaseModel):
    id: str                      # stable id (gap_kind + target) so answers de-dupe
    gap_kind: GapKind
    target_id: str = ""
    question: str
    example: str = ""            # placeholder shown to the user
    value: float = 0.0           # ranking score (see question/rank.py)
    load_bearing: bool = False


class QuestionBatch(BaseModel):
    questions: list[Question] = Field(default_factory=list)
    remaining: int = 0           # candidate questions not in this batch
    terminated: bool = False     # loop end-condition satisfied (no load-bearing gaps left)
    warnings: list[str] = Field(default_factory=list)  # load-bearing gaps still open
