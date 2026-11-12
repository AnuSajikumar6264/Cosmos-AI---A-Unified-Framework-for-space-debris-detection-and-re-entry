# Final claims and evidence matrix

Date: 2026-11-04 · revision `78ee339`

One row per claim the manuscript makes. Each row names the exact value, the artifact it is read
from, whether it was mechanically re-derived, and the evidence tier that governs the verb the
manuscript may use.

Re-derivation harness: `scripts/final_system_audit.py` → `outputs/final_audit/`.

---

## Legend

**Tier** — CONF confirmatory (pre-registered, never-scored fold) · MEAS measured (archived
predictions, forward folds, not pre-registered) · EXPL exploratory (test leaderboard inspected
first) · NEG negative · PEND pending evidence.

**Re-derived** — ✔ recomputed from the artifact by the audit harness and matched · ○ read
directly from a result file without independent recomputation.

---

## 1. Central claims

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 1 | Selection and forward-test rankings are rank-independent at origin 2011 | Spearman **0.000** | `phase_g_lifetime/phase_g_lifetime_results.json` | ✔ | MEAS |
| 2 | Same at origin 2016 | Spearman **0.000** | same | ✔ | MEAS |
| 3 | `physics_only` wins the forward test fold at origin 2011 | rank **1 of 19** (1 of 17 point-forecast arms) | `origin2011_uncontrolled/regression_test.csv` | ✔ | MEAS |
| 4 | `physics_only` ranks last at origin 2016 | rank **19 of 19** (17 of 17) | `origin2016_uncontrolled/regression_test.csv` | ✔ | MEAS |
| 5 | Model ordering inverts across evaluation slices | **23.64 %** of slice pairs have negative rank correlation, 11 slices | `g5_rolling/g5_rolling_results.json` | ✔ | MEAS |
| 6 | Published leaderboard is exactly recomputable from archived predictions | max absolute deviation **0.000e+00**, both origins, every arm | `test_predictions.npz` + `regression_test.csv` | ✔ | MEAS |

## 2. Confirmatory experiment (origin 2006)

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 7 | Pre-registration unchanged since before any fit | SHA-256 `9ea4bf4171cad1b8…` intact | `outputs/g5d_origin2006/prereg_freeze.json` | ✔ | — |
| 8 | Model ranking is unstable across temporal origins | **H2 SUPPORTED** — no arm present at all three origins holds its rank | `g5d_origin2006/analysis/g5d_analysis.json` | ✔ | **CONF** |
| 9 | Rank pattern of the physics baseline on the common arm set | **1st / 4th / 1st** at 2011 / 2016 / 2006 (rank range 3) | same | ✔ | **CONF** |
| 10 | Selection transfer at origin 2006 | **H1 NOT EVALUABLE** — only 2 learners carried a tune-A score | same | ✔ | NEG |
| 11 | Point-mass composition shift explains ranking instability | **H3 UNDERPOWERED** — 3 arms against a pre-registered floor of 5 | same | ✔ | NEG |
| 12 | Overall pre-registered outcome | **INCONCLUSIVE** | same | ✔ | — |
| 13 | Arms fitted versus pre-registered | **4 of 7**; deviation logged, protocol unedited | `g5d_run_manifest.json`, `G5D_DEVIATIONS.md` | ○ | — |

## 3. Reproducibility

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 14 | Learner backends refittable in the declared environment | **2 of 7** (`xgboost` 3.4.1, `torch` 2.14.0+xpu) | `final_repro_phase_p/final_reproducibility.json` | ✔ | MEAS |
| 15 | The unavailable five include the learner selected at each origin | `kumo` (2011), `tabm` (2016); also `tabicl`, best test performer at 2016 | same + `summary.json` `best_learner_on_tuneA` | ✔ | MEAS |
| 16 | The cause is not package unavailability | all five backends currently published on the package index | package-index query, this session | ✔ | MEAS |
| 17 | None of the five is declared in any requirements file | 0 of 5 declared | `requirements*.txt` | ✔ | MEAS |
| 18 | No software environment was recorded for any published run | published `summary.json` carries no package, interpreter or revision field | `summary.json` per origin | ✔ | MEAS |
| 19 | The one environment snapshot cannot be the fitting environment | contains `lightgbm`, `torch`, `xgboost`; lacks `catboost`, `tabm`, `tabicl`, `sdm` | `outputs/baseline/venv_freeze_2026-10-24.txt` | ✔ | MEAS |
| 20 | Provenance tooling exists and is never invoked | `run_metadata()` / `tracked_run()` defined, zero call sites | `cosmos/ai/provenance.py` + repository search | ✔ | MEAS |
| 21 | Experimental configuration *is* recorded | tuned hyperparameters per learner, 53 features, seeds (0,1,2,3,4), seed 0 for tuning | `summary.json` `fits`; `lifetime/run.py` `SEEDS` | ✔ | MEAS |
| 22 | Archived predictions present for every published origin | **2 / 2** | `test_predictions.npz` | ✔ | MEAS |

## 4. Structural integrity and leakage controls

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 23 | Telemetry pre-registration freeze intact | 28 files, **0 changed, 0 missing** | `research_design/preregistration/freeze.json` | ✔ | — |
| 24 | Dated forecast digest intact | every hashed file matches | `outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt` | ✔ | — |
| 25 | Temporal ordering holds at all three origins | train < train_end ≤ tune < tune_end; origin ≤ test < test_end | cohort + `ORIGINS` | ✔ | — |
| 26 | Launch families do not straddle the calibration split | **0** overlapping families at every origin | cohort splits | ✔ | — |
| 27 | Test folds are pairwise disjoint by object | **0** shared objects in all three pairs | cohort splits | ✔ | — |
| 28 | Mean-elicited endpoint never drives selection, ranking or a headline | no occurrence in any analysis script | `scripts/*.py` | ✔ | — |
| 29 | Published artifacts retain their original columns | preserved; `rmse_log10` deliberately not deleted | `regression_test.csv` | ✔ | — |
| 30 | Manuscript source artifacts present and digested | **10 / 10** | `final_reproducibility.json` | ✔ | — |

## 5. Negative results

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 31 | Cross-domain integration provides measurable predictive value | **NOT DEMONSTRATED** | `phase_e/phase_e_results.json` | ○ | **NEG** |
| 32 | C1 (launch-family → lifetime) | PARTIALLY SUPPORTED — improves at one origin only; learner confounded with origin | same | ○ | NEG |
| 33 | C1 feature effects reverse sign across origins | `no_physics`: **+0.00225** at 2011 (helps), **−0.00496** at 2016 (hurts, significant after BH) | same | ○ | NEG |
| 34 | C2 (survival → debris cloud), calibration-controlled | learned arm better by **0.0503** mean absolute fraction error, 95 % CI [0.0189, 0.0805], p = 0.002, 32 clouds / 160 cloud-years | `twin_couplings/c2_cloud_survival.csv` | ○ | MEAS |
| 35 | C3 (status → re-entry probability) | INCONCLUSIVE | `twin_couplings/c3_summary.json` | ○ | NEG |
| 36 | C4 (health → conjunction) | **NOT EVALUABLE** — **0 joinable pairs** across the three candidate corpora | `phase_e_results.json` | ○ | NEG |
| 37 | The deployed fusion is the best combiner | **No** — `cosmos_gated` best in **0 of 11** slices, mean rank 5.73, range 2–9 | `g5_rolling_results.json` | ○ | NEG |
| 38 | A parameter-free blend beats the deployed fusion at origin 2016 | **19.4 %** (0.060376 → 0.048644) | `regression_test.csv` + `phase_g_lifetime_results.json` | ✔ | EXPL |
| 39 | Both blend candidates were promoted | **No — DO NOT PROMOTE** on both; fail the joint accuracy-and-coverage criterion (median blend over-covers at 80 % in 7 of 11 slices) | `phase_g_lifetime_results.json`, `g5_rolling_results.json` | ○ | — |

## 6. Narrow measurements

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 40 | Loss concentrates below the censoring cap | **4.13×** (2011), **6.60×** (2016) | `g5_censoring/g5_causal_results.json` | ✔ | MEAS |
| 41 | The earlier censoring attribution was wrong | resolved-outcome fraction ≈ **1.000** in every split; the real difference is the at-cap point mass | same | ✔ | — |

## 7. Prospective evidence

| # | Claim | Value | Artifact | Re-derived | Tier |
|---|---|---|---|---|---|
| 42 | Prospective test at the 2026-08-16 origin, 30-day horizon, `physics_history` | 13,186 objects; **29 events vs 43.75 expected**; Brier **0.00127**; ECE **0.00130**; AUC-ROC **0.982**; AUC-PR **0.714** | `twin_prospective_t1/t1_summary.json` | ○ | MEAS |
| 43 | The prior-based arm over-forecasts | 118.0 expected against 29 observed | same | ○ | MEAS |
| 44 | The registered 2026-10-27 forecast is scored | **No** — `[PENDING EVIDENCE]`. Latest outcome coverage 2026-10-26; **−1 outcome days**; 30-day horizon needs a snapshot ≥ **2026-11-26** | `scripts/check_t1_later_snapshot.py` | ✔ | **PEND** |

## 8. Exploratory — must never be stated as findings

| # | Observation | Artifact | Tier |
|---|---|---|---|
| 45 | A gradient-boosted arm ranks last on tune-A and first on test at all three origins | `phase_g_lifetime_results.json`, `g5d_analysis.json` | **EXPL** |
| 46 | Neural arms degrade 1.75×–2.10× between origins vs 0.97×–1.63× for the gradient-boosted arm | same | **EXPL** |
| 47 | Interval coverage degrades with distance from the forecast origin | `phase_h/phase_h_results.json`, `g5_rolling_results.json` | **EXPL** — an instance of a published bound (preprint), not an independent finding |
| 48 | Per-horizon independent isotonic calibration harms coherence and Brier | `phase_g_multihorizon/multihorizon_results.json` | **EXPL** — design diagnostic |

## 9. Literature claims

| # | Claim | Value | Artifact | Tier |
|---|---|---|---|---|
| 49 | Every manuscript reference resolves against a live index | **41 candidates: 37 verified, 3 ambiguous, 1 harness artifact** | `outputs/final_literature/reference_verification.json` | MEAS |
| 50 | Attribution errors found and corrected | **7** (Clark & McCracken year; Bailey→Inoue/Jin/Rossi; LiveHouse-TS authors; Taggart year; Siew authorship; Massimi year; citation counts) | `FINAL_REFERENCE_VERIFICATION_MATRIX.md` | MEAS |
| 51 | Cited works that do not exist, removed | **2** (claimed ACM CSUR selective-prediction survey; SpotGEO challenge paper) | same | MEAS |
| 52 | Non-peer-reviewed references identified and labelled | **12** preprints or deposits; 4 hold load-bearing roles | same | MEAS |
| 53 | Conformal prediction in space — strict search | **1** genuine instance of 3,010 records examined; **0** for conjunction assessment | `LITERATURE_COMPARISON_MATRIX.md` | MEAS |

## 10. Claims that must carry a stated convention

| Value | Convention |
|---|---|
| "1st of 17 / 17th of 17" | **point-forecast arms.** Over all 19 published rows (including two `marginal_conformal` interval variants): 1st of 19 / 19th of 19. Both correct; pick one and state it |
| "1st / 4th / 1st" | the **common 4-arm set** fittable at all three origins — a different, smaller set than the 17 |
| 23.64 % | fraction of **slice pairs**, over 11 slices. Not of arms, not of objects |
| 4.13× / 6.60× | ratio of **mean per-object pinball** below the cap to at the cap, per origin |
| 19.4 % | relative pinball reduction at **origin 2016 only**. Not an average over origins |

## 11. Audit outcome

28 mechanical checks: **26 PASS, 2 FAIL, 0 NOT_EVALUABLE. 0 critical failures.**

The two failures are the known, reported limitations — training-level reproducibility (rows
14–20) and one stale living-document figure, since corrected. Neither is a claim defect.

**No claim in this matrix is stated above its tier, and no claim lacks a named artifact.**
