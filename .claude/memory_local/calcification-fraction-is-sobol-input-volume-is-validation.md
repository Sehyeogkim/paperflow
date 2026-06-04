# 설계 결정: 석회화 민감도 입력은 fraction, V_calc은 validation 전용

**맥락:** master_thesis Ch3 (ch3_method2.md) CP(calcified plaque) 표현형의 석회화 처리.
2026-06-02 논의·확정.

## 결정
- 석회화 형상은 단순 primitive가 아니라 `Appendix_code/cal_gen.py`의 **seed 기반
  region-growing 알고리즘**으로 lipid core 내부에 생성한다(이방성 KD-tree 전파).
- **민감도 분석(GPR surrogate + Sobol)의 석회화 입력 = 석회화 분율 `f_calc`**
  (LHS로 독립 샘플). CP 입력은 LAP 12개 + `f_calc` + `E_calc` = 14개.
- **석회화 부피 `V_calc`은 입력이 아님.** 생성 후 측정되는 종속량이고, 그 **분포를
  임상 보고 범위와 대조하는 validation 용도**로만 쓴다.

## 입력 데이터 실체 (`data/input_parameter/input.csv`, 1000행)
컬럼 20개: DOS, lesion_length, lumen_axial_skewness, lipid_length_ratio,
alpha(=θ_lip), PI, d_fc_ca, fraction, ca_axial_skewness, ca_shoulder_skewness,
ca_strength_ratio, fc_av_th, SBP, PP, tau(=ρ_d), DBP, E_vessel, E_fc, E_lipid, E_cal.
- 석회화 생성 파라미터는 **fraction 하나가 아니라 5개**(d_fc_ca, fraction, 2 skewness,
  ca_strength_ratio)가 LHS로 독립 샘플됨.
- `fc_av_th`=0.01 고정(FC 두께 균일가정과 일치), `DBP`=SBP−PP 파생.
- 석회화 생성 파라미터는 **5개**(fraction + d_fc_ca + 2 skewness + ca_strength_ratio).
  ⚠️ cal_gen.py 157–158줄은 d_fc_ca를 0.01로 override하지만 **그 코드는 설명용 버전일 뿐,
  실제 데이터 생성엔 LHS 샘플된 d_fc_ca가 적용됨(저자 2026-06-02 확인). d_fc_ca는 dead 아님.**
- 샘플 수: **LAP 1,000 / CP 1,300** (CP는 별도 CSV). 유효쌍 LAP 784/1,000, CP 727/1,300.
  CP 입력공간 = 18개(분석 14 + 생성 4: 2 skewness + strength ratio + d_fc_ca).

## shape 파라미터 처리 방침 (2026-06-02 확정)
- SA 입력은 fraction + E_cal (CP=14). 위치·이방성(2 skewness + strength ratio)은
  **데이터 생성 시엔 변동했지만 SA 입력에서 제외**.
- 정당화: 동일 데이터셋에 shape 파라미터를 입력으로 추가한 **검증용 Sobol 1회**를
  돌려 전차지수 무시가능(S_T≈0) 확인 → 그걸 근거로 제외. 〔TODO: S_T 수치 채우기〕
- **중요: LHS/FSI 데이터 재생성 안 함.** 재실행은 surrogate 재학습 + Sobol뿐(저비용).
  기존 727 CP 샘플 재활용.

## 왜 (이게 코드만 봐선 안 보이는 이유)
- `V_calc`은 lipid core 내부에 기하학적으로 구속됨 → lipid 형상(arc angle,
  lipid length ratio, lesion length, DS …)에 의존 → **다른 형태변수와 상관**.
- Sobol은 입력 독립성을 가정 → `V_calc`을 입력으로 쓰면 지수가 편향되고 reviewer가
  정확히 그 지점을 친다. `f_calc`은 독립 LHS 변수라 안전.
- `f_calc` 범위는 결과 `V_calc` 분포가 임상 보고 범위 [ref 21]를 포괄하도록 설정.

## 글에 반영된 위치
- `contents/ch3_method2.md` §3.1.1 형태변수 bullet, Table 1 행(`f_calc`, 단위 –),
  Table 1 아래 주석(validation 명시), §3.1.2 "석회화 형상 생성(CP 전용)" 문단.
- `contents/appendix_A_calcification.md` — 알고리즘 전 과정 (Appendix A).

## 미해결 TODO
- `f_calc` 샘플 범위 [min,max] 확정 (parameterB CSV) → Table 1의 〔TODO〕 채우기.
- 생성 파라미터(skewness/strength) 범위·고정값 명시.

관련: [[master-thesis-target-journal-and-fsi-companion]]
