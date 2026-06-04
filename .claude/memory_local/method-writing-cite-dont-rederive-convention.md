# 방침: 표준 모델은 재유도 말고 "인용 + 값 + 코드공개", 비표준만 Appendix 수식으로

**맥락:** master_thesis Ch3 method 작성. 2026-06-02 합의(저자 질문 "공학저널에선 어떻게?").

## 결정 (저널式, 타겟=CBM)
공학저널에서 확립된 모델(Windkessel, time-varying elastance, coronary lumped BC,
Sobol 등)은 **본문에서 알고리즘을 풀어쓰지 않는다.** 대신:
1. **Cite** — 정전 문헌 인용.
2. **State your choices** — 표준에서 *우리가 고른* 부분만 본문 1–2문장.
3. **Values in a table** — 파라미터 값은 표로.
4. **Code/Data Availability** — `.py`를 GitHub/Zenodo(DOI)로 공개·인용 (요즘 거의 필수).
5. **Appendix** — 정말 비표준인 절차만 *수식 몇 줄*. 코드 walkthrough 금지.

석사논문 본체는 Appendix 길게 OK(work 증명)이지만, **저널 제출본 main text는 압축.**
워크플로우상 한국어 draft가 본체 → Appendix는 살려두고 본문만 저널式으로.

## 적용 사례
- §3.1.2 석회화: 본문 3문장 + Appendix A(recipe). [[calcification-fraction-is-sobol-input-volume-is-validation]]
- §3.1.3 입구/심근압 BC: 본문 cite 4개 + Appendix B(비표준 적합·재척도만 수식).

## BC canonical refs (reference store에 검증 완료)
- `westerhof2009windkessel` — 3-element Windkessel (RCR)
- `vignonclementel2006` — 3D FE 유출 BC 결합 (신규 추가)
- `kim2010coronary` — 관상동맥 lumped BC + intramyocardial pressure (신규 추가)
- `suga1973elastance` (+ `stergiopulos1996elastance` 보완) — time-varying elastance

## TODO
- BC 파라미터 결과값 Table 〔X〕 작성 (본문·Appendix B 연결).
- Code Availability 섹션에 P_in.py / P_myo.py / cal_gen.py repo+DOI.
