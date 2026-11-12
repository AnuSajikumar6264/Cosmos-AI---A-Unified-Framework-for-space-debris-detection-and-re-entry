# L17 — methodology decision: do not recalibrate the per-horizon lifetime probabilities

Decision date: 2026-11-04. Decided by: project author (approval recorded in the Phase D
instruction). Option taken: **(a) preserve the existing calibration**.

This is a documented decision **not** to change methodology. It is not authorisation to edit
pre-registration-frozen files, and no frozen file was modified.

## The defect

The saved per-horizon **calibrated** lifetime columns in
`outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` are not a coherent cumulative
distribution: `P(decay <= 30 d)` can exceed `P(decay <= 90 d)`.

| Column family | Objects with values | Cross-horizon violations | Worst drop |
|---|---|---|---|
| `p_lifetime_*` (isotonic-calibrated) | 13,238 | **123 (0.93 %)** | **0.1797** |
| `p_lifetime_raw_*` (uncalibrated) | 13,238 | 0 | none |
| `p_physics_prior_*` | 31,396 | 0 | none |
| `p_physics_history_*` | 13,238 | 0 | none |
| `p_*` (**final reported forecast**) | 31,396 | 0 | none |

Worst observed case: `p_lifetime_30d = 0.7797`, `p_lifetime_90d = 0.6000`,
`p_lifetime_1yr = 0.8571`.

Reproduce with:

```bash
python scripts/audit_horizon_coherence.py --as-of 2026-10-27
# writes outputs/audit/horizon_coherence_2026-10-27.json, including the artifact SHA-256
```

## Cause

`cosmos/ai/twin/engine.py:291`:

```python
T.loc[iu, f"p_lifetime_{k}"] = M["iso"][k].predict(FU.horizon_prob(q1, h))
```

`M["iso"][k]` is a **separate isotonic regressor per horizon `k`**, each fitted against that
horizon's own labels. Isotonic regression is monotone in its input score, but nothing couples
the three fitted maps to each other, so the calibrated triple need not be nondecreasing in
the horizon. The uncalibrated `p_lifetime_raw_*` is read off a single monotone quantile
function (`FU.horizon_prob`) and is therefore coherent by construction.

## Scope: what is and is not affected

The twin's reported forecast selects per regime and **does not use `p_lifetime_*`**:

```python
T[f"p_{k}"] = np.where(unc,  T[f"p_physics_history_{k}"],
               np.where(regime == "operator_controlled", base_rate, T[f"p_physics_prior_{k}"]))
```

- **Not affected**: the headline `p_30d` / `p_90d` / `p_1yr` forecast, the dated twin
  summary, T1's `p_*` column, and the physics variants.
- **Affected**: `p_lifetime_*` where used as a *comparison* column for the learned expert, in
  particular the `reentry-comparison` module output in `engine.run` and the lifetime variant
  rows of the twin forecast comparison.

## Decision and rationale

Option (a) — preserve — was chosen over (b) joint / isotonic-in-horizon recalibration.

1. The headline forecast is unaffected, so the defect does not change any reported re-entry
   probability.
2. Recalibrating would alter values in an already-published artifact and would require
   re-running the dated twin, which conflicts with preserving existing scientific outputs.
3. The affected columns are a secondary comparison, not a load-bearing claim. The honest cost
   of preserving them is a documented limitation, which is cheaper than a methodology change
   and leaves the published record intact.
4. Option (b) remains available later if a manuscript claim about *calibration quality of the
   learned lifetime expert* is made. It would then need a logged deviation and a re-run.

## Required handling, and where it is enforced

| Requirement | Enforcement |
|---|---|
| Do not modify the isotonic calibration in `engine.py` | No change made; `git diff cosmos/ai/twin/engine.py` shows only the pre-existing provenance edits. |
| Do not regenerate or overwrite calibrated artifacts | `scripts/run_pipeline.py` refuses to overwrite a run directory; no twin re-run was executed. |
| Preserve existing `p_lifetime_*` values | Values are read, never written. `scripts/audit_horizon_coherence.py` is read-only. |
| Downstream consumers abstain on non-coherent rows and record why | `cosmos/ai/adapters.py` `lifetime_estimates` abstains, records the reason, and lists the objects in `noncoherent_horizon_probabilities`; written to `lifetime_noncoherent_horizons.csv`. |
| Distinguish comparison columns from the final `p_*` forecast | Stated in this document, in the limitations register (L17), and in the dashboard's "Lifetime prediction coherence" section. |
| Do not claim the horizon-specific calibrated probabilities form a coherent CDF | `LifetimeEstimate` rejects a non-monotone horizon CDF at the contract boundary, so such a row cannot enter a typed result. |

## Tests holding the decision in place

| Test | What it fixes |
|---|---|
| `tests/test_contracts.py::test_lifetime_rejects_a_noncoherent_horizon_cdf` | The exact observed triple (0.7797, 0.600, 0.8571) is rejected by the contract. |
| `tests/test_integration.py::test_noncoherent_calibrated_probabilities_abstain_rather_than_being_repaired` | Flagged rows are genuinely non-monotone, are absent from results, and carry a reason. |
| `tests/test_end_to_end.py::test_lifetime_estimates_are_coherent_cdfs` | No non-coherent row reaches a written output table. |
| `tests/test_artifact_audit.py::test_horizon_audit_detects_a_hand_built_cdf_violation` | The audit detects a violation computed by hand, independent of the code under test. |
| `tests/test_dashboard.py::test_dashboard_shows_abstentions_with_their_recorded_reasons` | L17 and the unaffected final forecast are both shown to a reader. |

## Wording for any future manuscript

Permitted: "the learned lifetime expert's horizon probabilities are calibrated independently
per horizon and are therefore not constrained to be monotone across horizons; 0.93 % of
objects violate monotonicity, and these are excluded from downstream use."

Not permitted: describing `p_lifetime_30d/90d/1yr` as a calibrated re-entry CDF, or reporting
calibration quality from them without stating this defect.

## Status

**NOT VALIDATED** as a coherent CDF, by construction and by decision. The defect is
documented, bounded, measured and enforced downstream. See [limitations
register](limitations_register.md) L17 and the [decision
log](../../research_design/METHODOLOGY_DECISIONS.md).
