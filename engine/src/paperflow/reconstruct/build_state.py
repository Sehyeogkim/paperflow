"""Build the canonical research state + evidence inventory from ProjectState.

Two layers:
  - deterministic: profile every file, attach the user's description, infer a coarse role,
    and lift a research-state skeleton out of the core message / outline / data / references.
  - optional LLM enrichment: fill the inferential research-state fields (study_type,
    research_problem, study_design, outcomes ...). Skipped (gracefully) when no API key.

The deterministic layer alone is enough to run the rest of the MVP offline.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config
from ..schemas.evidence_inventory import EvidenceAsset, EvidenceInventory
from ..schemas.project_state import ProjectState
from ..schemas.research_state import Dataset, ResearchState
from . import profile_data

RESEARCH_STATE_FILE = "research_state.json"
EVIDENCE_INVENTORY_FILE = "evidence_inventory.json"

# (keyword set, inferred_role, unit_of_analysis, related_sections, artifact_usage). First match
# wins. Heuristic, conservative; LLM enrichment (when available) can refine.
_ROLE_RULES: list[tuple[tuple[str, ...], str, str, list[str], list[str]]] = [
    (("sobol_grp", "grp", "group"), "global sensitivity result", "input-variable group",
     ["method", "result", "discussion"], ["figure"]),
    (("sobol", "sensitivity"), "global sensitivity result", "input variable",
     ["method", "result", "discussion"], ["figure"]),
    (("input", "design"), "input design space", "sample", ["method"], ["table"]),
    (("inflow", "elastance", "boundary", "/bc", "bc.md"), "boundary condition", "",
     ["method"], []),
    (("reference", ".bib", "references"), "reference list", "", ["introduction", "discussion"], []),
]
_KIND_ROLE: dict[str, tuple[str, list[str], list[str]]] = {
    "png": ("figure", ["result"], ["figure"]), "jpg": ("figure", ["result"], ["figure"]),
    "jpeg": ("figure", ["result"], ["figure"]), "svg": ("figure", ["result"], ["figure"]),
    "pdf": ("reference document", ["introduction", "discussion"], []),
    "md": ("supporting document", [], []), "txt": ("supporting document", [], []),
    "dat": ("measurement / waveform", ["method", "result"], []),
    "json": ("structured record", [], []),
}


def _infer_role(rel: str, desc: str, kind: str) -> tuple[str, str, list[str], list[str], str]:
    """(role, unit, related_sections, artifact_usage, confidence). Description present OR a
    filename/context rule match -> high; kind-based default -> medium; nothing -> low/unknown."""
    hay = f"{rel} {desc}".lower()
    for keys, role, unit, secs, arts in _ROLE_RULES:
        if any(k in hay for k in keys):
            conf = "high"
            return role, unit, list(secs), list(arts), conf
    if kind in _KIND_ROLE:
        role, secs, arts = _KIND_ROLE[kind]
        return role, "", list(secs), list(arts), ("high" if desc.strip() else "medium")
    return "unknown", "", [], [], ("high" if desc.strip() else "low")


def _inferred_description(role: str, unit: str, columns: dict, user_desc: str) -> str:
    if user_desc.strip():
        return user_desc.strip()        # user statement is the source of truth (LLM may extend)
    parts = [role] if role and role != "unknown" else []
    if unit:
        parts.append(f"per {unit}")
    if columns:
        parts.append("columns: " + ", ".join(list(columns)[:8]))
    return "; ".join(parts)


def build_evidence_inventory(project_dir: str, ps: ProjectState) -> EvidenceInventory:
    """Profile every data asset and record it as a GLOBAL research evidence asset (deterministic).
    Description is optional — role/meaning is inferred from filename, columns, content, context."""
    project = Path(project_dir)
    assets: list[EvidenceAsset] = []
    for d in ps.data_assets:
        prof = profile_data.profile_file(project / d.path)
        columns: dict[str, str] = {}
        if isinstance(prof.get("columns"), dict):
            columns = {k: str(v) for k, v in prof["columns"].items()}
        elif prof.get("sheets"):  # xlsx: merge first sheet's columns for a quick view
            first = next(iter(prof["sheets"].values()), {})
            columns = {k: str(v) for k, v in (first.get("columns") or {}).items()}
        role, unit, secs, arts, conf = _infer_role(d.path, d.note, d.kind)
        assets.append(EvidenceAsset(
            path=d.path, kind=d.kind, user_description=d.note,
            inferred_description=_inferred_description(role, unit, columns, d.note),
            inferred_role=role, unit_of_analysis=unit,
            related_sections=secs, artifact_usage=arts, confidence=conf,
            columns=columns, profile=prof,
        ))
    return EvidenceInventory(assets=assets)


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    for sep in (". ", ".\n", "다. ", "다.\n"):
        i = text.find(sep)
        if i != -1:
            return text[: i + len(sep)].strip()
    return text.splitlines()[0].strip() if text else ""


def build_research_state_skeleton(ps: ProjectState, inventory: EvidenceInventory) -> ResearchState:
    """Lift a research-state skeleton from the parsed inputs (no LLM)."""
    cm = ps.core_message
    primary = cm.one_sentence.strip() or (cm.summary_bullets[0] if cm.summary_bullets else "")
    objective = _first_sentence(cm.one_paragraph) or primary

    datasets: list[Dataset] = []
    input_variables: list[str] = []
    for a in inventory.assets:
        if a.kind in ("csv", "xlsx", "xls", "dat"):
            datasets.append(Dataset(name=Path(a.path).stem, path=a.path,
                                    description=a.user_description, role=a.inferred_role))
        if "input" in a.inferred_role and a.columns:
            input_variables.extend(c for c in a.columns if c not in input_variables)

    possible_claims: list[str] = list(cm.summary_bullets)
    for p in ps.outline.skeleton:
        if p.claim_sentence and p.claim_sentence not in possible_claims:
            possible_claims.append(p.claim_sentence)

    rs = ResearchState(
        primary_message=primary,
        objective=objective,
        datasets=datasets,
        input_variables=input_variables,
        key_observations=list(cm.summary_bullets),
        possible_claims=possible_claims,
        limitations=list(cm.out_of_scope),
        known_references=list(ps.reference_keys),
        source="skeleton",
    )
    # flag the inferential fields the skeleton could not fill — these become reconstruction gaps
    for field in ("study_type", "research_problem", "study_design"):
        if not getattr(rs, field):
            rs.unknowns.append(field)
    if not rs.outcomes:
        rs.unknowns.append("outcomes")
    return rs


def enrich_research_state(ps: ProjectState, rs: ResearchState,
                          inventory: EvidenceInventory) -> ResearchState:
    """Optional LLM pass that fills the inferential fields. Never raises — on any failure
    (no key, bad JSON, API error) the skeleton is returned unchanged."""
    from ..llm import client
    from ..util import inputs_block, prompt
    try:
        sys = prompt("reconstruct_state")
    except Exception:
        return rs
    inv_block = json.dumps(
        [{"path": a.path, "role": a.inferred_role, "unit": a.unit_of_analysis,
          "description": a.user_description, "columns": list(a.columns)} for a in inventory.assets],
        ensure_ascii=False)
    user = (f"{inputs_block(ps)}\n\n## EVIDENCE INVENTORY\n{inv_block}\n\n"
            f"## CURRENT SKELETON\n{rs.model_dump_json(indent=2)}")
    try:
        raw = client.call_json("reasoning", sys, user, step="reconstruct.state", max_tokens=2500)
    except Exception:
        return rs
    # merge: LLM fills scalars + extends lists, but never deletes skeleton facts
    merged = rs.model_dump()
    for k in ("study_type", "research_problem", "objective", "study_design", "primary_message"):
        if isinstance(raw.get(k), str) and raw[k].strip():
            merged[k] = raw[k].strip()
    for k in ("methods", "outcomes", "comparisons", "key_observations", "possible_claims",
              "limitations", "input_variables"):
        extra = [str(x).strip() for x in (raw.get(k) or []) if str(x).strip()]
        merged[k] = list(dict.fromkeys([*merged.get(k, []), *extra]))
    merged["unknowns"] = [u for u in merged.get("unknowns", []) if not merged.get(u)]
    merged["source"] = "llm_enriched"
    try:
        return ResearchState.model_validate(merged)
    except Exception:
        return rs


def enrich_evidence_inventory(ps: ProjectState, inventory: EvidenceInventory) -> EvidenceInventory:
    """Optional LLM pass: infer each file's meaning/role from filename + columns + sample values
    + project context (core message, research plan, outline, sibling files). User descriptions
    are kept as the source of truth and only extended; conflicts are flagged as uncertainties.
    Never raises — falls back to the deterministic inventory on any failure."""
    from ..llm import client
    from ..util import inputs_block, prompt
    if not inventory.assets:
        return inventory
    try:
        sys = prompt("infer_evidence")
    except Exception:
        return inventory
    files = [{
        "path": a.path, "kind": a.kind, "user_description": a.user_description,
        "columns": list(a.columns), "profile": {k: a.profile.get(k) for k in
                  ("rows", "numeric_ranges", "sample_row", "sheets") if k in a.profile},
    } for a in inventory.assets]
    user = (f"{inputs_block(ps)}\n\n## FILES TO INFER (return one object per path)\n"
            f"{json.dumps(files, ensure_ascii=False)[:9000]}")
    try:
        raw = client.call_json("reasoning", sys, user, step="reconstruct.evidence", max_tokens=3500)
    except Exception:
        return inventory
    by_path = {str(r.get("path")): r for r in (raw.get("files") or []) if isinstance(r, dict)}
    for a in inventory.assets:
        r = by_path.get(a.path)
        if not r:
            continue
        if isinstance(r.get("inferred_description"), str) and r["inferred_description"].strip():
            a.inferred_description = r["inferred_description"].strip()
        if isinstance(r.get("inferred_role"), str) and r["inferred_role"].strip():
            a.inferred_role = r["inferred_role"].strip()
        if isinstance(r.get("unit_of_analysis"), str) and r["unit_of_analysis"].strip():
            a.unit_of_analysis = r["unit_of_analysis"].strip()
        for fld in ("related_sections", "artifact_usage", "key_observations", "uncertainties"):
            vals = [str(x).strip() for x in (r.get(fld) or []) if str(x).strip()]
            if vals:
                setattr(a, fld, list(dict.fromkeys(vals)))
        if str(r.get("confidence", "")).lower() in ("high", "medium", "low"):
            a.confidence = str(r["confidence"]).lower()
    return inventory


def reconstruct(project_dir: str, ps: ProjectState | None = None,
                use_llm: bool | None = None) -> tuple[ResearchState, EvidenceInventory]:
    """Build (research_state, evidence_inventory). use_llm=None -> auto (on if a key exists)."""
    if ps is None:
        from ..ingest.parse_inputs import ingest
        ps = ingest(project_dir)
    if use_llm is None:
        use_llm = bool(config.available_providers())
    inventory = build_evidence_inventory(project_dir, ps)
    if use_llm:
        inventory = enrich_evidence_inventory(ps, inventory)
    rs = build_research_state_skeleton(ps, inventory)
    if use_llm:
        rs = enrich_research_state(ps, rs, inventory)
    return rs, inventory


# ---------- persistence (main/ working copies; also bundled into _paperflow_out) ----------

def _main(project_dir: str) -> Path:
    p = Path(project_dir) / "main"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save(project_dir: str, rs: ResearchState, inventory: EvidenceInventory) -> None:
    m = _main(project_dir)
    (m / RESEARCH_STATE_FILE).write_text(rs.model_dump_json(indent=2))
    (m / EVIDENCE_INVENTORY_FILE).write_text(inventory.model_dump_json(indent=2))


def load(project_dir: str) -> tuple[ResearchState | None, EvidenceInventory | None]:
    m = Path(project_dir) / "main"
    rs = inv = None
    rp, ip = m / RESEARCH_STATE_FILE, m / EVIDENCE_INVENTORY_FILE
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
