"""Propose a section structure (one-line summary + subheadings) for the Stage-3 confirm
step. ONE LLM call, before any prose — the user reviews/edits this, then contracts honor it.
"""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.claim import ClaimGraph
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt


def propose(ps: ProjectState, graph: ClaimGraph, sections: list[str]) -> dict:
    graph_block = json.dumps(graph.model_dump(), ensure_ascii=False)[:6000]
    user = (f"{inputs_block(ps)}\n\n## CLAIM GRAPH\n{graph_block}\n\n"
            f"## SECTIONS TO STRUCTURE\n{', '.join(sections)}")
    try:
        raw = client.call_json("reasoning", prompt("structure"), user,
                               step="structure", max_tokens=2000, effort="low")
    except Exception:
        raw = {}
    out: dict[str, dict] = {}
    for sec in sections:
        s = raw.get(sec) or raw.get(sec.capitalize()) or {}
        if isinstance(s, dict):
            heads = [str(h).strip() for h in (s.get("subheadings") or []) if str(h).strip()]
            out[sec] = {"summary": str(s.get("summary", "")).strip(), "subheadings": heads}
        else:
            out[sec] = {"summary": "", "subheadings": []}
    return out
