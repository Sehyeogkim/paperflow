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

# (keyword set, inferred_role, unit_of_analysis) — first match wins. Heuristic, deliberately
# conservative; the LLM enrichment (when available) can override role on research_state.
_ROLE_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("sobol_grp", "grp", "group"), "global sensitivity result", "input-variable group"),
    (("sobol", "sensitivity"), "global sensitivity result", "input variable"),
    (("input", "design"), "input design space", "sample"),
    (("inflow", "elastance", "boundary", "/bc", "bc.md"), "boundary condition", ""),
    (("reference", ".bib", "references"), "reference list", ""),
]
_KIND_ROLE = {
    "png": "figure", "jpg": "figure", "jpeg": "figure", "svg": "figure",
    "pdf": "reference document", "md": "supporting document", "txt": "supporting document",
    "dat": "measurement / waveform", "json": "structured record",
}


def _infer_role(rel: str, desc: str, kind: str) -> tuple[str, str]:
    hay = f"{rel} {desc}".lower()
    for keys, role, unit in _ROLE_RULES:
        if any(k in hay for k in keys):
            return role, unit
    return _KIND_ROLE.get(kind, "data file"), ""


def build_evidence_inventory(project_dir: str, ps: ProjectState) -> EvidenceInventory:
    """Profile every data asset and record it as research evidence (deterministic)."""
    project = Path(project_dir)
    assets: list[EvidenceAsset] = []
    for d in ps.data_assets:
        prof = profile_data.profile_file(project / d.path)
        # surface columns as {name: dtype} from the profile when present
        columns: dict[str, str] = {}
        if isinstance(prof.get("columns"), dict):
            columns = {k: str(v) for k, v in prof["columns"].items()}
        elif prof.get("sheets"):  # xlsx: merge first sheet's columns for a quick view
            first = next(iter(prof["sheets"].values()), {})
            columns = {k: str(v) for k, v in (first.get("columns") or {}).items()}
        role, unit = _infer_role(d.path, d.note, d.kind)
        assets.append(EvidenceAsset(
            path=d.path, kind=d.kind, user_description=d.note,
            inferred_role=role, unit_of_analysis=unit,
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


def reconstruct(project_dir: str, ps: ProjectState | None = None,
                use_llm: bool | None = None) -> tuple[ResearchState, EvidenceInventory]:
    """Build (research_state, evidence_inventory). use_llm=None -> auto (on if a key exists)."""
    if ps is None:
        from ..ingest.parse_inputs import ingest
        ps = ingest(project_dir)
    inventory = build_evidence_inventory(project_dir, ps)
    rs = build_research_state_skeleton(ps, inventory)
    if use_llm is None:
        use_llm = bool(config.available_providers())
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
