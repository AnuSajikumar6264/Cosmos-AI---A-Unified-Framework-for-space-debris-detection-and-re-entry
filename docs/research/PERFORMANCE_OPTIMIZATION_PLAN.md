# Performance optimization plan — diagnosis-driven

Date: 2026-11-04. This plan was written **after** the diagnosis below, not before it, so that
the candidate experiments address measured causes rather than guesses.

## Baseline reconstruction — passed

All 34 model-origin pinball values were recomputed from the saved test predictions and match
the published `regression_test.csv` to **0.00e+00**. Work proceeds on a verified baseline.

```bash
python scripts/phase_g_lifetime_optimization.py --n-boot 4000   # includes the reconstruction
```

## Root-cause diagnosis

### Finding 1 — model selection carries zero information about forward performance

| Origin | Selected on tune-A | Its test rank | Spearman(tune-A, test) | Cost vs best achievable |
|---|---|---|---|---|
| 2016 | `tabm` | **5 of 7** | **+0.000** | **+18.7 %** pinball |
| 2011 | `kumo` | 2 of 7 | **+0.000** | +3.4 % pinball |

### Finding 2 — the mechanism is a selection/evaluation distribution mismatch

`run.py:split` builds the development set as `censor_at(d[t0 < va_end], origin)`. Tune-A and
tune-B are therefore **censored at the forecast origin**, while the test fold is observed over
a long forward window:

| Origin | tune-A n | tune-B n | test n | tune-A event rate | test event rate | tune-A max days | test max days |
|---|---|---|---|---|---|---|---|
| 2016 | 1,741 | 1,560 | 2,993 | 0.343 | 0.533 | 2,555 | 3,951 |
| 2011 | **248** | **332** | 2,680 | 0.423 | 0.447 | 2,542 | **5,778** |

Two problems compound:

1. **Horizon truncation.** The selection set cannot observe lifetimes beyond ~2,550 days; the
   test fold at origin 2011 extends to 5,778 days. Models are chosen on a short-horizon,
   heavily censored target and scored on a long-horizon one.
2. **Tiny selection and calibration sets at origin 2011** — 248 objects for choosing among 7
   learners and **332** for conformal calibration.

### Finding 3 — this single mechanism explains four previously separate findings

| Previously reported as | Actually a symptom of |
|---|---|
| Gated expert underperforms its own components (2016: 0.0604 vs tabicl 0.0499) | selection non-transfer |
| Feature-effect sign reversals across learners (E12) | ablations fitted to the tune distribution, scored on the test distribution |
| Conformal coverage fails and flips direction (Phase H) | **tune-B is censored at the origin, test is not** — a concrete exchangeability violation, not generic drift |
| C1 not reproducible | the same selection instability |

Phase H's coverage result now has a mechanism: over-coverage at origin 2011 (tiny, short-window
calibration set → conservative residuals) and under-coverage at 80 % at 2016.

## Candidate experiments, in priority order

| ID | Candidate | Rationale | Cost | Status |
|---|---|---|---|---|
| **G1** | Selection-free robust combination (median / mean of a pre-specified candidate set) | if selection does not transfer, do not select | none (saved quantiles) | **DONE** → [`LIFETIME_MODEL_IMPROVEMENT.md`](LIFETIME_MODEL_IMPROVEMENT.md) |
| **G2** | Coherent multi-horizon reading instead of per-horizon isotonic | fixes L17 coherence with no recalibration | none | **DONE** → [`MULTI_HORIZON_CALIBRATION_EXPERIMENTS.md`](MULTI_HORIZON_CALIBRATION_EXPERIMENTS.md) |
| G3 | Horizon-matched / windowed conformal calibration | targets the measured exchangeability violation directly | needs new calibration fits | **NOT RUN** |
| G4 | Physics + learned residual model | tests whether physics is better used as a prior than as features | needs model training | **NOT RUN** (partial evidence from G1) |
| G5 | Rolling-origin / expanding-window validation | the only way to confirm any candidate | needs refits at new origins | **NOT RUN** — this is the critical gap |
| G6 | Survival-formulation comparison (RSF, discrete-time hazard, Cox) | censoring handled natively rather than by capping | needs model training | **NOT RUN** |
| G7 | Telemetry improvements | pre-registration must stay intact | new experiments | **NOT RUN** → [`TELEMETRY_MODEL_IMPROVEMENT.md`](TELEMETRY_MODEL_IMPROVEMENT.md) |

## Pre-specified acceptance criteria

Fixed **before** any candidate was scored on test:

1. Must improve pinball significantly (BH-corrected, launch-family cluster bootstrap) against
   the incumbent at **both** temporal origins.
2. Must not significantly degrade against any incumbent at either origin.
3. Must not lose interval coverage relative to the incumbent.
4. A single favourable origin is **not** sufficient.
5. Nominal coverage attained by inflating interval width does not count as improvement.

## Honesty constraint recorded up front

The test leaderboard was inspected during the diagnosis. Every candidate result is therefore
**exploratory**. The candidates are parameter-free and derived from the diagnosed mechanism
rather than fitted to the test fold, but **confirmation requires a fresh temporal origin
(G5)**, which has not been run.
