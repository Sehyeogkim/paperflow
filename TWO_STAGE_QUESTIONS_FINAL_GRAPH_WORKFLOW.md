# PaperFlow — Two-Stage Questions → Final Logic Graph → Direct Manuscript Generation

## 0. Status and precedence

This document defines the new canonical PaperFlow MVP workflow.

Where this document conflicts with older descriptions in:

- `workflow_design.md`
- `MVP_2026-06-28.md`
- existing `/diagnose → /plan → /generate` UI behavior
- preliminary adaptive-question experiments

this document takes precedence.

The literature-derived requirement workflow is defined separately in:

- `LITERATURE_GROUNDED_REQUIREMENT_PIPELINE.md`

The present document connects that workflow to Logic Graph construction and manuscript generation.

---

# 1. Product decision

The default MVP experience is:

```text
User input
→ literature-grounded overall schema
→ first missing-information questions
→ user answers
→ preliminary Logic Graph
→ graph-gap validation
→ second questions only when load-bearing graph gaps remain
→ final Logic Graph
→ immediate manuscript generation
→ manuscript preview and DOCX/PDF output
```

The system may ask at most **two question rounds**:

1. **Requirement questions**: collect missing study facts identified from the project-specific `overall_schema.json`.
2. **Logic questions**: collect only information needed to complete load-bearing Claim–Evidence–Data–Method relationships.

There is no mandatory plan-confirmation screen in the default path.

Logic Graph, section structure, figure plan, and section contracts are still generated, but they are internal compilation artifacts rather than an additional mandatory user gate.

---

# 2. Why two stages are necessary

A literature-derived schema can determine whether expected information exists, for example:

- constitutive material model
- boundary conditions
- mesh-independence test
- validation method
- primary outcome
- statistical comparison

However, the presence of those fields does not guarantee a complete scientific argument.

A manuscript also requires explicit relationships:

```text
Method
→ produces Data / Evidence
→ supports Claim
→ contributes to Main Contribution
```

Example:

```text
Known facts:
- Sobol sensitivity analysis was used.
- Morphological variables had the highest sensitivity.
- 500 simulation cases were analyzed.

Still unclear:
- Which exact metric supports "highest sensitivity"?
- Which data file or columns contain that result?
- What comparison establishes dominance?
- What is the valid scope of the conclusion?
```

Therefore:

- Stage 1 fills missing **research facts**.
- Stage 2 fills missing **logical relationships**.

---

# 3. Canonical end-to-end state machine

```text
STATE A — INPUT_READY
  User inputs and uploaded files are saved.

STATE B — REQUIREMENT_ANALYSIS
  Literature search and per-paper extraction run.
  overall_schema.json is generated.
  User coverage is evaluated.

STATE C — REQUIREMENT_QUESTIONS
  First-round questions are shown.

STATE D — REQUIREMENT_ANSWERS_SAVED
  First-round answers are persisted.
  Research State is rebuilt with those answers.

STATE E — PRELIMINARY_GRAPH
  A preliminary Logic Graph is generated.
  The graph is validated for load-bearing gaps.

STATE F1 — LOGIC_QUESTIONS
  Enter only when important graph gaps remain.

STATE F2 — GRAPH_READY
  Enter immediately when no important graph gaps remain.

STATE G — LOGIC_ANSWERS_SAVED
  Second-round answers are persisted.
  Final Research State and Final Logic Graph are rebuilt.

STATE H — FINAL_GRAPH_VALIDATED
  Final graph passes structural and grounding validation,
  or unresolved items are explicitly downgraded / qualified.

STATE I — MANUSCRIPT_COMPILATION
  Internal writing plan, figures, section contracts, drafting,
  validation, citation filling, and export run automatically.

STATE J — COMPLETE
  manuscript.json, DOCX, PDF/TeX, graph, reports, and previews exist.
```

No infinite adaptive loop is allowed in the MVP.

```text
Maximum question rounds = 2
```

---

# 4. Stage 1 — literature-grounded requirement questions

## 4.1 Inputs

Stage 1 consumes:

- journal information
- core message
- normalized outline
- research plan / related documents
- uploaded data
- uploaded reference PDFs
- inferred Evidence Inventory
- initial Research State
- target-journal constraints

## 4.2 Derivation

Use the pipeline specified in `LITERATURE_GROUNDED_REQUIREMENT_PIPELINE.md`:

```text
Find 10–20 related papers
→ extract per-paper reported items
→ normalize aliases and concepts
→ generate project-specific overall_schema.json
→ compare schema against user materials
```

## 4.3 Question criteria

Generate a first-round question only when all are true:

- requirement status is `missing` or `partial`
- requirement level is `mandatory` or `strongly_expected`
- requirement is applicable to the user's study
- the user has not already answered it
- the answer could materially affect the manuscript or Logic Graph

Do not ask about `common` or `optional` items unless they block a major claim.

## 4.4 Stage-1 question schema

```json
{
  "id": "REQ_mesh_independence",
  "stage": "requirement",
  "requirement_key": "mesh_independence",
  "question": "주요 결과인 peak plaque stress에 대해 mesh-independence test를 수행했나요?",
  "why_asked": "Peak stress is mesh-sensitive and this check was reported in most applicable related simulation studies.",
  "expected_answer": "Compared mesh sizes, comparison metric, and observed difference",
  "requirement_level": "strongly_expected",
  "sources": ["paper_01", "paper_04", "paper_09"],
  "allow_unknown": true
}
```

## 4.5 Persistence

Persist separately from graph questions.

Recommended:

```text
main/answers_requirement.json
```

Alternative backward-compatible representation:

```json
{
  "requirement": {
    "mesh_independence": "..."
  },
  "logic": {}
}
```

A migration adapter may continue to expose a flattened `ProjectState.answers` view.

---

# 5. Rebuild Research State after Stage 1

This is mandatory.

The current behavior that merely appends an `AUTHOR ANSWERS` text block to an old saved `research_state.json` is not sufficient as the canonical architecture.

After first-round answers:

```text
Initial inputs
+ Evidence Inventory
+ literature-derived overall schema
+ requirement answers
→ Finalized Research State v2
```

Persist:

```text
main/research_state_v1.json       # before questions
main/research_state_v2.json       # after Stage-1 answers
main/evidence_inventory.json
```

`research_state_v2.json` should include:

```json
{
  "study_type": "",
  "research_problem": "",
  "objective": "",
  "study_design": "",
  "methods": [],
  "input_variables": [],
  "outcomes": [],
  "comparisons": [],
  "key_observations": [],
  "possible_claims": [],
  "limitations": [],
  "unknowns": [],
  "answer_provenance": [
    {
      "field": "mesh_independence",
      "source": "author_answer_requirement",
      "answer_id": "REQ_mesh_independence"
    }
  ]
}
```

Author answers are facts supplied by the author, not facts inferred from literature.

Their provenance must remain distinguishable.

---

# 6. Preliminary Logic Graph

## 6.1 Construction time

Build the Preliminary Logic Graph **after Stage-1 answers**, not before the literature-grounded question round.

```text
Research State v2
+ Evidence Inventory
+ overall_schema.json
+ related literature
→ preliminary_logic_graph.json
```

The graph builder may still use two LLM passes:

```text
Pass A — Claim skeleton
Pass B — Grounding nodes and edges
```

## 6.2 Canonical node types

Keep the current typed vocabulary:

- `claim`
- `evidence`
- `method`
- `data`
- `warrant`
- `source`
- `artifact`

## 6.3 Canonical edge types

Keep the current typed vocabulary:

- `supports`
- `produces`
- `uses`
- `derived_from`
- `part_of`
- `visualizes`
- `justifies`
- `qualifies`
- `contradicts`

## 6.4 Provenance requirements

Every non-claim factual node should carry provenance where possible.

```json
{
  "id": "E3",
  "kind": "evidence",
  "text": "Morphological variables had the highest total Sobol index.",
  "provenance": [
    {
      "type": "data_asset",
      "path": "data/sobol_results.csv",
      "columns": ["group", "ST"]
    },
    {
      "type": "author_answer",
      "answer_id": "REQ_sensitivity_result"
    }
  ],
  "confidence": 0.91
}
```

Never create a precise numerical Evidence node without a traceable data or author-answer source.

---

# 7. Graph-gap validation

After generating `preliminary_logic_graph.json`, run a dedicated deterministic + LLM-assisted graph-gap validator.

The validator should not ask whether the graph is aesthetically complete.

It should identify only **load-bearing defects** that prevent defensible writing.

## 7.1 Required checks

### Claim grounding

- Does every main Claim have at least one supporting Evidence node?
- Does every superiority, dominance, prediction, or validation Claim have an explicit comparison basis?
- Are causal Claims supported by evidence appropriate for causality, rather than association only?

### Evidence traceability

- Is each critical Evidence node connected to Data, Method, or an explicit author answer?
- Are exact values traceable to a file, result, or answer?
- Is the unit / metric clear when required?

### Method–result relationship

- Is it clear which Method generated each major result?
- Are major outcome definitions present?
- Are comparison groups or conditions explicit?

### Scope and qualification

- Does an overgeneralized Claim need a qualifier?
- Is the applicability boundary clear?
- Are known limitations represented?

### Graph integrity

- no dangling edges
- no isolated load-bearing nodes
- no invalid source/destination type pairs
- no Evidence node supporting a Claim that contradicts its wording
- no literature Source incorrectly represented as the user's experimental Evidence

## 7.2 Gap schema

```json
{
  "graph_id": "preliminary_v1",
  "load_bearing_gaps": [
    {
      "id": "GAP_C1_EVIDENCE",
      "type": "missing_evidence_to_claim",
      "severity": "high",
      "claim_ids": ["C1"],
      "related_node_ids": [],
      "description": "The main claim has no quantitative result connected to it.",
      "information_needed": "The result metric and value that support the claim",
      "can_degrade_to_qualifier": false
    }
  ],
  "non_blocking_warnings": [],
  "ready_for_finalization": false
}
```

Persist:

```text
main/graph_gap_report.json
```

---

# 8. Stage 2 — logic questions

## 8.1 Conditional execution

Stage 2 runs only when:

```text
graph_gap_report.load_bearing_gaps is not empty
```

If there are no load-bearing gaps:

```text
Preliminary Logic Graph
→ promote/rebuild as Final Logic Graph
→ manuscript generation
```

Do not show an empty or ceremonial second question page.

## 8.2 Stage-2 scope

Stage-2 questions are not another reporting checklist.

They ask only for missing relationships such as:

- Which result directly supports this Claim?
- Which data file or column contains that result?
- What metric or baseline establishes the comparison?
- Which Method generated this Evidence?
- What is the valid scope of the conclusion?
- Should the Claim be weakened if direct evidence does not exist?

## 8.3 Stage-2 question schema

```json
{
  "id": "LOGIC_GAP_C1_EVIDENCE",
  "stage": "logic",
  "gap_id": "GAP_C1_EVIDENCE",
  "claim_ids": ["C1"],
  "question": "‘Morphological factors dominate VI variation’이라는 주장을 직접 지지하는 결과값은 무엇인가요?",
  "why_asked": "The preliminary Logic Graph contains the claim but no quantitative Evidence node connected to it.",
  "expected_answer": "Metric, value/ranking, comparison target, and source file or table",
  "allow_unknown": true,
  "fallback_if_unknown": "downgrade_claim"
}
```

## 8.4 Maximum size

Only ask high-severity load-bearing gaps.

Recommended MVP limit:

```text
maximum Stage-2 questions = 5
```

Lower-severity issues become warnings or qualifiers.

## 8.5 Persistence

```text
main/answers_logic.json
```

---

# 9. Final Research State and Final Logic Graph

After Stage-2 answers, or immediately when Stage 2 is unnecessary:

```text
Research State v2
+ logic answers
+ preliminary graph
+ graph gap report
→ Final Research State
→ Final Logic Graph
```

Persist:

```text
main/research_state_final.json
main/final_logic_graph.json
main/final_graph_validation.json
```

## 9.1 Unknown answers

When the user selects "모름 / 나중에":

- never invent the missing fact
- never create an unsupported Evidence node
- weaken, qualify, or remove the affected Claim
- preserve an unresolved warning
- add a manuscript TODO only when necessary

Example:

```text
Strong claim:
"The proposed VI predicts plaque rupture."

No validation evidence available:
→ downgrade to
"The proposed VI provides a mechanically motivated vulnerability measure whose predictive performance requires external validation."
```

## 9.2 Final graph acceptance

A graph may be accepted when:

- all retained main Claims have support
- critical Evidence is traceable
- comparison Claims have metric and comparator
- unsupported Claims have been removed or qualified
- remaining gaps are explicitly non-blocking
- schema validation passes

The system should prefer a narrower defensible graph over a broad fabricated graph.

---

# 10. Direct manuscript generation

## 10.1 Default behavior

Once the Final Logic Graph is accepted:

```text
Final Logic Graph
→ internal figure plan
→ internal section structure
→ section contracts
→ section drafting
→ section validation
→ citation filling
→ manuscript.json
→ DOCX / PDF / TeX
```

This runs continuously without another mandatory user confirmation.

## 10.2 Remove the default plan gate

Current behavior:

```text
answers
→ startPlan()
→ user reviews claim graph / figures / subheadings
→ user clicks "제작 시작"
→ generate
```

New default behavior:

```text
answers
→ build/validate graph
→ optional Stage-2 questions
→ compile immediately
```

The former Plan Review UI may be retained only as:

- optional advanced mode
- debug/developer view
- post-generation inspection and revision tool

It must not be required for the normal MVP path.

## 10.3 Internal plan

An internal `_plan.json` may still be created for backward compatibility.

It should be generated automatically from `final_logic_graph.json` and immediately consumed by generation.

```text
final_logic_graph.json
→ auto_plan()
→ _plan.json
→ generate_from_plan()
```

No human confirmation flag is required in default mode.

---

# 11. Recommended API workflow

The implementation may preserve existing endpoints internally, but the external state transition should be clear.

## 11.1 Start requirement analysis

```http
POST /api/projects/requirement-analysis
```

Returns a job ID and eventually:

```json
{
  "type": "requirement_questions_ready",
  "questions": [],
  "overall_schema_path": "main/literature/overall_schema.json"
}
```

For backward compatibility, `/api/projects/diagnose` may call this new pipeline.

## 11.2 Submit Stage-1 answers

```http
POST /api/projects/answers/requirement
```

Then start:

```text
rebuild Research State v2
→ build preliminary graph
→ validate graph gaps
```

Response/job result should be one of:

```json
{
  "next": "logic_questions",
  "questions": []
}
```

or:

```json
{
  "next": "generation_started",
  "job_id": "..."
}
```

## 11.3 Submit Stage-2 answers

```http
POST /api/projects/answers/logic
```

Then:

```text
rebuild Final Research State
→ build Final Logic Graph
→ validate
→ start manuscript generation
```

## 11.4 One orchestration endpoint option

A single orchestration endpoint may be simpler:

```http
POST /api/projects/advance
```

with state-dependent behavior.

However, explicit endpoints are easier to test and debug for the MVP.

---

# 12. UI changes

## 12.1 Stage-1 screen

Title:

```text
논문 작성에 필요한 정보를 확인해주세요
```

Show:

- first-round requirement questions
- why each question is asked
- source papers / guideline evidence
- expected answer
- "모름 / 나중에"

Submit button:

```text
답변 제출 → 논리 구조 확인
```

Do not label it "계획 수립".

## 12.2 Between stages

Show progress:

```text
답변을 연구 구조에 반영하는 중
→ Claim–Evidence 관계 구성 중
→ 논리적 빈틈 검사 중
```

## 12.3 Stage-2 screen

Only show when required.

Title:

```text
논리 구조를 완성하기 위해 몇 가지만 더 확인해주세요
```

Explain that these questions concern Claim–Evidence relationships, not repeated metadata collection.

Submit button:

```text
답변 제출 → 논문 생성
```

## 12.4 No Stage 2

When no graph gaps remain, transition directly to:

```text
논리 구조가 완성되었습니다. 논문을 생성하고 있습니다.
```

## 12.5 Completion screen

Show:

- manuscript preview
- DOCX download
- PDF/TeX
- Logic Graph view
- requirement derivation report
- unresolved warnings

Logic Graph is inspectable after generation, not a mandatory pre-generation gate.

---

# 13. Code changes by area

## 13.1 Requirement pipeline

Implement according to `LITERATURE_GROUNDED_REQUIREMENT_PIPELINE.md`.

Likely modules:

```text
engine/src/paperflow/requirement/
  literature_search.py
  content_retrieval.py
  paper_extract.py
  normalize_items.py
  synthesize_schema.py
  compare_user_state.py
  generate_questions.py
```

## 13.2 Research-state rebuilding

Add explicit rebuild/finalize functions.

```text
engine/src/paperflow/reconstruct/build_state.py
```

Suggested API:

```python
reconstruct_initial(project_dir, ps) -> ResearchState
reconstruct_after_requirement_answers(project_dir, ps, overall_schema, answers) -> ResearchState
finalize_after_logic_answers(project_dir, state_v2, answers, graph_gaps) -> ResearchState
```

Do not silently reuse stale `research_state.json` after answers change.

## 13.3 Graph construction

Current:

```text
engine/src/paperflow/compile/claim_graph.py
```

Add graph phase or metadata:

```python
build_preliminary(ps, overall_schema) -> ClaimGraph
build_final(ps, preliminary_graph, logic_answers, gap_report) -> ClaimGraph
```

The same underlying prompt logic may be reused, but artifacts must be distinct.

## 13.4 Graph-gap validator

Add:

```text
engine/src/paperflow/graph/
  validate_gaps.py
  generate_logic_questions.py
```

or equivalent under `question/`.

This validator must operate on typed nodes and edges rather than only free-text unknowns.

## 13.5 Question schemas

Extend question schema with:

```text
stage
why_asked
sources
gap_id
claim_ids
fallback_if_unknown
```

## 13.6 Orchestration

Current `method_result.py` separates:

```text
plan()
generate_from_plan()
```

Add a default direct orchestration function:

```python
compile_from_final_graph(project_dir, out_dir, progress=...) -> RunManifest
```

Possible implementation:

```python
def compile_from_final_graph(...):
    auto_plan_from_final_graph(...)
    return generate_from_plan(...)
```

## 13.7 Server/UI

Current UI callback:

```javascript
saveAnswers()
await startPlan()
```

Replace with state-aware orchestration:

```javascript
saveRequirementAnswers()
await buildPreliminaryGraphAndAdvance()
```

Then either:

```javascript
renderLogicQuestions()
```

or:

```javascript
startDirectGeneration()
```

After Stage-2 answers:

```javascript
saveLogicAnswers()
await startDirectGeneration()
```

---

# 14. Artifact layout

Recommended project artifacts:

```text
main/
  research_state_v1.json
  answers_requirement.json
  research_state_v2.json
  preliminary_logic_graph.json
  graph_gap_report.json
  questions_logic.json
  answers_logic.json
  research_state_final.json
  final_logic_graph.json
  final_graph_validation.json
  _plan.json                       # internal/backward-compatible

main/literature/
  search_queries.json
  selected_papers.json
  paper_001.json
  ...
  normalized_items.json
  overall_schema.json
  requirement_status.json
  questions_requirement.json

_paperflow_out/
  manuscript.json
  manuscript_preview.html
  paper.docx
  paper.tex
  paper.pdf
  final_logic_graph.json
  requirement_derivation.html
  graph_gap_report.json
  validation_report.json
  run_manifest.json
```

---

# 15. Failure and fallback policy

## Literature search failure

Use the static requirement pack as an explicit fallback.

Record:

```json
{
  "requirement_source": "static_fallback"
}
```

## Preliminary graph build failure

Do not silently continue to confident manuscript generation.

Options:

1. retry the graph build once with a reduced prompt;
2. fall back to a deterministic minimal graph from Research State;
3. record a warning and constrain manuscript claims.

## Stage-2 unknown answers

Downgrade or qualify the affected claims.

## Final validation failure

Do not enter an infinite question loop.

After two rounds:

```text
remove unsupported claims
or
convert them to limitations / future work
```

Then generate the strongest defensible manuscript possible.

---

# 16. Acceptance criteria

> 상태 (2026-06-26). 괄호 = 검증 근거. `pytest`(litreq 제외) = 65 passed.

## Stage 1

- [x] `overall_schema.json` is generated from related literature or explicit fallback. (기존 req_pipeline + static fallback)
- [x] First-round questions come from missing/partial applicable high-value requirements. (generate_questions)
- [x] Every question includes `why_asked` and source provenance. (GroundedQuestion.why_asked/sources)
- [x] Answers are stored separately as requirement answers. (`main/answers_requirement.json`)

## State rebuilding

- [x] Research State is rebuilt after Stage-1 answers. (`reconstruct_after_requirement_answers`)
- [x] The rebuilt state records answer provenance. (`answer_provenance`; test_requirement_answer_rebuilds_state)
- [x] Stale pre-answer state is not silently reused as final state. (fresh v1→v2, source="v2")

## Preliminary graph

- [x] Preliminary Logic Graph is generated after Stage-1 answers. (`build_preliminary`; test_advance_path_*)
- [x] Typed nodes/edges retained. (claim/evidence/method/data/warrant/source/artifact)
- [x] Exact Evidence values are traceable. (untraceable numeric evidence rejected in finalize)

## Graph-gap validation

- [x] Validator checks Claim support, Evidence traceability, comparison basis, qualifiers, integrity. (`graph/validate_gaps.py`)
- [x] `graph_gap_report.json` is generated.
- [x] Only load-bearing gaps trigger Stage 2. (test_graph_gap_noncritical_warning_does_not_trigger_stage2)

## Stage 2

- [x] Stage 2 is skipped when no load-bearing gaps exist. (test_advance_path_a_no_stage2)
- [x] Logic questions reference specific claims/gaps. (test_logic_question_contains_claim_and_gap_ids)
- [x] Maximum Stage-2 question count is enforced. (MAX_STAGE2=5; test_logic_questions_capped_at_max)
- [x] Unknown answers trigger downgrade/qualification, not fabrication. (test_unknown_logic_answer_downgrades_claim)

## Final graph

- [x] Final Research State is persisted. (`research_state_final.json`)
- [x] Final Logic Graph is persisted and validated. (`final_logic_graph.json` + `final_graph_validation.json`)
- [x] Unsupported claims are removed or qualified. (finalize: downgrade/qualify/remove)

## Generation

- [x] Default flow does not require Plan Review confirmation. (UI: answers → advance; no startPlan)
- [x] Final graph automatically produces internal plan, figures, contracts, manuscript. (`auto_plan_from_final_graph`→`generate_from_plan`)
- [x] Manuscript generation starts immediately after graph readiness. (`finalize_and_compile`)
- [x] Completion screen exposes graph and reports as optional inspection. (output preview pane)

## Regression

- [x] Existing manuscript writer and exporters continue to work. (generate_from_plan unchanged)
- [x] Existing `_plan.json`-based generation reused internally. (auto_plan writes _plan.json)
- [x] Static requirement fallback works offline. (req_pipeline fallback)
- [~] Existing demo project completes end-to-end. (build() proven in earlier full gpt-5 run; new advance() live re-run not repeated to save cost — see limitations)
- [x] Tests cover both paths (no Stage-2 / Stage-2 required) + the "모름" path. (test_advance_path_a/b/c)

---

# 17. Required tests

## Unit tests

```text
test_requirement_answer_rebuilds_state

test_preliminary_graph_created_after_requirement_answers

test_graph_gap_missing_evidence_detected

test_graph_gap_missing_comparator_detected

test_graph_gap_noncritical_warning_does_not_trigger_stage2

test_logic_question_contains_claim_and_gap_ids

test_unknown_logic_answer_downgrades_claim

test_final_graph_rejects_untraceable_numeric_evidence
```

## Integration tests

### Path A — no second questions

```text
input
→ requirement questions
→ answers
→ preliminary graph complete
→ direct finalization
→ manuscript generated
```

### Path B — second questions required

```text
input
→ requirement questions
→ answers
→ preliminary graph contains missing Claim–Evidence edge
→ logic question
→ answer
→ final graph
→ manuscript generated
```

### Path C — user does not know

```text
logic question
→ "모름"
→ unsupported claim removed or qualified
→ manuscript still generated with warning
```

---

# 18. Implementation priority

```text
P0-1  Complete literature-grounded requirement questions
P0-2  Separate requirement-answer persistence
P0-3  Rebuild Research State after Stage-1 answers
P0-4  Build preliminary Logic Graph
P0-5  Implement graph-gap validator
P0-6  Generate conditional Stage-2 logic questions
P0-7  Finalize Research State and Logic Graph
P0-8  Auto-plan and generate without confirmation gate
P0-9  Update UI state machine
P0-10 Add integration tests and derivation report
```

---

# 19. Final canonical definition

PaperFlow's central workflow is:

> PaperFlow first learns the information structure expected for the user's specific study from related literature, asks for missing research facts, constructs the scientific Logic Graph, asks only for any remaining load-bearing logical connections, and then compiles the completed graph directly into a manuscript.

In compact form:

```text
Literature-grounded schema
→ requirement questions
→ preliminary Logic Graph
→ conditional logic questions
→ Final Logic Graph
→ manuscript compiler
```
