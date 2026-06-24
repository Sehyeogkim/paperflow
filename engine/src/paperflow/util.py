"""Shared helpers: load prompt files, render the input context block for LLM calls."""
from __future__ import annotations

from pathlib import Path

from .schemas.project_state import ProjectState

_PROMPTS = Path(__file__).resolve().parents[2] / "prompts"


def prompt(name: str) -> str:
    return (_PROMPTS / f"{name}.txt").read_text()


def inputs_block(ps: ProjectState) -> str:
    """Compact, stable rendering of the author inputs — shared as the cacheable prefix."""
    cm = ps.core_message
    lines = [
        "## JOURNAL INFO",
        f"title: {ps.journal_info.working_title}",
        f"field: {ps.journal_info.author_field}",
        f"target: {ps.journal_info.target_journals}",
        "",
        "## CORE MESSAGE",
        f"one_sentence: {cm.one_sentence}",
        f"one_paragraph: {cm.one_paragraph}",
        "novelty / key claims:",
        *[f"  - {b}" for b in cm.summary_bullets],
    ]
    if cm.keywords:
        lines += [f"keywords: {', '.join(cm.keywords)}"]
    if cm.out_of_scope:
        lines += ["out_of_scope:", *[f"  - {b}" for b in cm.out_of_scope]]
    if ps.answers:
        lines += ["", "## AUTHOR ANSWERS (filled gaps — treat as author-provided fact)"]
        lines += [f"  - {k}: {v}" for k, v in ps.answers.items()]
    if ps.style:
        lines += ["", "## AUTHOR STYLE (writing constraints — follow these)", ps.style[:1500]]
    if ps.journal_constraints:
        lines += ["", "## JOURNAL CONSTRAINTS (target journal limits — obey)"]
        lines += [f"  - {k}: {v}" for k, v in ps.journal_constraints.items()]
    lines += ["", "## OUTLINE SKELETON (Phase A: one claim per paragraph)"]
    for p in ps.outline.skeleton:
        tag = f"[{p.section_label}] " if p.section_label else ""
        lines.append(f"  {p.n}. {tag}{p.claim_sentence}")
    if ps.outline.structured_raw:
        lines += ["", "## OUTLINE STRUCTURE (Phase B)", ps.outline.structured_raw[:4000]]
    lines += ["", "## DATA FILES PROVIDED"]
    if ps.data_assets:
        for d in ps.data_assets:
            cols = f" cols={d.columns}" if d.columns else ""
            note = f" — {d.note}" if d.note else ""
            lines.append(f"  - {d.path} ({d.kind}){cols}{note}")
    else:
        lines.append("  (none)")
    lines += ["", "## EXISTING REFERENCE KEYS", "  " + (", ".join(ps.reference_keys) or "(none)")]
    if ps.found_references:
        lines += ["", "## FOUND REFERENCES (real papers from literature search — citable as [cite:key])"]
        for r in ps.found_references:
            role = f" — {r.topic}" if r.topic else ""
            lines.append(f"  - [cite:{r.key}] {r.authors.split(',')[0]} {r.year or ''}: "
                         f"{r.title[:80]}{role}")
    return "\n".join(lines)
