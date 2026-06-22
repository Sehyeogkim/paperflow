# 0605 Final Analysis — Calcified Plaque 1000 Cases

Jeff's final DOE preparation for 1000-case calcified-plaque ROM-FSI analysis.

project dir(local): C:\Users\jeff\project_inventor\33_0605_final_analysis
---

## 1. 목표

- 기존 1000-case **LAP** (lesion / hemodynamic) DOE는 유체 시뮬레이션이 이미 끝났으므로 **재사용**.
- 여기에 **calcification 파라미터** 5개 (+ 상수 1개) DOE를 추가 LHS로 만들어 paring.
- 핵심 동기: 기존 `fraction`을 uniform으로 뽑았을 때 calcification volume이 right-skewed → CV(calcification volume) 와 VI(vulnerability index) 의 음의 상관관계가 잘 안 보이는 문제 발생.
- 따라서 **`fraction`을 truncated normal**로 바꿔 calcification volume이 중간에 몰리는 분포로 전환하는 것이 본 작업의 핵심.

---

## 2. 산출물

| 파일 | 설명 |
|---|---|
| `input_LAP.csv`  | 기존 LAP DOE를 정리 — 불필요한 컬럼 제거, `case_id` 부여, DBP 제거 |
| `input_Cal.csv`  | Calcification 파라미터 LHS (이번 작업에서 새로 생성) |
| `input_0605.csv` | **최종 merged DOE** (LAP + Cal, random-pairing) |
| `input_LAP.png`  | LAP 변수 marginal distribution 시각화 |
| `input_Cal.png`  | Cal 변수 marginal distribution 시각화 |
| `LHS_Cal_only.py` | Cal block LHS 생성 스크립트 |
| `plot_input_LAP.py` / `plot_input_Cal.py` | distribution plot 스크립트 |
| `merge_LAP_Cal.py` | LAP + Cal random-pairing & 검증 스크립트 |

---

## 3. `input_LAP.csv` 정리 내역

원본에서 다음 컬럼을 제거 (Cal block에서 새로 샘플링할 변수들 + 미사용 변수):

- `d_fc_ca`, `fraction`, `ca_axial_skewness`, `ca_shoulder_skewness`, `ca_strength_ratio`, `E_cal`
- `DBP` 제거 (SBP, PP만 독립 LHS이고 DBP = SBP − PP로 유도되는 종속변수 → marginal이 삼각분포가 되어 분석에 부적합)

추가:
- `case_id` (0~999) 를 맨 앞 컬럼으로 삽입.

최종 컬럼 (14):
`case_id, DOS, lesion_length, lumen_axial_skewness, lipid_length_ratio, alpha, PI, fc_av_th, SBP, PP, tau, E_vessel, E_fc, E_lipid`

> `fc_av_th = 0.01` 은 고정 상수.

---

## 4. `input_Cal.csv` 생성 — `LHS_Cal_only.py`

### 4-1. Parameter spec

| 변수 | 범위 | 분포 | 비고 |
|---|---|---|---|
| `d_fc_ca` | 0.01 (const) | — | fibrous cap–calcification 간격 고정 |
| `fraction` | (0.1, 0.8) | **truncated normal**<br>μ=0.45, σ=(hi−lo)/6 ≈ 0.1167 | calcification volume의 right-skewness 완화 목적 |
| `ca_axial_skewness` | (0.0, 0.8) | uniform | |
| `ca_shoulder_skewness` | (0.0, 0.8) | uniform | |
| `ca_strength_ratio` | (0.1, 10.0) | **log-uniform** | 아래 4-2 참고 |
| `E_cal` | (0.7×10¹⁰, 2.5×10¹¹) | uniform | Young's modulus |

### 4-2. 왜 `ca_strength_ratio`는 log-uniform인가

`cal_gen.py:294-312`에서 `strength_axial / strength_circum`은 KDTree distance metric을 변형하는 데만 쓰이며, **scale-invariant** (절대 크기 무의미, 비율만 의미). 따라서 한 파라미터(ratio)로 표현 가능.

또한 ratio는 **reciprocal-symmetric** 구조 (axial 강함 ↔ circum 강함이 ratio=1 기준 대칭). Linear [0.1, 10]로 뽑으면 [1, 10] 구간이 90%, [0.1, 1] 구간이 10%로 한쪽 morphology에 편향. **log-uniform**으로 뽑아야 등방(ratio=1) 기준 양쪽이 대칭이 되어 Sobol/sensitivity 분석에서 main effect 왜곡이 없음.

구현:
```python
ratio = lo * (hi / lo) ** u   # u ∈ [0,1], stratification 유지
```

### 4-3. 후처리
- 컬럼별 소수점 자릿수 round: fraction 4, ca_axial/shoulder 6, strength 4, E_cal 1
- `d_fc_ca = 0.01` 상수 컬럼을 맨 앞에 삽입
- `case_id` (0~999) 를 그 앞에 삽입

최종 컬럼 (7): `case_id, d_fc_ca, fraction, ca_axial_skewness, ca_shoulder_skewness, ca_strength_ratio, E_cal`

### 4-4. Marginal 검증 (`input_Cal.png`)

| 변수 | empirical mean | 이론값 | 검증 |
|---|---|---|---|
| fraction | 0.450 | 0.45 | truncnorm ✓ |
| ca_axial_skewness | 0.400 | 0.40 | uniform ✓ |
| ca_strength_ratio | **2.15** | 9.9/ln(100) ≈ 2.15 | log-uniform ✓ (산술 mean 5.0과 다름!) |
| E_cal | 1.29e11 | 1.285e11 | uniform ✓ |

---

## 5. Pairing 전략 — `merge_LAP_Cal.py`

### 5-1. 왜 두 블록을 따로 LHS 하고 합치는가

이상적으로는 19개 파라미터를 **joint LHS**로 한 번에 뽑는 것이 표준이지만, LAP DOE는 이미 유체 시뮬레이션이 완료된 상태라 재샘플링 불가. 따라서 차선책으로 **두 블록 독립 LHS + random permutation pairing** 채택.

### 5-2. Random permutation pairing

단순 row-wise concat은 두 sampler의 생성 순서를 그대로 물려받아 spurious correlation이 생길 위험. Cal 블록의 행을 **무작위 순열로 섞은 후 LAP과 짝지음** (seed=20260605으로 재현성 확보):

```python
rng = np.random.default_rng(20260605)
perm = rng.permutation(N)
cal_shuffled = cal.iloc[perm].reset_index(drop=True)
```

이렇게 하면:
- 각 블록의 marginal LHS 성질은 보존 (단조 행 교환은 marginal 불변)
- 두 블록 간 cross-correlation은 무작위화로 0에 근접

### 5-3. Pairing 검증 결과

LAP block (12 variable 변수) × Cal block (5 variable 변수) Pearson cross-correlation:

| 지표 | 값 | 기준 | 평가 |
|---|---|---|---|
| max \|r\| | **0.073** | < 0.1 | ✓ |
| mean \|r\| | **0.023** | ≈ 0 | ✓ |

N=1000에서 두 독립 변수 표본상관의 standard error ≈ 1/√N ≈ 0.032이므로 max 0.073은 우연 변동 범위 내. 즉 random pairing이 두 블록 사이 spurious correlation을 충분히 제거함.

### 5-4. 최종 산출물 `input_0605.csv`

- shape: **(1000, 20)**
- 컬럼: `case_id` + LAP 13개 + Cal 6개
- 상수 컬럼: `fc_av_th = 0.01`, `d_fc_ca = 0.01`

---

## 6. Reviewer 방어용 method 문장 (영문)

> The lesion/hemodynamic parameter block (LAP, 13 variables) and the calcification parameter block (Cal, 5 variables) were independently sampled by Latin Hypercube Sampling (N=1000 each) and merged via random permutation pairing (seed = 20260605) to decorrelate the two blocks while preserving the LHS space-filling property of each marginal block. The maximum absolute Pearson cross-correlation between LAP and Cal variables in the merged DOE was 0.073 (mean 0.023), confirming the empirical independence of the two blocks. Within the Cal block, `fraction` was drawn from a truncated normal distribution (μ=0.45, σ=0.117, support [0.1, 0.8]) to mitigate the right-skewness of the resulting calcification volume and recover the expected negative CV–VI correlation; `ca_strength_ratio` was drawn from a log-uniform distribution over [0.1, 10] to give the isotropic case (ratio=1) the central, symmetric position in sample space; the remaining Cal variables were uniformly distributed.

---

## 7. 재현 절차

```bash
# 1) Cal block LHS 재생성 (이미 input_Cal.csv 있으면 스킵)
python LHS_Cal_only.py

# 2) (선택) marginal 분포 시각 검증
python plot_input_LAP.py
python plot_input_Cal.py

# 3) LAP + Cal random-pairing merge
python merge_LAP_Cal.py
# → input_0605.csv
```
