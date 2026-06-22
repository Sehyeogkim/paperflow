# Chapter 3 — Parametric Analysis Framework for Plaque Rupture Risk

(Fig — Workflow overview: 3 stages ① dataset generation ② VI selection ③ surrogate-based global sensitivity analysis)

<!-- 초안 언어: 한국어 먼저 → 확정 후 같은 파일에서 영어로 in-place 교체 (CLAUDE.md house rule).
     실수치 출처: 본인 학위논문 PDF(20244152_sehyeog.pdf) Ch.2 Methods. [n] = 학위논문 인용번호 →
     reference-hunter가 references.json/bib로 정규화. 〔TODO〕 = PDF에도 없어 본인 확인이 필요한 값.
     대응: figure_flow Method2 / outline chapter3. ch2=FSI 엔진(도구), 이 장=그 위의 4-stage 분석. -->

본 장에서는 관상동맥 플라크의 파열 위험을 형태학적·혈류역학적·재료적 인자에 대해 체계적으로 규명하기 위한 **3단계 파라메트릭 분석 프레임워크**를 제시한다. 분석은 (1) Chapter 2에서 검증한 비용효율적 맥동성 FSI를 forward solver로 사용하여, 플라크 종류별(LAP 1,000 / CP 1,300) 입출력 데이터셋을 생성하고(Stage 1), (2) 응력(stress)과 강도(strength)의 비로 정의되는 파열 취약성 지표(vulnerability index, VI) 후보를 형성한 뒤 임상 기준에 적합한 지표들을 선별하며(Stage 2), (3) 선정된 VI에 대해 가우시안 과정 회귀(Gaussian process regression, GPR) 대리모델을 학습하고, 소볼(Sobol) 분산 기반 전역 민감도 분석으로 각 인자군의 기여도를 정량화하는 순서로 진행된다. 전체 흐름은 Fig (workflow overview)에 정리하였다.

---

## 3.1 Data generation  [Stage 1]

Fig 3에 보이듯이, 비용효율 FSI를 이용해 두 가지 플라크 표현형(phenotype)에 대한 입출력 데이터셋을 각각 구축하였다. 대상은 **이상화된 관상동맥 모델(idealized coronary artery model)**이며, 표현형은 서로 다른 구성거동(constitutive behavior)을 보존하기 위해 분리하여 모델링하였다:

- **LAP (low-attenuation plaque)**: 혈관벽, 섬유막(fibrous cap, FC), 지질핵(lipid core)의 **3개 고체 도메인**.
- **CP (calcified plaque)**: 위 3개에 석회화(calcification) 도메인을 더한 **4개 고체 도메인**.

기본(고정) 형상은 원통형 관상동맥 분절로, 길이 $10$ cm, 내강 반경 $r_\text{ref}=0.1$ cm, 벽 두께 $t_\text{wall}=0.02$ cm로 고정하였다.

형태학적 입력 변수는 비침습적이고 범용성이 높은 관상동맥 CT 혈관조영(CCTA)에서 도출하는 것을 전제로 하여, 향후 임상 적용으로의 확장이 용이하도록 설계하였다. 다만 섬유막 두께는 CCTA로 분해되지 않고 OCT 등 침습 영상으로만 측정 가능하므로, 공간적으로 균일하다고 가정하여 단일 스칼라로 환원하고 모든 샘플에서 $t_\text{FC}=100\ \mu\text{m}$로 고정하였다. 이 값은 파열 취약 플라크의 in vivo OCT 측정과 부합한다 \cite{yonetsu2011, virmani2000}. 이로써 침습 영상이 필요한 유일한 형태 변수를 제거하여, 전체 입력공간을 CCTA만으로 구성할 수 있는 단독 워크플로우와의 정합성을 유지한다.

(Fig 3 — Idealized coronary model geometry + morphological parameters: (a) LAP 3-domain vs CP 4-domain, (b) 형태 변수 annotation. 형상 기호 $r_\text{ref}$, $t_\text{wall}$, $t_\text{FC}$를 함께 표기.)

### 3.1.1 Input parameters

입력 변수는 **형태학적·혈류역학적·재료적** 세 인자군으로 구성되며, 변수별 기호·단위·범위·출처는 Table 1에 정리한다.

- **형태학적(morphological) 변수**
  - 협착도 $DS$ [%]: 최소내강 지름 기준 협착률, $DS=(1-r_\text{min}/r_\text{ref})\times100$.
  - 병변 길이 $L_\text{lesion}$ [cm]: 중심선 방향 병변 길이.
  - 내강 축방향 왜도 $\gamma_z$ [–]: 병변 중점 대비 최소내강면적(MLA) 위치의 정규화 축방향 편이로, $z_\text{MLA}=z_\text{lesion}\,\gamma_z$로 정의한다. $\gamma_z>0$이면 distal, $<0$이면 proximal 쪽 치우침.
  - 양성 재형성 지수 $PI$ [–]: 병변부와 기준부의 내강 단면적 비, $PI=A_\text{inflated}/A_\text{ref}=r_\text{max}^2/r_\text{ref}^2$. $PI>1$이면 외향(양성) 재형성.
  - 지질핵 호 각도 $\theta_\text{lipid}$ [°]: 최대 지질부담 단면에서의 원주방향 각도 범위.
  - 지질 길이비 $r_\text{lipid}$ [–]: $r_\text{lipid}=L_\text{lipid}/L_\text{lesion}$.
  - (CP 전용) 석회화 분율 $f_\text{calc}$ [–]: lipid core 부피 대비 석회화 부피 분율로, 석회화의 양을 나타내는 **민감도 분석 입력**이다. (임상 부피 $V_\text{calc}$은 lipid core 내부 구속으로 독립 샘플이 불가능하여 입력에서 제외하고 validation에만 사용한다 — 생성 방식은 §3.1.2, 세부는 Table 1 주석 참조.)
- **혈류역학적(hemodynamic) 변수**
  - 수축기압 $P_\text{sys}$ [mmHg], 맥압 $\Delta P=P_\text{sys}-P_\text{dia}$ [mmHg], 이완기 감쇠비 $\tau$ [–](distal RCR Windkessel로 결정).
  - LHS 시 비생리적 조합 배제를 위해 $P_\text{dia}=P_\text{sys}-\Delta P>40$ mmHg 제약을 부과.
- **재료적(material) 변수**: 혈관벽 $E_\text{vessel}$, 섬유막 $E_\text{FC}$, 지질핵 $E_\text{lipid}$, (CP 전용) 석회화 $E_\text{calc}$의 영률. CGS 단위(dyn/cm²)로 부여한다. 관상동맥은 심장주기 동안 작은 변형 영역(약 3–5% radial wall strain)에서 거동하므로 〔TODO: ref〕, 모든 조직을 **선형탄성·등방성**으로 가정하는 것이 타당하다.

입력공간은 **라틴 하이퍼큐브 샘플링(LHS)**으로 채웠다. LAP는 12개 변수에 대해 1,000개 입력벡터를, CP는 18개 변수에 대해 1,300개 입력벡터를 추출하였다. CP의 18개는 Table1에 정의된 분석 입력 14개에, 다양한 석회화 형상을 묘사하기 위한 **석회화 생성 파라미터 4개**(위치·이방성 및 표면 버퍼; §3.1.2)를 더한 것이다. 이 추가 4개는 데이터 생성 시에만 변동시키고, 이들을 입력에 포함해 학습한 surrogate에서의 별도 Sobol 분석(§3.3.2)에서 기여가 무시할 수준(전차지수 ≈ 0)으로 확인되어, **최종 민감도 분석에서는 제외하고 $f_\text{calc}$·$E_\text{calc}$만 포함한 14개**를 입력으로 정의하였다.

(Table 1 — Input variables, symbols, units, sampling ranges, references)

| Group | Variable | Symbol | Unit | Range [min, max] | Ref |
|---|---|---|---|---|---|
| Morphological | Degree of stenosis | $DS$ | % | [25, 75] | \cite{stone2011prospect} |
| | Lesion length | $L_\text{lesion}$ | cm | [1.0, 3.0] | \cite{brosh2005} |
| | Lumen axial skewness | $\gamma_z$ | – | [−0.5, 0.5] | \cite{wang2015ivus} |
| | Positive remodeling index | $PI$ | – | [0.9, 1.2] | \cite{schoenhagen2000} |
| | Lipid arc angle | $\theta_\text{lipid}$ | ° | [120, 270] | \cite{xing2017} |
| | Lipid length ratio | $r_\text{lipid}$ | – | [0.5, 0.8] | \cite{tanaka2009} |
| | Calcified fraction (CP) | $f_\text{calc}$ | – | [0.10, 0.80] | \cite{mintz1995} |
| Hemodynamic | Systolic pressure | $P_\text{sys}$ | mmHg | [100, 170] | \cite{whelton2018} |
| | Pulse pressure | $\Delta P$ | mmHg | [35, 80] | \cite{franklin1999} |
| | Decay ratio | $\tau$ | – | [0.01, 0.50] | \cite{kim2010coronary, sankaran2016} |
| Material | Vessel-wall modulus | $E_\text{vessel}$ | dyn/cm² | [1×10⁶, 1.4×10⁷] | \cite{holzapfel2005} |
| | Fibrous-cap modulus | $E_\text{FC}$ | dyn/cm² | [4×10⁶, 2.3×10⁷] | \cite{loree1994static} |
| | Lipid-core modulus | $E_\text{lipid}$ | dyn/cm² | [1×10⁴, 1×10⁶] | \cite{loree1994lipid} |
| | Calcification modulus (CP) | $E_\text{calc}$ | dyn/cm² | [7×10⁹, 2.5×10¹¹] | \cite{ebenstein2009} |

*LHS 제약: $P_\text{dia}=P_\text{sys}-\Delta P>40$ mmHg.*


### 3.1.2 Geometry construction and meshing

각 LHS 샘플마다 **Autodesk Inventor** [30]로 파라메트릭 CAD 모델을 프로그래밍 방식으로 생성하고, 유체·고체 유한요소 메시로 분리 이산화하였다.

**석회화 형상 생성(CP 전용).** 석회화는 단순 형상 primitive가 아니라 lipid core 내부에서 **seed 기반 region-growing 알고리즘**으로 생성하여 불규칙한 임상적 형태를 재현하였다(전 과정은 Appendix A). 생성된 석회화에서 측정한 부피 $V_\text{calc}$은 입력이 아니라 lipid core 구속으로 독립 샘플이 불가능한 derived 양이며, 그 분포를 임상 보고 범위 [21]와 대조해 샘플링의 생리학적 타당성을 검증(validation)하는 데 사용한다(CP 전반 $V_\text{calc}\in[5.14\times10^{-4},\,2.81\times10^{-2}]$ cm³).

- **고체 도메인**: 병변 부근 box-meshing 전략의 **2차 사면체(quadratic tetrahedral)** 요소, 샘플당 약 $3\text{–}4\times10^6$개.
- **유체 도메인**: **1차 사면체(linear tetrahedral)** 요소 약 $5.5\times10^6$개, 내강벽에서 **3겹 프리즘 경계층**을 inflation하여 근벽 속도구배(WSS 추출에 필요)를 해상.

메시 독립성은 병변 영역 box-meshing의 대표 요소 크기를 $0.05$, $0.04$, $0.03$ cm로 변화시키며(고체 도메인 전체 요소 수 약 $2.3$, $3.2$, $4.9\times10^6$) 확인하였다. 대표 케이스(case 0)의 수축기 섬유막 최대 주응력(maximum principal stress; PSS에 해당)을 수렴 지표로 삼은 결과 각각 $1.1$, $1.0$, $1.0\times10^6$ dyn/cm²로, $0.04$ cm와 $0.03$ cm가 사실상 동일하였다(상대 변화 < 1%). 이에 정확도와 계산비용을 절충하여 병변 영역 대표 요소 크기를 **$0.04$ cm**로 채택하였다.

### 3.1.3 Boundary conditions

(Fig 4 — Boundary conditions: fluid + solid)

- **유체 경계조건**: 입구에는 생리학적 압력파형 $P_\text{in}(t)$를 부과한다. 고정된 관상동맥 유입파형 $Q(t)$에 3-요소 Windkessel(RCR) 모델 [cite: westerhof2009windkessel]을 적합하되, 관상동맥 비 $R_p/R_d=1/10$을 고정하고 나머지 파라미터($P_d$, $R_d$, $C=\tau/R_d$)를 수렴된 last-cycle 압력의 최대·최소가 샘플링된 $P_\text{sys}$, $P_\text{dia}=P_\text{sys}-\Delta P$에 맞도록 least-squares로 적합하였다. 따라서 입구 파형의 진폭·형상은 세 혈류역학 변수 $P_\text{sys}$, $\Delta P$, $\tau$로 **완전히 결정**된다(적합 절차는 Appendix B). 각 출구에는 3D 영역에 하류 lumped-parameter 모델을 결합하는 유출 경계조건 [cite: vignonclementel2006] 형식의 **관상동맥 미세혈관 경계조건**을 부과하였다. 관상동맥 유동의 이완기 우세성을 재현하기 위해 출구 모델은 수축기 심근 수축에 의한 혈관 압박을 **심근압 $P_\text{myo}(t)$** 항으로 포함하며 [cite: kim2010coronary], $P_\text{myo}(t)$는 시간가변 elastance 기반 lumped 심장 모델 [cite: suga1973elastance]로 산출한다(Appendix B). 대표 입구 파형·출구 BC 모식도는 Fig 4에 제시한다.
- **고체 경계조건**: chapter2 에서 명시된, Phase 2 정식화와 일관되게, 3D CFD에서 복원한 벽면 압력장을 다중도메인 고체 메시의 **내벽(lumen-side)에 surface traction**으로 부과한다. 혈관 분절 양 끝단(입·출구 cap 단면)은 **고정단(fixed support)**으로 구속한다.

### 3.1.4 Output parameters

각 LHS 샘플에 대해 비용효율 FSI를 수축기 정점($t_\text{sys}$)과 이완기말($t_\text{dia}$) 2회 호출하여 두 시점의 응력장을 얻고, **각 노드에서 최대 주응력(maximum principal stress) $\sigma$**를 산출하였다. 이로부터 두 응력 지표를 노드별로 정의한다:

- **PSS (plaque structural stress)** $=\sigma(t_\text{sys})$: 수축기 최대 주응력 — 단조 파단(monotonic fracture) 시나리오.
- **ΔPSS** $=\sigma(t_\text{sys})-\sigma(t_\text{dia})$: 동일 노드에서 두 시점 최대 주응력의 차, 즉 맥동 응력 진폭 — **피로 파괴(fatigue) 시나리오**.

두 지표는 섬유막 노드 전체에서 노드별로 계산하며, 단일노드 노이즈를 줄이기 위해 최대하중 노드 중심의 반경 $r=0.01$ cm 구면 이웃에서 공간 평균(sphere-averaging)한다 [34].


### 3.1.5 Computational details

- **메시 생성**: Gmsh [31] + VMTK [32], SimVascular 파이프라인 [33] 통합 환경.
- **Phase 1 (1D 맥동 ROM)**: in-house C++ 코드.
- **Phase 2 (3D 유체)**: SimVascular의 비압축성 Navier–Stokes 솔버 [33]. **Phase 2 (3D 구조)**: ANSYS Mechanical (ANSYS Inc., Canonsburg, PA, USA). 모든 3D 해석은 안정화 유한요소 정식화 사용.
- **하드웨어**: 3D 해석 — Intel Xeon 96 cores(2 sockets)/257 GB RAM HPC 클러스터. 1D ROM — Intel Core i7-12700K 3.61 GHz/64 GB 데스크톱.

---

## 3.2 Vulnerability Index formulation and selection  [Stage 2]

파열은 응력이 강도를 초과할 때 발생하므로, 취약성 지표를 **응력과 강도의 비**로 정의한다: $\text{VI}=\text{stress}/\text{strength}$ [cite: Corti2022]. 중요한 점은 각 input parameter 입력변수 별로, 계산된 주응력이 다르지만, strength 또한 다르다는 점이다. 

### 3.2.1 VI formulation

응력은 §3.1.4의 PSS·ΔPSS 2종을 사용한다. 한편 섬유막 강도를 직접 모델링·정량화한 선행연구는 없어, 세 가지 파열 시나리오 — (i) 고정 극한응력, (ii) 에너지밀도, (iii) 고정 극한변형률 — 를 선형탄성 가정과 결합하여 강도를 단일 지수 $\alpha$로 매개화하였다:

$$\text{strength} \propto E_\text{FC}^{\alpha}, \qquad \alpha \in \{0.0,\ 0.5,\ 1.0\}$$

각 지수는 고전 파괴이론에 대응한다:

- $\alpha = 0$ — **Rankine(최대응력, maximum-stress)** [37].
- $\alpha = 0.5$ — **Beltrami(에너지밀도, energy-density)** [38].
- $\alpha = 1$ — **St. Venant(최대변형률, maximum-strain)** [39].

응력 2종과 강도 지수 3종을 조합하여 **6개 VI 후보**를 정의한다:

$$\text{VI}(\sigma,\alpha) = \frac{\sigma}{E_\text{FC}^{\alpha}}, \quad \sigma\in\{\text{PSS},\Delta\text{PSS}\},\ \alpha\in\{0.0,0.5,1.0\}$$

각 케이스에서 섬유막 전 노드에 대해 VI를 계산하고, 그 **최댓값을 해당 케이스의 대표 VI**로 사용한다(강도가 노드별 상수이므로 대표 위치는 응력장이 결정하며, 이 위치를 §3.1.4의 파열 위치 지수로 활용한다).
### 3.2.2 VI Candidate Selection (seven-criterion rubric)

6개 후보 VI를 임상적으로 확립된 고위험 플라크 특징 **7가지 기준**(Table 2)으로 선별하였다. 각 기준은 케이스별로 추출한 **플라크 feature**(입력 변수 또는 시뮬레이션에서 계산된 양)와 VI가 가져야 할 상관 방향을 임상 근거로부터 *a priori*로 고정한 것이다. 예를 들어 기준 1은 "섬유막 영률이 낮을수록 고위험"이므로 VI는 $E_\text{FC}$와 **음의 상관**이어야 한다. 각 (후보, 기준) 쌍에 대해 해당 feature와 VI의 **Spearman 순위상관 부호**를 계산하여, 기대 방향과 일치하면 compliant(◯), 아니면 ×로 분류하였다(부호 판정이 목적이므로 비선형 단조 관계에 강건한 순위상관 사용). **7개 기준을 모두 만족하는 후보만 물리적으로 admissible**로 본다.

기준 1–6은 해당 feature가 주 LHS 데이터셋에서 변동하므로 그대로 평가하였다. 다만 기준 7(섬유막 두께)은 본 시뮬레이션에서 $t_\text{FC}$를 고정하였으므로 주 데이터셋으로는 평가할 수 없다. 이를 위해 나머지 입력을 모두 평균값에 고정하고 $t_\text{FC}$와 $E_\text{FC}$만 변화시킨 **별도 15개 시뮬레이션**(LAP 기준; $E_\text{FC}\in\{12,16,20\}$ MPa × $t_\text{FC}\in\{40,80,120,160,200\}\ \mu\text{m}$)을 수행하여 이 데이터에서 기준 7을 평가하였다. 이 추가 시뮬레이션의 목적은 후보 VI가 임상적으로 잘 알려진 이 특징(얇은 섬유막일수록 고위험)을 재현하는지 확인하는 데 있다.

<!-- 〔확인 1〕 상관계수는 방향판정 목적이라 Spearman으로 작성 — 실제 Pearson을 썼다면 교체.
     〔확인 2〕 15-sim의 E_FC={12,16,20} MPa가 Table 1의 E_FC 범위([4×10⁶, 2.3×10⁷] dyn/cm² ≈ 0.4–2.3 MPa)와
     ~10× 어긋남 → 단위/값 정합 확인 필요. -->


(Table 2 — Seven established high-risk plaque features)

| # | Clinical fact | Model feature (per case) | Simulation data | Ref |
|---|---|---|---|---|
| 1 | Soft plaque substrate | Low $E_\text{lipid}$, | LAP | [10] |
| 2 | Less calcified plaque (CP only) | Low $f_\text{calc}$ | CP | [43] |
| 3 | Large lipid arc angle | Large $\theta_\text{lipid}$ | LAP | [41] |
| 4 | Large plaque burden | High lipid-core volume | LAP | [15] |
| 5 | (delta FFR 전문 용어 찾아서 넣기) gradient | High ΔFFR | LAP | [42] |
| 6 | Collagen-deficient fibrous cap | Low $E_\text{FC}$ | LAP | [40] |
| 7 | Thin fibrous cap | Low fibrous-cap thickness | * | [13] |
*: additional data to testify

이 rubric으로 **admissible로 판정된 지표만을** 이후 surrogate 학습·민감도 분석의 대상으로 삼는다. 6개 후보 전체의 후보별·기준별 통과/탈락 매트릭스와 최종 채택 지표는 **Results §3.1(Fig. 6)에서 제시한다.**

---

## 3.3 Surrogate-based global sensitivity analysis  [Stage 3]

소볼 민감도 분석은 표현형당 1만 회 이상의 모델 평가를 요구하여 비용효율 FSI로도 직접 수행할 수 없다. 따라서 본 stage는 먼저 입력→VI 사상을 학습하는 GPR 대리모델(surrogate)을 구축하고(3.3.1), 그 surrogate 위에서 소볼 분산 기반 전역 민감도 분석을 수행한다(3.3.2). 즉 surrogate는 분석을 가능케 하는 인프라이고, 전역 민감도 정량화가 이 stage의 목적이다.

### 3.3.1 GPR surrogate model

각 VI 후보·표현형마다 입력벡터($d=12$ LAP, $d=14$ CP)를 스칼라 VI로 사상하는 **GPR 대리모델**을 개별 학습하였다. LAP 1,000 / CP 1,300개 LHS 샘플 중 일부는 boolean operation problem, 메시 품질 문제나 비물리적 입력 조합으로 수렴에 실패하여, 유효 샘플은 **LAP 784/1,000, CP 1075/1,300**이었다.

모델은 scikit-learn `GaussianProcessRegressor` [35]로 구현하고, **ARD(Automatic Relevance Determination)** [36] 적용 제곱지수(squared-exponential) 커널을 사용하였다. ARD는 입력 차원마다 독립 lengthscale을 부여하여 정식 Sobol 분석 전 입력 중요도의 1차 단서를 제공한다. 커널 하이퍼파라미터는 주변 로그우도(marginal log-likelihood) 최대화로 결정하였다. 정확도는 leave-one-out 교차검증 결정계수($R^2_\text{LOO}$)로 보고하며, 두 표현형 모두 $R^2_\text{LOO}>0.94$으로 높은 예측 정확도를 보였다.

### 3.3.2 Sobol variance-based indices

학습된 GPR(유효 LAP 784 / CP 1,075)에 대해 **소볼(Sobol) 분산 기반 전역 민감도 분석**을 수행하였다 [44]. 입력 $X_i$의 **1차 지수**

$$S_i = \frac{\text{Var}_{X_i}\!\left[\mathbb{E}_{X_{\sim i}}(Y\mid X_i)\right]}{\text{Var}(Y)}$$

는 $X_i$ 단독 기여를, **전차 지수**

$$S_{Ti} = \frac{\mathbb{E}_{X_{\sim i}}\!\left[\text{Var}_{X_i}(Y\mid X_{\sim i})\right]}{\text{Var}(Y)}$$

는 상호작용을 포함한 총기여를 정량화한다. Saltelli 준난수 표본추출로 1·전차 지수를 추정하였고(2차 지수는 계산하지 않음), 표현형당 기저표본 $N=1{,}024$로 LAP($d=12$)는 $N(d+2)=14{,}336$, CP($d=14$)는 $16{,}384$회 surrogate 평가를 수행하였다 [45].

개별 변수 지수에 더해, 세 인자군 $G\in\{\text{형태, 재료, 혈류역학}\}$의 **군 단위(group) Sobol 지수**를 계산하였다. 각 입력을 소속 인자군에 배정한 뒤, 군 전체를 하나의 묶음 변수 $X_G$로 취급하는 grouped-Sobol 추정을 동일한 Saltelli 표본에 적용하였다:

$$S_G = \frac{\text{Var}_{X_G}\!\left[\mathbb{E}_{X_{\sim G}}(Y\mid X_G)\right]}{\text{Var}(Y)}, \qquad S_{TG} = \frac{\mathbb{E}_{X_{\sim G}}\!\left[\text{Var}_{X_G}(Y\mid X_{\sim G})\right]}{\text{Var}(Y)}.$$

군의 1차 지수 $S_G$는 군 내 변수를 **함께** 변화시켰을 때의 분산 기여를, 전차 지수 $S_{TG}$는 타 군과의 상호작용을 포함한 총 기여를 정량화한다. 이 군 지수는 개별 지수의 단순 합이 아니라 **군 내 변수 간 상호작용까지 올바르게 반영**한다.


