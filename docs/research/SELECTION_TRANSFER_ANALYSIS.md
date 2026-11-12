# Selection-transfer analysis

Date: 2026-11-04. **Finding: model selection does not identify models that generalize forward.**
Status: exploratory.

Evidence: `outputs/g5_censoring/g5_causal_results.json`, `outputs/g5_rolling/g5_rolling_results.json`,
`outputs/phase_g_lifetime/phase_g_lifetime_results.json`. Figure:
`outputs/g5_figures/fig_g5_selection_transfer.png`.

## 1. Tune-A versus future-test rank correlation

| Origin | Models compared | Spearman(tune-A, test) | Selected model | Its test rank | Regret |
|---|---|---|---|---|---|
| 2016 | 7 | **+0.000** | `tabm` | **5 of 7** | **+18.7 %** pinball |
| 2011 | 7 | **+0.000** | `kumo` | 2 of 7 | +3.4 % pinball |

Zero rank correlation at both origins. The selection score and the evaluation score are
rank-independent.

Selection regret = (selected model's test pinball ÷ best achievable test pinball) − 1.

## 2. Decomposed by target subpopulation

| Correlation with tune-A ranking | Origin 2011 | Origin 2016 |
|---|---|---|
| test overall | +0.000 | +0.000 |
| test **at-cap** subset | **−0.429** | **−0.536** |
| test **below-cap** subset | +0.321 | −0.107 |

On the at-cap subpopulation, tune-A ranking is **negatively** correlated with test performance
at both origins. Models that score better on the selection set do measurably *worse* on the
majority subpopulation of the test set. This is stronger than "uninformative".

## 3. Ranking variation across 11 evaluation slices

Pairwise Spearman between slices (55 pairs):

| Statistic | Value |
|---|---|
| Mean | **+0.327** |
| Median | +0.364 |
| Minimum | **−0.400** |
| Fraction of pairs negative | **24 %** |

So ordering is weakly positively associated across epochs, with roughly a quarter of slice
pairs disagreeing in direction. Rank *ranges* per model: `physics_only` 1–11, `equal_average`
1–10, `xgboost` 3–11, `cosmos_gated` 2–9. Only the candidate median blend stays within 1–4.

## 4. Performance by launch family

All intervals in this project resample launch families, because objects within a family share
release conditions and decay together. The practical consequences measured here:

- ignoring that dependence narrows intervals by **more than 3×**
  (`tests/test_phase_e.py::test_paired_bootstrap_widens_when_observations_are_clustered`);
- slices contain 78–151 independent families against 198–841 objects, so the effective sample
  is roughly a fifth of the nominal one;
- a held-out-**family** generalization experiment (train on some families, test on others at
  fixed epoch) was **not run** and would separate family-level from epoch-level instability.

## 5. Does the selection process consistently identify generalizing models?

**No.** Three independent lines of evidence:

1. Zero rank correlation between selection and evaluation at both origins.
2. Negative correlation on the at-cap subpopulation at both origins.
3. The selected model is never the best in any of the 11 evaluation slices, and the deployed
   gated expert built on that selection ranks 2–9 with a mean of 5.73 and is never first.

## 6. Why — and what remains unexplained

The selection and evaluation populations differ structurally: test objects are **launched after
the forecast origin**, so they are a different population rather than a subsample. Measured
differences include the at-cap point mass (0.593 → 0.740 at origin 2011; 0.722 → 0.555 at
2016, reversing direction) and target spread (sd 0.503 vs 0.812 at origin 2016).

But the cap-mass shift **does not consistently predict** test loss across models
(ρ = +0.891 at origin 2011, **−0.158** at 2016), so the composition shift is **not a
sufficient explanation**. See
[`CENSORING_MISMATCH_CAUSAL_ANALYSIS.md`](CENSORING_MISMATCH_CAUSAL_ANALYSIS.md). The
mechanism behind the zero rank correlation is **not established**.

What is established is the *phenomenon*, measured three ways, and the fact that it is **not**
caused by censoring (`known5` ≈ 1 in all splits) and **not** fully explained by the point-mass
shift.

## Consequence for methodology

Any result in this project that depends on having chosen the right model — the gated fusion,
the per-origin best learner, the feature-group ablations fitted with the selected learner's
hyperparameters — inherits this instability. That includes C1's original PARTIALLY SUPPORTED
verdict, which E12 had already downgraded for a related reason.

The constructive implication is that **selection-free combination** is the more defensible
default here, which is why the G1 candidates were specified that way. The median blend's
tight rank range (1–4 across 11 slices) supports that reasoning even though it failed the
coverage criterion and was not promoted.

## Limitations

1. Exploratory: the test folds have been scored repeatedly.
2. Two forecast origins; slices within an origin share training data.
3. 7 models in the selection comparison — a rank correlation on 7 points is noisy, and
   "+0.000" should be read as "no detectable association", not as an exact null.
4. No alternative selection objective was implemented or tested.
