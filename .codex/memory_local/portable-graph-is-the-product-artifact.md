# Portable graph is the product artifact

2026-08-10 결정: 데모 HTML은 지식의 추출·질문·시각화를 위한 인터페이스이고,
실제 제품 산출물은 후속 작업에 단독으로 전달할 수 있는 `graph.json`이다.

`graph.json`은 다음을 함께 담는다.

- 논문·코드에서 재추출 가능한 layer 1 지식
- 저자에게 질문해야만 얻는 layer 2 지식과 실제 답변
- node kind, edge relation, field 의미를 설명하는 자기설명적 스키마
- 모델이 답변을 추측하지 않고 노드 ID로 근거를 인용하도록 하는 사용 규칙
- readiness gate, failure diagnosis, transfer plan, handover brief의 application recipe
- application을 검증할 수 있는 시나리오와 합격 조건

효용은 일반 답변의 문장 품질이 아니라, 실제 연구 작업에서 GO/HOLD 판정,
실패 원인 역추적, 이전 조건 재검증, 저자 재확인 비용 감소로 측정한다.

