# Lifetime model improvement — G1 robust combination

Date: 2026-11-04. Verdict: **DO NOT PROMOTE on accuracy.** One notable calibration finding.
Status: **exploratory** (the test leaderboard was seen during diagnosis).

```bash
python scripts/phase_g_lifetime_optimization.py --n-boot 4000     # exit 0
```
Outputs: `outputs/phase_g_lifetime/phase_g_lifetime_results.json`, `lifetime_candidate_table.csv`.

## Hypothesis

Because tune-A selection carries zero rank information about forward test performance
(Spearman +0.000 at both origins), a **selection-free** parameter-free combination will
outperform the tune-A-selected gated expert and be more stable across origins.

## Candidate specification — fixed before scoring

Members chosen **by role, not by test performance**:

- `physics_only` — the domain prior, available at every origin;
- `tabm`, `tabicl`, `kumo` — the study's own pre-specified pool `models.RECENT`.

Combiners: row-wise **median** and row-wise **mean** of the quantile matrices, then sorted
along the quantile axis (exactly as `run.py` monotonises its seed ensembles). **No parameters.**

Incumbents: `cosmos_gated` (deployed), `equal_average`, `stack_constant`.
Endpoint: pinball loss of log10 capped lifetime on objects with a known five-year outcome.
Independent unit: launch family. 4000-draw paired cluster bootstrap, BH across 6 contrasts.

## Accuracy results

### Origin 2016 (2,978 objects, 621 launch families)

| Model | Pinball |
|---|---|
| **robust_median_blend** | **0.048644** |
| tabicl | 0.049944 |
| kumo | 0.050768 |
| robust_mean_blend | 0.051921 |
| tabm (tune-A selected) | 0.059292 |
| stack_constant | 0.060122 |
| cosmos_gated (deployed) | 0.060376 |
| equal_average | 0.069090 |
| physics_only | 0.089249 |

| Contrast | Δ | Relative | 95 % CI | p_adj | Verdict |
|---|---|---|---|---|---|
| median_blend vs cosmos_gated | −0.011732 | **−19.4 %** | [−0.017346, −0.006829] | **<0.0001** | **candidate better** |
| median_blend vs equal_average | −0.020446 | −29.6 % | [−0.030519, −0.012010] | **<0.0001** | candidate better |
| median_blend vs stack_constant | −0.011478 | −19.1 % | [−0.016946, −0.006791] | **<0.0001** | candidate better |
| mean_blend vs cosmos_gated | −0.008455 | −14.0 % | [−0.013050, −0.004219] | **<0.0001** | candidate better |

### Origin 2011 (2,667 objects, 435 launch families)

| Model | Pinball |
|---|---|
| **physics_only** | **0.052676** |
| equal_average | 0.052697 |
| robust_median_blend | 0.057549 |
| cosmos_gated (deployed) | 0.058263 |
| tabicl | 0.059584 |
| kumo (tune-A selected) | 0.061613 |
| robust_mean_blend | 0.064271 |
| tabm | 0.099437 |

| Contrast | Δ | Relative | 95 % CI | p_adj | Verdict |
|---|---|---|---|---|---|
| median_blend vs cosmos_gated | −0.000714 | −1.2 % | [−0.004070, +0.002167] | 0.6545 | inconclusive |
| median_blend vs equal_average | +0.004852 | +9.2 % | [−0.003215, +0.011819] | 0.4612 | inconclusive |
| median_blend vs stack_constant | −0.003227 | −5.3 % | [−0.006955, +0.000215] | 0.4110 | inconclusive |
| mean_blend vs cosmos_gated | +0.006008 | +10.3 % | [−0.002159, +0.016271] | 0.4612 | inconclusive |

## Promotion decision — DO NOT PROMOTE

Both candidates improve significantly against **all three** incumbents at origin 2016 and are
**inconclusive against every incumbent** at origin 2011. Criterion 1 (significant improvement
at **both** origins) fails. Criterion 4 explicitly forbids promotion on one favourable origin.

Neither candidate significantly degrades anywhere, so the honest statement is: *a large,
significant gain at one origin and no detectable difference at the other.* That is not
reproducible improvement.

## The deeper finding — no model wins at both origins

| Model | Rank at 2016 | Rank at 2011 |
|---|---|---|
| robust_median_blend | **1** | 3 |
| tabicl | 2 | 5 |
| physics_only | **9 (last)** | **1** |
| equal_average | 8 | 2 |
| cosmos_gated (deployed) | 7 | 4 |
| tabm | 5 | **8** |

`physics_only` goes from **last at 2016 to first at 2011**. This is the same non-transfer
phenomenon as the selection failure, now visible in the model ranking itself. **The ordering of
models is not a stable property of the task**; it is a property of the (model, origin) pair.

A consequence for the manuscript: no "best lifetime model" claim is defensible from two
origins. The defensible claim is about the *instability itself*, which is measured.

## Notable secondary finding — `robust_mean_blend` is the only well-calibrated model

Cells attaining nominal coverage (cluster-bootstrapped), out of 2 levels per origin:

| Model | Origin 2011 | Origin 2016 | Total |
|---|---|---|---|
| **robust_mean_blend** | **2 / 2** | **2 / 2** | **4 / 4** |
| cosmos_gated (deployed) | 0 / 2 | 1 / 2 | 1 / 4 |
| stack_constant | 0 / 2 | 1 / 2 | 1 / 4 |
| equal_average | 0 / 2 | 0 / 2 | 0 / 4 |
| robust_median_blend | 0 / 2 | 0 / 2 | 0 / 4 |

| Model | 2011 cov80 / cov90 | width | 2016 cov80 / cov90 | width |
|---|---|---|---|---|
| robust_mean_blend | 0.7698 / 0.8796 | 0.863 | 0.8015 / 0.9060 | 0.555 |
| cosmos_gated | 0.9231 / 0.9591 | 0.877 | 0.7169 / 0.8741 | 0.433 |

It is **not** achieved by inflating width: at origin 2011 the mean blend is **narrower** than
the deployed expert (0.863 vs 0.877) *and* better calibrated. At 2016 it is wider (0.555 vs
0.433), but the deployed expert **under-covers** there, so the extra width is warranted rather
than wasteful.

**This is not grounds for promotion.** The pre-specified acceptance criteria are stated on
pinball; promoting on coverage after seeing the coverage table would be changing the endpoint
after the fact. It is recorded as an exploratory observation worth a confirmatory test.

## Why the gated fusion underperforms

At origin 2016 the deployed `cosmos_gated` (0.0604) is worse than five of its own candidate
components, including `tabicl` (0.0499). The gate is fitted on tune-A — the same distribution
that carries zero rank information about test. The gate is not broken as code; it is fitted on
an uninformative signal. This is why a parameter-free combiner beats it by 19.4 % at 2016.

## Limitations

1. **Exploratory.** The test leaderboard was inspected during diagnosis.
2. Two origins; neither candidate confirmed on a fresh one.
3. The candidate reuses the same saved predictions, so it inherits every upstream limitation.
4. Coverage is measured only on objects with a known five-year outcome.
5. Interval bounds for the blends are combined from the members' conformalised bounds, which
   is not the same as conformalising the blend itself — a cleaner construction would
   recalibrate the blend directly (not run).
6. Origin 2011's tune/calibration sets (248 / 332) are small enough that *any* conclusion
   there is weakly powered.

## Recommended next steps

1. **G5 rolling-origin validation** — the only way to confirm or refute either candidate. This
   is the single highest-value remaining lifetime experiment and it requires refits.
2. **Enlarge the selection and calibration sets**, or select on a forward-in-time slice rather
   than a family split within the development period. This addresses the root cause rather
   than its symptoms, and is a protocol change requiring approval.
3. **Conformalise the blend directly** rather than combining member bounds.
