"""Deterministic completeness gate for planning and manuscript generation.

The requirement report is produced by an LLM, but enforcing it must not depend on
another model call.  This module therefore has deliberately small, fail-closed
rules that are shared by the web API and direct flow entry points.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..schemas.requirement import CompletionClass, MissingItem, RequirementReport
from . import detect


_EXACT_UNRESOLVED = {
    "", "-", "?", "모름", "모르겠음", "모르겠습니다", "미정", "알 수 없음",
    "확인 필요", "확인필요", "unknown", "i don't know", "i do not know",
    "don't know", "do not know", "not sure", "n/a", "na", "tbd", "pending",
    "later", "undecided",
}
_UNRESOLVED_PATTERNS = (
    re.compile(r"(?:모름|모르겠|알\s*수\s*없)"),
    re.compile(r"(?:나중에|추후|향후)\s*(?:보완|확인|제공|결정)?"),
    re.compile(r"(?:보완|확인|제공|결정)\s*(?:필요|예정)"),
    re.compile(r"\b(?:tbd|unknown|pending)\b", re.IGNORECASE),
    re.compile(r"\bto be (?:confirmed|determined|provided|added)\b", re.IGNORECASE),
    re.compile(r"\b(?:fill|add|confirm|decide) (?:in )?later\b", re.IGNORECASE),
)


def is_unresolved_answer(value: Any) -> bool:
    """Return True for blank answers and explicit deferrals/unknown placeholders.

    A substantive-looking answer that still says a critical value is unknown or
    will be supplied later remains unresolved.  This prevents a parenthetical
    placeholder from laundering a missing high-risk method detail through the gate.
    """
    if value is None:
        return True
    text = " ".join(str(value).strip().split())
    if text.casefold() in _EXACT_UNRESOLVED:
        return True
    return any(pattern.search(text) for pattern in _UNRESOLVED_PATTERNS)


def _load_answers(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir) / "main" / "answer.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text())
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _question(item: MissingItem) -> dict[str, Any]:
    return {
        "id": item.field,
        "field": item.field,
        "question": item.question,
        "example": item.example,
        "reviewer_risk": item.reviewer_risk,
        "why_it_matters": item.why_it_matters,
        "status": "unresolved",
    }


@dataclass(frozen=True)
class PreflightResult:
    allowed: bool
    error: str | None
    classification: str | None
    questions: list[dict[str, Any]]

    @property
    def pending(self) -> list[str]:
        return [str(question["field"]) for question in self.questions]

    def payload(self) -> dict[str, Any]:
        """Stable API/error representation; ``pending`` keeps the old UI working."""
        out: dict[str, Any] = {
            "allowed": self.allowed,
            "classification": self.classification,
            "questions": self.questions,
            "pending": self.pending,
        }
        if self.error:
            out["error"] = self.error
        return out


class PreflightBlocked(RuntimeError):
    """Raised when a direct flow call bypasses an API-level completeness check."""

    def __init__(self, result: PreflightResult):
        self.result = result
        super().__init__(result.error or "requirement_preflight_blocked")


def evaluate(project_dir: str | Path, *, require_report: bool = True) -> PreflightResult:
    """Evaluate whether critical requirement information is sufficient to proceed.

    ``require_report=False`` is used only by the graph-confirmation API so legacy
    graph-only clients remain compatible.  When a report exists, its high-risk and
    insufficient-evidence rules are always enforced.
    """
    report: RequirementReport | None = detect.load_report(str(project_dir))
    if report is None:
        return PreflightResult(
            allowed=not require_report,
            error="requirement_report_missing" if require_report else None,
            classification=None,
            questions=[],
        )

    answers = _load_answers(project_dir)
    unresolved = [
        item for item in report.missing
        if item.reviewer_risk.strip().lower() == "high"
        and is_unresolved_answer(answers.get(item.field))
    ]
    classification = report.classification.value

    if report.classification == CompletionClass.INSUFFICIENT_EVIDENCE:
        # Include actionable questions even if the detector did not label them high risk.
        actionable = [
            item for item in report.missing
            if item.question and is_unresolved_answer(answers.get(item.field))
        ]
        return PreflightResult(
            allowed=False,
            error="insufficient_evidence",
            classification=classification,
            questions=[_question(item) for item in (actionable or unresolved)],
        )

    if unresolved:
        return PreflightResult(
            allowed=False,
            error="unanswered_questions",
            classification=classification,
            questions=[_question(item) for item in unresolved],
        )

    return PreflightResult(
        allowed=True, error=None, classification=classification, questions=[])


def require_allowed(project_dir: str | Path, *, require_report: bool = True) -> PreflightResult:
    result = evaluate(project_dir, require_report=require_report)
    if not result.allowed:
        raise PreflightBlocked(result)
    return result
