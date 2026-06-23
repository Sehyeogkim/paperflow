"""Config: load .env, resolve model registry (tier -> provider:model), API keys.

Keys are read from engine/.env (gitignored). If a key is missing, calls to that
provider raise a clear error — but the rest of the pipeline (parsing, requirement
checks that don't need that tier) still works.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# load engine/.env (next to pyproject), then process env as fallback
_ENGINE_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ENGINE_ROOT / ".env")

DEFAULT_REGISTRY = {
    "fast": os.getenv("PAPERFLOW_FAST_MODEL", "deepseek:deepseek-chat"),
    "writer": os.getenv("PAPERFLOW_WRITER_MODEL", "deepseek:deepseek-chat"),
    "reasoning": os.getenv("PAPERFLOW_REASONING_MODEL", "openai:gpt-4o"),
    "image": os.getenv("PAPERFLOW_IMAGE_MODEL", "fal:fal-ai/nano-banana"),
}

# escalation: if a tier's provider has no key, fall back along this chain
ESCALATION = ["fast", "writer", "reasoning"]


@dataclass
class ModelRef:
    tier: str
    provider: str
    model: str


def resolve(tier: str) -> ModelRef:
    spec = DEFAULT_REGISTRY.get(tier, DEFAULT_REGISTRY["writer"])
    provider, _, model = spec.partition(":")
    return ModelRef(tier=tier, provider=provider, model=model)


def api_key(provider: str) -> str | None:
    env = {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "fal": "FAL_KEY",
    }.get(provider)
    return os.getenv(env) if env else None


def available_providers() -> list[str]:
    return [p for p in ("openai", "deepseek", "gemini", "anthropic", "fal") if api_key(p)]


def pick_available(tier: str) -> ModelRef:
    """Resolve a tier, but if its provider has no key, walk the escalation chain
    to the first tier whose provider key exists (keeps the pipeline runnable with
    whatever single provider is configured)."""
    ref = resolve(tier)
    if api_key(ref.provider):
        return ref
    for t in ESCALATION:
        alt = resolve(t)
        if api_key(alt.provider):
            return ModelRef(tier=tier, provider=alt.provider, model=alt.model)
    return ref  # no keys at all — caller will error with a clear message
