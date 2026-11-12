# Performance optimization — final report

Date: 2026-11-04. Branch `product/mission-intelligence-console`. Baseline HEAD `78ee339`.

**Outcome: one recommended change (reporting-only), no model promoted, and a root-cause
diagnosis that explains several previously separate failures as one mechanism.**

## Baseline reconstruction — PASS

All 34 model-origin pinball values recomputed from saved predictions match the published
`regression_test.csv` to **0.00e+00**. All E12 cache reconstructions match published arrays to
**0.0**. Work proceeded on a verified baseline.

## The root cause

`cosmos/ai/lifetime/run.py:split` builds the development set as
`censor_at(d[t0 < va_end], origin)`. Tune-A (model selection) and tune-B (conformal
calibration) are therefore **censored at the forecast origin**, while the test fold is observed
over a long forward window.

| Origin | tune-A n | tune-B n | test n | tune-A event rate | test event rate | tune-A max days | test max days |
|---|---|---|---|---|---|---|---|
| 2016 | 1,741 | 1,560 | 2,993 | 0.343 | 0.533 | 2,555 | 3,951 |
| 2011 | **248** | **332** | 2,680 | 0.423 | 0.447 | 2,542 | **5,778** |

Measured consequence: **Spearman(tune-A pinball, test pinball) = +0.000 at both origins.**
Selection carries no rank information about forward performance. At origin 2016 the selected
learner (`tabm`) ranks **5 of 7** on test and costs **+18.7 %** pinball against the best
available.

### One mechanism, four previously separate findings

| Previously reported as | Now explained by |
|---|---|
| Gated expert underperforms five of its own components (2016) | the gate is fitted on tune-A, an uninformative signal |
| Feature-effect sign reversals, significant in both directions (E12) | ablations fitted to the tune distribution, scored on the test distribution |
| Conformal coverage fails and flips direction (Phase H) | tune-B is censored at the origin, test is not — a **concrete** exchangeability violation |
| C1 not reproducible | the same selection instability |

This is the most substantive scientific result of the phase. It converts "the models are
unstable" into a specific, testable, fixable protocol defect.

## Candidate results

| Candidate | Endpoint | Origin 2016 | Origin 2011 | Promoted? |
|---|---|---|---|---|
| G1 `robust_median_blend` | pinball | **−19.4 %** vs deployed, p_adj < 0.0001 | −1.2 %, n.s. | **No** — one origin only |
| G1 `robust_mean_blend` | pinball | −14.0 %, p_adj < 0.0001 | +10.3 %, n.s. | **No** |
| G1 `robust_mean_blend` | coverage | 2/2 nominal | 2/2 nominal | **No** — endpoint not pre-specified |
| G2 coherent reading | Brier, coherence | Brier −6.1e−03 (30 d), −8.7e−03 (72 d), both p < 0.0001; **0 vs 54** coherence violations | — | **Recommended for reporting** |

### Best verified candidate against every relevant baseline

`robust_median_blend`, origin 2016 (2,978 objects, 621 launch families):

| Baseline | Baseline pinball | Candidate | Δ | Relative | 95 % CI | p_adj |
|---|---|---|---|---|---|---|
| `cosmos_gated` (deployed) | 0.060376 | 0.048644 | −0.011732 | **−19.4 %** | [−0.017346, −0.006829] | <0.0001 |
| `stack_constant` | 0.060122 | 0.048644 | −0.011478 | −19.1 % | [−0.016946, −0.006791] | <0.0001 |
| `equal_average` | 0.069090 | 0.048644 | −0.020446 | −29.6 % | [−0.030519, −0.012010] | <0.0001 |
| `tabm` (tune-A selected) | 0.059292 | 0.048644 | — | −18.0 % | — | not contrasted |
| `tabicl` (best single) | 0.049944 | 0.048644 | — | −2.6 % | — | not contrasted |
| `physics_only` | 0.089249 | 0.048644 | — | −45.5 % | — | not contrasted |

Origin 2011 (2,667 objects, 435 launch families): every contrast **inconclusive**; the
candidate ranks 3rd of 9 behind `physics_only` (0.052676) and `equal_average` (0.052697).

**Criterion 1 fails. Not promoted.**

## Why nothing was promoted

The pre-specified criteria require improvement at **both** origins. Promoting on origin 2016
alone would reproduce exactly the error this phase diagnosed: generalising from one favourable
evaluation population. The incumbent is retained.

## Accepted change

**Report the coherent multi-horizon reading** (`p_lifetime_raw_*`) rather than the
independently-calibrated one. It is coherent by construction and significantly better by Brier
at both evaluated horizons, needs no recalibration or retraining, modifies no published
artifact, and leaves the L17 decision untouched.

Carried caveat: both readings over-forecast by **8.7×–14.8×** on the T1 window. Adopting the
coherent reading improves ranking and removes incoherence; it does **not** make the
probabilities calibrated.

## What was not done

| Item | Status | Reason |
|---|---|---|
| G5 rolling-origin / expanding-window validation | **NOT RUN** | needs refits; **the critical gap** — every candidate is unconfirmed without it |
| G4 physics-prior + learned residual (arms 4–5) | **NOT RUN** | needs new model training; est. hours of compute |
| G6 survival formulations (RSF, discrete-time hazard, Cox) | **NOT RUN** | needs new model training |
| G3 windowed / weighted conformal calibration | **NOT RUN** | needs new calibration fits |
| Telemetry improvement | **NOT RUN** | frozen modules; no unscored test half remains — see [`TELEMETRY_MODEL_IMPROVEMENT.md`](TELEMETRY_MODEL_IMPROVEMENT.md) |
| Debris / collision / re-entry improvements | **NOT RUN** | not reached this pass |
| Ballistic-coefficient and density sensitivity | **NOT RUN** | not attempted |
| Monte Carlo sample-count efficiency (32 samples) | **NOT RUN** | not measured |

## Honesty statement

Every result in this phase is **exploratory**. The test leaderboard was inspected during the
diagnosis, and these test folds have been scored repeatedly across the project's history. They
are no longer a clean held-out population. Nothing here is confirmatory evidence, and the
phase's main output is a diagnosis plus one reporting change — not a performance claim.

## Consequence for the manuscript

Strengthened: the project can now state a **mechanism** for its instability, measured and
reproducible, rather than only reporting that results vary. Specifically —

1. selection/evaluation censoring mismatch, with Spearman +0.000 at both origins;
2. a deployed fusion beaten by 19.4 % at one origin by a parameter-free combiner, and
   outranked by five of its own components there;
3. model ranking not stable across origins (`physics_only` last at 2016, first at 2011);
4. per-horizon isotonic calibration harming both coherence and Brier, with a plateau mechanism
   that explains both symptoms.

Weakened: any claim that COSMOS-AI's lifetime models are well selected, well calibrated, or
stably ordered. Those claims should be removed.

## Integrity verification after this phase

| Check | Result |
|---|---|
| Pre-registration freeze | **INTACT** |
| Hashed 2026-10-27 forecast | **twins.jsonl: OK** |
| L17 isotonic columns | **unmodified** |
| Historical experiment outputs | **unmodified** — all new results in new directories |
| Models retrained | **none** |
