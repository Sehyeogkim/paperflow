so this is a template to write down the journal paper with the claude agents
## AGENT
    The workflow below is driven in the main chat with Claude. These agents
    (in .claude/agents/) help at specific moments — research, verification, critique:
    - reference-hunter        : finds real, DOI-verified citations + records exact
                                source location & verbatim quote to reference/references.json (+ .bib)
    - reference-double-checker: re-verifies that store (quote real? at location? supports claim?)
    - reviewer           : harsh peer-reviewer critique (rigor, gaps)
    - advisor            : PI/advisor view (contribution, story, "so what?")
    - data-analyzer      : verifies your analysis vs. data/ ; flags errors/gaps
    - figure-schematic   : builds conceptual figures as HTML/SVG (not data plots)
    - polish             : final pass — LaTeX, grammar, terminology, journal format
    (roadmap: figure-builder — understands the whole paper and makes full figures)

## Procesdure (beginner)
    0. Journal info & setup  (working title, field, ranked target journals, +optional affiliation/lab/advisor)
                             → also save #1 journal's style guide to writing_style/
    1. Core message      (1 sentence + 1 paragraph: the ONE thing the paper proves) [mandatory]
    2. Figure flow       (each figure + the one message it conveys)
    3. Outline           (A: one claim-sentence per paragraph = logic check → B: structured outline, Intro→Conclusion)
    4. Draft Method + Result first
    5. Draft Intro + Discussion
    6. Draft Abstract + Title last
        (write in Korean → translate to English)

    Quick start: open master_thesis/0_journal_info.md and fill it in, then tell Claude `/core-message`.