# Journal Paper Template (with Claude agents)

This repo is a reusable template for writing academic journal papers with Claude(agetns).
The goal: make journal writing **creative, easy, and convenient**.

## Repo layout

The root holds shared config (this file, `readme.md`, `.claude/agents/`, `blackboard/design.md`).
**Each top-level subdirectory is ONE independent journal paper**, e.g.:

- `master_thesis/`
- `engnineering_master_thesis/`

Agents and workflow are shared across all papers; the content in each subdir is not.

## Per-paper file layout

Each paper directory follows the same numbered structure, matching the workflow steps:

```

<paper>/
  0_core_message.md     # the ONE thing the paper proves (1 sentence + 1 paragraph)
  1_target_journal.md   # ranked target journals + the author's field
  2_figure.md           # figure flow: each figure + the single message it conveys
  3_skeleton.md         # paragraph skeleton: one sentence = one paragraph's claim
  4_outline.md          # full outline, Intro -> Conclusion
  5_contents/             # the actual drafts
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

## Workflow (run in order, 0 -> 7, from the reference)

0. **Core message** — 1 sentence + 1 paragraph: the ONE thing the paper proves. [mandatory]
1. **Target journal + field** — pick ranked journals; fetch/record each journal's
   structure & tone into `writing_style/<journal>.md`. The #1 journal is the default.
2. **Figure flow** — list each figure and the single message it conveys (text only, no real figures yet).
3. **Paragraph skeleton** — one sentence per paragraph, across the whole paper.
4. **Full outline** — expand the skeleton into a structured outline, Intro -> Conclusion.
5. **Draft Method + Result first** — these are grounded in what was actually done.
6. **Draft Intro + Discussion** — written once the Results' story is clear.
7. **Draft Abstract + Title last.**

## House rules

- The author drafts in **Korean first, then translates to English.** Preserve meaning and
  technical nuance over literal translation; keep terminology consistent with `writing_style/`.
- **Figure-first, result-first.** Never write Intro/Discussion/Abstract before the figures
  and Results story are settled.
- Every claim in prose should trace back to a figure, a number in `data/`, or a citation.
- Match the target journal's structure and tone (`writing_style/<journal>.md`) — section
  order, length, and voice vary by journal.
- When unsure what the paper is trying to say, re-read `0_core_message.md` before drafting.

## Agents

The workflow (0→7) is driven in the MAIN conversation with the author. Agents are
**helpers invoked at specific moments** — mostly for research, verification, and critique.
They live in `.claude/agents/` (shared across all papers):

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
  figure pipeline. Final paper figures are planned as text in `2_figure.md` and produced by the
  author's real tooling (matplotlib/Illustrator → vector). Do not treat a blackboard HTML as a
  finished journal figure.
