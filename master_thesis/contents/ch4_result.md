# Chapter 4. Results

본 장에서는 세 단계 프레임워크(데이터셋 생성 → 취약성 지수 선정 → 대리모델 기반 전역 민감도 분석)의
결과를 LAP(저감쇠 플라크)와 CP(석회화 플라크) 두 표현형에 대해 제시한다. 먼저 6개 취약성 지수 후보를
임상 기준으로 선별하여 두 개의 최종 지수를 확정하고(§4.1), 이 지수에 대한 Sobol 전역 민감도 분석 결과를
제시하며(§4.2), 마지막으로 파열 위치 분포 결과를 임상 데이터와 비교한다(§4.3).


## 4.1 취약성 지수(Vulnerability Index) 선정

취약성 지수는 응력과 강도의 비 VI = σ/strength로 정의하였다. 응력 2종(PSS, ΔPSS)과 강도 지수
3종(strength ∼ $E_\text{FC}^{\alpha}$, α = 0.0/0.5/1.0)을 조합해 **6개 후보**를 만들고, 각 후보를
임상적으로 확립된 **7개 고위험 플라크 특징**에 대해 feature–VI 상관의 *부호*가 임상 기대 방향과
일치하는지로 선별하였다(7개 모두 일치해야 admissible).

각 (feature, VI 후보) 쌍의 상관(Pearson $r$·Spearman $\rho$)은 **Fig. 4.1**에 산점도로 제시하였다.
(A)는 LHS 데이터셋의 6개 feature로, row 1–5는 LAP 시뮬레이션(plaque burden·ΔFFR·$E_\text{FC}$·
$E_\text{lipid}$·lipid arc angle), row 6은 CP 시뮬레이션(calcification volume)에서 얻은 VI 관계이다.
(B)는 주 해석에서 고정했던 FC 두께를 별도 sweep(§3.2.2)으로 변화시켜 얻은 row 7(thin fibrous cap)이다. 예를들어서, del_PSS / E_fc^0.0 = VI를 기준으로, 우리가 분석했을때, plaque burden이 커질수록 위험도가 높아지는 음의 상관관계를 시물레이션 결과로부터 얻었고, 이는 기준1의 높은 위험도 플라크의 기준이 plauqe burden이 크다는 것을 통해 타당한 VI라는 것으로 해석한다.

*Fig. 4.1 — Input–VI correlation. (A) LAP·CP LHS dataset (rows 1–6); (B) fibrous-cap-thickness sweep (row 7). 각 칸에 Pearson $r$·Spearman $\rho$ 표기.*

Fig. 4.1에서 row 4–7은 6개 후보가 모두 같은 부호를 보여 후보를 변별하지 못하는 반면, **row 1–3
(plaque burden·ΔFFR·collagen-deficient cap)에서만 후보에 따라 상관 부호가 갈린다.** 각 상관의 부호를
임상 기대 방향과 대조한 요약이 **Table 4.1**이다(◯ 일치 / × 위배).

*Table 4.1 — Compliance of the six Vulnerability Index candidates (VI = σ / strength, strength = $E_\text{FC}^{\alpha}$) with the seven high-risk plaque features of Table 2 (§3.2.2). ◯: clinically consistent; ×: violates expected direction.*

(열 = VI 후보: 바깥 stress(PSS / ΔPSS) × 안쪽 strength $E_\text{FC}^{\alpha}$; 모서리 = 행축 feature ＼ 열축 VI.)

| # | High-risk feature ＼ VI  | PSS / $E_\text{FC}^{0.0}$ | PSS / $E_\text{FC}^{0.5}$ | PSS / $E_\text{FC}^{1.0}$ | ΔPSS / $E_\text{FC}^{0.0}$ | ΔPSS / $E_\text{FC}^{0.5}$ | ΔPSS / $E_\text{FC}^{1.0}$ |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | Large plaque burden | × | × | × | ◯ | ◯ | ◯ |
| 2 | High ΔFFR | × | × | × | ◯ | ◯ | ◯ |
| 3 | Collagen-deficient fibrous cap | × | ◯ | ◯ | × | ◯ | ◯ |
| 4 | Soft plaque | ◯ | ◯ | ◯ | ◯ | ◯ | ◯ |
| 5 | Large lipid arc angle | ◯ | ◯ | ◯ | ◯ | ◯ | ◯ |
| 6 | Less calcified plaque | ◯ | ◯ | ◯ | ◯ | ◯ | ◯ |
| 7 | Thin fibrous cap | ◯ | ◯ | ◯ | ◯ | ◯ | ◯ |
| | **All 7 satisfied?** | ✗ | ✗ | ✗ | ✗ | **✓** | **✓** |



6개 후보 중 **ΔPSS/$E_\text{FC}^{0.5}$와 ΔPSS/$E_\text{FC}^{1.0}$ 두 열만 7기준을 모두
만족**하며, VI1, VI2로 표기한다. 탈락 양상은 두 가지다.

- **PSS 후보(α 무관)** — plaque burden·ΔFFR에서 VI가 음의 상관($\rho \approx -0.1$)을 보여
  "부담·ΔFFR 증가 → 위험 증가(양의 상관)" 기대와 어긋난다. 같은 두 feature에서 ΔPSS는 양의 상관
  ($\rho \approx +0.1\text{–}0.2$)으로 부호를 회복한다 → **피로 진폭 ΔPSS가 필요**.
- **α = 0.0 후보(강도 정규화 없음)** — collagen-deficient cap에서 VI–$E_\text{FC}$가 양의 상관
  ($\rho \approx +0.43$)이 되어 "$E_\text{FC}$ 감소 → 위험 증가(음의 상관)" 기대를 위배한다. α ≥ 0.5로
  $E_\text{FC}$를 분모에 넣으면 음의 상관($\rho \approx -0.35\text{–}{-0.79}$)으로 뒤집힌다 →
  **α > 0(재료 정규화)이 필요**.

따라서 응력 = ΔPSS, 강도 = $E_\text{FC}^{\alpha}$ (α > 0)일 때에만 7기준을 동시에 충족하며, VI1·VI2를
최종 지수로 채택한다. 이후 §4.2 민감도 분석은 이 둘에 대해 수행한다. (임상적 함의는 §5.1–5.2.)


## 4.2 민감도 분석 결과

### 4.2.1 GPR 대리모델 정확도

확정된 두 지수(VI1, VI2)에 대해, 각 표현형의 입력 → VI 사상을 학습하는 Gaussian Process Regression(GPR) 대리모델을 구축하였다. 전체 LHS 샘플(LAP 1,000 / CP 1,000) 중 일부는 boolean·메시 생성 실패으로 학습에 사용한 유효 입출력 쌍은 다음과 같다.

| 표현형 | 유효 입출력 쌍 | VI1 기준 R² | VI2 기준 R² |
|---|---|---|---|
| LAP | 784 / 1,000 | 0.9598 | ? |
| CP  | ? / 1,000 | ? | ? |


### 4.2.2 Sobol 전역 민감도 지수

figure 4.2 sensitivty (A) individual (B) group senstiivty anayliss.

GPR 대리모델 위에서 Saltelli 샘플링으로 1차 지수($S_1$)와 전차수 지수($S_T$)를 산출하였다(인자별·인자군별; **Fig. 7**). 개별 민감도를 분석하 (A)를 살펴보면, 지배 인자는 VI1,2에서 모두 **재료 모듈러스($E_\text{vessel}$, $E_\text{FC}$)와 수축기압($P_\text{sys}$)**이다. 또한, (B)의 그룹 민감도를 살펴보면, **두 표현형(LAP·CP)과 두 지수(VI1·VI2) 모두에서 **재료물성군(Material)이 지배적**이었다. 그리고 혈류학적 파라메터가 그 높은 민감도를 보이며, 형태학적 파라메터의 경우, 낮은 개별민감도이지만 St가 높은 것으로 확인된다.


## 4.3 파열 위치 결과
(figure 파열 위치 (A) circumferetial (B) axial )

파열 위치 지수로부터 얻은 파열 위치 분포를, 원주방향과
축방향으로 나누어 어느 영역에 위치해 있는지를 분석하였다. 파열 위치의 경우, 한 case내에서 가장 높은 VI의 위치이므로, PSS, del PSS에 따른 두 그룹으로만 분석이 구분된다. (전달하고싶은 메세지는 6개의 VI이지만, 분모 strength가 결국 노드끼리는 같으므로 rupture location을 구분하는거는 결국 stress = PSS and del PSS임.) figure 8A를 살펴보면, 먼저 원주방향의 경우 shoulder에서의 파열이 PSS and del PSS 각각 56.9, 57.5%로 더 빈번하게 발생하는 것으로 확인된다. 또한 (B)의 축방향 을 살펴보면, Minium Lumen Area 앞뒤 영역인 middle 영역에서 60.2%, 67.3%로 더 빈번하게 파열이 발생하는것으로 확인되었다.