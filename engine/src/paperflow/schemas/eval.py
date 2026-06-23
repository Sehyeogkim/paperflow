"""Run manifest — token accounting (the MVP's core measurement) + outcome summary."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .requirement import CompletionClass


class CallRecord(BaseModel):
    step: str
    tier: str               # fast | writer | reasoning
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # prompt tokens served from cache (subset of input_tokens)


class RunManifest(BaseModel):
    project_dir: str
    sections: list[str] = Field(default_factory=list)
    classification: CompletionClass | None = None
    calls: list[CallRecord] = Field(default_factory=list)

    @property
    def total_input(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_cached(self) -> int:
        return sum(c.cached_tokens for c in self.calls)

    @property
    def cache_hit_rate(self) -> float:
        """Fraction of input tokens served from cache (0.0–1.0)."""
        ti = self.total_input
        return (self.total_cached / ti) if ti else 0.0

    def by_step(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for c in self.calls:
            d = out.setdefault(c.step, {"input": 0, "output": 0, "cached": 0, "calls": 0})
            d["input"] += c.input_tokens
            d["output"] += c.output_tokens
            d["cached"] += c.cached_tokens
            d["calls"] += 1
        return out
