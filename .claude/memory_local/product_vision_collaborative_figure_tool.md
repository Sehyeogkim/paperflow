# 제품 비전: 인간+Claude 협업 figure 디자인 도구 ("figure용 Cursor")

**날짜:** 2026-06-02
**유형:** 제품 비전 / 아키텍처 (논의 단계, 미구현)

## 한 줄 요약
ParaView(3D 과학 시각화) + PowerPoint식 2D 주석 + Claude 협업을 섞은,
**"figure 디자인용 Cursor"** — 인간은 지각적 판단(마우스), Claude는 계산적 작업을 담당.

## 분업 원리 (핵심)
- **Claude/코드:** 계산·논리로 표현되는 것 — MLA 찾기, 도메인 분리, 색 지정, "1000번 반복".
- **인간:** 공간·미감 판단 — 카메라 각도, 라벨 위치, "여기 답답해". 하기는 쉽지만 좌표로 표현 불가.
- **둘 다 혼자선 못 함:** Claude는 좋은 각도를 못 느끼고, 인간은 카메라 행렬을 타이핑 못 함.
  → 사용자 논문의 "인간도 AI도 혼자선 최적 못 낸다"의 완벽한 구체 사례.
- 페인포인트 근거: [[painpoint_figure_design_lastmile]]

## 핵심 기술 원리: 양방향 상태 동기화
인간이 마우스로 각도를 잡음 → 앱이 **카메라 상태(position/focal/view-up = 숫자 몇 개)** 기록
→ Claude가 그 숫자를 받아 **추측 못 했던 좌표를 손에 쥠** → 재현·확장.

## 오픈소스 포크 가능성 (Cursor가 VS Code 포크한 것처럼)
- **VS Code:** 오픈 (Code-OSS, MIT) — Cursor가 포크.
- **ParaView:** ✅ 완전 오픈소스 (BSD, Kitware), VTK 기반, 플러그인+파이썬 스크립팅 → **포크/임베드 가능.**
- **VTK:** ✅ 오픈 (BSD) — 렌더링 코어.
- **`trame`** (Kitware): VTK/ParaView를 파이썬으로 **커스텀 웹앱으로 감싸는 프레임워크** — 자작 도구의 길.
- **PowerPoint:** ❌ 독점(MS). 2D 디자인 레이어는 직접(웹 canvas) 만들거나 LibreOffice Impress 대체.

## 아키텍처 (MCP의 위치)
```
[ 인터랙티브 앱 ]  ← 인간이 마우스로 편집 (카메라/라벨)
  trame/ParaView(3D) + 웹 canvas(2D PPT식 주석)
        │  양방향 상태 동기화
[ MCP 서버 ]  ← 앱 상태(카메라·도메인·선택) 노출 + 연산 수신 (set_camera/threshold/screenshot…)
        │
[ Claude ]  ← MLA·도메인·색·반복 담당
```
- **MCP = Claude↔앱 제어 채널 1개일 뿐.** GUI/렌더/canvas는 MCP가 안 줌 → 실제 앱(trame)이 담당.

## 분야 일반성 (왜 계산분야만의 게 아닌가)
공통 추상 = **"원천 아티팩트 → figure, 그 사이 수동 디자인 단계".**
제품 코어 = "디자인 canvas + AI 협업", 데이터 로더(ParaView=mesh / 이미지=PNG / matplotlib=plot)는
**플러그인**으로 교체 → 분야 무관. (실험가: PNG 더미→plot, 계산가: mesh→3D.)

## 범위 정직성
- **집중 MVP(현실적, 수일~수주):** trame 앱이 .vtu 로드 → 마우스 카메라 회전 →
  MCP가 get_camera/set_camera/threshold/screenshot 노출. Claude=MLA+도메인+색, 인간=각도.
- **풀 비전:** 진짜 제품, 훨씬 큼. 하지만 아키텍처는 위 구조로 일관 확장.

## 현재 워크플로우와의 관계
지금은 Claude가 **pyvista로 혼자 렌더(헤드리스 PNG, Claude가 직접 봄)** → 인간이 GUI로 마감.
GUI 협업 다리: ParaView Python Shell(코드 붙여넣기), Trace(인간 수작업→파이썬 기록→Claude 확장),
스크린샷(Claude의 "눈"). 실시간 GUI 조종은 불가, 코드+스크린샷으로 사실상 협업.
