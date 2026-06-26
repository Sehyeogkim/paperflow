"""Step 8 — generated-file listing + read-only HTML preview endpoints."""
from pathlib import Path

from fastapi.testclient import TestClient

from paperflow.output import manuscript_state as ms_mod
from paperflow.output import write_docx
from paperflow.server.app import app

client = TestClient(app)


def _seed_output(tmp_path: Path) -> str:
    out = tmp_path / "_paperflow_out"
    out.mkdir(parents=True)
    ms = ms_mod.build({"method": "We did **X**.", "result": "Material dominates."},
                      meta={"title": "Demo Paper", "authors": "A B"})
    (out / "manuscript.json").write_text(ms.model_dump_json(indent=2))
    (out / "Method.md").write_text("## Setup\nWe did X with <unsafe> chars.")
    (out / "claim_graph.json").write_text('{"nodes": [], "edges": []}')
    write_docx.write_docx(ms, out / "paper.docx")
    return str(tmp_path)


def test_output_list(tmp_path):
    pdir = _seed_output(tmp_path)
    r = client.get("/api/projects/output/list", params={"project_dir": pdir})
    names = {f["name"] for f in r.json()["files"]}
    assert {"manuscript.json", "Method.md", "paper.docx"} <= names
    docx_entry = next(f for f in r.json()["files"] if f["name"] == "paper.docx")
    assert docx_entry["previewable"] is True


def test_preview_manuscript_json_renders_html(tmp_path):
    pdir = _seed_output(tmp_path)
    r = client.get("/api/projects/output/preview",
                   params={"project_dir": pdir, "rel": "_paperflow_out/manuscript.json"})
    data = r.json()
    assert data["kind"] == "manuscript"
    assert "Demo Paper" in data["html"]
    assert "pf-preview" in data["html"]


def test_preview_md_is_escaped(tmp_path):
    pdir = _seed_output(tmp_path)
    r = client.get("/api/projects/output/preview",
                   params={"project_dir": pdir, "rel": "_paperflow_out/Method.md"})
    data = r.json()
    assert data["kind"] == "md"
    assert "<h2>Setup</h2>" in data["html"]
    assert "&lt;unsafe&gt;" in data["html"]      # escaped, not injected


def test_preview_docx_flags_download(tmp_path):
    pdir = _seed_output(tmp_path)
    r = client.get("/api/projects/output/preview",
                   params={"project_dir": pdir, "rel": "_paperflow_out/paper.docx"})
    assert r.json()["download"] is True


def test_output_file_download_and_traversal_guard(tmp_path):
    pdir = _seed_output(tmp_path)
    r = client.get("/api/projects/output/file",
                   params={"project_dir": pdir, "rel": "_paperflow_out/paper.docx"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats")
    # path traversal is refused
    bad = client.get("/api/projects/output/preview",
                     params={"project_dir": pdir, "rel": "../../../etc/passwd"})
    assert bad.json().get("error") == "not_found"
