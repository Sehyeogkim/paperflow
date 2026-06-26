"""Parse the 3 input files (main/0,1,3) into ProjectState + scan data/ and reference/.

Deterministic, no LLM. Tolerant of formatting drift (matches on ## heading keywords).
Input contract per main/ : 0_journal_info.md, 1_coremessage.md, 3_outline.md
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

from ..schemas.evidence_inventory import EvidenceInventory
from ..schemas.project_state import (
    CoreMessage, DataAsset, JournalInfo, Outline, OutlineParagraph, ProjectState,
)
from ..schemas.research_state import ResearchState


def _sections(md: str) -> dict[str, str]:
    """Split a markdown doc into {lowercased ## heading: body}."""
    out: dict[str, str] = {}
    cur = None
    buf: list[str] = []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.*)", line)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur = m.group(1).strip().lower()
            buf = []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def _find(sec: dict[str, str], *keywords: str) -> str:
    for k, v in sec.items():
        if all(kw in k for kw in keywords):
            return v
    return ""


def _bullets(body: str) -> list[str]:
    return [re.sub(r"^[-*]\s+", "", ln).strip()
            for ln in body.splitlines() if re.match(r"^\s*[-*]\s+", ln)]


def parse_journal_info(md: str) -> JournalInfo:
    sec = _sections(md)
    extra: dict[str, str] = {}
    for b in _bullets(_find(sec, "extra") or _find(sec, "optional")):
        m = re.match(r"(.+?)\s*[:：]\s*(.*)", b)
        if m:
            key = re.sub(r"\s*\(.*?\)\s*", "", m.group(1)).strip().lower()
            extra[key] = m.group(2).strip()
    return JournalInfo(
        working_title=_find(sec, "working", "title") or _find(sec, "title"),
        author_field=_find(sec, "field"),
        target_journals=_find(sec, "target") or _find(sec, "journal"),
        extra=extra, raw=md,
    )


def parse_core_message(md: str) -> CoreMessage:
    sec = _sections(md)
    # novelty (preferred) maps to the key-claims list the claim graph builds from
    summary = _bullets(_find(sec, "novelty") or _find(sec, "핵심")
                       or _find(sec, "summary") or _find(sec, "one thing"))
    kw_raw = _find(sec, "keyword")
    keywords = [k.strip() for k in re.split(r"[,;\n]", kw_raw) if k.strip()]
    oos_raw = _find(sec, "out of scope") or _find(sec, "scope")
    # accept either bullet list or free text
    oos = _bullets(oos_raw) or [ln.strip() for ln in oos_raw.splitlines() if ln.strip()]
    return CoreMessage(
        one_sentence=_find(sec, "one sentence") or _find(sec, "sentence"),
        one_paragraph=_find(sec, "one paragraph") or _find(sec, "paragraph"),
        summary_bullets=summary,
        keywords=keywords,
        out_of_scope=oos,
        raw=md,
    )


def parse_outline(md: str) -> Outline:
    """Phase A = numbered claim sentences with optional [Section] labels.
    Phase B kept as raw text."""
    phase_a, phase_b = md, ""
    # split on a Phase B heading if present
    m = re.search(r"^##\s*Phase\s*B.*$", md, re.IGNORECASE | re.MULTILINE)
    if m:
        phase_a, phase_b = md[: m.start()], md[m.start():]

    skeleton: list[OutlineParagraph] = []
    label = ""
    for line in phase_a.splitlines():
        lm = re.match(r"^\[(.+?)\]\s*$", line.strip())
        if lm:
            label = lm.group(1).strip()
            continue
        nm = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if nm:
            skeleton.append(OutlineParagraph(
                n=int(nm.group(1)), section_label=label, claim_sentence=nm.group(2).strip()))
    return Outline(skeleton=skeleton, structured_raw=phase_b.strip(), raw=md)


def _read_data_notes(project: Path) -> dict[str, str]:
    """Per-file one-line descriptions written in the UI (main/data_notes.json)."""
    p = project / "main" / "data_notes.json"
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text())
        return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}
    except Exception:
        return {}


def _scan_data(project: Path) -> list[DataAsset]:
    assets: list[DataAsset] = []
    ddir = project / "data"
    if not ddir.is_dir():
        return assets
    notes = _read_data_notes(project)
    for p in sorted(ddir.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(project))
        note = notes.get(rel, "")
        suf = p.suffix.lower().lstrip(".")
        if suf == "csv":
            cols: list[str] = []
            try:
                with p.open(newline="") as f:
                    cols = next(csv.reader(io.StringIO(f.readline())), [])
            except Exception:
                pass
            assets.append(DataAsset(path=rel, kind="csv", columns=cols, note=note))
        elif suf in ("md", "dat", "txt", "json", "pdf", "png", "jpg", "jpeg", "xlsx", "xls"):
            assets.append(DataAsset(path=rel, kind=suf, note=note))
    return assets


def _reference_keys(project: Path) -> list[str]:
    rj = project / "reference" / "references.json"
    if not rj.is_file():
        return []
    try:
        data = json.loads(rj.read_text())
        items = data if isinstance(data, list) else data.get("references", [])
        return [it.get("key", "") for it in items if it.get("key")]
    except Exception:
        return []


def _read_answers(main: Path) -> dict[str, str]:
    """Gate A answers: main/answer.json = {field: answer}."""
    p = main / "answer.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text())
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_style(main: Path) -> str:
    """Author writing style (D constraint): main/style.md."""
    p = main / "style.md"
    return p.read_text().strip() if p.is_file() else ""


def _read_reconstruction(main: Path) -> tuple[ResearchState | None, EvidenceInventory | None]:
    """Load previously-built reconstruction state if present (no LLM, no rebuild).
    Keeps ingest() cheap/deterministic; reconstruct.build_state writes these files."""
    rs = inv = None
    rp, ip = main / "research_state.json", main / "evidence_inventory.json"
    if rp.is_file():
        try:
            rs = ResearchState.model_validate_json(rp.read_text())
        except Exception:
            rs = None
    if ip.is_file():
        try:
            inv = EvidenceInventory.model_validate_json(ip.read_text())
        except Exception:
            inv = None
    return rs, inv


def _read_optional(p: Path) -> str:
    """Read a file, or '' if absent. Outline is optional (minimal-input mode); journal/core
    may also be filled in later — ingest must never crash on a partial project."""
    try:
        return p.read_text()
    except FileNotFoundError:
        return ""


def ingest(project_dir: str) -> ProjectState:
    project = Path(project_dir)
    main = project / "main"
    js = parse_journal_info(_read_optional(main / "0_journal_info.md"))
    cm = parse_core_message(_read_optional(main / "1_coremessage.md"))
    ol = parse_outline(_read_optional(main / "3_outline.md"))
    rs, inv = _read_reconstruction(main)
    return ProjectState(
        project_dir=str(project),
        journal_info=js, core_message=cm, outline=ol,
        data_assets=_scan_data(project),
        reference_keys=_reference_keys(project),
        answers=_read_answers(main),
        style=_read_style(main),
        research_state=rs, evidence_inventory=inv,
    )
