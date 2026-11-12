# G5d pre-registration — confirmatory test at an unexamined temporal origin

Written: 2026-11-04, **before any model was fitted at origin 2006 and before any outcome at
that origin was scored.** This document is hashed and the hash recorded before execution; the
analysis script reads it and refuses to run if it has changed.

## 1. Why this is confirmatory rather than post-hoc

Every quantitative result in Phases E, H, G+ and G5 is post-hoc: the test folds at origins 2011
and 2016 have been scored repeatedly across the project's history. The project has **no
confirmatory evidence** for any claim.

Origin **2006** (test fold `t0 ∈ [2006-01-01, 2011-01-01)`) has **never been constructed or
scored** in this repository. Verified before writing this document:

- `LR.ORIGINS` contains only `2011` and `2016`;
- origin 2011's test fold is `[2011-01-01, 2016-01-01)` and origin 2016's is
  `[2016-01-01, 2021-10-27)`;
- `test.t0.max() < 2011-01-01` for the candidate fold — **disjoint from both**.

Therefore results at origin 2006 constitute the project's first **confirmatory** evidence.

## 2. Primary hypothesis — the phenomenon

**H1 (primary, confirmatory).** At an unexamined temporal origin, model selection on tune-A
carries no rank information about forward test performance.

- **Operationalisation.** Spearman rank correlation between tune-A pinball and test pinball
  across the learner set.
- **Prediction.** |ρ| < 0.5 (i.e. no strong association), consistent with ρ = +0.000 observed
  at both existing origins.
- **Falsification.** ρ ≥ 0.7 would refute the claim that selection non-transfer is a general
  property of this task and would require withdrawing it.

**H2 (primary, confirmatory).** Model ranking is unstable across temporal origins.

- **Operationalisation.** Rank of each model at origin 2006 versus its rank at origins 2011
  and 2016; and the rank range of `physics_only`.
- **Prediction.** No model holds the same rank across all three origins; `physics_only`'s rank
  varies by ≥ 3 positions across origins.
- **Falsification.** A model ranking first (or within one position of first) at all three
  origins would refute instability.

## 3. Secondary hypothesis — the mechanism

**H3 (secondary).** The point-mass composition shift between the selection and evaluation
populations predicts test loss.

- **Measured a priori** (before fitting), from the split construction alone:

  | Origin | tune-A at-cap | test at-cap | shift |
  |---|---|---|---|
  | 2011 | 0.593 | 0.740 | **+0.148** |
  | 2016 | 0.722 | 0.555 | **−0.167** |
  | **2006 (new)** | **0.398** | **0.665** | **+0.267** |

- **Directional prediction.** Origin 2006's shift is **positive and the largest of the three**,
  with the same sign as origin 2011. Origin 2011 produced Spearman(|cap-mass error|, test
  pinball) = **+0.891**; origin 2016, with a negative shift, produced **−0.158**. If the
  mechanism is real and sign-dependent as that pattern suggests, origin 2006 must produce a
  **positive** correlation, and ≥ +0.5.
- **Falsification.** A correlation ≤ 0 at origin 2006 refutes H3. Combined with origin 2016's
  −0.158, that would mean the mechanism fails in 2 of 3 origins and must be **closed as
  NOT_CONFIRMED and not pursued further**.
- H3 is explicitly **secondary**. H1/H2 do not depend on it.

## 4. Data and splits — fixed

| Element | Value |
|---|---|
| Origin key | `2006` |
| Split tuple | `("1999-01-01", "2001-01-01", "2006-01-01", "2011-01-01")` |
| Population | `uncontrolled` = object classes D, R, C (unchanged) |
| Injection method | `LR.ORIGINS["2006"] = (...)` **at runtime**; `cosmos/ai/lifetime/run.py` is never edited |
| Expected train | 18,960 objects / 3,589 launch families |
| Expected tune-A | 211 / 105 |
| Expected tune-B | 544 / 115 |
| Expected test | **7,281 / 443** |
| Target | `z = log10(min(time_days, 1826.25))`, unchanged |
| Censoring | unchanged (`censor_at` at the origin; `known5` mask) |
| Features | `FULL` feature groups, unchanged |

Split sizes above were computed from the split function before fitting and are recorded here so
a deviation at execution time is detectable.

## 5. Arms — fixed

Exactly the arms the published protocol produces at every origin, with no additions:

1. `physics_only` — physics Monte-Carlo expert.
2. The seven learners of `LEARNER_SET`: xgboost, lightgbm, catboost, mlp, tabm, tabicl, kumo.
3. `cosmos_gated`, `cosmos_gated_tuneA`, `stack_constant`, `equal_average` — fusion arms.
4. Feature-group ablations of the selected learner (`no_family`, `no_physics`, `no_design`,
   `no_space_weather`, `plus_rcs_2026`).
5. **Added for analysis only, no fitting:** `robust_median_blend` and `robust_mean_blend`,
   the parameter-free combinations pre-specified in Phase G+ over
   `(physics_only, tabm, tabicl, kumo)`.

Tuning budget, seeds (0–4) and `n_trials` are the published defaults. No hyperparameter is
tuned on the origin-2006 test fold.

## 6. Metrics — fixed

| Role | Metric | Justification |
|---|---|---|
| Primary | pinball loss of `z` on `known5` objects | quantile-elicited, locally elicitable under fixed-horizon right-censoring (ref. [8]) |
| Interval | empirical coverage at 80 % and 90 % | quantile-endpoint intervals, locally elicitable (ref. [8]) |
| Rank | Spearman correlations as in §2–3 | — |
| **Excluded** | `rmse_log10` | mean-elicited; **not** locally elicitable under fixed-horizon right-censoring (ref. [8]) |

## 7. Statistics — fixed

- Independent unit: **launch family**. Paired cluster bootstrap, 4000 draws, seed `20261027`.
- Multiplicity: Benjamini-Hochberg within each family of related tests.
- Intervals: 95 % percentile.
- Verdicts read from intervals, not point estimates.

## 8. Outcome classification — fixed before execution

| Outcome | Condition |
|---|---|
| **CONFIRMED** | H1 and H2 hold at origin 2006 **and** H3's correlation ≥ +0.5 |
| **PARTIALLY_SUPPORTED** | H1 and H2 hold; H3 is in (0, +0.5) |
| **NOT_CONFIRMED** | H1 and H2 hold; H3 ≤ 0 → the mechanism is closed |
| **INCONCLUSIVE** | H1 or H2 cannot be assessed (e.g. a fit fails) |
| **NOT_EVALUABLE** | the origin-2006 pipeline cannot be executed |

**The novelty claim for the mechanism may be upgraded only under CONFIRMED.** A single
favourable statistic is not sufficient, and H3 is secondary by construction.

## 9. Stopping rule

G5d is executed **once**. The hypothesis is closed on its result regardless of outcome. No
further origins will be added to pursue H3 unless genuinely new independent data arrive.

## 10. Integrity commitments

- `cosmos/ai/lifetime/run.py` and every other published file are **not edited**; the origin is
  injected at runtime.
- Output goes to a new directory `outputs/g5d_origin2006/`; no existing artifact is touched.
- The pre-registration freeze, hashed forecast, L17 columns and all historical results are
  preserved and re-verified after execution.
- If the realised split sizes differ materially from §4, that is reported as a deviation.
