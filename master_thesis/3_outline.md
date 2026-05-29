# Outline  (workflow step 3)

이 파일은 두 phase로 채운다. **Phase A를 먼저 통과시킨 뒤** Phase B로 넘어간다.

## Phase A — Skeleton (논리 점검)
문단(paragraph)마다 **주장 한 문장**씩. 소제목·번호·하위항목 없이 주장 문장만.
이 문장들을 위→아래로 이어 읽었을 때 논리가 점프 없이 흐르는지 확인한다.

[Intro]
1. 관상동맥 플라크 파열은 ACS의 주원인이고 심혈관 사망 부담이 크다.
2. 파열 위험은 임상/병리·혈류역학·생체역학(형태+재료) 세 인자군이 복합 작용해 결정된다.
3. 그러나 기존 전산 연구는 형태단독·정상상태·소표본이라, 세 인자군을 맥동 FSI로 동시에 본 적이 없다.   ← gap
4. 본 연구는 (선행 검증된) 비용효율 FSI를 활용해 1,000-sample로 세 인자군을 동시에 분석하고,
   ΔPSS 기반 지표의 임상 타당성과 재료물성의 지배성을 규명한다.   ← 핵심메시지

[Methods]
5. 분석은 4단계(데이터생성→VI선정→GPR surrogate→Sobol)로 구성된다.
6. 데이터는 선행 논문에서 검증된 비용효율 맥동 FSI로 생성한다(도구, 인용).
7. 두 표현형(LAP 3도메인 / CP 4도메인)을 각각 모델링하고, FC 두께는 균일 가정해 단일 스칼라 변수로 변동시킨다.
8. 입력은 형태·혈류역학·재료 3군으로 1,000-sample 설계공간을 이룬다.
9. 출력은 PSS·ΔPSS(구면평균)와 파열위치 지수로 측정한다.
10. 취약성지수 VI=stress/strength로, stress 2종 × strength 3시나리오 = 6개 후보를 만든다.
11. 6개를 7개 임상기준의 부호일치로 선별해 VI1=ΔPSS/E_FC^0.5, VI2=ΔPSS/E_FC^1.0을 채택한다.
12. 최종 VI에 GPR surrogate를 학습한다(LAP 784 / CP 727 유효쌍).
13. Sobol 1차·전차 지수로 민감도를 분석한다.

[Results]
14. 6개 후보의 기준별 부호를 검토하면 2개만 7기준을 전부 만족한다(11의 근거).
15. 민감도 결과 재료물성이 지배적이며 상위 4인자는 E_vessel·E_FC·수축기압·맥압이다(Material>Hemo>Morpho).
16. (optional) 파열위치는 원주방향 shoulder-dominant(임상·시뮬 일치)이나, 축방향은 임상 proximal vs 시뮬 distal로 어긋난다.

[Discussion]
17. ΔPSS가 PSS보다 강한 예측인자다 → 맥동성(피로)이 중요하다.
18. strength 정규화가 필요하다(재료가 분모로 들어가야, α>0).
19. 재료>혈류역학>형태 순의 지배성은 임상 위험 층화에 함의(형태보다 OCT 기반 강성 특성화가 정보가치 큼).
20. 축방향 파열위치 불일치는 FC두께 균일 가정의 한계로 설명된다.
21. 한계: 균일 FC두께·이상화 geometry·선형탄성.

[Conclusion]
22. 비용효율 FSI 활용으로 세 인자군 동시 대규모 분석이 가능했고, ΔPSS 임상 타당성·재료물성 지배성을 규명했다.

> ⚠️ 논리 점검 메모: 11(Methods에서 VI 확정)의 근거가 14(Results)에 있어 **앞으로 참조(forward reference)**가
> 생긴다. 의도된 구조면 OK지만 "Methods에서 결과를 미리 단정"으로 보일 수 있어 Phase B에서 표현을 주의한다.

---

## Phase B — Outline (구조 확장)
Phase A가 논리적으로 흐르면, 소제목(2.1, 2.2 ...) 구조로 확장한다. Intro → Conclusion.

0. Abstract

1. Introduction
    - Motivation: why does coronary plaque rupture matter? (leading cause of ACS; WHO burden)
    - 3 factors categories governing rupture risk: 
        clinical/pathological, hemodynamic, biomechanical (morpho + material)
    - Prior computational studies: limited to morphology-only, steady-state, or small sample sizes; no study covers all three factor groups simultaneously with pulsatile FSI
    - Novelty (findings-first — the cost-effective FSI method itself is prior work, cited as a tool [cite]):
        (a) Leveraging our previously-validated cost-effective FSI [cite], the FIRST study to cover all three
            factor groups (morphological, hemodynamic, material) simultaneously at 1,000-sample scale under pulsatile conditions
        (b) Pulsatile simulation yields both PSS (monotonic) and ΔPSS (fatigue) scenarios → finding: ΔPSS-based VI is clinically more appropriate
        (c) First Sobol sensitivity analysis across morphological + hemodynamic + material parameters simultaneously → finding: material is the dominant factor

2. Methods
    - Overview: four-stage framework —
        (1) dataset generation via cost-effective pulsatile FSI,
        (2) formulation and clinical screening of vulnerability indices (6 → 2 final),
        (3) GPR surrogate training on the finalized VIs, and
        (4) Sobol sensitivity analysis.

    2.1 Cost-effective FSI  (TOOL — method published in prior work [cite]; NOT re-claimed as novelty)
        - Framework: brief recap of the previously-validated method (cite prior paper)
        - Validation (3 geometries): journal → condense / cite prior paper;
          thesis → include full validation geometries (학위논문용)

    2.2 Dataset Generation                                       [Stage 1]
        Idealized Coronary Artery Model
        - Two plaque phenotypes analyzed separately:
            - LAP (Low Attenuation Plaque): 3 solid domains = vessel wall, fibrous cap (FC), lipid core
            - CP  (Calcified Plaque):        4 solid domains = vessel wall, fibrous cap (FC), lipid core, calcification
        - FC thickness assumed spatially uniform (globally constant)
          → Justification: allows fc thickness to be treated as a single scalar input variable,
            enabling systematic parametric variation across the 1,000-sample design space
    
        2.2.1 Input Parameters
            - Morphological parameters
            - Hemodynamic parameters
            - Material properties

        2.2.2 Geometry construction and meshing
        2.2.3 Boundary conditions
        2.2.4 Computational details
        2.2.5 Output Parameters
            - Stress metrics
                - Plaque Structure Stress (PSS): peak systolic stress
                - ΔPSS: stress amplitude (PSS_systolic − PSS_diastolic), fatigue scenario
                - Sphere-averaging method for spatial reduction

    2.3 Vulnerability Index Formulation                          [Stage 2]
        2.3.1 Strength metrics
            - Three scenarios: ultimate stress, ultimate strain, density-based E
            - With linear elastic assumption: Strength ~ E_FC^α, α = {0.0, 0.5, 1.0}
        2.3.2 Vulnerability Index (VI) definition
            - VI = Stress / Strength → 6 candidates: stress = {PSS, ΔPSS} × α = {0.0, 0.5, 1.0}
        2.3.3 Rupture location index
            - argmax over fibrous-cap nodes (set by the stress field; strength is node-wise constant)
        2.3.4 Seven-criterion screening → final metric
            - Screen the 6 candidates by the SIGN of each parameter–VI correlation
              against the expected clinical direction; admissible = satisfies all 7.
            - Decision (finalized here): VI1 = ΔPSS / E_FC^0.5 and VI2 = ΔPSS / E_FC^1.0
              are confirmed as the final vulnerability metrics.
              (Per-criterion pass/fail rationale → Results 3.1.)
            #high-rupture-risk features (selection rubric):
                1. Collagen-deficient fibrous cap → Low E_FC
                2. Soft plaque                   → Low E_lipid, E_vessel
                3. Large lipid arc angle          → High lipid arc angle
                4. Large plaque burden            → High lipid volume
                5. High ΔFFR / WSS               → High ΔFFR, WSS
                6. Non-calcified (soft) plaque    → Low calcification volume
                7. Thin fibrous cap               → Low FC thickness

    2.4 GPR Surrogate                                            [Stage 3]
        - Trained on the finalized VIs only (VI1, VI2; input → VI mapping)
        - LAP: 784 / 1,000 valid input–output pairs
        - CP:  727 / 1,000 valid input–output pairs

    2.5 Sensitivity Analysis                                     [Stage 4]
        - Sobol indices: first-order (S1) and total-order (S_total)

3. Results

    3.1 Vulnerability Index Selection — per-criterion rationale
        - Criterion-by-criterion evidence for all 6 candidates against the 7 clinical features:
          which candidate satisfies / violates each criterion, with directionality reasoning (the "why")
        - Confirms the two metrics finalized in Methods §2.3.4:
            - VI1 = ΔPSS / E_FC^0.5
            - VI2 = ΔPSS / E_FC^1.0

    3.2 Sensitivity Analysis Results
        - Sobol indices for VI1 and VI2 (LAP and CP separately)
        - Top 4 dominant parameters (both VIs): E_vessel, E_FC, systolic pressure, pulse pressure
        - Factor importance ranking: Material > Hemodynamic > Morphological

    3.3 Rupture Location (supplementary / optional)
        - Circumferential: shoulder-dominant in both clinical data and simulation results
        - Axial: proximal-dominant in clinical data; simulation shows distal-dominant
          → Discrepancy explained by constant-FC-thickness assumption:
            WSS-driven proximal FC thinning is not captured → stated limitation

4. Discussion
    4.1 ΔPSS > PSS: pulsatility is critical; stress amplitude is a stronger rupture predictor than peak stress alone
    4.2 Strength Normalization - strength matters (material enters VI denominator → α > 0 required)
    4.3 Material > Hemodynamic > Morphological: implications for clinical risk stratification
        - E_vessel and E_FC are the dominant determinants → material characterization (e.g., OCT-based stiffness) is more informative than geometry alone
    4.4 Rupture location - clincial vs our data.
    4.5 Limitations
        - Globally constant FC thickness
        - Idealized geometry (no patient-specific tortuosity, side branches)
        - Linear elastic material model

5. Conclusion
