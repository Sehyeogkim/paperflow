"""Deterministically turn tabular project data into manuscript-ready LaTeX tables.

The LLM may describe a table, but it must never be responsible for copying the actual
numbers into it.  This module groups homomorphic CSV files by schema and materializes
their rows directly.  Known Sobol schemas receive stable, publication-friendly layouts;
unknown schemas still get a lossless (up to the documented safety cap) combined table.
"""
from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_MAX_GENERIC_ROWS = 200
_HASH_PREFIX = re.compile(r"^[0-9a-f]{8,64}_", re.IGNORECASE)
_SOBOL_NAME = re.compile(
    r"(?:^|_)sobol_(?P<level>grp|group|ind|individual)_(?P<model>[a-z0-9]+)_"
    r"(?P<outcome>[a-z0-9]+)(?:_|$)", re.IGNORECASE)


@dataclass(frozen=True)
class DataArtifact:
    """One physical table assembled from one or more source CSV files."""

    key: str
    kind: str
    caption: str
    label: str
    source_paths: tuple[str, ...]
    schema: tuple[str, ...]
    total_rows: int
    displayed_rows: int
    latex: str

    def manifest_entry(self) -> dict:
        entry = asdict(self)
        entry.pop("latex", None)
        return entry


@dataclass(frozen=True)
class _CsvData:
    path: Path
    relative_path: str
    fields: tuple[str, ...]
    rows: tuple[dict[str, str], ...]

    @property
    def source_name(self) -> str:
        return _HASH_PREFIX.sub("", self.path.stem)


def _read_csv(project: Path, path: Path) -> _CsvData | None:
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fields = tuple((name or "").strip() for name in (reader.fieldnames or []))
            if not fields or any(not name for name in fields):
                return None
            rows = tuple({field: (row.get(field) or "").strip() for field in fields}
                         for row in reader)
    except (OSError, UnicodeError, csv.Error):
        return None
    if not rows:
        return None
    return _CsvData(path=path, relative_path=path.relative_to(project).as_posix(),
                    fields=fields, rows=rows)


def _schema(data: _CsvData) -> tuple[str, ...]:
    # Column order is not part of a CSV schema: producers commonly reorder equivalent
    # exports.  Sorting makes those files coalesce into the same physical table.
    return tuple(sorted(field.casefold() for field in data.fields))


def _field_map(data: _CsvData) -> dict[str, str]:
    return {field.casefold(): field for field in data.fields}


def _source_dimensions(data: _CsvData) -> tuple[str, str]:
    match = _SOBOL_NAME.search(data.source_name)
    if not match:
        return data.source_name, ""
    return match.group("model").upper(), match.group("outcome").upper()


def _source_sort(data: _CsvData) -> tuple:
    model, outcome = _source_dimensions(data)
    model_rank = {"LAP": 0, "CP": 1}.get(model, 99)
    outcome_match = re.search(r"(\d+)", outcome)
    outcome_rank = int(outcome_match.group(1)) if outcome_match else 999
    return model_rank, model, outcome_rank, outcome, data.relative_path


def _escape(value: object, *, allow_math: bool = False) -> str:
    text = str(value)
    if allow_math and len(text) >= 2 and text.startswith("$") and text.endswith("$"):
        return text
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _number(value: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _escape(value)
    if abs(number) < 0.00005:
        number = 0.0
    return f"{number:.4f}"


def _longtable(*, columns: str, headers: list[str], rows: list[list[str]],
               caption: str, label: str) -> str:
    header = " & ".join(headers) + r" \\"
    body = "\n".join(" & ".join(row) + r" \\" for row in rows)
    return "\n".join([
        rf"\begin{{longtable}}{{{columns}}}",
        rf"\caption{{{_escape(caption)}}}\label{{{label}}}\\",
        r"\toprule", header, r"\midrule", r"\endfirsthead",
        rf"\caption[]{{{_escape(caption)} (continued)}}\\",
        r"\toprule", header, r"\midrule", r"\endhead",
        r"\midrule", rf"\multicolumn{{{len(headers)}}}{{r}}{{Continued on next page}}\\",
        r"\endfoot", r"\bottomrule", r"\endlastfoot",
        body, r"\end{longtable}",
    ])


def _sobol_artifact(key: str, datasets: list[_CsvData]) -> DataArtifact:
    is_group = key == "sobol_group"
    entity_field = "group" if is_group else "parameter"
    caption = ("Group-level Sobol sensitivity indices across lesion models and outcomes."
               if is_group else
               "Individual-parameter Sobol sensitivity indices across lesion models and outcomes.")
    label = "tab:sobol-group" if is_group else "tab:sobol-individual"
    rows: list[list[str]] = []
    for data in sorted(datasets, key=_source_sort):
        fields = _field_map(data)
        model, outcome = _source_dimensions(data)
        for row in data.rows:
            entity_key = fields.get("display_name", fields[entity_field])
            s1, st = row[fields["s1"]], row[fields["st"]]
            try:
                interaction = str(float(st) - float(s1))
            except ValueError:
                interaction = ""
            rows.append([
                _escape(model), _escape(outcome), _escape(row[entity_key], allow_math=True),
                _number(s1), _number(st), _number(interaction),
            ])
    headers = ["Model", "Outcome", "Group" if is_group else "Parameter",
               r"$S_1$", r"$S_T$", r"$S_T-S_1$"]
    latex = _longtable(columns="lllrrr", headers=headers, rows=rows,
                       caption=caption, label=label)
    paths = tuple(data.relative_path for data in sorted(datasets, key=_source_sort))
    schema = _schema(datasets[0])
    return DataArtifact(key=key, kind="table", caption=caption, label=label,
                        source_paths=paths, schema=schema, total_rows=len(rows),
                        displayed_rows=len(rows), latex=latex)


def _generic_artifact(index: int, datasets: list[_CsvData]) -> DataArtifact:
    first = datasets[0]
    source_count = len(datasets)
    caption = (f"Combined data for CSV schema {index} from {source_count} source "
               f"file{'s' if source_count != 1 else ''}.")
    label = f"tab:data-schema-{index}"
    rows: list[list[str]] = []
    total_rows = sum(len(data.rows) for data in datasets)
    for data in sorted(datasets, key=lambda item: item.relative_path):
        data_fields = _field_map(data)
        for row in data.rows:
            if len(rows) >= _MAX_GENERIC_ROWS:
                break
            rows.append([_escape(data.source_name)] +
                        [_escape(row[data_fields[field.casefold()]], allow_math=True)
                         for field in first.fields])
    headers = ["Source"] + [_escape(field) for field in first.fields]
    columns = "l" * len(headers)
    latex = _longtable(columns=columns, headers=headers, rows=rows,
                       caption=caption, label=label)
    return DataArtifact(
        key=f"csv_schema_{index}", kind="table", caption=caption, label=label,
        source_paths=tuple(data.relative_path for data in datasets), schema=_schema(first),
        total_rows=total_rows, displayed_rows=len(rows), latex=latex,
    )


def materialize(project_dir: str | Path) -> list[DataArtifact]:
    """Build stable tables for every non-empty CSV schema under ``data/``.

    The known group-Sobol and individual-Sobol tables are deliberately ordered first so
    prose that calls them Table 1 and Table 2 resolves to real numbered artifacts.
    """
    project = Path(project_dir).resolve()
    data_dir = project / "data"
    if not data_dir.is_dir():
        return []
    datasets = [data for path in sorted(data_dir.rglob("*.csv"))
                if (data := _read_csv(project, path)) is not None]
    grouped: dict[tuple[str, ...], list[_CsvData]] = {}
    for data in datasets:
        grouped.setdefault(_schema(data), []).append(data)

    known: dict[str, list[_CsvData]] = {"sobol_group": [], "sobol_individual": []}
    generic: list[list[_CsvData]] = []
    for schema, items in grouped.items():
        names = set(schema)
        if names == {"group", "s1", "st"}:
            known["sobol_group"].extend(items)
        elif {"parameter", "s1", "st"}.issubset(names):
            known["sobol_individual"].extend(items)
        else:
            generic.append(items)

    artifacts = [_sobol_artifact(key, known[key])
                 for key in ("sobol_group", "sobol_individual") if known[key]]
    for index, items in enumerate(sorted(generic, key=lambda group: _schema(group[0])), start=1):
        artifacts.append(_generic_artifact(index, items))
    return artifacts


def render(artifacts: list[DataArtifact]) -> str:
    """Render already-materialized artifacts as an includable LaTeX fragment."""
    return "\n\n".join(artifact.latex for artifact in artifacts).strip()


# Explicit public names for orchestration code; ``materialize`` remains the concise API.
build_data_artifacts = materialize
build_tables = materialize
