# G5 rolling-origin validation

Date: 2026-11-04. **Outcome: no candidate promoted.** The historical baseline is retained.

```bash
python scripts/g5_rolling_origin.py --n-boot 2000       # exit 0
python scripts/g5_figures.py                            # exit 0, 5 figures
```
Outputs: `outputs/g5_rolling/` (results JSON, per-slice rank / pinball / coverage CSVs),
figures in `outputs/g5_figures/`.

## Design, stated precisely

A full rolling-origin experiment refits every learner at each new forecast origin. **That was
not done** — it needs hours of GPU time and new tuning passes, and the repository defines only
two origins (2011, 2016).

What was done instead: the fitted models are **held fixed** and the **evaluation population is
advanced** through 11 chronological launch-year slices of the two existing test folds.

| Origin | Slices | Objects per slice | Launch families per slice |
|---|---|---|---|
| 2011 | launch years 2011–2015 | 198–758 | 78–133 |
| 2016 | launch years 2016–2021 | 282–841 | 87–151 |

All 11 slices passed the eligibility thresholds (≥ 150 objects, ≥ 40 launch families), fixed
before scoring.

**This tests evaluation-population sensitivity, not retraining sensitivity.** It is a weaker
design than rolling-origin retraining and that distinction is carried through every result
below. It is nonetheless far stronger than Phase G+'s two evaluation populations, and the
slices differ enormously in composition — the at-cap share runs from 0.881 (2017) to **0.284**
(2019), with the event rate moving inversely from 0.304 to 0.754.

## Pre-specified promotion criteria

Fixed before scoring, and now **enforced in code** (`promotion` block in the script):

1. Significantly better (BH-corrected across slices) in a **majority** of eligible slices.
2. Significantly worse in **none**.
3. Coverage **not degraded** relative to the incumbent at any nominal level.

An earlier draft of the script stated criterion 3 but did not enforce it; that was corrected
before the result was interpreted, and the correction changed the verdict (see the decision
log).

## Results

### Best model per slice — no model is consistently best

| Slice | n | families | at-cap | Best model | Deployed expert's rank |
|---|---|---|---|---|---|
| 2011/2011 | 597 | 91 | 0.704 | physics_only | 4 |
| 2011/2012 | 758 | 133 | 0.695 | equal_average | 2 |
| 2011/2013 | 198 | 78 | 0.667 | equal_average | 3 |
| 2011/2014 | 529 | 106 | 0.790 | tabicl | 6 |
| 2011/2015 | 585 | 90 | 0.832 | equal_average | 5 |
| 2016/2016 | 408 | 87 | 0.814 | robust_median_blend | 7 |
| 2016/2017 | 654 | 102 | 0.881 | robust_median_blend | 5 |
| 2016/2018 | 282 | 151 | 0.582 | tabicl | 5 |
| 2016/2019 | 356 | 131 | 0.284 | robust_median_blend | 8 |
| 2016/2020 | 841 | 120 | 0.389 | robust_median_blend | 9 |
| 2016/2021 | 437 | 122 | 0.371 | tabicl | 9 |

Five different models take first place across 11 slices. **The deployed expert is never
best**, and its rank degrades monotonically through the origin-2016 slices (5 → 9).

### Ranking stability

| Model | Mean rank | Min | Max | Range | Times best |
|---|---|---|---|---|---|
| **robust_median_blend** | **2.27** | 1 | 4 | **3** | 4 |
| tabicl | 3.91 | 1 | 8 | 7 | 3 |
| kumo | 4.73 | 2 | 8 | 6 | 0 |
| equal_average | 5.09 | 1 | 10 | 9 | 3 |
| robust_mean_blend | 5.27 | 2 | 9 | 7 | 0 |
| cosmos_gated (deployed) | 5.73 | 2 | 9 | 7 | 0 |
| stack_constant | 6.55 | 2 | 9 | 7 | 0 |
| xgboost | 6.73 | 3 | 11 | 8 | 0 |
| **physics_only** | 7.91 | **1** | **11** | **10** | 1 |
| mlp | 8.91 | 5 | 11 | 6 | 0 |
| tabm | 8.91 | 6 | 11 | 5 | 0 |

`physics_only` spans the **entire range, rank 1 to rank 11**. The candidate median blend has
the tightest range (3) and the best mean rank (2.27).

**Pairwise rank agreement between slices**: mean Spearman **+0.327**, median +0.364, minimum
**−0.400**, and **24 % of slice pairs are negatively correlated**. Model ordering is weakly
positively associated across epochs and frequently inverts.

### Promotion decision

| Candidate | Accuracy criterion | Coverage criterion | Verdict |
|---|---|---|---|
| `robust_median_blend` | **MET** — better in **6/11**, worse in 0 | **FAILED** — cov90 at-nominal 4/11 vs incumbent 8/11 | **DO NOT PROMOTE** |
| `robust_mean_blend` | **FAILED** — better in 4/11, worse in 1 (2011/2012) | MET — cov80 9/11 vs 3/11; cov90 10/11 vs 8/11 | **DO NOT PROMOTE** |

**Neither candidate satisfies both criteria.** There is a genuine accuracy/calibration
trade-off: the median blend is sharper and more accurate but systematically over-covers
(7/11 slices at both levels); the mean blend is the best-calibrated model in the comparison but
is not reliably more accurate and degrades at one slice.

The historical baseline (`cosmos_gated`) is **retained**, despite never ranking best in any
slice. Retaining it is the correct decision under the pre-specified criteria, and that is the
point of specifying them in advance.

## Figures

| Figure | Content |
|---|---|
| `fig_g5_rank_by_slice.png` | model rank across the 11 slices; `physics_only` collapsing 1 → 11 at the origin boundary |
| `fig_g5_promotion.png` | per-slice Δ pinball vs deployed, with cluster CIs and significance |
| `fig_g5_coverage_by_slice.png` | empirical coverage vs nominal at both levels across slices |
| `fig_g5_cap_mass.png` | at-cap fraction by split and origin, showing the direction reversal |
| `fig_g5_selection_transfer.png` | tune-A vs test pinball scatter, Spearman +0.000 at both origins |

## Evidential status

**Exploratory.** The parent test folds have been scored repeatedly across the project's
history, and the slices are sub-populations of them. This is a robustness re-analysis and
**not** independent confirmation. A genuinely confirmatory evaluation requires either a
rolling-origin refit or eligible future observations (Phase F, from 2026-11-26).

## Limitations

1. Models were not refitted per slice; only the evaluation population advances.
2. Slices are sub-populations of already-scored folds.
3. Slice sizes (198–841 objects) limit within-slice power.
4. Only two forecast origins underlie the 11 slices, so slices within an origin share training
   data and are not independent of one another.
5. Blend interval bounds are combined from member bounds rather than conformalised directly.

## What was not run

| Item | Status | Cost |
|---|---|---|
| Rolling-origin **refit** at new origins (e.g. 2013, 2018) | **NOT RUN** | ~1–3 h GPU per origin |
| Arm B — consistent censoring treatment in the development set | **NOT RUN** | protocol change + refits |
| Arm C — survival-aware selection (IPCW, survival likelihood) | **NOT RUN** | new objective + refits |
| Arm D — selection-free ensemble | **DONE** (this document) | none |
