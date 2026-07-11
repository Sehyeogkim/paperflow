"""Project-specific requirement schema synthesized from related literature.

`OverallSchema` replaces the static YAML pack at runtime: it is built per project from the
canonical requirement keys clustered across the selected papers. Each `RequirementKey`
records prevalence, applicability, a requirement level, and the source papers it came from.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RequirementLevel = Literal[
    "mandatory", "strongly_expected", "common", "optional", "unsupported"
]
RequirementSource = Literal["literature_derived", "static_fallback", "hybrid"]


class Applicability(BaseModel):
    required_when: list[str] = Field(default_factory=list)
    not_applicable_when: list[str] = Field(default_factory=list)


class ContentSupport(BaseModel):
    full_text: int = 0
    partial_text: int = 0
    abstract_only: int = 0


class RequirementKey(BaseModel):
    key: str                            # canonical key, e.g. "mesh_independence"
    category: str                       # universal-schema top-level category
    aliases: list[str] = Field(default_factory=list)
    observed_in: int = 0                # distinct papers that reported it
    applicable_papers: int = 0          # papers to which it applies (prevalence denominator)
    prevalence: float = 0.0             # observed_in / max(applicable_papers, 1)
    applicability: Applicability = Field(default_factory=Applicability)
    requirement_level: RequirementLevel = "common"
    reason: str = ""
    evidence_sources: list[str] = Field(default_factory=list)   # paper_ids
    content_support: ContentSupport = Field(default_factory=ContentSupport)


class OverallSchema(BaseModel):
    project_id: str = ""
    study_archetype: str = ""
    source_papers: int = 0
    requirement_source: RequirementSource = "literature_derived"
    requirements: list[RequirementKey] = Field(default_factory=list)
