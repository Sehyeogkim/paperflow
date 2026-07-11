### Interpretation of ΔPSS-based vulnerability indices
본 연구에서는 파열위험지표를 stress/strength 비로 정의하고, stress로서 심장주기 내 진폭을 나타내는 ΔPSS를 채택하는 것이 임상적 기준과 일관된 거동을 보인다고 결론지었다. FSI 시뮬레이션에서 도출한 시간해석 PSS 필드로부터 ΔPSS = max_{t∈cycle} σ₁(t) − min_{t∈cycle} σ₁(t)를 계산하여 VI 후보를 구성한 결과(6개 후보 비교), ΔPSS 기반 후보들이 순간 최대 PSS 기반 후보들보다 7개 임상 sign 기준의 부호 일치성 및 선택 기준을 더 잘 만족하였다(E_VI_candidates_eval; M_PSS). 이는 ΔPSS가 주기적 진폭·피로 누적 효과를 반영하므로 파열모사에서 더 관련성이 높기 때문이며(W_deltaPSS_fatigue), 따라서 ΔPSS의 정당성을 확보하려면 시간 해상도(본 연구: Δt = 1 ms)와 맥동성 FSI 처리가 필수적임을 시뮬레이션 검증 결과(E_sim_validation)가 뒷받침한다. 단, 본 결과는 본 연구의 이상화된 표현형과 시뮬레이션 조건에 기반한 것이며 환자 결과에 대한 직접적 예측이나 즉시적 임상 적용을 주장하지 않는다.

ΔPSS 기반 VIs의 우수성에 대한 근거 요약
후보 VI 6종(응력: PSS·ΔPSS × 정규화 지수 α 3종)에 대한 7개 임상 sign 기준 평가 결과, ΔPSS를 stress로 사용한 후보들이 전체 기준의 부호 일치성에서 PSS 기반 후보들을 능가했고, 최종적으로 VI1과 VI2(둘 다 ΔPSS 기반)가 모든 기준을 충족하였다(E_VI_candidates_eval, M_VI_selection). 이 선별 절차는 FSI에서 산출한 표면 평균 PSS/ΔPSS를 입력으로 사용한 일관된 비교를 통해 수행되었고(D_input_csv, M_PSS), 따라서 ΔPSS 기반 지표가 본 연구에서 정의한 임상적 합치성 관점에서 우수하다는 경험적 근거를 제공한다. 다만 이 우수성은 본 연구에 사용된 LAP·CP 표현형과 설계공간에 한정되며, 환자군 일반화는 추가 검증이 필요하다.

Role of material normalization (strength) in VI definition
본 분석은 stress 단독 지표보다 stress/strength 형태의 정규화가 VI 설계상 필요함을 보여준다(C2). 세 가지 strength 정규화 시나리오(지수 α 변화)를 포함한 후보군을 비교한 결과, α 값 변화에 따라 VI의 부호 거동과 민감도 순위가 달라졌고(E_VI_candidates_eval, D_input_csv), 이는 strength를 분모로 포함하지 않거나 부적절한 정규화 지수를 사용할 경우 임상적 기준 일관성이 손상될 수 있음을 시사한다. 동시에 본 연구에서 α=0.5 및 α=1.0인 두 후보(VI1 = ΔPSS / E_FC^{0.5}, VI2 = ΔPSS / E_FC^{1.0})가 7개 기준을 모두 만족하여 strength 정규화 적용의 실용적 근거를 제공하나, 모든 플라크 유형에 대해 단일 최적 α를 일반화하는 것은 본 논문의 범위를 벗어난다.

How variation of α changed candidate rankings and selection of VI1/VI2
정규화 지수 α를 변경하며 6개 후보의 임상 sign 부호 일치성을 체계적으로 평가한 결과, 동일한 stress 측정(ΔPSS)이라도 α에 따라 후보의 순위와 선택 여부가 바뀌었다(M_VI_selection, E_VI_candidates_eval). 구체적으로 α 값이 달라지면 E_FC(섬유막 강성)의 영향이 VI에 미치는 크기와 방향이 변하여 일부 후보는 7개 기준을 만족하지 못했고, α=0.5 및 α=1.0인 경우에만 모든 기준을 충족하는 일관된 거동을 보였다. 이러한 발견은 strength 정규화의 형태가 VI 특성과 민감도에 실질적 영향을 미치므로, VI 설계 시 정규화 전략을 명시적으로 검토해야 함을 의미한다(단, 본 연구 결과가 임상 표준을 확정하는 것은 아니다).

Dominance of material properties and implications for risk stratification
GPR 대리모델 위에서 수행한 Sobol 전역 민감도 분석의 그룹화 결과는 Material 그룹이 Hemodynamics 및 Morphology 그룹보다 VI 분산에서 더 큰 기여를 함을 일관되게 보여준다(두 표현형·두 VI 모두, data/sobol/sobol_grp_*.csv; W_sobol_theory). 그룹 수준의 1차(S1) 및 전차(ST) 지수에서 Material이 우위에 있었고, 이는 재료물성 불확실성(특히 섬유막·혈관벽 강성)이 VI 변동성의 주된 원인임을 시사한다. 이 결과는 형태학적 변수 및 일시적 혈류 변수보다 조직 강성 특성의 정량화와 불확실성 감소가 위험 층화 신뢰성을 높이는 데 우선순위가 될 수 있음을 시사하지만, 형태·혈류의 중요성을 모든 임상 맥락에서 배제해서는 안 된다.

Top individual drivers and measurement/prioritization implications
개별 입력 수준의 Sobol 지수(data/sobol/sobol_ind_*.csv)는 E_vessel, E_FC, SBP, PP를 일관되게 상위 4개 결정인자로 식별하였다(E_Sobol_individual), 따라서 VI 불확실성 저감을 위해 우선적으로 관심을 두어야 할 측정 항목은 혈관·섬유막 강성 및 수축기혈압·맥압이라는 실용적 시사점을 제공한다. 임상적으로는 조직 강성을 계측할 수 있는 영상 기반 강성 측정(예: OCT 기반 탄성 해석 등)과 혈압 관리가 VI 분산을 줄이는 데 기여할 수 있으나, 이러한 권고는 관찰적·모델 기반 우선순위 제안일 뿐 개입이 파열을 예방한다는 인과적 결론을 내리기 위해서는 임상시험이 필요하다. 또한 대리모델 유도 순위는 근사 오차에 민감할 수 있음을 염두에 두어야 한다.

Methodological considerations and limitations
본 연구는 여러 방법론적 제한을 갖는다: 사용된 플라크는 이상화된 표현형(LAP 3도메인, CP 4도메인)이며, 섬유막 두께는 균일한 단일 스칼라로 가정되었고(M_DOE, D_input_csv), 모든 구성요소는 선형 탄성 재료로 모델링되었다(M_FEM). 본 연구에서 활용한 비용효율적 맥동성 FSI 파이프라인과 경계조건은 선행 연구·부록 문서를 도구로 인용했으며 그 자체의 제안·검증은 본문 범위 밖이다(M_FSI). 대리모델(GPR)은 Matern 5/2 커널·ARD·로그 주변우도 최대화·5-fold CV로 훈련되어 교차검증에서 LAP VI1 R²=0.93 RMSE=0.07, CP VI1 R²=0.90 RMSE=0.09 등 양호한 성능을 보였으나(E_GPR_performance), 대리모델 근사와 샘플 수 제한(유효쌍 LAP 784, CP 727)은 Sobol 지수 추정에 불확실성을 남길 수 있으며 이를 해석 시 고려해야 한다. 마지막으로 본 연구는 모델 기반 민감도·선택 절차에 근거한 권고를 제시할 뿐 환자 결과 기반의 임상 검증은 이루어지지 않았다.

Recommendations for future work
향후 연구는 본 연구에서 제시한 발견을 환자-특이적 데이터와 결합하여 검증할 필요가 있다(환자별 지형·섬유막 두께 이질성, 비선형·피로·손상 축적 재료 모델 도입). 또한 섬유막·혈관벽의 공간적 가변성을 포함한 모델링과 영상 기반 강성 측정법의 통합(예: OCT 탄성지도화)을 통해 VI 불확실성을 실질적으로 줄일 수 있는지 평가해야 한다. 방법론적으로는 대리모델과 Sobol 분석의 민감도에 대한 추가 민감도(예: surrogate error 전파 평가) 및 대규모 환자 데이터에 대한 외적 검증이 필요하며, 본 연구에서 사용한 GPR 기반 접근은 낮은 계산비용으로 전역 민감도 평가를 가능하게 했다는 점에서 실용적 출발점을 제공한다(E_GPR_performance, D_input_csv).
