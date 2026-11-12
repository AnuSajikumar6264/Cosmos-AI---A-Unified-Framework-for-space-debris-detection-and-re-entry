# Phase 3 — Recalibration alternatives for the lifetime intervals (G3′), pre-declared protocol

Declared 2026-11-06, before any alternative was computed. Status: **EXPLORATORY, post hoc**.
Nothing here changes the frozen evaluation protocol, the archived intervals, or the deployed
calibrator; the result informs the Phase 9 discussion of *why* the archived coverage deviates and
whether a different conformal construction would have been defensible. No alternative is adopted.

## Justification

Phase H (`outputs/phase_h/coverage_table.csv`, launch-family cluster bootstrap) found the deployed
Mondrian CQR intervals of `cosmos_gated` **over-cover at origin 2011** (0.923 and 0.959 at nominal
0.80 / 0.90) and **under-cover at origin 2016** (0.717 at nominal 0.80, interval excludes 0). The
same construction errs in opposite directions on two origins, which is the signature of a
calibration set (tune-B) that is not exchangeable with the test cohort — temporal drift between the
calibration window and the forecast origin, not a coding fault. The directive lists "recalibration
alternatives (windowed / weighted)" and allows them only with a pre-declared protocol; this is it.

## Inputs (all archived; nothing refitted)

Per origin `o ∈ {2011, 2016, 2006}`: `tuneB_predictions.npz` (quantiles of every arm on the
calibration split, outcome `z`, `known5`) and `test_predictions.npz` (quantiles and the archived
`lo80/hi80/lo90/hi90`, outcome `z`, `known5`). Group covariates (object class, perigee band, launch
date, launch family) come from `cosmos.ai.lifetime.run.split(load_cohort(), o, "uncontrolled")`, the
same split function that produced the archives. Directories:
`outputs/benchmarks/reentry_lifetime/origin{2011,2016}_uncontrolled/`, `outputs/g5d_origin2006/lifetime/`.

## Arms

`cosmos_gated` (deployed), `physics_only`, and the origin's selected learner
(`summary.json::best_learner_on_tuneA`).

## Reproduction gate (must pass before anything else is reported)

R0 — refit `MondrianCQR(mondrian=True)` on tune-B (`known5` rows) exactly as `run.py` lines
291–301 do and recompute the test intervals. They must equal the archived `lo/hi` arrays to
1e-9 on every object. If they do not, the study stops and the discrepancy is reported.

## Alternatives (each calibrated on tune-B only; the test split is touched once, for scoring)

| id | construction | fixed choices |
|---|---|---|
| R1 | marginal split-CQR (one correction, no groups) | — |
| R2 | Mondrian by object class only (`coarse`) | `MIN_GROUP = 40` as deployed |
| R3 | asymmetric CQR: separate lower and upper corrections, each at `α/2` | symmetric score replaced by two one-sided scores |
| R4 | recency-windowed: Mondrian CQR calibrated on the most recent **half** of tune-B by canonical epoch `t0` | window = median `t0` of tune-B |
| R5 | recency-weighted conformal (weighted empirical quantile, Tibshirani et al. 2019 style) with weights `exp(−Δyears / 2)`, Δ = years between the object's canonical epoch `t0` and the forecast origin; test points carry weight 1; marginal (no groups) | half-life fixed at 2 years before looking at results |

*Time variable (fixed 2026-11-06 before any alternative was run, after reading `run.split`):* the
split itself is defined on the canonical orbit epoch `t0` (`train: t0 < tr_end`, `tune: tr_end ≤ t0 <
va_end`, `test: o ≤ t0 < te_end`), so recency in R4/R5 is measured on `t0`, not on launch date.
Reproduction gate R0 passed on 2026-11-06 before R1–R5 were computed: max |Δ| = 0.0 against the
archived intervals for all nine (origin × arm) pairs.

## Metrics and criterion

For each (origin, arm, level ∈ {0.80, 0.90}, construction): empirical coverage on `known5` test
objects, deviation from nominal, launch-family cluster-bootstrap 95 % CI of the deviation (2,000
draws, seed 20261106), mean interval width in log10 days.

**Primary criterion (pre-declared):** for `cosmos_gated`, the mean absolute deviation from nominal
over the six (origin × level) cells. An alternative is "closer to nominal" if its mean absolute
deviation is below R0's **and** the paired cluster-bootstrap CI of the difference excludes 0.
**Secondary:** mean width relative to R0 — an alternative that reaches nominal only by widening
everywhere is reported as such.

## What this study cannot show

* It cannot validate any construction prospectively: every origin is historical and the test
  outcomes were already used to report the archived coverage (post hoc).
* With three origins there is no basis for choosing a half-life or window size; R4/R5 use the
  single value fixed above and are not tuned.
* Coverage is measured on objects with a known five-year outcome; censored objects are excluded.
* The deployed snapshot (as-of 2026-10-27) has no outcomes, so nothing here can be checked on it.

## Outputs

`outputs/phase3_uncertainty/recalibration_alternatives/{coverage_by_construction.csv, results.json,
run.log}`; regression test `tests/test_recalibration_alternatives.py` pinning R0 reproduction and
the direction of the primary result, whatever it is.
