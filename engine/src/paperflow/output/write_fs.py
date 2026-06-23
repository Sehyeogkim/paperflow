"""Write all run artifacts to <output_dir>/."""
from __future__ import annotations

import json
from pathlib import Path

from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.eval import RunManifest
from ..schemas.requirement import RequirementReport


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def write_all(out_dir: Path, *, sections: dict[str, str], graph: ClaimGraph,
              contracts: dict[str, SectionContract], requirement: RequirementReport,
              figure_spec: dict, manifest: RunManifest,
              literature_md: str = "", found_references=None,
              reference_table=None, validation_report=None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, md in sections.items():
        (out_dir / f"{name.capitalize()}.md").write_text(md)
    if literature_md:
        (out_dir / "Literature.md").write_text(literature_md)
    if found_references:
        _dump(out_dir / "reference_candidates.json",
              [r.model_dump() for r in found_references])
    if reference_table:
        _dump(out_dir / "reference_table.json", reference_table)
    if validation_report is not None:
        _dump(out_dir / "validation_report.json", validation_report)
    _dump(out_dir / "claim_graph.json", graph.model_dump())
    _dump(out_dir / "contracts.json", {k: v.model_dump() for k, v in contracts.items()})
    _dump(out_dir / "requirement_report.json", requirement.model_dump())
    _dump(out_dir / "figure_spec.json", figure_spec)
    _dump(out_dir / "run_manifest.json", {
        **manifest.model_dump(),
        "totals": {
            "input_tokens": manifest.total_input,
            "output_tokens": manifest.total_output,
            "cached_tokens": manifest.total_cached,
            "cache_hit_rate": round(manifest.cache_hit_rate, 4),
        },
        "by_step": manifest.by_step(),
    })
