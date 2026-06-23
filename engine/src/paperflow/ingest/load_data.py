"""Load actual values from small data files so the writer can ground Result prose in
real numbers (Sobol indices, parameter ranges) instead of [DATA_NEEDED] placeholders.

Only small tabular files are inlined (cap rows/chars) — big files stay referenced by path.
"""
from __future__ import annotations

from pathlib import Path

_MAX_ROWS = 30
_MAX_CHARS = 3500


def load_values(project_dir: str, paths: list[str]) -> str:
    """Render the given data files (paths relative to project) as compact text blocks."""
    project = Path(project_dir)
    blocks: list[str] = []
    for rel in paths:
        p = project / rel
        if not p.is_file():
            continue
        if p.suffix.lower() == ".csv":
            rows = p.read_text().splitlines()[: _MAX_ROWS + 1]
            blocks.append(f"### {rel}\n" + "\n".join(rows))
        elif p.suffix.lower() in (".md", ".dat", ".txt"):
            blocks.append(f"### {rel}\n" + p.read_text()[:_MAX_CHARS])
    return "\n\n".join(blocks)


def values_for_section(project_dir: str, section: str, data_paths: list[str]) -> str:
    """Pick the data files most relevant to a section and inline their values."""
    if section == "result":
        want = [p for p in data_paths if "/sobol/" in p or p.endswith(".csv")]
    elif section == "method":
        want = [p for p in data_paths if "input_parameter" in p or p.endswith(("bc.md", ".dat"))]
    else:
        want = []
    return load_values(project_dir, want[:10])
