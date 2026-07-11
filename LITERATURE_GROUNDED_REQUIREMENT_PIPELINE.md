# PaperFlow — Literature-Grounded Requirement Derivation

## 0. 목적

현재 PaperFlow의 질문 생성은 다음 구조다.

```text
사용자 입력
→ 고정 `computational_biomechanics.yaml`
→ 입력에 있는 항목 / 없는 항목 판별
→ 누락 질문 생성
```

이 방식은 빠른 scaffold로는 유용하지만, PaperFlow가 주장하려는 핵심 기술과 다르다.

PaperFlow가 실제로 구현해야 하는 구조는 다음과 같다.

```text
사용자 연구 입력
→ 연구 분야와 study archetype 추론
→ 유사 문헌 10–20편 검색
→ 각 문헌에서 보고된 세부 항목을 자유롭게 추출
→ 동의어·유사 개념 통합
→ 프로젝트 전용 overall schema 생성
→ 사용자 입력으로 채울 수 있는 항목 판별
→ 채울 수 없는 항목에 대해 질문 생성
```

핵심 목표는 **고정 체크리스트를 적용하는 것**이 아니라,

> 유사 연구와 사용자의 claim에서 이번 논문에 필요한 정보 구조를 먼저 구성하고, 그 구조와 사용자 입력의 차이를 질문으로 변환하는 것

이다.

---

# 1. 변경 후 전체 흐름

```text
1. Universal schema 준비
2. User research state 구성
3. Literature search query 생성
4. OpenAlex에서 관련 논문 후보 검색
5. 10–20편 선정
6. 각 논문의 가능한 원문/초록 확보
7. 논문별 open-ended item extraction
8. 추출 항목 normalization / clustering
9. overall_schema.json 생성
10. overall schema와 user input 비교
11. missing keys를 질문으로 변환
12. 사용자 답변을 final research state와 logic graph에 반영
```

---

# 2. Universal schema

전 연구 분야에 공통인 상위 구조만 고정한다.

```json
{
  "objective": [],
  "study_design": [],
  "data_or_sample": [],
  "methods": [],
  "models_and_equations": [],
  "numerical_or_experimental_settings": [],
  "validation": [],
  "outcomes": [],
  "results": [],
  "statistical_analysis": [],
  "limitations": [],
  "figures_and_tables": [],
  "reported_items": []
}
```

고정하는 것은 상위 관점뿐이다.

분야별 세부 key는 미리 전부 정의하지 않는다.

예:

```text
mesh independence
constitutive material model
patient inclusion criteria
ablation study
augmentation strategy
primary endpoint
```

이런 항목은 유사 문헌에서 동적으로 추출한다.

---

# 3. 문헌 검색

## 3.1 검색 입력

검색 query는 다음을 사용해 생성한다.

- 연구 분야
- core message
- objective
- study design
- 주요 methods
- 주요 outcomes
- target journal
- 사용자가 업로드한 reference title / DOI

## 3.2 검색 방식

OpenAlex를 1차 discovery layer로 사용한다.

```text
Research State
→ 4–8개 검색 query 생성
→ OpenAlex 검색
→ 중복 제거
→ relevance 기준 후보 20–30편
→ 최종 10–20편 선택
```

선정 시 단순 relevance 상위만 고르지 않는다.

권장 구성:

- 가장 유사한 연구: 5–8편
- 목표 저널의 유사 논문: 2–4편
- 대표 method / validation 논문: 2–4편
- 최신 연구: 2–4편

## 3.3 문헌 content level

각 논문은 반드시 content 수준을 기록한다.

```json
{
  "paper_id": "doi:...",
  "content_level": "full_text | partial_text | abstract_only",
  "source": "user_pdf | repository | open_access_url | exa | openalex",
  "title": "",
  "doi": "",
  "year": 2025
}
```

세부 Method requirement는 `full_text` 또는 `partial_text`에서만 강하게 추출한다.

`abstract_only` 논문은 다음 용도로 제한한다.

- 관련성 판정
- 연구 목적
- study type
- 주요 outcome
- 주요 conclusion

Abstract만으로 mesh, solver, convergence, boundary condition 등 세부 설정을 추출했다고 주장하지 않는다.

---

# 4. 논문별 자유 추출

## 4.1 핵심 원칙

각 논문마다 새로운 완전한 schema를 만드는 것이 아니다.

상위 category는 고정하고, 세부 항목 이름은 자유롭게 추출한다.

## 4.2 출력 schema

각 논문에 대해 다음 JSON을 생성한다.

```json
{
  "paper_id": "doi:...",
  "study_archetype": "",
  "content_level": "full_text",
  "reported_items": [
    {
      "raw_name": "hyperelastic constitutive formulation",
      "category": "methods",
      "sub_category": "physical_or_mathematical_model",
      "description": "Mooney–Rivlin model was used for the vessel wall",
      "section": "Methods",
      "evidence_text": "short supporting passage or extracted statement",
      "importance_to_main_claim": "high | medium | low | unknown",
      "explicitly_reported": true,
      "applies_to": ["finite_element_simulation"],
      "source_location": "Methods > Material model"
    }
  ]
}
```

## 4.3 추출 관점

LLM은 다음 관점으로 논문을 읽는다.

- 연구 목적
- 연구 설계
- 데이터 / 표본 / geometry
- 사용한 model
- equation
- algorithm
- solver
- material or constitutive law
- boundary / initial conditions
- numerical settings
- experimental settings
- validation
- convergence / independence test
- statistical analysis
- outcome metric
- comparison / baseline
- main result
- limitation
- figure / table 구성

## 4.4 자유 추출의 제한

다음은 금지한다.

- 문헌에 없는 항목을 관행으로 추정하여 추가
- abstract-only 논문에서 세부 method를 단정
- 한 논문의 독특한 구현 세부를 바로 universal requirement로 승격
- `used in paper`와 `required for user paper`를 동일시

---

# 5. Concept normalization

## 5.1 목적

논문마다 다른 표현을 동일 개념으로 통합한다.

예:

```text
mesh convergence study
mesh independence analysis
grid independence test
mesh sensitivity analysis
→ mesh_independence
```

```text
constitutive material model
hyperelastic constitutive law
material formulation
→ material_constitutive_model
```

## 5.2 clustering 출력

```json
{
  "canonical_key": "mesh_independence",
  "aliases": [
    "mesh convergence study",
    "grid independence test",
    "mesh sensitivity analysis"
  ],
  "category": "validation",
  "applicable_to": [
    "quantitative_numerical_simulation",
    "peak_field_value_claim"
  ],
  "source_items": [
    "paper_01:item_04",
    "paper_03:item_07",
    "paper_08:item_02"
  ]
}
```

## 5.3 normalization 규칙

- 동일 의미의 alias를 합친다.
- 너무 좁은 implementation detail은 상위 개념으로 병합한다.
- 서로 다른 개념은 억지로 합치지 않는다.
- 각 canonical key에 source item을 유지한다.
- LLM 결과는 Pydantic schema로 검증한다.

---

# 6. overall_schema.json

## 6.1 역할

`overall_schema.json`은 해당 프로젝트에 필요한 정보 구조다.

고정 YAML의 대체물이지만, 프로젝트별로 새로 생성된다.

## 6.2 권장 구조

```json
{
  "project_id": "coronary_plaque_demo",
  "study_archetype": "computational plaque biomechanics sensitivity study",
  "source_papers": 15,
  "requirements": [
    {
      "key": "mesh_independence",
      "category": "validation",
      "aliases": [
        "mesh convergence",
        "grid independence",
        "mesh sensitivity"
      ],
      "observed_in": 8,
      "applicable_papers": 11,
      "prevalence": 0.73,
      "applicability": {
        "required_when": [
          "peak_stress_claim",
          "quantitative_field_comparison"
        ],
        "not_applicable_when": [
          "pure_experimental_study"
        ]
      },
      "requirement_level": "strongly_expected",
      "reason": "The primary quantitative outcome is mesh-sensitive.",
      "evidence_sources": [
        "paper_01",
        "paper_03",
        "paper_08"
      ],
      "content_support": {
        "full_text": 6,
        "partial_text": 2,
        "abstract_only": 0
      }
    }
  ]
}
```

## 6.3 requirement level

각 key는 다음 중 하나로 분류한다.

### mandatory

- 저널 guideline 또는 reporting standard가 명시적으로 요구
- claim을 성립시키는 데 논리적으로 필수

### strongly_expected

- 유사하고 적용 가능한 논문의 다수가 보고
- reviewer가 요구할 가능성이 높음
- 해당 claim의 신뢰성에 직접 영향

### common

- 자주 보고되지만 이번 연구의 핵심 claim에 필수는 아님

### optional

- 특정 구현 또는 특정 연구 설계에서만 사용

### unsupported

- 근거가 약하거나 abstract-only 추론에 의존
- 사용자 질문 생성에는 사용하지 않음

## 6.4 prevalence 계산

전체 논문 수를 무조건 분모로 사용하지 않는다.

```text
prevalence = observed_in / applicable_papers
```

예:

- simulation paper 11편 중 8편에서 mesh independence 보고
- 전체 15편 중 8편으로 계산하지 않음

---

# 7. 요구사항 결합 규칙

최종 requirement는 다음 네 근거를 결합한다.

```text
Universal base requirements
+ Literature-derived requirements
+ Claim-triggered requirements
+ Target-journal / reporting-standard requirements
```

## 7.1 Universal base requirements

항상 필요한 최소 항목:

- research objective
- study subject / data / sample
- primary method
- primary outcome
- main result
- limitation boundary

## 7.2 Literature-derived requirements

유사 문헌의 공통 보고 관행에서 도출한다.

## 7.3 Claim-triggered requirements

사용자 claim에 따라 추가한다.

예:

```text
"peak stress increased"
→ stress definition
→ mesh independence
→ comparison condition

"the model is accurate"
→ validation dataset
→ validation metric
→ baseline

"A is more important than B"
→ sensitivity / statistical comparison
→ uncertainty or robustness
```

## 7.4 Journal / standard requirements

- target journal author guideline
- reporting checklist
- domain standard

이 근거는 literature frequency보다 높은 우선순위를 가질 수 있다.

---

# 8. 사용자 입력과 비교

## 8.1 입력 source

다음 전체를 비교 대상으로 사용한다.

- journal info
- core message
- normalized outline
- research plan / related documents
- uploaded references
- data files
- Evidence Inventory
- Research State
- existing answers

## 8.2 requirement status

각 key는 다음 상태로 판정한다.

```text
present
partial
missing
not_applicable
uncertain
```

권장 출력:

```json
{
  "key": "mesh_independence",
  "status": "missing",
  "found_evidence": [],
  "reason": "No mesh comparison or convergence result was found in the uploaded material.",
  "source_requirements": [
    "overall_schema:mesh_independence"
  ]
}
```

---

# 9. 질문 생성

## 9.1 질문 대상

질문은 다음 조건일 때 생성한다.

- status가 `missing` 또는 `partial`
- requirement level이 `mandatory` 또는 `strongly_expected`
- 현재 연구에 applicable
- 이미 답변하지 않음

## 9.2 질문 구조

```json
{
  "id": "mesh_independence",
  "question": "주요 결과인 peak plaque stress에 대해 mesh-independence test를 수행했나요?",
  "why_asked": "Peak stress is mesh-sensitive, and 8 of 11 applicable related simulation papers reported a mesh-convergence check.",
  "expected_answer": "Compared mesh sizes, metric used, and the observed difference",
  "requirement_level": "strongly_expected",
  "sources": [
    "paper_01",
    "paper_03",
    "paper_08"
  ],
  "allow_unknown": true
}
```

질문에는 반드시 다음을 포함한다.

- 왜 묻는지
- 어떤 답변을 원하는지
- 어떤 문헌 / guideline에서 유도됐는지
- 답을 모를 수 있는 선택지

## 9.3 MVP 질문 정책

현재 MVP에서는 질문을 완전한 adaptive decision tree로 만들지 않는다.

```text
전체 requirement gap 생성
→ 우선순위 정렬
→ 작은 batch로 제공
```

사용자 답변에 따라 전체 literature pipeline을 다시 실행하지 않는다.

---

# 10. 고정 YAML의 새 역할

기존 `computational_biomechanics.yaml`은 삭제하지 않는다.

하지만 기본 runtime의 primary source로 사용하지 않는다.

새 역할:

- literature search 실패 시 fallback
- universal base checklist 보완
- 테스트 fixture
- 생성된 overall schema와 비교하는 sanity check

정상 경로:

```text
Literature-derived overall schema
```

fallback 경로:

```text
Static pack
```

결과에는 어떤 경로를 사용했는지 기록한다.

```json
{
  "requirement_source": "literature_derived | static_fallback | hybrid"
}
```

---

# 11. 코드 구조 제안

```text
engine/src/paperflow/requirement/
  universal.py
  literature_search.py
  content_retrieval.py
  paper_extract.py
  normalize_items.py
  synthesize_schema.py
  compare_user_state.py
  generate_questions.py
  fallback.py

engine/src/paperflow/schemas/
  literature_paper.py
  paper_extraction.py
  overall_schema.py
  requirement_status.py

engine/src/paperflow/prompts/
  derive_search_queries.txt
  extract_reported_items.txt
  normalize_reported_items.txt
  synthesize_overall_schema.txt
  compare_requirement_to_user.txt
  generate_grounded_questions.txt
```

## 권장 산출물

```text
main/literature/
  search_queries.json
  selected_papers.json
  paper_001.json
  paper_002.json
  ...
  normalized_items.json
  overall_schema.json
  requirement_status.json
  grounded_questions.json
```

---

# 12. 서버 workflow 변경

현재:

```text
POST /api/projects/diagnose
→ ingest
→ static pack detect
→ questions
```

변경:

```text
POST /api/projects/diagnose
→ ingest
→ reconstruct Research State
→ search/select papers
→ retrieve available content
→ per-paper extraction
→ normalize concepts
→ synthesize overall schema
→ compare user input
→ generate grounded questions
```

진행 상태를 SSE 또는 기존 workflow rail에 표시한다.

```text
STEP 1 · 연구 분야 분석
STEP 2 · 관련 문헌 검색
STEP 3 · 문헌 내용 분석
STEP 4 · 프로젝트 schema 생성
STEP 5 · 사용자 입력 비교
STEP 6 · 질문 생성
```

---

# 13. MVP 현실 범위

## 반드시 구현

- OpenAlex로 관련 논문 후보 검색
- 최종 10–20편 선택
- title / abstract 기반 extraction
- 사용자가 올린 PDF 또는 접근 가능한 full text가 있으면 우선 사용
- 논문별 JSON 생성
- 자유 항목 추출
- alias normalization
- overall schema 생성
- 사용자 입력과 비교
- source가 붙은 질문 생성
- static YAML fallback

## 시간이 부족하면 축소 가능

- Exa 연동은 adapter interface만 만들고 실제 호출은 optional
- full text가 없는 논문은 abstract-only로 표시
- target journal guideline은 기존 cache 사용
- normalization은 한 번의 reasoning call로 구현

## 이번 MVP에서 하지 않음

- paywall 우회
- 모든 논문의 완전한 full-text 확보
- 완전한 domain ontology 구축
- 질문 답변 후 literature pipeline 전체 재실행
- requirement frequency의 통계적 신뢰구간
- reviewer behavior prediction

---

# 14. 정직한 제품 표현

MVP에서 가능한 주장:

> PaperFlow identifies related studies, extracts commonly reported methodological and evidentiary items, and compares them with the user's materials to generate grounded clarification questions.

MVP에서 하면 안 되는 주장:

> PaperFlow perfectly knows everything required in every research field.

또는:

> Every generated question is definitively required by the target journal.

질문의 의미는 다음으로 표현한다.

```text
mandatory
strongly expected
common practice
optional
```

---

# 15. Acceptance criteria

## Literature discovery

- [ ] 사용자 입력으로 검색 query가 생성된다.
- [ ] OpenAlex에서 관련 논문 후보가 검색된다.
- [ ] 중복 제거 후 10–20편이 선택된다.
- [ ] 각 논문의 DOI, title, abstract, content level이 기록된다.

## Per-paper extraction

- [ ] 각 논문별 JSON이 생성된다.
- [ ] 상위 category는 고정되고 세부 item은 자유롭게 추출된다.
- [ ] 각 item에 source paper와 evidence location이 남는다.
- [ ] abstract-only 논문은 세부 Method 추론에 제한이 적용된다.

## Schema synthesis

- [ ] alias / synonym이 canonical key로 통합된다.
- [ ] `overall_schema.json`이 생성된다.
- [ ] observed count와 applicable count가 분리된다.
- [ ] 각 key에 applicability와 requirement level이 존재한다.
- [ ] 각 key에 source papers가 존재한다.

## User comparison

- [ ] 각 key가 present / partial / missing / not_applicable / uncertain으로 분류된다.
- [ ] 사용자 input source가 추적된다.
- [ ] missing 판단에 근거가 남는다.

## Questions

- [ ] mandatory 또는 strongly expected missing item만 우선 질문된다.
- [ ] 질문에 why_asked가 포함된다.
- [ ] 질문에 source paper 또는 guideline이 연결된다.
- [ ] 기존 batch question UI에서 표시된다.
- [ ] static YAML은 fallback으로만 사용된다.

## Regression

- [ ] 기존 demo project가 실행된다.
- [ ] OpenAlex 실패 시 static fallback으로 질문이 생성된다.
- [ ] 기존 answer 저장과 manuscript generation이 깨지지 않는다.

---

# 16. 구현 우선순위

```text
P0-1. Per-paper extraction schema
P0-2. OpenAlex search + paper selection
P0-3. paper_*.json 생성
P0-4. normalization / clustering
P0-5. overall_schema.json 생성
P0-6. user-state comparison
P0-7. grounded question generation
P0-8. /diagnose 연결
P0-9. static fallback
P0-10. derivation HTML 수정
```

현재 `diagnose_question_derivation.html`도 수정해야 한다.

기존처럼:

```text
user input → fixed YAML → questions
```

를 보여주면 안 된다.

새 보고서는 다음을 보여줘야 한다.

```text
user input
→ generated search queries
→ selected related papers
→ per-paper extracted items
→ normalized concepts
→ overall schema
→ user input coverage
→ generated questions
```

각 질문을 클릭하면 다음이 보여야 한다.

- source papers
- extracted evidence
- canonical requirement key
- applicability reason
- user input에서 찾지 못한 이유

---

# 17. 최종 결정

PaperFlow의 질문 엔진은 다음으로 정의한다.

> A literature-grounded requirement derivation engine that constructs a project-specific schema from related studies and asks only for high-value information missing from the user's research materials.

고정 YAML은 중심 엔진이 아니라 fallback이다.
