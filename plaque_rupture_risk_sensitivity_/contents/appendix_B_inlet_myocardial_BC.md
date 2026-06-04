# Appendix B — Inlet pressure and intramyocardial pressure generation

<!-- 초안 언어: 한국어 먼저 → 확정 후 영어 in-place 교체 (CLAUDE.md house rule).
     출처: Appendix_code/P_in.py, P_myo.py. 본문 대응: ch3_method2.md §3.1.3 유체 BC.
     원칙(저널式): Windkessel·elastance·coronary BC 자체는 표준 모델이므로 §3.1.3에서 인용으로 처리하고,
     여기엔 "우리의 비표준 선택(적합 절차·시간 재척도)"만 수식으로 적는다. 코드 walkthrough는 하지 않으며
     전체 구현은 Code Availability(P_in.py, P_myo.py) 참조. -->

§3.1.3의 입구 압력파형 $P_\text{in}(t)$와 관상동맥 출구 BC의 심근압 $P_\text{myo}(t)$를 생성하는 절차 중, 표준 모델(RCR Windkessel [cite: westerhof2009windkessel], 시간가변 elastance [cite: suga1973elastance], 관상동맥 lumped BC [cite: kim2010coronary])에서 **본 연구가 특정하게 선택·구현한 부분**만 기술한다. 전체 구현은 공개 코드(`P_in.py`, `P_myo.py`)에 있다.

## B.1 입구 압력파형: RCR 적합

고정된 관상동맥 유입파형 $Q(t)$에 대해 3-요소 Windkessel을 다음 ODE로 적분한다:

$$\frac{dP_c}{dt} = -\frac{1}{\tau}\,(P_c - P_d) + \frac{Q(t)}{C}, \qquad P(t) = R_p\,Q(t) + P_c(t),$$

여기서 $\tau$는 샘플링된 이완기 시간상수, $C=\tau/R_d$이다. 본 연구의 선택은 다음과 같다:

1. **관상동맥 비 제약**: $R_p/R_d = 1/10$로 고정 (SimVascular 관상동맥 기준 $R_p\approx140$, $R_d\approx1415$) [cite: kim2010coronary].
2. **압력 정합 적합**: 결정변수 $(P_d,\ \ln R_d)$를, 주기적으로 수렴한 last-cycle 압력의 최대·최소가 목표 $(P_\text{sys},\ P_\text{dia})$에 맞도록 정규화 잔차

   $$r = \left[\frac{\max_t P - P_\text{sys}}{|P_\text{sys}|},\ \frac{\min_t P - P_\text{dia}}{|P_\text{dia}|}\right]$$

   를 최소화하는 비선형 최소제곱으로 결정한다. $P_\text{dia}=P_\text{sys}-\Delta P$.
3. **주기 수렴**: 한 심박의 $Q(t)$를 $n$ cycle 반복해 forward Euler로 적분하고, 직전 cycle의 말단 $P_c$를 다음 cycle 초기값으로 이어 주기정상상태의 마지막 cycle을 취한다.
4. **시간 척도·단위**: 시간축을 $T=60/\text{HR}$로 스케일하고, 압력은 mmHg→dyn/cm²($\times1333.22$)로 변환해 solver 입력으로 저장한다.

결과적으로 $P_\text{in}(t)$는 $(P_\text{sys},\ \Delta P,\ \tau)$ 세 변수에 의해 유일하게 결정된다.

## B.2 심근압: lumped 심장 모델

관상동맥 출구 BC의 압박항 $P_\text{myo}(t)$는 시간가변 elastance $E(t)$ 기반 lumped 심장 모델의 **심실압**으로 둔다($P_\text{myo}\approx P_\text{LV}$) [cite: kim2010coronary]. 본 연구의 구현 선택:

1. **Elastance 시간 재척도(two-zone)**: 정규화 elastance $e(x)$($x=t/t_\text{sys}$, $y=E/E_\text{max}$)를 수축기/이완기 두 구간으로 나눠 실제 시간으로 사상한다:

   $$x\in[0,1]\ \to\ t\in[0,t_\text{sys}], \qquad x\in[1,x_\text{max}]\ \to\ t\in[t_\text{sys},\,T],$$

   $E(t)=E_\text{max}\,e(x)$. 심실압 $P_\text{LV}(t)=E(t)\,V_\text{LV}(t)$.
2. **심장 ODE**: 심방–심실–대동맥 lumped 회로를 판막(승모판·대동맥판) 다이오드 로직과 함께 trapezoidal 적분으로 풀며, 대동맥압 afterload로 B.1의 $P_\text{in}(t)$를 사용한다. 주기정상상태의 마지막 cycle 심실압을 $P_\text{myo}(t)$로 추출한다.
3. **주요 상수**: $E_\text{max}=2.0$ mmHg/mL, 심박출량 $5$ L/min, $t_\text{sys}=0.4$ s, HR$=60$ bpm (심방 elastance·저항·관성 등 나머지 회로 상수는 공개 코드 참조).

<!-- 〔TODO〕 ① BC 파라미터 결과값 표(R_p, R_d, C, P_d 또는 대표 case) → 본문 Table 〔X〕와 연결.
     ② 유입파형 Q(t) 출처/형상 1문장 + 인용.
     ③ elastance 정규화 곡선 e(x) 출처 인용([cite: stergiopulos1996elastance] 보완 가능). -->
