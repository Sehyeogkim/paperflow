import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from paperflow.ingest.artifact_manifest import (
    ExtractionLimits,
    build_artifact_manifest,
)


def _record(manifest, name):
    return next(item for item in manifest.artifacts if item.original_name == name)


def _write_minimal_text_pdf(path: Path, text: str) -> None:
    """Write a tiny single-page PDF with one extractable Helvetica text run."""

    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = "BT /F1 12 Tf 72 100 Td (%s) Tj ET" % escaped
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
         "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Length %d >>\nstream\n%s\nendstream" % (len(stream.encode("ascii")), stream),
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(("%d 0 obj\n%s\nendobj\n" % (number, obj)).encode("ascii"))
    xref = len(output)
    output.extend(("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(("%010d 00000 n \n" % offset).encode("ascii"))
    output.extend((
        "trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref)
    ).encode("ascii"))
    path.write_bytes(bytes(output))


def test_extracts_text_markdown_csv_and_json_with_relative_provenance(tmp_path):
    project = tmp_path / "project"
    data = project / "data"
    refs = project / "reference"
    main = project / "main"
    data.mkdir(parents=True)
    refs.mkdir()
    main.mkdir()
    (data / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (data / "설명.md").write_text("# 제목\n내용", encoding="utf-8")
    (data / "values.csv").write_text("name,value\na,1\nb,2\n", encoding="utf-8")
    (refs / "metadata.json").write_text(
        json.dumps({"title": "Study", "year": 2025}), encoding="utf-8")
    (main / "private.txt").write_text("must not be scanned", encoding="utf-8")

    manifest = build_artifact_manifest(project)

    assert {item.original_name for item in manifest.artifacts} == {
        "notes.txt", "설명.md", "values.csv", "metadata.json",
    }
    assert all(item.status == "extracted" for item in manifest.artifacts)
    notes = _record(manifest, "notes.txt")
    assert notes.sha256 == hashlib.sha256(b"alpha\nbeta\n").hexdigest()
    assert notes.chunks[0].locator.relative_path == "data/notes.txt"
    assert notes.chunks[0].locator.line_start == 1
    assert notes.chunks[0].locator.line_end == 2
    assert "/" not in notes.logical_id
    assert len(notes.logical_id) <= 59

    csv_record = _record(manifest, "values.csv")
    assert csv_record.mime_type == "text/csv"
    assert csv_record.metadata["header"] == ["name", "value"]
    assert csv_record.metadata["sample_rows"] == [["a", "1"], ["b", "2"]]
    assert csv_record.chunks[0].locator.row_start == 1
    assert csv_record.chunks[0].locator.row_end == 3

    json_record = _record(manifest, "metadata.json")
    assert json_record.metadata["top_level_keys"] == ["title", "year"]
    assert json_record.chunks[0].locator.json_pointer == "$"

    serialized = manifest.to_json()
    assert str(project.resolve()) not in serialized
    assert json.loads(serialized)["manifest_version"] == "1.0"


def test_blocks_absolute_and_traversal_paths(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    manifest = build_artifact_manifest(
        project,
        relative_paths=["../secret.txt", str(outside.resolve())],
    )

    assert [item.status for item in manifest.artifacts] == ["blocked", "blocked"]
    assert {item.error_code for item in manifest.artifacts} == {
        "path_escape", "absolute_path",
    }
    serialized = manifest.to_json()
    assert str(outside.resolve()) not in serialized
    assert all(item.sha256 is None for item in manifest.artifacts)


def test_explicit_paths_are_limited_to_scan_roots_and_symlinks_are_blocked(tmp_path):
    project = tmp_path / "project"
    data = project / "data"
    main = project / "main"
    data.mkdir(parents=True)
    main.mkdir()
    target = main / "private.txt"
    target.write_text("private", encoding="utf-8")
    symlink = data / "alias.txt"
    try:
        symlink.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    manifest = build_artifact_manifest(
        project,
        relative_paths=["main/private.txt", "data/alias.txt"],
    )

    assert [item.status for item in manifest.artifacts] == ["blocked", "blocked"]
    assert [item.error_code for item in manifest.artifacts] == [
        "outside_scan_roots", "symlink_not_allowed",
    ]
    assert all(item.sha256 is None for item in manifest.artifacts)


def test_reports_limits_unsupported_and_parse_errors_without_aborting(tmp_path):
    project = tmp_path / "project"
    data = project / "data"
    data.mkdir(parents=True)
    (data / "large.txt").write_text("123456", encoding="utf-8")
    (data / "raw.bin").write_bytes(b"binary")
    (data / "bad.json").write_text("{not json", encoding="utf-8")
    limits = replace(ExtractionLimits(), max_file_bytes=5)

    manifest = build_artifact_manifest(project, limits=limits)

    large = _record(manifest, "large.txt")
    assert large.status == "limit_exceeded"
    assert large.error_code == "file_byte_limit"
    assert large.sha256 == hashlib.sha256(b"123456").hexdigest()
    assert _record(manifest, "raw.bin").status == "unsupported"
    bad_json = _record(manifest, "bad.json")
    # It exceeds the deliberately tiny byte limit before parsing; explicit parsing error
    # is covered by a second, in-limit malformed file.
    assert bad_json.status == "limit_exceeded"

    (data / "x.json").write_text("{", encoding="utf-8")
    parsed = build_artifact_manifest(project, relative_paths=["data/x.json"])
    assert parsed.artifacts[0].status == "error"
    assert parsed.artifacts[0].error_code == "json_error"
    assert parsed.artifacts[0].chunks == []


def test_extracts_pdf_text_with_page_locator(tmp_path):
    pytest.importorskip("pypdf")
    project = tmp_path / "project"
    data = project / "data"
    data.mkdir(parents=True)
    _write_minimal_text_pdf(data / "paper.pdf", "Hello PDF")

    limits = replace(ExtractionLimits(), max_chunk_chars=4)
    manifest = build_artifact_manifest(project, limits=limits)
    record = _record(manifest, "paper.pdf")

    assert record.status == "extracted"
    assert record.metadata["pages_total"] == 1
    assert record.metadata["pages_extracted"] == 1
    assert "Hello PDF" in "".join(chunk.text for chunk in record.chunks)
    assert all(len(chunk.text) <= 4 for chunk in record.chunks)
    assert record.chunks[0].locator.page == 1


def test_extracts_xlsx_sheet_header_and_sample(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    project = tmp_path / "project"
    data = project / "data"
    data.mkdir(parents=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sobol"
    sheet.append(["parameter", "S1"])
    sheet.append(["elasticity", 0.75])
    sheet.append(["pressure", 0.2])
    workbook.save(data / "results.xlsx")
    workbook.close()

    manifest = build_artifact_manifest(project)
    record = _record(manifest, "results.xlsx")

    assert record.status == "extracted"
    summary = record.metadata["sheets"][0]
    assert summary["sheet"] == "Sobol"
    assert summary["header"] == ["parameter", "S1"]
    assert summary["sample_rows"][0] == ["elasticity", "0.75"]
    assert record.chunks[0].locator.sheet == "Sobol"
    assert record.chunks[0].locator.row_start == 1


def test_xlsx_zip_bomb_preflight_fails_gracefully(tmp_path):
    project = tmp_path / "project"
    data = project / "data"
    data.mkdir(parents=True)
    path = data / "oversized.xlsx"
    import zipfile
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"0" * 1_024)
    limits = replace(ExtractionLimits(), max_xlsx_uncompressed_bytes=100)

    manifest = build_artifact_manifest(project, limits=limits)
    record = _record(manifest, "oversized.xlsx")

    assert record.status == "error"
    assert record.error_code == "xlsx_error"
    assert "uncompressed byte limit" in record.error_message


def test_rejects_unsafe_scan_roots(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError):
        build_artifact_manifest(project, scan_roots=("../outside",))
