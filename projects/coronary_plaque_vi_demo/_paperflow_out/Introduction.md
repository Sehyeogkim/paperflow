### Clinical importance of plaque rupture
관상동맥 죽상경화 플라크의 파열은 급성 관상동맥 증후군(ACS)의 주된 병인으로 작용하며 전 세계 심혈관 사망의 상당 부분을 차지하므로, 플라크 파열 위험을 정량화·예측하는 신뢰성 있는 지표 개발이 임상적·연구적으로 시급하다 [cite:thomascgasse2005] [cite:nikhiljoshi2013]. (이 절에서는 본 연구의 계산적 방법이나 새로운 임상시험 결과를 제시하지 않는다.)

관상동맥 플라크의 파열 취약성은 플라크의 형태학적 특징(예: 섬유막 두께, 병변 길이, 석회화 분포), 혈류역학(예: 혈압, 맥압, 국소 유동장) 및 조직의 재료특성(특히 섬유막 및 혈관벽의 강성·강도)이 상호작용하여 결정된다; 따라서 이들 인자는 복합적으로 플라크 내 응력장과 파열 위치·가능성에 영향을 미치며 선행 연구들의 관찰과 일치한다 [cite:frankgijsen2019] [cite:claireconway2014] [cite:thomascgasse2005]. 다만 본 단락에서는 어느 단일 인자가 반드시 우세하다고 주장하지 않으며, 인자들 간 상호작용의 중요성을 요약하는 데 중점을 둔다.

Limitations of stress-only metrics and role of strength
기존 전산 연산 연구들은 주로 응력(stress) 기반의 취약성 지표를 제안하면서 섬유막 강도(strength)를 환자별 차이를 반영하지 않고 상수로 고정하는 경우가 많았다; 이런 접근은 서로 다른 재료물성 하에서의 비교성을 확보하지 못하고 실패역학의 기본 원리(부하 대비 강도의 비)를 반영하지 못한다 [cite:thomascgasse2005]. 물리적으로 의미 있는 취약성 지수는 국부적 하중을 국소 강도로 정규화한 무차원 비율(stress/strength)이어야 하며, 특히 섬유막 강도로 정규화하는 경우 E_fc^α 형태의 정규화 지표에서 지수 α의 선택은 VI의 물질 민감도 및 전역 민감도 해석에 실질적인 영향을 미친다(정규화 방식의 선택이 VI 거동을 변형시킨다는 점을 강조한다). 본 단락은 이후 실증적 비교를 통해 어떤 정규화가 임상적 일관성을 더 잘 제공하는지를 제시할 것임을 연결한다; 그러나 여기서는 해당 비교의 정량적 증거를 제시하지 않는다 [cite:thomascgasse2005].

### Need for simultaneous, pulsatile FSI exploration
파열의 피로성 기전 관점에서 심주기 진폭(ΔPSS, pulsatile amplitude)은 단일 시점의 최대응력(peak PSS)보다 손상 누적과 파열 가능성에 대해 물리적으로 더 직접적인 의미를 갖는다; 따라서 ΔPSS를 정확히 평가하려면 시간-분해능을 갖춘 맥동성(FSI) 시뮬레이션이 필요하며, 준정적 또는 정상 상태(steady) 해석은 이러한 진폭 정보를 복원할 수 없다. 그러나 형태·혈류역학·재료의 세 인자군을 현실적인 분포 범위에서 동시에 넓게 변동시키며 맥동성 FSI 하에서 전역 민감도 분석을 수행하려면 막대한 계산 비용이 요구되어 기존 연구에서는 이 전체 공간을 포괄적으로 탐색하지 못했다; 본 연구에서는 입구 유량 및 심근 elastance와 같은 시간의존 경계조건(예: inflow.dat, elastance.dat)과 비용효율 FSI 경계조건 사양을 기반으로 ΔPSS를 산출하고자 한다. 이 단락은 ΔPSS 기반 VI의 필요성과 맥동성 시뮬레이션의 필수성을 제시하되, 비용효율 FSI 기법 자체의 새 제안·검증은 본 논문의 범위를 벗어난다는 점을 명시한다.

### Study objective and approach
본 연구의 목적은(1) 선행에서 검증된 비용효율 맥동 FSI 파이프라인을 사용하여 이상적 관상동맥 플라크 표현형(LAP 및 CP)에 대해 대규모 입력설계공간에서 맥동성 FSI 출력을 생성하고, (2) stress/strength 형태의 후보 취약성 지수(VI; stress로 peak PSS 및 ΔPSS, strength로 E_fc^α의 여러 시나리오)를 임상적으로 확립된 7개 고위험 플라크 기준과의 sign-consistency로 선별하여 clinically-consistent VI를 결정한 후, (3) 선택된 VI에 대해 Gaussian process regression surrogate(ARD Matérn 5/2 + White-noise, 하이퍼파라미터 최적화 L-BFGS-B 20 restarts, 입력 표준화·출력 표준화, 5-fold CV)를 학습하고 Saltelli 샘플링 기반 Sobol 전역 민감도(S1, ST)를 surrogate 위에서 산출하여 형태·혈류역학·재료군의 상대적 기여도를 정량화하는 것이다. 방법론적 세부사항(시뮬레이션 시간적분, Δt, 주기수, 재료 모델 등)은 Materials and Methods에 기술하고, 비용효율 FSI 기법의 원천 검증은 기존 문헌을 인용하여 처리한다; 결과 절에서는 VI 선별 결과와 Sobol 그룹·파라미터 수준 민감도(예: material group S1 ≈ 0.75, E_fc S1 ≈ 0.55 등) 및 GPR 성능 지표를 제시할 것이다.
