---
name: draft-method-result
description: Workflow step 4. Draft the Method and Result sections first (they are grounded in what was actually done). Korean draft -> English. Use after the outline. Writes into <paper>/4_contents/method.md and result.md.
argument-hint: "[paper dir, e.g. master_thesis]"
---

# /draft-method-result — Step 4: draft Method + Result first

Method and Result come first because they are grounded in what was actually done — no interpretation needed yet.

## 1. Find the paper directory & read context
- Resolve the paper dir. Read `3_outline.md` (structure), `2_figure_flow.md` (what each figure shows),
  `1_coremessage.md` (the claim), and skim `data/` + `reference/`.

## 2. ▶ Ask first (in Korean)
- 어느 섹션부터? (보통 Method → Result)
- 한국어로 먼저 쓰고 영어로 번역하는 흐름 맞나?
- 각 주장/수치를 뒷받침할 **figure / data 파일**이 어디 있나? (없으면 어디서 가져오나)

## 3. Rules
- **모든 주장은 figure·data·citation으로 추적 가능**해야 한다. 근거 없는 단정 금지.
- 한국어 초안 → 영어 번역(의미·기술 뉘앙스 우선, `writing_style/` 용어 일관).
- Method: 재현 가능하게(파라미터·도구·BC·메시·통계). Result: 사실만, 해석은 Discussion으로 미룸.
- 필요 시 에이전트 호출: 데이터/수치 검증 → `data-analyzer`, 인용 필요 → `reference-hunter`.
- outline의 forward-reference 메모가 있으면 표현 주의(Methods에서 결과 단정하지 않기).

## 4. Save
Write `<paper>/4_contents/method.md`, `<paper>/4_contents/result.md` (섹션 구조는 `3_outline.md` Phase B를 따른다).

## 5. Gate → next
Result의 "스토리"가 분명해지면 → 다음은 **`/draft-intro-discussion` (step 5)**.
Respond in Korean; keep code / equations / citations / technical terms in original language.
