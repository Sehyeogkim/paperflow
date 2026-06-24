"""Assemble the drafted section markdown into a single LaTeX manuscript (paper.tex).

The prose already uses LaTeX math ($...$). This converts headings, citation markers and
data-needed markers to LaTeX, escapes specials in plain prose (leaving math untouched),
and wraps everything in an article skeleton + a thebibliography built from reference_table.
Compile with XeLaTeX/LuaLaTeX (kotex) for the Korean draft.
"""
from __future__ import annotations

import re

# proper journal reading order (abstract handled separately)
_BODY_ORDER = ["introduction", "method", "result", "discussion", "conclusion"]
_TITLE = {"introduction": "Introduction", "method": "Methods", "result": "Results",
          "discussion": "Discussion", "conclusion": "Conclusion"}

_PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage[hidelinks]{hyperref}
\usepackage{kotex}            % Korean draft — compile with XeLaTeX or LuaLaTeX
\usepackage[margin=1in]{geometry}"""

_MATH = re.compile(r"(\$\$.*?\$\$|\$[^$]*?\$)", re.DOTALL)
_CITE_NEED = re.compile(r"\[cite:\s*what_i_need\s*[—\-:]\s*([^\]]+)\]", re.IGNORECASE)
_DATA_NEED = re.compile(r"\[DATA_NEEDED:\s*([^\]]+)\]", re.IGNORECASE)
_CITE = re.compile(r"\[cite:\s*([^\]]+?)\]", re.IGNORECASE)

_ESCAPES = (("\\", "\\textbackslash "), ("&", "\\&"), ("%", "\\%"), ("#", "\\#"),
            ("_", "\\_"), ("~", "\\textasciitilde "), ("^", "\\textasciicircum "))


def _esc(s: str) -> str:
    for a, b in _ESCAPES:
        s = s.replace(a, b)
    return s


def _inline(text: str) -> str:
    """Convert one prose line to LaTeX: protect math, convert markers, escape the rest."""
    math: list[str] = []
    text = _MATH.sub(lambda m: math.append(m.group(0)) or f"\x00MA{len(math)-1}\x00", text)

    holds: list[str] = []

    def hold(latex: str) -> str:
        holds.append(latex)
        return f"\x00MK{len(holds)-1}\x00"

    text = _CITE_NEED.sub(lambda m: hold(r"\textbf{[CITATION NEEDED: " + _esc(m.group(1).strip()) + "]}"), text)
    text = _DATA_NEED.sub(lambda m: hold(r"\textbf{[DATA NEEDED: " + _esc(m.group(1).strip()) + "]}"), text)
    text = _CITE.sub(lambda m: hold(r"\cite{" + re.sub(r"\s+", "", m.group(1)) + "}"), text)

    text = _esc(text)
    for i, h in enumerate(holds):
        text = text.replace(f"\x00MK{i}\x00", h)
    for i, mm in enumerate(math):
        text = text.replace(f"\x00MA{i}\x00", mm)
    return text


def _body(md: str) -> str:
    out: list[str] = []
    for line in md.splitlines():
        if not line.strip():
            out.append("")
            continue
        h = re.match(r"^#{2,4}\s+(.*)", line)
        out.append(r"\subsection{" + _esc(h.group(1).strip()) + "}" if h else _inline(line))
    return "\n".join(out).strip()


def _bibliography(reference_table, found_references) -> str:
    """Merge every cited source — literature-search finds + reference-hunter fills —
    into one \\bibitem list, deduped by key, so no \\cite resolves to [?]."""
    by_key: dict[str, dict] = {}
    for r in list(found_references or []) + list(reference_table or []):
        key = r.get("key")
        if key and key not in by_key:
            by_key[key] = r
    items = []
    for key, r in by_key.items():
        authors, title = _esc(r.get("authors", "")), _esc(r.get("title", ""))
        year = r.get("year") or "n.d."
        doi = r.get("doi", "")
        line = f"\\bibitem{{{key}}} {authors} ({year}). {title}."
        if doi:
            line += f" \\href{{https://doi.org/{doi}}}{{DOI: {doi}}}"
        items.append(line)
    if not items:
        return ""
    return "\\begin{thebibliography}{99}\n" + "\n".join(items) + "\n\\end{thebibliography}"


def assemble(sections: dict[str, str], reference_table=None, found_references=None,
             meta: dict | None = None) -> str:
    """Build the full paper.tex string from the section markdown + all cited references."""
    meta = meta or {}
    title = meta.get("title") or "Untitled Manuscript"
    authors = meta.get("authors") or ""
    parts = [_PREAMBLE, f"\\title{{{_esc(title)}}}", f"\\author{{{_esc(authors)}}}",
             "\\date{}", "\\begin{document}", "\\maketitle"]
    if sections.get("abstract", "").strip():
        parts += ["\\begin{abstract}", _body(sections["abstract"]), "\\end{abstract}"]
    for sec in _BODY_ORDER:
        if sections.get(sec, "").strip():
            parts += [f"\\section{{{_TITLE[sec]}}}", _body(sections[sec])]
    bib = _bibliography(reference_table, found_references)
    if bib:
        parts.append(bib)
    parts.append("\\end{document}")
    return "\n\n".join(parts) + "\n"
