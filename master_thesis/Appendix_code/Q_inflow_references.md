# Citations for the prescribed inlet inflow waveform Q(t) — Appendix B

**Our Q(t) (file `data/input_parameter/inflow.dat`, Fig. B1(a)):** peak ≈ 81 cc/s (mL/s),
cycle-mean ≈ 20 cc/s (≈ 1.2 L/min), HR = 60 bpm (T = 1 s), **systole-dominant** shape —
single dominant peak at t/T ≈ 0.22, a small secondary peak near t/T ≈ 0.6, near-zero in
late diastole.

---

## TL;DR — paste/adapt into Appendix B

> The prescribed inlet volumetric inflow waveform Q(t) (peak ≈ 81 cc/s, cycle-mean ≈ 20 cc/s
> ≈ 1.2 L/min) is physiologically representative of a large-artery / aortic inlet. Its
> cycle-mean magnitude matches the resting mean flow measured in the **infrarenal abdominal
> aorta** in vivo (1.31 L/min ≈ 21.8 cc/s; Les et al., 2010), and its **systole-dominant**
> shape — a sharp systolic upstroke to a dominant peak followed by a small secondary
> deflection and near-zero late-diastolic flow — is the canonical large-artery (abdominal-
> aortic) pulsatile waveform (Nouh & Tafti, StatPearls; Willemet & Alastruey, 2015), of the
> kind routinely prescribed as the inlet boundary condition in cardiovascular CFD (Taylor,
> Hughes & Zarins, 1998; Olufsen et al., 2000). **Note:** because Q(t) is systole-dominant
> and ~20× larger in mean flow than a single coronary artery (which is diastole-dominant;
> Marcus et al., 1999), it is correctly interpreted as an aortic/large-artery inlet feeding
> the model, **not** as a single-coronary inflow.

> ⚠️ **Honesty on shape:** the aorta / large systemic arteries are **systole-dominant** (flow
> peaks in systole). A single **coronary** artery is **diastole-dominant** (flow peaks in
> diastole, because the vessels are compressed during systole) and ~20× smaller in mean flow.
> Our Q(t) is systole-dominant, so cite it as an **aortic / large-artery inlet**, never as a
> single-coronary inflow.

---

## Ranked references

### 1. les2010aaa — BEST magnitude match (mean) ✅
- **Citation:** Les AS, Shadden SC, Figueroa CA, Park JM, Tedesco MM, Herfkens RJ, Dalman RL,
  Taylor CA. *Quantification of hemodynamics in abdominal aortic aneurysms during rest and
  exercise using magnetic resonance imaging and computational fluid dynamics.* Annals of
  Biomedical Engineering, 38(4):1288–1313, 2010.
- **DOI:** 10.1007/s10439-010-9949-x · **PMID:** 20143263 · open-access full text PMC6203348
- **Supports:** the **cycle-mean** magnitude of Q(t). Infrarenal (IR) abdominal-aorta resting
  mean flow = **1.31 L/min ≈ 21.8 cc/s** ≈ our ~20 cc/s mean. (Supraceliac mean = 3.51 L/min.)
- **Source location:** Results — "Measured Flows and Pressures" (full text).
- **Verbatim quote:**
  > "The mean flow measured from the PC-MRI scans were 3.51 L/min (SD: 0.50; range: 2.51-4.32)
  > for SC and 1.31 L/min (SD: 0.34; range: 0.84-1.75) for IR."
- **Relation to our Q(t):** mean 20 cc/s ↔ IR mean 21.8 cc/s — places Q(t) at the
  abdominal-aortic / large-artery level. (Paper reports peak only as a Reynolds number, so no
  verbatim peak-cc/s value here.)
- **Access:** full_text · **Confidence:** high

### 2. nouh2026aorta — BEST shape match (systole-dominant, abdominal-aortic) ✅
- **Citation:** Nouh MR, Tafti D. *Doppler Abdominal Aorta Assessment, Protocols, and
  Interpretation.* StatPearls [Internet]. Treasure Island (FL): StatPearls Publishing; 2026.
- **DOI:** — (NCBI Bookshelf) · **URL:** https://www.ncbi.nlm.nih.gov/books/NBK621195/
- **Supports:** the **systole-dominant waveform shape** of Q(t).
- **Source location:** Clinical Significance — "Normal Abdominal Aorta Doppler Signature".
- **Verbatim quote:**
  > "The spectral trace above the inferior mesenteric artery branching off point displays a
  > rapid systolic upstroke, followed by a swift return to baseline, brisk yet short early
  > diastolic reverse, and low-velocity forward flow for the remainder of diastole, resulting
  > in a triphasic pattern."
- **Relation to our Q(t):** dominant systolic peak (t/T ≈ 0.22) → "rapid systolic upstroke";
  small secondary feature (~t/T ≈ 0.6) → early-diastolic deflection; near-zero late diastole →
  "low-velocity forward flow for the remainder of diastole". (Doppler *velocity* waveform —
  supports shape, not magnitude.)
- **Access:** full_text · **Confidence:** high

### 3. taylor1998aorta — canonical CFD inlet-BC practice ✅
- **Citation:** Taylor CA, Hughes TJR, Zarins CK. *Finite element modeling of three-dimensional
  pulsatile flow in the abdominal aorta: relevance to atherosclerosis.* Annals of Biomedical
  Engineering, 26(6):975–987, 1998.
- **DOI:** 10.1114/1.140 · **PMID:** 9846936
- **Supports:** that prescribing a physiologically realistic pulsatile Q(t) at a (large/
  abdominal) arterial inlet of a 3D FE model is established practice.
- **Source location:** Abstract.
- **Verbatim quote:**
  > "A comprehensive computational framework was developed, utilizing a stabilized, time
  > accurate, finite element method, to solve the equations governing blood flow in a model of
  > a normal human abdominal aorta under simulated rest, pulsatile, flow conditions."
- **Relation to our Q(t):** founding CFD reference for a rest pulsatile abdominal-aortic inlet
  waveform — the methodological precedent for our prescribed inlet BC. (Abstract gives no
  numeric peak/mean.)
- **Access:** abstract_only · **Confidence:** high (for the canonical-practice claim)

### 4. willemet2015 — secondary shape corroboration (systemic-artery, systole) ✅
- **Citation:** Willemet M, Alastruey J. *Arterial pressure and flow wave analysis using
  time-domain 1-D hemodynamics.* Annals of Biomedical Engineering, 43(1):190–206, 2015.
- **DOI:** 10.1007/s10439-014-1087-4 · **PMID:** 25138163 · full text PMC4286649
- **Supports:** systemic-artery (aorta/carotid/brachial/iliac) flow accelerates in early
  systole (systolic peak), corroborating the systole-dominance of Q(t).
- **Source location:** Results / Fig. 1 (wave-intensity analysis).
- **Verbatim quote:**
  > "The flow is accelerated by a forward compression wave (FCW) in early systole, and
  > decelerated by both a backward compression wave (BCW) in mid systole and a forward
  > expansion wave (FEW) in late systole."
- **Relation to our Q(t):** the early-systolic forward compression wave is the mechanism of our
  early-systolic peak (t/T ≈ 0.22). (Wave-intensity phrasing, not an explicit "systole- vs
  diastole-dominant" sentence — use as corroboration.)
- **Access:** full_text · **Confidence:** medium

### 5. olufsen2000 — already in store: measured ascending-aorta inlet Q(t) ✅
- **Citation:** Olufsen MS, Peskin CS, Kim WY, Pedersen EM, Nadim A, Larsen J. *Numerical
  simulation and experimental validation of blood flow in arteries with structured-tree outflow
  conditions.* Annals of Biomedical Engineering, 28(11):1281–1299, 2000.
- **DOI:** 10.1114/1.1326031 · **PMID:** 11212947
- **Supports:** a **measured ascending-aorta** volumetric inflow waveform used as a 1D/CFD inlet
  BC — systole-dominant with an early-systolic peak (cardiac period T = 1.1 s there).
- **Verbatim quote (figure caption):**
  > "The inflow is a periodic repetition of data measured in the ascending aorta (at A in Fig. 1)
  > during one period lasting 1.1 s."
- **Relation to our Q(t):** primary literature provenance for a systole-dominant aortic-root
  inlet waveform shape. (Already recorded; listed here for completeness.)
- **Access:** abstract_only / figure-caption · **Confidence:** medium-high

---

## Honesty / contrast reference (use to justify "aortic, not coronary")

### marcus1999lad — coronary is diastole-dominant and ~20× smaller ⚠️
- **Citation:** Marcus JT, Smeenk HG, Kuijer JPA, Van der Geest RJ, Heethaar RM, Van Rossum AC.
  *Flow profiles in the left anterior descending and the right coronary artery assessed by MR
  velocity quantification…* Journal of Computer Assisted Tomography, 23(4):567–576, 1999.
- **DOI:** 10.1097/00004728-199907000-00017 · **PMID:** 10433289
- **Supports:** the explicit statement that a single coronary (LAD) is **NOT** a match for Q(t).
- **Source location:** Abstract (results/conclusion).
- **Verbatim quote:**
  > "Mean flow through the cardiac cycle was 59.1+/-15.0 ml/min." …
  > "It is confirmed noninvasively with MR that the LAD shows a predominantly diastolic flow."
- **Relation to our Q(t):** LAD mean flow ≈ **59 mL/min ≈ 1 cc/s** → ~20× **smaller** than our
  ~20 cc/s mean, **and** diastole-dominant (opposite of our systole-dominant shape). Therefore
  cite Q(t) as an **aortic / large-artery inlet**, not a coronary inlet.
- **Access:** abstract_only · **Confidence:** high

---

## Magnitude sanity check (why "aortic / large-artery", not whole-aorta or coronary)

| Vessel / level                     | Resting mean flow        | Peak/shape            | vs our Q(t) (peak 81, mean 20 cc/s, systole-dom.) |
|------------------------------------|--------------------------|-----------------------|---------------------------------------------------|
| Ascending aorta (whole CO)         | ~5–6.5 L/min (~90 cc/s)  | peak ~415 cc/s, syst. | too LARGE (Q is a fraction of whole CO)            |
| **Infrarenal abdominal aorta**     | **1.31 L/min (~22 cc/s)**| systole-dom. triphasic| **MATCH (mean & shape)** — les2010aaa, nouh2026   |
| Supraceliac abdominal aorta        | 3.51 L/min (~58 cc/s)    | systole-dominant      | larger (more proximal) — les2010aaa               |
| Single coronary (LAD)              | ~0.06 L/min (~1 cc/s)    | **diastole**-dominant | ~20× too small AND wrong shape — marcus1999lad     |

**Conclusion:** our Q(t) (mean ~20 cc/s, systole-dominant) sits squarely at the **infrarenal
abdominal-aortic / large-artery** level. Cite **les2010aaa** for the mean magnitude,
**nouh2026aorta** (+ **willemet2015**, **olufsen2000**) for the systole-dominant shape, and
**taylor1998aorta** for the canonical CFD inlet-BC precedent. Use **marcus1999lad** to make the
aorta-vs-coronary distinction explicit and avoid mis-citing Q(t) as a coronary inflow.

*All quotes above were read verbatim from the cited sources on 2026-06-20. DOIs/PMIDs verified
via PubMed/PMC. Recorded in `reference/references.json` and `reference/references.bib`.*
