# paperflow — business & product purpose (2026-06-22)

## 한 줄 목적 (지금 확정된 방향)

**연구자가 최소 입력 3개만 주면, agent가 "완성된 논문 한 편"을 자동 생성하는 SaaS.**
"먼저 만들어주고, 유저가 그 위에서 수정한다"(Agent mode)가 핵심 가설.

## 입력 계약 (유저가 주는 것 — 딱 이거만)

1. `main/0_journal_info.md` — 목표 저널 / 분야 / 저자 정보 (저널 형식·figure 개수 제한의 근거)
2. `main/1_coremessage.md` — 이 논문이 증명하는 단 하나 (1문장 + 1문단)
3. `main/3_outline.md` — 아웃라인 (섹션/문단 골격, 섹션별 한 줄 메모는 있을 수도 없을 수도)

(+ 선택: `data/` 에 raw 데이터. 부족하면 파이프라인이 유저에게 추가 요청.)

## 출력 (agent가 만드는 것)

**완성된 논문 한 편** = 본문 섹션(Method→Result→Discussion→Intro/Conclusion/Abstract)
+ figures(이미지까지 생성) + `references.bib`(검증된 인용). 유저는 Copilot mode로 다듬음.

## 비즈니스

- 구독제 SaaS. 개인 연구자(대학원생) → 랩/기업 B2B 확장.
- **모델은 고객에게 안 보임** → 비용 최적화 위해 task마다 다른 provider 자유롭게 사용
  (GPT / Gemini / DeepSeek / Claude 중 task별 최저비용 모델 라우팅). 마진 = 라우팅 + 캐싱.
- 개발 단계: 토큰은 우리(.env)가 제공한다고 가정.

## 자율 생성 workflow (Agent mode · 0→6)

0. **선행연구조사** — 비슷한 연구 조사 → `.md`. (web fetch 무거우면 학술 API: OpenAlex / Semantic Scholar / Crossref)
1. **최소 정보 질의** — outline에 빠진 필수 정보를 reasoning model이 유저에게 질문
   (예: "mesh independence test 하셨나요?"). 섹션별 required-info 스키마로 boundary 고정.
2. **Figure 결정** — 저널 figure 개수 제한 fetch → 어떤 figure를 몇 패널·각 패널 어떤 정보로 (제작 전 설계).
3. **본문 작성** — Method → Result → Discussion → Intro/Conclusion/Abstract 순.
   논리 흐름 보완 = write → logic-check(긴 system prompt) → revise 루프.
   citation은 초기엔 `\cite{what_I_need}` 또는 0단계서 찾은 키로 placeholder.
4. **Citation** — reference-hunter(실제 DOI 검증 인용) → reference-double-checker(재검증).
5. **Figure 생성** — figure agent + image gen(nanobanana/gpt-image). 원큐 성공하도록 LLM이 아주 상세히 지시(figure AI 프로젝트 재활용).
6. **Reviewer mode** — 보수적 동료심사자 관점으로 전체 수정.

## 검증 셋 (이미 보유)

`projects/master_thesis/` 에 실제 완성 논문(ch2~ch6 + data + figures + reference)이 있음.
→ **입력 3개(0,1,3)만 주고 agent가 재생성 → 실제 논문과 비교**가 그대로 품질·토큰 측정 테스트.

## 미정/논의 중 (→ 별도 결정 문서)

모델 라우팅 구현(멀티프로바이더라 Claude Agent SDK ❌ → 코드 오케스트레이션 파이프라인),
언어(Python vs Node), 정보 boundary 스키마, logic-check 설계, figure 재활용 범위. 작업순서 본 파일 §0~6 기준.
