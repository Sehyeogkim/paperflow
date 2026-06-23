"""Draft each paragraph against its contract (writer tier). Drafting only — logic
validation runs once per section afterwards (see compile/validator.py), per the
"write everything, then validate section by section" workflow."""
from __future__ import annotations

import json
import re

from ..ingest.load_data import values_for_section
from ..llm import client
from ..schemas.claim import ClaimGraph, ParagraphContract, SectionContract
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


def _draft_paragraph(ps: ProjectState, graph: ClaimGraph, c: ParagraphContract,
                     section_so_far: str, data_values: str) -> str:
    contract_block = json.dumps({
        **c.model_dump(),
        "nodes": _node_refs(graph, c.claim_ids),
    }, ensure_ascii=False, indent=2)
    prior = section_so_far.strip() or "(this is the first paragraph of the section)"
    dv = (f"\n\n## DATA VALUES (real numbers from the author's files — use these verbatim "
          f"where relevant; do NOT invent numbers)\n{data_values}") if data_values else ""
    user = (
        f"{inputs_block(ps)}{dv}\n\n"
        f"## SECTION SO FAR (continue coherently; do NOT repeat definitions/claims already stated)\n{prior}\n\n"
        f"## PARAGRAPH CONTRACT (write the NEXT paragraph only)\n{contract_block}"
    )
    return client.call(
        "writer", prompt("writer"), user, step="writer", max_tokens=1400, temperature=0.4
    ).text.strip()


def write_section(ps: ProjectState, graph: ClaimGraph, contract: SectionContract) -> str:
    """Draft the whole section paragraph-by-paragraph. No inline validation."""
    allowed = set(ps.all_citation_keys)  # existing store + literature-search finds
    data_values = values_for_section(ps.project_dir, contract.section,
                                     [d.path for d in ps.data_assets])
    out: list[str] = []
    seen_headings: set[str] = set()
    for c in contract.paragraphs:
        # deterministic heading insertion (don't rely on the model for structure)
        if c.heading and c.heading not in seen_headings:
            seen_headings.add(c.heading)
            out.append(f"### {c.heading}")
        section_so_far = "\n\n".join(out)
        draft = _draft_paragraph(ps, graph, c, section_so_far, data_values)
        out.append(_guard_citations(draft, allowed))  # never let invented keys survive
    return "\n\n".join(out).strip() + "\n"
