# rules/

상황별(파일 경로별) 조건부 규칙을 두는 곳. CLAUDE.md는 매 세션 항상 로드되지만,
여기 규칙은 **필요할 때만** 로드된다.

- `paths:` frontmatter **없으면** → 세션 시작 시 항상 로드 (CLAUDE.md와 동일)
- `paths:` frontmatter **있으면** → 매칭되는 파일이 context에 들어올 때만 로드

규칙은 Claude가 "읽고 따르는 가이드"이지 강제(enforce)는 아니다.
반드시 강제해야 하는 건 hooks/permissions(settings.json)로.

## 예시 (아직 안 만듦, 작업하다 필요하면 추가)

```markdown
---
paths:
  - "**/4_contents/*.md"
---

# 초안 작성 규칙
- 한국어 먼저 → 영어 번역
- 모든 주장은 figure / data / citation으로 추적 가능해야
```
