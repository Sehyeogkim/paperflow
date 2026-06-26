# PaperFlow — business & product purpose (2026-06-26)

## 한 줄 목적

**연구자가 연구 자료를 업로드하고 핵심 질문에 답하면, PaperFlow가 연구의 논리 구조를 복원하여 근거 추적이 가능한 논문 초안을 Word 파일로 생성하는 SaaS.**

제품 경험의 핵심은 다음 한 줄이다.

> 자료를 업로드한다 → 필요한 질문에 답한다 → 논문 Word 초안이 완성되고 앱 오른쪽에서 바로 확인된다.

## 해결하려는 문제

연구자는 논문 작성에 필요한 정보와 데이터는 이미 가지고 있지만, 이를 다음 구조로 정리하는 데 가장 많은 시간을 쓴다.

- 무엇을 핵심 주장으로 둘 것인가
- 어떤 데이터와 분석이 각 주장을 지지하는가
- 어떤 선행연구가 배경·방법·해석을 정당화하는가
- 각 내용을 Introduction, Method, Result, Discussion에 어떻게 배치할 것인가

PaperFlow는 단순한 문장 생성기가 아니라, 흩어진 연구 자료를 논문의 논리 구조로 변환하는 **Manuscript Compiler**이다.

## 사용자 입력 계약

### 필수

1. **Journal and user information**
   - 목표 저널
   - 연구 분야
   - 저자·소속 등 논문 메타데이터

2. **Core message**
   - 이 논문에서 가장 말하고 싶은 결과 또는 주장
   - 한 문장 또는 짧은 문단

3. **Data / result files + explanation**
   - CSV, XLSX, JSON, TXT, 이미지, 결과표 등
   - 각 파일이 무엇이며 어떤 분석에서 생성되었는지 한 줄 설명

4. **Research plan or related documents**
   - 연구계획서, 연구노트, 기존 Method 문서, 발표자료, thesis draft 등
   - 관련 reference PDF/BibTeX/DOI 목록 포함 가능

### 선택

5. **Outline**
   - 사용자가 이미 가지고 있다면 업로드
   - 없으면 PaperFlow가 자동 생성

## 핵심 기술

### 1. Research Reconstruction Engine

사용자 자료와 데이터에서 다음을 복원한다.

- 연구문제와 목적
- 연구 설계와 방법
- 데이터셋과 변수
- 주요 결과 후보
- 비교 대상과 baseline
- contribution 후보
- limitations
- 알려진 사실과 누락정보

결과는 구조화된 `research_state.json`으로 저장한다.

### 2. Critical Question Engine

잠정 logic graph를 완성하기 위해 필요한 정보를 사용자에게 질문한다.

- 질문 수를 임의로 5개 이하로 제한하지 않는다.
- 질문은 정보 가치와 논문 방향에 미치는 영향으로 우선순위를 정한다.
- 한 화면에는 작은 묶음으로 제시하고, 답변에 따라 다음 질문을 적응적으로 생성한다.
- 종료 조건은 질문 개수가 아니라 **핵심 claim을 방어 가능한 수준으로 작성할 정보가 확보되었는가**이다.

### 3. Evidence-aware Logic Graph

논문 작성 전 다음 관계를 구조화한다.

```text
Claim
├─ Evidence: 이번 연구에서 관찰한 결과
│  ├─ Data: 실제 파일·수치·측정값
│  └─ Method: 결과를 생성한 실험·해석·통계 절차
├─ Reference: 배경, 방법 정당화, 결과 비교 문헌
├─ Warrant: Evidence가 Claim을 지지하는 과학적 이유
├─ Qualifier: 조건, 한계, 적용 범위
└─ Artifact: Figure, Table, Equation으로 보여주는 방식
```

Logic graph는 사용자 화면의 주인공이 아니라, 초안의 논리성과 근거 추적성을 보장하는 내부 엔진이다.

## 문헌조사의 역할

문헌조사는 한 번의 일반 검색이 아니라 두 단계로 수행한다.

1. **Field reconstruction search**
   - 유사 연구의 일반적 논문 구조
   - 필수 방법·검증 항목
   - 일반적인 Figure/Table 표현 방식

2. **Claim-specific search**
   - 각 claim의 배경 문헌
   - 방법을 정당화하는 문헌
   - 결과를 비교·해석할 문헌
   - logic graph에서 비어 있는 reference/warrant 보완

문헌조사의 목적은 논문을 많이 모으는 것이 아니라, logic graph를 완성하는 것이다.

## 최종 워크플로우

```text
User inputs
→ document/data ingestion
→ research state reconstruction
→ field-level literature search
→ preliminary logic graph
→ adaptive critical-question loop
→ claim-specific literature search
→ final logic graph
→ section/paragraph plan
→ manuscript generation
→ grounding/fact checks
→ DOCX export + right-side preview
```

## 출력

- Introduction
- Method
- Result
- Discussion
- Conclusion
- Abstract(선택 또는 자동)
- Figure/Table placeholder와 제작 prompt
- 검증된 references
- logic graph / evidence map
- grounding 및 missing-information report
- `.docx` 다운로드 파일
- 앱 오른쪽에서 확인할 HTML preview

백엔드의 원본은 Word 파일이 아니라 구조화된 manuscript state이다. 동일한 상태에서 HTML preview와 DOCX를 각각 생성한다.

## MVP 범위 — 2026-06-28

### 포함

- 위 사용자 입력 업로드
- 파일별 설명 입력
- 관련 논문 검색
- research state 생성
- preliminary logic graph 생성
- 적응형 질문/답변
- final logic graph 생성
- 전체 논문 초안 생성
- Figure/Table placeholder와 prompt 생성
- DOCX export
- 파일 클릭 시 오른쪽 preview

### 제외

- Word 수준의 본문 직접 편집
- 실시간 공동편집
- 실제 journal figure 이미지 생성
- 완전한 citation entailment 검증
- 모든 연구 분야에 대한 범용 requirement schema
- 복잡한 multi-agent reviewer 시스템

## 검증 가설

1. 사용자가 제공하는 정보가 많을수록 초안 품질은 올라간다.
2. 그러나 입력과 질문이 많아질수록 이탈률도 증가한다.
3. PaperFlow의 핵심 실험은 **초안 품질과 사용자 피로도 사이의 threshold**를 찾는 것이다.
4. 사용자는 완벽한 논문보다 자신의 연구를 이해하고 만든 수정 가능한 초안을 원한다.
5. 주요 claim이 data/reference와 연결된 evidence map이 있으면 AI 초안에 대한 신뢰도가 상승한다.

## 비즈니스

- 개인 연구자와 대학원생을 시작점으로 하는 구독형 SaaS
- 이후 연구실, 대학, R&D 조직으로 확장
- 모델은 고객에게 노출하지 않고 task별 provider routing과 caching으로 비용 최적화
- 핵심 자산은 모델 자체가 아니라 research reconstruction schema, question policy, logic graph, grounding pipeline이다.
