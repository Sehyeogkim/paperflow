# master_thesis `.tex` rebuilt from Notion (2026-06-19)

`master_thesis/20244152_sehyeog_0619.tex` was fully rewritten to mirror the Notion
"Journal final" page (Abstract → Conclusion + Appendix A/B). Korean body text is the
source of truth there. Compiles via `master_thesis/build.sh` (pdflatex → bibtex →
pdflatex ×2) → 48-page PDF, 0 undefined citations.

## Figure-page mapping is an ASSUMPTION — verify against the real figures
`figures/figure_page_01..11.pdf` were assigned **sequentially in document order**
(I could not see the images). Mapping used:
- 01 Ch2 framework · 02 Ch2 geometries · 03 Ch2 validation
- 04 Ch3 workflow · 05 Ch3 plaque geometry/morphology · 06 Ch3 BC · 07 Ch3 rupture-location-index
- 08 Ch4 input–VI correlation · 09 Ch4 Sobol · 10 Ch4 rupture location · 11 Appendix A1 calcification process
- **Appendix A2 (calcification distribution) and Appendix B1 (inlet pressure/elastance) have NO page** →
  left as `% TODO: Figure ...` comments (only 11 pages available, 13 figures needed).

## Tables: persisted vs replaced
- **Persisted from old .tex** (Notion references but doesn't reproduce them): the 3 Ch2 boundary-condition
  tables (`bc-ideal-aaa`, `bc-heart-aorta`, `bc-subject-coronary`) and the 2 Ch2 validation-result tables
  (`val-l2-error`, `val-cost`).
- **Replaced with Notion versions:** Table 3.1 input vars (now has Equation + Reference/Basis cols),
  Table 3.2 seven criteria, Table 4.1 VI compliance; **added** Table 4.2 GPR accuracy, Appendix A/B tables.

## Bibliography
Switched from inline `thebibliography` to `\bibliography{reference/references}`. `references.bib` was
extended (67→103 entries) using the Notion reference sub-pages. Alias keys in the body were remapped to
canonical bib keys (e.g. `virmani2006`→`virmani_vulnerable_plaque`, `Sankaran2012`→`sankaran2012cabg`,
`costopoulos_vh_ivus`→`costopoulos2017`, `teng_pss`→`teng2014`, `ref12/ref13`→`jang2005oct/narula2013`).
Entries with `note = {VERIFY ...}` are stubs lacking a confirmed source (e.g. `yang2021hemodynamics`,
`toth2014ffr`, `fluid_newtonian_blood`, `polzer2019`, `teng2019`, `zhao2024`, `wang2021_multipatient`,
`lissoni2025_coronary_methods`, `cilla2015`) — fill these in. See [[method-writing-cite-dont-rederive-convention]].
