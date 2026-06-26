# PaperFlow `/diagnose` 재설계 개발 로그 — fail → fix 루프

> 날짜: 2026-06-26
> 범위: 고정 YAML 기반 질문 생성 → **literature-grounded requirement derivation**으로 교체,
> 그리고 6분 14초 → 2분 25초 성능 튜닝까지.
> 목적: "왜 이 코드가 이렇게 생겼는지" — 각 결정의 **계기(fail)와 처방(fix)**을 남긴다.

관련 스펙:
- `LITERATURE_GROUNDED_REQUIREMENT_PIPELINE.md` — 문헌 기반 요구 도출
- `TWO_STAGE_QUESTIONS_FINAL_GRAPH_WORKFLOW.md` — 2단계 질문 → 논리그래프 → 즉시 생성
- 검증 프로젝트: `projects/coronary_plaque_vi_demo` (관상동맥 플라크 ΔPSS 민감도 연구)

---

## 0. 출발점 — 무엇을 왜 바꿨나

**기존 구조**

```
사용자 입력 → 고정 computational_biomechanics.yaml (10 required + 4 conditional)
→ 입력에 있냐/없냐 판정 → 누락 질문
```

빠른 scaffold로는 좋지만, PaperFlow의 핵심 주장(“유사 연구에서 이 논문에 필요한 정보 구조를 **학습**한다”)과 다르다. 고정 체크리스트는 분야가 바뀌면 못 쓴다.

**목표 구조**

```
사용자 입력 → 연구 분야·archetype 추론 → 유사 문헌 10~20편 검색
→ 논문별 보고 항목 추출 → 개념 정규화 → 프로젝트 전용 overall_schema
→ 사용자 입력과 비교 → 충족 안 된 핵심 항목만 질문 (출처 논문 연결)
```

고정 YAML은 **삭제 대상이 아니라 fallback**으로 강등.

---

## 1. 1차 구축 — literature-grounded 파이프라인

신규 모듈 (`engine/src/paperflow/requirement/`):
`literature_search` → `content_retrieval` → `paper_extract` → `normalize_items`
→ `synthesize_schema` → `compare_user_state` → `generate_questions` → `fallback` → `pipeline`(오케스트레이터)

신규 스키마: `literature.py`(LiteraturePaper/ReportedItem/PaperExtraction),
`overall_schema.py`(RequirementKey/OverallSchema), `requirement_status.py`(RequirementStatus/GroundedQuestion).

신규 프롬프트 6개 + `/api/projects/diagnose` 연결. **핵심 통합 제약**: generate 단계가
`detect.load_report()`로 `RequirementReport`를 재사용하므로, 새 파이프라인도 **호환
RequirementReport를 항상 저장**해야 기존 생성·답변 저장이 안 깨진다.

모킹 테스트 7개 작성(discovery/extraction/schema/comparison/questions/E2E/fallback). 전체 그린.

---

## 2. FAIL → FIX 루프

### FAIL #1 — 라이브 첫 실행이 조용히 static fallback으로 떨어짐
- **증상**: 질문은 9개 나왔는데 `requirement_source = static_fallback`, 모든 질문 `sources=['static_pack']`. 즉 **선행연구가 아니라 고정 YAML에서 나옴.**
- **추적**: 산출물 타임스탬프로 단계별 확인 → 검색·16편 추출까지는 정상인데 `normalized_items.json`의 **클러스터 수 = 0**. pipeline의 `if not clusters: fallback`이 발동.
- **근본 원인 (FAIL #2로 이어짐)** ↓

### FAIL #2 — normalize가 gpt-5 full로 타임아웃
- **재현**: 저장된 16편 추출본(=155개 항목)을 normalize에 그대로 넣어 호출 → **2분+ 걸려 타임아웃** → `except` → `[]` → fallback.
- **원인**: gpt-5 **full(추론 모델)**에게 155개 항목을 한 번에 클러스터링시키니 과도하게 느림. 게다가 OpenAlex 선정 16편 중 일부가 주제 무관(wetland salinization, antimicrobial peptides 등)이라 노이즈 항목까지 섞임.
- **FIX**:
  - `normalize_items`: tier **reasoning(full) → fast(mini)**. mini로 ~60~98초에 17~21 클러스터 정상 산출.
  - **tolerant ref 매칭** 추가: LLM이 `paper_1:item_1`처럼 zero-pad 안 해도 `paper_001:item_01`로 정규화 매칭 (전부 필터링돼 0클러스터 되는 것 방지).
  - **fallback 로깅**: 조용히 떨어지지 않게 `stderr` + `main/literature/_fallback.json`에 사유 기록. (이전엔 왜 fallback인지 알 수가 없었음 → 디버깅 지옥)
  - 논문 **16 → 10편** 축소 (추출 빨라지고 노이즈↓).

### 결정 — 도메인 YAML 삭제 (사용자 요청)
- 사용자: "yaml 그냥 삭제해, 백업 있음."
- **위험**: `fallback.run → detect.load_pack()`가 그 파일을 읽음 → 삭제하면 fallback 크래시 + 테스트 깨짐. 스펙은 "삭제하지 말라"지만 **사용자 지시 우선**.
- **FIX**: `detect.load_pack()`가 파일 없으면 **universal 최소 6항목**(`universal.UNIVERSAL_BASE_REQUIREMENTS`)으로 우아하게 대체. literature가 primary, universal 팩이 유일한 fallback 바닥. 크래시·테스트 깨짐 없음.

### FAIL #3 — prevalence가 죄다 1.0 (변별력 없음)
- **증상**: overall_schema의 모든 요구사항이 `prevalence=1.0`, 거의 다 `mandatory`.
- **원인**: synthesize의 gpt-5가 `applicable_papers`를 그냥 `observed_in`과 같게 반환 → `prevalence = observed_in/applicable_papers = 1.0` 고정.
- **FIX**: synthesize **출력 간단화** — LLM은 `requirement_level`·`required_when`·`reason`만 판단. `applicable_papers`는 **코드가 결정적 계산**(= 전체 선정 논문 수). 그 결과 prevalence가 `observed_in/총편수`로 **0.9~0.1 변별**. + synthesize tier도 mini.

### FAIL #4 — compare가 너무 관대 + 비결정적 (질문이 0개 나옴)
- **증상**: 어떤 런은 "14개 전부 present → 질문 0개", 어떤 런은 "3 partial → 질문 3개". **같은 입력인데 런마다 결과가 다름.**
- **결정적 증거**: 서버 로그에 diagnose 요청 2건(포트 63556, 63579)이 각각 다른 결과. answer.json은 비어 있었음(이전 답변 탓 아님).
- **원인**: compare(mini)가 **"관련 데이터 파일이 있다 = 그 방법론이 서술됐다"**로 착각. `inflow.dat`(유량 데이터)가 있다고 solver·mesh independence가 present 처리됨. mini는 미묘한 판단에 약하고 **들쭉날쭉**.
- **FIX**:
  - `compare_user_state`: tier **fast(mini) → reasoning(gpt-5 full)**. (방금 본 오판 때문에 **mini로 되돌리지 않음**.)
  - 프롬프트 **엄격화**: "데이터 파일 존재 ≠ 방법론 서술. method/setting/validation류는 식·설정값·절차가 실제로 적혀야 present. core message의 고수준 언급은 partial." 데이터 파일 경로를 present 근거로 인용 금지.
  - 결과: present 9·partial 2·missing 2처럼 **실제 빈틈을 포착**. 들쭉날쭉 사라짐.

---

## 3. 성능 — 6분 14초가 너무 길다

엄격·정확해졌지만 **첫 질문 화면까지 374초(6m14s)**. 인터랙티브 SaaS엔 과함.

**단계별 측정 (튜닝 전)**

| 단계 | 시간 | 모델 |
|------|-----:|------|
| 검색·선정 | 13s | mini + HTTP |
| 논문 추출 10편 | 94s | mini |
| normalize | 98s | mini |
| synthesize | 35s | mini |
| compare | 55s | gpt-5 full |
| questions | 82s | gpt-5 full |
| **합계** | **374s** | |

**핵심 진단**: 느린 두 단계(추출·normalize)는 **이미 mini**. → 모델만 더 낮춰선 해결 안 됨.
진짜 원인은 **7개 순차 단계 + 과한 출력 + `reasoning_effort` 미지정**.

> 결정적 코드 발견: client가 gpt-5에 `reasoning_effort`를 **안 넘김**(기본 medium) +
> `max_completion_tokens = max(.., 16000)`. → mini조차 매번 medium effort로 과하게 “생각”.
> 그리고 `max_completion_tokens`는 **상한(cap)이지 목표가 아님** — 16k를 줄여도 속도는 안 변함.
> **진짜 레버는 `reasoning_effort`.**

---

## 4. Phase 0 튜닝 (FIX)

### 0-1 — client에 `reasoning_effort` 추가 (가장 큰 레버)
- `call`/`call_json`에 `effort` 인자 추가 → gpt-5/o-series면 chat completions payload에 `reasoning_effort` 전달 (Responses API 이전 불필요, 저위험). 비-reasoning provider엔 자동 무시.
- `max_completion_tokens` floor 16000 → **8000**(reasoning 헤드룸은 두되 과하지 않게).
- 단계별 effort: extract/synthesize/queries = `minimal`, normalize = `low`, compare = `low`.
- **mini도 reasoning 모델**이라 effort=minimal이 먹혀 추출·synthesize까지 같이 빨라짐.

### 0-2 — compare + questions를 **한 호출로 병합**
- 기존: compare(상태 판정) → questions(missing/partial만 질문 생성). gpt-5 full **2콜 순차**.
- 변경: `compare_and_question()` 단일 gpt-5 **low** 호출이 상태 판정 + askable 항목 질문까지 한 번에 반환. `generate_questions.py`는 삭제(로직 흡수).
- 왕복 1회 제거.

### 0-3 — 추출 출력 축소 + item 캡
- abstract-only 추출은 `raw_name/category/sub_category/explicitly_reported`만 (description·evidence_text 등 미사용 필드 제거).
- 논문당 **최대 6개 item** 캡 → normalize payload 축소.

### 최종 tier/effort 맵

| 단계 | 모델 | effort |
|------|------|--------|
| 검색 쿼리 | mini | minimal |
| 논문 추출 | mini | minimal |
| normalize | mini | low |
| synthesize | mini | minimal |
| compare + questions (병합) | **gpt-5 full** | **low** |

> 원칙: 대량·분류(추출·normalize·synthesize)는 mini+minimal로 빠르게, 미묘한 판단(compare)과
> 최종 사용자 노출(questions)은 gpt-5로 정확하게 — 단 effort=low로 과사고 차단.

---

## 5. Phase 0 측정 결과 — 374s → 145s (−61%)

| 단계 | 이전 | **이후** | 변화 |
|------|-----:|-----:|------|
| 검색·선정 | 13s | 11s | (HTTP, 동일) |
| 논문 추출 | 94s | **11s** | effort=minimal + 스키마 축소 + 6개 캡 |
| normalize | 98s | **34s** | effort=low |
| synthesize | 35s | **13s** | effort=minimal |
| compare+questions | 137s (2콜) | **75s (1콜)** | 병합 + gpt-5 low |
| **합계** | **374s** | **145s** | **−61%** |

**품질 유지 확인**: `requirement_source=literature_derived`, 질문 5개 전부 출처 논문 연결
(constitutive_material_model · surrogate_model_construction · sensitivity_and_robustness_checks
· time_resolution_and_scales · mechanical_testing_protocol), 엄격 compare 정상(present 8·partial 4·missing 2).
전체 72 테스트 그린.

남은 병목: **compare+questions 75초**(gpt-5 low 단일 호출 — 정확도 중요 단계).

---

## 6. 남은 계획 (Phase 1+)

| # | 변경 | 기대 |
|---|------|------|
| 1-1 | normalize **category별 병렬** (category 고정이라 cross-category 클러스터 불가 → 쪼개 동시 처리) | 34s → 가장 느린 category ~10~15s |
| 1-2 | 추출 workers 6→10 (10편 1 wave) | 추출 추가 단축 |
| 1-3 | **stage fingerprint 캐시** (field+core+keywords+journal+ref_dois 해시 동일 시 search/extract/normalize/schema 재사용; outline·답변만 바뀌면 compare+questions만 재실행) | 재실행 **수초** |
| 2 | DOI별 extraction 전역 캐시 / embeddings 기반 deterministic clustering | 근본 절감 |

목표: 첫 실행 **~2분 이하**, 재실행 **수초**. 데모용 Fast/Quality 2모드 옵션.

---

## 7. 교훈 (요약)

1. **조용한 fallback은 적**이다 — 왜 떨어졌는지 안 남기면 "literature인 줄 알았는데 사실 YAML"을 못 잡는다. → stderr+파일 로깅.
2. **모델 크기 ≠ 속도 레버**. 추론 모델의 진짜 레버는 `reasoning_effort`. cap(max_tokens)은 목표가 아니다.
3. **순차 LLM 호출을 줄여라** — compare+questions 병합 한 방으로 1콜 제거.
4. **정확도 vs 속도는 단계별로 다르게** — 분류는 mini, 판단은 gpt-5(단 low effort).
5. **mini는 미묘한 판단에서 들쭉날쭉** — compare를 mini로 내렸다가 "파일 있으니 present" 오판 + 런마다 다른 결과로 되돌림.
6. **출력 스키마를 줄이면 LLM이 덜 생각한다** — 추출 6필드→4필드 + 6개 캡으로 94s→11s에 기여.

---

*paperflow · feature/research-reconstruction-mvp · 2026-06-26*
