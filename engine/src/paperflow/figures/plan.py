"""Figure PLANNING only (no image generation).

Figure-first (Whitesides): the claim graph already designed which evidence is shown as a
figure/table (artifact nodes with represented_as). We derive the figure_spec from those
artifact nodes so the writer references them as it drafts. If the graph has no artifacts
(e.g. graph build failed), fall back to the author's figures/2_figure_flow.md.

Generation (fal.ai nanobanana pro via FAL_KEY) is a separate later stage.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..schemas.claim import ClaimGraph


def _caption_and_prompt(kind: str, message: str, shown: list[str]) -> tuple[str, str]:
    """Deterministic caption draft + generation prompt (MVP: no real image is made)."""
    shown_txt = "; ".join(t for t in shown if t)
    caption = message.strip()
    if shown_txt:
        caption = f"{caption} ({shown_txt})" if caption else shown_txt
    prompt = (
        f"Produce a publication-quality {kind} that conveys ONE message: "
        f"\"{message.strip()}\"."
    )
    if shown_txt:
        prompt += f" It should visualize: {shown_txt}."
    prompt += (" Use only the author's real data; do not fabricate values. "
               "Label axes/units; keep it self-contained via the caption.")
    return caption, prompt


def _from_graph(graph: ClaimGraph) -> list[dict]:
    figures: list[dict] = []
    for n in graph.artifacts:
        if n.represented_as not in ("figure", "table"):
            continue
        # which evidence does this artifact visualize?
        shows = [e.dst for e in graph.edges if e.src == n.id and e.rel == "visualizes"]
        shown_texts = [(graph.node(d).text if graph.node(d) else d) for d in shows]
        caption, gen_prompt = _caption_and_prompt(n.represented_as, n.text, shown_texts)
        figures.append({
            "id": n.id,
            "kind": n.represented_as,
            "message": n.text,
            "section": n.section or "",
            "visualizes": shows,
            "caption_draft": caption,
            "generation_prompt": gen_prompt,
            "status": "planned",
            "source": "claim_graph",
        })
    return figures


def _from_markdown(project_dir: str) -> list[dict]:
    figures: list[dict] = []
    p = Path(project_dir) / "figures" / "2_figure_flow.md"
    if p.is_file():
        md = p.read_text()
        for m in re.finditer(r"(?im)^#{0,4}\s*(fig(?:ure)?\.?\s*\d+[a-z]?)\b[:\-—\s]*(.*)$", md):
            msg = m.group(2).strip()
            caption, gen_prompt = _caption_and_prompt("figure", msg, [])
            figures.append({
                "id": m.group(1).strip(),
                "kind": "figure",
                "message": msg,
                "panels": [],
                "caption_draft": caption,
                "generation_prompt": gen_prompt,
                "status": "planned",
                "source": "figures/2_figure_flow.md",
            })
    return figures


def plan(project_dir: str, graph: ClaimGraph | None = None) -> dict:
    figures = _from_graph(graph) if graph is not None else []
    if not figures:  # fallback when the graph designed no artifacts
        figures = _from_markdown(project_dir)
    return {"generation": "deferred (fal.ai nano-banana pro)", "figures": figures}
