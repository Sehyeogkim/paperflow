---
name: figure-flow
description: Workflow step 2. Plan the figure flow — list each figure/table and the SINGLE message it conveys (text only, no real figures). Use after the core message is locked. Writes <paper>/2_figure_flow.md.
argument-hint: "[paper dir, e.g. master_thesis]"
---

# /figure-flow — Step 2: figure flow (one message per figure)

Papers are built around figures. Lock the figure narrative before any prose. **No real figures here** — only the flow and each figure's one-line message.

## 1. Find the paper directory & read context
- Resolve the paper dir ($ARGUMENTS or ask).
- Read `1_coremessage.md` (the claim everything serves) and `0_journal_info.md` (figure norms/limits).
- If `2_figure_flow.md` already has content → refine mode.

## 2. ▶ Ask first (in Korean)
- 핵심 메시지를 뒷받침하려면 **어떤 결과/구성요소**를 보여줘야 하나? (Method 흐름 + Result 핵심)
- 각 figure가 전달할 **단 하나의 메시지**는? ("라벨"이 아니라 "독자가 이 그림에서 가져갈 한 문장")
- 각 항목이 **data plot**인가 **개념도(schematic)**인가? (아래 규칙 적용)

## 3. Rules
- **One figure = one message.** 메시지가 둘이면 패널로 쪼개거나 figure를 분리.
- **data plot**(정량 그래프) → 실제 데이터/플로팅 도구 경로 (NOT 생성형). **schematic/개념도** → `figure-schematic` 에이전트로 HTML/SVG 가능.
- 변수·범위가 많으면 figure 대신 **Table**로.
- **번호를 연속**으로 (누락·중복 금지). 배치 섹션(Method/Result/Discussion) 표기.

## 4. Save
Write `<paper>/2_figure_flow.md`: 섹션별로 `Fig N — 제목` + `message:` 한 줄. (Table도 동일 형식.)

## 5. Gate → next
모든 figure에 "한 메시지"가 달렸고 번호가 깔끔하면 → 다음은 **`/outline` (step 3)**.
Respond in Korean; keep technical terms in original language.
