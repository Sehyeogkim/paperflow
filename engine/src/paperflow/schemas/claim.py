"""Claim Graph + Section/Paragraph contracts — the load-bearing logic structure.

The pipeline does NOT write prose first. It builds a TYPED claim graph (nodes of
distinct kinds + typed edges), derives a contract per paragraph (what it must claim,
what it must NOT claim, what supports it), drafts against the contract, then validates
the draft back against the contract.

Design note (why typed, not flat): a figure is NOT a sub-claim — it is an *artifact*
that *displays* evidence. Conflating them mixes two different questions: "is this claim
logically supported?" (epistemic) vs "show it as a figure or a table?" (document design).
One typed node carries all three concerns as attributes — no need for three separate
graphs: `kind` = epistemic role, `represented_as`/`section` = document realization,
`provenance` = where the evidence came from.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 6 node kinds: claim (assertion) / evidence (a result that supports a claim) /
# artifact (figure|table|paragraph that displays evidence) / warrant (background
# principle linking evidence->claim) / method (what was done) / source (a reference).
NodeKind = Literal["claim", "evidence", "artifact", "warrant", "method", "source"]

# 5 edge relations between nodes.
EdgeRel = Literal["supports", "visualizes", "derived_from", "qualifies", "contradicts"]


class GNode(BaseModel):
    id: str                       # "C1", "C1.1", "E1", "M1", "F3", "T2", "W1", "R12"
    kind: NodeKind
    text: str
    parent_id: str | None = None  # claim hierarchy: subclaim -> its main claim
    role: str = ""                # epistemic role tag: problem|gap|contribution|validation|limitation|...
    represented_as: Literal["figure", "table", "text"] | None = None  # document design (artifacts)
    section: str | None = None    # introduction|method|result|discussion|conclusion|abstract
    provenance: str | None = None  # CSV path / cite key / "[DATA_NEEDED]" / "user_statement"


class GEdge(BaseModel):
    src: str
    dst: str
    rel: EdgeRel


class ClaimGraph(BaseModel):
    main_contribution: str = ""
    nodes: list[GNode] = Field(default_factory=list)
    edges: list[GEdge] = Field(default_factory=list)

    @property
    def claims(self) -> list[GNode]:
        return [n for n in self.nodes if n.kind == "claim"]

    @property
    def artifacts(self) -> list[GNode]:
        return [n for n in self.nodes if n.kind == "artifact"]

    def node(self, nid: str) -> GNode | None:
        return next((n for n in self.nodes if n.id == nid), None)


class ParagraphContract(BaseModel):
    paragraph_id: str             # M-01, R-03
    section: str                  # "method" | "result"
    heading: str = ""             # e.g. "2.1 Cost-effective FSI framework"
    purpose: str                  # one-line intent
    claim_ids: list[str] = Field(default_factory=list)
    supports: list[str] = Field(default_factory=list)   # data/figure/artifact node refs to ground to
    must_not_claim: list[str] = Field(default_factory=list)
    transition_from: str = ""
    transition_to: str = ""


class SectionContract(BaseModel):
    section: str
    paragraphs: list[ParagraphContract] = Field(default_factory=list)
