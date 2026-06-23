"""ClaimGraph + outline -> SectionContract (paragraph contracts), per section."""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt


def build(ps: ProjectState, graph: ClaimGraph, section: str) -> SectionContract:
    graph_block = json.dumps(graph.model_dump(), ensure_ascii=False, indent=2)
    user = (
        f"{inputs_block(ps)}\n\n## CLAIM GRAPH\n{graph_block}\n\n"
        f"## TARGET SECTION\n{section}"
    )
    raw = client.call_json("reasoning", prompt("contracts"), user,
                           step=f"contracts.{section}", max_tokens=4096)
    raw.setdefault("section", section)
    for p in raw.get("paragraphs", []):
        if isinstance(p, dict):
            p.setdefault("section", section)  # LLM often sets section only at top level
    return SectionContract.model_validate(raw)
