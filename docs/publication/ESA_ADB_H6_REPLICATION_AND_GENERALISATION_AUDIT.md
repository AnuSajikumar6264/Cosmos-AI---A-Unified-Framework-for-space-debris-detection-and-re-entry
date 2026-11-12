# ESA-ADB H6 — replication and generalisation audit

Date 2026-11-05 · read-only · **the pre-registered result and protocol are unmodified**

**Headline: H6 is a real, well-executed, pre-registered result — but it compares two whole
protocols differing in five respects, so it cannot be attributed to any single mechanism. And a
published 2026 paper reports Mission 1 full-channel scores an order of magnitude higher, including
for the same trivial baseline. That discrepancy is the track's largest rejection risk.**

Inspected: `research_design/preregistration/{PREREG_TELEMETRY_V1.md, freeze.json,
freeze_09a98f5e160e.json, DEVIATIONS.md, POSTHOC_PLAN_V2.md, posthoc_v2_freeze.json}`,
`thesis/audit/STAGE1_AUDIT.md` §1–§7, `thesis/audit/CLAIM_EVIDENCE_MATRIX.md`,
`research_design/NOVELTY_NOTE.md`, `outputs/benchmarks/telemetry_esa_adb/results.csv` (128 rows,
56 tags, 2 missions × 2 channel scales), `thesis/build/Q1_Readiness_and_Roadmap.md`.

---

## 1. What the pre-registered study actually is

| Element | Detail |
|---|---|
| Data | ESA Anomalies Dataset v1.0 (Zenodo 12528696), Missions 1 and 2, official grids (30 s, 18 s) |
| Splits | Official, at 2007-01-01 (M1) and 2001-10-01 (M2) |
| Channels | **Target sets of 58 (M1) and 47 (M2)** — full channel scale, plus a lightweight subset |
| M1 labels | Train: 109 annotated events on target channels (63 anomalies, 42 rare, 4 comms gaps). **Test: 55 anomalies, 36 rare** |
| M2 labels | **Test: 6 anomalies, 356 rare events** |
| Mission 3 | On disk, **no official split**; authors advise against benchmarking; 8 anomalies + 25 rare total |
| Models | AR(8) ridge 1e-3 horizon 16, OOF with K = 5 contiguous blocks and a 1-day purge; XGBoost 3-class, 400 trees depth 8; EventTCN 8 levels, receptive field 1,021, **220,739 parameters**, 1,500 steps |
| Comparators | Point-level ACI (α = 0.01, γ ∈ {0.001, 0.005, 0.01, 0.05}), threshold layer, rolling layer |
| Metric | Corrected event-wise F0.5 over anomalies and rare events, computed by **vendored official code** |
| Metric integrity | Official metric files **byte-identical to upstream commit 67194d3** (verified against the shipped tarball) |
| Seeds | A2, A3: 5 each; ablations: 3; A0, A1 deterministic |
| Statistics | Paired bootstrap, fixed 30-day blocks (**86 on M1, 22 on M2**), hierarchical over seeds, B = 2,000, **Holm** over {H4, H5, H6}, minimum effect **+0.05** |

**Pre-registered outcomes (M1, conformal-BH layer, frozen rule):**

| ID | Comparison | Estimate | 95 % CI | Raw p | Holm p | Verdict |
|---|---|---|---|---|---|---|
| H4 | A3 − A1 | −0.222 | [−0.395, +0.042] | 0.101 | 0.101 | **refuted** (no gain ≥ 0.05; not shown worse) |
| H5 | A3 − A2 | −0.338 | [−0.540, −0.033] | 0.035 | 0.070 | **refuted** (no gain ≥ 0.05) |
| H6 | A1 − A0 | **+0.353** | **[+0.206, +0.488]** | 0.0005 (floor) | **0.0015** | **supported** |

Holm arithmetic independently checked and correct. **Mission 2 replication (no inference):**
H4 +0.001 [−0.055, +0.054]; H5 −0.029 [−0.103, +0.037]; **H6 −0.089 [−0.143, −0.049] — reversed.**

## 2. What H6 establishes — and what it does not

**H6 establishes:** on Mission 1 at full channel scale, under the conformal-BH alarm layer,
protocol **A1** outperforms protocol **A0** by +0.353 event-wise F0.5 [+0.206, +0.488], Holm
p = 0.0015, by a frozen rule with a pre-specified minimum effect.

**H6 does not establish** that any particular design choice causes the gain, because **A0 and A1
differ in five respects simultaneously** (`STAGE1_AUDIT.md` §5.1 — note the thesis and deviation
log say four; the independent code audit found a fifth):

| # | Difference | A0 | A1 |
|---|---|---|---|
| 1 | Forecaster fit data | `fit` period only, nominal check on target and lag 8 | all nominal training samples, all 8 lags nominal |
| 2 | **Residual scale σ** *(newly identified)* | out-of-sample residuals on the 3-month `es` period | in-sample residuals over the whole training half; per-fold in-sample σ for OOF scores. **Per-channel ratio of median nominal scores: median 1.007, range 0.52–4.70; 37 of 58 M1 channels at the σ floor** |
| 3 | Calibration pool | 792,000 rows from the 9 months before test, from the model that scores test | **7,364,161 OOF rows** from five fold models with different σ, while test scores come from the full-fit model |
| 4 | **Selection data** | **9 M1 events** (7 anomalies, 2 rare); M2: 43 rare, 0 anomalies | **105 M1 events** (+4 gaps); M2: 282 |
| 5 | Grid | {1e-2, 1e-3, 3e-4, 1e-4} × {1, 3, 10, 30} | {1e-2 … 1e-5} × {1, 3, 10, 30, 100} |

Identical in both: normalisation, score formula, forecast-origin schedule on test, alarm layer,
1 h merge, objective, refit-after-selection rule. **The frozen code reproduces the saved A0 and A1
alarms bit for bit.**

So the defensible statement is *"this protocol beats that protocol on this mission at this
channel scale"* — a protocol comparison, not a mechanism claim. The provisional title *"Beyond
Model Complexity…"* is compatible with the evidence **only if** these conditions are stated.

## 3. Can the five confounds be isolated from existing artifacts?

**Partially — and it has already been attempted post hoc.**

`Q1_Readiness_and_Roadmap.md` D.4 item 2 records: *"Run a factorial H6 that crosses scores,
calibration pool and selection data on one grid… **Done post hoc as a one-factor-at-a-time
decomposition (P1): the selection data carry the effect.**"* A `POSTHOC_PLAN_V2.md` and
`posthoc_v2_freeze.json` exist, so the post-hoc work was itself planned and frozen.

**Limits of what exists:**

| Limit | Consequence |
|---|---|
| One-factor-at-a-time, not factorial | **Interactions unidentified.** With five factors, OFAT cannot separate main effects from interactions |
| Run on test halves already seen | Exploratory status; cannot be confirmatory |
| Difference #2 (residual scale σ) newly identified | The decomposition was designed around *four* differences; the fifth was not a factor in it |
| Difference #3 involves a 9× change in calibration-pool size **and** a model mismatch (fold models vs full-fit model) | Two sub-factors bundled into one "factor" |

**Verdict: a true factorial attribution is NOT available from existing artifacts.** A 2⁵ design is
32 cells; a fractional design on the three plausible drivers (#2, #3, #4) is 8 cells and would be
sufficient. This is the single most valuable additional experiment for the track.

## 4. Why the result reverses on Mission 2 — and why the trivial rule scores 0.9648

**I verified this directly, and the answer is a label-composition artifact, not a modelling
finding.**

Mission 2's test half contains **6 anomalies and 356 rare events**. The headline metric
(`anomaly_and_rare/EW_F0.5`) is therefore ~98 % determined by rare events. Splitting the composite
metric apart:

| Mission / scale | Arm | `anomaly_and_rare/EW_F0.5` | **`anomaly/EW_F0.5`** | rare-event-only runs | false alarms/yr |
|---|---|---|---|---|---|
| **M2 lightweight** | **`out_of_limits`** | **0.9648** | **0.0877** | 3,162 | 7.4 |
| M2 lightweight | `cosmos_monitor` | 0.7881 | **0.0000** | 213 | 0.6 |
| M2 lightweight | `ar8` | 0.7741 | **0.0000** | 261 | 19.1 |
| M2 lightweight | `patchtst` | 0.7028 | **0.0000** | 205 | 0.0 |
| M2 target (full) | `out_of_limits` | 0.8936 | 0.0897 | 2,462 | 20.6 |
| M2 target (full) | `ar8` | 0.7940 | 0.2157 | 228 | 1.3 |
| M1 target (full) | `out_of_limits` | **0.0007** | 0.0004 | 8,802 | **11,627** |
| M1 target (full) | `cosmos_monitor` | 0.0038 | 0.0022 | 1,860 | **3,278** |
| M1 target (full) | `patchtst` | 0.0901 | 0.0661 | 28 | 34 |

**Three conclusions:**

1. **The 0.9648 is rare-event detection, not anomaly detection.** On anomalies alone the same rule
   scores **0.0877**. An out-of-limits rule catches out-of-limit excursions, which is close to what
   "rare event" operationally means. The project reached the same conclusion independently —
   claim T2 in its own matrix reads: *"the parameter-free out-of-limit rule scores 0.894 on Mission
   2 full channels, so **Mission 2 is near-saturated**."*
2. **Mission 2 is not a usable anomaly-detection benchmark.** Every learned arm scores **exactly
   0.0000** on anomalies at M2 lightweight. With 6 anomalies in the test half, no method can be
   discriminated.
3. **Therefore "H6 reverses on Mission 2" is weaker evidence than it sounds.** The M2 composite
   metric measures a substantially different quantity than the M1 composite does. The reversal is
   a statement about rare-event alarm behaviour under a near-saturated metric, not a demonstration
   that the protocol effect fails to generalise across missions.

This refinement **helps** the paper: it converts an apparently damaging reversal into a
characterised metric artifact. But it also removes M2 as a generalisation test, which is the point
below.

## 5. The largest rejection risk — an unexplained order-of-magnitude discrepancy

`research_design/NOVELTY_NOTE.md` records closest prior work, and one entry is decisive:

**Brancato, Lucchetti, Kimura, Omata & Giglio**, *Aerospace Science and Technology*, 2026-10-02,
`10.1016/j.ast.2026.113957` (full text paywalled; abstract read by the project). Claimed to use the
*"full ESA-ADB hierarchical protocol"*, **Mission 1 only**, with label-free SMED and Q-GPR plus
adaptive retraining. Reported: **M1 full: SMED 0.902, Q-GPR 0.883, out-of-limit reference 0.754.**

Against COSMOS-AI's M1 full-channel numbers:

| Arm | Brancato et al. (M1 full) | COSMOS-AI (m1_target) |
|---|---|---|
| Best method | **0.902** (SMED, label-free) | ~0.09 (`patchtst`) to 0.2022 (`tcn_tc_s2`, ±0.226) |
| **Out-of-limit reference** | **0.754** | **0.0007** |

**The trivial baseline differs by roughly three orders of magnitude on the same mission, the same
channel scale and nominally the same official metric.** That cannot be a method effect. It points
to a difference in protocol, preprocessing, channel selection, event-matching or metric variant.

The project states this plainly and does not paper over it: *"Brancato et al.'s 0.902 remains
unexplained"*, and evidence gap 1 in the Q1 roadmap reads *"cannot be reconciled with this study
without their full text and code."*

**Corroborating datapoint.** TC-CAD (Şahin, Zenodo `10.5281/zenodo.23322711`) reports anomaly
event-wise F0.5 of **0.090** at its C-0 configuration — squarely in COSMOS-AI's range, not
Brancato's. So two independent efforts land near 0.09 while one reports 0.90. That increases the
probability that the discrepancy is a protocol variant rather than a COSMOS-AI defect — but it
does not resolve it.

**Why this is the dominant rejection risk:** a reviewer familiar with Brancato et al. — plausibly
a reviewer *from* that group, as the project's own VENUES.md notes for Aerospace Science and
Technology — will see a submission reporting ~0.09 where a published paper reports 0.902, and will
not accept "unexplained" as an answer. **No claim of competitive absolute performance on M1 full
channels is defensible until this is reconciled.** The H6 *protocol-comparison* result is less
exposed, because it is a relative within-study contrast.

## 6. Other material limitations found in the prior audit (independently reviewed)

| # | Limitation | Severity |
|---|---|---|
| 1 | **Test-half exposure.** Both test halves were scored in **128 configuration–layer combinations during the exploratory phase, before the pre-registered protocol was designed.** The project states: *"the pre-registration was motivated by a test result."* | **Severe for a confirmatory claim.** It is disclosed, which is the right conduct, but it caps how strongly H6 can be presented |
| 2 | **Only 1 of 8 cells is confirmatory.** The selection effect's sign changes across channel sets and layers | Severe for generalisation |
| 3 | **Bootstrap is an approximation of the official metric.** Each event reduced to one [min, max] span although 81 of 91 M1 test events have several intervals; off-grid events undetectable; TNR from sample counts not seconds. Exact for A1, all A3 seeds, all M2 arms. Differences: H5 −0.330 vs −0.338; H6 +0.352 vs +0.353 — **no verdict changes** | Confirmed defect, small; must be described as an approximation |
| 4 | **Freeze gate covers code only.** Not the freeze record, selection JSONs, OOF outputs, the test driver, or library versions. **A1 selection files predate the last edit of `oof_benchmark.py` and were not re-run** — grids and argmax match the frozen rule, but provenance cannot be attested | Provenance concern; no effect found |
| 5 | **Official "restore" step puts test labels into test inputs** (benchmark-inherent). M1: 51 grid points changed, 13 annotated only because of restore, **zero effect on M1 detections**. M2: 470 points, 1 run exists only through restore. **Not mentioned in the pre-registration** | Benchmark limitation; must be disclosed |
| 6 | **Comparator fairness.** ACI's γ tuned to a point rate, not the event objective; with γ = 0.05 each channel is silenced 80 steps after an exceedance. **Neither supervised scorer had a tuning budget. One deep architecture only** | Material — a reviewer will call this an unfair comparison |
| 7 | **Seed variance.** Trees 0.157–0.769; TCN 0.085–0.358 with 5 seeds → arm means uncertain to about **±0.1** | Material; H4/H5 are underpowered against a +0.05 threshold |
| 8 | **Cross-fitting optimism.** CV strongly over-estimates test performance (lightweight M1: 0.528 → 0.025). **Forward chaining not done** | Material |
| 9 | Mission 2 has only **22 bootstrap blocks**; H6's raw p sits at the 1/2000 floor | Moderate |

**Leakage: the independent code audit found no path by which test-half labels reach any model,
score, calibration pool or selection.** `select()` loads test scores but does not use them. All
identified flows are input-only and quantified. No anomaly or rare event crosses any fold,
selection, calibration or split boundary. **This is a genuine strength.**

## 7. Experiments essential to establish generalisation

| # | Experiment | Answers | Feasible from existing artifacts? |
|---|---|---|---|
| **A** | **Fractional factorial decomposition of H6** over the three plausible drivers (residual scale σ, calibration pool, selection data), 8 cells, pre-registered, on a held-out or clearly-labelled-exploratory basis | *Which* protocol difference carries the +0.353 — the attribution H6 cannot currently support | Requires refitting; the code is frozen and reproduces alarms bit-for-bit, so it is tractable |
| **B** | **Reconcile Brancato et al.** Reproduce their out-of-limit reference (0.754) under their stated protocol | **The dominant rejection risk.** Needs their full text and ideally their code | **Blocked** — paywalled; project gap 1 |
| **C** | **Forward-chaining control** instead of cross-fitting | Quantifies the cross-fitting optimism (0.528 → 0.025 suggests it is large) | Requires refitting; recorded as attempted post hoc (P2) and *"the gain did not replicate by the pre-set rule"* |
| **D** | **Anomaly-only metric reported throughout, alongside the composite** | Removes the Mission 2 saturation artifact from every comparison | **Yes — already in `results.csv`.** Near-zero cost, high value |
| **E** | **Equal tuning budget** for ACI, XGBoost and the TCN; ≥ 2 deep architectures | Closes the comparator-fairness objection (limitation 6) | Requires refitting |
| **F** | **More seeds** for the supervised arms (current 5 / 3 against ±0.1 arm-mean uncertainty) | H4/H5 are currently underpowered against the +0.05 threshold | Requires refitting |
| **G** | A **third mission or later ESA release** with a usable anomaly count | A genuine cross-mission generalisation test. **M2 cannot serve** (6 anomalies); M3 is advised against by its authors (8 anomalies) | **Blocked by data availability** |

**D is free and should be done regardless.** A, C, E, F require refitting but the pipeline is
frozen and reproducible. **B and G are blocked** — by paywall and by data availability
respectively, and both should be reported as blockers rather than worked around.

## 8. Preservation statement

The pre-registered protocol, its freeze records, the deviation log, the post-hoc plan and all
recorded verdicts (**H4 refuted, H5 refuted, H6 supported**) are **unmodified**. Nothing in this
audit reinterprets a pre-registered outcome after the fact: the five-way confound, the Mission 2
metric composition and the Brancato discrepancy were all documented by the project before this
audit, and this document verifies and quantifies them rather than revising the verdicts.
