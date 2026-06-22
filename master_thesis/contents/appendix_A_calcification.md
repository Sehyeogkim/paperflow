# Appendix A — Calcification generation algorithm (CP)

<!-- 초안 언어: 한국어 먼저 → 확정 후 영어 in-place 교체 (CLAUDE.md house rule).
     출처: Appendix_code/cal_gen.py (HXT_mesh_II.Voronoi_tesselation_KDTREE 및 whole_meshing_process).
     본문 대응: ch3_method2.md §3.1.2 "석회화 형상 생성(CP 전용)".
     핵심 메시지: 석회화 부피 V_calc은 직접 샘플 불가(lipid core 내부 구속) → 독립 입력은 분율 f_calc;
                 형상은 seed 기반 region-growing으로 생성, V_calc은 생성 후 측정되는 종속 기술자. -->

CP(calcified plaque) 표현형의 석회화는 구·타원체 같은 해석적 형상으로 부여하지 않고, lipid core 내부에서 **seed 기반 region-growing(영역 성장) 알고리즘**으로 생성하여 in vivo에서 관찰되는 불규칙한 석회화 형태를 재현하였다. 생성을 위한 형태학 입력파라메터와 생성 절차는 다음과 같다.

## A.1 입력 파라미터

| 기호 | 의미 | 단위 | 범위 (LHS) | 처리 |
|---|---|---|---|---|
| $f_\text{calc}$ | 석회화 분율 (calcified-cell fraction) | – | [0.10, 0.80] | **민감도 분석 입력** |
| $s_\text{ax}$ | seed의 축방향 위치 | – | [0, 0.80] | SA 제외 |
| $s_\text{circ}$ | seed의 원주방향 위치 | – | [0, 0.80] | SA 제외 |
| $w$ | 전파 이방성 비(축 vs 원주 가중) | – | [0.1, 10] | SA 제외 |
| $d_\text{buf}$ | 석회화–표면 버퍼 거리 | cm | [0.005, 0.02] | SA 제외 |

CP 데이터 생성에는 LAP 입력파라메터 12개와 석회화 형상 생성 파라미터 **5개**($f_\text{calc}$,$s_\text{ax}$, $s_\text{circ}$, $w$, $d_\text{buf}$), 그리고 석회화 재료 파라메터 ($E_\text{cal}$) 포함하여, 총 18개 1300 입력벡터를 함께 LHS로 변동시켰다. 이 중 최종적으로 민감도 분석 입력에서 제외된 파라메터 4가지($s_\text{ax}$, $s_\text{circ}$, $w$, $d_\text{buf}$)는 Sobol 분석에서 기여가 무시할 수준으로 확인되었다. 구체적으로, 주 출력값인 첨두 플라크 응력(PSS)에 대한 1차 Sobol 지수 $S_1$은 다음과 같다.

| 파라메터 | 의미 | $S_1$ (PSS) |
|---|---|---|
| $s_\text{ax}$ | seed 축방향 위치 | $1.8\times10^{-5}$ |
| $s_\text{circ}$ | seed 원주방향 위치 | $3.9\times10^{-4}$ |
| $w$ | 전파 이방성 비 | $4.7\times10^{-9}$ |
| $d_\text{buf}$ | 석회화–표면 버퍼 거리 | $\approx0\ (-3.6\times10^{-10})$ |

네 변수 모두 $S_1<10^{-3}$으로, 지배적 입력($E_\text{fc}$ $S_1\!\approx\!0.24$, SBP $\approx0.23$, $E_\text{vessel}\approx0.18$) 대비 약 3–4 차수(order of magnitude) 작다. 따라서, 민감도 분석 입력으로 남기는 석회화 형태학 변수는 $f_\text{calc}$, 단 1개이다.

## A.2 생성 절차

1. **도메인 확보 (erosion).** 미리 생성된 lipid core 볼륨 메시에서, 각 tetra cell 중심으로부터 섬유막 표면과의 거리를 KD-tree로 계산하여 섬유막 표면에서 $d_\text{buf}$ 이내의 셀을 제거한다. 남은 내부 셀 집합이 석회화가 존재할 수 있는 영역이며, 이로써 석회화가 섬유막·lipid 경계에 닿지 않도록 버퍼를 둔다.

2. **석회화 셀 개수 결정.** $N_\text{calc}=\operatorname{round}(f_\text{calc}\times N_\text{lipid,internal})$. 석회화를 구성하는 메쉬의 셀의 갯수를 바탕으로 석회화 구성부피를 계산한다.

3. **seed 위치 결정.** 내부 영역의 $z$ 범위를 $[0,1]$로 정규화하여 축방향 위치 $z_\text{seed}=z_\text{min}+(z_\text{max}-z_\text{min})\,s_\text{ax}$를 정한다. 해당 $z$ 단면의 lipid 반각 $\theta_\text{lipid}(z_\text{seed})$에 $s_\text{circ}$를 곱해 원주방향 각도 $\theta_\text{seed}=s_\text{circ}\,\theta_\text{lipid}(z_\text{seed})$를 얻고, $z=z_\text{seed}$ 단면에서 lumen 중심으로부터 seed까지의 거리 $d_\text{seed}$를 $d_\text{seed}=r_\text{lumen}(z_\text{seed})+t_\text{FC}+d_\text{buf}$로 두어 seed의 $(x,y,z)$ 좌표 $\big(x_\text{seed}=d_\text{seed}\sin\theta_\text{seed},\ y_\text{seed}=d_\text{seed}\cos\theta_\text{seed}+y_c(z_\text{seed})\big)$를 산출한다. 여기서 $d_\text{seed}$는 $z=z_\text{seed}$ 단면의 lumen 중심에서 seed까지의 거리이고, $t_\text{FC}$는 섬유막 두께(fibrous-cap thickness)이다.

4. **이방성 전파.** 셀 중심 좌표를 $(x,y)\!\to\!\sqrt{w}\,(x,y)$로 스케일링한 변환 공간에서 KD-tree를 구성하고, 변환된 seed로부터 최근접 $N_\text{calc}$개 셀을 선택한다. 이는 거리² $\approx w(dx^2+dy^2)+dz^2$의 가중 거리 기준으로 석회화 blob을 성장시켜, 등방/축방향 우세/원주방향 우세 형태를 모두 만들 수 있게 한다. 선택된 셀에 석회화 태그를 부여한다.

5. **표면 평활화.** 석회화 셀 집합을 표면(STL)으로 추출하고 Laplacian smoothing으로 메시 표면을 매끄럽게 한다.

6. 이후 검증을 위해서 Calcification volume을 측정한다. 