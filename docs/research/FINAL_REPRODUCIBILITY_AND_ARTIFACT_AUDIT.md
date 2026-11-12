# Final reproducibility and artifact audit

Date: 2026-11-04 · revision `78ee339`
Evidence: `outputs/final_repro_phase_p/final_reproducibility.json`,
`outputs/final_audit/final_system_audit.json`
Harnesses: `scripts/final_reproducibility_audit.py`, `scripts/final_system_audit.py`

**Verdict: PARTIAL. Prediction-level reproducibility is complete and verified.
Training-level reproducibility is not achievable, and the reason is worse than the project's
own documents have been saying.**

---

## 1. The two levels, kept separate

The manuscript must never use the unqualified word "reproducible". Two distinct properties hold
to very different degrees:

| | What it means | Status |
|---|---|---|
| **Prediction-level** | Every published number can be recomputed from archived per-object predictions | **COMPLETE, verified** — max deviation **0.000e+00** across both origins and every arm |
| **Training-level** | The models themselves can be refitted from the declared environment | **NOT ACHIEVABLE** — see §3 |

Prediction-level reproducibility is not a weak property. It means an independent party can
re-score every arm under a different metric, re-run the cluster bootstrap, re-derive every rank,
recompute coverage, and challenge any analysis decision — all of it, exactly. What they cannot do
is retrain.

## 2. Integrity: all intact

| Item | State |
|---|---|
| Pre-registration freeze (28 files) | **INTACT** — 0 changed, 0 missing |
| Dated 2026-10-27 forecast digest | **INTACT** — every hashed file matches |
| G5d pre-registration | **INTACT** — `9ea4bf4171cad1b8…`, unchanged since it was hashed before any fit |
| Manuscript source artifacts | **10 / 10 present**, each digested |

## 3. Training-level reproducibility — the real finding

The project's existing documents say "2 of 7 learners are reinstallable", which is true but
frames this as a dependency gap. Phase N/P checks show the problem is upstream of that.

### 3.1 Current state: 2 of 7 backends importable

| Learner | Backend | Importable | Declared in any requirements file | Published role |
|---|---|---|---|---|
| `xgboost` | `xgboost` 3.4.1 | yes | yes | reference baseline, both origins |
| `mlp` | `torch` 2.14.0+xpu | yes | yes | reference baseline; E12's common learner |
| `lightgbm` | `lightgbm` | **no** | **no** | reference baseline, both origins |
| `catboost` | `catboost` | **no** | **no** | reference baseline, both origins |
| `tabm` | `tabm` | **no** | **no** | **SELECTED learner at origin 2016** |
| `tabicl` | `tabicl` | **no** | **no** | best test performer at origin 2016; RECENT pool |
| `kumo` | `sdm` | **no** | **no** | **SELECTED learner at origin 2011** |

### 3.2 The cause is not package unavailability

All five missing backends are **currently published on PyPI**: `lightgbm` 4.7.0, `catboost`
1.2.10, `tabm` 0.0.3, `tabicl` 2.2.0, `sdm` 1.6.0. Nothing has been yanked or withdrawn.

**None of the five is declared in any requirements file.** `requirements-ai.txt` declares
`torch`, `scikit-learn` and `xgboost` and stops there. So the declared environment was never
capable of refitting five of the seven published arms — this is a gap in the declaration, not a
loss of availability.

### 3.3 No software environment was recorded for any published benchmark run

This is the finding that matters most, and it is new.

- The published `summary.json` for each origin records `origin`, `population`, `snapshot`,
  `dates`, `sizes`, `tuneA_pinball`, `gates`, `fits` and timings. It records **no package
  versions, no Python version and no git revision.**
- The one environment snapshot that exists, `outputs/baseline/venv_freeze_2026-10-24.txt`
  (303 packages), contains `lightgbm==4.7.0`, `torch==2.13.0+xpu` and `xgboost==3.4.1` — and
  **does not contain `catboost`, `tabm`, `tabicl` or `sdm` at all**. It therefore cannot be the
  environment in which those four arms were fitted.
- `cosmos/ai/provenance.py` provides `run_metadata()` and `tracked_run()` for exactly this
  purpose. **Neither is called anywhere in the codebase.** The capability was built and never
  wired in.
- Separately, the environment has **drifted since the freeze**: `lightgbm` was present at
  2026-10-24 and is not importable now.

**Consequence**: even if all five backends were installed today at their current PyPI versions,
that would not reconstruct the environment that produced the published numbers — because that
environment was never written down. Installing current versions would produce *a* refit, not
*the* refit, and any discrepancy would be uninterpretable.

This is precisely why the user's instruction not to install arbitrary newer versions to force
compatibility is the correct call, and it is now a documented reason rather than a preference.

### 3.4 What *is* recorded, and what that buys

Not everything is lost. Per learner, `summary.json["fits"][learner]` records the **tuned
hyperparameters** (e.g. for `xgboost` at origin 2016: `max_depth` 4, `learning_rate` 0.0801,
`subsample` 0.7884, `colsample_bytree` 0.6016, `min_child_weight` 6.211, `reg_lambda` 0.2410),
plus `n_features` (53), `tuned`, and per-seed fit timings. Seeds are the fixed module constants
`SEEDS = (0, 1, 2, 3, 4)` with `seed=0` used for tuning, and the fit cache is keyed by an MD5
fingerprint over `(CACHE_VERSION, name, groups, seeds, n_trials, fixed_params)`.

So the **experimental configuration is fully recorded**; only the **software environment** is
not. An independent party who installs a backend can refit with the exact recorded
hyperparameters and seeds — they just cannot guarantee the same backend build.

## 4. Artifact inventory

877 files, 174.5 MB across 18 output trees.

| Files | Size | Tree | Role |
|---|---|---|---|
| 483 | 75.2 MB | `outputs/benchmarks` | published benchmark results — the manuscript's primary evidence |
| 13 | 85.1 MB | `outputs/twin` | dated, hash-verified 2026-10-27 forecast (registered, not yet scored) |
| 309 | 2.0 MB | `outputs/pipeline` | end-to-end pipeline run records |
| 19 | 10.8 MB | `outputs/g5d_origin2006` | confirmatory experiment: refit, analysis, pre-registration freeze |
| 21 | 0.4 MB | `outputs/product` | Mission Intelligence Console artifacts |
| 5 | 0.5 MB | `outputs/g5_figures` | the five G5 figures, all postdating their source JSONs |
| 5 | 0.1 MB | `outputs/g5_rolling` | 11 launch-epoch evaluation slices |
| 3 each | <0.1 MB | `outputs/phase_e`, `phase_g_lifetime`, `phase_h` | ablation, selection-transfer and uncertainty results |
| 2 each | <0.1 MB | `g5_censoring`, `phase_g_multihorizon`, `e12_same_learner`, `dashboard`, `final_audit` | supporting analyses |
| 1 each | — | `final_literature`, `final_repro_phase_p`, `audit` | this phase's own records |

The two large trees are both LFS-tracked. The published predictions were committed in
`3ff35f4` ("Upload complete COSMOS-AI project and datasets using Git LFS").

## 5. Claim-to-artifact traceability

Every headline claim resolves to a named artifact, and each was re-derived from it in Phase N:

| Claim | Artifact | Re-derived |
|---|---|---|
| Published pinball leaderboards | `origin{2011,2016}_uncontrolled/test_predictions.npz` + `regression_test.csv` | exactly (0.000e+00) |
| `physics_only` 1st of 19 at 2011; 19th of 19 at 2016 | same | yes |
| Selection non-transfer, ρ = 0.000 at both origins | `phase_g_lifetime/phase_g_lifetime_results.json` | yes |
| 23.64 % of slice pairs inverted | `g5_rolling/g5_rolling_results.json` | yes |
| Loss concentrates 4.13×–6.60× below the cap | `g5_censoring/g5_causal_results.json` | yes |
| G5d INCONCLUSIVE; H2 SUPPORTED; H3 UNDERPOWERED | `g5d_origin2006/analysis/g5d_analysis.json` | yes |
| `physics_only` 1st/4th/1st on the common arm set | same | yes |
| T1 prospective, 30 d: Brier 0.00127, ECE 0.00130, AUC-ROC 0.982 | `benchmarks/twin_prospective_t1/t1_summary.json` | read directly |
| 2026-10-27 forecast, registered and unscored | `outputs/twin/as_of_2026-10-27/` + `FORECAST_SHA256.txt` | digest verified |

No headline number in the manuscript lacks a named, digested source.

## 6. Required manuscript language

The reproducibility statement must assert exactly this and no more:

> All published quantitative results are reproducible at the prediction level: per-object
> quantile predictions for every model arm and both temporal origins are archived, and every
> reported score, rank, bootstrap interval and coverage figure was recomputed from those
> archives to exact agreement. The benchmark is **not** reproducible at the training level. Five
> of the seven learners' backends — including the learner selected at each origin — are not
> declared in the project's requirements files, and no software environment was recorded for any
> published benchmark run, so the exact fitting environment cannot be reconstructed. Tuned
> hyperparameters and random seeds **are** recorded per learner, so an independent party can
> refit under a documented configuration, but not under the original software build.

What the statement must **not** say: that the project is "fully reproducible", that the
environment is "captured in requirements-ai.txt", or that installing current backend versions
would reproduce the published models.

## 7. Isolated, forward-only corrections proposed

None of these can retroactively fix a frozen artifact. They prevent recurrence and are offered
for approval, not applied to published outputs:

1. **Wire `provenance.run_metadata()` into run entry points** so every future run records git
   revision, Python version and the installed versions of the packages it imports. The function
   already exists and is tested; it is simply not called.
2. **Declare the five missing backends in `requirements-ai.txt`**, pinned to the versions
   currently on PyPI, with a comment stating these are *forward* pins and are **not** the
   versions that produced the published results. This makes future runs declarable without
   making a false claim about the past.
3. **Add a `scripts/` environment-capture step** writing a `pip freeze` next to each run's
   output directory.

Items 1–3 change no published artifact and no scientific conclusion. They are listed in
`FINAL_BLOCKERS_AND_REMAINING_WORK.md` as post-submission engineering work.

## 8. What this audit does not establish

- **Digest verification proves files are unchanged, not correct.** Every hash in §2 confirms
  nobody edited the artifact. None of it speaks to whether the underlying analysis was sound.
- **Exact prediction-level reproduction is arithmetic fidelity, not validity.** The manuscript's
  numbers match the archives. Whether the estimand, the 1826.25-day cap, the cohort construction
  or the launch-family clustering are the right choices is argued in the methodology documents
  and is not settled here.
- **The absence of a recorded environment is not evidence that results are wrong.** It is
  evidence that one specific verification route — independent refitting — is closed. The other
  route, independent re-scoring and re-analysis, is fully open and was exercised.
- **Nothing here is a positive scientific result.** The project's conclusions remain negative or
  inconclusive, and a clean artifact audit does not change that.
