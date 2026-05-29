# Figure flow  (workflow step 2)

주의: 여기서 실제 그림은 안 그린다. flow와 **각 figure가 전달할 메시지 한 줄**만 적는다.

## Method
- **Fig 1 — Workflow overview** (4 stages: ① dataset generation ② VI selection ③ surrogate training ④ sensitivity)
  - message: 전체 4단계 framework를 한눈에.
- **Fig 2 — Cost-effective FSI framework (recap)** — 선행 논문에서 검증된 방법의 간단 요약 + 인용
  - message: 본 연구가 *활용*하는 도구임을 보임 (재검증이 목적 아님 → 간결하게, 상세 validation은 prior paper 인용). 분량 부담 크면 생략/축소 가능.(학위논문에서는 validation geometry 추가하자)
- **Fig 3 — Idealized coronary model geometry + morphological parameters** (2 panels)
  - (a) LAP (3 solid domains) vs CP (4 solid domains) 도메인 구성
  - (b) morphological parameters를 geometry에 annotate (FC thickness, lipid arc angle, plaque burden 등)
  - message: 두 plaque phenotype의 도메인 차이 + morphological 변수가 기하학적으로 무엇인지/어디에 정의되는지. (변수 범위는 Table 1)
- **Fig 4 — Boundary conditions** (fluid + solid)
  - message: 맥동 유동/고체 경계조건 설정.
- **Fig 5 — Output metrics**: PSS / ΔPSS (sphere-averaging), VI = stress/strength, rupture-location index
  - message: 무엇을 출력으로 측정하는가(응력지표·취약성지수·파열위치)의 정의.
- **Table 1 — Input parameters**: morphological + hemodynamic + material (range / distribution)
  - message: 1,000-sample 설계공간의 전체 입력변수와 범위.

## Result
- **Fig 6 — VI selection**: 7 criteria × 6 candidates (6 columns × 7 rows)
  - message: 6개 후보 중 7개 임상 기준을 모두 만족하는 2개 (VI1 = ΔPSS/E_FC^0.5, VI2 = ΔPSS/E_FC^1.0) 선정.
- **Fig 7 — Sensitivity analysis** (Sobol S1 & S_total; individual + grouped)
  - message: Material > Hemodynamic > Morphological; 지배 인자 = E_vessel, E_FC, 수축기압, 맥압.
- **Fig 8 — Rupture location results** (optional; outline §3.3)
  - message: 원주방향 shoulder-dominant(임상·시뮬 일치); 축방향은 임상 proximal vs 시뮬 distal (constant-FC-thickness 가정의 한계).

<!-- 번호 정리: 이전 버전의 Figure4 누락 / Figure6 중복을 수정. 형태변수는 Fig3(geometry)+Table1로 분리. -->
