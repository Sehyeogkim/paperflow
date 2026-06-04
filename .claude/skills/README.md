# skills/

`/이름` 으로 부르거나 Claude가 자동으로 부르는 재사용 작업 묶음.
워크플로 0→6의 각 단계가 실제 실행 가능한 명령으로 만들어져 있다.

공통 골격: ① paper dir 확인 → ② 선행 단계 산출물 읽기 → ③ **먼저 질문** →
④ 작성·수정 루프 → ⑤ 해당 .md 저장 → ⑥ gate(이 단계 충분한가?) + 다음 단계 안내.

각 스킬은 **폴더 하나** = `skills/<이름>/SKILL.md` + (선택) 템플릿·체크리스트 등 보조 파일.

## frontmatter 옵션
- `description:` — Claude가 언제 자동 호출할지 판단하는 기준
- `disable-model-invocation: true` — 사용자만 호출 (Claude 자동호출 금지)
- `user-invocable: false` — `/` 메뉴에서 숨김 (Claude만 호출)
- `argument-hint:` — 인자 힌트. 본문에서 `$ARGUMENTS`, `$0`, `$1`로 사용

## 단계별 skill (구축 완료)
- `/journal-setup`          — step 0: 제목·분야·타깃 저널 + 저널 스타일 fetch
- `/core-message`           — step 1: 핵심 메시지(한 문장+한 문단) 끌어내기
- `/figure-flow`            — step 2: figure별 "한 메시지" 흐름
- `/outline`                — step 3: (A)skeleton 논리점검 → (B)구조 확장
- `/draft-method-result`    — step 4: Method·Result 초안 (근거 기반)
- `/draft-intro-discussion` — step 5: Intro·Discussion 초안 (결과 확정 후)
- `/abstract-title`         — step 6: Abstract·Title 최종

## 유틸리티 skill
- `/ssh <harvey|ws1|ws2> [command]` — 등록 서버에 SSH 키로 원샷 명령 실행/복사
  (주 용도: HPC에서 결과 수치(Sobol·R²·파열위치%)를 가져와 초안의 `[TODO]` 채우기)

(전부 세션 재시작 후 `/` 메뉴에 잡힘.)
