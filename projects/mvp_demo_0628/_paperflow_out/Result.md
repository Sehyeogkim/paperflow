### Simulation outputs and validation
제작한 맥동성 FSI 시뮬레이션으로부터 시간-해상도의 PSS 장(field of maximum principal stress σ₁ on the fibrous cap surface), 구면(표면) 평균화된 ΔPSS 및 파열위치 지수(rupture-location index)를 추출하였다. 경계조건과 구동파형은 문서화된 프로토콜과 제공된 elastance/inflow 파형을 사용하여 적용했고(문서화 참조) 고체 영역은 2차 사면체 요소, 평균 엘리먼트 크기 0.05 mm, 시간적 적분 간격 Δt = 1 ms, 상대 residual 수렴기준 1e-4로 계산하였다. 메쉬 독립성 검증에서 PSS는 0.1→0.05 mm 간격에서 약 6% 변화, 0.05→0.025 mm 간격에서 약 2% 변화함을 확인하여 채택한 분해능의 이산화 오차가 허용 가능한 수준임을 확인하였다; 이들 출력은 선행 문헌에서 보고된 PSS·FFR·파열위치 경향과 일관되었다(E_sim_validation) [cite:violetacarva2021]. 본 절의 후속 분석에 사용된 모든 VI 후보는 이 시뮬레이션에서 계산된 PSS·ΔPSS·파열위치 지수를 기초로 구성되었다. (지원 문서: 경계조건·BC 문서 및 입력 파형 파일 참조)

다음 문단으로 이동합니다 → R-02

맡은 역할: R-01에서 R-02로 논리적 전환을 지시했으므로 본문 흐름상 순차 연결을 유지합니다.

FSI 출력 및 메쉬 독립성 결과에 관한 추가 세부사항은 Methods에 기술되어 있다(요약된 수치 및 파라미터는 Methods 섹션 참조).

### 
FSI 후처리된 응력 지표(표면 평균 PSS 및 ΔPSS)는 모든 유효 시뮬레이션 케이스에 대해 계산·저장되었다. 여기서 PSS는 섬유막 표면의 최대 주응력 σ₁을 의미하고, ΔPSS는 한 심장주기 내에서 $$\Delta\mathrm{PSS}=\max_{t\in cycle}\sigma_1(t)-\min_{t\in cycle}\sigma_1(t)$$ 로 정의하였다(M_PSS). 표면 평균치는 캡 표면을 등면적 분할한 노드의 단순 산술평균을 사용하였다. 설계공간의 입력 샘플(후속 필터링으로 유효쌍 도출) 전체에 대해 이들 지표가 일관되게 추출되었으며, ΔPSS는 주기성 하중에 의한 진폭성(피로) 효과를 포착하므로 취약성지수 구성의 핵심 스트레스 입력으로 사용되었다(E_sim_validation, W_deltaPSS_fatigue).

다음 문단으로 이동합니다 → R-03

VIs 구성 및 후보 평가에 사용된 PSS·ΔPSS 산출 절차의 구체적 구현은 Methods에 기재되어 있다.

### Vulnerability-index candidate evaluation and selection
두 가지 스트레스 측정치(instantaneous PSS, ΔPSS)와 세 가지 강도 정규화 시나리오(강도 지수 α 선택)를 조합한 총 6개 후보 VI를, 사전 정의한 7개의 임상적 부호(sign/antisign) 기준에 따라 비교 평가하였다(E_VI_candidates_eval). 평가 결과 ΔPSS 기반 후보들 가운데 두 지표만이 모든 7개 기준을 만족하였고, 최종 선택된 지표는 VI1 = ΔPSS / E_{FC}^{0.5} 및 VI2 = ΔPSS / E_{FC}^{1.0}이었다(C2.2). 이 선택 결과는 ΔPSS 기반 VI가 순간 최대 PSS 기반 VI보다 사전 정의된 임상기준과의 부호 일치성에서 우수함을 시사하며(C1.1), strength 정규화 지수 α의 선택이 VI의 거동과 임상기준 부합성에 영향을 미친다는 근거를 제공한다(C2.1). (선택 절차와 후보별 부호 검토 결과는 본문의 해당 표와 설명을 참조)

다음 문단으로 이동합니다 → R-04

후보 VI의 임상적 유효성(환자 결과와의 연관성)은 본 연구의 범위에 포함되지 않음을 명확히 한다.

### Surrogate model performance
최종 선택된 VI들(VI1·VI2)에 대해 유효 시뮬레이션 쌍을 사용하여 Gaussian Process Regression(GPR) 대리모델을 학습하였고, 학습 표본수는 LAP에서 784개, CP에서 727개였다. 5-fold 교차검증 결과(LAP VI1) $R^2=0.93$, RMSE=0.07, 예측구간 포함율 94%; (CP VI1) $R^2=0.90$, RMSE=0.09, 예측구간 포함율 92%로 보고되었다(E_GPR_performance, C4.1). GPR는 Matern 5/2 커널(ARD), 로그 주변우도 최대화로 하이퍼파라미터를 학습하고 입력·출력은 z-점수 정규화하였으며 잡음항 α는 1e-6으로 고정하였다(구현: scikit-learn 1.3.0). 대리모델의 캘리브레이션 및 교차검증 성능이 양호하여 이후의 Sobol 전역 민감도 분석을 위한 근거가 마련되었다(단, 대리모델은 근사임을 인정함).

다음 문단으로 이동합니다 → R-05

대리모델을 이용한 대규모 Monte Carlo 기반 Sobol 평가는 계산 비용을 크게 절감하여 실용적 분석을 가능하게 했다(세부 수치는 Methods 및 성능 표 참조).

### Grouped Sobol sensitivity (Material vs Hemodynamics vs Morphology)
그룹화된 Sobol 전역 민감도 분석 결과, 네 가지 경우(표현형 LAP·CP × 선택 VI1·VI2) 모두에서 Material 그룹의 1차 지수(S1)와 전차 지수(ST)가 Hemodynamics 및 Morphology 그룹보다 컸다(E_Sobol_grouped, C3.1). 예를 들어 LAP VI2 및 CP VI2에서 Material의 S1은 각각 0.7507·0.7968(반올림) 수준이며(LAP VI2 S1=0.7507, CP VI2 S1=0.7968), 해당 ST 값도 유사하게 Material 우위를 나타낸다(데이터는 (Fig)·(Table)에 요약됨). 전체적으로 그룹별 분산 기여 순위는 Material > Hemodynamics > Morphology로 일관되었고, 이는 선택된 ΔPSS 기반 VI들에 대한 출력 분산이 주로 재료물성 변수에 의해 설명됨을 의미한다(C3).

다음 문단으로 이동합니다 → R-06

그룹별 지수는 분산 기여도를 정량화하며 인과성을 직접 증명하지 않음을 유의한다.

### Individual-parameter Sobol indices and top drivers
개별 입력 변수 수준의 Sobol 1차(S1) 및 전차(ST) 지수 분석에서 모든 경우에 걸쳐 상위 결정인자로 일관되게 확인된 네 변수는 vessel wall Young's modulus ($E_{vessel}$), fibrous cap Young's modulus ($E_{fc}$), systolic blood pressure ($P_{sys}$, SBP) 및 pulse pressure (PP)였다(E_Sobol_individual, C3.2). 예컨대 LAP VI2에서 $E_{fc}$의 S1=0.5503, $E_{vessel}$의 S1=0.1459, SBP의 S1=0.0786, PP의 S1=0.0303(반올림)로 나타났고, CP VI2에서는 $E_{fc}$의 S1=0.6272, $E_{vessel}$의 S1=0.1287, SBP의 S1=0.0955, PP의 S1=0.0308 등으로 보고되었다(개별 수치는 Table·Fig에 정리). 이 결과는 어떤 개별 입력들이 Material·Hemo 그룹 내에서 분산을 주도하는지를 명확히 보여주며, 상위 네 변수는 선택된 ΔPSS 기반 VI의 변동을 가장 강하게 설명한다. 단, 순위는 모델 가정(이상화된 기하학·선형 탄성 등)과 설계공간에 의존하므로 in vivo 인과성을 단정하지 않는다.
