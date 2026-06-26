"""Stage 9: assemble overall_schema.json from clusters (DETERMINISTIC — no LLM call).

requirement_level / required_when / reason are now judged inside the normalize step (merged
normalize+synthesize, one fewer round-trip). Here we only compute counts — observed_in,
prevalence, evidence_sources, content_support — so nothing can be hallucinated.
"""
from __future__ import annotations

from ..schemas.literature import LiteraturePaper
from ..schemas.overall_schema import (
    Applicability, ContentSupport, OverallSchema, RequirementKey,
)
from ..schemas.project_state import ProjectState

_RANK = {"mandatory": 0, "strongly_expected": 1, "common": 2, "optional": 3, "unsupported": 4}
_VALID = ("mandatory", "strongly_expected", "common", "optional", "unsupported")


def _papers_in(source_items: list[str]) -> list[str]:
    return sorted({s.split(":", 1)[0] for s in source_items if ":" in s})


def synthesize(clusters: list[dict], ps: ProjectState, papers: list[LiteraturePaper],
               project_id: str, archetype: str) -> OverallSchema:
    """Build the OverallSchema from clusters (which already carry requirement_level/required_when/
    reason from the normalize step). Pure computation — never calls the LLM, never raises."""
    level_by_paper = {p.paper_id: p.content_level for p in papers}
    reqs: list[RequirementKey] = []
    for c in clusters:
        src_papers = _papers_in(c["source_items"])
        observed_in = len(src_papers)
        support = ContentSupport()
        for pid in src_papers:
            lvl = level_by_paper.get(pid, "abstract_only")
            setattr(support, lvl, getattr(support, lvl) + 1)
        # applicable_papers = all selected papers, so prevalence has real variance (observed/total)
        applicable_papers = len(papers)
        prevalence = round(observed_in / max(applicable_papers, 1), 3)
        level = str(c.get("requirement_level", "common"))
        reqs.append(RequirementKey(
            key=c["canonical_key"], category=c["category"], aliases=c.get("aliases", []),
            observed_in=observed_in, applicable_papers=applicable_papers, prevalence=prevalence,
            applicability=Applicability(
                required_when=[str(x) for x in (c.get("required_when") or [])]),
            requirement_level=level if level in _VALID else "common",
            reason=str(c.get("reason", "")),
            evidence_sources=src_papers, content_support=support,
        ))
    reqs.sort(key=lambda r: (_RANK.get(r.requirement_level, 9), -r.prevalence))
    return OverallSchema(
        project_id=project_id, study_archetype=archetype, source_papers=len(papers),
        requirement_source="literature_derived", requirements=reqs,
    )
