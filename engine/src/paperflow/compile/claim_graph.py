"""core message + outline -> ClaimGraph (reasoning tier), built in TWO passes:
  Pass A — claim skeleton (main claims + subclaims).
  Pass B — grounding (evidence / method / data / warrant / source / artifact + edges).

A typed VALIDATOR then runs (not a silent sanitizer): node kinds and edge relations are
coerced from known synonyms to the canonical vocabulary; UNKNOWN relations are dropped
(never coerced to 'supports'); edges whose src->dst kinds violate the allowed matrix are
dropped; dangling edges are dropped. One bad edge never crashes a run, and a wrong edge
never silently passes as valid.
"""
from __future__ import annotations

from ..llm import client
from ..schemas.claim import ClaimGraph
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt

_VALID_NODE = {"claim", "evidence", "method", "data", "warrant", "source", "artifact"}
_VALID_EDGE = {"supports", "produces", "uses", "derived_from", "part_of",
               "visualizes", "justifies", "qualifies", "contradicts"}

_NODE_MAP = {**{k: k for k in _VALID_NODE},
             "assertion": "claim", "contribution": "claim", "hypothesis": "claim",
             "conclusion": "claim", "subclaim": "claim", "objective": "claim",
             "result": "evidence", "finding": "evidence", "observation": "evidence",
             "measurement": "evidence", "datum": "evidence",
             "dataset": "data", "file": "data", "csv": "data", "output": "data",
             "procedure": "method", "technique": "method", "approach": "method",
             "protocol": "method", "submethod": "method", "step": "method",
             "assumption": "warrant", "principle": "warrant", "background": "warrant",
             "rationale": "warrant", "premise": "warrant",
             "reference": "source", "citation": "source", "paper": "source", "prior_work": "source",
             "figure": "artifact", "table": "artifact", "chart": "artifact",
             "plot": "artifact", "equation": "artifact", "panel": "artifact"}
# known synonyms -> canonical relation. UNKNOWN relations are intentionally absent:
# they get dropped, not mapped to 'supports'.
_EDGE_MAP = {**{r: r for r in _VALID_EDGE},
             "support": "supports", "demonstrates": "supports", "confirms": "supports",
             "shows_that": "supports", "evidences": "supports",
             "generates": "produces", "yields": "produces", "outputs": "produces",
             "computes": "produces",
             "consumes": "uses", "takes": "uses", "requires": "uses", "requires_input": "uses",
             "computed_from": "derived_from", "based_on": "derived_from", "from": "derived_from",
             "calculated_from": "derived_from",
             "subprocess_of": "part_of", "component_of": "part_of", "belongs_to": "part_of",
             "step_of": "part_of",
             "shows": "visualizes", "displays": "visualizes", "illustrates": "visualizes",
             "depicts": "visualizes", "presents": "visualizes",
             "licenses": "justifies", "grounds": "justifies", "motivates": "justifies",
             "limits": "qualifies", "caveats": "qualifies", "restricts": "qualifies",
             "weakens": "qualifies",
             "refutes": "contradicts", "conflicts": "contradicts", "disagrees": "contradicts"}

# allowed (src_kind, dst_kind) per relation — directional
_ALLOWED_EDGE: dict[str, set[tuple[str, str]]] = {
    "supports": {("evidence", "claim"), ("claim", "claim")},
    "produces": {("method", "data"), ("method", "evidence")},
    "uses": {("method", "data")},
    "derived_from": {("evidence", "data"), ("evidence", "evidence"), ("data", "data"),
                     ("data", "method")},
    "part_of": {("method", "method"), ("claim", "claim")},
    "visualizes": {("artifact", "evidence"), ("artifact", "method"), ("artifact", "data")},
    "justifies": {("warrant", "claim"), ("source", "warrant"), ("warrant", "method"),
                  ("source", "claim")},
    "qualifies": {("warrant", "claim"), ("claim", "claim")},
    "contradicts": {("evidence", "claim"), ("claim", "claim")},
}


def _coerce_kind(k) -> str:
    return _NODE_MAP.get(str(k).strip().lower(), "claim")


def validate(raw: dict) -> dict:
    """Coerce node kinds, drop unknown/invalid/dangling edges. Returns a clean dict."""
    nodes = [n for n in (raw.get("nodes") or []) if isinstance(n, dict) and n.get("id")]
    for n in nodes:
        n["kind"] = _coerce_kind(n.get("kind"))
        n.setdefault("text", "")
    raw["nodes"] = nodes
    kind_of = {n["id"]: n["kind"] for n in nodes}

    out_edges, idx = [], 1
    for e in raw.get("edges") or []:
        if not isinstance(e, dict) or e.get("src") not in kind_of or e.get("dst") not in kind_of:
            continue  # dangling -> drop
        rel = _EDGE_MAP.get(str(e.get("rel", "")).strip().lower())
        if rel is None:
            continue  # UNKNOWN relation -> drop (never coerce to supports)
        if (kind_of[e["src"]], kind_of[e["dst"]]) not in _ALLOWED_EDGE.get(rel, set()):
            continue  # wrong src->dst kinds -> drop
        e["rel"] = rel
        if not e.get("id"):
            e["id"] = f"L{idx}"
        idx += 1
        out_edges.append(e)
    raw["edges"] = out_edges
    return raw


def build(ps: ProjectState) -> ClaimGraph:
    ib = inputs_block(ps)
    # Pass A — claim skeleton
    a = client.call_json("reasoning", prompt("claim_graph_a"), ib, step="claim_graph.a", max_tokens=2500, effort="low")
    claims = [c for c in (a.get("claims") or []) if isinstance(c, dict) and c.get("id")]
    for c in claims:
        c["kind"] = "claim"
    claim_block = "\n".join(f"- {c['id']} [{c.get('section', '')}] {c.get('text', '')}" for c in claims)

    # Pass B — grounding for the given claims
    b = client.call_json("reasoning", prompt("claim_graph_b"),
                         f"{ib}\n\n## CLAIM SKELETON (do not restate these)\n{claim_block}",
                         step="claim_graph.b", max_tokens=4096, effort="low")

    merged = {
        "main_contribution": a.get("main_contribution", ""),
        "nodes": claims + [n for n in (b.get("nodes") or []) if isinstance(n, dict)],
        "edges": (a.get("claim_edges") or []) + (b.get("edges") or []),
    }
    return ClaimGraph.model_validate(validate(merged))


def build_preliminary(ps: ProjectState) -> ClaimGraph:
    """Preliminary Logic Graph — built AFTER Stage-1 answers (TWO_STAGE_QUESTIONS §6).
    ps must already carry Research State v2 + Evidence Inventory (rendered via inputs_block)."""
    return build(ps)


def build_final(preliminary: ClaimGraph, logic_questions=None,
                logic_answers: dict | None = None) -> ClaimGraph:
    """Final Logic Graph — deterministically applies Stage-2 logic answers to the preliminary
    graph (unknown → downgrade/qualify/remove; real → traceable author-answer evidence) and
    rejects untraceable numeric evidence. No extra LLM call, so artifacts stay reproducible."""
    from ..graph.finalize import finalize
    return finalize(preliminary, list(logic_questions or []), logic_answers or {})
