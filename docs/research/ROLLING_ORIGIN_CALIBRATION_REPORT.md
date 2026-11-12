# Rolling-origin calibration report

Date: 2026-11-04. **Finding: no model attains nominal coverage across evaluation epochs, and
the deployed expert's 80 % interval is wrong in both directions depending on epoch.**

Evidence: `outputs/g5_rolling/g5_coverage_by_slice.csv`, `outputs/phase_h/`.
Figure: `outputs/g5_figures/fig_g5_coverage_by_slice.png`.

## Coverage across 11 evaluation slices

| Model / level | At nominal | Under-covers | Over-covers | Empirical range |
|---|---|---|---|---|
| `cosmos_gated` / 80 % | **3 / 11** | 4 | 4 | 0.572 – 0.960 |
| `cosmos_gated` / 90 % | 8 / 11 | 0 | 3 | 0.812 – 0.978 |
| `robust_mean_blend` / 80 % | **9 / 11** | 1 | 1 | 0.583 – 0.927 |
| `robust_mean_blend` / 90 % | **10 / 11** | 0 | 1 | 0.809 – 0.965 |
| `robust_median_blend` / 80 % | 4 / 11 | 0 | 7 | 0.809 – 0.962 |
| `robust_median_blend` / 90 % | 4 / 11 | 0 | 7 | 0.933 – 0.983 |

Verdicts are cluster-bootstrapped per slice (launch-family resampling), so "at nominal" means
the deviation's 95 % interval includes zero — not that the point estimate looks close.

## Readings

**1. The deployed expert's 80 % interval fails in both directions.** It under-covers in 4
slices and over-covers in 4, reaching nominal in only 3 of 11, with empirical coverage spanning
**0.572 to 0.960**. A single "80 % interval" claim is not supportable; the realised level
depends on which launch epoch is evaluated.

**2. The 90 % interval is more robust than the 80 %** for the deployed expert (8/11 at nominal,
never under-covering). If one interval must be reported, the 90 % level is the defensible one.

**3. `robust_mean_blend` is the best-calibrated model measured** — 9/11 and 10/11 at nominal —
and it achieves this without systematic width inflation (at origin 2011 it is **narrower** than
the incumbent: mean width 0.863 vs 0.877 in log10 days). It was still **not promoted**, because
the pre-specified accuracy criterion failed (better in 4/11, worse in 1).

**4. The accuracy-leading candidate is the worst calibrated.** `robust_median_blend` over-covers
in 7/11 slices at both levels. Taking a median across quantile functions narrows the central
estimate but does not shrink the combined interval bounds proportionally, so intervals end up
conservative. This is the accuracy/calibration trade-off that blocked promotion.

**5. Coherence is not calibration.** The G2 finding — that the coherent `p_lifetime_raw_*`
reading beats the isotonic one on Brier at both horizons — sits alongside the fact that **both
readings over-forecast by 8.7×–14.8×** on the T1 window. A coherent, better-ranked probability
is still not a calibrated probability, and must not be described as one.

## Temporal degradation (Phase H, unchanged)

| Origin | Model | cov90 range | Spread | Rank trend with year |
|---|---|---|---|---|
| 2016 | physics_only | 0.732 – 0.974 | **0.242** | **−0.94** |
| 2016 | cosmos_gated | 0.812 – 0.963 | 0.151 | **−0.83** |
| 2011 | cosmos_gated | 0.929 – 0.978 | 0.049 | −0.60 |

Near-monotone decline with time from the origin at origin 2016.

## Exchangeability — what is and is not violated

Conformal validity requires the calibration and test data to be exchangeable. Measured facts:

| Candidate violation | Measured? | Verdict |
|---|---|---|
| Censoring differs between tune-B and test | **No** — `known5` ≈ 1 in both | **not a violation** |
| Target point mass differs (tune-B 0.563/0.645 vs test 0.740/0.555) | **Yes**, and it reverses direction | **violation** |
| Test objects launched after the origin (different population, not a subsample) | **Yes**, by construction | **violation** |
| Calibration-set size (332 objects at origin 2011) | **Yes** | weak calibration, compounding the above |

So exchangeability **is** violated, but the earlier censoring-based account of *how* was wrong
(see [`CENSORING_MISMATCH_CAUSAL_ANALYSIS.md`](CENSORING_MISMATCH_CAUSAL_ANALYSIS.md)).

**No distribution-free coverage guarantee may be claimed.** The guarantee's precondition is
measurably false, and the realised coverage is measurably wrong — in both directions.

## Claims that must be withdrawn or qualified

| Claim | Required change |
|---|---|
| "Conformalised intervals provide distribution-free coverage" | **Withdraw.** Exchangeability is violated and coverage is not attained. |
| "The 80 % interval is calibrated" | **Withdraw.** 3/11 slices at nominal, range 0.572–0.960. |
| "The 90 % interval is calibrated" | **Qualify** — 8/11 slices for the deployed expert, never under-covering; state the range. |
| "Uncertainty is validated" | **Withdraw.** Implemented and measured, not validated. |
| "Coverage degrades under temporal shift" | **Supportable**, with rank trends −0.83 to −0.94 and the per-slice table. |

## Not run

- Windowed / rolling conformal recalibration per slice (**G3**) — would test whether refreshing
  the calibration set per epoch restores coverage. This is the most promising remaining
  uncertainty experiment.
- Weighted or adaptive conformal prediction under covariate shift.
- Direct conformalisation of the blend rather than combining member bounds.
- Censoring-aware coverage on objects *without* a known five-year outcome (currently excluded).
