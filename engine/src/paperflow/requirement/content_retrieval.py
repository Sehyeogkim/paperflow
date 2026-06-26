"""Stage 6: attach the best available content level to each paper.

MVP: OpenAlex abstracts are the default (`abstract_only`). If the author uploaded a PDF whose
title/DOI matches a selected paper, we promote it to `full_text`. The retriever is an adapter
(Protocol) so a future Exa/open-access full-text fetcher can plug in without touching callers.
"""
from __future__ import annotations

import re
from typing import Protocol

from ..schemas.literature import LiteraturePaper
from ..schemas.project_state import ProjectState


class ContentRetriever(Protocol):
    def fetch(self, paper: LiteraturePaper) -> tuple[str, str] | None:
        """Return (content_level, text) or None if no better content is available."""
        ...


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def attach_content(papers: list[LiteraturePaper], ps: ProjectState,
                   retriever: ContentRetriever | None = None) -> list[LiteraturePaper]:
    """Promote papers to full/partial text where a local source matches; else keep abstract_only.
    Never raises — content discovery is best-effort."""
    # local PDFs the user uploaded (title/DOI match → treat as full text we can quote)
    pdfs = [a for a in (ps.data_assets or []) if str(getattr(a, "path", "")).lower().endswith(".pdf")]
    pdf_tokens = [_norm(getattr(a, "path", "")) + " " + _norm(getattr(a, "note", "")) for a in pdfs]

    out: list[LiteraturePaper] = []
    for p in papers:
        level, _ = p.content_level, None
        if retriever is not None:
            try:
                got = retriever.fetch(p)
                if got:
                    lvl, text = got
                    out.append(p.model_copy(update={"content_level": lvl,
                                                    "abstract": text or p.abstract,
                                                    "source": "open_access_url"}))
                    continue
            except Exception:
                pass
        title_tok = _norm(p.title)
        doi_tok = _norm(p.doi)
        if title_tok and any(title_tok[:40] in t or (doi_tok and doi_tok in t) for t in pdf_tokens):
            out.append(p.model_copy(update={"content_level": "full_text", "source": "user_pdf"}))
        else:
            out.append(p)
    return out
