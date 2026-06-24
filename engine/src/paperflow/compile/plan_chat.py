"""Stage-3 chat: refine the saved plan (main contribution, subheadings, figure intent)
through conversation. One LLM call per turn; returns a reply + an applied patch.
"""
from __future__ import annotations

import json

from ..llm import client
from ..util import prompt


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
    return plan


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
