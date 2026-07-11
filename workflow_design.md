# PaperFlow — Research Reconstruction workflow (2026-06-26)

> 목표: 사용자의 연구 자료를 논문의 논리 구조로 복원하고, 필요한 질문을 거쳐 전체 논문 초안을 DOCX와 preview로 생성한다.

## 1. 사용자 입력

### 필수

- Journal and user information
- Core message
- Data/result files
- 각 data file의 한 줄 설명
- Research plan 또는 관련 문서
- 사용자가 가진 references

### 선택

- Outline
- 기존 draft
- writing style sample

기존 `0_journal_info.md`, `1_coremessage.md`, `3_outline.md` 형식은 legacy mode로 유지한다. 새로운 minimal-input mode에서는 업로드 자료로부터 이 상태를 내부적으로 생성한다.

---

## 2. 전체 파이프라인

```text
A. INGEST
   upload files + descriptions

B. RECONSTRUCT
   documents/data → research_state.json + evidence_inventory.json

C. LITERATURE SEARCH 1
   field reconstruction + paper/figure patterns

D. PRELIMINARY LOGIC GRAPH
   claim/evidence/data/method/reference/warrant/qualifier/artifact

E. QUESTION LOOP
   find graph gaps → rank questions → user answers → update state/graph

F. LITERATURE SEARCH 2
   claim-specific references and comparison studies

G. FINAL LOGIC GRAPH
   freeze major claims, evidence links, section roles and figure/table plan

H. MANUSCRIPT PLAN
   section → subsection → paragraph contracts

I. WRITE
   Method → Result → Discussion → Introduction → Conclusion → Abstract

J. CHECK
   numerical grounding + claim coverage + citation existence + consistency

K. EXPORT
   manuscript.json → HTML preview + DOCX
```

---

## 3. Canonical backend states

### 3.1 `research_state.json`

```json
{
  "study_type": "",
  "research_problem": "",
  "objective": "",
  "primary_message": "",
  "study_design": "",
  "methods": [],
  "datasets": [],
  "input_variables": [],
  "outcomes": [],
  "comparisons": [],
  "key_observations": [],
  "possible_claims": [],
  "limitations": [],
  "known_references": [],
  "unknowns": []
}
```

### 3.2 `evidence_inventory.json`

각 사용자 파일의 의미를 단순 path/column 수준이 아니라 연구 맥락으로 저장한다.

```json
{
  "assets": [
    {
      "path": "data/result.csv",
      "user_description": "group-level Sobol result",
      "inferred_role": "global sensitivity result",
      "unit_of_analysis": "input-variable group",
      "columns": {},
      "key_observations": [],
      "uncertainties": []
    }
  ]
}
```

### 3.3 `logic_graph.json`

Node kinds:

- `claim`
- `evidence`
- `data`
- `method`
- `reference`
- `warrant`
- `qualifier`
- `artifact`

Core relations:

```text
method      ─produces────→ data/evidence
evidence    ─derived_from→ data
evidence    ─supports────→ claim
claim       ─supports────→ claim
reference   ─justifies───→ warrant/claim
warrant     ─justifies───→ claim/method
qualifier   ─qualifies───→ claim
a rtifact   ─visualizes──→ evidence/data/method
```

각 main claim은 최소한 다음을 가져야 한다.

- claim text
- supporting evidence 또는 명시적 `[EVIDENCE_NEEDED]`
- evidence provenance
- method producing the evidence
- warrant 또는 reference
- qualifier/limitation
- section role
- artifact plan

---

## 4. Literature research design

### Pass 1 — field reconstruction

목적:

- 이 연구가 어떤 paper archetype에 속하는가
- 해당 분야에서 필수적으로 보고하는 정보가 무엇인가
- 일반적인 section logic은 무엇인가
- 어떤 Figure/Table이 통상 사용되는가

출력:

- `field_pattern.json`
- representative papers
- required-information candidates
- common figure/table patterns

### Pass 2 — claim-specific research

Preliminary logic graph의 각 claim을 기준으로 검색한다.

- background/gap reference
- method justification reference
- comparison study
- interpretation/warrant reference
- contradictory or limiting literature

출력:

- claim별 reference 후보
- DOI/OpenAlex identifier
- reference role
- 아직 검증되지 않은 citation은 명확히 표시

---

## 5. Critical-question loop

질문 수를 고정하지 않는다. 대신 질문을 다음 기준으로 정렬한다.

```text
question_value =
    impact_on_primary_claim
  + impact_on_method_correctness
  + impact_on_result_interpretation
  + reviewer_risk
  - inferability_from_existing_files
  - user_answering_cost
```

### 질문 유형

1. **Claim selection**
   - 어떤 결과가 primary finding인가
   - 어떤 표현을 contribution으로 주장할 수 있는가

2. **Data meaning**
   - 행/열/단위/표본/제외 기준
   - 파일 간 관계

3. **Method reconstruction**
   - 분석 순서
   - solver/statistics/model 설정
   - 기존 방법과 이번 연구의 contribution 구분

4. **Interpretation boundary**
   - association vs causation
   - 적용 범위
   - limitations

5. **Missing evidence**
   - claim을 뒷받침하는 실제 결과가 있는가
   - validation 또는 baseline이 있는가

### UX 원칙

- 질문은 작은 batch로 보여준다.
- 답변 후 research state와 graph를 업데이트한다.
- 이미 답변한 내용은 다시 묻지 않는다.
- 사용자는 모름/나중에 보완을 선택할 수 있다.
- unanswered question이 generation을 완전히 막지는 않는다.
- 다만 load-bearing claim이 근거 없이 남으면 warning 또는 placeholder로 출력한다.

### 종료 조건

다음이 만족되면 질문 loop를 종료한다.

- main claims가 선택됨
- 각 main claim에 evidence 또는 missing 상태가 명확함
- evidence를 생성한 method/data가 연결됨
- 핵심 수치의 의미와 단위가 파악됨
- 해석 범위와 limitation이 정의됨

---

## 6. Manuscript generation

Logic graph를 section 및 paragraph contract로 변환한다.

### 권장 생성 순서

1. Method
2. Result
3. Discussion
4. Introduction
5. Conclusion
6. Abstract

### Paragraph contract

각 문단은 다음 필드를 가진다.

```json
{
  "section": "result",
  "purpose": "show the dominant factor group",
  "claim_ids": ["C3"],
  "evidence_ids": ["E7"],
  "data_ids": ["D4"],
  "reference_ids": [],
  "qualifier_ids": ["Q2"],
  "artifact_ids": ["F4"],
  "must_not_claim": ["clinical causality"]
}
```

Writer는 prose를 자유 생성하는 것이 아니라 contract를 자연어로 compile한다.

---

## 7. Figure/Table planning

MVP에서는 실제 이미지를 생성하지 않는다.

Logic graph의 `artifact` 노드에 다음을 저장한다.

- figure/table type
- 전달할 single message
- source data
- section
- panels
- caption draft
- generation prompt

선행연구의 figure pattern은 참고하되, 그대로 복제하지 않는다.

---

## 8. Fact and grounding checks

### MVP 포함

1. Numerical grounding
   - 본문 수치가 user data 또는 user answer에 존재하는지 확인

2. Claim coverage
   - main claim이 evidence/data/reference와 연결되는지 확인

3. Citation existence
   - DOI/OpenAlex record 존재 확인

4. Internal consistency
   - 표본 수, 변수명, 주요 결과가 section 사이에서 일관되는지 확인

### 이후

- citation entailment
- statistical recomputation
- unit validation
- table-text consistency at cell level
- external reviewer agents

---

## 9. Export architecture

Word 파일 자체를 canonical state로 사용하지 않는다.

```text
manuscript.json
├─ HTML preview
├─ DOCX export
├─ optional LaTeX/PDF
└─ grounding report
```

MVP UI:

- 왼쪽: workflow/questions
- 가운데: generated files
- 오른쪽: 클릭한 manuscript의 read-only preview
- 직접 편집 기능은 제외

---

## 10. Current repository migration

현재 구현에서 재사용할 것:

- FastAPI/SSE server
- provider routing
- OpenAlex search
- typed claim graph validator
- section contracts/writer/validator
- citation-key guard
- PDF/TeX output

새로 추가할 것:

```text
engine/src/paperflow/reconstruct/
  extract_documents.py
  profile_data.py
  build_state.py

engine/src/paperflow/schemas/
  research_state.py
  evidence_inventory.py

engine/src/paperflow/question/
  rank.py
  loop.py

engine/src/paperflow/output/
  manuscript_state.py
  write_docx.py
```

수정할 것:

- `ingest/parse_inputs.py`: minimal-input mode 지원
- `requirement/detect.py`: completeness checklist → graph-gap question generation
- `server/app.py`: all-questions hard gate 제거, adaptive batch 지원
- `compile/claim_graph.py`: research state + evidence inventory 입력
- `figures/`: 이미지 생성보다 artifact planning 우선

---

## 11. MVP acceptance criteria

- 사용자가 필수 입력 4종을 업로드할 수 있다.
- 각 data file에 설명을 붙일 수 있다.
- outline이 없어도 research state와 preliminary logic graph가 만들어진다.
- graph gap에 기반한 질문이 생성된다.
- 답변을 반영해 final logic graph가 만들어진다.
- Introduction, Method, Result, Discussion, Conclusion이 생성된다.
- Figure/Table placeholder와 prompt가 생성된다.
- DOCX 파일을 다운로드할 수 있다.
- 생성 파일 클릭 시 오른쪽에서 read-only preview가 열린다.
- 주요 claim의 grounding 상태가 output report에 기록된다.
