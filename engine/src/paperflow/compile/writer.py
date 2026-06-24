"""Draft each paragraph against its contract (writer tier). Drafting only — logic
validation runs once per section afterwards (see compile/validator.py), per the
"write everything, then validate section by section" workflow."""
from __future__ import annotations

import json
import re

from ..ingest.load_data import values_for_section
from ..llm import client
from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt


def _guard_citations(text: str, allowed: set[str]) -> str:
    """Deterministic anti-hallucination guard: any [cite:KEY] whose KEY is not in the
    reference store (and isn't already a 'what_I_need' marker) is rewritten so the
    invented key can never survive as if it were a real, verified citation."""
    def repl(m: re.Match) -> str:
        body = m.group(1).strip()
        if body.lower().startswith("what_i_need"):
            return m.group(0)
        keys = [k.strip() for k in re.split(r"[;,]", body) if k.strip()]
        good = [k for k in keys if k in allowed]
        bad = [k for k in keys if k not in allowed]
        if not bad:
            return m.group(0)
        out = []
        if good:
            out.append("[cite:" + ", ".join(good) + "]")
        out.append("[cite:what_I_need — " + ", ".join(bad) + "]")
        return " ".join(out)
    return re.sub(r"\[cite:([^\]]+)\]", repl, text)


def _node_refs(graph: ClaimGraph, ids: list[str]) -> list[dict]:
    """Resolve contract node ids to typed nodes. A paragraph may reference claims,
    evidence, or artifacts — surface kind + how an artifact is displayed."""
    refs: list[dict] = []
    for i in ids:
        n = graph.node(i)
        if n is None:
            refs.append({"id": i, "kind": "?", "text": ""})
        else:
            d = {"id": n.id, "kind": n.kind, "text": n.text}
            if n.represented_as:
                d["represented_as"] = n.represented_as
            refs.append(d)
    return refs


def _paragraph_briefs(graph: ClaimGraph, contract: SectionContract) -> str:
    """Ordered paragraph contracts with their claim/evidence/artifact nodes resolved."""
    briefs = [{**c.model_dump(), "nodes": _node_refs(graph, c.claim_ids)}
              for c in contract.paragraphs]
    return json.dumps(briefs, ensure_ascii=False, indent=2)


def write_section(ps: ProjectState, graph: ClaimGraph, contract: SectionContract) -> str:
    """Draft the whole section in ONE writer call (1 call per section, not per paragraph).
    Faster (≈6 calls/run vs ~29) and more coherent — the model sees the whole section at once."""
    allowed = set(ps.all_citation_keys)  # existing store + literature-search finds
    data_values = values_for_section(ps.project_dir, contract.section,
                                     [d.path for d in ps.data_assets])
    dv = (f"\n\n## DATA VALUES (real numbers from the author's files — use these verbatim "
          f"where relevant; do NOT invent numbers)\n{data_values}") if data_values else ""
    # hard journal limit: enforce the abstract word count from the (pre-fetched) guideline
    limit = ps.journal_constraints.get("abstract_word_limit") if contract.section == "abstract" else None
    limit_note = (f"\n\n## HARD LIMIT (obey strictly)\nThis is the ABSTRACT: it MUST be at most "
                  f"{limit} words — one concise paragraph, NO headings. Count words and stay under "
                  f"{limit}.") if limit else ""
    user = (
        f"{inputs_block(ps)}{dv}{limit_note}\n\n"
        f"## SECTION CONTRACT — write the COMPLETE '{contract.section}' section\n"
        f"Write exactly one paragraph per contract below, in this order.\n\n"
        f"{_paragraph_briefs(graph, contract)}"
    )
    n = max(1, len(contract.paragraphs))
    max_tokens = min(8000, 1100 * n + 800)  # scale to paragraph count
    if limit:
        max_tokens = min(max_tokens, int(limit * 3))  # words -> token budget cap
    draft = client.call(
        "writer", prompt("writer_section"), user, step="writer",
        max_tokens=max_tokens, temperature=0.4,
    ).text.strip()
    return _guard_citations(draft, allowed).strip() + "\n"  # never let invented keys survive
