"""Deterministic data-file profiling (no LLM).

CSV/XLSX get column + dtype + numeric-range profiling so the reconstruction can describe
each file as research evidence. Text/binary files get a light profile (size, line count).
Everything is bounded (rows/cells capped) so a huge file never blocks the pipeline.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

_MAX_ROWS = 500          # cap rows scanned for dtype/range inference
_SAMPLE_VALUES = 200     # per-column values considered for dtype guess


def _is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _infer_dtype(values: list[str]) -> str:
    vals = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not vals:
        return "empty"
    if all(_is_int(v) for v in vals):
        return "int"
    if all(_is_float(v) for v in vals):
        return "float"
    return "text"


def profile_csv(path: Path) -> dict:
    """Columns, dtypes, row count, numeric ranges, and a sample row — all bounded."""
    try:
        text = path.read_text(errors="replace")
    except Exception as e:  # unreadable file must not crash the pipeline
        return {"kind": "csv", "error": str(e)[:120]}
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return {"kind": "csv", "rows": 0, "columns": {}}
    header = [h.strip() for h in header]
    col_values: dict[str, list[str]] = {h: [] for h in header}
    rows = 0
    sample_row: dict[str, str] = {}
    for row in reader:
        rows += 1
        if rows == 1:
            sample_row = {header[i]: row[i] for i in range(min(len(header), len(row)))}
        if rows <= _MAX_ROWS:
            for i, h in enumerate(header):
                if i < len(row) and len(col_values[h]) < _SAMPLE_VALUES:
                    col_values[h].append(row[i])
    columns = {h: _infer_dtype(col_values[h]) for h in header}
    numeric_ranges: dict[str, list[float]] = {}
    for h, dtype in columns.items():
        if dtype in ("int", "float"):
            nums = [float(v) for v in col_values[h] if _is_float(v)]
            if nums:
                numeric_ranges[h] = [min(nums), max(nums)]
    return {
        "kind": "csv",
        "rows": rows,
        "columns": columns,
        "numeric_ranges": numeric_ranges,
        "sample_row": sample_row,
        "truncated": rows > _MAX_ROWS,
    }


def profile_xlsx(path: Path) -> dict:
    """Per-sheet columns + row count via openpyxl (read-only). Degrades if openpyxl absent."""
    try:
        import openpyxl  # optional dependency
    except Exception:
        return {"kind": "xlsx", "error": "openpyxl not installed"}
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        return {"kind": "xlsx", "error": str(e)[:120]}
    sheets: dict[str, dict] = {}
    for ws in wb.worksheets:
        rows_iter = ws.iter_rows(values_only=True)
        try:
            header = next(rows_iter)
        except StopIteration:
            sheets[ws.title] = {"rows": 0, "columns": {}}
            continue
        header = [str(h).strip() if h is not None else "" for h in header]
        col_values: dict[int, list[str]] = {i: [] for i in range(len(header))}
        rows = 0
        for row in rows_iter:
            rows += 1
            if rows <= _MAX_ROWS:
                for i in range(len(header)):
                    if i < len(row) and row[i] is not None and len(col_values[i]) < _SAMPLE_VALUES:
                        col_values[i].append(str(row[i]))
        columns = {header[i] or f"col{i}": _infer_dtype(col_values[i]) for i in range(len(header))}
        sheets[ws.title] = {"rows": rows, "columns": columns}
    wb.close()
    return {"kind": "xlsx", "sheets": sheets}


def profile_text(path: Path) -> dict:
    try:
        text = path.read_text(errors="replace")
    except Exception as e:
        return {"kind": "text", "error": str(e)[:120]}
    lines = text.splitlines()
    return {"kind": "text", "lines": len(lines), "chars": len(text),
            "head": "\n".join(lines[:15])[:1000]}


def profile_file(path: Path) -> dict:
    """Dispatch on suffix. Always returns a dict (never raises)."""
    if not path.is_file():
        return {"error": "not_found"}
    suf = path.suffix.lower().lstrip(".")
    if suf == "csv":
        return profile_csv(path)
    if suf in ("xlsx", "xls"):
        return profile_xlsx(path)
    if suf in ("md", "txt", "dat", "json", "bib", "tex"):
        return profile_text(path)
    # binary / opaque (pdf, png, ...) — record size only
    try:
        size = path.stat().st_size
    except Exception:
        size = 0
    return {"kind": suf or "file", "bytes": size}
