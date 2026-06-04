---
name: outline
description: Workflow step 3. Build the outline in two phases — (A) skeleton: one claim-sentence per paragraph to catch logic gaps, then (B) expand to a structured outline (Intro->Conclusion). Use after the figure flow. Writes <paper>/3_outline.md.
argument-hint: "[paper dir, e.g. master_thesis]"
---

# /outline — Step 3: skeleton → structured outline

Two phases in `3_outline.md`. **Do NOT start Phase B until Phase A's argument flows.**

## 1. Find the paper directory & read context
- Resolve the paper dir. Read `1_coremessage.md`, `2_figure_flow.md`, `0_journal_info.md`.
- If `3_outline.md` has content → refine mode (respect existing work; reorganize, don't delete).

## 2. Phase A — Skeleton (▶ ask + draft claim sentences)
- 목표: 문단마다 **주장 한 문장**. 소제목·번호·하위항목 없이 주장만.
- ▶ 먼저 묻기: "Intro의 논리 사슬은? (위험성 → 인자 → gap/한계 → payoff → 본 연구 목표=핵심메시지)"
  각 섹션(Intro/Methods/Results/Discussion/Conclusion)을 주장 문장 시퀀스로.
- 이 문장들을 **위→아래로 이어 읽어** 논리 점프를 찾는다. 점프가 있으면 문장을 추가/수정.
  - 흔한 함정: "아무도 안 했다"(gap)만 있고 "왜 할 가치가 있나"(payoff)가 없음 → reviewer가 "so what?" 함.
  - forward reference(Methods가 Results 결과를 미리 단정 등)는 메모로 남긴다.
- **Phase A가 점프 없이 흐를 때까지 Phase B로 넘어가지 않는다.**

## 3. Phase B — Structured outline
- 검증된 skeleton을 소제목(2.1, 2.2 ...) 구조로 확장. Intro → Conclusion.
- Phase A에서 남긴 메모(예: forward reference)를 표현에서 주의.

## 4. Save
Write `<paper>/3_outline.md`: `## Phase A — Skeleton` (번호 매긴 주장 문장들 + 논리 메모) → `---` → `## Phase B — Outline` (구조).

## 5. Gate → next
skeleton 논리가 흐르고 구조가 잡히면 → 다음은 **`/draft-method-result` (step 4)**.
Respond in Korean; keep technical terms in original language.
