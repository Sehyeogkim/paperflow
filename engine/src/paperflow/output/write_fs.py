"""Write all run artifacts to <output_dir>/."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import data_artifacts
from . import latex
from ..compile import manuscript_quality
from ..schemas.claim import ClaimGraph, SectionContract
from ..schemas.eval import RunManifest
from ..schemas.requirement import RequirementReport


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def _compile_pdf(out_dir: Path, tex_name: str = "paper.tex") -> bool:
    """Best-effort LaTeX -> PDF (XeLaTeX for kotex). Never raises — a failed compile
    just means no PDF; the .tex artifact is always present."""
    pdf_path = out_dir / tex_name.replace(".tex", ".pdf")
    # Output directories are reused across revisions. Never let a PDF from a previous
    # manuscript masquerade as the current run when no TeX engine is available or the
    # new compilation fails.
    pdf_path.unlink(missing_ok=True)
    engine = shutil.which("xelatex") or shutil.which("lualatex")
    if not engine:
        return False
    try:
        for _ in range(2):  # second pass resolves \cite / refs
            subprocess.run([engine, "-interaction=nonstopmode", "-halt-on-error", tex_name],
                           cwd=str(out_dir), capture_output=True, text=True, timeout=180)
    except Exception:
        return False
    return pdf_path.is_file()


def write_all(out_dir: Path, *, sections: dict[str, str], graph: ClaimGraph,
              contracts: dict[str, SectionContract], requirement: RequirementReport,
              figure_spec: dict, manifest: RunManifest,
              literature_md: str = "", found_references=None,
              reference_table=None, validation_report=None, paper_meta=None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, md in sections.items():
        (out_dir / f"{name.capitalize()}.md").write_text(md)
    # assembled LaTeX manuscript (the "finished paper" artifact) + compiled PDF
    found = [r.model_dump() for r in (found_references or [])]
    tables = data_artifacts.materialize(manifest.project_dir)
    tables_tex = data_artifacts.render(tables)
    if tables_tex:
        (out_dir / "data_tables.tex").write_text(tables_tex + "\n")
        _dump(out_dir / "data_artifact_manifest.json",
              [artifact.manifest_entry() for artifact in tables])
    else:
        # The output directory can be reused across runs.  Do not advertise generated
        # tables from an earlier input set after the project's CSV files are removed.
        (out_dir / "data_tables.tex").unlink(missing_ok=True)
        (out_dir / "data_artifact_manifest.json").unlink(missing_ok=True)
    paper_tex = latex.assemble(
        sections, reference_table=reference_table, found_references=found,
        meta=paper_meta or {}, data_artifacts=tables_tex)
    (out_dir / "paper.tex").write_text(paper_tex)
    quality_report = manuscript_quality.inspect(sections, paper_tex)
    _dump(out_dir / "manuscript_quality.json", quality_report)
    _compile_pdf(out_dir)
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
    # Existing callers safely ignore this; orchestration/server callers can now use it to
    # withhold a "complete" state whenever deterministic blocking findings remain.
    return quality_report
