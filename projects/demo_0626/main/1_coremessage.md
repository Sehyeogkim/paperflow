## One paragraph
관상동맥 죽상경화 플라크의 파열은 급성 관상동맥 증후군의 주된 원인으로, 전 세계 심혈관 사망의 상당 부분을 차지한다. 따라서 플라크 파열 위험도를 정량화하여 예측하기 위해 computational method으로 플라크의 응력분포(PSS, ΔPSS)를 분석하는 연구들이 진행되어왔다. 여기서 선행연구들은 주로 파열위험지표를 stress와 strength의 비로 정의하였고, 섬유막의 strength는 실제로 환자마다 다르지만 불확실성으로 인해 고정된 상수로 고려하였다. 또한 플라크 파열 위험도는 재료물성·혈류역학·형태학적 인자가 복합적으로 작용해 결정되나, 기존 전산 연구들은 높은 계산 비용으로 인해 이 세 인자군을 맥동성 유체-고체 연성(FSI) 해석 조건 하에서 동시에 분석하지 못하였다. 본 연구에서는 이상적 관상동맥 모델을 활용해 비용 효율적 맥동성 FSI 기법으로 저감쇠 플라크(LAP)와 석회화 플라크(CP) 각각에 대해 대규모 입출력 데이터셋을 구축하였다. 파열 취약성 지수(VI)는 stress와 strength의 비율로 정의하였으며, stress는 최대응력·최대진폭 2가지, strength는 3가지 파열 시나리오를 기준으로 총 6가지 위험지표를 정의하였다. 임상적으로 확립된 고위험 플라크 특징 7가지를 모두 만족하는 두 지수를 선정하였다. 가우시안 과정 회귀(GPR) 대리 모델과 소볼 민감도 분석을 적용한 결과, 재료물성이 혈류역학·형태학적 인자보다 파열 위험도에 더 큰 영향을 미치며, 혈관 벽 탄성계수·섬유막 탄성계수·수축기 혈압·맥압이 주요 결정 인자임이 확인되었다. 또한 응력을 최대진폭(피로) 관점에서 해석했을 때 임상적으로 더 적합함을 확인하였다.

## Novelty
- 발견 1: 파열위험지표 = stress/strength이며, stress는 ΔPSS(피로·진폭 관점)가 임상적으로 더 적합 → 맥동성 시뮬레이션의 필요성
- 발견 2: 파열위험 지표 정의에 strength 정규화가 필요하다
- 발견 3: 소볼 민감도 분석 결과 재료물성(material)이 혈류역학·형태보다 파열 위험을 지배 (Material > Hemo > Morpho)

## Keywords
coronary plaque rupture, fluid-structure interaction, Sobol sensitivity analysis, Gaussian process regression, ΔPSS, vulnerability index

## Out of scope
cost-effective 맥동성 FSI 기법 자체의 제안/검증 (선행 논문 소관 → 본 논문에서는 도구로 인용만)
