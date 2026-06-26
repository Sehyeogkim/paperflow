"""Write all run artifacts to <output_dir>/."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import latex, manuscript_state, write_docx
from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.eval import RunManifest
from ..schemas.requirement import RequirementReport


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def _compile_pdf(out_dir: Path, tex_name: str = "paper.tex") -> bool:
    """Best-effort LaTeX -> PDF (XeLaTeX for kotex). Never raises — a failed compile
    just means no PDF; the .tex artifact is always present."""
    engine = shutil.which("xelatex") or shutil.which("lualatex")
    if not engine:
        return False
    try:
        for _ in range(2):  # second pass resolves \cite / refs
            subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error", tex_name],
                           cwd=str(out_dir), capture_output=True, text=True, timeout=180)
    except Exception:
        return False
    return (out_dir / tex_name.replace(".tex", ".pdf")).is_file()


def write_all(out_dir: Path, *, sections: dict[str, str], graph: ClaimGraph,
              contracts: dict[str, SectionContract], requirement: RequirementReport,
              figure_spec: dict, manifest: RunManifest,
              literature_md: str = "", found_references=None,
              reference_table=None, validation_report=None, paper_meta=None,
              warnings=None, research_state=None, evidence_inventory=None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, md in sections.items():
        (out_dir / f"{name.capitalize()}.md").write_text(md)
    # assembled LaTeX manuscript (the "finished paper" artifact) + compiled PDF
    found = [r.model_dump() for r in (found_references or [])]
    (out_dir / "paper.tex").write_text(latex.assemble(
        sections, reference_table=reference_table, found_references=found,
        meta=paper_meta or {}))
    _compile_pdf(out_dir)

    # canonical manuscript state -> manuscript.json + DOCX + HTML preview + grounding report
    meta = dict(paper_meta or {})
    if requirement and requirement.classification:
        meta["classification"] = requirement.classification.value
    ms = manuscript_state.build(
        sections, graph=graph, figure_spec=figure_spec, meta=meta,
        reference_table=reference_table, found_references=found, warnings=warnings)
    (out_dir / "manuscript.json").write_text(ms.model_dump_json(indent=2))
    (out_dir / "manuscript_preview.html").write_text(manuscript_state.to_html(ms))
    _dump(out_dir / "grounding_report.json", ms.grounding.model_dump())
    write_docx.write_docx(ms, out_dir / "paper.docx")
    if research_state is not None:
        (out_dir / "research_state.json").write_text(research_state.model_dump_json(indent=2))
    if evidence_inventory is not None:
        (out_dir / "evidence_inventory.json").write_text(
            evidence_inventory.model_dump_json(indent=2))
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
