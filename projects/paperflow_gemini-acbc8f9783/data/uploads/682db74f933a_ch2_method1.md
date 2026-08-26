# Chapter 2 — Method 1: Cost-effective FSI

<!--
초안 언어: 한국어 (수식·수치·전문용어는 원어 유지) → 확정 후 같은 파일에서 영어로 in-place 교체.
출처: master_thesis/reference/Snapshot_based_Framework_ver2.pdf (Kim et al., KAIST, under review).
인용: [cite:<key>] → reference/references.json + references.bib 에 등록.
figure/table 번호는 thesis 자체 체계, 캡션 주석에 원논문 Fig/Table 매핑 표기.
대응 outline: chapter2 / 대응 figure flow: Method1.
-->

## Overview — 분석 파이프라인 (4-stage)

본 연구의 분석은 총 4단계 파이프라인으로 구성된다: **(1)** 저비용 FSI를 활용한 입출력 데이터 생성, **(2)** 파열 위험지표(vulnerability index)의 형성 및 임상 기준 선별, **(3)** 대리모델(GPR surrogate) 학습, **(4)** 소볼(Sobol) 민감도 분석.

이 가운데 **stage 1의 데이터 생성을 구동하는 엔진이 본 장(chapter 2)에서 설명하는 비용효율적 맥동성 FSI 기법**이다. 이 기법은 저자의 선행 연구에서 제안·검증된 것으로[cite:kim_snapshot], 본 연구에서는 이를 *도구*로 활용한다. 본 장에서는 그 기반이 되는 FSI 기법 자체와 검증을 다루며, **4단계 파이프라인 전체(stage 1~4)의 구성과 workflow overview figure는 chapter 3에서 제시한다.**

<!-- workflow overview(4-stage) figure는 ch3로 이동. ch2에는 figure 없이 텍스트 포인터만. Fig 1 = 2.1의 FSI framework. -->

---

## 2.1 Cost-effective FSI framework

전체 파이프라인을 순서대로 살펴보기에 앞서, 데이터 생성에 사용된 비용효율적 FSI 기법을 정리한다. 완전 연성(fully coupled) 3차원 맥동 FSI 해석은 혈관벽 응력 평가에 가장 충실하지만, 반복적·환자특이적 적용에는 계산 비용이 지나치게 크다[cite:kim_snapshot]. 본 기법의 핵심 아이디어는 맥동 하중의 **시간 성분과 공간 성분을 분리(decouple)** 하는 것으로, 다음과 같이 요약된다:

> 임의의 유체·고체 맥동 경계조건이 주어졌을 때, 심장주기 내 특정 목표 시점 $t_a$에서의 국소 혈관벽 응력장 $\sigma(t_a)$는, **단일 맥동 1차원(1D) 축소차수 해석**과 **그 시점 $t_a$에서 평가된 정적(steady) 3차원 유체·구조 해석**을 결합하여 정확하게 근사할 수 있다.

이 접근은 첨두 수축기(peak systole)나 이완기말(end diastole)처럼 **대표 시점의 생체역학 지표**만으로도 충분한 진단 정보를 얻을 수 있다는 관찰에 근거한다[cite:kim_snapshot]. 즉, 시간 의존적 연성 문제 전체를 풀지 않고 대표 시점의 순간 응력 상태만 추정한다.

(Fig 1 — Cost-effective FSI framework: snapshot-based coupling 개요.)

### Process (3 sequential steps)

Figure 1에 보이듯, 본 기법은 세 단계로 순차 진행된다.

- **Step 1 — 1D pulsatile reduced-order hemodynamics (fluid).** 물리 기반 1D 축소차수모델(ROM)로 맥동 해석을 수행하여, 혈관 트리 전체(입·출구 포함)에서 시간에 따른 압력 $P(t)$와 유량 $Q(t)$ 파형을 계산한다. 여기서 목표 시점 $t_a$의 경계조건 값 $P_{BC}(t_a)$, $Q_{BC}(t_a)$를 추출한다.
- **Step 2 — steady 3D fluid → wall traction.** 추출한 경계조건을 정적 3차원 유체 해석에 부과한다. 시간적으로는 정적이지만 혈관 도메인의 기하 복잡성을 그대로 보존하며, 내강 표면(luminal surface)에 작용하는 **벽면 traction**(압력 + 점성 전단응력의 합)을 계산한다.
- **Step 3 — steady 3D structural → stress.** 계산된 벽면 traction을 고체(벽) 도메인 표면에 경계조건으로 부과하여 준정적(quasi-static) 구조 해석을 수행하고, 최종적으로 $t_a$에서의 응력장 $\sigma_{vm}(t_a)$을 얻는다.

여러 목표 시점 $t_a$에 대해 Step 2~3을 반복하면, 1회의 맥동 1D 해석만으로 심장주기 내 대표 시점들의 응력 상태를 복원할 수 있다. 비용이 큰 완전 과도(transient) 3D FSI를 매 시점 푸는 대신 정적 snapshot 해석으로 대체함으로써 계산 비용을 크게 절감하며, 이 절감 덕분에 chapter 3의 1,000-sample 규모 데이터셋 생성이 가능해진다.

---

## 2.2 Governing equations

### 2.2.1 One-dimensional reduced-order hemodynamics (Step 1)

맥동 혈류는 강체 벽(rigid wall) 가정 하에서 다음 1차원 지배방정식으로 계산한다:

$$\frac{\partial Q}{\partial z} = 0 \tag{1}$$

$$\frac{\partial Q}{\partial t} + \frac{\partial}{\partial z}\!\left(\frac{\alpha Q^2}{S}\right) + \frac{S}{\rho}\frac{\partial P}{\partial z} = N\frac{Q}{S} \tag{2}$$

여기서 $S$는 단면적, $z$는 축방향 좌표, $\alpha$는 운동량 보정계수, $N$은 점성 저항항이다. 포물선형 속도분포를 가정하여 $\alpha = 4/3$, $N = 8\pi\nu$로 둔다.

식 (1)~(2)는 전역(global) 맥동 혈류는 효율적으로 포착하나, 협착(stenosis)·분기(bifurcation) 같은 기하학적으로 복잡한 영역의 압력 손실 표현에는 한계가 있다. 이를 보완하기 위해 저자의 선행 연구[cite:choi2025rom]에서 개발된 물리 기반 ROM을 도입하여, 압력강하를 유량의 비선형 함수로 모델링한다:

$$\Delta P = aQ + bQ^2 + c\frac{dQ}{dt} \tag{3}$$

계수 $a$, $b$, $c$는 각각 점성·비선형·관성 기여를 나타내며, geometry별 전처리 절차로 식별된다[cite:choi2025rom].

### 2.2.2 Snapshot coupling and 3D governing equations (Step 2–3)

각 목표 시점 $t_a$에서 정적 3차원 유체 해석으로 벽면 traction을 정의한다:

$$\mathbf{t}_{wall}(t_a) = \sigma_f(t_a)\,\mathbf{n} \quad \text{on } \Gamma_{wall} \tag{4}$$

이 traction을 고체 도메인의 대응 표면에 surface mapping으로 전달하여 경계조건으로 부과한다. 구조 문제는 입·출구를 고정한 준정적 가정 하에서 풀며, 평형방정식은 다음과 같다:

$$\nabla\cdot\sigma_s + \mathbf{f}_s = 0 \quad \text{in } \Omega_s \tag{5}$$

3차원 유체 해석은 비압축성 Navier–Stokes 방정식과 연속방정식을 푼다. 비교 기준이 되는 완전 연성 FSI 해석에서는 유체·고체 도메인을 ALE(arbitrary Lagrangian–Eulerian) 정식화로 연성하여 계면에서의 메시 변형과 상호작용을 일관되게 처리한다.

본 기법은 각 시점에서 순간 유체 traction이 구조 응답을 지배하고 과도 유체 관성은 응력 평가에 2차적 영향만 미친다고 가정한다. 따라서 전체 과도 동역학이 아니라 **순간 응력 상태**를 근사하도록 설계된다.

### 2.2.3 Constitutive assumption

혈관벽은 등방 선형탄성(isotropic linear elastic) 재료로 모델링한다. 혈관 조직은 실제로 비선형·이방성·초탄성 거동을 보이나[cite:masson2011], 선형탄성은 수치적 안정성과 파라미터 불확실성 감소 측면에서 전산 생체역학에서 널리 채택되어 왔다[cite:cheng1993]. 본 연구에서는 이 단순 구성모델을 통해 상세 재료 거동을 포착하기보다 **제안 기법 자체의 성능을 분리·평가**하는 데 목적을 둔다.

---

## 2.3 Validation models

제안 기법을 해부학적·혈류역학적 복잡도가 점증하는 **3가지 geometry**에 대해 검증하였다: (1) 이상적 좌전하행지(LAD) 관상동맥, (2) 환자 특이 관상동맥, (3) 환자 특이 복부대동맥류(AAA).

> ⚠️ **도메인 구성 — 본 검증의 핵심 특징.** 본 장의 세 모델은 **유체 1개 + 고체(벽) 1개, 총 2개 도메인**으로 구성되며, 벽은 **단일 균질(homogeneous) 선형탄성 도메인**이다. 즉 plaque 조성(섬유막·지질핵·석회화)을 명시적으로 구분하지 않는다 — 이는 본 기법 검증 단계의 의도된 단순화이자 한계이다. **Chapter 3의 메인 연구에서는 이 단일 벽을 다도메인(혈관벽 + FC + lipid (+ calcification))으로 확장**하여 파열 위험을 평가한다.

### 2.3.1 Geometries

(Fig 2 — (A) ideal LAD coronary geometry + inlet pressure waveform + coronary lumped-parameter BC. 원논문 Fig 2.)
(Fig 3 — subject-specific coronary geometry + heart/Windkessel/coronary BC. 원논문 Fig 3.)
(Fig 4 — subject-specific AAA geometry + inlet flow-rate waveform + Windkessel RCR BC. 원논문 Fig 4.)

- **이상적 LAD 관상동맥** (Fig 2): 단순 원통 분절. 전체 길이 $L = 10$ cm, lumen 반경 $R = 0.1$ cm, 벽 두께 $t = 0.02$ cm. 협착 질환 모사를 위해 원위부(distal)에 협착도(DOS) **55%**의 편심 협착(eccentric stenosis)을 도입.
- **환자 특이 관상동맥** (Fig 3): CT 영상으로 재구성. 좌주간지(LM)·중간 LAD·원위 LAD에 직렬 삼중 협착 — DOS 각각 **68% / 69% / 70%** (평균 69%).
- **환자 특이 AAA** (Fig 4): CT 영상으로 재구성. 상당한 내강 확장과 복잡한 유동을 보이는 동맥류, outlet 2개(b, c).

유체·고체 도메인은 상용 메시 소프트웨어 MeshSim(Simmetrix Inc., Clifton Park, NY, USA)로 사면체(tetrahedral) 메시를 생성하였다. 유체 도메인은 근벽부 혈류 해상도를 위해 벽 근처에 **경계층(boundary layer) 3겹**을 추가하였다.

### 2.3.2 Material properties

검증 모델의 고체·유체 물성은 문헌값을 바탕으로 부여하였다(선형탄성·고정값).

| 대상 | Young's modulus $E$ | Poisson's ratio $\nu$ | density $\rho$ | 출처 |
|---|---|---|---|---|
| Coronary wall | $1.0\times10^{7}$ dynes/cm² | 0.45 | $\rho_s = 1.1$ g/cm³ | [cite:cheng1993, hsu2014, chen2021ldl, jiang2022] |
| AAA wall | $6.0\times10^{7}$ dynes/cm² | 0.49 | $\rho_s = 1.0$ g/cm³ | [cite:joldes2016, figueroa2006] |
| Blood (incompressible Newtonian) | — | — | $\rho_f = 1.06$ g/cm³, $\mu_f = 0.04$ poise | — |

준정적 구조 해석 가정 하에서 관성항 $\rho_s\,\partial^2 d_s/\partial t^2$은 무시한다.

> ⚠️ **구분 메모.** 본 절의 material property는 **검증용 고정 물성**이다. Chapter 3의 민감도 분석에서 다루는 material(E_FC, E_vessel 등)은 1,000-sample로 **변동시키는 입력 변수**로, 서로 다른 대상이다.

### 2.3.3 Boundary conditions

각 geometry의 유체 경계조건은 맥동 입구 파형과 출구 lumped-parameter(관상동맥)·Windkessel(RCR) 모델로 부과하였다. 고체 도메인은 모든 경우에서 입·출구 단면을 고정하고 내강 표면에 유체 유발 traction을 가하였으며, 이 경계조건 체계는 완전 연성 기준 FSI와 제안 기법에 동일하게 적용해 직접 비교 가능성을 확보하였다. 경계조건 값은 Table 1·2에 정리한다. (출처: 원논문 Fig 2~4, `data/cost_effective_FSI_BC/bc.md`와 일치)

**Table 1 — Ideal coronary & AAA boundary-condition coefficients**

| Model | Parameter | Value | Unit |
|---|---|---|---|
| Ideal coronary (outlet b) | $R_a$ | 78827 | dynes·s/cm⁵ |
| | $C_a$ | $0.396\times10^{-6}$ | cm⁵/dynes |
| | $R_{a\text{-micro}}$ | 128094 | dynes·s/cm⁵ |
| | $C_{im}$ | $3.20\times10^{-5}$ | cm⁵/dynes |
| | $R_v$ | 19706 | dynes·s/cm⁵ |
| | $R_{v\text{-micro}}$ | 19706 | dynes·s/cm⁵ |
| | inlet | prescribed pressure waveform (≈70–130 mmHg) | — |
| AAA (outlets b, c) | $R_p$ | 450.0 | dyn·s/cm⁵ |
| | $C$ | $5.0\times10^{-4}$ | cm⁵/dyn |
| | $R_d$ | 6820.0 | dyn·s/cm⁵ |
| | inlet | prescribed flow-rate waveform | — |

**Table 2 — Subject-specific coronary boundary-condition coefficients**

*Heart inlet model (a):*

| Parameter | Value | Unit |
|---|---|---|
| $CO$ | 5.0 | L/min |
| $t_{cycle}$ | 1.0 | s |
| $t_{sys}$ | 0.33 | s |
| $R_{LA}$ | 5.0 | dyn·s/cm⁵ |
| $L_{LA}$ | 1.0 | dyn·s²/cm⁵ |
| $R_{LV}$ | 10.0 | dyn·s/cm⁵ |
| $L_{LV}$ | 10.0 | dyn·s²/cm⁵ |
| $E_{max}$ | 2.0 | mmHg/cc |

*Aortic Windkessel RCR (b):* $R_p = 232.44$, $C = 1.50\times10^{-3}$, $R_d = 1317.18$ (단위: $R$ [dyn·s/cm⁵], $C$ [cm⁵/dynes])

*Coronary outlets (c–m):*

| Outlet | $R_a$ | $R_{a\text{-micro}}$ | $R_{v\text{-micro}}$ | $C_a$ | $C_{im}$ |
|---|---|---|---|---|---|
| c | 76680 | 128624 | 39576 | $2.86\times10^{-7}$ | $2.31\times10^{-6}$ |
| d | 67588 | 113374 | 34884 | $3.97\times10^{-7}$ | $3.21\times10^{-6}$ |
| e | 65168 | 109315 | 33635 | $4.37\times10^{-7}$ | $3.53\times10^{-6}$ |
| f | 56556 | 94868 | 29190 | $6.31\times10^{-7}$ | $5.11\times10^{-6}$ |
| g | 64918 | 108895 | 33506 | $4.41\times10^{-7}$ | $3.57\times10^{-6}$ |
| h | 70224 | 117796 | 36244 | $3.60\times10^{-7}$ | $2.91\times10^{-6}$ |
| i | 71302 | 119603 | 36801 | $3.45\times10^{-7}$ | $2.79\times10^{-6}$ |
| j | 46302 | 77668 | 23898 | $1.06\times10^{-6}$ | $8.60\times10^{-6}$ |
| k | 66831 | 112104 | 34493 | $7.50\times10^{-7}$ | $6.07\times10^{-6}$ |
| l | 65058 | 109130 | 33578 | $8.04\times10^{-7}$ | $6.51\times10^{-6}$ |
| m | 55847 | 93680 | 28824 | $1.20\times10^{-7}$ | $9.70\times10^{-7}$ |

(단위: $R$ [dynes·s/cm⁵], $C$ [cm⁵/dynes])

---

## 2.4 Computational details

- **Solver.** 모든 3차원 해석(정적 유체, prestressing, 맥동 강체벽 유체, 완전 연성 FSI)은 svFSI[cite:zhu2022svfsi]로 수행하였다. 1D ROM 해석은 in-house C++ 솔버로 수행하였다.
- **Hardware.** 3D 해석은 Intel™ Xeon 프로세서(2 소켓, 96 코어)와 257 GB RAM을 갖춘 HPC 클러스터에서 수행. 1D ROM은 Intel™ Core i7-12700K(3.61 GHz)·64 GB RAM 데스크톱에서 수행.
- **Prestressing.** 혈관벽의 prestressed 형상을 얻기 위해, 수렴된 맥동 해로부터 cycle-averaged 입구 압력과 출구 유량을 계산해 정적 유체 해석에 적용하고, 그 결과의 시간평균 벽면 traction을 구조 도메인에 prestressing 해석으로 부과하였다. 이 prestressed 형상으로 완전 연성 FSI와 제안 기법의 **모든 구조 해석을 초기화**한다.
- **Validation runs.** 추가로 맥동 강체벽 3D 유체 해석을 수렴까지 수행하여, 벽 변형이 없는 조건에서 ROM 예측과 고충실도 3D 유체 해를 비교하였다.
- **Representative time instants.** 심장주기 내 5개 대표 시점을 정의: $t_1$ 이완기말(end-diastole), $t_2$ 벽운동 유발 체적변화율 최대, $t_3$ 첨두 수축기(peak systole), $t_4$ 체적변화율 최소, $t_5$ 중기 이완기(mid-diastole). 이상적 LAD 모델에서는 가속기(acceleration phase)가 체적변화율 극값과 일치하지 않아 추가 시점 $t^{*}$를 포함하였다.

---

## 2.5 Validation results

### 2.5.1 Validation metric

제안 기법의 정확도는 **완전 연성(ALE) 과도 3D FSI 해를 ground truth로** 삼아, 동일 고체 메시 상에서 절점별로 von Mises 응력을 비교해 정량화하였다. 각 목표 시점 $t_a$에서 전역 상대 $L_2$-노름 오차를 다음과 같이 정의한다:

$$e_{L2}(t_a) = \frac{\left[\sum_{i=1}^{N}\left(\sigma^{Prop}_{vm,i}(t_a) - \sigma^{FSI}_{vm,i}(t_a)\right)^2\right]^{1/2}}{\left[\sum_{i=1}^{N}\left(\sigma^{FSI}_{vm,i}(t_a)\right)^2\right]^{1/2}} \tag{6}$$

여기서 $N$은 전체 고체 절점 수이다. 국소 절점값이 아닌 기준 FSI 해의 $L_2$-노름으로 정규화함으로써, 절대 응력이 작은 이완기 등에서 상대오차가 인위적으로 부풀려지는 것을 방지한다.

### 2.5.2 Results

(Fig 5 — von Mises stress contour at $t_2, t_3, t_4$: 세 geometry에 대해 proposed vs reference FSI vs absolute error. 원논문 Fig 8.)

세 geometry 모두에서 제안 기법은 기준 FSI의 von Mises 응력장을 **낮은 전역 상대 $L_2$ 오차**로 재현하였다(Table 3). 오차는 이완기말·중기 이완기에서 가장 작고, **급격한 벽 운동(rapid wall motion) 시점에서 상대적으로 커지는** 경향을 보였다 — 강체벽 근사가 compliant FSI 응답에서 가장 크게 벗어나는 구간이기 때문이다.

**Table 3 — Selected time instants and global relative $L_2$-norm error of von Mises stress** (원논문 Table 1)

| Time point | Idealized coronary | | Subject-specific coronary | | Subject-specific AAA | |
|---|---|---|---|---|---|---|
| | Time (s) | Error (%) | Time (s) | Error (%) | Time (s) | Error (%) |
| $t_1$: End-diastole | 0.05 | 0.13 | 0.05 | 1.98 | 0.08 | 0.22 |
| $t_2$: Max vol.-change rate | 0.15 | 0.96 | 0.15 | 3.04 | 0.15 | 1.12 |
| $t_3$: Peak systole | 0.28 | 0.28 | 0.25 | 3.91 | 0.25 | 1.00 |
| $t_4$: Min vol.-change rate | 0.35 | 0.91 | 0.35 | 4.45 | 0.35 | 0.87 |
| $t_5$: Mid-diastole | 0.80 | 0.15 | 0.70 | 1.62 | 0.70 | 0.30 |
| $t^{*}$: Additional phase | 0.45 | 0.17 | – | – | – | – |

→ 오차는 이상적 관상동맥 **< 1%**, 환자 특이 관상동맥 **< 5%**, AAA **< 2%**에 머물렀다.

**계산 비용.** 제안 기법은 완전 연성 3D FSI 대비 세 모델 모두에서 **30배 이상**의 비용 절감을 달성하였다(Table 4). 절감의 핵심은 완전 맥동 3D 해석을 축소차수 혈류 + 정적 3D snapshot 해석으로 대체한 데 있다. ramped-flow 단계는 geometry당 1회 전처리(ROM 계수 식별용)로, 이후 추가 snapshot 평가에서는 반복하지 않는다.

**Table 4 — Computational time (min)** (원논문 Table 2)

| Simulation stage | Idealized coronary | Subject-specific coronary | Subject-specific AAA |
|---|---|---|---|
| Ramped-flow ᵃ | 3.3 | 33 | 5 |
| 1D pulsatile | 0.2 | 3 | 0.9 |
| 3D steady fluid | 1.2 | 15 | 7 |
| 3D steady solid | 8 | 65 | 21 |
| **Total (proposed)** | **12** | **116** | **34** |
| Full 3D FSI | 6866 | 9989 | 1030 |

ᵃ geometry당 1회 전처리 단계(추가 snapshot 평가 시 반복하지 않음).

검증 결과는 본 기법이 완전 과도 FSI를 대체하여 chapter 3의 대규모(1,000-sample) 데이터 생성에 사용될 수 있음을 뒷받침한다.

<!-- ⚠️ 원논문 Fig 8/9의 contour peak absolute-error 값은 본문 서술과 그림 라벨이 일부 불일치(예: AAA peak abs error 본문 6.69E4 vs 그림 7.40E4; AAA stress range 본문 3.09E4 vs 그림 3.18E4). ch2 검증 서술은 깔끔한 Table 3(L2 error)·Table 4(cost)에 근거하며, contour 절대오차 수치를 본문에 인용할 경우 원논문에서 먼저 확정 필요. -->

---

<!-- 다음 단계: 이 한국어 초안 확정 → 영어로 in-place 교체. 이후 ch3_method2.md(메인 민감도 분석)로. -->
<!-- 인용 key는 reference/references.json + references.bib 에 등록됨. \cite{} 매핑은 LaTeX 변환 시 적용. -->
