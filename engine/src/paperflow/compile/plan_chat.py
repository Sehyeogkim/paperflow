"""Stage-3 chat: refine the saved plan (main contribution, subheadings, figure intent)
through conversation. One LLM call per turn; returns a reply + an applied patch.
"""
from __future__ import annotations

import json

from ..llm import client
from ..util import prompt
from .claim_graph import validate

# edge relations that ground a claim with its supporting nodes, by the supporting node's kind.
_SUPPORT_KINDS = ("evidence", "method", "data", "warrant", "source", "artifact")


def _graph_tree(plan: dict) -> list[str]:
    """Render the claim graph as a per-claim tree: each main claim -> its subclaims ->
    each claim's directly supporting evidence/method/data/warrant/source/artifact."""
    cg = plan.get("claim_graph") or {}
    nodes = [n for n in (cg.get("nodes") or []) if isinstance(n, dict) and n.get("id")]
    edges = [e for e in (cg.get("edges") or []) if isinstance(e, dict)]
    by_id = {n["id"]: n for n in nodes}
    claims = [n for n in nodes if n.get("kind") == "claim"]
    if not claims:
        return []
    # main claims = claim nodes with no parent_id; subclaims keyed by parent.
    mains = [c for c in claims if not c.get("parent_id")]
    subs_of: dict[str, list[dict]] = {}
    for c in claims:
        pid = c.get("parent_id")
        if pid:
            subs_of.setdefault(pid, []).append(c)
    if not mains:  # no parent links -> treat every claim as a main claim
        mains = claims

    def supports(claim_id: str) -> list[str]:
        out = []
        for e in edges:
            if e.get("dst") != claim_id:
                continue
            src = by_id.get(e.get("src"))
            if src and src.get("kind") in _SUPPORT_KINDS:
                out.append(f"        - [{src['kind']}] {src.get('text', '')} (via {e.get('rel')})")
        return out

    def render_claim(c: dict, indent: str) -> list[str]:
        rows = [f"{indent}- ({c['id']}) {c.get('text', '')}"]
        rows.extend(supports(c["id"]))
        return rows

    lines = ["", "claim graph (per-claim tree):"]
    for m in mains:
        lines.extend(render_claim(m, "  "))
        for sub in subs_of.get(m["id"], []):
            lines.extend(render_claim(sub, "    "))
    return lines


def _plan_summary(plan: dict) -> str:
    lines = [f"main_contribution: {plan.get('main_contribution', '')}", "", "structure:"]
    for sec, s in (plan.get("structure") or {}).items():
        subs = ", ".join(s.get("subheadings") or []) or "(none)"
        lines.append(f"  {sec}: {s.get('summary', '')}  | subheadings: {subs}")
    figs = (plan.get("figures") or {}).get("figures") or []
    if figs:
        lines.append("")
        lines.append("figures:")
        for f in figs:
            lines.append(f"  [{f.get('id')}] ({f.get('kind')}, {f.get('section')}): {f.get('message')}")
    lines.extend(_graph_tree(plan))
    return "\n".join(lines)


def _apply_patch(plan: dict, patch: dict) -> dict:
    if not isinstance(patch, dict):
        return plan
    if isinstance(patch.get("main_contribution"), str) and patch["main_contribution"].strip():
        plan["main_contribution"] = patch["main_contribution"].strip()
    struct = plan.setdefault("structure", {})
    for sec, s in (patch.get("structure") or {}).items():
        if not isinstance(s, dict):
            continue
        cur = struct.setdefault(sec, {"summary": "", "subheadings": []})
        if isinstance(s.get("summary"), str):
            cur["summary"] = s["summary"].strip()
        if isinstance(s.get("subheadings"), list):
            cur["subheadings"] = [str(h).strip() for h in s["subheadings"] if str(h).strip()]
    fig_patch = {f.get("id"): f.get("message") for f in (patch.get("figures") or [])
                 if isinstance(f, dict) and f.get("id")}
    for f in (plan.get("figures") or {}).get("figures") or []:
        if f.get("id") in fig_patch and isinstance(fig_patch[f["id"]], str):
            f["message"] = fig_patch[f["id"]].strip()
    gp = patch.get("graph_patch")
    if isinstance(gp, dict):
        _apply_graph_patch(plan, gp)
    return plan


def _apply_graph_patch(plan: dict, gp: dict) -> None:
    """Mutate plan['claim_graph'] (nodes/edges) per the graph_patch, then re-validate so
    invalid/dangling edges and unknown kinds are dropped."""
    cg = plan.setdefault("claim_graph", {})
    nodes = cg.setdefault("nodes", [])
    edges = cg.setdefault("edges", [])

    delete_node_ids = {str(i) for i in (gp.get("delete_node_ids") or [])}
    if delete_node_ids:
        nodes[:] = [n for n in nodes if str(n.get("id")) not in delete_node_ids]
        edges[:] = [e for e in edges
                    if str(e.get("src")) not in delete_node_ids
                    and str(e.get("dst")) not in delete_node_ids]

    for n in (gp.get("add_nodes") or []):
        if isinstance(n, dict) and n.get("id"):
            nodes.append(dict(n))

    update_nodes = {str(u.get("id")): u for u in (gp.get("update_nodes") or [])
                    if isinstance(u, dict) and u.get("id")}
    for n in nodes:
        u = update_nodes.get(str(n.get("id")))
        if u:
            for k, v in u.items():
                if k != "id":
                    n[k] = v

    delete_edge_ids = {str(i) for i in (gp.get("delete_edge_ids") or [])}
    if delete_edge_ids:
        edges[:] = [e for e in edges if str(e.get("id")) not in delete_edge_ids]

    for e in (gp.get("add_edges") or []):
        if isinstance(e, dict) and e.get("src") and e.get("dst"):
            edges.append(dict(e))

    for u in (gp.get("update_edges") or []):
        if not isinstance(u, dict):
            continue
        uid, usrc, udst = u.get("id"), u.get("src"), u.get("dst")
        for e in edges:
            matches_id = uid is not None and str(e.get("id")) == str(uid)
            matches_pair = (uid is None and usrc is not None and udst is not None
                            and e.get("src") == usrc and e.get("dst") == udst)
            if matches_id or matches_pair:
                for k, v in u.items():
                    e[k] = v

    plan["claim_graph"] = validate(cg)


def revise(plan: dict, history: list[dict], message: str) -> tuple[str, dict]:
    """Returns (reply, possibly-patched plan). The caller persists the plan."""
    convo = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in (history or [])[-8:])
    user = (f"## CURRENT PLAN\n{_plan_summary(plan)}\n\n"
            f"## CONVERSATION SO FAR\n{convo}\n\n## AUTHOR MESSAGE\n{message}")
    try:
        raw = client.call_json("reasoning", prompt("plan_chat"), user, step="plan_chat", max_tokens=2000)
    except Exception as e:
        return (f"(수정 처리 중 오류: {str(e)[:100]})", plan)
    reply = str(raw.get("reply", "")).strip() or "반영했어요."
    patch = raw.get("patch")
    if patch:
        plan = _apply_patch(plan, patch)
    return reply, plan
