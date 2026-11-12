# Part 2 — scientific novelty comparison

Date 2026-11-05

Inspection level is marked for every reference: **[FULL]** full text read · **[META]** verified
bibliographic metadata only · **[ABS]** abstract read (by me or recorded by the project) ·
**[BLOCKED]** not obtainable.

---

## 1. Verified literature base

### 1.1 Direct competitors on ESA-ADB

| Ref | Record | Inspection | Relationship |
|---|---|---|---|
| **Brancato, L., Lucchetti, A., Kimura, Y., Omata, N., Giglio, M., Tsutsumi, S., Cadini, F.** *Evaluating scalable similarity search and Gaussian process regression for satellite telemetry anomaly detection on the ESA-ADB benchmark.* **Aerospace Science and Technology 180:113957**, issue 2027-01, online 2026-10-02. `10.1016/j.ast.2026.113957`. 0 citations | **[META]** full metadata verified via Crossref; **[ABS]** abstract read by the project; **[BLOCKED]** full text paywalled | **The closest competitor, and it is explicitly an *evaluation* paper on the same benchmark.** Reports M1 full: SMED **0.902**, Q-GPR 0.883, out-of-limit reference 0.754. Politecnico di Milano + JAXA collaboration |
| **Şahin — "TC-CAD"** Zenodo `10.5281/zenodo.23322711`, 2026-10-13, under review | **[FULL]** artefacts and pre-registrations read by the project | Telecommand conditioning **pre-registered negative**; ACI best point-level calibration but anomaly event-wise F0.5 collapses 0.090 → ~1e-5; budgeted deferral removes 29–33 pp of rare-nominal alarms. **Pre-empts the abstention/operator-budget angle** |
| **Heydari, Mostafavi & Nyarko** IEEE Access 2026, `10.1109/ACCESS.2026.3714708` | **[ABS]** abstract read by the project | Cross-mission threshold-policy transfer under alert-workload budgets. **Pre-empts workload budgets** |

### 1.2 Recent transformer-based satellite telemetry anomaly detection

| Ref | Record | Inspection |
|---|---|---|
| **Fejjari, A., Delavault, A., Camilleri, R. & Valentino, G.** *Transformer-based anomaly detection for satellite telemetry data.* **Acta Astronautica 238:739–745**, 2026. `10.1016/j.actaastro.2025.09.035`. **7 citations** | **[META]** verified; **[BLOCKED]** full text (ScienceDirect) |
| **Dai, A., Xiao, Y., Ren, F., Shen, H., Zhi, S. & Ma, B.** *Temporal-enhanced transformer for anomaly detection in spacecraft irregular-interval telemetry.* **Advances in Space Research 77:2356–2371**, 2026. `10.1016/j.asr.2025.10.088`. **3 citations** | **[META]** verified; **[BLOCKED]** full text |

Both confirm the topic is active in COSMOS-AI's candidate venues. **Dai et al. addresses
irregular-interval telemetry**, which is methodologically adjacent: ESA-ADB uses fixed 30 s / 18 s
grids and its official "restore" step moves annotated samples onto grid points.

### 1.3 Satellite lifetime / SSA benchmarks

| Ref | Record | Inspection | Relationship |
|---|---|---|---|
| **Shorten, D. P., Yang, Y., Maclean, J. & Roughan, M.** *Wide-scale Monitoring of Satellite Lifetimes: Pitfalls and a Benchmark Dataset.* J. Spacecraft and Rockets 60(6):2003–2007, 2023. `10.2514/1.A35642`; preprint `arXiv:2212.08662` | **[FULL]** 29-page preprint read and text-extracted | **Does NOT occupy the lifetime contribution.** Manoeuvre detection from TLEs, 15 satellites. "decay", "re-entry", "quantile", "uncertainty" each appear **0 times**. "Lifetimes" = end-of-life via manoeuvre history |
| **Zhou, H. et al.** *Orbital Decay Prediction in LEO.* JGR Space Physics, 2026. `10.1029/2025JA034593` | **[ABS]** | One platform, 113 ICME events, SMA loss over hours–days. Not catalogue-scale time-to-decay |
| **He, J. et al.** *Expandable Orbit Decay Prediction Using Continual Learning.* Int. J. Aerospace Eng., 2024. `10.1155/2024/8887634` | **[ABS]** | Proposes a *solution* to temporal degradation; protocol undisclosed |
| **Salmaso, F., Trisolini, M. & Colombo, C.** Aerospace, 2023. `10.3390/aerospace10030297` | **[ABS]** | >400 objects, re-entry epoch, no censoring treatment |

### 1.4 Methodological prior art — previously uncited and material

| Ref | Record | Inspection | Why it matters |
|---|---|---|---|
| **Candès, E., Lei, L. & Ren, Z.** *Conformalized survival analysis.* **JRSS-B 85(1):24–45**, 2023. `10.1093/jrsssb/qkac004` | **[META]** verified in-repo | **Direct methodological prior art** for conformal prediction on censored lifetimes — exactly Track 2's construction. **Uncited in the manuscript** |
| **Gui, Y., Hore, R., Ren, Z. & Barber, R. F.** *Conformalized survival analysis with adaptive cut-offs.* **Biometrika 111(2):459–477**, 2024. `10.1093/biomet/asad076` | **[META]** verified in-repo | Same. **Uncited** |
| **Liu et al.** *The Elephant in the Room: Towards A Reliable Time-Series Anomaly Detection Benchmark.* 2024 | **[META]** verified in-repo | Benchmark-reliability critique — supports Track 1/3 framing |
| **Sehili et al.** *Multivariate Time Series Anomaly Detection: Fancy Algorithms and Flawed Evaluation Methodology.* 2023 | **[META]** verified in-repo | Evaluation-methodology critique — directly supports the project's genre |
| **Gneiting, T.** *Making and Evaluating Point Forecasts.* JASA, 2011. `10.1198/jasa.2011.r10138` | **[META]** | The elicitability argument excluding mean-based scores |
| **Henzi, Ziegel & Gneiting.** *Isotonic Distributional Regression.* JRSS-B, 2021. `10.1111/rssb.12450` | **[META]** | **Directly relevant to defect L17** — monotone predictive CDFs by construction, i.e. the principled fix for independent per-horizon isotonic calibration |

## 2. Novelty assessment by track

Classification: **Established novelty** · **Potential novelty requiring verification** ·
**Incremental engineering** · **Not sufficiently novel** · **Unsupported claim**.

### Track 1 — OPS-SAT anomaly detection

| Candidate claim | Classification | Reasoning |
|---|---|---|
| A late-fusion CNN+MLP detector achieves AUC-PR 0.9719 time-blocked and beats a time-series foundation model by +0.0316 (95 % CI [0.0134, 0.0558], p < 0.001) | **Incremental engineering contribution** | The result is real and significance-tested, but on the *official* protocol only. Beating a foundation model on a 529-fragment supervised classification task is a solid applied result, not a methodological advance. Fejjari et al. and Dai et al. show transformer-based satellite AD is an active, crowded area |
| **The late fusion itself contributes** | **UNSUPPORTED** | `cnn` alone is **better** on the official protocol (0.9870 vs 0.9855); the time-blocked margin over `cnn` is **+0.0007**. An architecture that does not beat its own branch has not demonstrated that fusion does anything |
| The fusion improves **calibration and seed stability** (ECE 0.035 vs `cnn` 0.121, a 3.5× difference; F1 SD 0.0066 vs 0.0977, 15×) | **Potential novelty requiring verification** | Large, real differences and a more defensible framing than accuracy. **But untested** — no significance test for either, and no branch ablation attributing them to the fusion |
| Label efficiency: AUC-PR 0.910 at 10 % of labels | **Incremental** | Useful, standard |

**Track 1 verdict: incremental engineering, with one unverified claim that could become a
reliability contribution if experiment E6 supports it.** No reconstruction-based baseline and no
published satellite-specific comparator on this benchmark.

### Track 2 — Orbital lifetime prediction and uncertainty

| Candidate claim | Classification | Reasoning |
|---|---|---|
| A catalogue-scale forward-in-time lifetime benchmark (64,516-row cohort, three temporal origins, archived per-object predictions) | **Established novelty as an artifact** | Shorten et al. does **not** occupy it (§1.3, full text verified). Zhou, He and Salmaso differ in scale, estimand or protocol. No comparable benchmark located |
| Selection and test rankings are rank-independent at both published origins (ρ = 0.000, n = 7) | **Potential novelty requiring verification** | A domain-first measurement, but n = 7 bounds ρ only to ≈[−0.77, +0.77]; no permutation test. Establishes absence of *reassurance*, not absence of signal |
| **Selection regret of 3.4 % → 18.7 % → 25.2 % across origins, significant at origin 2016 (CI [+0.0040, +0.0169], zero-regret in 0 of 4,000 resamples)** | **Established novelty — the strongest single result in Track 2** | A *significant*, operationally legible cost measure. Monotone with temporal displacement, and corroborating the ρ finding from an independent statistic |
| Physics baseline ranks 1st of 19 at one origin and 19th of 19 at another | **Established novelty as a measurement** | Well-evidenced leaderboard instability |
| Censoring-aware conformal quantile treatment | **Not sufficiently novel** | Candès et al. (2023) and Gui et al. (2024) are direct prior art and currently **uncited**. Correct application of a known method |
| A distribution-free coverage guarantee | **UNSUPPORTED** | Exchangeability fails by construction (forward-in-time test folds) and empirically (coverage 0.572–0.960 across slices) |
| An identified mechanism for calibration failure via outcome-dependent covariate availability | **Potential novelty requiring verification** | Reproduced from archives (coverage −11.9 pp at 90 % when the availability pattern shifts). But the deployed arm does not use RCS; the analogous `am_design` pathway is **unablated** |

**Track 2 verdict: the artifact and the regret result are defensible; the uncertainty methodology
is not novel and has uncited prior art.**

### Track 3 — Pre-registered ESA-ADB alarm-selection study

| Candidate claim | Classification | Reasoning |
|---|---|---|
| A pre-registered, hash-frozen comparison under the official ESA-ADB protocol at full channel scale, with official metric code verified byte-identical to upstream | **Established novelty as methodology** | **The most rigorous work in the project.** Brancato et al. is also an evaluation paper on this benchmark, but pre-registration with a frozen rule and a declared minimum effect is distinctive |
| H6: an alarm-layer selection protocol outperforms the calibration-window protocol on M1 at full scale, +0.353 [+0.206, +0.488], Holm p = 0.0015 | **Potential novelty requiring verification** | Statistically strong, but **compares two whole protocols differing in five respects**, so no mechanism attribution. The project's own code audit found the fifth difference the thesis missed |
| A supervised deep event scorer shows no benefit over AR(8) or trees (H4, H5 refuted) | **Established novelty as a negative result** | Pre-registered negative, which is publishable and under-supplied. **But:** seed SDs reach ±0.1 against a +0.05 threshold, so H4/H5 are underpowered; and neither supervised scorer had a tuning budget, with only one deep architecture tried |
| Event aggregation succeeds where point-level adaptive calibration fails, for a mechanical reason | **Potential novelty requiring verification — and the best surviving distinction** | The project's own novelty note identifies this as the one distinction that survives against TC-CAD, which calibrates point-level. Needs the mechanism stated and tested |
| Competitive absolute performance on M1 full channels | **UNSUPPORTED — BLOCKED** | Brancato et al. report 0.902 where COSMOS-AI's best is ~0.09–0.20. The out-of-limit discrepancy is explained (different estimators), the method gap is not |
| Abstention / operator-budget deferral | **Not sufficiently novel** | **Pre-empted** by TC-CAD (deferral + budgets) and Heydari et al. (workload budgets). The project's own note: *"Do not build the paper on this"* |
| Generalisation of the selection effect | **UNSUPPORTED** | Reverses on M2 and on the lightweight M1 subset; only 1 of 8 cells is confirmatory. And M2 cannot serve as a test — 6 anomalies, every learned arm at exactly 0.0000 on anomaly-only |

**Track 3 verdict: the strongest methodology and the strongest statistics, carrying the largest
unresolved external blocker.**

## 3. Cross-track novelty summary

| | Track 1 OPS-SAT | Track 2 Lifetime | Track 3 ESA-ADB |
|---|---|---|---|
| Strongest classification achieved | Incremental engineering | **Established novelty** (artifact + regret) | **Established novelty** (methodology + negative) |
| Claims classified UNSUPPORTED | 1 (the fusion) | 1 (coverage guarantee) | 2 (competitive performance; generalisation) |
| Claims classified *not sufficiently novel* | 0 | 1 (conformal survival — uncited prior art) | 1 (abstention/budgets — pre-empted) |
| Direct competitor on the same benchmark | Ruszczak et al. (dataset only) | **None located** | **Brancato et al. — an evaluation paper on the same benchmark** |
| Uncited prior art that must be added | reconstruction baselines; Liu 2024, Sehili 2023 | **Candès 2023, Gui 2024, Shorten 2023** | Brancato 2026, Fejjari 2026, Dai 2026 |
| Blocking external unknown | none | none | **Brancato's 0.902** |

## 4. The one claim that is novel across two tracks

Both Track 2 and Track 3 independently produce evidence about **the validity of model-selection
and alarm-selection protocols under temporal displacement**:

- Track 2: ρ(validation, test) = 0.000 at both origins; **selection regret 3.4 % → 18.7 % → 25.2 %**, significant at one origin.
- Track 3: the selection protocol carries a large effect on M1 (+0.353) that **reverses** on M2 and on the lightweight subset; and an exploratory diagnostic finds supervised scores shift between train and test **without the shift tracking test performance**.
- Track 1 supplies the contrasting case: on temporally adjacent splits, validation→test rank transfer is **ρ = +1.000** (official) and **+0.800** (time-blocked).

**That cross-task pattern is the project's most distinctive intellectual content.** Its status is
**potential novelty requiring verification**: it is assembled from three differently-designed
studies, the regimes differ in dataset, task, metric and model family as well as in temporal
displacement, and the n values are 5, 7 and 3-origin. It is a hypothesis with three supporting
measurements, not an established result — and it is exactly what a pre-registered
temporal-displacement ladder would test.

## 5. Claims that must be removed or weakened

| Claim | Action |
|---|---|
| The late-fusion architecture improves detection accuracy | **Remove.** Replace with the calibration/stability framing, and only after E6 |
| Any distribution-free or finite-sample coverage guarantee | **Remove.** Exchangeability fails by construction |
| Competitive or state-of-the-art performance on ESA-ADB M1 | **Remove** until the Brancato gap is reconciled |
| The selection effect generalises across missions | **Remove.** Reverses on M2; M2 is near-saturated and cannot test it |
| Evidence-graded abstention / operator-budget deferral as a contribution | **Remove.** Pre-empted by TC-CAD and Heydari et al. |
| "Physics-informed" of the OPS-SAT hybrid | **Remove.** It is CNN+MLP late fusion |
| Novel conformal or censored-survival methodology | **Weaken to correct application**, and cite Candès et al. 2023 and Gui et al. 2024 |
| H2 / H6 described as confirming a mechanism | **Weaken.** H2 chance level 0.1985; H6 confounded five ways |
| Validated digital twin, validated decision support, validated cross-domain fusion | **Remove entirely.** Unsupported |
