"""Research state — the reconstructed logic of the study, recovered from the user's
uploaded documents + data + answers.

This is canonical backend state (workflow_design.md §3.1). It is built in two layers:
  - a deterministic skeleton from ProjectState (core message, outline, data, references)
  - optional LLM enrichment that fills the inferential fields (study_type, problem, design)

Downstream (claim graph, questions) reads this; nothing here requires an LLM, so the
schema round-trips and the skeleton builder both work fully offline.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Dataset(BaseModel):
    """A dataset the study produced or consumed (richer than a raw file path)."""
    name: str = ""
    path: str = ""                 # relative path if it maps to an uploaded file
    description: str = ""          # user-provided or inferred one-liner
    role: str = ""                 # e.g. "input design space" | "sensitivity result"


class ResearchState(BaseModel):
    study_type: str = ""           # e.g. "computational_biomechanics"
    research_problem: str = ""
    objective: str = ""
    primary_message: str = ""
    study_design: str = ""
    methods: list[str] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    input_variables: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    comparisons: list[str] = Field(default_factory=list)
    key_observations: list[str] = Field(default_factory=list)
    possible_claims: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    known_references: list[str] = Field(default_factory=list)  # citation keys already on hand
    unknowns: list[str] = Field(default_factory=list)          # gaps the reconstruction flagged

    # author answers folded into this state, kept distinguishable from literature-inferred facts
    # each: {"field": ..., "source": "author_answer_requirement|author_answer_logic", "answer_id": ...}
    answer_provenance: list[dict] = Field(default_factory=list)

    # provenance of how this state was built — "skeleton" | "llm_enriched" | "v2" | "final"
    source: str = "skeleton"
