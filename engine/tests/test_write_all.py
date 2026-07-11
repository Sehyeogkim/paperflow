"""Integration — write_all emits the full canonical artifact bundle (offline)."""
import json

import docx

from paperflow.output.write_fs import write_all
from paperflow.schemas.claim import ClaimGraph, GEdge, GNode
from paperflow.schemas.eval import RunManifest
from paperflow.schemas.requirement import CompletionClass, RequirementReport
from paperflow.schemas.research_state import ResearchState
from paperflow.schemas.evidence_inventory import EvidenceInventory, EvidenceAsset


def test_write_all_emits_manuscript_docx_grounding(tmp_path):
    out = tmp_path / "_paperflow_out"
    graph = ClaimGraph(nodes=[
        GNode(id="C1", kind="claim", text="Material dominates"),
        GNode(id="E1", kind="evidence", text="ST=0.72"),
    ], edges=[GEdge(src="E1", dst="C1", rel="supports")])
    figure_spec = {"figures": [{"id": "F1", "kind": "figure", "section": "result",
                                "message": "Sobol chart", "caption_draft": "Fig 1. Sobol.",
                                "generation_prompt": "Make a bar chart."}]}
    report = RequirementReport(study_type="x", classification=CompletionClass.EXPERT_REVIEW_REQUIRED)
    write_all(
        out,
        sections={"method": "We did **X**.", "result": "Material dominates."},
        graph=graph, contracts={}, requirement=report,
        figure_spec=figure_spec, manifest=RunManifest(project_dir=str(tmp_path)),
        found_references=[], paper_meta={"title": "T", "authors": "A B"},
        warnings=["claim_without_evidence: something"],
        research_state=ResearchState(primary_message="m"),
        evidence_inventory=EvidenceInventory(assets=[EvidenceAsset(path="data/x.csv", kind="csv")]),
    )
    # canonical + derived artifacts all present
    for name in ("manuscript.json", "paper.docx", "grounding_report.json",
                 "manuscript_preview.html", "research_state.json", "evidence_inventory.json",
                 "claim_graph.json", "paper.tex"):
        assert (out / name).is_file(), f"missing {name}"

    ms = json.loads((out / "manuscript.json").read_text())
    assert ms["meta"]["title"] == "T"
    assert ms["figures"][0]["id"] == "F1"
    assert ms["grounding"]["warnings"] == ["claim_without_evidence: something"]

    d = docx.Document(str(out / "paper.docx"))
    texts = "\n".join(p.text for p in d.paragraphs)
    assert "Material dominates." in texts and "T" in texts

    grounding = json.loads((out / "grounding_report.json").read_text())
    assert grounding["claims"][0]["id"] == "C1"
    # C1 has evidence only (no data/ref) -> partial
    assert grounding["claims"][0]["status"] == "partial"
