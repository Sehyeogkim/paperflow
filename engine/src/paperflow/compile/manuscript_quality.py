"""Deterministic final-manuscript quality gate.

LLM review is useful for argument quality, but release-blocking mechanical defects must be
repeatable and cheap to detect.  Every finding returned here is deterministic and JSON-safe.
"""
from __future__ import annotations

import re
from typing import Iterable

_INTERNAL_ID = re.compile(
    r"(?<![A-Za-z0-9_])(?:[CMEDWFRL]\d+(?:\.\d+)*|(?:TH|PIT|DEC|PF)(?:_?[A-Z0-9]+)+)"
    r"(?![A-Za-z0-9_])"
)
_PLACEHOLDER = re.compile(
    r"\[(?:DATA[_ ]NEEDED|CITATION[_ ]NEEDED|cite:\s*what_i_need)\b|"
    r"\b(?:DATA|CITATION)[_ ]NEEDED\b",
    re.IGNORECASE,
)
_FAILED = re.compile(r"generation\s+failed|section\s+generation\s+failed", re.IGNORECASE)
_CITE_MD = re.compile(r"\[cite:\s*([^\]]+)\]", re.IGNORECASE)
_CITE_TEX = re.compile(r"\\cite\w*\{([^}]+)\}")
_BIBITEM = re.compile(r"\\bibitem\{([^}]+)\}")
_TABLE_ENV = re.compile(r"\\begin\{(?:table\*?|longtable)\}")
_FIGURE_ENV = re.compile(r"\\begin\{figure\*?\}")


def _finding(code: str, message: str, *, section: str = "", matches: Iterable[str] = ()) -> dict:
    finding = {"code": code, "severity": "blocking", "message": message}
    if section:
        finding["section"] = section
    unique = list(dict.fromkeys(str(item) for item in matches if str(item)))
    if unique:
        finding["matches"] = unique[:20]
    return finding


def _referenced_numbers(text: str, noun: str) -> set[int]:
    if noun == "table":
        prefix = r"Tables?"
    else:
        prefix = r"(?:Figures?|Figs?\.?)"
    refs: set[int] = set()
    # Capture the compact reference phrase only; stopping early avoids treating result values
    # or publication years later in the sentence as figure/table numbers.
    phrase = re.compile(
        rf"\b{prefix}\s+(\d+(?:\s*(?:,|and|&|[-–—])\s*\d+)*)",
        re.IGNORECASE,
    )
    for match in phrase.finditer(text):
        refs.update(int(value) for value in re.findall(r"\d+", match.group(1)))
    return refs


def inspect(sections: dict[str, str], latex_text: str = "") -> dict:
    """Return ``{ok, blocking_count, findings, metrics}`` for a finished manuscript.

    ``latex_text`` should be the assembled manuscript so table/figure environments and the
    bibliography can be verified.  Passing sections alone is supported for preflight use;
    any prose artifact reference is then correctly considered unresolved.
    """
    findings: list[dict] = []
    prose = "\n".join(sections.values())
    for section, text in sections.items():
        if not text.strip():
            findings.append(_finding("empty_section", "Required manuscript section is empty.",
                                     section=section))
            continue
        failed = _FAILED.findall(text)
        if failed:
            findings.append(_finding("failed_section", "Section contains a generation failure.",
                                     section=section, matches=failed))
        internal = _INTERNAL_ID.findall(text)
        if internal:
            findings.append(_finding(
                "internal_graph_id", "Internal knowledge-graph identifiers leaked into prose.",
                section=section, matches=internal,
            ))
        placeholders = _PLACEHOLDER.findall(text)
        if placeholders:
            findings.append(_finding(
                "unresolved_placeholder", "DATA/CITATION placeholder remains unresolved.",
                section=section, matches=placeholders,
            ))

    table_count = len(_TABLE_ENV.findall(latex_text))
    figure_count = len(_FIGURE_ENV.findall(latex_text))
    table_refs = _referenced_numbers(prose, "table")
    figure_refs = _referenced_numbers(prose, "figure")
    missing_tables = sorted(number for number in table_refs if number > table_count)
    missing_figures = sorted(number for number in figure_refs if number > figure_count)
    if missing_tables:
        findings.append(_finding(
            "dangling_table_reference",
            f"Prose references table number(s) with no materialized table (found {table_count}).",
            matches=[f"Table {number}" for number in missing_tables],
        ))
    if missing_figures:
        findings.append(_finding(
            "dangling_figure_reference",
            f"Prose references figure number(s) with no materialized figure (found {figure_count}).",
            matches=[f"Figure {number}" for number in missing_figures],
        ))

    cited: set[str] = set()
    for marker in _CITE_MD.findall(prose):
        if not marker.lower().lstrip().startswith("what_i_need"):
            cited.update(key.strip() for key in marker.split(",") if key.strip())
    for marker in _CITE_TEX.findall(latex_text):
        cited.update(key.strip() for key in marker.split(",") if key.strip())
    bibitems = {key.strip() for key in _BIBITEM.findall(latex_text)}
    for section in ("introduction", "discussion"):
        section_text = sections.get(section, "")
        section_citations = {
            key.strip()
            for marker in _CITE_MD.findall(section_text)
            if not marker.lower().lstrip().startswith("what_i_need")
            for key in marker.split(",") if key.strip()
        }
        if section_text.strip() and not section_citations:
            findings.append(_finding(
                "missing_section_citations",
                f"The {section} section has no resolved scholarly citations.",
                section=section,
            ))
    if cited and not bibitems:
        findings.append(_finding(
            "citation_without_bibliography",
            "The manuscript contains citations but no bibliography entries.",
            matches=sorted(cited),
        ))
    elif cited - bibitems:
        findings.append(_finding(
            "citation_without_entry",
            "One or more citation keys have no matching bibliography entry.",
            matches=sorted(cited - bibitems),
        ))

    return {
        "ok": not findings,
        "blocking_count": len(findings),
        "findings": findings,
        "metrics": {
            "sections": len(sections),
            "materialized_tables": table_count,
            "materialized_figures": figure_count,
            "citations": len(cited),
            "bibliography_entries": len(bibitems),
        },
    }


def validate_manuscript(sections: dict[str, str], latex_text: str = "") -> dict:
    """Descriptive alias for callers that treat the quality gate as validation."""
    return inspect(sections, latex_text)


check_manuscript = validate_manuscript
