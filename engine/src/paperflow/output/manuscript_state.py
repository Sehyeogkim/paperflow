"""Canonical manuscript state — the single source of record for a generated draft.

The backend canonical artifact is NOT the Word file; it is this structured state
(workflow_design.md §9). HTML preview and DOCX are both rendered FROM it, so they never
drift. Pure data + deterministic renderers (no LLM, no I/O) -> fully testable offline.
"""
from __future__ import annotations

import html
import re

from pydantic import BaseModel, Field

from ..schemas.claim import ClaimGraph

# reading order of the assembled manuscript
SECTION_ORDER = ["abstract", "introduction", "method", "result", "discussion", "conclusion"]
_SECTION_TITLE = {
    "abstract": "Abstract", "introduction": "Introduction", "method": "Methods",
    "result": "Results", "discussion": "Discussion", "conclusion": "Conclusion",
}


class ManuscriptMeta(BaseModel):
    title: str = ""
    authors: str = ""
    affiliation: str = ""
    journal: str = ""
    field: str = ""
    keywords: list[str] = Field(default_factory=list)
    classification: str = ""


class ManuscriptSection(BaseModel):
    name: str                    # canonical key (method, result, ...)
    title: str                   # display title (Methods, Results, ...)
    markdown: str = ""


class FigurePlaceholder(BaseModel):
    id: str
    kind: str = "figure"         # figure | table
    section: str = ""
    message: str = ""
    caption_draft: str = ""
    generation_prompt: str = ""
    status: str = "planned"      # MVP never renders a real image


class ReferenceEntry(BaseModel):
    key: str
    authors: str = ""
    year: int | None = None
    title: str = ""
    doi: str = ""


class ClaimGrounding(BaseModel):
    id: str
    text: str = ""
    status: str = "missing"      # grounded | partial | missing
    evidence_ids: list[str] = Field(default_factory=list)
    data_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)


class GroundingReport(BaseModel):
    claims: list[ClaimGrounding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        out = {"grounded": 0, "partial": 0, "missing": 0}
        for c in self.claims:
            out[c.status] = out.get(c.status, 0) + 1
        return out


class ManuscriptState(BaseModel):
    meta: ManuscriptMeta = Field(default_factory=ManuscriptMeta)
    sections: list[ManuscriptSection] = Field(default_factory=list)
    figures: list[FigurePlaceholder] = Field(default_factory=list)
    references: list[ReferenceEntry] = Field(default_factory=list)
    grounding: GroundingReport = Field(default_factory=GroundingReport)

    def section(self, name: str) -> ManuscriptSection | None:
        return next((s for s in self.sections if s.name == name), None)


# ---------- grounding ----------

def build_grounding(graph: ClaimGraph | None, warnings: list[str] | None = None) -> GroundingReport:
    """Per main-claim grounding status, derived from the claim graph's support edges."""
    rep = GroundingReport(warnings=list(warnings or []))
    if graph is None:
        return rep
    mains = [c for c in graph.claims if not c.parent_id] or graph.claims
    for c in mains:
        ev, data, refs = [], [], []
        for e in graph.edges_into(c.id):
            src = graph.node(e.src)
            if not src:
                continue
            if e.rel == "supports" and src.kind == "evidence":
                ev.append(src.id)
            elif e.rel in ("justifies", "qualifies") and src.kind in ("warrant", "source"):
                refs.append(src.id)
        # data behind the supporting evidence
        for eid in ev:
            for e in graph.edges_out(eid):
                d = graph.node(e.dst)
                if e.rel == "derived_from" and d and d.kind == "data":
                    data.append(d.id)
        if ev and (data or refs):
            status = "grounded"
        elif ev or data or refs:
            status = "partial"
        else:
            status = "missing"
        rep.claims.append(ClaimGrounding(
            id=c.id, text=c.text, status=status,
            evidence_ids=ev, data_ids=sorted(set(data)), reference_ids=refs))
    return rep


# ---------- build ----------

def _figures_from_spec(figure_spec: dict | None) -> list[FigurePlaceholder]:
    out: list[FigurePlaceholder] = []
    for f in (figure_spec or {}).get("figures", []) or []:
        if not isinstance(f, dict):
            continue
        out.append(FigurePlaceholder(
            id=str(f.get("id", "")), kind=f.get("kind", "figure"),
            section=f.get("section", "") or "", message=f.get("message", "") or "",
            caption_draft=f.get("caption_draft", "") or "",
            generation_prompt=f.get("generation_prompt", "") or "",
            status=f.get("status", "planned")))
    return out


def _references(reference_table=None, found_references=None) -> list[ReferenceEntry]:
    by_key: dict[str, ReferenceEntry] = {}
    for r in list(found_references or []) + list(reference_table or []):
        d = r if isinstance(r, dict) else r.model_dump()
        key = d.get("key")
        if key and key not in by_key:
            by_key[key] = ReferenceEntry(
                key=key, authors=d.get("authors", "") or "", year=d.get("year"),
                title=d.get("title", "") or "", doi=d.get("doi", "") or "")
    return list(by_key.values())


def build(sections: dict[str, str], *, graph: ClaimGraph | None = None,
          figure_spec: dict | None = None, meta: dict | None = None,
          reference_table=None, found_references=None,
          warnings: list[str] | None = None) -> ManuscriptState:
    """Assemble the canonical manuscript state from the generated pieces."""
    meta = meta or {}
    sec_models: list[ManuscriptSection] = []
    for name in SECTION_ORDER:
        md = sections.get(name)
        if md and md.strip():
            sec_models.append(ManuscriptSection(
                name=name, title=_SECTION_TITLE.get(name, name.capitalize()), markdown=md))
    # any non-standard sections, kept in input order after the standard ones
    for name, md in sections.items():
        if name not in SECTION_ORDER and md and md.strip():
            sec_models.append(ManuscriptSection(name=name, title=name.capitalize(), markdown=md))
    return ManuscriptState(
        meta=ManuscriptMeta(
            title=meta.get("title", ""), authors=meta.get("authors", ""),
            affiliation=meta.get("affiliation", ""), journal=meta.get("journal", ""),
            field=meta.get("field", ""), keywords=list(meta.get("keywords", []) or []),
            classification=meta.get("classification", "") or ""),
        sections=sec_models,
        figures=_figures_from_spec(figure_spec),
        references=_references(reference_table, found_references),
        grounding=build_grounding(graph, warnings),
    )


# ---------- renderers (markdown + read-only HTML preview) ----------

def to_markdown(ms: ManuscriptState) -> str:
    lines: list[str] = []
    if ms.meta.title:
        lines += [f"# {ms.meta.title}", ""]
    if ms.meta.authors:
        lines += [f"*{ms.meta.authors}*", ""]
    for s in ms.sections:
        if s.name == "abstract":
            lines += ["## Abstract", "", s.markdown.strip(), ""]
        else:
            lines += [f"## {s.title}", "", s.markdown.strip(), ""]
    if ms.figures:
        lines += ["## Figures & Tables (planned)", ""]
        for f in ms.figures:
            lines.append(f"- **{f.id}** ({f.kind}, {f.section or 'n/a'}): {f.caption_draft}")
        lines.append("")
    if ms.references:
        lines += ["## References", ""]
        for r in ms.references:
            yr = f" ({r.year})" if r.year else ""
            doi = f" DOI: {r.doi}" if r.doi else ""
            lines.append(f"- [{r.key}] {r.authors}{yr}. {r.title}.{doi}")
    return "\n".join(lines).strip() + "\n"


_MD_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"\*(.+?)\*"), r"<em>\1</em>"),
]


def _inline_html(text: str) -> str:
    out = html.escape(text)
    for pat, rep in _MD_INLINE:
        out = pat.sub(rep, out)
    return out


def _md_block_to_html(md: str) -> str:
    """Minimal, safe markdown -> HTML (headings, paragraphs, list items). Escapes everything."""
    parts: list[str] = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                parts.append("</ul>"); in_list = False
            continue
        h = re.match(r"^(#{1,4})\s+(.*)", line)
        li = re.match(r"^[-*]\s+(.*)", line)
        if h:
            if in_list:
                parts.append("</ul>"); in_list = False
            lvl = len(h.group(1))
            parts.append(f"<h{lvl}>{_inline_html(h.group(2))}</h{lvl}>")
        elif li:
            if not in_list:
                parts.append("<ul>"); in_list = True
            parts.append(f"<li>{_inline_html(li.group(1))}</li>")
        else:
            if in_list:
                parts.append("</ul>"); in_list = False
            parts.append(f"<p>{_inline_html(line)}</p>")
    if in_list:
        parts.append("</ul>")
    return "\n".join(parts)


_PREVIEW_CSS = """
<style>
.pf-preview{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#2D2D2D;
  line-height:1.6;max-width:760px;margin:0 auto;padding:8px 4px;}
.pf-preview h1{color:#1A1A1A;font-size:1.5rem;border-bottom:2px solid #CC785C;padding-bottom:6px;}
.pf-preview h2{color:#1A1A1A;font-size:1.2rem;margin-top:1.4em;}
.pf-preview h3{color:#6B5E54;font-size:1.05rem;}
.pf-preview .pf-authors{color:#6B5E54;font-style:italic;}
.pf-preview .pf-badge{display:inline-block;font-size:.72rem;padding:1px 7px;border-radius:8px;
  margin-left:6px;vertical-align:middle;}
.pf-preview .g-grounded{background:#7A9A6D;color:#fff;}
.pf-preview .g-partial{background:#E8D5C4;color:#6B5E54;}
.pf-preview .g-missing{background:#C25744;color:#fff;}
.pf-preview .pf-fig{background:#E6E0D4;border:1px dashed #D4C5B0;border-radius:6px;
  padding:10px 12px;margin:8px 0;font-size:.9rem;}
.pf-preview .pf-warn{background:#C2574420;border-left:3px solid #C25744;padding:8px 12px;
  margin:6px 0;font-size:.85rem;}
.pf-preview .pf-ref{font-size:.85rem;color:#6B5E54;}
</style>
"""


def to_html(ms: ManuscriptState) -> str:
    """Self-contained read-only HTML preview (rendered on the right pane of the UI)."""
    p: list[str] = [_PREVIEW_CSS, '<div class="pf-preview">']
    if ms.meta.title:
        p.append(f"<h1>{html.escape(ms.meta.title)}</h1>")
    if ms.meta.authors:
        p.append(f'<div class="pf-authors">{html.escape(ms.meta.authors)}</div>')
    if ms.grounding.warnings:
        for w in ms.grounding.warnings:
            p.append(f'<div class="pf-warn">⚠ {html.escape(w)}</div>')
    status_by_text = {c.text: c.status for c in ms.grounding.claims}
    for s in ms.sections:
        p.append(f"<h2>{html.escape(s.title)}</h2>")
        p.append(_md_block_to_html(s.markdown))
    figs_for = {}
    for f in ms.figures:
        figs_for.setdefault(f.section or "", []).append(f)
    if ms.figures:
        p.append("<h2>Figures &amp; Tables (planned)</h2>")
        for f in ms.figures:
            p.append(f'<div class="pf-fig"><strong>{html.escape(f.id)}</strong> '
                     f'({html.escape(f.kind)}{", " + html.escape(f.section) if f.section else ""}) — '
                     f'{html.escape(f.caption_draft or f.message)}</div>')
    if ms.references:
        p.append("<h2>References</h2><div class='pf-ref'>")
        for r in ms.references:
            yr = f" ({r.year})" if r.year else ""
            p.append(f"<div>[{html.escape(r.key)}] {html.escape(r.authors)}{yr}. "
                     f"{html.escape(r.title)}.</div>")
        p.append("</div>")
    # grounding footer
    s = ms.grounding.summary
    if ms.grounding.claims:
        p.append(f'<h2>Grounding</h2><div class="pf-ref">grounded: {s["grounded"]} · '
                 f'partial: {s["partial"]} · missing: {s["missing"]}</div>')
        for c in ms.grounding.claims:
            p.append(f'<div class="pf-ref">{html.escape(c.text[:90])} '
                     f'<span class="pf-badge g-{c.status}">{c.status}</span></div>')
    p.append("</div>")
    _ = status_by_text  # reserved for inline claim badges (future)
    return "\n".join(p)
