"""Requirement pack + completion-possibility classification (anti-hallucination core)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CompletionClass(str, Enum):
    SUBMISSION_READY_DRAFT = "SUBMISSION_READY_DRAFT"
    EXPERT_REVIEW_REQUIRED = "EXPERT_REVIEW_REQUIRED"
    MISSING_CRITICAL_INFORMATION = "MISSING_CRITICAL_INFORMATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ConditionalReq(BaseModel):
    name: str
    required_when: list[str] = Field(default_factory=list)


class RequirementPack(BaseModel):
    study_type: str
    required: list[str] = Field(default_factory=list)
    conditional: list[ConditionalReq] = Field(default_factory=list)


class MissingItem(BaseModel):
    field: str
    why_it_matters: str = ""
    reviewer_risk: str = "medium"   # low | medium | high
    question: str = ""              # phrased question to ask the user
    example: str = ""               # a sample answer, shown to the user as input placeholder
    priority: float = 0.0


class RequirementReport(BaseModel):
    study_type: str
    classification: CompletionClass
    present: list[str] = Field(default_factory=list)
    missing: list[MissingItem] = Field(default_factory=list)
    notes: str = ""
