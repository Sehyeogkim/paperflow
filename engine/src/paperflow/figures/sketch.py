"""Deterministic SVG sketches for PLANNED figures, shown in the Stage-3 confirm step.

No image generation (that is the separate, paid `paperflow figures` stage). These are cheap
schematic placeholders — a bar-chart or table mock — so the user can SEE what each figure
will convey and approve/redirect it visually before any prose is written.
"""
from __future__ import annotations

_ACCENT = "#CC785C"
_ACC2 = "#E8D5C4"
_INK = "#1A1A1A"
_MUTED = "#6B5E54"
_BORDER = "#D4C5B0"


def _bar_svg() -> str:
    heights = [70, 46, 30, 22, 14]  # a descending sensitivity-style bar chart
    bars = []
    x = 26
    for h in heights:
        y = 96 - h
        bars.append(f'<rect x="{x}" y="{y}" width="20" height="{h}" rx="2" fill="{_ACCENT}"/>')
        x += 30
    return (
        f'<svg viewBox="0 0 280 120" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="figure sketch">'
        f'<rect width="280" height="120" rx="8" fill="#FAF8F2" stroke="{_BORDER}"/>'
        f'<line x1="20" y1="96" x2="190" y2="96" stroke="{_MUTED}" stroke-width="1"/>'
        f'<line x1="20" y1="20" x2="20" y2="96" stroke="{_MUTED}" stroke-width="1"/>'
        + "".join(bars) +
        f'<text x="205" y="40" font-size="9" fill="{_MUTED}">S1 / ST</text>'
        f'<text x="205" y="54" font-size="9" fill="{_MUTED}">bar chart</text>'
        f'</svg>'
    )


def _table_svg() -> str:
    rows, cols = 4, 4
    cell_w, cell_h, x0, y0 = 58, 20, 16, 18
    cells = []
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * cell_w, y0 + r * cell_h
            fill = _ACC2 if r == 0 else ("#FFFFFF" if r % 2 else "#FBF6F0")
            cells.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" '
                         f'fill="{fill}" stroke="{_BORDER}" stroke-width="0.8"/>')
            if r == 0:
                cells.append(f'<text x="{x + cell_w/2}" y="{y + 13}" font-size="8" '
                             f'text-anchor="middle" fill="{_INK}" font-weight="700">col{c+1}</text>')
    return (
        f'<svg viewBox="0 0 280 120" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="table sketch">'
        f'<rect width="280" height="120" rx="8" fill="#FAF8F2" stroke="{_BORDER}"/>'
        + "".join(cells) +
        f'<text x="140" y="112" font-size="9" text-anchor="middle" fill="{_MUTED}">table</text>'
        f'</svg>'
    )


def sketch_for(kind: str) -> str:
    return _table_svg() if (kind or "").lower() == "table" else _bar_svg()


def attach_sketches(fig_spec: dict) -> dict:
    """Add an `svg` schematic to each planned figure in the figure_spec."""
    for f in fig_spec.get("figures", []):
        if isinstance(f, dict):
            f["svg"] = sketch_for(f.get("kind", "figure"))
    return fig_spec
