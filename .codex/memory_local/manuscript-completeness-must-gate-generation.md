# Manuscript completeness must gate generation

On 2026-08-26, the Gemini 2.5 Flash demo produced a visually polished five-page PDF that still felt materially incomplete. The product had already classified the project as `MISSING_CRITICAL_INFORMATION` and identified ten missing reproducibility fields (geometry, governing equations, material properties, boundary conditions, numerical solver, sample definition, mesh independence, timestep independence, validation, and convergence criteria). However, the interview asked only three narrower questions, accepted demo assumptions as author answers, and allowed generation to complete.

The product requirement is therefore: `complete` must mean evidence-complete, not merely that every planned section contains prose. High-risk missing fields must block graph confirmation and document generation unless the author supplies evidence or explicitly selects a visibly labeled draft-with-gaps mode. Planned tables/figures, citations/references, and unresolved internal claim tokens must also be validated as actual manuscript artifacts before a paper is presented as complete.

Related: [[question-to-logic-graph-to-document-product-loop]], [[portable-graph-is-the-product-artifact]]
