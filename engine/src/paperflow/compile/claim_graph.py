"""core message + outline -> ClaimGraph (reasoning tier).

The LLM occasionally emits out-of-vocabulary node kinds / edge relations (e.g. an edge
rel 'produces' or 'enables'). The typed schema is strict, so we coerce unknown values to
the nearest valid one and drop dangling edges BEFORE validation — one bad edge must never
crash a whole run.
"""
from __future__ import annotations

from ..llm import client
from ..schemas.claim import ClaimGraph
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt

_VALID_NODE = {"claim", "evidence", "artifact", "warrant", "method", "source"}
_VALID_EDGE = {"supports", "visualizes", "derived_from", "qualifies", "contradicts"}

# synonyms the model tends to produce -> canonical kind/rel (valid values map to themselves)
_NODE_MAP = {**{k: k for k in _VALID_NODE},
             "assertion": "claim", "contribution": "claim", "hypothesis": "claim",
             "conclusion": "claim", "subclaim": "claim", "objective": "claim",
             "result": "evidence", "finding": "evidence", "data": "evidence",
             "observation": "evidence", "measurement": "evidence", "datum": "evidence",
             "figure": "artifact", "table": "artifact", "chart": "artifact",
             "plot": "artifact", "panel": "artifact", "visualization": "artifact",
             "assumption": "warrant", "principle": "warrant", "background": "warrant",
             "rationale": "warrant", "premise": "warrant",
             "procedure": "method", "technique": "method", "approach": "method", "protocol": "method",
             "reference": "source", "citation": "source", "paper": "source", "prior_work": "source"}
_EDGE_MAP = {**{r: r for r in _VALID_EDGE},
             "enables": "supports", "produces": "supports", "leads_to": "supports",
             "causes": "supports", "results_in": "supports", "yields": "supports",
             "implies": "supports", "informs": "supports", "motivates": "supports",
             "demonstrates": "supports", "explains": "supports", "support": "supports",
             "shows": "visualizes", "displays": "visualizes", "illustrates": "visualizes",
             "depicts": "visualizes", "presents": "visualizes", "visualize": "visualizes",
             "from": "derived_from", "based_on": "derived_from", "computed_from": "derived_from",
             "uses": "derived_from", "derives": "derived_from", "measured_from": "derived_from",
             "limits": "qualifies", "caveats": "qualifies", "restricts": "qualifies",
             "weakens": "qualifies", "constrains": "qualifies",
             "refutes": "contradicts", "conflicts": "contradicts", "disagrees": "contradicts"}


def _sanitize(raw: dict) -> dict:
    nodes = [n for n in (raw.get("nodes") or []) if isinstance(n, dict) and n.get("id")]
    for n in nodes:
        n["kind"] = _NODE_MAP.get(str(n.get("kind", "")).strip().lower(), "claim")
        n.setdefault("text", "")
    raw["nodes"] = nodes
    ids = {n.get("id") for n in nodes}
    edges = []
    for e in raw.get("edges") or []:
        if not isinstance(e, dict):
            continue
        e["rel"] = _EDGE_MAP.get(str(e.get("rel", "")).strip().lower(), "supports")
        if e.get("src") in ids and e.get("dst") in ids:  # drop edges to missing nodes
            edges.append(e)
    raw["edges"] = edges
    return raw


def build(ps: ProjectState) -> ClaimGraph:
    raw = client.call_json("reasoning", prompt("claim_graph"), inputs_block(ps),
                           step="claim_graph", max_tokens=4096)
    return ClaimGraph.model_validate(_sanitize(raw))
