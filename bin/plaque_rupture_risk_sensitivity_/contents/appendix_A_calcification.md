# Appendix A — Calcification generation algorithm (CP)

<!-- 초안 언어: 한국어 먼저 → 확정 후 영어 in-place 교체 (CLAUDE.md house rule).
     출처: Appendix_code/cal_gen.py (HXT_mesh_II.Voronoi_tesselation_KDTREE 및 whole_meshing_process).
     본문 대응: ch3_method2.md §3.1.2 "석회화 형상 생성(CP 전용)".
     핵심 메시지: 석회화 부피 V_calc은 직접 샘플 불가(lipid core 내부 구속) → 독립 입력은 분율 f_calc;
                 형상은 seed 기반 region-growing으로 생성, V_calc은 생성 후 측정되는 종속 기술자. -->

CP(calcified plaque) 표현형의 석회화는 구·타원체 같은 해석적 형상으로 부여하지 않고, lipid core 내부에서 **seed 기반 region-growing(영역 성장) 알고리즘**으로 생성하여 in vivo에서 관찰되는 불규칙한 석회화 형태를 재현하였다. 생성을 위한 입력파라메터와 생성 절차는 다음과 같다.

## A.1 입력 파라미터

| CSV 컬럼 | 기호 | 의미 | 단위 | 범위 (LHS) | 처리 |
|---|---|---|---|---|---|
| `fraction` | $f_\text{calc}$ | 석회화 분율 (calcified-cell fraction) | – | [0.10, 0.80] | **민감도 분석 입력** |
| `ca_axial_skewness` | $s_\text{ax}$ | seed의 축방향 위치 | – | [0, 0.80] | SA 제외 |
| `ca_shoulder_skewness` | $s_\text{circ}$ | seed의 원주방향 위치 | – | [0, 0.80] | SA 제외 |
| `ca_strength_ratio` | $w$ | 전파 이방성 비(축 vs 원주 가중) | – | [0.1, 10] | SA 제외 |
| `d_fc_ca` | $d_\text{buf}$ | 석회화–표면 버퍼 거리 | cm | [0.005, 0.02] | SA 제외 |
| `E_cal` | $E_\text{calc}$ | 석회화 영률 | dyn/cm² | [7×10⁹, 2.5×10¹¹] | **민감도 분석 입력** (재료 인자군) |

CP 데이터 생성에는 분석 입력 14개에 더해 석회화 형상 생성 파라미터 **4개**($s_\text{ax}$, $s_\text{circ}$, $w$, $d_\text{buf}$)를 함께 LHS로 변동시켰다(총 18개, 1,300 입력벡터). 이 중 최종적으로 민감도 분석 입력에서 제외된 파라메터 4가지는 Sobol 분석에서 기여가 무시할 수준으로 확인되었다. 따라서, 민감도 분석 입력으로 남기는 석회화 변수는 $f_\text{calc}$와 $E_\text{calc}$ 2개이다.

## A.2 생성 절차

1. **도메인 확보 (erosion).** lipid core 볼륨 메시에서, 각 tetra cell 중심으로부터 섬유막 표면과의 거리를 KD-tree로 계산하여 표면에서 $d_\text{buf}$ 이내의 셀을 제거한다. 남은 내부 셀 집합이 석회화가 존재할 수 있는 영역이며, 이로써 석회화가 섬유막·lipid 경계에 닿지 않도록 버퍼를 둔다.

2. **석회화 셀 개수 결정.** $N_\text{calc}=\operatorname{round}(f_\text{calc}\times N_\text{lipid,internal})$.

3. **seed 위치 결정.** 내부 영역의 $z$ 범위를 $[0,1]$로 정규화하여 $z_\text{seed}=z_\text{min}+(z_\text{max}-z_\text{min})\,s_\text{ax}$로 축방향 위치를, 해당 $z$ 단면의 lipid 반각에 $s_\text{circ}$를 곱해 원주방향 각도를 정하고, lumen 중심·반경·섬유막 두께·버퍼로부터 seed의 $(x,y,z)$ 좌표를 산출한다. seed를 포함하는(없으면 최근접) tetra를 seed cell로 지정한다.

4. **이방성 전파.** 셀 중심 좌표를 $(x,y)\!\to\!\sqrt{w_\text{circ}}\,(x,y)$, $z\!\to\!\sqrt{w_\text{ax}}\,z$로 스케일링한 변환 공간에서 KD-tree를 구성하고, 변환된 seed로부터 최근접 $N_\text{calc}$개 셀을 선택한다. 이는 거리² $\approx w_\text{circ}(dx^2+dy^2)+w_\text{ax}\,dz^2$의 가중 거리 기준으로 석회화 blob을 성장시켜, 등방/축방향 우세/원주방향 우세 형태를 모두 만들 수 있게 한다. 선택된 셀에 석회화 태그를 부여한다.

5. **표면 평활화.** 석회화 셀 집합을 표면(STL)으로 추출하고 Laplacian smoothing으로 메시 표면을 매끄럽게 한다.

6. **lipid 내부 보장 (boolean intersection).** 평활화된 석회화 표면과 lipid core를 boolean intersection하여 석회화가 lipid core 경계를 넘지 않도록 강제한다. `select_enclosed_points`로 석회화 전 점이 lipid 내부에 있는지 검증하며, 실패한 case는 폐기한다.

7. **고체 도메인 통합.** 석회화 STEP을 lipid·fc·lumen·solid와 함께 gmsh로 불러와 lipid core에서 석회화 영역을 cut하고, solid·lipid·fc·calcification에 각각 물리 태그를 부여한 뒤 병변 영역 box-field로 국소 세분화하여 2차 사면체 메시를 생성한다.

8. 이후 검증을 위해서 Calcification volume을 측정한다. 