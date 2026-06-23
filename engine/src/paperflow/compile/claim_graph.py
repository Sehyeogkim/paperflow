"""core message + outline -> ClaimGraph (reasoning tier)."""
from __future__ import annotations

from ..llm import client
from ..schemas.claim import ClaimGraph
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt


def build(ps: ProjectState) -> ClaimGraph:
    raw = client.call_json("reasoning", prompt("claim_graph"), inputs_block(ps),
                           step="claim_graph", max_tokens=4096)
    return ClaimGraph.model_validate(raw)
