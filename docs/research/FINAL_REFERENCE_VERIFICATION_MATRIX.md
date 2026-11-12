# Final reference verification matrix (Phase O)

Date: 2026-11-04 · revision `78ee339` · machine-readable record:
`outputs/final_literature/reference_verification.json`
Harness: `scripts/final_reference_verification.py` (live Crossref + OpenAlex + arXiv; nothing
confirmed from memory)

**41 candidates resolved: 37 VERIFIED, 3 AMBIGUOUS, 1 harness artifact.**
**7 references carried a wrong attribution and are corrected below. 2 must be dropped.**

Verification rule enforced by the harness: a record counts as a match only when at least one
claimed field was *checkable and checked* — claimed first author present in the author list,
year within ±1, venue prefix matching, or an expected title fragment present. A claim with
nothing comparable fails. Silence is not agreement.

---

## 1. Corrections — the repository asserted something the index does not support

These are the substantive findings of Phase O. Each must be applied before the manuscript cites
the work.

| # | Repository asserted | The index says | Action |
|---|---|---|---|
| **O-1** | "Clark & McCracken **2002**" | **Clark & McCracken 2001**, *Tests of equal forecast accuracy and encompassing for nested models*, Journal of Econometrics, `10.1016/S0304-4076(01)00071-9`, 876 citations | Correct the year to **2001** |
| **O-2** | "**Bailey 2014**" (rolling-window selection) | **No such work resolves.** The intended paper is **Inoue, Jin & Rossi 2017**, *Rolling window selection for out-of-sample forecasting with time-varying parameters*, Journal of Econometrics, `10.1016/j.jeconom.2016.03.006`, 286 citations | **Replace** with Inoue, Jin & Rossi 2017 |
| **O-3** | "LiveHouse-TS / **Chung** 2026" | **Wen, Zhou, Liu, Zhong & Liang 2026**, *LiveHouse-TS: An Open-world Living Benchmark for Time Series Foundation Models*, `arXiv:2608.17299` (preprint) | Paper is real; **correct the authors** and mark it **PP** |
| **O-4** | "**ACM CSUR 2025** survey" on selective prediction / abstention | **No such survey resolves.** The ACM CSUR hit on that query is *Selective Forgetting in Machine Learning* (machine unlearning — a different topic). The nearest real item is **He, Jiang & Xiao 2026**, *A Survey on Uncertainty Quantification Methods for Deep Learning*, ACM Computing Surveys, `10.1145/3786319`, 81 citations — a UQ survey, **not** a selective-prediction survey | **Drop** the claimed citation. The reject-option role is already correctly filled by Hendrickx et al. 2024. Cite He et al. 2026 only for UQ, and as **2026** |
| **O-5** | "**Taggart 2026**" (elicitability of quantiles) | **Taggart 2022**, *Point forecasting and forecast evaluation with generalized Huber loss*, Electronic Journal of Statistics, `10.1214/21-EJS1957`, 30 citations. The canonical elicitability result is **Gneiting 2011**, *Making and Evaluating Point Forecasts*, JASA, `10.1198/jasa.2011.r10138`, 1014 citations | Correct to **Taggart 2022**; add **Gneiting 2011** as the primary citation for the elicitability argument |
| **O-6** | "**Siew et al. 2025**" | No Siew first-author work resolves. Siew is a **co-author** of **Rodriguez-Fernandez, Sarangerel, Siew et al. 2024**, *Towards a Machine Learning-Based Approach to Predict Space Object Density Distributions*, AIAA SCITECH 2024, `10.2514/6.2024-1673`, 6 citations | **Correct** to Rodriguez-Fernandez et al. 2024, or drop |
| **O-7** | "Massimi **2023**… 37 citations" | **Massimi et al. 2024**, IET Radar, Sonar & Navigation, `10.1049/rsn2.12547`, **39** citations | Correct the year to **2024** |

## 2. Must be dropped, not softened

| Reference | Why |
|---|---|
| **SpotGEO challenge paper** | AMBIGUOUS after three independent attempts across Crossref, OpenAlex and arXiv. No record matching a SpotGEO challenge paper exists in any index. Only the **dataset deposit** is citable: **Chen, Liu & Chin 2020**, *spotGEO dataset*, Zenodo, `10.5281/zenodo.3874325` (**DS** — a deposit, not peer reviewed). Cite the deposit; make no claim about a challenge paper. |
| **"ACM CSUR 2025 selective-prediction survey"** | See **O-4**. The citation as written describes a work that does not exist. |

## 3. Newly resolved — previously recorded as unretrievable

| Reference | Record | Note |
|---|---|---|
| **DebrisWatch II** | **Blake, Cooke, Paragini et al. 2026**, *DebrisWatch II: Digging deeper for geosynchronous debris*, `arXiv:2605.27516` | The earlier OpenAlex record was truncated; it now resolves in full. It is a **preprint (PP)** — label it as such, not as peer reviewed |
| **DebrisWatch I** | **Blake, Chote, Pollacco et al. 2021**, Advances in Space Research, `10.1016/j.asr.2020.08.008`, 26 citations | Peer reviewed; the citable companion to the above |
| **Castet & Saleh 2009** | **Journal of Spacecraft and Rockets**, *Satellite Reliability: Statistical Data Analysis and Modeling*, `10.2514/1.42243`, 83 citations | Now resolved to the journal article. A separate book chapter (`10.1201/9780203859759.ch121`) exists; cite the **journal article** |

## 4. Verified without change

### 4.1 Load-bearing positioning references

| Ref | Record | Year | Venue | Review | Citations |
|---|---|---|---|---|---|
| R1 Zhou et al. | `10.1029/2025JA034593` | 2026 | JGR: Space Physics | PR | 0 |
| R2 He et al. | `10.1155/2024/8887634` | 2024 | Int. J. Aerospace Eng. | PR | 2 |
| R3 Salmaso et al. | `10.3390/aerospace10030297` | 2023 | Aerospace | PR | 17 |
| R15 Ruszczak et al. | `10.1038/s41597-025-05035-3` | 2025 | Scientific Data | PR | 47 |
| R20 Lu et al. | `10.1371/journal.pone.0360910` | 2026 | PLOS ONE | PR | 0 |
| R21 Zou et al. | `10.1016/j.mlwa.2026.101038` | 2026 | Mach. Learn. with Appl. | PR | 1 |
| R22 Barber et al. | `10.1214/23-AOS2276` | 2023 | Annals of Statistics | PR | **381** (was recorded as 352) |
| R23 Wang & Hyndman | `arXiv:2410.13115` | 2024 | arXiv | **PP** | — |
| R25 Henzi, Ziegel & Gneiting | `10.1111/rssb.12450` | 2021 | JRSS-B | PR | 55 |
| Caldas & Soares | `10.1016/j.actaastro.2024.03.072` | 2024 | Acta Astronautica | PR | **50** (was recorded as 53) |
| Herrmann et al. | `10.1007/s12567-023-00529-5` | 2024 | CEAS Space Journal | PR | 23 |
| Acciarini, Baydin & Izzo (ML-dSGP4) | `arXiv:2402.04830` | 2024 | arXiv | **PP** | — |

### 4.2 Selection / distribution-shift references

| Record | Year | Venue | Review | Citations |
|---|---|---|---|---|
| Gulrajani & López-Paz, *In Search of Lost Domain Generalization* `10.48550/arXiv.2007.01434` | 2020 | arXiv (also ICLR 2021) | PP/PR | 455 |
| Yao, Choi, Cao et al., *Wild-Time* `10.52202/068431-0749` | 2022 | NeurIPS 35 Datasets & Benchmarks | PR | 11 |
| Wen et al., *LiveHouse-TS* `arXiv:2608.17299` | 2026 | arXiv | **PP** | 0 |
| Clark & McCracken `10.1016/S0304-4076(01)00071-9` | **2001** | Journal of Econometrics | PR | 876 |
| Inoue, Jin & Rossi `10.1016/j.jeconom.2016.03.006` | **2017** | Journal of Econometrics | PR | 286 |

### 4.3 Conformal prediction

| Record | Year | Venue as resolved | Review | Citations |
|---|---|---|---|---|
| Gibbs & Candès, *Adaptive Conformal Inference Under Distribution Shift* `10.48550/arXiv.2106.00170` | 2021 | arXiv (commonly cited as NeurIPS 2021) | PP | 84 |
| Tibshirani, Barber, Candès & Ramdas, *Conformal Prediction Under Covariate Shift* `10.48550/arXiv.1904.06019` | 2019 | arXiv (commonly cited as NeurIPS 2019) | PP | 126 |
| Zaffran, Dieuleveut, Féron et al., *Adaptive Conformal Predictions for Time Series* `10.48550/arXiv.2202.07282` | 2022 | arXiv (commonly cited as ICML 2022) | PP | 43 |
| Angelopoulos, Bates, Fisch et al., *Conformal Risk Control* `10.48550/arXiv.2208.02814` | 2022 | arXiv | PP | 37 |
| Barber, Candès, Ramdas & Tibshirani, *Conformal prediction beyond exchangeability* `10.1214/23-AOS2276` | 2023 | Annals of Statistics | PR | 381 |

**Venue caution for this group**: only the arXiv DOIs are confirmed. These four are *commonly*
cited with NeurIPS/ICML venues, and that attribution could not be confirmed from Crossref,
OpenAlex or arXiv. The manuscript should cite the **arXiv DOI** for each, or verify the
proceedings record independently before attributing a conference venue.

### 4.4 Abstention / reject option

| Record | Year | Venue | Review | Citations |
|---|---|---|---|---|
| Hendrickx, Perini, Van der Plas et al., *Machine learning with a reject option: a survey* `10.1007/s10994-024-06534-x` | 2024 | Machine Learning | PR | 118 |
| Geifman & El-Yaniv, *SelectiveNet* `10.48550/arXiv.1901.09192` | 2019 | arXiv (also ICML 2019) | PP/PR | 161 |
| He, Jiang & Xiao, *A Survey on Uncertainty Quantification Methods for Deep Learning* `10.1145/3786319` | **2026** | ACM Computing Surveys | PR | 81 |

### 4.5 Censored-survival evaluation (foundational, retained despite age)

| Record | Year | Venue | Citations |
|---|---|---|---|
| Castet & Saleh, *Satellite Reliability: Statistical Data Analysis and Modeling* `10.2514/1.42243` | 2009 | J. Spacecraft and Rockets | 83 |
| Graf, Schmoor, Sauerbrei & Schumacher, *Assessment and comparison of prognostic classification schemes for survival data* `10.1002/(SICI)1097-0258(19990915/30)18:17/18<2529::AID-SIM274>3.0.CO;2-5` | 1999 | Statistics in Medicine | 593 |
| Antolini, Boracchi & Biganzoli, *A time-dependent discrimination index for survival data* `10.1002/sim.2427` | 2005 | Statistics in Medicine | 299 |
| Uno, Cai, Pencina et al., *On the C-statistics for evaluating overall adequacy of risk prediction procedures with censored survival data* `10.1002/sim.4154` | 2011 | Statistics in Medicine | 1465 |
| Sonabend, Bender & Vollmer, *Avoiding C-hacking…* `10.1093/bioinformatics/btac451` | 2022 | Bioinformatics | 14 |
| Gneiting, *Making and Evaluating Point Forecasts* `10.1198/jasa.2011.r10138` | 2011 | JASA | 1014 |
| Taggart, *Point forecasting and forecast evaluation with generalized Huber loss* `10.1214/21-EJS1957` | **2022** | Electronic J. of Statistics | 30 |

### 4.6 Telemetry and debris

| Record | Year | Venue | Citations |
|---|---|---|---|
| Hundman, Constantinou, Laporte et al., *Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding* `10.1145/3219819.3219845` | 2018 | KDD | 1603 |
| Massimi, Ferrara, Petrucci et al. `10.1049/rsn2.12547` | **2024** | IET Radar, Sonar & Nav. | 39 |
| Blake, Chote, Pollacco et al., *DebrisWatch I* `10.1016/j.asr.2020.08.008` | 2021 | Advances in Space Research | 26 |
| Blake, Cooke, Paragini et al., *DebrisWatch II* `arXiv:2605.27516` | 2026 | arXiv (**PP**) | 0 |
| Chen, Liu & Chin, *spotGEO dataset* `10.5281/zenodo.3874325` | 2020 | Zenodo (**DS**) | 1 |

## 5. Harness artifact (not a reference problem)

`mldsgp4` was reported CORRECTED only because its candidate record carried no checkable claim
field — the retrieved record (Acciarini, Baydin & Izzo 2024, `arXiv:2402.04830`, *Closing the Gap
Between SGP4 and High-Precision Propagation via Differentiable Programming*) is correct. Treated
as VERIFIED.

## 6. Review-status discipline

Twelve of the verified references are **preprints or dataset deposits, not peer-reviewed
articles**: Gulrajani & López-Paz, Gibbs & Candès, Tibshirani et al., Zaffran et al.,
Angelopoulos et al., SelectiveNet, Wang & Hyndman, ML-dSGP4, LiveHouse-TS, DebrisWatch II, the
TC-CAD deposit, and the spotGEO deposit.

Four of these carry load-bearing roles in the contribution argument — **Wang & Hyndman
(`arXiv:2410.13115`)** and **Zou et al. (peer reviewed)** between them withdraw the temporal
calibration-failure contribution, and the **TC-CAD deposit** closes evidence-graded abstention.
A contribution withdrawn partly on the strength of a preprint must say so: the manuscript should
state that the withdrawal rests on a peer-reviewed article (Zou et al. 2026) **plus** a preprint,
rather than presenting the whole closure as peer-reviewed prior art. Withdrawing a claim on
weaker evidence than one would need to assert it is the conservative direction, so the
withdrawal stands — but the reader is entitled to know.

## 7. What Phase O does not establish

- **Metadata verification is not content verification.** Every record above was matched on
  authors, year, venue and title. Specific *quoted findings* attributed to these works — for
  example Wang & Hyndman's "coverage error increases with the forecasting horizon", TC-CAD's
  "29–33 pp budgeted deferral", or Zou et al.'s rolling-origin construction — were **not**
  re-read from full text in this phase. They were recorded during the Phase I search. Any such
  quote that survives into the manuscript must be checked against the full text at
  proof stage, or paraphrased without attributing a number.
- **Citation counts move.** Three counts in the previous matrix were already stale (Barber
  352→381, Caldas & Soares 53→50, Massimi 37→39). Citation counts should be dropped from the
  manuscript entirely rather than maintained.
- **A verified reference is not a relevant reference.** Resolution says the work exists as
  described; whether it occupies the contribution space is the argument in
  `NOVELTY_AND_CONTRIBUTION_STATEMENT.md`, not a result of this audit.
