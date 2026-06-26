"""Load-bearing graph-gap report (TWO_STAGE_QUESTIONS_FINAL_GRAPH_WORKFLOW.md §7).

This is distinct from the lightweight `question.GraphGap` used by the legacy adaptive batch:
here a gap is a *load-bearing defect* that prevents defensible writing, carrying severity,
the affected claim(s), what information would resolve it, and whether it can degrade to a
qualifier instead of forcing a question.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GapType = Literal[
    "missing_evidence_to_claim",     # a main claim has no supporting evidence
    "missing_comparator",            # superiority/dominance claim w/o comparison basis
    "untraceable_evidence",          # evidence value not traceable to data/method/answer
    "missing_method_for_evidence",   # evidence with no producing method/data
    "missing_qualifier",             # overgeneralized claim needs scope/limitation
    "graph_integrity",               # dangling edge / invalid type pair / isolated node
]
Severity = Literal["high", "medium", "low"]


class LoadBearingGap(BaseModel):
    id: str                                   # e.g. GAP_C1_EVIDENCE
    type: GapType
    severity: Severity = "high"
    claim_ids: list[str] = Field(default_factory=list)
    related_node_ids: list[str] = Field(default_factory=list)
    description: str = ""
    information_needed: str = ""
    can_degrade_to_qualifier: bool = False


class GraphGapReport(BaseModel):
    graph_id: str = "preliminary_v1"
    load_bearing_gaps: list[LoadBearingGap] = Field(default_factory=list)
    non_blocking_warnings: list[str] = Field(default_factory=list)
    ready_for_finalization: bool = True

    @property
    def high_severity(self) -> list[LoadBearingGap]:
        return [g for g in self.load_bearing_gaps if g.severity == "high"]

    def needs_stage2(self) -> bool:
        """Stage 2 runs only when load-bearing gaps remain."""
        return bool(self.load_bearing_gaps)
