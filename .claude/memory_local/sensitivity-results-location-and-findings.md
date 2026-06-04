# 민감도 분석 결과: 위치 + 핵심 수치

## 원격 데이터 위치 (cvbml02 = ws2)
- `cvbml02:/home/jeff/project/55c_final_defense_0512/Figure_final/`
  - `data_CP/sobol_{grp,ind}_{LAP,CP}_{VI1,VI2}.csv` — Sobol 인덱스(인자군/인자별 × 표현형 × VI). **8개 파일이 최종 민감도 결과.**
  - `data_LAP/merged_expE2.csv` (LAP, 784행), `data_CP/merged.csv` (CP, 1075행) — 상관 figure 원본.
  - `data_FC/` — 섬유막 두께 sweep(3 E_fc × 5 = 15점), §3.2.2 기준 #7용.
  - `claude_session_memory/result_memory.md` — figure 제작 메모(row/col 구조, 전처리).
- 로컬 사본: `master_thesis/data/sobol/` (8개 csv scp 완료).
- 접근: `/ssh ws2 "..."` 스킬. 결과 fetch 후 `[TODO]` 채우기. [[master-thesis-target-journal-and-fsi-companion]]

## 핵심 발견 (ch4_result §4.2.2에 반영됨)
- **재료물성군 지배** — 네 경우(LAP/CP × VI1/VI2) 모두 $S_1$ 기준 Material > Hemodynamic > Morphological. Material $S_1$ ≈ 0.50(VI1)–0.80(VI2). VI2(α=1.0)에서 재료 지배 더 강함(E_FC가 분모 1제곱).
- **지배 인자 = E_vessel, E_FC, P_sys(수축기압).** α에 따라 1위 갈림: VI1→E_vessel($S_T$≈0.42) 1위, VI2→E_FC($S_T$≈0.6) 1위.
- **PP(맥압)는 작음**($S_T$≈0.03–0.07) — 초기 초안의 "top4 = E_vessel/E_FC/SBP/**PP**"는 틀렸고 수정함. E_cal·lumen skewness·PI는 ≈0. CP의 Ca fraction만 VI1에서 중간($S_T$≈0.15).

## 방법 nuance (result2.md 출처)
- **CP는 18 input 중 calcification 제작 4개(d_fc_ca, ca_axial_skewness, ca_shoulder_skewness, ca_strength_ratio) 제외 → 14개로 surrogate.** [[calcification-fraction-is-sobol-input-volume-is-validation]]
- `fc_av_th`(섬유막 두께)는 LAP·CP 둘 다 상수(0.01cm)라 입력에서 제외 → 그래서 기준 #7은 별도 FC sweep 필요.

## 미해결 (사용자 확인 필요)
- R²_LOO(초안 LAP 0.9598 / CP 0.9361) 출처 파일 못 찾음 — surrogate 학습 스크립트 위치?
- 유효샘플 수: figure 메모는 LAP 764 / CP 1058(threshold 후), 초안은 784 / 1075. 어느 게 surrogate 학습 N인지.
- 파열 위치(§4.3 shoulder/proximal/distal %) 데이터는 이 폴더에 없음 — 별도 위치.
