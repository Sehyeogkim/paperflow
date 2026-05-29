---
name: core-message
description: Workflow step 0. Elicit and lock the paper's ONE core message (1 sentence + 1 paragraph) before any drafting. Use at the very start of a paper, or when the author's direction feels vague / the paper has drifted. Writes the result to <paper>/0_coremessage.md.
argument-hint: "[paper dir, e.g. master_thesis]"
---

# /core-message — Step 0: lock the core message

Your job is to pull a sharp, single core message out of the author's head and record it. This is the foundation every later step (figures, skeleton, drafting) is checked against. Do NOT let the author skip ahead to writing before this exists.

## 1. Find the paper directory
- If `$ARGUMENTS` names a paper dir, use it. Otherwise infer from context, or ask which paper.
- If `<paper>/0_coremessage.md` already has content, read it and treat this as a *refine* session, not a blank start.

## 2. Interrogate (this is the real work — don't rush to write)
Ask the author, one or two at a time, in Korean. Push back when answers are vague or hedge:
- 이 연구로 **새로 알게 된/증명한 단 하나**가 뭔가? (여러 개면 → 가장 중요한 하나로 좁히게)
- 그게 **사실이 아니었다면** 무엇이 무너지나? (그게 진짜 핵심)
- 누가 이걸 신경 쓰나? (독자/분야) 그들의 기존 통념을 **어떻게 바꾸나**?
- 한 문장으로: "우리는 ___를 보임으로써 ___를 가능/반박/입증했다."

Challenge hedging ("~에 대해 연구했다", "~을 분석했다")—그건 주제(topic)지 메시지(message)가 아니다. 주장(claim)이 나올 때까지 더 캐물어라.

## 3. Distill and confirm
Draft:
- **One sentence** — the claim, specific and falsifiable (no "studied/analyzed"; use "show/demonstrate/enable").
- **One paragraph (3-5 sentences)** — the gap it fills, what was done, the key result, why it matters.

Show it to the author, get a yes / refine. Iterate until they confirm it's *the* message.

## 4. Save
Write the confirmed message to `<paper>/0_coremessage.md` in this shape:

```markdown
# Core message

## One sentence
<the single claim>

## One paragraph
<3-5 sentences: gap → what we did → key result → why it matters>

## Out of scope (optional)
<things this paper deliberately does NOT claim>
```

Then tell the author: this is now the anchor — `/brainstorm-figures` (step 2) and every later step will be checked against it. Respond in Korean; keep technical terms in their original language.
