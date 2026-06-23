# paperflow — Agent-mode 자율 생성 workflow & 결정 문서 (2026-06-22)

> 목적: Agent mode(입력 3개 → 완성 논문 자동 생성) 파이프라인의 작업순서 + 미결 결정.
> 입력 계약: `main/0_journal_info.md`, `main/1_coremessage.md`, `main/3_outline.md` (+ 선택 `data/`).
> 출력: 완성 논문(본문 섹션 + figures + references.bib). 검증셋 = `projects/master_thesis/` 실제 논문(answer key).

---

## ★ 아키텍처 보정 (제일 중요)

모델을 고객에게 안 보이고 **GPT/Gemini/DeepSeek 자유 라우팅** → **Claude Agent SDK ❌**(Claude 전용).
0→6은 **자율 agent가 아니라 결정적 workflow(고정 순서)** → 무거운 agent 프레임워크 불필요.
**각 step = "최저비용 provider 골라 LLM 호출 + 파일 read/write"하는 코드 파이프라인.** (figure AI = 이 패턴 선례)
→ 모든 호출을 우리가 통제 = 토큰 효율화 최적.

---

## 작업순서 (Agent mode · 0 → 6)

### 0. 선행연구조사
비슷한 연구 조사 → `.md`. **web scraping ❌ → 학술 API ✅**: OpenAlex(무료·키불필요·2.5억논문, 1순위) / Semantic Scholar(무료·키) / Crossref(DOI 검증).

### 1. 최소 정보 질의
outline에 빠진 필수 정보를 reasoning model이 유저에게 질문 (예: "mesh independence test 하셨나요?").
**단일 system prompt = 커버리지 불안정 → 섹션별 required-info 스키마(체크리스트)로 boundary 고정.**
예: `Method.required = [mesh_independence, boundary_condition, solver_settings, material_model, validation_against, sample_size]`
→ 모델은 outline↔스키마 대조 후 빠진 것만 질문(문구만 LLM). 결정적.

### 2. Figure 결정 (제작 전 설계)
저널 figure 개수 제한 fetch(journal_info) → 어떤 figure를 몇 패널·각 패널 어떤 정보로. 제작 X, 설계만.

### 3. 본문 작성 (Method → Result → Discussion → Intro/Conclusion/Abstract)
LLM 글쓰기 논리흐름 부족 보완 = **3중 보강**:
1) outline skeleton(문단당 1주장)으로 프로즈 전 논리 고정
2) grounding(모든 주장→data/figure/cite 추적)으로 hand-waving 차단
3) **logic-agent**(write → "각 문단 주장이 앞에서 따라오나+근거 있나" 긴 system prompt 체크 → revise)
citation은 초기 `\cite{what_I_need}` 또는 §0서 찾은 키로 placeholder → §4서 치환.

### 4. Citation
reference-hunter(실제 DOI 검증 인용 + 출처위치+인용문) → reference-double-checker(재검증).

### 5. Figure 생성
figure agent + image gen(nanobanana/gpt-image, **fal.ai `FAL_KEY` 사용**). 원큐 성공하도록 초상세 프롬프트.
= **figure AI 프로젝트(`/Users/jeff/project/0_figure_0614/figureai`) 재활용**: figure_state.json + 상세 프롬프트 + single-shot.

### 6. Reviewer mode
보수적 동료심사자 관점으로 전체 수정.

---

## 🧩 미결 결정 (답변 채우기)

- [ ] **D1. 파이프라인 언어** — ① Python(figure AI·데이터·학술API 친화, 추천) ② Node ③ 혼합
    - 답변:
- [ ] **D2. lit search(§0)** — OpenAlex+Semantic Scholar API(추천) / web fetch / skip(유저 reference만)
    - 답변:
- [ ] **D3. 정보 boundary(§1)** — 섹션별 required-info 스키마(추천) / 단일 system prompt / 둘 다
    - 답변:
- [ ] **D4. 모델 라우팅 맵(가설)** — 싼(DeepSeek·Gemini Flash·GPT-mini)=추출/포맷/조사, 강(GPT·Claude·Gemini Pro)=본문/logic/review. 이 매핑 OK? provider 우선순위?
    - 답변:
- [ ] **D5. figure 재활용(§5)** — figureai 모듈 import / 핵심만 포팅 / phase2로 미룸
    - 답변:
- [ ] **D6. 먼저 PoC할 step** — 제일 불확실 = §3(본문 논리흐름) or §1(정보질의). 어디부터?
    - 답변:
- [ ] **D7. 확인** — 0→6은 자율 agent 아니라 결정적 코드 파이프라인 맞지?
    - 답변:

## 🔑 토큰 (.env)
- figureai/.env.example 에 `FAL_KEY`(이미지 생성) 확인됨. gpt/gemini/deepseek 키 위치는 아직 미확인 → 알려줄 것.

## 검증
입력 3개(0,1,3)만 주고 agent가 §0~6 재생성 → `projects/master_thesis/`(실제 ch2~ch6+data+figures+reference)와 비교 = 품질·토큰 측정.
