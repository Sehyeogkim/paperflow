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
    0. Core message      (1 sentence + 1 paragraph: the ONE thing the paper proves) [mandatory]
    1. Target journal + field  → save style guide to writing_style/
    2. Figure flow       (each figure + the one message it conveys)
    3. Paragraph skeleton (one sentence = one paragraph's claim, whole paper)
    4. Full outline      (Intro → Conclusion)
    5. Draft Method + Result first
    6. Draft Intro + Discussion
    7. Draft Abstract + Title last
        (write in Korean → translate to English)