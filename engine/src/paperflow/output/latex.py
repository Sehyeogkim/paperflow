"""Assemble the drafted section markdown into an Elsevier `elsarticle` manuscript (paper.tex).

Matches the author's real CiBM submission format (see reference_elsarticle.tex):
  - \\documentclass[preprint,12pt]{elsarticle} + \\begin{frontmatter} (title/author/affiliation/
    abstract/keyword)
  - body \\section{} flow continuously (NO \\clearpage between them — that is thesis \\chapter style)
  - inline thebibliography (numbered, elsarticle-num default)
Compile with XeLaTeX/LuaLaTeX (kotex) for the Korean draft.
"""
from __future__ import annotations

import re

# proper journal reading order (abstract handled in the frontmatter)
_BODY_ORDER = ["introduction", "method", "result", "discussion", "conclusion"]
_TITLE = {"introduction": "Introduction", "method": "Methods", "result": "Results",
          "discussion": "Discussion", "conclusion": "Conclusion"}

_PREAMBLE = r"""\documentclass[preprint,12pt]{elsarticle}
\usepackage{amssymb}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{makecell}
\usepackage{multirow}
\usepackage{kotex}            % Korean draft — compile with XeLaTeX or LuaLaTeX"""

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


def _esc_fig(s: str) -> str:
    """Stricter escape for plain figure-box text (no math passthrough): also handle $ < > { }."""
    s = _esc(s or "")
    for a, b in (("$", "\\$"), ("<", "\\textless "), (">", "\\textgreater "),
                 ("{", "\\{"), ("}", "\\}")):
        s = s.replace(a, b)
    return s


def _figures_block(figures) -> str:
    """Render each PLANNED figure/table as a bordered placeholder box: the box holds a
    description of WHAT to draw, and the caption/title sits underneath. No real images (MVP)."""
    figs = list(figures or [])
    if not figs:
        return ""
    parts = ["\\clearpage", "\\section*{Figures \\& Tables — placeholders (to be created)}"]
    fig_n, tab_n = 0, 0
    for f in figs:
        is_table = (f.get("kind") == "table")
        if is_table:
            tab_n += 1
            label = f"Table {tab_n}"
        else:
            fig_n += 1
            label = f"Figure {fig_n}"
        desc = _esc_fig((f.get("message") or "").strip())
        detail = _esc_fig((f.get("generation_prompt") or "").strip()[:220])
        cap = _esc_fig((f.get("caption_draft") or f.get("message") or "").strip())
        sec = _esc_fig((f.get("section") or "").strip())
        inner = (f"\\textbf{{[{label} — 여기에 이 그림을 그리세요]}}\\\\[8pt]\n{desc}"
                 + (f"\\\\[8pt]{{\\small\\itshape {detail}}}" if detail else ""))
        parts.append(
            "\\begin{center}\n"
            f"\\fbox{{\\parbox[c][5cm][c]{{0.82\\linewidth}}{{\\centering {inner}}}}}\\\\[5pt]\n"
            f"\\textbf{{{label}.}} {cap}" + (f"\\quad{{\\small($\\rightarrow$ {sec})}}" if sec else "")
            + "\n\\end{center}\n\\vspace{10pt}"
        )
    return "\n".join(parts)


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
            line += f" DOI: {_esc(doi)}"
        items.append(line)
    if not items:
        return ""
    return "\\begin{thebibliography}{99}\n" + "\n".join(items) + "\n\\end{thebibliography}"


def _frontmatter(meta: dict, sections: dict[str, str]) -> str:
    """elsarticle \\begin{frontmatter}: title, authors (+corresponding), affiliation,
    abstract, keywords."""
    title = _esc(meta.get("title") or "Untitled Manuscript")
    affil = _esc(meta.get("affiliation") or meta.get("field") or "")
    corr = (meta.get("corresponding") or "").strip()
    authors = [a.strip() for a in re.split(r"[;,/]|\band\b", meta.get("authors") or "") if a.strip()]
    authors = authors or ["Anonymous"]
    corr_idx = -1
    if corr:
        tok = corr.split()[0]
        corr_idx = next((i for i, n in enumerate(authors) if tok and tok in n), len(authors) - 1)
    p = ["\\begin{frontmatter}", f"\\title{{{title}}}"]
    for i, n in enumerate(authors):
        p.append(f"\\author[label1]{{{_esc(n)}}}" + ("\\corref{cor1}" if i == corr_idx else ""))
    if corr_idx >= 0:
        p.append("\\cortext[cor1]{Corresponding author}")
    p.append(f"\\affiliation[label1]{{organization={{{affil}}}, country={{}}}}")
    if sections.get("abstract", "").strip():
        p += ["\\begin{abstract}", _body(sections["abstract"]), "\\end{abstract}"]
    kws = [k for k in (meta.get("keywords") or []) if str(k).strip()]
    if kws:
        p.append("\\begin{keyword}\n" + " \\sep ".join(_esc(str(k)) for k in kws) + "\n\\end{keyword}")
    p.append("\\end{frontmatter}")
    return "\n".join(p)


def assemble(sections: dict[str, str], reference_table=None, found_references=None,
             meta: dict | None = None, figures=None) -> str:
    """Build the full elsarticle paper.tex from the section markdown + all cited references.
    `figures` (figure_spec['figures']) are rendered as end-matter placeholder boxes."""
    meta = meta or {}
    journal = _esc(meta.get("journal") or "")
    head = _PREAMBLE + (f"\n\\journal{{{journal}}}" if journal else "")
    parts = [head, "\\begin{document}", _frontmatter(meta, sections)]
    for sec in _BODY_ORDER:  # body sections flow continuously (no \clearpage)
        if sections.get(sec, "").strip():
            parts += [f"\\section{{{_TITLE[sec]}}}", _body(sections[sec])]
    bib = _bibliography(reference_table, found_references)
    if bib:
        parts.append(bib)
    figblock = _figures_block(figures)
    if figblock:
        parts.append(figblock)
    parts.append("\\end{document}")
    return "\n\n".join(parts) + "\n"
