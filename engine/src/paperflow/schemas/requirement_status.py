"""User-coverage comparison + grounded question schemas.

`RequirementStatus` is the per-key verdict after comparing the project's `OverallSchema`
against the user's materials. `GroundedQuestion` is the question shown to the author — it
always carries WHY it is asked and WHICH papers/guideline it traces to.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CoverageStatus = Literal["present", "partial", "missing", "not_applicable", "uncertain"]


class RequirementStatus(BaseModel):
    key: str
    status: CoverageStatus
    found_evidence: list[str] = Field(default_factory=list)   # where in user material it was found
    reason: str = ""
    source_requirements: list[str] = Field(default_factory=list)   # overall_schema:<key>


class GroundedQuestion(BaseModel):
    id: str                              # canonical requirement key
    question: str
    why_asked: str = ""                  # reviewer-facing rationale (lit/guideline grounded)
    expected_answer: str = ""            # what kind of answer is wanted (placeholder text)
    requirement_level: str = "strongly_expected"
    reviewer_risk: str = "high"          # low | medium | high (mapped from requirement_level)
    sources: list[str] = Field(default_factory=list)          # paper_ids / guideline ids
    applicability_reason: str = ""       # why this requirement applies to THIS study
    not_found_reason: str = ""           # why it could not be found in user material
    allow_unknown: bool = True
    priority: float = 0.0
