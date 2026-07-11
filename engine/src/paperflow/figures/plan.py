"""Figure PLANNING only (no image generation).

Figure-first (Whitesides): the claim graph already designed which evidence is shown as a
figure/table (artifact nodes with represented_as). We derive the figure_spec from those
artifact nodes so the writer references them as it drafts. If the graph has no artifacts
(e.g. graph build failed), fall back to the author's figures/2_figure_flow.md.

Generation (fal.ai nanobanana pro via FAL_KEY) is a separate later stage.
"""
from __future__ import annotations

import json
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
            "shown_texts": [t for t in shown_texts if t],
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


def _enrich_image_prompts(figures: list[dict]) -> None:
    """Replace the template generation_prompt with an LLM-crafted, detailed image-gen system
    prompt per figure (the thing the author pastes into nanobanana pro / GPT image). One call;
    on any failure the deterministic template prompt is kept."""
    if not figures:
        return
    from ..llm import client
    from ..util import prompt as _prompt
    payload = [{"id": f["id"], "kind": f.get("kind", "figure"), "message": f.get("message", ""),
                "visualizes": [str(t) for t in (f.get("shown_texts") or [])]} for f in figures]
    try:
        raw = client.call_json("fast", _prompt("figure_image_prompt"),
                               "## PLANNED VISUALS\n" + json.dumps(payload, ensure_ascii=False),
                               step="figure.image_prompt", max_tokens=2500, effort="low")
    except Exception:
        return
    by_id = {str(x.get("id")): str(x.get("image_prompt", "")).strip()
             for x in (raw.get("figures") or []) if x.get("id")}
    for f in figures:
        ip = by_id.get(f["id"])
        if ip:
            f["generation_prompt"] = ip


def plan(project_dir: str, graph: ClaimGraph | None = None) -> dict:
    figures = _from_graph(graph) if graph is not None else []
    if not figures:  # fallback when the graph designed no artifacts
        figures = _from_markdown(project_dir)
    _enrich_image_prompts(figures)   # template prompt -> detailed image-gen system prompt (LLM)
    return {"generation": "deferred (fal.ai nano-banana pro)", "figures": figures}
