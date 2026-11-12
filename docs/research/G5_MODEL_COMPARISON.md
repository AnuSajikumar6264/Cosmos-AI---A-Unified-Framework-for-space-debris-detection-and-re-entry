# G5 model comparison — candidates against every relevant baseline

Date: 2026-11-04. **Decision: no candidate promoted. Historical baseline retained.**
Status: exploratory.

## Pre-specified criteria (enforced in code)

1. Significantly better (BH-corrected) in a **majority** of the 11 eligible evaluation slices.
2. Significantly worse in **none**.
3. Coverage **not degraded** relative to the incumbent at any nominal level.

## Summary verdict

| Candidate | Criterion 1 (accuracy) | Criterion 2 (no degradation) | Criterion 3 (coverage) | **Verdict** |
|---|---|---|---|---|
| `robust_median_blend` | **MET** (6/11) | **MET** (0 worse) | **FAILED** (cov90 4/11 vs 8/11) | **DO NOT PROMOTE** |
| `robust_mean_blend` | **FAILED** (4/11) | **FAILED** (worse at 2011/2012) | MET (9/11, 10/11) | **DO NOT PROMOTE** |

## Candidate vs every baseline — accuracy

Aggregate test pinball on the full folds (lower is better), with the 11-slice rank summary:

| Model | Origin 2016 | Origin 2011 | Mean rank (11 slices) | Rank range | Times best |
|---|---|---|---|---|---|
| **robust_median_blend** (candidate) | **0.048644** | 0.057549 | **2.27** | **1–4** | 4 |
| tabicl | 0.049944 | 0.059584 | 3.91 | 1–8 | 3 |
| kumo | 0.050768 | 0.061613 | 4.73 | 2–8 | 0 |
| robust_mean_blend (candidate) | 0.051921 | 0.064271 | 5.27 | 2–9 | 0 |
| tabm | 0.059292 | 0.099437 | 8.91 | 6–11 | 0 |
| stack_constant | 0.060122 | 0.060776 | 6.55 | 2–9 | 0 |
| **cosmos_gated** (deployed) | 0.060376 | 0.058263 | 5.73 | 2–9 | **0** |
| equal_average | 0.069090 | **0.052697** | 5.09 | 1–10 | 3 |
| physics_only | 0.089249 | **0.052676** | 7.91 | **1–11** | 1 |
| mlp | 0.057776 | 0.114661 | 8.91 | 5–11 | 0 |
| xgboost | 0.057582 | 0.064842 | 6.73 | 3–11 | 0 |

### Per-slice contrasts, `robust_median_blend` vs the deployed expert

Significantly better in 6 of 11 slices (BH-corrected), worse in 0. Full per-slice deltas with
cluster CIs are in `outputs/g5_rolling/g5_rolling_results.json` and
`outputs/g5_figures/fig_g5_promotion.png`.

Aggregate-fold contrasts from Phase G+ (4000-draw cluster bootstrap, BH-corrected):

| Baseline | Origin 2016 Δ | Relative | p_adj | Origin 2011 Δ | p_adj |
|---|---|---|---|---|---|
| `cosmos_gated` | −0.011732 | **−19.4 %** | <0.0001 | −0.000714 | 0.65 |
| `stack_constant` | −0.011478 | −19.1 % | <0.0001 | −0.003227 | 0.41 |
| `equal_average` | −0.020446 | −29.6 % | <0.0001 | +0.004852 | 0.46 |

## Candidate vs every baseline — calibration

| Model / level | At nominal (of 11 slices) | Under | Over | Empirical range | Mean width (2011 / 2016) |
|---|---|---|---|---|---|
| `robust_mean_blend` / 80 % | **9** | 1 | 1 | 0.583–0.927 | 0.863 / 0.555 |
| `robust_mean_blend` / 90 % | **10** | 0 | 1 | 0.809–0.965 | 1.258 / 0.855 |
| `cosmos_gated` / 80 % | 3 | 4 | 4 | 0.572–0.960 | 0.877 / 0.433 |
| `cosmos_gated` / 90 % | 8 | 0 | 3 | 0.812–0.978 | 1.214 / 0.671 |
| `robust_median_blend` / 80 % | 4 | 0 | 7 | 0.809–0.962 | 0.868 / 0.547 |
| `robust_median_blend` / 90 % | 4 | 0 | 7 | 0.933–0.983 | 1.287 / 0.834 |

## The trade-off that blocked promotion

The two candidates sit at opposite ends of a sharpness/coverage trade-off:

- **median blend** — best accuracy (mean rank 2.27, tightest rank range, best in 4/11 slices,
  −19.4 % against the deployed expert at origin 2016) but **over-covers in 7/11 slices**.
- **mean blend** — best calibration measured anywhere in this project (9/11 and 10/11 at
  nominal, and *narrower* than the incumbent at origin 2011) but not reliably more accurate,
  and significantly **worse** at slice 2011/2012.

Neither dominates. Promoting either would require relaxing a criterion fixed in advance.

## Why the incumbent is retained despite never ranking best

`cosmos_gated` is never first in any of the 11 slices and has mean rank 5.73. It is retained
because:

1. no candidate satisfies the pre-specified criteria;
2. its 90 % interval is the second-best calibrated (8/11, never under-covering);
3. replacing a published model on exploratory evidence from repeatedly-scored folds would be
   precisely the error this phase was designed to avoid.

This is an uncomfortable but correct outcome: the evidence is strong enough to say the
incumbent is **not the best available**, and not strong enough to say which replacement is
reproducibly better.

## G2 — the one accepted change (reporting only)

| Property | isotonic `p_lifetime_*` | coherent `p_lifetime_raw_*` |
|---|---|---|
| Cross-horizon violations | **54** | **0** |
| Brier, 30 d | 8.704e−03 | **2.604e−03** |
| Brier, 72 d | 1.344e−02 | **4.750e−03** |
| Paired Brier Δ | — | −6.100e−03 (30 d), −8.690e−03 (72 d), both p < 0.0001 |
| AUC-ROC | 0.9970 / 0.9944 | 0.9980 / 0.9949 |
| Expected/observed events | 10.51× / 9.52× | 14.79× / **8.73×** |

Accepted as a **reporting choice** for the evaluated comparison. L17 is unchanged, the isotonic
columns are preserved with their provenance, and the recommendation explicitly does **not**
describe either reading as calibrated — both over-forecast by roughly an order of magnitude.

## Artifacts preserved

| Check | Result |
|---|---|
| Pre-registration freeze | **INTACT** |
| Hashed `twins.jsonl` | **OK** |
| L17 isotonic columns | **unmodified** |
| Phase G+ results | **preserved** (`outputs/phase_g_lifetime/`, `outputs/phase_g_multihorizon/`) |
| Historical benchmark/twin artifacts | **unmodified** |
| Models retrained | **none** |
