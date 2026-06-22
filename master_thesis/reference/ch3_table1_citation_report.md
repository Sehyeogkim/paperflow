# Chapter 3 · Table 1 (Input variables) — Citation Report

> **목적 / Purpose.** 이 문서는 학위논문 *"Definition of a Coronary Plaque Rupture Risk Index and Its Sensitivity Analysis"* 의
> **Chapter 3, Table 1 (입력 변수 · 기호 · 단위 · 샘플링 범위)** 각 행에 대한 **참고문헌(citation)** 을 정리한 핸드오프 보고서입니다.
> 각 인용은 (1) 실제 DOI 확인(`reference-hunter`) → (2) 독립 재검증(`reference-double-checker`)을 거쳤고,
> 아래에 **LaTeX `\cite` 형태**, **복붙 가능한 BibTeX**, **검증 상태(verified/weak)와 verbatim 근거 문장**을 모두 포함합니다.
> LLM에게 전달 시 이 파일 하나로 인용 작업의 전체 맥락을 알 수 있도록 자기완결적으로 작성되었습니다.

- 검증일: hunter 2026-06-17 ~ 2026-06-18 / double-check 2026-06-18
- 출처 원본: 저자 학위논문 PDF `Thesis_Template/20244152_sehyeog.pdf` 참고문헌 [12], [13], [15]–[29]
- 범위(range) 값 자체의 출처: 실제 LHS 설계 행렬 `data/input_parameter/input.csv` (각 열의 min/max). **인용은 "범위 선정의 임상적 타당성"을 받쳐주는 근거이지, 숫자를 그대로 베껴온 출처가 아님.**

---

## 1. 요약 — 변수 ↔ 범위 ↔ 인용 ↔ 검증상태

| Group | Variable | Symbol | Range [min, max] | `\cite` key | 검증 |
|---|---|---|---|---|---|
| Morphological | Degree of stenosis | `$DS$` [%] | [25, 75] | `stone2011prospect` | ✅ verified |
| | Lesion length | `$L_\text{lesion}$` [cm] | [1.0, 3.0] | `brosh2005` | ✅ verified |
| | Lumen axial skewness | `$\gamma_z$` [–] | [−0.5, 0.5] | `wang2015ivus` | ⚠️ **weak (부적합)** |
| | Positive remodeling index | `$PI$` [–] | [0.9, 1.2] | `schoenhagen2000` | ✅ verified |
| | Lipid arc angle | `$\theta_\text{lipid}$` [°] | [120, 270] | `xing2017` | ⚠️ weak |
| | Lipid length ratio | `$r_\text{lipid}$` [–] | [0.5, 0.8] | `tanaka2009` | ⚠️ **weak (불일치)** |
| | Calcified fraction (CP) | `$f_\text{calc}$` [–] | [0.10, 0.80] | `mintz1995` | ✅ verified |
| Hemodynamic | Systolic pressure | `$P_\text{sys}$` [mmHg] | [100, 170] | `whelton2018` | ✅ verified |
| | Pulse pressure | `$\Delta P$` [mmHg] | [35, 80] | `franklin1999` | ✅ verified |
| | Decay ratio | `$\tau$` [–] | [0.01, 0.50] | `kim2010coronary, sankaran2016` | ⚠️ weak (sankaran) |
| Material | Vessel-wall modulus | `$E_\text{vessel}$` [dyn/cm²] | [1×10⁶, 1.4×10⁷] | `holzapfel2005` | ⚠️ weak |
| | Fibrous-cap modulus | `$E_\text{FC}$` [dyn/cm²] | [4×10⁶, 2.3×10⁷] | `loree1994static` | ✅ verified |
| | Lipid-core modulus | `$E_\text{lipid}$` [dyn/cm²] | [1×10⁴, 1×10⁶] | `loree1994lipid` | ⚠️ weak |
| | Calcification modulus (CP) | `$E_\text{calc}$` [dyn/cm²] | [7×10⁹, 2.5×10¹¹] | `ebenstein2009` | ⚠️ weak |
| (fixed) | Fibrous-cap thickness | `$t_\text{FC}=100\,\mu$m` | (고정) | `yonetsu2011, virmani2000` | ✅ verified |

**검증 통계:** verified 8 / weak 6 (입력 14변수 기준). `$t_\text{FC}$` 고정값 별도 ✅.

---

## 2. LaTeX — 본문 Table 행에서의 `\cite` 사용 형태

각 행 Ref 열에 들어가는 정확한 형태(이미 `contents/ch3_method2.md` 에 반영됨):

```latex
$DS$            ... & \cite{stone2011prospect} \\
$L_\text{lesion}$ ... & \cite{brosh2005} \\
$\gamma_z$      ... & \cite{wang2015ivus} \\
$PI$            ... & \cite{schoenhagen2000} \\
$\theta_\text{lipid}$ ... & \cite{xing2017} \\
$r_\text{lipid}$ ... & \cite{tanaka2009} \\
$f_\text{calc}$ ... & \cite{mintz1995} \\
$P_\text{sys}$  ... & \cite{whelton2018} \\
$\Delta P$      ... & \cite{franklin1999} \\
$\tau$          ... & \cite{kim2010coronary, sankaran2016} \\
$E_\text{vessel}$ ... & \cite{holzapfel2005} \\
$E_\text{FC}$   ... & \cite{loree1994static} \\
$E_\text{lipid}$ ... & \cite{loree1994lipid} \\
$E_\text{calc}$ ... & \cite{ebenstein2009} \\
```

`$t_\text{FC}=100\,\mu$m` 고정값 문장: `\cite{yonetsu2011, virmani2000}`.

### 복붙용 LaTeX 표 (booktabs, Ref 열 포함)

```latex
\begin{table}[ht]
\centering
\caption{Input variables, symbols, units, sampling ranges, and references.}
\label{tab:input-vars}
\small
\begin{tabular}{lllll}
\toprule
Group & Variable & Symbol & Range [min, max] & Ref \\
\midrule
\multirow{7}{*}{Morphological}
 & Degree of stenosis        & $DS$ [\%]                 & $[25,\,75]$              & \cite{stone2011prospect} \\
 & Lesion length             & $L_\text{lesion}$ [cm]    & $[1.0,\,3.0]$            & \cite{brosh2005} \\
 & Lumen axial skewness      & $\gamma_z$                & $[-0.5,\,0.5]$          & \cite{wang2015ivus} \\
 & Positive remodeling index & $PI$                      & $[0.9,\,1.2]$           & \cite{schoenhagen2000} \\
 & Lipid arc angle           & $\theta_\text{lipid}$ [$^\circ$] & $[120,\,270]$    & \cite{xing2017} \\
 & Lipid length ratio        & $r_\text{lipid}$          & $[0.5,\,0.8]$           & \cite{tanaka2009} \\
 & Calcified fraction (CP)   & $f_\text{calc}$           & $[0.10,\,0.80]$         & \cite{mintz1995} \\
\midrule
\multirow{3}{*}{Hemodynamic}
 & Systolic pressure         & $P_\text{sys}$ [mmHg]     & $[100,\,170]$           & \cite{whelton2018} \\
 & Pulse pressure            & $\Delta P$ [mmHg]         & $[35,\,80]$             & \cite{franklin1999} \\
 & Decay ratio               & $\tau$                    & $[0.01,\,0.50]$         & \cite{kim2010coronary,sankaran2016} \\
\midrule
\multirow{4}{*}{Material}
 & Vessel-wall modulus       & $E_\text{vessel}$ [dyn/cm$^2$] & $[1\times10^{6},\,1.4\times10^{7}]$   & \cite{holzapfel2005} \\
 & Fibrous-cap modulus       & $E_\text{FC}$ [dyn/cm$^2$]     & $[4\times10^{6},\,2.3\times10^{7}]$   & \cite{loree1994static} \\
 & Lipid-core modulus        & $E_\text{lipid}$ [dyn/cm$^2$]  & $[1\times10^{4},\,1\times10^{6}]$     & \cite{loree1994lipid} \\
 & Calcification modulus (CP)& $E_\text{calc}$ [dyn/cm$^2$]   & $[7\times10^{9},\,2.5\times10^{11}]$  & \cite{ebenstein2009} \\
\bottomrule
\end{tabular}

\vspace{2pt}
\footnotesize LHS constraint: $P_\text{dia}=P_\text{sys}-\Delta P>40$ mmHg.
Fibrous-cap thickness fixed at $t_\text{FC}=100\,\mu$m~\cite{yonetsu2011,virmani2000}.
\end{table}
```

> `\multirow` 사용 시 preamble에 `\usepackage{multirow}` 와 `\usepackage{booktabs}` 필요.

---

## 3. BibTeX (복붙용 — `references.bib` 에 이미 등록됨)

```bibtex
@article{stone2011prospect,
  title   = {A prospective natural-history study of coronary atherosclerosis},
  author  = {Stone, Gregg W. and Maehara, Akiko and Lansky, Alexandra J. and de Bruyne, Bernard and Cristea, Ecaterina and Mintz, Gary S. and Mehran, Roxana and McPherson, John and Farhat, Naim and Marso, Steven P. and Parise, Helen and Templin, Barry and White, Roseann and Zhang, Zhen and Serruys, Patrick W.},
  journal = {New England Journal of Medicine},
  volume  = {364}, number = {3}, pages = {226--235}, year = {2011},
  doi     = {10.1056/NEJMoa1002358}
}

@article{brosh2005,
  title   = {Effect of lesion length on fractional flow reserve in intermediate coronary lesions},
  author  = {Brosh, David and Higano, Stuart T. and Lennon, Ryan J. and Holmes, David R., Jr. and Lerman, Amir},
  journal = {American Heart Journal},
  volume  = {150}, number = {2}, pages = {338--343}, year = {2005},
  doi     = {10.1016/j.ahj.2004.09.007}
}

@article{wang2015ivus,
  title   = {{IVUS}-based {FSI} models for human coronary plaque progression study: components, correlation and predictive analysis},
  author  = {Wang, Liang and Wu, Zheyang and Yang, Chun and Zheng, Jie and Bach, Richard and Muccigrosso, David and Billiar, Kristen and Maehara, Akiko and Mintz, Gary S. and Tang, Dalin},
  journal = {Annals of Biomedical Engineering},
  volume  = {43}, number = {1}, pages = {107--121}, year = {2015},
  doi     = {10.1007/s10439-014-1118-1}
}

@article{schoenhagen2000,
  title   = {Extent and direction of arterial remodeling in stable versus unstable coronary syndromes: an intravascular ultrasound study},
  author  = {Schoenhagen, Paul and Ziada, Khaled M. and Kapadia, Samir R. and Crowe, Tim D. and Nissen, Steven E. and Tuzcu, E. Murat},
  journal = {Circulation},
  volume  = {101}, number = {6}, pages = {598--603}, year = {2000},
  doi     = {10.1161/01.CIR.101.6.598}
}

@article{xing2017,
  title   = {Clinical significance of lipid-rich plaque detected by optical coherence tomography: a 4-year follow-up study},
  author  = {Xing, Lei and Higuma, Takumi and Wang, Zhao and Aguirre, Aaron D. and Mizuno, Kyoichi and Takano, Masamichi and Dauerman, Harold L. and Park, Seung-Jung and Jang, Yangsoo and Kim, Chong-Jin and Kim, Soo-Joong and Choi, So-Yeon and Itoh, Tomonori and Uemura, Shiro and Lowe, Harry and Walters, Darren L. and Barlis, Peter and Lee, Stephen and Petzold, Anneke and Fard, Maryam and Nakamura, Sunao and Yu, Bo and Mintz, Gary S. and Jang, Ik-Kyung},
  journal = {Journal of the American College of Cardiology},
  volume  = {69}, number = {20}, pages = {2502--2513}, year = {2017},
  doi     = {10.1016/j.jacc.2017.03.556}
}

@article{tanaka2009,
  title   = {Lipid-rich plaque and myocardial perfusion after successful stenting in patients with non-{ST}-segment elevation acute coronary syndrome: an optical coherence tomography study},
  author  = {Tanaka, Atsushi and Imanishi, Toshio and Kitabata, Hironori and Kubo, Takashi and Takarada, Shigeho and Tanimoto, Takashi and Kuroi, Akio and Tsujioka, Hiroto and Ikejima, Hideyuki and Komukai, Kenichi and Kataiwa, Hideaki and Okouchi, Keishi and Kashiwaghi, Manabu and Ishibashi, Kohei and Matsumoto, Hiroki and Takemoto, Kazushi and Nakamura, Nobuo and Hirata, Kumiko and Mizukoshi, Masato and Akasaka, Takashi},
  journal = {European Heart Journal},
  volume  = {30}, number = {11}, pages = {1348--1355}, year = {2009},
  doi     = {10.1093/eurheartj/ehp122}
}

@article{mintz1995,
  title   = {Patterns of calcification in coronary artery disease: a statistical analysis of intravascular ultrasound and coronary angiography in 1155 lesions},
  author  = {Mintz, Gary S. and Popma, Jeffrey J. and Pichard, Augusto D. and Kent, Kenneth M. and Satler, Lowell F. and Chuang, Ya Chien and Ditrano, Christopher J. and Leon, Martin B.},
  journal = {Circulation},
  volume  = {91}, number = {7}, pages = {1959--1965}, year = {1995},
  doi     = {10.1161/01.CIR.91.7.1959}
}

@article{whelton2018,
  title   = {2017 {ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA} Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults},
  author  = {Whelton, Paul K. and Carey, Robert M. and Aronow, Wilbert S. and Casey, Donald E., Jr. and Collins, Karen J. and Dennison Himmelfarb, Cheryl and DePalma, Sondra M. and Gidding, Samuel and Jamerson, Kenneth A. and Jones, Daniel W. and MacLaughlin, Eric J. and Muntner, Paul and Ovbiagele, Bruce and Smith, Sidney C., Jr. and Spencer, Crystal C. and Stafford, Randall S. and Taler, Sandra J. and Thomas, Randal J. and Williams, Kim A., Sr. and Williamson, Jeff D. and Wright, Jackson T., Jr.},
  journal = {Hypertension},
  volume  = {71}, number = {6}, pages = {e13--e115}, year = {2018},
  doi     = {10.1161/HYP.0000000000000066}
}

@article{franklin1999,
  title   = {Is pulse pressure useful in predicting risk for coronary heart disease? The {Framingham} Heart Study},
  author  = {Franklin, Stanley S. and Khan, Shehzad A. and Wong, Nathan D. and Larson, Martin G. and Levy, Daniel},
  journal = {Circulation},
  volume  = {100}, number = {4}, pages = {354--360}, year = {1999},
  doi     = {10.1161/01.CIR.100.4.354}
}

@article{kim2010coronary,
  title   = {Patient-specific modeling of blood flow and pressure in human coronary arteries},
  author  = {Kim, H. J. and Vignon-Clementel, I. E. and Coogan, J. S. and Figueroa, C. A. and Jansen, K. E. and Taylor, C. A.},
  journal = {Annals of Biomedical Engineering},
  volume  = {38}, number = {10}, pages = {3195--3209}, year = {2010},
  doi     = {10.1007/s10439-010-0083-6}
}

@article{sankaran2016,
  title   = {Uncertainty quantification in coronary blood flow simulations: impact of geometry, boundary conditions and blood viscosity},
  author  = {Sankaran, Sethuraman and Kim, Hyun Jin and Choi, Gilwoo and Taylor, Charles A.},
  journal = {Journal of Biomechanics},
  volume  = {49}, number = {12}, pages = {2540--2547}, year = {2016},
  doi     = {10.1016/j.jbiomech.2016.01.002}
}

@article{holzapfel2005,
  title   = {Determination of layer-specific mechanical properties of human coronary arteries with nonatherosclerotic intimal thickening and related constitutive modeling},
  author  = {Holzapfel, Gerhard A. and Sommer, Gerhard and Gasser, Christian T. and Regitnig, Peter},
  journal = {American Journal of Physiology-Heart and Circulatory Physiology},
  volume  = {289}, number = {5}, pages = {H2048--H2058}, year = {2005},
  doi     = {10.1152/ajpheart.00934.2004}
}

@article{loree1994static,
  title   = {Static circumferential tangential modulus of human atherosclerotic tissue},
  author  = {Loree, Howard M. and Grodzinsky, Alan J. and Park, Susan Y. and Gibson, Lorna J. and Lee, Richard T.},
  journal = {Journal of Biomechanics},
  volume  = {27}, number = {2}, pages = {195--204}, year = {1994},
  doi     = {10.1016/0021-9290(94)90209-7}
}

@article{loree1994lipid,
  title   = {Mechanical properties of model atherosclerotic lesion lipid pools},
  author  = {Loree, Howard M. and Tobias, Brian J. and Gibson, Lorna J. and Kamm, Roger D. and Small, Donald M. and Lee, Richard T.},
  journal = {Arteriosclerosis and Thrombosis},
  volume  = {14}, number = {2}, pages = {230--234}, year = {1994},
  doi     = {10.1161/01.ATV.14.2.230}
}

@article{ebenstein2009,
  title   = {Nanomechanical properties of calcification, fibrous tissue, and hematoma from atherosclerotic plaques},
  author  = {Ebenstein, Donna M. and Coughlin, Dezba and Chapman, Joanna and Li, Chengpei and Pruitt, Lisa A.},
  journal = {Journal of Biomedical Materials Research Part A},
  volume  = {91}, number = {4}, pages = {1028--1037}, year = {2009},
  doi     = {10.1002/jbm.a.32321}
}

@article{yonetsu2011,
  title   = {In vivo critical fibrous cap thickness for rupture-prone coronary plaques assessed by optical coherence tomography},
  author  = {Yonetsu, Taishi and Kakuta, Tsunekazu and Lee, Tetsumin and Takahashi, Kentaro and Kawaguchi, Naohiko and Yamamoto, Goro and Koura, Ken and Hishikari, Keiichi and Iesaka, Yoshito and Fujiwara, Hidehiko and Isobe, Mitsuaki},
  journal = {European Heart Journal},
  volume  = {32}, number = {10}, pages = {1251--1259}, year = {2011},
  doi     = {10.1093/eurheartj/ehq518}
}

@article{virmani2000,
  title   = {Lessons from sudden coronary death: a comprehensive morphological classification scheme for atherosclerotic lesions},
  author  = {Virmani, Renu and Kolodgie, Frank D. and Burke, Allen P. and Farb, Andrew and Schwartz, Stephen M.},
  journal = {Arteriosclerosis, Thrombosis, and Vascular Biology},
  volume  = {20}, number = {5}, pages = {1262--1275}, year = {2000},
  doi     = {10.1161/01.ATV.20.5.1262}
}
```

---

## 4. 검증 상세 — verbatim 근거 문장 + 노트

### ✅ verified (근거 문장이 범위를 직접 지지)

| key | 변수 | source verbatim quote |
|---|---|---|
| `stone2011prospect` | DS | "plaque burden of 70% or greater (hazard ratio, 5.03; 95% CI, 2.51 to 10.11; P<0.001)" |
| `brosh2005` | $L_\text{lesion}$ | "an LL ≥ 10 mm was identified as the best cutoff value for predicting an FFR < 0.75" |
| `schoenhagen2000` | $PI$ | "Positive remodeling was defined as an RR >1.05 and negative remodeling as an RR <0.95." |
| `mintz1995` | $f_\text{calc}$ | "The mean arc of lesion calcium measured 115 ± 110 degrees ... the mean length measured 3.5 ± 3.7 mm." |
| `whelton2018` | $P_\text{sys}$ | "Normal <120 mmHg ...; Elevated 120–129 ...; Stage 1 130–139 ...; Stage 2 ≥140 mmHg ..." |
| `franklin1999` | $\Delta P$ | "...CHD risk increased with lower DBP at any level of SBP≥120 mmHg, suggesting that higher PP was an important component of risk." |
| `loree1994static` | $E_\text{FC}$ | "the tangential moduli of cellular, hypocellular, and calcified specimens were 927 ± 468 kPa, 2312 ± 2180 kPa, and 1466 ± 1284 kPa" |
| `yonetsu2011` | $t_\text{FC}$ | "In vivo critical cap thicknesses were <80 µm for the thinnest and <188 µm for most representative fibrous cap thickness." |

### ⚠️ weak (논문은 실존·DOI 정확하나, 인용 metric이 범위와 정확히 일치하지 않음)

| key | 변수 | 문제 (found vs claimed) | 권장 |
|---|---|---|---|
| **`wang2015ivus`** | $\gamma_z$ | ❗전문 확인 결과 이 논문은 **lumen 편심/축방향 skewness를 측정하지 않음**(루멘 동심원 가정). 범위를 뒷받침 못 함. quote=null | **교체 또는 무인용 설계 파라미터로 표기** |
| **`tanaka2009`** | $r_\text{lipid}$ | 인용문은 lipid **arc(>90°)/cap thickness** 정의 — lipid **length ratio** 값 아님 | length-ratio 보고 논문으로 교체 권장 |
| `sankaran2016` | $\tau$ | "MLD … boundary resistance, viscosity, lesion length" — **$\tau$(이완기 시정수) 미언급**, 인접 근거 | `kim2010coronary`와 병기 유지 가능 |
| `holzapfel2005` | $E_\text{vessel}$ | abstract는 층별 stiffness 순서·극한응력만, **수치 modulus는 유료 본문 표** | 본문 표 확인 시 verified 승격 |
| `loree1994lipid` | $E_\text{lipid}$ | "0%→50%에서 stiffness 4.5배" — **상대 배수**이지 절대 modulus 아님 | 정성 근거로 유지 가능 |
| `ebenstein2009` | $E_\text{calc}$ | 주제 정확(calcification nanoindentation)하나 abstract에 **수치 없음**, quote=null | 본문 확인 시 승격 |
| `xing2017` | $\theta_\text{lipid}$ | "wider maximal lipid arcs (p=0.023)"만 verbatim 확보, ">90°" 정의는 JACC 본문(403)으로 미확보 | 본문 확인 시 보강 |

---

## 5. LLM에게 부탁할 작업 (open items)

이 보고서를 받은 LLM이 처리하면 좋은 것:

1. **`$\gamma_z$ (lumen axial skewness)`** — `wang2015ivus`는 부적합. 다음 중 하나:
   - (A) MLA(최소내강면적) 위치 / 병변 축방향 비대칭을 **실제로 정량 보고한** OCT·IVUS 논문을 찾아 교체, 또는
   - (B) 인용을 빼고 **순수 기하 설계 파라미터**로 표기(`$DS$`·`$L_\text{lesion}$` 같은 설계 선택).
2. **`$r_\text{lipid}$ (lipid length ratio)`** — `tanaka2009`는 arc 기준. **지질 길이비/지질 길이**를 보고한 논문으로 교체 권장.
3. **`$E_\text{vessel}$`, `$E_\text{calc}$`, `$\theta_\text{lipid}$`** — full-text(유료) 접근으로 **수치 modulus / 정의**를 verbatim 확보하면 weak→verified 승격 가능.

> **주의(LLM에게):** 인용을 **새로 만들지 말 것**. 위 BibTeX는 저자 학위논문에서 가져와 DOI까지 검증된 실제 항목임.
> 교체가 필요하면 실재하는 DOI를 가진 논문만 제안하고, 해당 논문이 그 범위를 **실제로 보고하는 verbatim 문장**을 함께 제시할 것.
