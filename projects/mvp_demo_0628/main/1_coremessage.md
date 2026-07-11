## One paragraph
관상동맥 죽상경화 플라크의 파열은 급성 관상동맥 증후군의 주된 원인으로, 전 세계 심혈관 사망의 상당 부분을 차지한다. 선행연구들은 파열위험지표를 stress와 strength의 비로 정의하였으나 섬유막 strength를 고정 상수로 가정하였고, 높은 계산 비용 때문에 재료물성·혈류역학·형태학적 인자군을 맥동성 FSI 조건에서 동시에 분석하지 못하였다. 본 연구는 이상적 관상동맥 모델과 비용 효율적 맥동성 FSI 기법으로 저감쇠 플라크(LAP)와 석회화 플라크(CP)에 대한 대규모 입출력 데이터셋을 구축하고, 취약성 지수(VI)를 stress/strength로 정의(stress 2종 × strength 3시나리오 = 6개 후보)하여 임상 고위험 특징 7가지를 모두 만족하는 2개 지표를 선정하였다. GPR 대리모델과 소볼 민감도 분석 결과, 재료물성이 혈류역학·형태보다 파열 위험을 지배하며 혈관 벽·섬유막 탄성계수, 수축기압, 맥압이 주요 결정 인자였고, 응력을 최대진폭(피로) 관점(ΔPSS)으로 해석하는 것이 임상적으로 더 적합함을 확인하였다.

## Novelty
- 파열위험지표 = stress/strength이며, stress는 ΔPSS(피로·진폭 관점)가 임상적으로 더 적합 → 맥동성 시뮬레이션의 필요성
- 파열위험 지표 정의에 strength 정규화가 필요하다 (재료가 분모로 들어가야 하며, 정규화 지수 α에 따라 민감도가 바뀜다)
- 소볼 민감도 분석 결과 재료물성(material)이 혈류역학·형태보다 파열 위험을 지배 (Material > Hemo > Morpho)

## One sentence
플라크 파열 위험은 strength로 정규화한 ΔPSS 기반 VI로 더 잘 설명되며, 재료물성이 위험을 지배한다.

## Keywords
coronary plaque rupture, fluid-structure interaction, Sobol sensitivity analysis, Gaussian process regression, ΔPSS, vulnerability index

## Out of scope
cost-effective 맥동성 FSI 기법 자체의 제안/검증 (선행 논문 소관 → 본 논문에서는 도구로 인용만)
