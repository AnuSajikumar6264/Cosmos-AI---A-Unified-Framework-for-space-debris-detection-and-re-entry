# Final reproducibility report (Phase M)

Date: 2026-11-04. **Verdict: PARTIAL.** Integrity is intact and every manuscript source
artifact is present and digested, but **5 of 7 learners cannot be reinstalled from the declared
requirements** — including **both** learners that were *selected* at the two published origins.

> **Correction (2026-11-04).** An earlier draft of this report stated 4 of 7, mapping `tabm`'s
> backend to `torch`. Reading the class bodies in `cosmos/ai/lifetime/models.py` shows
> `TabMQuantile` imports a package named **`tabm`**, and `TabICLQuantile` imports both `tabicl`
> and `sdm.nn.attention`. The corrected count is **2 of 7 reproducible**. The backend map is now
> derived from the source rather than assumed.

```bash
python scripts/final_reproducibility_audit.py     # exit 0
```
Output: `outputs/final_repro/final_reproducibility.json`.

## 1. The headline defect

| Learner | Backend | Importable | Declared in requirements | Published role |
|---|---|---|---|---|
| xgboost | `xgboost` 3.4.1 | yes | yes | reference baseline |
| mlp | `torch` 2.14.0+xpu | yes | yes | baseline; the common learner in E12 |
| **tabm** | **`tabm`** (plus torch) | **NO** | **NO** | **SELECTED at origin 2016**; member of `RECENT` and of the Phase G+ robust blends |
| **lightgbm** | `lightgbm` | **NO** | **NO** | reference baseline, both origins |
| **catboost** | `catboost` | **NO** | **NO** | reference baseline, both origins |
| **tabicl** | `tabicl` | **NO** | **NO** | **best test performer at origin 2016**; member of the pre-specified `RECENT` pool and of the Phase G+ robust blends |
| **kumo** | `sdm` | **NO** | **NO** | **SELECTED learner at origin 2011** — its gated fusion and *all* origin-2011 ablations |

**2 of 7 reproducible** — only `xgboost` and `mlp`. This was discovered when the G5d refit
crashed during tuning on `lightgbm`, and the count was corrected again when a second run crashed
on `tabm`; it had not been detected before because every earlier analysis read **cached
predictions** rather than refitting.

### Why `kumo` in particular cannot simply be installed

`cosmos/ai/lifetime/models.py:KumoQuantile` documents its backend as NVIDIA
`structured-data-models` 0.2.1 with **OpenMDW-1.1 licensed weights**, and notes that a
25k-row context "still exceeds a 24 GB card". So reinstating it requires a licensed
model-weight download *and* specific GPU hardware — not a `pip install`. `tabicl` is likewise
a weights-based tabular foundation model.

### What this does and does not invalidate

| Question | Answer |
|---|---|
| Are the published **numbers** traceable? | **Yes.** Per-object predictions are cached in `test_predictions.npz` and `learner_cache/`, and every reported pinball value was recomputed from them to **0.00e+00** during Phase G+. |
| Can the published **models** be refitted? | **No**, for 4 of 7. |
| Can a **new origin** be run under the published protocol? | **No** — this is exactly why G5d had to deviate, twice, ending at a **2-learner** subset. |
| Does this change any existing conclusion? | **No conclusion changes**, but it bounds them severely: **both** published origins' selected learners (`kumo`@2011, `tabm`@2016) cannot be regenerated here, so neither published leaderboard can be reproduced from source. |

This must be stated in the manuscript's reproducibility statement. "Results are reproducible"
would be false as written; "reported values are recomputable from archived predictions; four
learner backends are not installable from the declared requirements" is accurate.

## 2. Integrity — all INTACT

| Check | State | Detail |
|---|---|---|
| Pre-registration freeze | **INTACT** | all 28 frozen files match |
| Dated 2026-10-27 forecast | **INTACT** | `twins.jsonl` digest verified |
| G5d pre-registration | **INTACT** | `9ea4bf4171cad1b8…` unchanged since it was hashed before fitting |

## 3. Manuscript source artifacts — 10/10 present, digested

| Artifact | SHA-256 (first 12) |
|---|---|
| `origin2011_uncontrolled/test_predictions.npz` | `9c55799bdc03` |
| `origin2016_uncontrolled/test_predictions.npz` | `a2fa43b5dbfb` |
| `origin2011_uncontrolled/regression_test.csv` | `bbd92b656870` |
| `origin2016_uncontrolled/regression_test.csv` | `520d137035f1` |
| `twin/as_of_2026-10-27/forecast_table.csv.gz` | `b15644aab581` |
| `twin_couplings/c2_cloud_survival.csv` | `5b558ba17e4b` |
| `twin_couplings/c3_summary.json` | `d9a0d7301262` |
| `twin_prospective_t1/t1_objects.csv.gz` | `a4573a00004e` |
| `conjunction_kelvins_cac/test_predictions.npz` | `b8e806e41a4f` |
| `telemetry_esa_adb/results.csv` | `1e98567df6a2` |

Full digests in the results JSON. **A digest confirms a file is unchanged, not that it is
correct.**

## 4. Environment

Python 3.12.16, Linux 6.17.0-1010-intel x86_64, glibc 2.41, 512 CPUs.
numpy, pandas, scikit-learn, torch 2.14.0+xpu, xgboost 3.4.1, matplotlib, fastapi 0.162.0,
pydantic 2.14.1. Published GPU results used an Intel XPU device; bit-exact reproduction on
other accelerators is not claimed.

## 5. Evaluation-endpoint correctness (carried from Phase I)

| Endpoint | Used in | Locally elicitable under fixed-horizon right-censoring? |
|---|---|---|
| Pinball loss on quantiles | all Phase E/G+/G5/G5d comparisons | **yes** |
| Interval coverage (quantile endpoints) | Phase H, G5 | **yes** |
| Brier on horizon-event indicators | G2 | **yes** (binary) |
| Expected/observed event counts | G2 | **yes** (binary) |
| **`rmse_log10`** | published `regression_test.csv` only | **NO — mean-elicited** |

`rmse_log10` is **excluded by non-use**, enforced by
`tests/test_final_evaluation_guards.py::test_no_analysis_script_uses_a_mean_elicited_endpoint`.
The published CSV is **not edited** — a second guard asserts the column is still present, so a
historical artifact is preserved rather than rewritten.

## 6. Phase F prospective validation — re-checked, still BLOCKED

| Horizon | Required snapshot data date | Status |
|---|---|---|
| 30 d | ≥ **2026-11-26** | **BLOCKED** |
| 90 d | ≥ 2027-01-25 | BLOCKED |
| 1 yr | ≥ 2027-10-27 | BLOCKED |

Newest outcome coverage on disk ends **2026-10-26**; outcome days available after the forecast:
**−1**. No retrospective substitute was used. The hashed forecast digest re-verified.

## 7. Phase H reproduced

Coverage results re-derived and unchanged: the deployed expert under-covers at 80 % at origin
2016 (0.7169, CI excludes zero) and over-covers at both levels at origin 2011; coverage degrades
near-monotonically with time from origin (rank trend −0.83 to −0.94). Remaining calibration
limitations are unchanged and documented in `PHASE_H_UNCERTAINTY_AUDIT.md` and
`ROLLING_ORIGIN_CALIBRATION_REPORT.md`.

## 8. Required actions before submission

1. **Declare the missing backends** in `requirements-ai.txt` with versions, and record that
   `kumo`/`sdm` needs OpenMDW-1.1 weights and ≈24 GB of GPU memory. This is a documentation
   fix; it does **not** make them installable here.
2. **State the reproducibility boundary honestly** in the manuscript (§1).
3. Keep `rmse_log10` out of every reported table.
4. Re-run this audit immediately before submission and attach its JSON.

## 9. Status

| Gate | Status |
|---|---|
| Integrity preserved | **PASS** |
| Manuscript artifacts present and digested | **PASS** |
| Reported values recomputable from archived predictions | **PASS** |
| Published models refittable from declared requirements | **FAIL** — **2/7**; both selected learners missing |
| Evaluation endpoints correct | **PASS** |
| Mean-elicited endpoint excluded | **PASS** (enforced by test) |
| Prospective validation | **BLOCKED** |
| Overall | **PARTIAL** |
