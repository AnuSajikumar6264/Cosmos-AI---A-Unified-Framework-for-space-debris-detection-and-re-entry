# Part 2 — baseline competitiveness audit

Date 2026-11-05

**Headline: the Brancato out-of-limit discrepancy is explained. The two "out-of-limit" baselines
are not the same estimator — they share a name and nothing else. The project documented this
before I found it. The remaining method-level gap (0.902 vs ~0.09) is NOT explained and remains a
blocker.**

---

## 1. The out-of-limit discrepancy — resolved

| | Brancato et al. (AST 2026) | COSMOS-AI |
|---|---|---|
| Reported M1 full-channel out-of-limit reference | **0.754** | **0.0007** |
| False alarms/year (COSMOS-AI, m1_target) | — | **11,627** |
| Rare-event-only runs (COSMOS-AI, m1_target) | — | 8,802 |

### 1.1 The mechanism, from the project's own code

`cosmos/ai/telemetry/baselines.py:7–10` states it explicitly:

> `out_of_limits` — the operational status quo: alarm when a sample leaves the [min, max] range of
> the channel's NOMINAL training samples (no free parameter). **Brancato et al. (AST 2026,
> doi:10.1016/j.ast.2026.113957) use an out-of-limit detector as their reference; their exact
> limits are not public, so this is ours.**

And the implementation (`baselines.py:42–53`) confirms limits are derived **empirically from the
training half's nominal samples**:

```python
lo[k], hi[k] = np.min(x[keep]), np.max(x[keep])   # keep = nominal training samples
return ((X < lo) | (X > hi)).astype(np.uint8), lo, hi
```

### 1.2 Why this produces a ~1,000× difference

These are different estimators with opposite error profiles:

| | **Empirical [min, max] envelope** (COSMOS-AI) | **Operational channel limits** (the usual meaning) |
|---|---|---|
| Source | Observed training-half nominal range | Engineering red/yellow limits from the mission's telemetry database |
| Width | **Extremely tight** — the narrowest envelope containing the training nominal data | **Wide** — set with engineering margin, well outside normal operation |
| Behaviour on non-stationary telemetry | Any test sample outside the observed training range fires. Over years of test data, across 58 OR-ed channels, essentially everything fires | Fires only on genuinely extreme excursions |
| Consequence | Precision → 0; **11,627 false alarms/year**; EW-F0.5 **0.0007** | High precision; plausibly **0.754** |

**This is a definitional difference, not a protocol error by either side.** A name collision.

### 1.3 Evidence that COSMOS-AI's metric and pipeline are correct

Three independent facts argue the discrepancy is not a COSMOS-AI implementation defect:

1. **The official metric code is byte-identical to upstream.** `ESA_ADB_metrics.py`,
   `latency_metrics.py`, `metric.py`, `ranking_metrics.py` and `utils.py` were verified against
   commit `67194d3` in the shipped tarball.
2. **The ported official GlobalSTD reproduces published values to within 0.001 in all 8
   configurations** (project claim T1, against DMLR Table 4). If the metric adapter and
   preprocessing were wrong, GlobalSTD would not reproduce.
3. **An independent third effort lands in COSMOS-AI's range.** TC-CAD (Şahin, Zenodo
   `10.5281/zenodo.23322711`) reports anomaly event-wise F0.5 of **0.090** at its C-0
   configuration — close to COSMOS-AI's `patchtst` 0.0901 at m1_target, and an order of magnitude
   below Brancato's 0.902.

So two independent groups land near 0.09 and one reports 0.90.

## 2. What remains unexplained — and it is the blocker

**The out-of-limit reference is explained. The method gap is not.**

Brancato's SMED (0.902) and Q-GPR (0.883) are not limit-based detectors, so §1's explanation does
not transfer to them. Their reference baseline scoring 0.754 where a tight-envelope rule scores
0.0007 tells us their entire evaluation sits in a regime where alarms are far sparser — but it
does not tell us why their *methods* score ten times higher.

**Per your instruction I will not speculate about which cause it is.** I can only enumerate the
candidate differences and state exactly what would discriminate between them.

| # | Candidate difference | Why it could produce the gap | What would settle it |
|---|---|---|---|
| 1 | **Channel set** | "Full ESA-ADB hierarchical protocol" may use a different target-channel definition than COSMOS-AI's 58 (M1). Fewer or differently-chosen channels change the OR-ed alarm burden dramatically | Their channel list, or the count |
| 2 | **Hierarchy level reported** | The ESA-ADB protocol is hierarchical (global / subsystem / channel). COSMOS-AI reports event-wise F0.5 at the global level. A subsystem- or channel-level figure is a different number | Which hierarchy level their 0.902 is at |
| 3 | **Metric variant** | COSMOS-AI's headline is `anomaly_and_rare`; `anomaly`-only differs sharply (§4). If Brancato report one and COSMOS-AI the other, the numbers are not comparable | Whether 0.902 covers anomalies only or anomalies + rare events |
| 4 | **Event matching / aggregation** | Their 8-archetype event-morphology taxonomy implies substantial post-processing before scoring | Their aggregation and merge rules |
| 5 | **Test population / period** | "Mission 1 only" could denote a channel or temporal subset rather than the full official test half | Their test-half definition and event counts |
| 6 | **Adaptive retraining** | Their methods retrain adaptively over the test period; COSMOS-AI's protocol fits once. This is a legitimate method difference, not an incomparability — but it changes the regime | Their retraining schedule |

**Information required, minimally:** the full text of `10.1016/j.ast.2026.113957` — specifically
its channel set, the hierarchy level of the reported F0.5, the metric variant
(anomaly vs anomaly+rare), the event-matching rule, and the out-of-limit definition. Their code
would settle it outright.

**Status: BLOCKED — paywalled.** The project's own evidence gap 1 says the same: *"cannot be
reconciled with this study without their full text and code."*

### 2.1 Consequence for claims

**No competitive-performance or superiority claim is defensible for the ESA-ADB track until this
is resolved.** What remains defensible:

- The **within-study protocol comparison** (H6: A1 − A0 = +0.353 [+0.206, +0.488], Holm
  p = 0.0015). A relative contrast between two protocols evaluated identically is not exposed to
  the discrepancy.
- The **negative deep-learning result** (H4, H5 refuted), also a within-study contrast.
- The **mechanism finding** that event aggregation succeeds where point-level adaptive calibration
  fails.

What is **not** defensible: any statement positioning COSMOS-AI's absolute numbers against the
published state of the art on M1 full channels.

## 3. Baseline competitiveness per track

### Track 1 — OPS-SAT

| Baseline family | Arm | Time-blocked AUC-PR | Assessment |
|---|---|---|---|
| Foundation model | `chronos-bolt-small` | 0.9191 | **Strong, modern comparator.** Used as frozen embeddings + linear probe — a fair but *different-information* setup that must be documented |
| Gradient boosting | `xgboost` / `lightgbm` / `catboost` | 0.9639 / — / — | Strong |
| Lightweight neural | `fcnn` (13k params) / `cnn` (68k) / `transformer` (71k) | 0.9666 / 0.9712 / 0.9418 | Strong |
| Classical | `logreg`, `random_forest`, `adaboost`, `cosmos_robust_z` | 0.9617 / 0.9555 / 0.9440 / 0.6732 | Adequate |
| Isolation | `iforest` | 0.3313 | Present; uses no labels — information difference must be stated |
| **Reconstruction** | — | — | **ABSENT.** The one standard family missing |
| **Published satellite-specific method** | — | — | **ABSENT on OPS-SAT** (`patchtst` is only on ESA-ADB) |

**Verdict: competitive and nearly complete.** Eleven arms across five families, one protocol, five
seeds. Two gaps, both cheap to close. **Critically: the fusion does not beat its own CNN branch**
(0.9712 vs 0.9719 time-blocked, +0.0007; `cnn` is *better* on the official protocol), so the
architectural claim is unsupported — see `PART2_SCIENTIFIC_NOVELTY_COMPARISON.md`.

### Track 2 — Orbital lifetime

| Baseline | Status |
|---|---|
| `physics_only` (analytic drag) | Present — and **wins at origin 2011 (1st of 19)** |
| Trivial combiners (`equal_average`, `stack_constant`) | Present |
| 6 learned families + gated fusion | Present |
| Feature ablations (4 groups + 1 additive) | Present, but **untuned** (inherit parent hyperparameters) |
| **External published method** | **ABSENT** |
| **Trivial reference predictor** (empirical marginal quantiles, constant-at-cap) | **ABSENT** |
| ML-dSGP4-class | Not attempted — **justified**: no TLE/B\*/ephemeris data, and Shorten et al. (2023) independently documents TLE hazards |

**Verdict: internally thorough, externally uncalibrated.** Every reference point is the project's
own. A reviewer cannot tell whether absolute losses are good. **A trivial marginal-quantile
baseline is nearly free from archives and should be added.**

### Track 3 — ESA-ADB

| Baseline | m1_lightweight | m1_target | Assessment |
|---|---|---|---|
| **`global_std` (official)** | 0.2527 (std5) / 0.0011 (std3) | 0.0029 / 0.0004 | **Reproduces published values to within 0.001 in 8 configurations** — the strongest validity evidence in the project |
| `out_of_limits` | 0.2019 | 0.0007 | Present but **not comparable to Brancato's** (§1) |
| `ar8` | 0.4025 ± 0.0083 | 0.0768 ± 0.0105 | Strong unsupervised forecaster |
| **`patchtst` (published)** | 0.3725 ± 0.1589 | 0.0901 ± 0.0481 | **Published architecture, re-implemented** |
| `tcn` (EventTCN, 220,739 params) | — | 0.1587 ± 0.1834 | The supervised arm; **no benefit** (H4, H5 refuted) |
| `chronos-bolt-small` | — | 0.0215 ± 0.0205 | Foundation model |
| `cosmos_monitor` | 0.2021 | 0.0038 | The project's own monitor — **ties a trivial rule at lightweight, far worse at full scale** |
| Point-level ACI comparator | — | — | Present, but **γ tuned to a point rate, not the event objective** — a fairness defect the project records |

**Verdict: the strongest baseline set in the project, with two defects.** It includes a reproduced
official baseline, a published architecture, a foundation model and label-free rules. The defects
are (a) the ACI comparator's tuning mismatch, (b) **neither supervised scorer had a tuning budget,
and only one deep architecture was tried** — both recorded in the project's own risk ranking.

## 4. The anomaly-only versus composite metric problem

This affects baseline interpretation on every ESA-ADB comparison and should be reported throughout.

| Mission / scale | Arm | `anomaly_and_rare/EW_F0.5` | `anomaly/EW_F0.5` |
|---|---|---|---|
| M2 lightweight | `out_of_limits` | **0.9648** | **0.0877** |
| M2 lightweight | `cosmos_monitor` | 0.7881 | **0.0000** |
| M2 lightweight | `ar8` | 0.7741 | **0.0000** |
| M2 lightweight | `patchtst` | 0.7028 | **0.0000** |
| M2 target | `ar8` | 0.7940 | 0.2157 |
| M1 target | `patchtst` | 0.0901 | 0.0661 |

M2's test half holds **6 anomalies and 356 rare events**, so the composite is ~98 % rare-event
driven. **Every learned arm scores exactly 0.0000 on anomalies at M2 lightweight.** The project
reached the same conclusion independently: *"Mission 2 is near-saturated."*

**Recommendation: report the anomaly-only metric alongside the composite everywhere.** It is
already in `results.csv`, so the cost is zero and it removes a systematic misreading.

## 5. Summary

| Question | Answer |
|---|---|
| Is the out-of-limit discrepancy explained? | **Yes** — different estimators sharing a name (§1). Documented in the project's own code |
| Is COSMOS-AI's metric implementation sound? | **Yes** — byte-identical official metric; GlobalSTD reproduced to 0.001 in 8 configurations |
| Is the method-level gap (0.902 vs ~0.09) explained? | **No. BLOCKED on paywalled full text.** Six candidate causes enumerated; none speculated upon |
| Can a competitive-performance claim be made for Track 3? | **No, not until resolved** |
| Can the H6 protocol comparison still be claimed? | **Yes** — a within-study relative contrast is not exposed to the discrepancy |
| Which track has the most competitive baselines? | **Track 3**, then Track 1, then Track 2 |
| Which track is externally uncalibrated? | **Track 2** — every reference point is internal |
