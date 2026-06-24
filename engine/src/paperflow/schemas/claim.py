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
# 7 node kinds: claim (assertion the paper argues) / evidence (a result-proposition) /
# method (an action that produced/analyzed data) / data (a real object: CSV/image/sim
# output/measurement) / warrant (a principle licensing evidence->claim) / source (a
# reference) / artifact (figure|table|equation that DISPLAYS evidence or method).
NodeKind = Literal["claim", "evidence", "method", "data", "warrant", "source", "artifact"]

# 9 edge relations (directional). Allowed src->dst kind combinations are enforced in
# compile/claim_graph.py (_ALLOWED_EDGE); violations are dropped, not silently coerced.
EdgeRel = Literal["supports", "produces", "uses", "derived_from", "part_of",
                  "visualizes", "justifies", "qualifies", "contradicts"]


class GNode(BaseModel):
    id: str                       # "C1", "C1.1", "E1", "M1", "M1.2", "D3", "F3", "W1", "R12"
    kind: NodeKind
    text: str
    parent_id: str | None = None  # hierarchy: subclaim -> main claim, OR submethod -> method
    subtype: str = ""             # method subtype: simulation|preprocessing|analysis|validation|...
    role: str = ""                # epistemic role: problem|gap|contribution|validation|limitation|...
    represented_as: Literal["figure", "table", "text"] | None = None  # document design (artifacts)
    section: str | None = None    # introduction|method|result|discussion|conclusion|abstract
    provenance: str | None = None  # CSV path / cite key / "[DATA_NEEDED]" / "user_statement"


class GEdge(BaseModel):
    id: str = ""                  # "L17" (optional; assigned during build if missing)
    src: str
    dst: str
    rel: EdgeRel
    rationale: str = ""           # WHY this link holds — the edge's evaluable content
    grounding_status: Literal["grounded", "partial", "missing", "unverified"] = "unverified"


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

    def edges_into(self, nid: str) -> list[GEdge]:
        return [e for e in self.edges if e.dst == nid]

    def edges_out(self, nid: str) -> list[GEdge]:
        return [e for e in self.edges if e.src == nid]


class ParagraphContract(BaseModel):
    paragraph_id: str             # M-01, R-03
    section: str                  # "method" | "result"
    heading: str = ""             # e.g. "2.1 Cost-effective FSI framework"
    purpose: str                  # one-line intent
    claim_ids: list[str] = Field(default_factory=list)
    context_node_ids: list[str] = Field(default_factory=list)  # evidence/method/data/warrant/source/artifact for this paragraph
    required_edge_ids: list[str] = Field(default_factory=list)  # edges whose rationale the paragraph must respect
    supports: list[str] = Field(default_factory=list)   # data/figure/artifact node refs to ground to
    must_not_claim: list[str] = Field(default_factory=list)
    transition_from: str = ""
    transition_to: str = ""


class SectionContract(BaseModel):
    section: str
    paragraphs: list[ParagraphContract] = Field(default_factory=list)
