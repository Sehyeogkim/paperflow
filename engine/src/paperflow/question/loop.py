"""Adaptive question loop — batch the highest-value gaps, persist answers, never hard-gate.

The loop is re-entrant: each call rebuilds gaps from the CURRENT graph/state, drops the
questions already answered, and returns the next small batch. Termination is by gap state
(no load-bearing gaps remain), not by question count. Unanswered load-bearing gaps are
returned as warnings — generation is always allowed to proceed.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..schemas.claim import ClaimGraph
from ..schemas.evidence_inventory import EvidenceInventory
from ..schemas.question import LOAD_BEARING, Question, QuestionBatch
from ..schemas.research_state import ResearchState
from . import gaps as gaps_mod
from . import rank as rank_mod

DEFAULT_BATCH = 4


def _answer_path(project_dir: str) -> Path:
    return Path(project_dir) / "main" / "answer.json"


def load_answers(project_dir: str) -> dict[str, str]:
    p = _answer_path(project_dir)
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text())
        return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_answers(project_dir: str, answers: dict[str, str]) -> dict[str, str]:
    """Merge new answers into main/answer.json (non-empty values only). Returns the merged map."""
    merged = load_answers(project_dir)
    for k, v in (answers or {}).items():
        if str(v).strip():
            merged[str(k)] = str(v).strip()
    p = _answer_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(merged, ensure_ascii=False, indent=2))
    return merged


def next_batch(graph: ClaimGraph | None,
               research_state: ResearchState | None = None,
               evidence_inventory: EvidenceInventory | None = None,
               answered: dict[str, str] | None = None,
               batch_size: int = DEFAULT_BATCH) -> QuestionBatch:
    """Compute the next adaptive question batch from the current graph/state."""
    answered = answered or {}
    found = gaps_mod.detect(graph, research_state, evidence_inventory)
    ranked = rank_mod.rank(found)
    pending = [q for q in ranked if q.id not in answered]

    load_bearing_open = [q for q in pending if q.load_bearing]
    batch = pending[:max(0, batch_size)]
    return QuestionBatch(
        questions=batch,
        remaining=max(0, len(pending) - len(batch)),
        terminated=not load_bearing_open,
        warnings=_warnings(found, answered),
    )


def _warnings(found, answered: dict[str, str]) -> list[str]:
    """Human-readable load-bearing gaps still unanswered (derived from gaps, not questions)."""
    out: list[str] = []
    for g in found:
        if g.kind not in LOAD_BEARING:
            continue
        qid = f"{g.kind}:{g.target_id or g.target_text[:40]}"
        if qid not in answered:
            out.append(f"{g.kind}: {g.target_text or g.target_id}".strip(": "))
    return out


def warnings_for(graph: ClaimGraph | None,
                 research_state: ResearchState | None = None,
                 evidence_inventory: EvidenceInventory | None = None,
                 answered: dict[str, str] | None = None) -> list[str]:
    """Load-bearing gaps still unanswered — recorded at generation time (not a gate)."""
    found = gaps_mod.detect(graph, research_state, evidence_inventory)
    return _warnings(found, answered or {})
