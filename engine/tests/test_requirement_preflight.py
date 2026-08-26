import json

import pytest

from paperflow.flows import method_result
from paperflow.requirement import preflight
from paperflow.schemas.requirement import (
    CompletionClass,
    MissingItem,
    RequirementReport,
)


def _write_report(project, *, classification=CompletionClass.MISSING_CRITICAL_INFORMATION,
                  risk="high"):
    report = RequirementReport(
        study_type="computational_biomechanics",
        classification=classification,
        missing=[MissingItem(
            field="boundary_conditions",
            question="What boundary conditions were used?",
            example="Measured inlet waveform and outlet Windkessel model",
            reviewer_risk=risk,
            why_it_matters="The simulation cannot be reproduced without them.",
        )],
    )
    main = project / "main"
    main.mkdir(parents=True, exist_ok=True)
    (main / "requirement_report.json").write_text(report.model_dump_json(indent=2))


@pytest.mark.parametrize("answer", [
    "", "모름", "(모름 — 나중에 보완)", "정확한 값은 추후 제공 예정",
    "unknown", "TBD", "to be confirmed",
])
def test_high_risk_unknown_or_deferred_answers_remain_blocking(tmp_path, answer):
    project = tmp_path / "paper"
    _write_report(project)
    (project / "main" / "answer.json").write_text(json.dumps({
        "boundary_conditions": answer,
    }, ensure_ascii=False))

    result = preflight.evaluate(project)

    assert result.allowed is False
    assert result.error == "unanswered_questions"
    assert result.classification == "MISSING_CRITICAL_INFORMATION"
    assert result.pending == ["boundary_conditions"]
    assert result.questions[0]["question"].startswith("What boundary")


def test_substantive_high_risk_answer_allows_preflight(tmp_path):
    project = tmp_path / "paper"
    _write_report(project)
    (project / "main" / "answer.json").write_text(json.dumps({
        "boundary_conditions": "Measured inlet waveform; three-element Windkessel outlets.",
    }))

    result = preflight.evaluate(project)

    assert result.allowed is True
    assert result.classification == "MISSING_CRITICAL_INFORMATION"
    assert result.questions == []


def test_missing_report_fails_closed_and_direct_plan_does_not_ingest(tmp_path, monkeypatch):
    project = tmp_path / "paper"
    (project / "main").mkdir(parents=True)
    monkeypatch.setattr(method_result, "ingest", lambda *_: pytest.fail("ingest must not run"))

    with pytest.raises(preflight.PreflightBlocked) as caught:
        method_result.plan(str(project), ["method"], litsearch=False)

    assert caught.value.result.error == "requirement_report_missing"
    assert caught.value.result.classification is None
    assert caught.value.result.questions == []


def test_insufficient_evidence_always_blocks_even_with_an_answer(tmp_path):
    project = tmp_path / "paper"
    _write_report(project, classification=CompletionClass.INSUFFICIENT_EVIDENCE)
    (project / "main" / "answer.json").write_text(json.dumps({
        "boundary_conditions": "Measured inlet waveform and Windkessel outlets.",
    }))

    result = preflight.evaluate(project)

    assert result.allowed is False
    assert result.error == "insufficient_evidence"
    assert result.classification == "INSUFFICIENT_EVIDENCE"
    assert result.questions == []


def test_direct_generate_from_saved_plan_cannot_bypass_preflight(tmp_path):
    project = tmp_path / "paper"
    _write_report(project)
    method_result.save_plan(str(project), {"sections": ["method"]})

    with pytest.raises(preflight.PreflightBlocked) as caught:
        method_result.generate_from_plan(str(project), project / "out")

    assert caught.value.result.error == "unanswered_questions"
    assert caught.value.result.pending == ["boundary_conditions"]
