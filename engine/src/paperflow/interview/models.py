"""API-facing models for graph questions, append-only answers, patches, and audits."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.claim import ClaimGraph

QuestionKind = Literal["threshold", "pitfall", "decision", "requirement"]
AnswerCompletion = Literal["complete", "partial", "unknown"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InterviewQuestion(BaseModel):
    id: str
    target_node_id: str
    kind: QuestionKind
    text: str
    why_it_matters: str = ""
    risk: Literal["low", "medium", "high"] = "medium"
    must_capture: list[str] = Field(default_factory=list)
    priority: int = 0
    created_revision: int = 0
    followup_of: str | None = None


class AnswerEvent(BaseModel):
    """An immutable event; corrections are new events, never in-place edits."""

    model_config = ConfigDict(frozen=True)

    id: str
    question_id: str
    target_node_id: str
    text: str = ""
    completion: AnswerCompletion
    captured_fields: dict[str, str] = Field(default_factory=dict)
    source: Literal["author", "system"] = "author"
    created_at: datetime = Field(default_factory=utc_now)
    base_graph_revision: int
    resulting_graph_revision: int
    supersedes_answer_id: str | None = None


class NodeUpdate(BaseModel):
    id: str
    set_fields: dict[str, Any] = Field(default_factory=dict)
    append_provenance_refs: list[dict[str, Any]] = Field(default_factory=list)


class EdgeUpdate(BaseModel):
    id: str
    set_fields: dict[str, Any] = Field(default_factory=dict)
    append_provenance_refs: list[dict[str, Any]] = Field(default_factory=list)


class GraphPatch(BaseModel):
    """A revision-checked localized mutation description.

    Interview answers update an existing tacit node and its outgoing governance/risk
    edges only. Generic add/delete operations intentionally do not belong to this API.
    """

    base_revision: int
    target_revision: int
    reason: str = ""
    node_updates: list[NodeUpdate] = Field(default_factory=list)
    edge_updates: list[EdgeUpdate] = Field(default_factory=list)


class GraphAuditFinding(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "blocking"]
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)


class GraphAuditReport(BaseModel):
    graph_revision: int
    ok: bool
    findings: list[GraphAuditFinding] = Field(default_factory=list)
    metrics: dict[str, int] = Field(default_factory=dict)


class InterviewState(BaseModel):
    schema_version: str = "1.0"
    graph_revision: int = 0
    questions: list[InterviewQuestion] = Field(default_factory=list)
    answers: list[AnswerEvent] = Field(default_factory=list)

    def answered_question_ids(self) -> set[str]:
        return {a.question_id for a in self.answers}

    def pending_questions(self) -> list[InterviewQuestion]:
        answered = self.answered_question_ids()
        return sorted((q for q in self.questions if q.id not in answered),
                      key=lambda q: (-q.priority, q.id))


class InterviewTurnResult(BaseModel):
    graph: ClaimGraph
    state: InterviewState
    answer_event: AnswerEvent
    patch: GraphPatch
    audit: GraphAuditReport
    next_question: InterviewQuestion | None = None
