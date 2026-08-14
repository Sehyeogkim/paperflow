"""Unified multi-provider LLM client.

call(tier, system, user) -> LLMResult{text, input_tokens, output_tokens, provider, model}

Thin httpx adapters (no heavy SDKs) so token usage is captured directly and any
provider can be swapped via config. Each call is logged into the active RunManifest
(set via `set_manifest`) for cost measurement — the MVP's core metric.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from dataclasses import dataclass

import httpx

from .. import config
from ..schemas.eval import CallRecord, RunManifest

_TIMEOUT = httpx.Timeout(120.0)
_manifest_var: ContextVar[RunManifest | None] = ContextVar("paperflow_manifest", default=None)


def set_manifest(m: RunManifest) -> None:
    _manifest_var.set(m)


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str
    cached_tokens: int = 0  # prompt tokens served from cache (subset of input_tokens)


class LLMError(RuntimeError):
    pass


def call(tier: str, system: str, user: str, *, step: str = "", max_tokens: int = 4096,
         temperature: float = 0.3) -> LLMResult:
    ref = config.pick_available(tier)
    key = config.api_key(ref.provider)
    if not key:
        raise LLMError(
            f"No API key for any provider (tier={tier}). Add keys to engine/.env "
            f"(OPENAI_API_KEY / DEEPSEEK_API_KEY / GEMINI_API_KEY / ANTHROPIC_API_KEY)."
        )

    if ref.provider in ("openai", "deepseek"):
        res = _openai_compatible(ref.provider, ref.model, key, system, user, max_tokens, temperature)
    elif ref.provider == "anthropic":
        res = _anthropic(ref.model, key, system, user, max_tokens, temperature)
    elif ref.provider == "gemini":
        res = _gemini(ref.model, key, system, user, max_tokens, temperature)
    else:
        raise LLMError(f"Unsupported provider: {ref.provider}")

    manifest = _manifest_var.get()
    if manifest is not None:
        manifest.calls.append(CallRecord(
            step=step or tier, tier=tier, provider=ref.provider, model=ref.model,
            input_tokens=res.input_tokens, output_tokens=res.output_tokens,
            cached_tokens=res.cached_tokens,
        ))
    return res


def call_json(tier: str, system: str, user: str, *, step: str = "", max_tokens: int = 4096) -> dict:
    """Call expecting a JSON object back. Tolerant of ```json fences / surrounding prose.
    Retries once on a parse failure (a single bad JSON must not crash the pipeline)."""
    sys2 = system + "\n\nReturn ONLY a single valid JSON object. No prose, no markdown fences."
    last: Exception | None = None
    for _ in range(2):
        r = call(tier, sys2, user, step=step, max_tokens=max_tokens, temperature=0.1)
        try:
            return _extract_json(r.text)
        except LLMError as e:
            last = e
    raise last  # type: ignore[misc]


# ---------- provider adapters ----------

def _openai_compatible(provider, model, key, system, user, max_tokens, temperature) -> LLMResult:
    base = "https://api.openai.com/v1" if provider == "openai" else "https://api.deepseek.com"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    # gpt-5 / o-series reasoning models: use max_completion_tokens, fixed temperature
    if provider == "openai" and (model.startswith("gpt-5") or model.startswith(("o1", "o3", "o4"))):
        payload["max_completion_tokens"] = max(max_tokens, 16000)  # reasoning eats output budget
    else:
        payload["max_tokens"] = max_tokens
        payload["temperature"] = temperature
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(f"{base}/chat/completions",
                   headers={"Authorization": f"Bearer {key}"}, json=payload)
    _raise_for(r, provider)
    d = r.json()
    usage = d.get("usage", {})
    # OpenAI exposes cache hits under prompt_tokens_details.cached_tokens (auto prompt caching)
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return LLMResult(
        text=d["choices"][0]["message"]["content"] or "",
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        provider=provider, model=model, cached_tokens=cached,
    )


def _anthropic(model, key, system, user, max_tokens, temperature) -> LLMResult:
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json={
                "model": model, "max_tokens": max_tokens, "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
    _raise_for(r, "anthropic")
    d = r.json()
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    usage = d.get("usage", {})
    # Anthropic reports cache reads separately; input_tokens excludes them, so add for a true total
    cache_read = usage.get("cache_read_input_tokens", 0)
    return LLMResult(text=text, input_tokens=usage.get("input_tokens", 0) + cache_read,
                     output_tokens=usage.get("output_tokens", 0), provider="anthropic", model=model,
                     cached_tokens=cache_read)


def _gemini(model, key, system, user, max_tokens, temperature) -> LLMResult:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    with httpx.Client(timeout=_TIMEOUT) as c:
        r = c.post(
            url, params={"key": key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
            },
        )
    _raise_for(r, "gemini")
    d = r.json()
    cand = (d.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    um = d.get("usageMetadata", {})
    return LLMResult(text=text, input_tokens=um.get("promptTokenCount", 0),
                     output_tokens=um.get("candidatesTokenCount", 0), provider="gemini", model=model,
                     cached_tokens=um.get("cachedContentTokenCount", 0))


def _raise_for(r: httpx.Response, provider: str) -> None:
    if r.status_code >= 400:
        raise LLMError(f"{provider} API error {r.status_code}: {r.text[:400]}")


def _extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
        t = t.strip("`").strip()
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise LLMError(f"Model did not return valid JSON: {e}\n--- got ---\n{text[:600]}")
