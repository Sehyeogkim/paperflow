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

from typing import Any, Literal

from pydantic import BaseModel, Field

# 6 node kinds: claim (assertion) / evidence (a result that supports a claim) /
# artifact (figure|table|paragraph that displays evidence) / warrant (background
# principle linking evidence->claim) / method (what was done) / source (a reference).
# 7 node kinds: claim (assertion the paper argues) / evidence (a result-proposition) /
# method (an action that produced/analyzed data) / data (a real object: CSV/image/sim
# output/measurement) / warrant (a principle licensing evidence->claim) / source (a
# reference) / artifact (figure|table|equation that DISPLAYS evidence or method).
NodeKind = Literal[
    "claim", "evidence", "method", "data", "warrant", "source", "artifact",
    # Tacit-knowledge layer: why a parameter/action was chosen, what can fail, and
    # which alternative was selected. These are knowledge slots, not paper claims.
    "threshold", "pitfall", "decision",
]

# Directional relations. Allowed src->dst kind combinations are enforced and reported by
# compile/claim_graph.py; the compatibility adapter returns only the safe validated subset.
EdgeRel = Literal["supports", "produces", "uses", "derived_from", "part_of",
                  "visualizes", "justifies", "qualifies", "contradicts",
                  "feeds", "governs", "warns_about"]

KnowledgeStatus = Literal[
    "unverified", "missing", "partial", "answered", "author_attested",
    "verified", "rejected", "unknown",
]


class ProvenanceRef(BaseModel):
    """A machine-checkable pointer to the origin of one graph fact.

    ``GNode.provenance`` remains for backward compatibility with existing plans. New
    integrations should add structured refs so a file claim can point to a page, sheet,
    cell range, line range, or JSON path instead of merely naming a file.
    """

    source_type: Literal["file", "author", "external", "model", "system"]
    asset_id: str = ""
    locator: str = ""
    quote: str = ""
    quote_hash: str = ""
    verification_status: Literal["unverified", "author_attested", "verified", "rejected"] = "unverified"
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    provenance_refs: list[ProvenanceRef] = Field(default_factory=list)
    knowledge_status: KnowledgeStatus = "unverified"
    layer: Literal["documented", "tacit"] | None = None
    detail: str = ""             # answer/long-form knowledge; `text` stays the stable label
    question: str = ""           # tacit-slot question shown to the author
    why_it_matters: str = ""
    must_capture: list[str] = Field(default_factory=list)
    risk: Literal["low", "medium", "high"] = "medium"
    last_modified_revision: int = 0


class GEdge(BaseModel):
    id: str = ""                  # "L17" (optional; assigned during build if missing)
    src: str
    dst: str
    rel: EdgeRel
    rationale: str = ""           # WHY this link holds — the edge's evaluable content
    grounding_status: Literal["grounded", "partial", "missing", "unverified"] = "unverified"
    provenance_refs: list[ProvenanceRef] = Field(default_factory=list)
    last_modified_revision: int = 0


class ClaimGraph(BaseModel):
    schema_version: str = "1.0"
    revision: int = 0
    built_from_source_revision: int = 0
    confirmed_revision: int | None = None
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


class GraphValidationIssue(BaseModel):
    """One deterministic schema/relationship problem found in raw graph input."""

    code: str
    message: str
    location: str = ""
    item_id: str = ""
    severity: Literal["warning", "error"] = "error"
    value: Any = None


class GraphValidationResult(BaseModel):
    """Strict validation output suitable for an API response or persisted audit."""

    ok: bool
    graph: dict[str, Any]
    issues: list[GraphValidationIssue] = Field(default_factory=list)


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
