# Question-to-logic-graph-to-document product loop

2026-08-13 제품 정의: PaperFlow의 정식 사용자 흐름은 연구자가 기본 정보와 결과·참고 파일을 제공하면,
에이전트가 문서의 논리 구조에 필요한 공백을 찾아 질문하고, 답변마다 그래프를 국소적으로 갱신하며,
사용자가 특정 graph revision을 승인한 뒤 그 그래프를 유일한 근거로 문서를 생성하는 것이다.

핵심 제품 산출물은 revision과 provenance를 가진 자기설명적 논리/지식 그래프다.
그래프 시각화는 이 구조를 이해하고 수정하기 위한 보조 UI이며 제품의 목적 자체가 아니다.

질문은 단순 체크리스트가 아니라 어느 claim, evidence, method, data 연결을 왜 채우는지 명시해야 한다.
답변은 append-only 이력으로 남기고 `author_attested`, `verified`, `unknown`을 구분한다.
문서 생성은 승인된 graph revision과 strict graph audit를 통과해야 시작할 수 있다.

관련 결정: [[portable-graph-is-the-product-artifact]]
