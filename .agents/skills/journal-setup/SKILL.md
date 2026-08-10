---
name: journal-setup
description: Workflow step 0. Set up the paper's basics — working title, author's field, ranked target journals (+ optional affiliation/lab/advisor) — and capture the #1 journal's writing style. Use at the very start of a paper. Writes <paper>/0_journal_info.md and writing_style/<journal>.md.
argument-hint: "[paper dir, e.g. master_thesis]"
---

# /journal-setup — Step 0: paper basics + journal style

Set the foundation: who/where this paper targets, and how that journal wants papers written. Keep it light — this is a setup form, not deep work.

## 1. Find the paper directory
- If `$ARGUMENTS` names a paper dir, use it. Otherwise infer or ask which paper.
- If `<paper>/0_journal_info.md` already has content, read it → *refine* mode.

## 2. ▶ Ask first (one or two at a time, in Korean)
- 연구 **분야(field)**는? (예: computational biomechanics)
- **타깃 저널**을 순위대로? (1순위가 기본 스타일이 됨) — 저널명 철자 정확히.
- **잠정 제목**(working title)? (최종 제목은 step 6에서 확정 — 지금은 가제로 충분)
- (선택) 소속 / 연구실 / 지도교수 / 저자 — 원하면.

## 3. Capture the #1 journal's writing style
- Try to fetch the journal's scope, article structure (IMRaD? combined Results/Discussion?), length limits,
  and tone (Guide for Authors). If you cannot access it (paywall/login), ASK the author to paste the
  "Guide for Authors" text. Never invent a journal's rules.
- Save what you learn to `<paper>/writing_style/<journal>.md` (구조·문체·길이·인용형식 등).

## 4. Save
Write `<paper>/0_journal_info.md`:
```markdown
# Journal info & setup  (workflow step 0)
## Working title
<가제>
## Author's field
<field>
## Target journals  (순위대로, 1순위 = 기본 스타일)
1. <journal>
## (optional) Extra info
- Affiliation / Lab / Advisor / Authors
```

## 5. Gate → next
저널명·분야가 정해졌고 style이 `writing_style/`에 들어갔으면 → 다음은 **`/core-message` (step 1)**.
Respond in Korean; keep journal names / technical terms in original language.
