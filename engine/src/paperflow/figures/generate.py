"""Generate figure images with fal.ai nano-banana pro.

Derives the figure list from the (Fig N — caption) references in the generated sections,
turns each caption into a detailed image prompt (LLM), calls fal, and saves PNGs.

Runs independently of section generation (cheap to re-run via `paperflow figures`).
"""
from __future__ import annotations

import re
from pathlib import Path

import httpx

from .. import config
from ..llm import client
from ..util import prompt

# capture figures in several reference styles:
#   (Fig 3 — caption) / ( Fig 4 — caption)  |  Fig 6 (caption)  |  Fig 7 — caption ...
_FIG_RES = [
    re.compile(r"\(\s*Fig\.?\s*(\d+)\s*[—:\-]\s*([^)]+)\)", re.IGNORECASE),
    re.compile(r"\bFig\.?\s*(\d+)\s*\(([^)]+)\)", re.IGNORECASE),
    re.compile(r"\bFig\.?\s*(\d+)\s*[—:\-]\s*([^.)\n]{6,120})", re.IGNORECASE),
]


def _collect(out_dir: Path) -> dict[str, str]:
    figs: dict[str, str] = {}
    for md in out_dir.glob("*.md"):
        text = md.read_text()
        for rx in _FIG_RES:
            for n, cap in rx.findall(text):
                cap = cap.strip().strip("()").strip()
                if cap and (n not in figs or len(cap) > len(figs[n])):
                    figs[n] = cap
    return dict(sorted(figs.items(), key=lambda kv: int(kv[0])))


def _image_prompt(core_message: str, caption: str) -> str:
    user = f"## PAPER CORE MESSAGE\n{core_message}\n\n## FIGURE CAPTION\nFig — {caption}"
    return client.call("fast", prompt("figure_prompt"), user, step="figure.prompt",
                       max_tokens=600).text.strip()


def _fal_generate(model: str, img_prompt: str) -> bytes:
    key = config.api_key("fal")
    with httpx.Client(timeout=httpx.Timeout(180.0)) as c:
        r = c.post(f"https://fal.run/{model}",
                   headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
                   json={"prompt": img_prompt})
        if r.status_code >= 400:
            raise RuntimeError(f"fal error {r.status_code}: {r.text[:200]}")
        url = r.json()["images"][0]["url"]
        return c.get(url, timeout=180.0).content


def generate(project_dir: str, out_dir: Path, core_message: str,
             progress=lambda m: None) -> list[dict]:
    img_model = config.resolve("image").model
    if not config.api_key("fal"):
        progress("FAL_KEY 없음 — figure 생성 skip")
        return []
    figs = _collect(out_dir)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    made: list[dict] = []
    for n, cap in figs.items():
        progress(f"figure {n}: prompt")
        p = _image_prompt(core_message, cap)
        progress(f"figure {n}: nano-banana-pro 생성")
        try:
            data = _fal_generate(img_model, p)
        except Exception as e:  # one figure failing must not kill the rest
            made.append({"fig": n, "caption": cap, "error": str(e)[:160]})
            continue
        path = fig_dir / f"fig{n}.png"
        path.write_bytes(data)
        made.append({"fig": n, "caption": cap, "prompt": p, "file": str(path.name),
                     "bytes": len(data)})
    return made
