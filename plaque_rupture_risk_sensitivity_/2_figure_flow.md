# Figure flow  (workflow step 2)
주의: 여기서 실제 그림은 안 그린다. flow와 **각 figure가 전달할 메시지 한 줄**만 적는다.

## Method
- **Fig 1 — Workflow overview** (3 stages (1) data set generation , (2) rupture vulnerbaility index selection, (3) surrogate model trainng and senstivity anaylsis)
  - message: 전체 3단계 framework를 한눈에.
- **Fig 2 — Idealized coronary model geometry + morphological parameters** (2 pannels)
  - (A Plaque classification) LAP (3 solid domains) vs CP (4 solid domains) 도메인 구성
  - (B Plaque geometry) morphological parameters를 geometry에 annotate (FC thickness, lipid arc angle, plaque burden 등)
  - message: 두 plaque phenotype의 도메인 차이 + morphological 변수가 기하학적으로 무엇인지/어디에 정의되는지. (변수 범위는 Table 1)
- **Fig 3 — Boundary conditions** (fluid + solid)
  - message: 맥동 유동/고체 경계조건 설정.
- **Fig 4 - Cost effective FSI process
- **Fig 5 — rupture-location index definition.
- **Table 1 — Input parameters**: morphological + hemodynamic + material (range / distribution)
  - message: 1,000-sample 설계공간의 전체 입력변수와 범위.

## Result
- **Fig 6 — VI selection**: 7 criteria × 6 candidates (6 columns × 7 rows)
  - message: 6개 후보 중 7개 임상 기준을 모두 만족하는 2개 (VI1 = ΔPSS/E_FC^0.5, VI2 = ΔPSS/E_FC^1.0) 선정.
- **Fig 7 — Sensitivity analysis** (Sobol S1 & S_total; individual + grouped)
  - message: Material > Hemodynamic > Morphological; 지배 인자 = E_vessel, E_FC, 수축기압, 맥압.
- **Fig 8 — Rupture location results** (optional; outline §3.3)
  - message: 원주방향 shoulder-dominant(임상·시뮬 일치); 축방향은 임상 proximal vs 시뮬 distal (constant-FC-thickness 가정의 한계).