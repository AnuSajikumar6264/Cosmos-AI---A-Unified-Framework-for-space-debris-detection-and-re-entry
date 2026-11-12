# Phase 8 gate — addendum of 2026-11-08 (versioned; the original gate record is unchanged)

The accepted gate record is `docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md`
(sha256 `86ae2e8c828e3e18…`) with its machine record `outputs/audit/phase8_acceptance_gate.json`
(sha256 `83b1150215020e0e…`), evaluated 2026-11-06. Neither file is modified by this addendum; both
hashes are re-verified in `outputs/audit/protected_artifacts_before_x4_x6_x10_*.json`.

## 1. Acceptance

The user accepted Phase 8 as **PASS WITH LIMITATIONS** on 2026-11-08 and authorised exactly three
analyses — X4 (3b Stage 2), X6 Stage 1 (archive-only), X10 (E6, archive-only) — while prohibiting X3,
X6 Stage 2, X13 and full twin-state regeneration. Phase 9 remains locked; no manuscript or thesis
file was touched.

## 2. Corrections to the gate's cost table

| Item | Gate record said | Corrected | Why |
|---|---|---|---|
| X3 — 3b Stage 1 | "minutes CPU", re-selection only, no refit | **~30 min CPU**, and *not* refit-free | The AR(8) residual-score caches (`outputs/benchmarks/telemetry_esa_adb/oof/*/scores_*.npy`, the A0 run's `scores_cal.npy`/`scores_test.npy`) were lost to the `*.npy` ignore rule, the same mechanism that lost the OPS-SAT per-seed scores. Any re-selection must first recompute them (≈ 380 s for the M1 target OOF scores). Separately, the validity check X3 was to deliver already exists: post-hoc P1 reproduced A0 = 0.07435 and A1 = 0.42781 exactly and found the grid immaterial on both paths. |
| X10 — E6 branch ablation | "hours of training, 5 seeds × branches" | **minutes of CPU, no training** | The single-branch arms are the existing `cnn` and `fcnn` models; both have five regenerated seeds per protocol with per-seed scores, Brier and ECE already archived (`telemetry_opssat_regen_20261106/`). Only the statistics were missing. |
| X6 — am_design Stage 2 | "per protocol doc" | **BLOCKED as specified** | The protocol holds the selected learners fixed (`kumo` at 2011, `tabm` at 2016); neither backend is importable (nor `tabicl`, `lightgbm`, `catboost`). The protocol's own substitute (one available learner) costs 2–6 GPU-h. Stage 1 is free and was run. |
| Twin-state regeneration | "~1,250 s" | **BLOCKED — EXTERNAL DEPENDENCY** | `engine.run` → `study_learner()` → `tabm`, not importable. A no-refit re-emission of `twins.jsonl` from the archived table (seconds) is the only feasible form; it was not authorised and not run. |

## 3. Environment fact found during execution

`statsmodels` is not installed in this environment, so the archived odds-ratio estimator
(`cosmos/ai/lifetime/leak_check.py::adjusted_or`) cannot run. For X6 Stage 1 the identical model
(same design matrix, Newton MLE, cluster-robust sandwich with statsmodels' default correction) was
re-implemented in `scripts/cluster_logit.py` and **validated against the archived `leak_check.json`
values before use** (design-missing odds ratios and intervals reproduced to 1e-13 at both origins).
No package was installed; the environment lock of 2026-11-06 still describes the environment.

## 4. Execution record

See §5 of this addendum for X4 (appended when the run completed), and the completion tracker rows
marked "executed 2026-11-08" for X6 Stage 1 and X10. Pre- and post-execution hash records:
`outputs/audit/protected_artifacts_before_x4_x6_x10_*.json`, `outputs/audit/protected_artifacts_after_x4_x6_x10_*.json`.

## 5. X4 execution record (appended 2026-11-08 after completion)

| Item | Record |
|---|---|
| Command | `POSTHOC_TMP=/data2/anupa/tmp_posthoc python scripts/track3b_stage2_cells.py` (background; log `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/run.log`) |
| Runtime | 2,471 s total: OOF regeneration 353 s; S0/Sh/S1 score levels 123 s; seven cells 234–373 s each |
| Code | frozen `oof.py` (`ar8_oof`, K = 5, purge 1 day, seed 0), frozen `forecasting.py` (`forecast_record`, `residual_scale`, `nonconformity`), P1 cell runner `scripts/posthoc_v2/p1_decompose.py` (sha256 `4093fb2ef462f064…`, unchanged) imported unmodified; bootstrap `exact_metric.compare`, B = 2,000, seed 20261024 as in P1 |
| Redirections | `oof.oof_dir` and `p1_decompose.out_path` re-pointed at runtime to `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/` so no historical file was rewritten; the historical `oof/m1_target_ar8/folds.json` and the P1 records are byte-identical before and after (hash records above) |
| Regeneration check | regenerated OOF scores reproduce the archived `sha256_sample` `02455519984c` exactly; folds and channel list identical |
| Validity gate | c0 = A0 = 0.07435099036517134; c5 = A1 = 0.4278060106400274; c2, c3, c4 identical to the archived P1 cells (value, level, k) |
| Freeze | both ESA-ADB freezes verified before and after the run (28/28; 27/28 with the expected pre-registration-document difference) |
| Exposure | seven further scorings of the pre-registered M1 test half; exploratory; no operating point selected on test data |
| Blockers (not improvised) | (i) F1 fit-data factor at the P_half level is undefined — A0's fit-period model has no out-of-fold scores over the training half; (ii) the (P_cal, D_half) combination is defined neither in POSTHOC_PLAN_V2 P1 nor in the 3b proposal. The 2³ main effects of proposal §6 are therefore **not estimated**; the seven cells give conditional one-factor contrasts inside the defined cell space |
| Output | `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/m1_target_conformal_bh.json` (+ `cells_partial.json`, `alarms/`, `oof_regen/`); test `tests/test_track3b_stage2.py` |
