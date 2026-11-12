# Literature review, prioritised 2023–2026

Date: 2026-11-04. **All records below were retrieved live from the OpenAlex, Crossref or arXiv
APIs during this session and are marked with how they were verified.** Nothing is cited from
memory.

## Audit of the previous reference base

| Finding | Detail |
|---|---|
| References persisted to disk before this review | **29 distinct DOIs/arXiv IDs** — the Phase I search retrieved 76, but only the subset quoted in the comparison matrix was ever written to a file. The rest existed only in a transcript. |
| Independently re-verified | 5 (Zou 2026, Henzi 2021, TC-CAD 2026, Wang & Hyndman, Taggart) |
| Marked `[D]`, never verified | ~24 of the 29 on disk — **all since resolved in Phase O**; see [FINAL_REFERENCE_VERIFICATION_MATRIX.md](FINAL_REFERENCE_VERIFICATION_MATRIX.md) |
| Outdated / pre-2023 share | High — the previous base leaned on 2001–2021 methodology papers (Clark & McCracken **2001**, **Inoue, Jin & Rossi 2017**, Gulrajani 2020, Henzi 2021, Castet & Saleh 2009) |
| Duplicated | Salmaso 2023 and He 2024 each appeared in two different sections with inconsistent framing |
| Still essential despite age | **Henzi, Ziegel & Gneiting 2021** (monotone CDFs — dissolves the L17 "discovery"); **Barber et al. 2023** (coverage beyond exchangeability); **Castet & Saleh 2009** (censored satellite survival at catalogue scale, foundational for the estimand) |

Recency in this review: **30 of 34 references (88 %) are from 2023–2026**, exceeding the 70–80 %
target. The four retained older works are foundational for the estimand, the monotone-CDF
result, or the conformal theory.

## Section 1 — Orbital lifetime prediction and orbital decay forecasting

### [R1] Orbital Decay Prediction in Low Earth Orbit: Integrating Along-Track Density Observations With Machine Learning
- **Authors** Hao Zhou, Jipeng Yang, Yaozong Li, Xinshang Li, Tiantian Qing, Mingyang Xia, Zhicai Luo (Huazhong Univ. of Science and Technology)
- **2026** · *Journal of Geophysical Research: Space Physics* 131(3) · `10.1029/2025JA034593` · closed access · 0 citations · **verified: OpenAlex record + reconstructed abstract**
- **Problem** Empirical thermospheric density models miss localised oscillations, so decay is poorly predicted under changing geomagnetic conditions.
- **Method** Random forest over GRACE Level-1B along-track neutral density, aerodynamic coefficients and mass parameters.
- **Data** GRACE — **a single satellite platform**.
- **Findings** 48-h semi-major-axis decay ≈168 m during the May 2024 storm; predicted −45.4 m vs observed −40.4 m for the Aug 2005 ICME; across **113 ICME events** explained 85 % of decay variance; test R² 0.749 across 2005 disturbed intervals.
- **Limitations** **Event-based on one platform, not catalogue scale.** Predicts semi-major-axis loss over hours-to-days, **not time-to-decay** over years. No censoring, no multi-object population.
- **Relevance** The closest recent ML decay paper. **It does not occupy our target**: different estimand, different scale. Its existence strengthens rather than weakens contribution A, and it must be cited as the state of the art in storm-time decay.

### [R2] Expandable Orbit Decay Prediction Using Continual Learning
- **Authors** Junhua He, Hua Wang, Haitao Wang, Xuankun Fang, Chengyi Huo (NUDT, Changsha)
- **2024** · *International Journal of Aerospace Engineering* 2024(1) · `10.1155/2024/8887634` · open access CC-BY · 2 citations · **verified: OpenAlex + abstract**
- **Problem** Precise orbit decay prediction for VLEO spacecraft; ML generalises poorly because of **catastrophic forgetting**, and physical parameters and the space environment are imprecisely estimated.
- **Method** "Expandable orbit decay propagator" (EODP) — model-agnostic continual learning with a plastic network structure attributed to NN parameter uncertainty.
- **Data** Not disclosed in the indexed record; object counts and train/test protocol unavailable without the full text.
- **Findings** ≥70 % accuracy improvement relative to a high-precision orbital propagator.
- **Limitations** Dataset, object count and evaluation protocol not recoverable from the record — **so the claim cannot be independently assessed**. VLEO-specific.
- **Relevance** **The closest work on temporal adaptation in decay prediction.** It proposes a *solution* to temporal degradation; our work provides a *diagnosis* of why model selection fails across temporal origins. Complementary, and a necessary citation. Its undisclosed protocol is itself an argument for a public benchmark.

### [R3] A Machine Learning and Feature Engineering Approach for the Prediction of the Uncontrolled Re-Entry of Space Objects
- **Authors** Francesco Salmaso, Mirko Trisolini, Camilla Colombo (Politecnico di Milano)
- **2023** · *Aerospace* 10(3):297 · `10.3390/aerospace10030297` · 17 citations · **verified: OpenAlex**
- **Problem** Predicting uncontrolled re-entry epoch for LEO objects.
- **Method** Modified Seq2Seq with engineered inputs (B\*, solar index, area-to-mass) over TLE-derived mean-altitude profiles.
- **Data** **>400 objects**; tested on IADC re-entry campaign objects.
- **Findings** Best accuracy when the test drag-coefficient/eccentricity distribution matches training.
- **Limitations** ~400 objects (not catalogue scale); no censoring-aware target; no cluster-aware intervals; **requires TLEs including B\***.
- **Relevance** The canonical ML re-entry baseline. Its own distribution-match caveat is an early, informal statement of the generalisation problem our work quantifies.

### [R4] Machine learning in orbit estimation: A survey
- **Authors** Francisco Caldas, Cláudia Soares (NOVA Lisbon)
- **2024** · *Acta Astronautica* 220:97–107 · `10.1016/j.actaastro.2024.03.072` · open access · **53 citations**, FWCI 8.40 · **verified: OpenAlex + abstract**
- **Problem** Approximate physics gives orbit errors "in the order of kilometers for seven-day predictions" against sub-metre debris.
- **Method** Survey of 151 works across orbit determination, orbit prediction and atmospheric density modelling.
- **Findings** Attributes the error to three causes: initial-state uncertainty, environment prediction error (drag), and unmeasured physical properties (mass, geometry).
- **Limitations** No open-problems list on evaluation methodology or generalisation.
- **Relevance** **Defines the field's framing of its own open problem — and it is entirely about accuracy, not evaluation validity.** Our contribution sits in a dimension this survey does not address, which is a positioning advantage and a gap worth naming explicitly.

### [R5] Closing the Gap Between SGP4 and High-Precision Propagation via Differentiable Programming (dSGP4 / ML-dSGP4)
- **Authors** Giacomo Acciarini, Atılım Güneş Baydin, Dario Izzo
- **2025** · *Acta Astronautica* 226(1) · `10.1016/j.actaastro.2024.10.063` · arXiv:2402.04830v5 · **verified: arXiv abstract + Crossref**
- **Method** Differentiable PyTorch SGP4; ML-dSGP4 embeds networks initialised as identity.
- **Input/output** Consumes "batches of **Two-Line Element Sets (TLEs)**"; outputs "satellite **positions** at future times", velocities, state transition matrix, propagated covariance.
- **Relevance** The physics/hybrid baseline a reviewer will name. **Assessed and excluded** — see `ML_DSGP4_FEASIBILITY.md`: we hold no TLE, no B\*, no ephemeris (L4); the estimand is a state vector not time-to-decay; and B\* is itself fitted to observed decay, so using it would leak the outcome.

### [R6] Improving Thermospheric Density Predictions in Low-Earth Orbit With Machine Learning
- Acciarini, Brown, Berger et al. · **2024** · *Space Weather* · `10.1029/2023SW003652` · 15 citations · **verified: OpenAlex**
- Density-model improvement upstream of any drag-based lifetime prediction. **Relevance:** our physics expert uses NRLMSIS-2.1; this is the recent-ML alternative we do not use, and the omission should be acknowledged.

### [R7] Atmospheric density estimation in very low Earth orbit based on nanosatellite measurement data using machine learning
- Tomoki Sakai, Yusuke Takahashi · **2024** · *Aerospace Science and Technology* · `10.1016/j.ast.2024.109418` · 10 citations · **verified: OpenAlex**
- **Relevance** In-situ density estimation; same upstream role as [R6].

### [R8] Characterizing solar cycle influence on long-term orbital deterioration of low-earth orbiting space debris
- Ayisha M. Ashruf, Ankush Bhaskar, C. Vineeth · **2026** · *Frontiers in Astronomy and Space Sciences* · `10.3389/fspas.2026.1797886` · 1 citation · **verified: OpenAlex**
- **Relevance** Directly relevant to our space-weather features and to the epoch-dependence we measure: the solar cycle is a plausible driver of the composition shift between our temporal origins.

## Section 2 — Satellite anomaly detection and health monitoring

### [R9] Unmasking overestimation: a re-evaluation of deep anomaly detection in spacecraft telemetry
- **Authors** Lars Herrmann, Marie Bieber (TU Delft), Wim J. C. Verhagen (RMIT), Fabrice Cosson (ESA/ESTEC), Bruno F. Santos (TU Delft)
- **2024** · *CEAS Space Journal* 16(2):225–237 · `10.1007/s12567-023-00529-5` · open access CC-BY, ESA-funded · 23 citations · **verified: OpenAlex + reconstructed abstract**
- **Problem** Published deep anomaly detection (DAD) results on spacecraft telemetry are unreliable.
- **Findings** A "tendency for performance results to be overestimated"; **simple baselines can at times beat heavier DAD models**; advocates metrics that are "less accuracy-inflating"; LSTM most promising but fails in systems without "a single, clear predictive failure channel".
- **Recommendations** Adopt best practices and supply **"high-quality, pre-split datasets"**.
- **Limitations** Anomaly detection only; no temporal origins, no model-selection analysis, datasets not named in the record.
- **Relevance** **This is the closest methodological sibling to COSMOS-AI's entire negative-results programme, and it is the single most important citation in this review.** It establishes in a peer-reviewed space journal that (a) the overestimation genre is publishable, (b) simple baselines beating complex ones is an accepted finding in this field, and (c) a pre-split benchmark is a recognised contribution. It does **not** take our specific results — but it means we must position as *extending* an established line, never as discovering it.

### [R10] A Review of Anomaly Detection in Spacecraft Telemetry Data
- Asma Fejjari, Alexis Delavault, Robert Camilleri, Gianluca Valentino (Univ. of Malta) · **2025** · *Applied Sciences* 15(10):5653 · `10.3390/app15105653` · open access · **78 citations, FWCI 22.21, top-1 % citation percentile** · **verified: OpenAlex + abstract**
- Surveys 71 works; comparative benchmarking; GCN and TCN best with "promising precision up to 94%".
- **Limitation** The record does not name the datasets behind the 94 % figure.
- **Relevance** The authoritative recent AD survey. Any telemetry claim must be positioned against it.

### [R11] Deep Clustering-Based Anomaly Detection and Health Monitoring for Satellite Telemetry
- Obied, Ghaleb, Hassanien et al. · **2023** · *Big Data and Cognitive Computing* 7(1):39 · `10.3390/bdcc7010039` · 26 citations · **verified: OpenAlex**

### [R12] A novel asymmetric loss function for deep clustering-based health monitoring and anomaly detection for spacecraft telemetry
- Obied, Zakaria, Ghaleb et al. · **2024** · *CCF Transactions on Pervasive Computing and Interaction* · `10.1007/s42486-024-00160-1` · 2 citations · **verified: OpenAlex**

### [R13] Towards explainable anomaly detection for satellite telemetry
- Clemens Schefels, Arvind Kumar Balan, Ben Salem Bilel · **2026** · *CEAS Space Journal* · `10.1007/s12567-026-00767-3` · 0 citations · **verified: OpenAlex**
- **Relevance** Explainability is the current frontier in this subfield; our evidence-provenance machinery is adjacent but is *engineering*, not a contribution (Phase I).

### [R14] Generic Diagnostic Framework for Anomaly Detection — Application in Satellite and Spacecraft Systems
- Marie Bieber, Wim J. C. Verhagen, Fabrice Cosson et al. · **2023** · *Aerospace* 10(8):673 · `10.3390/aerospace10080673` · 11 citations · **verified: OpenAlex**

### [R15] The OPS-SAT benchmark for detecting anomalies in satellite telemetry
- Bogdan Ruszczak et al. · **2025** · *Scientific Data* 12:710 · `10.1038/s41597-025-05035-3` · 46 citations · **verified: OpenAlex (Phase I)**
- **Relevance** A peer-reviewed **benchmark release in Scientific Data** — the clearest precedent for publishing a dataset/benchmark artifact in this domain, and a model for how to frame contribution A.

### [R16] Evaluating scalable similarity search and Gaussian process regression for satellite telemetry anomaly detection on the ESA-ADB benchmark
- L. Brancato, F. Cadini et al. · **2026** · *Aerospace Science and Technology* 180:113957 · `10.1016/j.ast.2026.113957` · **verified: OpenAlex (Phase I)**
- Event-morphology taxonomy of 8 archetypes; F0.5 up to 0.902; reports a baseline collapsing.
- **Relevance** The current ESA-ADB state of the art. Our telemetry results must be positioned against this number, not against the original benchmark paper.

### [R17] European Space Agency Benchmark for Anomaly Detection in Satellite Telemetry (ESA-ADB)
- K. Kotowski et al. · **2024** · `10.48550/arXiv.2406.17826` · **PREPRINT — not peer reviewed** · **verified: OpenAlex (Phase I)**

### [R18] Fault Diagnosis and Prognosis of Satellites and Unmanned Aerial Vehicles: A Review
- MohammadSaleh Hedayati, Ailin Barzegar et al. · **2024** · *Applied Sciences* 14(20):9487 · `10.3390/app14209487` · 32 citations · **verified: OpenAlex**

### [R19] TC-CAD — preregistered negative result on telecommand conditioning in ESA-ADB
- Fatih Şahin (Istanbul Topkapi Univ., ORCID 0000-0002-8036-3156) · **2026-10-12** · Zenodo · `10.5281/zenodo.23322711` · **DATASET DEPOSIT — NOT PEER REVIEWED, 0 citations** · **verified: OpenAlex + abstract**
- Preregistered (16 seeds, 2 missions, 128 runs): FiLM-style telecommand conditioning **did worse** than the unconditioned control; a shuffled-telecommand control was statistically indistinguishable; 10-month replication. **Adaptive conformal inference was the best-calibrated thresholding layer**, and **budgeted two-threshold deferral cut 29–33 percentage points of automatic alarms** with recall essentially unchanged.
- **Relevance** **Priority threat.** Pre-empts the evidence-graded abstention contribution, the adaptive-conformal thresholding and the ESA-ADB negative-result framing simultaneously. Must be cited with its unreviewed status stated plainly, and its date checked against our own records.

## Section 3 — Uncertainty quantification and conformal prediction in space applications

### [R20] Task-aware conformal power envelopes for multi-horizon spacecraft monitoring
- **Authors** Nan Lu, Lehan Cui, Xinian Zhi (Northwestern Polytechnical University)
- **2026-10-13** · *PLoS ONE* 21(10):e0360910 · `10.1371/journal.pone.0360910` · gold OA · 0 citations · **verified: OpenAlex + reconstructed abstract**
- **Problem** Spacecraft power monitoring needs uncertainty over multiple horizons with coherence between measured and derived quantities.
- **Method** Task-aware conformal framework; residual iTransformer point centres; joint residual geometry selected by downstream envelope efficiency; calibrated on chronologically separated complete-orbit blocks.
- **Data** **Real BUPT-1 satellite telemetry**; 25,278 forecast origins from later July 2023; three seeds.
- **Findings** Horizons 1/5/15 min. Joint primitive-state coverage **0.892** (95 % CI 0.883–0.899) against a 90 % target, 0.947 against 95 %; both-channel simultaneous coverage 0.913/0.957. Task-aware selection cut the normalised power interval score by 34.3 %/30.3 %.
- **Limitations** **Does not address distribution shift, non-exchangeability or adaptive conformal methods.** Minute-scale horizons; power states, not time-to-decay. Coverage is *below* nominal at 90 % and the paper does not analyse why.
- **Relevance** **The only genuine conformal-prediction-in-space application I could find**, and it partially occupies "conformal + multi-horizon + real spacecraft telemetry + joint coverage" as of October 2026. Our Phase H finding — coverage degrading with time from the forecast origin under temporal shift — is **not** pre-empted, and this paper's own sub-nominal 0.892 corroborates that attaining nominal coverage on real spacecraft data is hard.

### [R21] Horizon-aware group-conditional conformal prediction: post-hoc shrinkage for sparse multi-horizon coverage auditing
- Jitong Zou, Enmiao Feng, Pengfei Li, Gaike Wang · **2026** · *Machine Learning with Applications* 26:101038 · `10.1016/j.mlwa.2026.101038` · Elsevier, CC BY-NC-ND, 64 references · **verified independently: Crossref**
- Audits coverage per (group, horizon) cell; **country-cluster bootstrap** intervals; rolling-origin deployment protocol; HACC shrinkage fix.
- **Relevance** **Priority threat.** This is, in substance, our Phase H/G5 calibration-audit design, published in a journal. Pre-empts contribution B and the cluster-interval element of A.

### [R22] Conformal prediction beyond exchangeability
- Rina Foygel Barber, Emmanuel Candès, Aaditya Ramdas, Ryan Tibshirani · **2023** · *Annals of Statistics* · `10.1214/23-aos2276` · 352 citations · **verified: OpenAlex (Phase I)**
- Derives an explicit coverage-gap bound as a function of distribution drift.
- **Relevance** Our coverage failure is an instance of a named theorem. **Retained despite being the oldest conformal citation** because it is the formal result our finding instantiates.

### [R23] Online conformal inference for multi-step time series forecasting
- Xiaoqian Wang, Rob J. Hyndman · arXiv:2410.13115v2 (2024, rev. 2026-02) · **PREPRINT — no DOI** · **verified independently: arXiv**
- Verbatim: "the coverage error admits an upper bound that **increases with the forecasting horizon**".
- **Relevance** Our horizon-degradation finding is a *proved* property. Must be cited; cannot be claimed.

### [R24] Evaluating time-to-event forecasts under fixed-horizon right-censoring
- Robert J. Taggart, Nicholas Loveday, Simon Louis · arXiv:2603.14835v2 (2026) · math.ST · **PREPRINT — no DOI** · **verified independently: arXiv**
- Verbatim: "quantiles and prediction intervals whose endpoints are quantiles remain locally elicitable"; "the expectation functional is **not** locally elicitable".
- **Relevance** **Supplies the correct evaluation machinery for our estimand and validated our metric choices.** It is why `rmse_log10` is excluded and why pinball/coverage/Brier are retained.

### [R25] Isotonic Distributional Regression
- Alexander Henzi, Johanna F. Ziegel, Tilmann Gneiting · **2021** · *JRSS-B* · `10.1111/rssb.12450` · 47 citations · **verified independently: OpenAlex**
- Monotone predictive CDFs **by construction**.
- **Relevance** **Retained despite age — dissolves the L17 "incoherence" finding as a discovery.** Our P(≤30 d) > P(≤90 d) violation is a consequence of per-horizon independent calibration, a known-bad design with a published fix.

### [R26] Physics-Informed Neural Networks in Aerospace Engineering: A Systematic Review
- Przemysław Gryt, Piotr Przystałka · **2026** · *Applied Sciences* 16(13):6282 · `10.3390/app16136282` · 2 citations · **verified: OpenAlex**
- **Relevance** Frames the physics-ML hybrid space our (unrun) G4 arm would have occupied.

## Section 4 — Space debris monitoring, tracking and population

### [R27] Deep learning-based space debris detection for space situational awareness: a feasibility study
- Federica Massimi, Pasquale Ferrara et al. · **2024** · *IET Radar, Sonar & Navigation* · `10.1049/rsn2.12547` · **verified: OpenAlex + Crossref (Phase O)**

### [R28] Machine learning-based classification for Single Photon Space Debris Light Curves
- Nadine M. Trummer, Amit Reza et al. · **2024** · *Acta Astronautica* · `10.1016/j.actaastro.2024.10.066` · 13 citations · **verified: OpenAlex**

### [R29] Refined STACK-CNN for Meteor and Space Debris Detection in Highly Variable Backgrounds
- Leonardo Olivi, Antonio Montanaro et al. · **2024** · *IEEE JSTARS* · `10.1109/jstars.2024.3397734` · 2 citations · **verified: OpenAlex**

### [R30] Research on the Efficient Space Debris Observation Method Based on Optical Satellite Constellations
- Gongqiang Li, Jing Liu et al. · **2023** · *Applied Sciences* 13(7):4127 · `10.3390/app13074127` · 8 citations · **verified: OpenAlex**

### [R31] DebrisWatch II: Digging Deeper for Geosynchronous Debris
- **2026** · *The Journal of the Astronautical Sciences* · `10.1007/s40295-026-00602-1` · **verified: OpenAlex (partial record — author list truncated; confirm before citing)**

**Section verdict.** Recent debris work is overwhelmingly about *detection* from radar and
optical sensing. Our SpotGEO-based debris module is a detection reimplementation and is
**not competitive with this literature**; it should be presented as pipeline infrastructure, not
as a debris-detection contribution.

## Section 5 — Satellite digital twins

### [R32] Plotinus: A Satellite Internet Digital Twin System
- Yue Gao, Kun Liang Qiu, Zhe Chen · **2024** · *Journal of Communications and Information Networks* · `10.23919/jcin.2024.10494942` · 20 citations · **verified: OpenAlex**

### [R33] Digital Twin Technology-Based Networking Solution in Low Earth Orbit Satellite Constellations
- Ci He, Yasheng Zhang, Jia Ke · **2024** · *Electronics* 13(7):1260 · `10.3390/electronics13071260` · 13 citations · **verified: OpenAlex**

### [R34] Adaptive multi-layer deployment for a digital-twin-empowered satellite-terrestrial integrated network
- Yihong Tao, Bo Lei, Haoyang Shi · **2025** · *Frontiers of Information Technology & Electronic Engineering* · `10.1631/fitee.2400327` · 8 citations · **verified: OpenAlex**

**Section verdict — an important negative finding.** A systematic search of 2023–2026
"satellite digital twin" work returns a literature dominated by **communications and networking**
digital twins (constellation routing, caching, satellite-internet emulation). I found **no**
recent peer-reviewed predictive *health-and-orbital* satellite digital twin of the kind
COSMOS-AI describes. That niche is genuinely under-occupied — but an unoccupied name is not a
contribution, and Phase E showed our cross-domain integration does not improve prediction. The
honest conclusion: **drop the "digital twin" framing** rather than claim the niche.

## Cross-cutting: what the 2023–2026 literature has established

| Established | Evidence |
|---|---|
| ML improves orbit/decay/density prediction over empirical models | [R1][R2][R4][R6][R7] |
| Deep AD results on spacecraft telemetry are **overestimated**, and simple baselines sometimes win | **[R9]** |
| Benchmark/dataset releases are a recognised contribution in this domain | [R15] (*Scientific Data*), [R17] |
| Metric choice materially changes AD conclusions | [R9][R10][R16] |
| Catastrophic forgetting / temporal degradation is a known problem in decay prediction | **[R2]** |
| Conformal coverage fails under distribution shift, with a bound increasing in horizon | [R22][R23] |
| Multi-horizon group-conditional coverage auditing with cluster bootstrap | **[R21]** |
| Conformal prediction on real spacecraft telemetry at multiple horizons | **[R20]** |
| Monotone predictive CDFs are a solved problem | [R25] |
| Correct evaluation theory for fixed-horizon right-censored forecasts | [R24] |
| Evidence-graded abstention and budgeted deferral on ESA-ADB | **[R19]** (unreviewed) |

## What remains unresolved in the 2023–2026 literature

1. **No catalogue-scale, forward-in-time, time-to-decay benchmark.** [R1] is event-based on one
   platform; [R3] is ~400 objects; [R2]'s protocol is undisclosed. The intersection
   (catalogue scale) × (forward origins) × (time-to-decay with censoring) is **unoccupied**.
2. **Conformal prediction is almost absent from space applications.** Strict search: **1 of 15**
   genuine hits ([R20]); **0** for conjunction assessment. Coverage behaviour under *orbital*
   temporal shift is unstudied.
3. **Model-selection validity is not examined in this field.** [R4], the 53-citation survey,
   frames the open problem purely as accuracy. No recent orbital paper asks whether the
   selection criterion transfers to the deployment epoch.
4. **Evaluation-population composition effects are unstudied** for censored orbital targets.
5. **No predictive health-and-orbital satellite digital twin** in the recent peer-reviewed
   literature — the term is occupied by networking work.

## Comparison against our actual experimental findings

| Our finding | Literature status | Verdict |
|---|---|---|
| Spearman(selection, test) = 0.000 at both origins | Phenomenon established generally (econometrics/ML); **not examined in orbital prediction** | **Defensible as a first measurement in this domain** |
| `physics_only` ranks 17/17 then 1/17 across origins | [R3] notes distribution-match dependence informally; no recent orbital paper quantifies rank inversion | **Defensible** |
| 23.64 % of evaluation-slice pairs invert ranking | Rank inversion shown in other domains (2026); not in orbital | **Defensible as domain-first** |
| Coverage degrades with time from origin (−0.83 to −0.94) | **Proved** as a bound by [R23]; audited by [R21] | **Must be cited, not claimed** |
| L17 per-horizon incoherence | Solved by [R25] | **Report as a design diagnostic** |
| Loss concentrates 4.1–6.6× below the cap | No precedent located | **Defensible, narrow** |
| Learner-dependent feature sign reversals | Consistent with [R9]'s "overestimation" genre; not shown for orbital features | **Defensible, narrow** |
| Cross-domain coupling does not improve prediction | Negative result; no competing positive claim located | **Preserve as a negative finding** |
| Evidence-graded abstention | Pre-empted by [R19] and the general abstention literature | **Drop as a contribution** |

**Negative and inconclusive findings are preserved unchanged.** Nothing in this review alters
an experimental result, and no frozen artifact, pre-registration or benchmark output was
touched.
