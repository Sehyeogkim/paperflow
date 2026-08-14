"""Deterministic interview orchestration and localized graph patching."""
from __future__ import annotations

from typing import Iterable

from ..compile.claim_graph import validate_strict
from ..schemas.claim import ClaimGraph
from .audit import audit_graph
from .models import (
    AnswerCompletion,
    AnswerEvent,
    EdgeUpdate,
    GraphPatch,
    InterviewQuestion,
    InterviewState,
    InterviewTurnResult,
    NodeUpdate,
)

_TACIT_KINDS = {"threshold", "pitfall", "decision"}
_DEFAULT_CAPTURE = {
    "threshold": ["decision_rule", "observable_signal", "transfer_condition"],
    "pitfall": ["check", "symptom", "failure_mode", "reproducibility_risk"],
    "decision": ["rationale", "alternatives_rejected", "rejection_reason", "constraint"],
}
_RISK_PRIORITY = {"high": 300, "medium": 200, "low": 100}


def _question_text(kind: str, label: str) -> str:
    if kind == "threshold":
        return f"{label}을(를) 정하는 기준은 무엇이며, 잘못 정했을 때 가장 먼저 보이는 신호는 무엇입니까?"
    if kind == "pitfall":
        return f"{label}에서 무엇을 확인하며, 결과가 틀렸다는 것을 무엇을 보고 압니까?"
    return f"{label}을(를) 선택한 이유와 검토했다가 버린 대안은 무엇입니까?"


def _component_touches_claim(graph: ClaimGraph, start: str) -> bool:
    adjacency: dict[str, set[str]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.src, set()).add(edge.dst)
        adjacency.setdefault(edge.dst, set()).add(edge.src)
    seen, frontier = {start}, [start]
    while frontier:
        current = frontier.pop(0)
        node = graph.node(current)
        if node and node.kind == "claim":
            return True
        for nxt in sorted(adjacency.get(current, set())):
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return False


def questions_from_graph(graph: ClaimGraph) -> list[InterviewQuestion]:
    """Create stable, ranked questions from unresolved tacit knowledge slots."""
    questions: list[InterviewQuestion] = []
    for node in graph.nodes:
        if node.kind not in _TACIT_KINDS:
            continue
        if node.knowledge_status not in {"unverified", "missing", "partial", "unknown"}:
            continue
        connected = len(graph.edges_into(node.id)) + len(graph.edges_out(node.id))
        priority = _RISK_PRIORITY[node.risk] + min(connected, 5) * 10
        if _component_touches_claim(graph, node.id):
            priority += 50
        questions.append(InterviewQuestion(
            id=f"Q-{node.id}", target_node_id=node.id, kind=node.kind,
            text=node.question.strip() or _question_text(node.kind, node.text),
            why_it_matters=node.why_it_matters,
            risk=node.risk,
            must_capture=node.must_capture or list(_DEFAULT_CAPTURE[node.kind]),
            priority=priority,
            created_revision=graph.revision,
        ))
    return sorted(questions, key=lambda q: (-q.priority, q.id))


def start_interview(graph: ClaimGraph, state: InterviewState | None = None) -> InterviewState:
    """Start or resume an interview without deleting prior questions or answers."""
    current = state.model_copy(deep=True) if state else InterviewState(graph_revision=graph.revision)
    if state and state.graph_revision > graph.revision:
        raise ValueError("interview state is newer than the supplied graph")
    existing = {q.id for q in current.questions}
    for question in questions_from_graph(graph):
        if question.id not in existing:
            current.questions.append(question)
            existing.add(question.id)
    current.graph_revision = graph.revision
    return current


def _append_unique_refs(existing: list[dict], additions: Iterable[dict]) -> list[dict]:
    out = list(existing)
    fingerprints = {(r.get("source_type"), r.get("asset_id"), r.get("locator"),
                     r.get("quote_hash"), r.get("metadata", {}).get("answer_id")) for r in out}
    for ref in additions:
        fp = (ref.get("source_type"), ref.get("asset_id"), ref.get("locator"),
              ref.get("quote_hash"), ref.get("metadata", {}).get("answer_id"))
        if fp not in fingerprints:
            out.append(ref)
            fingerprints.add(fp)
    return out


def apply_graph_patch(graph: ClaimGraph, patch: GraphPatch) -> ClaimGraph:
    """Apply only revision-checked updates to existing nodes/edges, then validate strictly."""
    if graph.revision != patch.base_revision:
        raise ValueError(f"stale graph revision: expected {graph.revision}, got {patch.base_revision}")
    if patch.target_revision != patch.base_revision + 1:
        raise ValueError("target_revision must increment base_revision by exactly one")
    if any(not edge.id for edge in graph.edges):
        raise ValueError("graph edges must have stable ids before interview patching")

    raw = graph.model_dump()
    nodes = {n["id"]: n for n in raw["nodes"]}
    edges = {e["id"]: e for e in raw["edges"]}
    allowed_node_fields = {"detail", "knowledge_status", "provenance", "last_modified_revision"}
    allowed_edge_fields = {"grounding_status", "last_modified_revision"}

    for update in patch.node_updates:
        if update.id not in nodes:
            raise ValueError(f"patch targets unknown node: {update.id}")
        forbidden = set(update.set_fields) - allowed_node_fields
        if forbidden:
            raise ValueError(f"interview patch cannot update node fields: {sorted(forbidden)}")
        nodes[update.id].update(update.set_fields)
        nodes[update.id]["provenance_refs"] = _append_unique_refs(
            nodes[update.id].get("provenance_refs") or [], update.append_provenance_refs)

    for update in patch.edge_updates:
        if update.id not in edges:
            raise ValueError(f"patch targets unknown edge: {update.id}")
        forbidden = set(update.set_fields) - allowed_edge_fields
        if forbidden:
            raise ValueError(f"interview patch cannot update edge fields: {sorted(forbidden)}")
        edges[update.id].update(update.set_fields)
        edges[update.id]["provenance_refs"] = _append_unique_refs(
            edges[update.id].get("provenance_refs") or [], update.append_provenance_refs)

    raw["nodes"] = list(nodes.values())
    raw["edges"] = list(edges.values())
    raw["revision"] = patch.target_revision
    result = validate_strict(raw)
    if not result.ok:
        codes = ", ".join(issue.code for issue in result.issues if issue.severity == "error")
        raise ValueError(f"graph patch failed strict validation: {codes}")
    return ClaimGraph.model_validate(result.graph)


def _next_answer_id(state: InterviewState) -> str:
    used = {a.id for a in state.answers}
    index = len(state.answers) + 1
    while f"ANS-{index:04d}" in used:
        index += 1
    return f"ANS-{index:04d}"


def _followup_id(state: InterviewState, question_id: str) -> str:
    used = {q.id for q in state.questions}
    index = 1
    while f"{question_id}.F{index}" in used:
        index += 1
    return f"{question_id}.F{index}"


def answer_question(
    graph: ClaimGraph,
    state: InterviewState,
    *,
    question_id: str,
    answer: str = "",
    completion: AnswerCompletion = "complete",
    captured_fields: dict[str, str] | None = None,
    base_revision: int,
    supersedes_answer_id: str | None = None,
) -> InterviewTurnResult:
    """Append an answer event, patch its one tacit node, audit, and select the next question."""
    if graph.revision != base_revision or state.graph_revision != base_revision:
        raise ValueError("stale interview turn; reload graph and interview state")
    question = next((q for q in state.questions if q.id == question_id), None)
    if question is None:
        raise ValueError(f"unknown question: {question_id}")
    previous = [a for a in state.answers if a.question_id == question_id]
    if previous and supersedes_answer_id not in {a.id for a in previous}:
        raise ValueError("question already answered; provide supersedes_answer_id to correct it")
    if completion != "unknown" and not answer.strip() and not any(
        str(v).strip() for v in (captured_fields or {}).values()
    ):
        raise ValueError("a complete or partial answer cannot be empty")

    node = graph.node(question.target_node_id)
    if node is None or node.kind not in _TACIT_KINDS:
        raise ValueError(f"question target is not a tacit graph node: {question.target_node_id}")

    next_revision = base_revision + 1
    answer_id = _next_answer_id(state)
    fields = {str(k): str(v).strip() for k, v in (captured_fields or {}).items() if str(v).strip()}
    rendered = answer.strip()
    if fields:
        field_text = "\n".join(f"- {key}: {value}" for key, value in fields.items())
        rendered = f"{rendered}\n{field_text}".strip()
    # A correction replaces the canonical detail while the superseded text remains in
    # the immutable event log and provenance history.
    combined_detail = "" if supersedes_answer_id else node.detail.strip()
    if rendered and rendered not in combined_detail:
        combined_detail = f"{combined_detail}\n\n{rendered}".strip()

    status = {"complete": "author_attested", "partial": "partial", "unknown": "unknown"}[completion]
    grounding = {"complete": "grounded", "partial": "partial", "unknown": "missing"}[completion]
    provenance = {
        "source_type": "author",
        "locator": f"interview:{question_id}:{answer_id}",
        "quote": rendered,
        "verification_status": "author_attested",
        "metadata": {"answer_id": answer_id, "question_id": question_id},
    }
    related = [e for e in graph.edges_out(node.id)
               if e.rel in {"governs", "warns_about"}]
    patch = GraphPatch(
        base_revision=base_revision,
        target_revision=next_revision,
        reason=f"author interview answer {answer_id}",
        node_updates=[NodeUpdate(
            id=node.id,
            set_fields={"detail": combined_detail, "knowledge_status": status,
                        "provenance": "user_statement",
                        "last_modified_revision": next_revision},
            append_provenance_refs=[provenance],
        )],
        edge_updates=[EdgeUpdate(
            id=edge.id,
            set_fields={"grounding_status": grounding,
                        "last_modified_revision": next_revision},
            append_provenance_refs=[provenance],
        ) for edge in related],
    )
    patched_graph = apply_graph_patch(graph, patch)
    event = AnswerEvent(
        id=answer_id, question_id=question_id, target_node_id=node.id,
        text=answer.strip(), completion=completion, captured_fields=fields,
        base_graph_revision=base_revision, resulting_graph_revision=next_revision,
        supersedes_answer_id=supersedes_answer_id,
    )
    new_state = state.model_copy(deep=True)
    new_state.answers.append(event)
    new_state.graph_revision = next_revision

    if completion == "partial":
        missing = [field for field in question.must_capture if field not in fields]
        missing = missing or list(question.must_capture)
        followup = InterviewQuestion(
            id=_followup_id(new_state, question.id), target_node_id=node.id,
            kind=question.kind,
            text="추가 확인이 필요합니다: " + ", ".join(missing) + "을(를) 구체적으로 알려주세요.",
            why_it_matters=question.why_it_matters, risk=question.risk,
            must_capture=missing, priority=question.priority + 5,
            created_revision=next_revision, followup_of=question.id,
        )
        new_state.questions.append(followup)

    report = audit_graph(patched_graph)
    pending = new_state.pending_questions()
    return InterviewTurnResult(
        graph=patched_graph, state=new_state, answer_event=event,
        patch=patch, audit=report, next_question=pending[0] if pending else None,
    )
