# memory_local — 프로젝트 로컬 메모리

이 폴더는 **이 프로젝트(AI-Human 협업 글쓰기 시스템 / 졸업 저널)에서
중요하게 발생·논의된 정보**를 보존하는 곳이다. 대화가 끝나도 다음 세션이
여기를 읽고 맥락을 이어간다.

## 규칙
- 중요한 프로젝트 정보(페인포인트, 가설, 제품 결정, 설계 방향)가 발생/논의되면
  **하나의 사실 = 하나의 .md 파일**로 여기에 저장.
- 파일명은 kebab-case로 내용을 설명 (예: `painpoint_figure_design_lastmile.md`).
- 새 파일을 만들면 아래 **인덱스**에 한 줄 추가.
- 관련 메모는 본문에서 `[[파일명]]`(확장자 제외)으로 링크.
- 상대 날짜는 절대 날짜로 변환해 기록.
- 코드/깃 히스토리/CLAUDE.md가 이미 담은 것은 중복 저장하지 않는다.

## 인덱스
- [페인포인트: figure 디자인의 지각적 last-mile](painpoint_figure_design_lastmile.md)
  — 글쓰기가 figure 요구를 늦게 드러냄 + 손으로만 가능한 마지막 디자인. 분야 일반화 가설 + 판별 질문.
- [제품 비전: 인간+Claude 협업 figure 도구](product_vision_collaborative_figure_tool.md)
  — "figure용 Cursor" (trame/ParaView + MCP), 양방향 카메라 상태 동기화, 오픈소스 포크 가능성.
- [타겟 저널(CBM) + FSI companion 논문 관계](master-thesis-target-journal-and-fsi-companion.md)
  — 타겟=Computers in Biology and Medicine(자유형식 first submission), FSI는 under-review companion, §2.1 governing eq 유지/validation 인용 결정.
- [석회화: fraction=Sobol 입력, V_calc=validation 전용](calcification-fraction-is-sobol-input-volume-is-validation.md)
  — V_calc은 lipid 내부 구속→비독립이라 Sobol 입력 불가; 독립 분율 f_calc을 입력으로, V_calc 분포는 임상범위 대조 validation.
- [Method 작성 방침: 표준은 인용, 비표준만 Appendix](method-writing-cite-dont-rederive-convention.md)
  — 저널式: 확립 모델은 cite+값표+코드공개, Appendix엔 비표준 수식만. BC canonical refs 4개 키 포함.
- [민감도 결과: 위치 + 핵심 수치](sensitivity-results-location-and-findings.md)
  — ws2 Sobol csv 위치(+로컬 사본), 재료물성 지배·지배인자(E_vessel/E_FC/P_sys)·PP는 작음, CP 14-input nuance, 미해결(R²·유효N·파열위치).
- [.tex을 Notion에서 재생성 (2026-06-19)](thesis-tex-rebuilt-from-notion-2026-06-19.md)
  — 20244152_sehyeog_0619.tex 전체를 Notion 본문으로 교체·컴파일(48p). figure_page 매핑은 순서 가정(검증 필요), A2/B1 figure 없음, references.bib 67→103 확장 + 별칭키 정규화, VERIFY stub 키 목록.
