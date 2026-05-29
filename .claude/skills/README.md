# skills/

`/이름` 으로 부르거나 Claude가 자동으로 부르는 재사용 작업 묶음.
워크플로 0→7의 각 단계를 실제 실행 가능한 명령으로 만들기 좋은 자리.

각 스킬은 **폴더 하나** = `skills/<이름>/SKILL.md` + (선택) 템플릿·체크리스트 등 보조 파일.

## frontmatter 옵션
- `description:` — Claude가 언제 자동 호출할지 판단하는 기준
- `disable-model-invocation: true` — 사용자만 호출 (Claude 자동호출 금지)
- `user-invocable: false` — `/` 메뉴에서 숨김 (Claude만 호출)
- `argument-hint:` — 인자 힌트. 본문에서 `$ARGUMENTS`, `$0`, `$1`로 사용

## 만들 만한 후보 (아직 안 만듦, 작업하다 필요하면 추가)
- `/core-message`     — 0단계: 핵심 메시지 끌어내기
- `/brainstorm-figures` — 2단계: 그림 아이디어 발산 (창의성 핵심)
- `/skeleton`         — 3단계: 문단 스켈레톤
- `/draft-section`    — 5~6단계: 섹션 초안
