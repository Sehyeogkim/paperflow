# Abstract

관상동맥 플라크 파열은 급성 심혈관 사건의 주된 기계학적 원인이지만, 그 위험을 결정하는
형태학적·혈류역학적·재료적 인자는 통상 개별적으로만 평가되어 왔다. 완전 연성(fully coupled)
맥동성 유체–고체 연성(FSI) 해석의 높은 계산 비용 때문에, 세 인자군을 **동시에**, 그리고
**대규모 맥동 조건 하에서** 분석한 in-silico 연구는 거의 존재하지 않았다.

본 연구에서는 비용효율적 맥동성 FSI 프레임워크[cite:kim_snapshot]를 forward solver로 활용하여,
이상화된 관상동맥 모델에 대해 두 표현형(low-attenuation plaque, LAP, 1,000 샘플 / calcified
plaque, CP, 1,300 샘플)의 라틴 하이퍼큐브 데이터셋을 구축하였다. 응력 2종(PSS, ∆PSS)과 섬유막
강도 정규화 지수 3종(strength $\propto E_\text{FC}^{\alpha}$, $\alpha \in \{0.0, 0.5, 1.0\}$)을 조합한
6개 파열 취약성 지수(Vulnerability Index, VI) 후보를 임상적으로 확립된 7개 고위험 플라크 특징에
대한 일관성 기준으로 선별하였고, 선정된 지수에 Gaussian Process Regression(GPR) 대리모델을
학습한 뒤(LOO $R^2 > 0.94$) Saltelli 표본추출 기반 Sobol 전역 민감도 분석을 수행하였다.

7개 임상 기준을 모두 만족하는 VI는 **맥동 응력 진폭(∆PSS)을 응력으로 사용하고 $\alpha > 0$의
섬유막 강도 정규화를 갖는 두 지수**뿐이었다(VI1 = ∆PSS/$E_\text{FC}^{0.5}$, VI2 = ∆PSS/$E_\text{FC}^{1.0}$).
단조 최대응력(PSS) 후보는 plaque burden·∆FFR 증가에 대한 임상 방향을 재현하지 못했고, 강도
정규화를 생략한 $\alpha = 0$ 후보는 섬유막 강성 저하(collagen-deficient cap)에 대한 방향을
재현하지 못했다. 인자군 단위 민감도 분석에서는 **재료물성군이 두 표현형·두 지수 모두에서 지배적**
이었으며, 재료 인자군의 1차 지수 합은 LAP에서 0.602(α = 0.5)에서 0.797(α = 1.0)로, CP에서
0.626에서 0.836으로 증가하여, $\alpha$가 커질수록 재료 지배성이 정량적으로 강화됨이 확인되었다.
지배적 개별 인자는 혈관벽 탄성계수($E_\text{vessel}$), 섬유막 탄성계수($E_\text{FC}$), 수축기압
($P_\text{sys}$)이었다. 형태학적 변수는 1차 지수가 작은 반면 전차 지수가 크게 나타나, 그 영향이
독립적 주효과가 아니라 재료·혈류역학 인자와의 상호작용을 통해 발현됨을 시사하였다. 파열 위치
분석에서는 원주방향으로 shoulder 영역(PSS 56.9%, ∆PSS 57.5%), 축방향으로 minimum lumen area
인근 영역(60.2%, 67.3%)이 우세하게 나타났다.

이 결과는 in-silico 플라크 파열 평가의 baseline으로서 정상 상태가 아닌 맥동성 혈류역학과 강도
정규화의 채택을 정당화하며, 임상 변환의 우선축이 형태학적 영상 계측보다 **환자-특이적 조직
강성 특성화**에 있음을 시사한다.

**Keywords**: coronary plaque rupture, fluid–structure interaction, vulnerability index, global
sensitivity analysis, Gaussian process regression, fibrous-cap stiffness.
