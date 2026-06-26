"""Stage 9: synthesize the project-specific overall_schema.json.

The LLM judges applicability / requirement_level / applicable_papers / reason per key
(the hard judgement). Code computes observed_in, evidence_sources, content_support, and
prevalence deterministically from the clusters so counts cannot be hallucinated.
"""
from __future__ import annotations

import json

from ..llm import client
from ..schemas.literature import LiteraturePaper
from ..schemas.overall_schema import (
    Applicability, ContentSupport, OverallSchema, RequirementKey,
)
from ..schemas.project_state import ProjectState
from ..util import inputs_block, prompt


def _papers_in(source_items: list[str]) -> list[str]:
    return sorted({s.split(":", 1)[0] for s in source_items if ":" in s})


def _judge(clusters: list[dict], ps: ProjectState, archetype: str) -> dict:
    payload = {
        "study_archetype": archetype,
        "clusters": [
            {"key": c["canonical_key"], "category": c["category"], "aliases": c["aliases"],
             "applicable_to": c["applicable_to"],
             "source_papers": _papers_in(c["source_items"])}
            for c in clusters
        ],
    }
    user = f"{inputs_block(ps)}\n\n## CANDIDATE REQUIREMENTS\n{json.dumps(payload, ensure_ascii=False)}"
    raw = client.call_json("reasoning", prompt("synthesize_overall_schema"), user,
                           step="lit.synthesize", max_tokens=4500)
    return {str(r.get("key")): r for r in (raw.get("requirements") or []) if r.get("key")}


def synthesize(clusters: list[dict], ps: ProjectState, papers: list[LiteraturePaper],
               project_id: str, archetype: str) -> OverallSchema:
    """Build the OverallSchema from clusters + an LLM judgement pass. Raises on LLM failure
    (caller decides fallback); deterministic count logic never raises."""
    judged = _judge(clusters, ps, archetype) if clusters else {}
    level_by_paper = {p.paper_id: p.content_level for p in papers}

    reqs: list[RequirementKey] = []
    for c in clusters:
        key = c["canonical_key"]
        src_papers = _papers_in(c["source_items"])
        observed_in = len(src_papers)
        support = ContentSupport()
        for pid in src_papers:
            lvl = level_by_paper.get(pid, "abstract_only")
            setattr(support, lvl, getattr(support, lvl) + 1)

        j = judged.get(key, {})
        applicable_papers = int(j.get("applicable_papers", observed_in) or observed_in)
        applicable_papers = max(observed_in, min(applicable_papers, len(papers)))  # clamp sane
        prevalence = round(observed_in / max(applicable_papers, 1), 3)
        app = j.get("applicability") or {}
        level = str(j.get("requirement_level", "common"))
        if level not in ("mandatory", "strongly_expected", "common", "optional", "unsupported"):
            level = "common"
        reqs.append(RequirementKey(
            key=key, category=c["category"], aliases=c["aliases"],
            observed_in=observed_in, applicable_papers=applicable_papers, prevalence=prevalence,
            applicability=Applicability(
                required_when=[str(x) for x in (app.get("required_when") or [])],
                not_applicable_when=[str(x) for x in (app.get("not_applicable_when") or [])]),
            requirement_level=level, reason=str(j.get("reason", "")),
            evidence_sources=src_papers, content_support=support,
        ))

    # sort by (level rank, prevalence) so the most expected requirements lead
    rank = {"mandatory": 0, "strongly_expected": 1, "common": 2, "optional": 3, "unsupported": 4}
    reqs.sort(key=lambda r: (rank.get(r.requirement_level, 9), -r.prevalence))

    return OverallSchema(
        project_id=project_id, study_archetype=archetype, source_papers=len(papers),
        requirement_source="literature_derived", requirements=reqs,
    )
