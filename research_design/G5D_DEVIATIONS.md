# G5d deviation log

This file records deviations from `G5D_PREREGISTRATION.md`. **The pre-registration itself is
never edited** — it is hashed in `outputs/g5d_origin2006/prereg_freeze.json` and a guard test
(`tests/test_final_evaluation_guards.py::test_preregistration_freeze_still_matches_the_protocol`)
fails if it changes. Deviations are logged here instead.

| # | Date (UTC) | Deviation | Cause | Effect on the pre-registered hypotheses | Outcomes seen first? |
|---|---|---|---|---|---|
| 1 | 2026-11-04 | **The pre-registered 7-learner arm set could not be fitted.** The run crashed during tuning on `lightgbm`. Audit of the environment found **4 of 7 learners unavailable**: `lightgbm`, `catboost`, `tabicl`, `kumo`. | None of the four is declared in `requirements-ai.txt`. `kumo` additionally requires NVIDIA `structured-data-models` with **OpenMDW-1.1 licensed weights** and ~24 GB of GPU memory for context encoding; `tabicl` is also a weights-based foundation model. These are licensed-artifact downloads, not routine installs. | **H1 (selection transfer) is weakened**: a Spearman correlation over 3 learners is very weakly powered and is reported as such. **H2 (ranking instability) remains testable** on a consistent arm set. **H3 (mechanism) remains testable**, since it is computed per model over whatever arms exist. | **No** — the failure occurred before any origin-2006 outcome was scored. |
| 2 | 2026-11-04 | **Reduced arm set adopted:** `physics_only`, `xgboost`, `mlp`, `tabm`. | The three learners that import successfully, plus the physics expert, which needs no learner. | These four arms exist in the **published caches at origins 2011 and 2016 as well**, so the cross-origin comparison uses an *identical* arm set at all three origins — removing rather than adding a confound relative to the published comparison, where the selected learner differed by origin. | No. |
| 3 | 2026-11-04 | **Fusion arms at origin 2006 are not compared across origins.** | `cosmos_gated`, `cosmos_gated_tuneA`, `stack_constant` and `equal_average` are built from the available candidate pool. At origin 2006 that pool is `(tabm)` only, versus `(tabm, tabicl, kumo)` at the published origins. The fusion arms are therefore **not the same estimator** and are not comparable. | Fusion arms are reported for origin 2006 in isolation and excluded from cross-origin ranking claims. | No. |
| 4 | 2026-11-04 | `MO.RECENT` intersects the available learners as `(tabm)` only, so the selected learner at origin 2006 is necessarily `tabm`, and the feature-group ablations are `tabm_*`. | Same dependency cause. | Convenient for comparison with origin 2016, whose selected learner was also `tabm`. Noted, not engineered. | No. |

## Consequence for the outcome classification

Under the pre-registered classification, the originally specified experiment (7 learners) is
**NOT_EVALUABLE** in this environment. The reduced variant is executed and reported as a
**documented deviation**, with H1 explicitly down-weighted for low power.

The dependency gap is itself a **reproducibility finding** and is carried into the final
reproducibility report: the published origin-2011 and origin-2016 results depend on learners
(`kumo` selected at 2011, `tabicl` best on test at 2016) that **cannot be reinstalled from the
declared requirements**, and one of which requires licensed weights and specific hardware.
