### Computational FSI simulations: scope and objectives
본 연구의 계산전략은 선행에서 검증된 비용‑효율적 맥동 FSI 파이프라인을 재사용하여 이상적 관상동맥 플라크 표현형 두 가지(저감쇠 플라크, LAP; 석회화 플라크, CP)에 대해 시간해상도가 확보된 대규모 입출력 데이터셋을 생성하고, 이를 바탕으로 취약성지수(VI) 후보를 도출·선별한 뒤 대리모델 및 전역 민감도분석을 수행하는 것이다. 구체적으로 본 연구에서는 맥동성(피로 관점) 응력 지표인 심주기 진폭 ΔPSS를 확보하기 위해 시간해상도 FSI 시뮬레이션을 적용하였고, 이후 GPR 대리모델의 학습 및 Sobol 전역 민감도분석을 통해 형태·혈류역학·재료군의 상대 기여를 정량화하는 것을 목표로 한다; 비용‑효율적 FSI 방법 자체의 제안·검증은 본 연구 범위를 벗어나며 해당 방법은 기존 문헌·도구를 재사용하였다 (참조: boundary condition 명세 및 파이프라인 설정 근거는 (Table 1)). 이 절차는 VI 정의가 stress/strength 비이며 stress는 ΔPSS(피로 관점)로 해석되어야 한다는 논리적 전제를 실증적 데이터 생성으로 뒷받침하기 위해 설계되었다. [cite:claireconway2014]

본 문단 전환: 다음으로 사용한 연속체 방정식과 경계조건·수치 결합 방식을 기술한다.

PDE/constitutive physics and numerical coupling
유체 역학은 비압축성 3D Navier–Stokes 방정식을 뉴턴 점성 유체(ρ = 1060 kg·m⁻3, μ = 0.0035 Pa·s) 가정으로 풀었고, 고체는 유한변형 준정적(large‑deformation quasi‑static) 해를 가정한 거의비압축 Neo‑Hookean (혈관벽·섬유막) 및 선형탄성(핵·석회화) 모델을 사용하였다. 유입 경계조건은 관상동맥 유량 파형(inflow time series)으로 Dirichlet를 적용하고, 심근 관여는 시간의존 elastance 파형(elastance time series)을 이용하여 관련 출구/심근 BC를 구성하였으며 상세한 Windkessel/미세혈관 파라미터는 본문 도표에 요약하였다 (Table 1). 유체-고체 연성은 partitioned strong coupling(고정점 반복) 방식으로 처리하였고, 시간적분은 BDF2를 사용하였다. 본 절에서는 대안적 연속체 모델(예: 이방성 또는 점탄성 모델)을 사용하지 않았음을 명시한다.

본 문단 전환: 다음으로 수치 파라미터 및 검증(시간·메시 독립성) 절차를 서술한다.

Numerical implementation and verification
시간이산화와 수렴 기준은 다음과 같다: BDF2 시간적분, Δt = 0.5 ms, 한 심주기당 1600 time step, 초기 3주기 계산 후 주기적 정상상태(상·하행 PSS 차 <1%)에 도달한 마지막 주기에서 통계량을 산출하였다. 연성 알고리즘의 고정점 반복은 상대 잔차 1e‑5 기준으로 수렴을 요구하였다. 메시 및 시간보폭 독립성 검증을 위해 유체 메시는 약 1.2M cells(최소 Δx ≈ 20 μm), 고체 메시는 약 0.45M 요소를 기준으로 coarse→fine 및 Δt/2 테스트를 수행하였고, peak PSS 변화가 <2%로 확인된 설정을 채택하였다(검증 결과 요약은 Supplementary 자료). 본 검증은 수치적 설정의 일관성을 확보하기 위한 수준이며, 본 연구에서 별도의 실험적 검증을 새로 수행하지는 않았다.

본 문단 전환: 다음으로 기하학·재료모델·샘플링 범위를 기술한다.

Geometry, material models and parameter ranges
기하학적 모델은 두 전형적 표현형으로 구성하였다: LAP(3도메인: 섬유막, 핵, 혈관벽)과 CP(4도메인: 섬유막, 핵, 석회화, 혈관벽). 섬유막 두께는 공간적으로 균일하다고 가정하고 단일 스칼라 변수(fc_av_th)로 변동시켰다. 재료 모델은 혈관벽·섬유막에 거의비압축 Neo‑Hookean(문헌 기반 계수), 핵 및 석회화에는 선형탄성을 적용하였으며 점탄성·이방성은 고려하지 않았다. 재료 파라미터 샘플 범위는 문헌 메타분석을 기반으로 설정하였고(예: E_fc ∈ [0.1, 2.0] MPa, E_vessel ∈ [0.2, 1.5] MPa, E_lipid ∈ [2, 15] kPa, E_cal ∈ [1, 20] GPa), 이러한 범위를 균등분포 LHS로 샘플링하였다. 선택한 이상적 기하학은 대표적 표현형을 모사하되 환자별 전 범위 변동을 완전히 포괄하지는 않는다.

본 문단 전환: 다음으로 입력 설계공간과 케이스 생성 절차를 설명한다.

Input design-space sampling and case generation
입력 설계공간은 형태(morphology), 혈류역학(hemodynamics) 및 재료(materials) 세 군을 포함하여 총 1,000개 파라미터 세트를 생성하였고, 각 행은 하나의 FSI 계산 케이스를 의미한다. 샘플링은 주로 LHS를 포함한 균등 분포 방식으로 수행하여 지정된 범위 내에서 광범위하게 탐색하였으며, 이 설계공간이 모든 생리학적 경우를 완전히 포함하지 않음을 명시한다. 각 설계점에 대해 동일한 시뮬레이션·후처리 파이프라인을 적용하여 일관된 출력 집합을 확보하였다.

본 문단 전환: 다음은 각 케이스에서 계산된 출력 및 VI 후보 생성 방법이다.

Output processing and candidate VI computation
각 FSI 케이스에 대해 표면 기반 peak PSS와 심주기 진폭인 ΔPSS(구면평균)를 계산하였고, 추가로 FFR 유사 지표와 rupture‑location index를 산출하였다. 취약성지수(VI)는 일반 형태 VI = stress/strength으로 정의하였고, stress는 두 가지 관점(peak PSS, ΔPSS), strength는 섬유막 강도 정규화 E_fc^α의 세 시나리오(α 변수 포함)로 설정하여 총 2×3 = 6개의 후보 VI를 생성하였다. 후보 VI들에 대한 표준화된 계산 과정 및 각 출력 정의(예: ΔPSS의 구면평균 산술)는 본 절차에 따라 자동화된 후처리 스크립트로 수행되었다(세부 수식과 처리 흐름은 Supplementary Methods에 기술).

본 문단 전환: 다음은 임상 기준과의 선별 절차를 기술한다.

Clinical sign‑consistency screening of VI candidates
6개 후보 VI는 문헌에서 보고된 7개의 임상적 고위험 플라크 특징과의 부호일치(sign‑consistency)를 기준으로 점수화하여 선별하였다(일치이면 1, 불일치이면 0). 각 VI별 평균 점수와 95% BCa 부트스트랩 신뢰구간은 1,000번 재표집으로 산출하였고, 동률 처리 시 ΔPSS 민감도를 우선하는 규칙을 적용하였다. 이 절차를 통해 VI1(ΔPSS/E_fc^0.5)와 VI2(ΔPSS/E_fc^1.0)이 7개 기준과 모두 일치하는 것으로 판정되어(평균 sign‑consistency = 1.00, 95% BCa CI 0.99–1.00) 최종 분석 대상 VI로 선정되었다(선정 결과 요약은 Table 3).

본 문단 전환: 다음은 대리모델 학습 절차이다.

Gaussian process surrogate training
선정된 VI에 대해 Gaussian process regression(GPR) 대리모델을 학습하였다. 커널은 ARD Matérn 5/2에 white‑noise 항을 추가한 형태를 사용했고, 입력은 z‑score 정규화, 출력(VI)은 표준화하였다. 하이퍼파라미터 최적화는 L‑BFGS‑B를 사용하여 20회 재시작(restarts)으로 수행하였다. 교차검증은 5‑fold CV로 평가하였고, 유효 학습 집합 크기는 LAP 784 유효쌍 및 CP 727 유효쌍이었다; 대리모델의 예측 불확실성은 GPR의 posterior 분산으로 표현하였다. 모델 성능 평가는 5‑fold CV R² 및 RMSE로 보고하였고(요약 수치 및 분포는 Results에 제시), 대리모델은 이후의 전역 민감도분석을 위해 약 1.5만 회 이상의 빠른 반복 평가를 가능케 하는 인프라로 사용되었다.

본 문단 전환: 마지막으로 대리모델 기반 Sobol 분석 절차를 기술한다.

Global sensitivity analysis on the surrogate
대리모델 위에서 전역 민감도분석은 Saltelli 샘플링 프로토콜을 사용하여 약 15,000개의 base 샘플을 생성하고, 이를 통해 Sobol 1차(S1) 및 total(ST) 지수를 그룹(형태/혈류/재료) 및 개별 파라미터 수준에서 추정하였다. 계산된 지수의 수렴성은 재현성 검증(반복실행 시 S1 변화 <0.01 수준)으로 확인하였고, 그룹·파라미터 수준의 결과는 data/sobol/*.csv 파일로 정리하였다; 결과 시각화는 그룹 수준(Fig. 4) 및 개별 파라미터 수준(Fig. 5)으로 제시하였다. 이 분석은 분산 기여도의 정량적 분해를 목적으로 하며, Sobol 지수는 인과성보다는 분산 기여도 측정임을 명확히 한다.
