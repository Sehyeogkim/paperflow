# Journal Paper Template (with Codex agents)

This repo is a reusable template for writing academic journal papers with Codex(agents).
The goal: make journal writing **creative, easy, and convenient**.

## Repo layout

The root holds shared config (this file, `readme.md`, `.Codex/agents/`, `blackboard/design.md`).
**Each top-level subdirectory is ONE independent journal paper**, e.g.:

- `master_thesis/`
- `engineering_master_thesis/`

Agents and workflow are shared across all papers; the content in each subdir is not.

## Per-paper file layout

Each paper directory follows the same numbered structure, matching the workflow steps:

```

<paper>/
  0_journal_info.md     # working title, author's field, ranked target journals (+ optional affiliation/lab/advisor)
  1_coremessage.md      # the ONE thing the paper proves (1 sentence + 1 paragraph)
  2_figure_flow.md      # figure flow: each figure + the single message it conveys
  3_outline.md          # (A) skeleton: one claim-sentence per paragraph (logic check) -> (B) structured outline
  4_contents/         # the actual drafts (Korean -> English, in place)
    Intro.md
    method.md
    result.md
    discussion.md
  writing_style/        # per-journal style guides (e.g. <journal>.md)
  blackboard/           # HTML diagrams/visuals for THIS paper (style from root blackboard/design.md)
  reference/            # references.json (key + source location + verbatim quote) + references.bib
  data/                 # raw notes, numbers, references the paper draws on
```

The `reference/` store is the bridge to the manuscript: each entry has a stable `key`
used both in `references.bib` and in the LaTeX `\cite{key}`, plus the exact source
location and verbatim quote so the author can open the cited paper and read the line.

## Workflow (run in order, 0 -> 6, from the reference)

0. **Journal info & setup** — record the working title, author's field, and ranked target journals
   (+ optional affiliation/lab/advisor) in `0_journal_info.md`. Then fetch/record the #1 journal's
   structure & tone into `writing_style/<journal>.md`; the #1 journal is the default style.
1. **Core message** — 1 sentence + 1 paragraph: the ONE thing the paper proves. [mandatory]
2. **Figure flow** — list each figure and the single message it conveys (text only, no real figures yet).
3. **Outline** — two phases in `3_outline.md`: (A) *skeleton* — one claim-sentence per paragraph,
   read in sequence to catch logic gaps; (B) expand the validated skeleton into a structured
   outline, Intro -> Conclusion. Don't move on until the skeleton's argument actually flows.
4. **Draft Method + Result first** — these are grounded in what was actually done.
5. **Draft Intro + Discussion** — written once the Results' story is clear.
6. **Draft Abstract + Title last.**

## House rules

- The author drafts in **Korean first, then translates to English in the SAME file (replace in place).**
  Drafts live in `4_contents/<section>.md`; write the Korean draft there, then overwrite it with the
  English once confirmed — English is the final artifact (target journals are English). Preserve meaning
  and technical nuance over literal translation; keep terminology consistent with `writing_style/`.
- **Figure-first, result-first.** Never write Intro/Discussion/Abstract before the figures
  and Results story are settled.
- Every claim in prose should trace back to a figure, a number in `data/`, or a citation.
- Match the target journal's structure and tone (`writing_style/<journal>.md`) — section
  order, length, and voice vary by journal.
- When unsure what the paper is trying to say, re-read `1_coremessage.md` before drafting.
- **Save important project knowledge to `.Codex/memory_local/`.** Whenever a significant piece of
  project information arises or is discussed — a painpoint, a hypothesis, a product/design decision,
  a research direction, a constraint not derivable from the code — write it as a `.md` file in
  `.Codex/memory_local/` (one fact per file, kebab-case name), then add a one-line pointer to the
  index in `.Codex/memory_local/README.md`. Convert relative dates to absolute. Link related memories
  with `[[filename]]`. This is project-local memory that persists across sessions; read it to regain
  context. Do NOT duplicate what the code, git history, or this AGENTS.md already records.

## Agents

The workflow (0→6) is driven in the MAIN conversation with the author. Agents are
**helpers invoked at specific moments** — mostly for research, verification, and critique.
They live in `.Codex/agents/` (shared across all papers):

- `reference-hunter` — finds real, DOI-verified citations AND records exact source location +
  verbatim quote into `<paper>/reference/references.json` (+ `references.bib`).
- `reference-double-checker` — independently re-verifies the reference store: paper exists, quote
  is real at that location, supports our claim; updates each entry's verification status.
- `reviewer` — harsh peer-reviewer critique: rigor, gaps, unsupported claims.
- `advisor` — PI/advisor view: contribution, story, "so what?", framing.
- `data-analyzer` — verifies the author's analysis against `data/`; flags errors/gaps (never fabricates).
- `figure-schematic` — builds CONCEPTUAL figures as HTML/SVG (not data plots) into `<paper>/blackboard/`.
- `polish` — final pass: LaTeX correctness, grammar, terminology, journal-format conformance.

Tip: `reviewer` + `advisor` are most powerful run in **parallel** on a finished draft.
Roadmap: a future `figure-builder` that understands the whole paper and produces full figures.

## Blackboard

When the user asks to draw a diagram or explain something visually, make an **HTML file**.

- **Style is global, output is per-paper.** Read the shared style from the root
  `blackboard/design.md`. Write the HTML into the *current paper's* folder:
  `<paper>/blackboard/<descriptive_name>.html` (e.g. `workflow_overview.html`, not `diagram1.html`).
- Only read `blackboard/design.md` when a visual is actually requested; otherwise skip it.
- The blackboard is for **thinking and explaining during writing** — it is NOT the publication
  figure pipeline. Final paper figures are planned as text in `2_figure_flow.md` and produced by the
  author's real tooling (matplotlib/Illustrator → vector). Do not treat a blackboard HTML as a
  finished journal figure.

# When generating HTML visualizations, diagrams, or any styled output, use the Anthropic/Codex brand color palette:
- Background: #F0EEE6 (warm cream/beige)
- Primary accent: #CC785C (Codex Orange / terracotta)
- Secondary accent: #E8D5C4 (light warm brown)
- Borders/dividers: #D4C5B0 (muted tan)
- Text (headings): #1A1A1A (near-black)
- Text (body): #2D2D2D (dark charcoal)
- Text (secondary/muted): #6B5E54 (warm gray-brown)
- Code background: #E6E0D4 (slightly darker cream)
- Code text: #8B4513 (saddle brown)
- Success/positive: #7A9A6D (muted olive green)
- Error/negative: #C25744 (muted red-orange)
- Highlight: #CC785C at 15% opacity for subtle background highlights

# 연구자들이 자주쓰는 html 항목들.
1. 정적 시각화 — SVG figure(논문용 벡터 그림), flowchart(순서도), 다이어그램(박스-화살표 구조도)
2. 데이터 표현 — 인터랙티브 차트(hover/줌), 비교 테이블, 히트맵/colormap
3. 탐색형 UI — 사이드바+본문 익스플로러(클릭 전환), 탭 레이아웃(탭으로 구획 전환), 접기/펼치기(collapsible 섹션)
4. 시간/단계 표현 — 타임라인 애니메이션(재생 버튼), 단계별 슬라이더(슬라이더 움직이면 값/그림 변화)
5. 발표/문서 — 슬라이드 덱(스크롤로 아래로 넘김 or 화살표로 넘김), 인터랙티브 리포트