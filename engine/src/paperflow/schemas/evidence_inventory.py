"""Evidence inventory — each uploaded file recorded as research context, not just a path.

Canonical backend state (workflow_design.md §3.2). The deterministic profiler fills
`columns`/`profile` from the file itself; `user_description` comes from data_notes.json;
`inferred_role` / `key_observations` / `uncertainties` are heuristic (and optionally
LLM-enriched). Fully offline-constructible.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceAsset(BaseModel):
    path: str                                  # relative to project dir
    kind: str = ""                             # csv | xlsx | md | dat | pdf | png | ...
    user_description: str = ""                 # from main/data_notes.json
    inferred_role: str = ""                    # e.g. "global sensitivity result"
    unit_of_analysis: str = ""                 # e.g. "input-variable group"
    columns: dict[str, str] = Field(default_factory=dict)   # column name -> dtype/role
    profile: dict = Field(default_factory=dict)             # rows, ranges, sheet names...
    key_observations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class EvidenceInventory(BaseModel):
    assets: list[EvidenceAsset] = Field(default_factory=list)

    def by_path(self, path: str) -> EvidenceAsset | None:
        return next((a for a in self.assets if a.path == path), None)
