# Censoring-mismatch causal analysis

Date: 2026-11-04. **Outcome: the Phase G+ hypothesis is NOT confirmed, and its attribution is
corrected.** Status: exploratory diagnostic re-analysis.

```bash
python scripts/g5_censoring_causal_analysis.py --n-boot 4000     # exit 0
```
Outputs: `outputs/g5_censoring/g5_causal_results.json`, `g5_cap_decomposition.csv`.
Figures: `outputs/g5_figures/fig_g5_cap_mass.png`, `fig_g5_selection_transfer.png`.

## Correction to Phase G+

Phase G+ reported that tune-A/tune-B are "censored at the origin while test is not", and
attributed the selection failure to that censoring mismatch. **That attribution was wrong in
its mechanism.**

`add_targets` defines `known5 = (event & time_days <= CAP) | (time_days >= CAP)`. Measured:

| Origin | train | tune-A | tune-B | test |
|---|---|---|---|---|
| 2011 | 0.9984 | **1.0000** | **1.0000** | 0.9951 |
| 2016 | 0.9985 | **0.9994** | **1.0000** | 0.9950 |

**`known5` is 0.998–1.000 in every split.** The capped target is effectively always known,
because every split's observation window exceeds the 5-year cap. Censoring relative to the cap
is therefore **not** the differentiator between selection and evaluation.

The `censor_at` call is real and does set `event = 0` for late-ending development objects, but
because `add_targets` then caps the target at 1826.25 days, administrative censoring at the
origin and genuine survival past five years are **indistinguishable in the target**. That is
why the asymmetry does not appear in `known5`.

## What actually differs: the target point mass

`z = log10(min(time_days, CAP))` collapses every object surviving five years onto a single
point, `z = 3.2616`. The share of the population at that point differs between selection and
evaluation — **and reverses direction between the origins**:

| Origin | train | tune-A | tune-B | test | tune-A → test shift |
|---|---|---|---|---|---|
| 2011 | 0.334 | 0.593 | 0.563 | **0.740** | **+0.148** (test cap-heavier) |
| 2016 | 0.389 | **0.722** | 0.645 | 0.555 | **−0.167** (test cap-lighter) |

The driver is launch-epoch composition: tune objects were launched 2004–2006 / 2009–2011 and
test objects 2011–2015 / 2016–2021, with different orbital regimes, launch profiles and
solar-cycle phase.

Target spread differs too: at origin 2016, tune-A `z` has sd 0.503 against test 0.812.

## Testing whether the point-mass shift explains the selection failure

**Falsifiable prediction.** If the cap point mass drives the failure, then (a) a model's
cap-mass error should predict its test loss, and (b) tune-A ranking should track the at-cap
subpopulation of test more closely than the below-cap subpopulation at origin 2016, where
tune-A is cap-heavy.

| Correlation | Origin 2011 | Origin 2016 |
|---|---|---|
| Spearman(tune-A, test overall) | **+0.000** | **+0.000** |
| Spearman(tune-A, test **at-cap**) | −0.429 | −0.536 |
| Spearman(tune-A, test **below-cap**) | +0.321 | −0.107 |
| Spearman(\|cap-mass error\|, test pinball) | **+0.891** | **−0.158** |

**The prediction fails.**

- (a) holds strongly at origin 2011 (ρ = +0.891) and **not at all** at origin 2016 (ρ = −0.158).
- (b) is contradicted: at origin 2016 tune-A tracks the at-cap subset **worse** (−0.536) than
  the below-cap subset (−0.107), the opposite of the prediction.

So the cap point-mass shift is real, large and direction-reversing, but it is **not a
consistent explanation** of the selection failure. **Hypothesis not confirmed.**

A further observation that should give any single-cause account pause: tune-A ranking is
**negatively** correlated with at-cap test performance at *both* origins (−0.43, −0.54).
Tune-A does not merely fail to inform; on that subpopulation it is actively anti-correlated.

## A robust structural finding that does hold

Per-object pinball loss for the deployed expert, decomposed:

| Origin | At-cap loss (95 % CI) | Below-cap loss (95 % CI) | Ratio |
|---|---|---|---|
| 2011 | 0.032336 [0.018471, 0.042676] | **0.133575** [0.110686, 0.166493] | **4.1×** |
| 2016 | 0.017385 [0.010555, 0.027234] | **0.114669** [0.094271, 0.134995] | **6.6×** |

Objects at the cap are nearly free to predict; **essentially all of the loss comes from the
below-cap minority** (26 % of objects at origin 2011, 44 % at 2016). The headline metric is
driven by a minority subpopulation whose size itself varies by epoch.

This is a genuine and reproducible property of the evaluation design, and it has a direct
methodological consequence: **pinball on a capped target is dominated by whichever fraction of
the population happens not to be at the cap**, so the metric's effective sample and its
sensitivity both change with the evaluation epoch.

## Additional leakage / population checks

| Check | Result |
|---|---|
| Future information in selection or calibration | **None found.** `dev` is restricted to `t0 < va_end` and censored at the origin; test begins at the origin. Temporal ordering train < tune < origin ≤ test holds. |
| Launch-family straddling | **None.** Tune-A/tune-B are split by md5 of `launch_family`, and test is disjoint by epoch. |
| `plus_rcs_2026` arm | **Deliberate labelled leak**, excluded from selection by the study's own design and never a candidate. |
| Population selection | Test selects `t0 ∈ [origin, te_end)`, so test objects are *launched after* the origin — a different population from tune, not a subsample of it. **This is the structural driver of the composition shift.** |
| Event-rate differences | tune-A 0.343 vs test 0.533 at origin 2016 — consistent with the composition shift, not with censoring. |

## Conclusion

| Claim | Status |
|---|---|
| Tune/test censoring mismatch causes the selection failure | **REFUTED** — `known5` ≈ 1 in all splits |
| Target cap point mass differs between selection and test | **CONFIRMED** — 0.593→0.740 and 0.722→0.555 |
| That shift reverses direction across origins | **CONFIRMED** |
| The shift explains the selection failure | **NOT CONFIRMED** — ρ = +0.891 at one origin, −0.158 at the other |
| Loss is concentrated in below-cap objects | **CONFIRMED** — 4.1× and 6.6× |
| Selection ranking is anti-correlated with at-cap test performance | **CONFIRMED** at both origins |
| A single cause explains all observed failures | **NOT SUPPORTED** |

The mandate's instruction not to assume a common cause was warranted: the selection failure,
the coverage failure and the feature sign reversals do **not** reduce to one mechanism on this
evidence.

## Limitations

1. Observational decomposition. Showing the loss concentrates below the cap does not show that
   removing the composition shift would fix selection.
2. Two origins; the reversal is observed once in each direction.
3. No model was refitted, so no alternative selection objective was tested.
4. The parent test folds have been scored repeatedly — diagnostic re-analysis, not confirmation.

## What would settle it

A **rolling-origin refit** in which the selection population's cap mass is deliberately matched
to the evaluation population's (for example by selecting on a forward slice rather than a
family split, or by stratifying the selection set on cap status). That is a protocol change
plus retraining, and is not done here.
