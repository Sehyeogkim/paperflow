# PaperFlow MVP Input UX Changes — 2026-06-26

## 목적

이번 변경은 PaperFlow MVP의 입력 UX를 단순화하면서도, 백엔드에서는 기존의 section별 구조와 Logic Graph를 유지하기 위한 것이다.

확정된 변경사항은 다음 세 가지다.

1. Outline 입력을 `Quick input`과 `Structured outline` 두 방식으로 지원한다.
2. Data 설명은 필수가 아니라 선택 사항으로 두고, AI가 먼저 의미를 추론한다.
3. MVP에서는 현재의 batch형 independent-question 구조를 유지한다. 답변 후 Research State와 preliminary Logic Graph를 매번 재생성하는 완전한 adaptive loop는 이후 버전으로 미룬다.

---

# 1. Outline 입력 UX

## 1.1 사용자 선택 방식

Outline 단계에서 사용자가 다음 두 방식 중 하나를 선택할 수 있어야 한다.

```text
[ Quick input ]   [ Structured outline ]
```

### Quick input

하나의 큰 입력창에 사용자가 자유롭게 작성한다.

사용자는 다음 중 어떤 형식으로 작성해도 된다.

- 자연어 연구 설명
- 논문의 논리 흐름
- 기존 outline 붙여넣기
- GPT가 작성한 outline
- claim과 evidence 중심 메모
- Introduction / Method / Result 등이 섞인 문장

예시 placeholder:

```text
연구의 목적, 사용한 방법, 주요 결과, 논문의 논리 흐름을 자유롭게 작성하세요.
기존 outline이나 AI가 작성한 내용을 그대로 붙여넣어도 됩니다.
```

### Structured outline

다음 section별 입력창을 제공한다.

- Introduction
- Method
- Result
- Discussion
- Conclusion
- Abstract (optional)

기존 PaperFlow의 section별 outline 입력 방식을 유지한다.

---

## 1.2 공통 내부 구조

Quick input과 Structured outline은 서로 다른 backend format으로 관리하지 않는다.

둘 다 최종적으로 동일한 normalized schema로 변환되어야 한다.

```json
{
  "input_mode": "quick",
  "raw_outline": "사용자가 입력한 원문",
  "sections": {
    "introduction": [],
    "method": [],
    "result": [],
    "discussion": [],
    "conclusion": [],
    "abstract": []
  },
  "claim_candidates": [],
  "method_notes": [],
  "result_notes": [],
  "unclassified_notes": []
}
```

### Quick input 처리

```text
Quick input raw text
→ Outline Normalizer LLM
→ normalized outline schema
→ 기존 section-based pipeline에서 사용
```

### Structured outline 처리

```text
Section별 사용자 입력
→ deterministic normalization
→ 동일한 normalized outline schema
```

---

## 1.3 중요한 보존 원칙

- `raw_outline`은 항상 원문 그대로 저장한다.
- LLM이 분류하지 못한 문장은 버리지 않고 `unclassified_notes`에 저장한다.
- Quick input과 Structured outline을 전환해도 입력 내용이 유실되면 안 된다.
- 기존 `3_outline.md` 형식은 legacy mode로 계속 지원한다.
- 최종적으로 기존 writer가 읽는 section structure를 생성할 수 있어야 한다.

---

## 1.4 MVP 구현 범위

### 반드시 구현

- Quick input / Structured outline 토글
- Quick input 큰 textarea
- Structured outline section별 textarea
- 선택한 입력 mode 저장
- Quick input을 section별 schema로 normalize하는 LLM 단계
- 사용자 원문 보존
- 기존 section-based pipeline과 호환

### MVP에서 제외

- Quick input과 Structured outline 간 실시간 양방향 자동 동기화
- 사용자가 structured outline을 수정할 때마다 LLM 재실행
- drag-and-drop outline editor
- graph 기반 outline visualization

MVP에서는 사용자가 최종적으로 선택한 mode의 입력을 기준으로 normalize하면 된다.

---

# 2. Data 업로드 및 설명 UX

## 2.1 사용자 안내 문구

사용자에게 다음과 같이 안내한다.

> 분석에 사용한 데이터와 결과 파일을 가능한 한 모두 업로드해주세요.  
> PaperFlow가 파일명, 컬럼, 파일 내용, 연구계획서와의 문맥을 바탕으로 각 파일의 의미를 추론합니다.

파일 설명은 필수가 아니다.

각 파일 옆에는 다음 입력을 제공한다.

```text
파일 설명 (선택)
입력하지 않으면 PaperFlow가 자동으로 추론합니다.
```

---

## 2.2 AI-first inference

데이터 업로드 후 PaperFlow가 먼저 각 파일의 의미를 추론한다.

분석에 사용할 정보:

- 파일명
- 확장자
- CSV/XLSX column names
- row/column shape
- 일부 sample values
- sheet names
- 이미지 파일명과 metadata
- 사용자의 core message
- research plan / related documents
- outline
- 같은 프로젝트의 다른 파일

처리 흐름:

```text
모든 data/result files 업로드
→ basic profiling
→ project context와 결합
→ file role inference
→ Evidence Inventory 생성
→ 의미가 불명확한 파일을 missing-information 질문에 포함
```

---

## 2.3 데이터는 global asset으로 관리

데이터를 처음부터 다음처럼 section별 폴더나 업로드 칸에 가두지 않는다.

```text
Method data
Result data
Discussion data
```

하나의 파일이 여러 section에서 사용될 수 있기 때문이다.

예:

```text
sobol_results.csv
├─ Method: Sobol 분석 방법 설명
├─ Result: sensitivity index 제시
├─ Discussion: 중요한 변수의 의미 해석
└─ Figure: bar chart 생성
```

따라서 모든 데이터는 global evidence repository에 저장하고, section과는 many-to-many 관계로 연결한다.

권장 내부 구조:

```json
{
  "path": "data/sobol_results.csv",
  "user_description": "",
  "inferred_description": "Group-level Sobol sensitivity results",
  "inferred_role": "sensitivity_result",
  "related_sections": [
    "method",
    "result",
    "discussion"
  ],
  "artifact_usage": [
    "figure"
  ],
  "confidence": 0.91,
  "uncertainties": []
}
```

`related_sections`는 hint이며 파일의 소속을 제한하는 값이 아니다.

---

## 2.4 사용자 설명과 AI 추론의 우선순위

1. 사용자가 설명을 작성한 경우 이를 우선 source로 사용한다.
2. AI는 사용자 설명을 파일 내용과 대조해 확장할 수 있다.
3. 사용자 설명과 파일 내용이 충돌하면 질문으로 올린다.
4. 설명이 없는 경우 AI가 전부 추론한다.
5. 추론이 모호하거나 핵심 claim에 영향을 미치면 질문 리스트에 포함한다.

예시 질문:

```text
`final_v3.csv`의 역할을 명확히 파악하기 어렵습니다.
이 파일은 어떤 분석 결과이며 각 행은 무엇을 나타내나요?
```

---

## 2.5 Confidence 정책

MVP에서 정교한 calibration은 필요하지 않지만 다음 상태는 구분한다.

### High confidence

- 파일명, 컬럼, 연구문서 문맥이 일치
- 질문하지 않음
- Evidence Inventory에 추론 결과 저장

### Medium confidence

- 가장 가능성 높은 역할을 저장
- 중요도가 높으면 질문 리스트에 포함 가능

### Low confidence

- 역할을 `unknown`으로 저장
- 질문 리스트에 반드시 포함

MVP에서는 숫자 confidence 대신 다음 enum을 사용해도 된다.

```text
high / medium / low
```

---

# 3. MVP 질문 시스템 정책

## 3.1 현재 구조 유지

이번 MVP에서는 질문을 완전한 sequential adaptive tree로 변경하지 않는다.

현재 구조를 유지한다.

```text
Research State + preliminary Logic Graph
→ 전체 gap 탐지
→ 질문 후보 생성
→ 우선순위 정렬
→ 작은 batch로 사용자에게 표시
→ 답변한 질문 제거
→ 다음 batch 표시
```

질문 후보에는 다음이 포함된다.

- 연구 목적/claim 불명확성
- Method 누락
- Result 의미 누락
- validation/baseline 누락
- limitation 누락
- 데이터 파일 의미 불명확성
- 파일 간 관계 불명확성

---

## 3.2 MVP에서 하지 않는 것

현재 MVP에서는 다음을 구현하지 않는다.

```text
질문 batch
→ 사용자 답변
→ Research State 재생성
→ preliminary Logic Graph 재생성
→ 기존 질문 전체 폐기
→ 새로운 질문 tree 생성
```

즉, 답변에 따라 다음 질문의 사고 방향 자체가 달라지는 fully adaptive questioning은 이후 버전으로 미룬다.

현재 질문 시스템은 정확히 다음 성격으로 정의한다.

> Ranked independent questions delivered in small batches.

UI나 제품 설명에서 이를 완전한 adaptive reasoning으로 과장하지 않는다.

---

## 3.3 답변의 사용

사용자 답변은 `answer.json`에 누적 저장한다.

최종 plan / final Logic Graph / manuscript generation 단계에서는 다음을 함께 사용한다.

- Research State
- Evidence Inventory
- user answers
- core message
- normalized outline
- literature results

따라서 질문이 independent하게 생성되더라도, 답변은 최종 Logic Graph와 논문 작성에 반영되어야 한다.

---

# 4. 변경 후 전체 MVP 입력 흐름

```text
1. Journal and user information
2. Core message
3. Research plan / related documents / references
4. Data/result files를 가능한 한 모두 업로드
   └─ file description은 optional
5. Outline 입력 방식 선택
   ├─ Quick input
   └─ Structured outline
6. Quick input이면 Outline Normalizer LLM 실행
7. Document extraction + data profiling
8. AI가 각 data file의 의미와 역할 추론
9. Research State + Evidence Inventory 생성
10. preliminary Logic Graph 생성
11. 누락정보와 불명확한 data meaning을 질문 리스트로 생성
12. 작은 batch로 질문 표시
13. 답변 누적 저장
14. final Logic Graph 생성
15. 전체 manuscript 생성
16. DOCX export + right-side preview
```

---

# 5. UI 요구사항

## Outline section

```text
Outline format
(●) Quick input
( ) Structured outline
```

Quick input 선택 시:

```text
[ 큰 textarea ]
```

Structured outline 선택 시:

```text
Introduction [textarea]
Method       [textarea]
Result       [textarea]
Discussion   [textarea]
Conclusion   [textarea]
Abstract     [textarea, optional]
```

## Data section

```text
Upload all research data and result files

[file name]
[file description — optional]
“Leave blank and PaperFlow will infer it.”
```

데이터 업로드 위치는 하나의 global area로 유지한다.

---

# 6. Backend 변경 요구사항

## 추가 또는 수정 권장 모듈

```text
engine/src/paperflow/ingest/normalize_outline.py
engine/src/paperflow/schemas/outline_state.py
engine/src/paperflow/reconstruct/profile_data.py
engine/src/paperflow/reconstruct/build_state.py
engine/src/paperflow/schemas/evidence_inventory.py
engine/src/paperflow/question/gaps.py
engine/src/paperflow/server/app.py
engine/src/paperflow/server/static/*
```

## 필요한 처리

- UI state에 `outline_mode` 저장
- Quick input raw text 저장
- Structured outline section 값 저장
- Quick input normalization endpoint 또는 reconstruction 단계 추가
- 파일 설명 없이도 upload 가능
- 각 업로드 파일별 optional description 저장
- data profiling 시 사용자 설명과 AI inference를 함께 사용
- low-confidence data meaning을 question gap으로 변환
- 기존 legacy project가 깨지지 않도록 fallback 유지

---

# 7. Backward compatibility

기존 프로젝트는 계속 동작해야 한다.

지원해야 할 기존 형식:

```text
0_journal_info.md
1_coremessage.md
3_outline.md
data/*
```

기존 `3_outline.md`가 있으면 Structured outline으로 간주한다.

새 UI 입력이 없을 때도 기존 CLI와 demo flow가 동작해야 한다.

---

# 8. Acceptance criteria

## Outline

- [ ] 사용자가 Quick input과 Structured outline 중 하나를 선택할 수 있다.
- [ ] Quick input 원문이 저장된다.
- [ ] Quick input이 section별 normalized schema로 변환된다.
- [ ] Structured outline은 LLM 없이 동일 schema로 변환된다.
- [ ] 기존 `3_outline.md` project가 계속 동작한다.

## Data

- [ ] 사용자가 설명 없이 여러 data/result file을 업로드할 수 있다.
- [ ] 파일 설명 입력은 optional이다.
- [ ] 각 파일에 basic profile이 생성된다.
- [ ] research documents와 core message를 이용해 파일 역할을 추론한다.
- [ ] 결과가 Evidence Inventory에 저장된다.
- [ ] 의미가 불명확한 파일은 질문 후보가 된다.
- [ ] 데이터는 특정 section에 고정되지 않는다.

## Questions

- [ ] 현재의 ranked independent-question batch 방식을 유지한다.
- [ ] data meaning 질문이 기존 missing-information 질문과 함께 표시된다.
- [ ] 답변은 누적 저장된다.
- [ ] unanswered question이 generation을 hard-block하지 않는다.
- [ ] 답변은 final Logic Graph와 manuscript generation에 반영된다.

## Regression

- [ ] 기존 demo project가 실행된다.
- [ ] 기존 CLI flow가 실행된다.
- [ ] 기존 section-based outline 입력이 유지된다.
- [ ] 기존 data upload가 깨지지 않는다.

---

# 9. 이번 결정의 핵심

```text
사용자에게 형식을 강요하지 않는다.
그러나 백엔드는 항상 구조화된 outline을 가진다.

사용자에게 모든 데이터 설명을 강요하지 않는다.
그러나 AI는 모든 파일의 의미를 추론하고 불확실한 부분만 질문한다.

데이터는 section별 소속물이 아니다.
연구 전체에서 재사용되는 global evidence asset이다.

MVP 질문은 완전한 adaptive tree가 아니다.
우선순위화된 independent questions를 작은 batch로 제공한다.
```
