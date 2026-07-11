### Validation of simulation outputs
본 연구의 맥동성 FSI 파이프라인은 관상동맥 입구 유량 및 심근 elastance 시계열을 경계조건으로 사용하여 BDF2 시간적분(Δt=0.5 ms, 1600 step/주기)으로 3주기 이후 주기적 정상상태에서 출력 통계를 산출하였다(M1). 생성된 시뮬레이션 출력은 기존 문헌에서 보고된 PSS·FFR·파열위치 경향과 일관되었고(대표 필드맵·요약 통계는 보충도표 S2에 제시), ΔPSS(심주기 진폭, fatigue 관점)가 단일 시점 peak PSS 보다 임상 고위험 특징과의 정렬성이 더 높았으며(후처리 비교 분석), 이 결과는 ΔPSS를 stress로 해석하는 근거를 제공한다(E_deltaPSS_vs_peakPSS; W1). 또한 본 연구에서 학습한 Gaussian process surrogate는 5-fold 교차검증에서 LAP에 대해 R²≈0.93, CP에 대해 R²≈0.90, RMSE≈0.12·σ(VI)를 보였고 예측 불확실성은 GPR의 posterior 분산으로 표현하여 후속 민감도 분석과 합성 진단평가에 안정적으로 활용되었다(E_gpr_performance; M2). 본 절의 비교·검증은 시뮬레이션의 face validity와 다운스트림 대리모델 기반 분석의 해석가능성을 뒷받침하되, 환자별 예후 예측 또는 cost‑effective FSI 기법 자체의 신규 검증을 주장하지는 않는다.

후보 취약성지수(VI) 선별 결과
6개의 후보 VI(응력: peak PSS, ΔPSS × 강도 정규화 E_fc^α의 α 시나리오 3종)를 7개의 임상적 고위험 플라크 기준에 대해 부호일치(sign‑consistency; 1/0) 방식으로 평가한 결과, ΔPSS 기반의 정규화 형태인 VI1=ΔPSS/E_fc^{0.5} 및 VI2=ΔPSS/E_fc^{1.0}만이 7개 기준을 모두 만족하는 것으로 확인되었다(E_VI_candidates_screening; M4). 두 지수의 평균 부호일치 점수는 1.00이며 95% BCa 부트스트랩 신뢰구간은 0.99–1.00으로 보고되었다(표: 후보 VI 선별 결과, F_VI_selection_table). 이 결과는 stress-only 지표보다 섬유막 강도로 정규화한 stress/strength 비가 임상적으로 확립된 고위험 소견과의 일관성을 높인다는 주장(C2.1)을 경험적으로 지지한다(정규화 지수의 지수 α는 VI의 물성 민감도를 조절함).

대리모델 기반 합성 진단성능
선택된 VI에 대해 GPR surrogate를 이용해 합성 고위험 레이블(7기준 중 ≥5 충족)에 대한 분리능을 평가한 결과, VI2(ΔPSS/E_fc)로 계산한 경우 ROC AUC≈0.84(95% CI 0.80–0.88)이며 Youden 최적점에서 민감도≈0.78, 특이도≈0.76을 보였다(대리모델 예측 및 ROC 곡선: F_ROC_VI2). 이러한 진단성능 평가는 대리모델의 교차검증 성능(R²·RMSE)과 함께 제시되었으며(E_gpr_performance), 여기서 보고된 분리능은 합성 라벨 기반의 평가에 해당하고 실제 환자 데이터에서의 임상적 유효성이나 예후 검증을 의미하지 않는다.

Global sensitivity: material dominance
Saltelli 샘플링 기반 Sobol 전역 민감도 분석(대리모델上, 약 15,000 base 샘플)은 그룹 수준에서 재료물성(Material) 그룹이 VI 변동성의 가장 큰 기여를 함을 밝혔다(Material > Hemodynamics > Morphology). 특히 LAP·VI2의 그룹 1차 지수 S1은 0.7507로 재료군이 지배적이었고, CP에서도 재료군 S1≈0.7968으로 유사한 우세가 관찰되었다. 이러한 그룹 수준 결과는 Sobol 이론에 따라 입력 그룹의 주요 효과 기여를 정량화한 것이며(W3), 본 분석은 두 전형적 플라크 표현형(LAP, CP)에 대한 범위 내에서의 분산 귀속을 보고한다.

개별 파라미터 수준의 영향도 순위
개별 파라미터 수준 Sobol 결과는 E_fc와 E_vessel이 가장 큰 1차 기여를 보였고, 그 다음으로 SBP(수축기압) 및 PP(맥압)가 주요 결정인자로 확인되었다. 예를 들어 LAP·VI2에서 E_fc의 1차 지수 S1≈0.5503이고 E_vessel S1≈0.1459, SBP S1≈0.0786, PP S1≈0.0303로 보고되어 상위 네 인자는 E_vessel·E_fc·SBP·PP 순으로 기여함을 나타낸다(E_individual_parameters). 이 결과는 재료물성 중 특히 섬유막 탄성(E_fc)과 혈관벽 탄성(E_vessel)이 VI 변동을 주도함을 정량적으로 보여준다(단, 본 순위는 본 연구의 설계공간 내에서의 결과이며 다른 기하학적 스펙트럼에 일반화되는 것은 추가 검증이 필요하다).

Interpretation of stress metric and strength normalization
본 연구의 비교분석은 ΔPSS(심주기 진폭)를 stress로 선택하고 VI를 stress/strength로 정의하는 것이 임상적으로 더 적합함을 시사한다(C1, C1.1, W1). ΔPSS 기반 VIs가 peak PSS 기반 지표보다 7개 임상기준과의 부호일치 및 선별 성능에서 우수했고(E_deltaPSS_vs_peakPSS, E1), 섬유막 강도 E_fc를 분모에 포함하는 정규화(E_fc^α)는 VI의 행동을 실질적으로 변경하여 임상기준과의 일관성을 향상시켰다(C2, C2.1). α의 선택(예: 0.5 vs 1.0)은 VI의 재료 민감도를 조절하므로 정규화 형태는 해석적·임상적 맥락에서 신중히 선택되어야 하며 본 연구의 α 값들이 생물학적 스케일링을 전부 대표한다고 주장하지는 않는다. 본 절의 근거는 VI 후보 선별표(F_VI_selection_table)와 그룹별 Sobol 결과에 근거한다.
