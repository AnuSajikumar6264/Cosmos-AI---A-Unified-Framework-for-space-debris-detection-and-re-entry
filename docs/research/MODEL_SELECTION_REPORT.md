# Model selection report and experiment registry

Date: 2026-11-04. Decision: **no candidate promoted.** The incumbent configuration is retained.

## Pre-specified acceptance criteria

Fixed before any candidate was scored on test:

1. Significant pinball improvement (BH-corrected, launch-family cluster bootstrap) against the
   incumbent at **both** temporal origins.
2. No significant degradation against any incumbent at either origin.
3. No loss of interval coverage relative to the incumbent.
4. A single favourable origin is **not** sufficient.
5. Nominal coverage obtained by inflating interval width does not count.

## Experiment registry

| Field | `robust_median_blend` | `robust_mean_blend` | `coherent_raw` reading |
|---|---|---|---|
| Model id | G1-median | G1-mean | G2-coherent |
| Type | parameter-free quantile median over a fixed set | parameter-free quantile mean | existing column, read off the monotone quantile function |
| Members / source | `physics_only`, `tabm`, `tabicl`, `kumo` | same | `p_lifetime_raw_*` |
| Data version | `test_predictions.npz`, origin 2011 & 2016 | same | `t1_objects.csv.gz` |
| Git commit | `78ee339` (worktree modified) | same | same |
| Hyperparameters | **none** | **none** | none |
| Seeds | inherits the study's 5-seed ensembles | same | n/a |
| Script | `scripts/phase_g_lifetime_optimization.py` | same | `scripts/phase_g_multihorizon_coherence.py` |
| Output | `outputs/phase_g_lifetime/` | same | `outputs/phase_g_multihorizon/` |
| Bootstrap | 4000 draws, seed 20261027, cluster = launch family | same | cluster = launch |
| Pinball 2016 | **0.048644** (best of 9) | 0.051921 | n/a |
| Pinball 2011 | 0.057549 (3rd of 9) | 0.064271 (7th) | n/a |
| vs `cosmos_gated` 2016 | **−19.4 %**, p_adj < 0.0001 | **−14.0 %**, p_adj < 0.0001 | n/a |
| vs `cosmos_gated` 2011 | −1.2 %, p_adj 0.65 (n.s.) | +10.3 %, p_adj 0.46 (n.s.) | n/a |
| Coverage cells at nominal | 0 / 4 | **4 / 4** | n/a |
| Brier vs incumbent reading | n/a | n/a | **better at both horizons**, p < 0.0001 |
| Coherence | n/a | n/a | **0 violations** vs 54 |
| Runtime | < 5 s (no fitting) | < 5 s | < 5 s |
| Memory | < 1 GB | < 1 GB | < 1 GB |
| **Criterion 1** | **FAIL** (one origin) | **FAIL** (one origin) | n/a (different endpoint) |
| **Criterion 2** | pass | pass | pass |
| **Criterion 3** | fail (0/4 nominal) | pass (4/4) | n/a |
| **Promotion** | **DO NOT PROMOTE** | **DO NOT PROMOTE** | **RECOMMENDED FOR REPORTING** |

## Decisions

### G1 — not promoted

Both blends improve significantly against all three incumbents at origin 2016 and are
inconclusive against every incumbent at origin 2011. Criterion 1 fails. Criterion 4 explicitly
forbids promotion on one favourable origin. **The incumbent `cosmos_gated` is retained.**

Recorded for the record: the deployed expert is beaten by 19.4 % at origin 2016 by a
parameter-free combination, and is outranked by five of its own components there. That is a
real weakness of the incumbent; it is not sufficient to promote a replacement that is
unconfirmed at the second origin.

### G1-mean coverage — noted, not promoted

`robust_mean_blend` attains nominal coverage at **4 of 4** (origin, level) cells — the only
model among five to do so — and does it without systematic width inflation (narrower than the
incumbent at origin 2011). Promoting on this would mean changing the endpoint after seeing the
coverage table, which criterion 1 does not permit. It is logged as the highest-priority
confirmatory candidate instead.

### G2 — recommended for reporting

The coherent reading is coherent by construction (0 vs 54 violations) **and** significantly
better by Brier at both evaluated horizons. It requires no recalibration, no retraining and no
change to any published artifact — it is a choice about which existing column to report.

This does **not** modify L17: the isotonic columns are preserved exactly, and the decision not
to recalibrate them stands.

**Caveat carried with the recommendation:** both readings over-forecast by 8.7×–14.8× on the
T1 window, so no calibrated-probability claim follows from adopting the coherent reading.

## Artifacts preserved

No historical artifact was modified. All new outputs are in new directories
(`outputs/phase_g_lifetime/`, `outputs/phase_g_multihorizon/`). The pre-registration freeze
verifies INTACT and the hashed forecast verifies OK.
