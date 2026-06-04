---
name: draft-intro-discussion
description: Workflow step 5. Draft the Introduction and Discussion — written once the Results' story is clear. Korean draft -> English. Use after Method/Result drafts exist. Writes into <paper>/4_contents/Intro.md and discussion.md.
argument-hint: "[paper dir, e.g. master_thesis]"
---

# /draft-intro-discussion — Step 5: draft Intro + Discussion

These are the hardest sections and must come AFTER Results, because they frame and interpret what the data showed.

## 1. Find the paper directory & read context
- Resolve the paper dir. Read `1_coremessage.md`, `3_outline.md` (esp. Phase A skeleton for the Intro logic chain),
  `2_figure_flow.md`, and the existing `4_contents/method.md` + `result.md`. Read `reference/references.json`.

## 2. ▶ Ask first (in Korean)
- Intro는 Phase A 논리 사슬(위험성→인자→한계→payoff→목표)을 그대로 따를까?
- Discussion에서 각 결과를 **핵심메시지로 어떻게 되돌릴지**? (so-what 연결)
- 완성 후 비평을 위해 `reviewer` / `advisor`를 (병렬로) 부를까?

## 3. Rules
- **Results 스토리가 확정되기 전엔 쓰지 않는다.** Intro/Discussion이 Result와 어긋나면 안 됨.
- Intro: Phase A skeleton의 논리 사슬을 산문으로. 마지막 문단 = 핵심메시지 + 기여.
- Discussion: 결과 해석 → 핵심메시지로 수렴 → 한계 → 함의. 새 결과를 여기서 만들지 않음.
- 인용 필요 → `reference-hunter`(찾고 저장) / 저장소 검증 → `reference-double-checker`.
- 완성 초안은 `reviewer`(엄밀성) + `advisor`(스토리/기여)를 **병렬**로 돌려 피드백 받기.
- 한국어 초안 → 영어 번역, `writing_style/` 용어 일관.

## 4. Save
Write `<paper>/4_contents/Intro.md`, `<paper>/4_contents/discussion.md` (구조는 `3_outline.md` Phase B).

## 5. Gate → next
Intro·Discussion이 핵심메시지와 정합하면 → 다음은 **`/abstract-title` (step 6)**.
Respond in Korean; keep citations / technical terms in original language.
