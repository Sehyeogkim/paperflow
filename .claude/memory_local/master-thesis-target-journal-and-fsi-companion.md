---
name: master-thesis-target-journal-and-fsi-companion
description: master_thesis 타겟 저널(CBM)과 companion FSI 논문(under review) 관계, §2.1 governing-equation 결정
metadata:
  type: project
---

`master_thesis/`(plaque vulnerability index 논문)의 두 가지 핵심 프로젝트 사실 (2026-06-02 확정):

**1. 두 산출물, 두 규범.**
- 같은 내용이 (a) 학교 제출용 **master thesis(자유 형식)** 와 (b) **저널 투고본** 두 곳으로 간다.
- 타겟 저널: **Computers in Biology and Medicine (CBM)**, Elsevier.
- CBM은 **"Your Paper Your Way"** — first submission은 자유 형식, 형식은 revision/accept 단계에서 맞춤.
  → 첫 투고 단계에서 thesis/journal 형식 구분은 거의 무의미. 지금은 논리·구조에 집중.

**2. Companion 논문 관계 (중요).**
- **"Cost-Effective Pulsatile FSI Framework"는 별도의, 지금 review 중인 논문** (Kim et al., under review)의 contribution.
- 이 thesis/journal 논문의 ★핵심 기여는 **§2.3 Vulnerability Index Formulation**. FSI는 그걸 가능하게 한 Stage-1 **enabler/도구**.
- 따라서 FSI를 헤드라인처럼 풀로 재설명하면 (a) under-review 논문과 text overlap(self-plagiarism) 플래그, (b) "이 논문 새로운 게 뭐냐" 리뷰어 반응 위험.

**§2.1 처리 결정 (governing equation 포함).**
- CBM Methods 규정: *"sufficient detail to allow the work to be reproduced"* + *"Methods already published should be indicated"*.
- 결론: **governing equation(Navier–Stokes+구조+FSI coupling)은 표준 물리식이라 풀버전 유지 = 재현성 목적상 정당/권장** (self-plagiarism 무관).
  위험한 건 validation의 novel 산문/결과를 베끼는 것 → **validation만 압축 + [ref] 인용**.
- 트리 최종형(노션 Schematic tree view): §2.1.1 Framework / §2.1.2 Governing equations(full) / §2.1.3 Validation(condensed+ref).

**노션 트리 구조 변경(2026-06-02):** §2.4 Statistical analysis + §2.5 Sobol → **§2.4 Statistical Analysis** 로 병합
(§2.4.1 Surrogate model–GPR [Stage 3] / §2.4.2 Sobol sensitivity analysis [Stage 4]). "four-stage framework" 프레이밍 유지.

노션 페이지: "🌲 Schematic tree view" (id 3652a46dc68c80859d53c56437941bf9) — `.tex` 구조 트리.

관련: [[painpoint_figure_design_lastmile]]
