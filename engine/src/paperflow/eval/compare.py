"""Compare generated output vs the answer-key thesis sections.

Deterministic structural comparison (no LLM): section presence, length, citation/figure/
equation/data-reference counts, and placeholder counts (how much was left as [DATA_NEEDED]
/ [cite:what_I_need] instead of fabricated). Writes a markdown report for human eval.

Answer key mapping: method <- main/ch2_method1.md + main/ch3_method2.md ; result <- main/ch4_result.md
"""
from __future__ import annotations

import re
from pathlib import Path

_ANSWER = {
    "introduction": ["main/ch1_Intro.md"],
    "method": ["main/ch2_method1.md", "main/ch3_method2.md"],
    "result": ["main/ch4_result.md"],
    "conclusion": ["main/ch6_conclusion.md"],
}


def _stats(text: str) -> dict:
    return {
        "chars": len(text),
        "words": len(text.split()),
        "headings": len(re.findall(r"(?m)^#{1,4}\s", text)),
        "citations": len(re.findall(r"\[cite:", text)),
        "cite_needed": len(re.findall(r"\[cite:\s*what_i_need", text, re.I)),
        "figures": len(re.findall(r"\(Fig", text)) + len(re.findall(r"\bFig\.?\s*\d", text)),
        # block ($$..$$) + \tag{} + inline ($..$, single-line, non-empty)
        "equations": (len(re.findall(r"\$\$", text)) // 2
                      + len(re.findall(r"\\tag\{", text))
                      + len(re.findall(r"(?<!\$)\$[^$\n]+\$(?!\$)", text))),
        "tables": len(re.findall(r"(?m)^\|", text)),
        "data_needed": len(re.findall(r"\[DATA_NEEDED", text)),
    }


def _read(project: Path, rels: list[str]) -> str:
    return "\n\n".join((project / r).read_text() for r in rels if (project / r).is_file())


def compare_report(project_dir: str, out_dir: Path) -> Path:
    project = Path(project_dir)
    lines = ["# paperflow output vs answer-key — comparison", ""]
    for section, rels in _ANSWER.items():
        gen_path = out_dir / f"{section.capitalize()}.md"
        if not gen_path.is_file():
            continue
        gen = _stats(gen_path.read_text())
        ans = _stats(_read(project, rels))
        lines += [
            f"## {section}",
            f"answer key: {', '.join(rels)}",
            "",
            "| metric | generated | answer key |",
            "|---|---:|---:|",
            *[f"| {k} | {gen[k]} | {ans[k]} |" for k in gen],
            "",
            f"_placeholders left (not fabricated): cite_needed={gen['cite_needed']}, "
            f"data_needed={gen['data_needed']}_",
            "",
        ]
    report = out_dir / "comparison.md"
    report.write_text("\n".join(lines))
    return report
