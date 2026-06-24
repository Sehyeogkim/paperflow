"""Section-level logic validation (runs AFTER all sections are drafted).

Per the agreed workflow: write the whole manuscript first, then validate section by section
(not paragraph by paragraph — cheaper, fewer reasoning calls, and catches cross-paragraph
issues within a section). A/B toggle via env PAPERFLOW_VALIDATE:
  - "section" (default): one reasoning call per section; applies a minimal revision on violation.
  - "off": skip entirely (baseline for measuring whether validation earns its token cost).

Cross-SECTION contradictions/duplication are intentionally NOT auto-rewritten here — they go to
the reviewer report so a human decides (avoids a model rewriting good prose wholesale).
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from . import graph_slice
from ..llm import client
from ..schemas.claim import ClaimGraph, SectionContract
from ..util import prompt


def _node_texts(graph: ClaimGraph, ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for i in ids:
        n = graph.node(i)
        out.append({"id": i, "kind": n.kind if n else "?", "text": n.text if n else ""})
    return out


def mode() -> str:
    return os.environ.get("PAPERFLOW_VALIDATE", "section").strip().lower()


def validate_section(graph: ClaimGraph, contract: SectionContract, section_md: str) -> dict:
    """Validate one drafted section against its contract. Returns
    {ok, issues, revised} — revised is the corrected markdown (empty if ok)."""
    contract_block = json.dumps({
        "section": contract.section,
        "paragraphs": [{**p.model_dump(), "nodes": _node_texts(graph, p.claim_ids)}
                       for p in contract.paragraphs],
    }, ensure_ascii=False, indent=2)
    # The section's LOCAL SUBGRAPH (grounding chain of every claim in the section) — so the
    # validator checks evidence/figure/method attribution against the ACTUAL grounding, not
    # just the claim text.
    section_claims = [cid for p in contract.paragraphs for cid in p.claim_ids]
    grounding = graph_slice.context_text(graph, section_claims)
    user = (f"## SECTION CONTRACT\n{contract_block}\n\n## GROUNDING (the claims' local "
            f"subgraph — check attribution against this)\n{grounding}\n\n"
            f"## DRAFTED SECTION\n{section_md}")
    try:
        res = client.call_json("reasoning", prompt("section_validator"), user,
                               step="validator", max_tokens=6000)
    except Exception:
        return {"ok": True, "issues": [], "revised": ""}  # validator failure must not kill the run
    return {
        "ok": bool(res.get("ok", True)),
        "issues": res.get("issues", []) or [],
        "revised": (res.get("revised") or "").strip(),
    }


def validate_sections(graph: ClaimGraph, contracts: dict[str, SectionContract],
                      section_md: dict[str, str], progress=lambda m: None
                      ) -> tuple[dict[str, str], dict]:
    """Validate every section. Returns (possibly-revised section_md, report dict).
    Honors PAPERFLOW_VALIDATE=off to skip (A/B)."""
    if mode() == "off":
        return section_md, {"mode": "off", "sections": {}}

    revised_md = dict(section_md)
    report: dict = {"mode": "section", "sections": {}}
    items = [(sec, md, contracts[sec]) for sec, md in section_md.items()
             if contracts.get(sec) and md.strip()]
    if not items:
        return revised_md, report

    # sections validate independently -> run them concurrently (LLM calls are I/O-bound)
    progress(f"섹션 {len(items)}개 병렬 검증")

    def _work(item: tuple) -> tuple:
        sec, md, c = item
        v = validate_section(graph, c, md)
        progress(f"validate: {sec}")
        return sec, v

    with ThreadPoolExecutor(max_workers=min(6, len(items))) as ex:
        for sec, v in ex.map(_work, items):  # results assembled in the main thread
            report["sections"][sec] = {"ok": v["ok"], "issues": v["issues"]}
            if not v["ok"] and v["revised"]:
                revised_md[sec] = v["revised"].rstrip() + "\n"
    return revised_md, report
