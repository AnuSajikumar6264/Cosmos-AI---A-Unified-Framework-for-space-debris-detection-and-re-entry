# X11 — Uncertainty and behaviour under missing or corrupted inputs: scope and blockers

Written 2026-11-06 (Phase 3.4 / 6). This records, module by module, what has been measured, what
can be measured from archived artifacts, and what would require refitting (with cost) or is blocked.
It is a scoping document; a status of IMPLEMENTED or PASS below is backed by the named test or
artifact, nothing else.

## Fact that frames everything

The deployed twin does **not** run any learned model at prediction time. Every adapter in
`cosmos/ai/adapters.py` reads an archived prediction table (`outputs/twin/as_of_<date>/forecast_table.csv.gz`,
`outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz`, `telemetry_esa_adb/results.csv`,
`vision_spotgeo/*_test_submission.json`) and wraps it in contracts. **No fitted lifetime, conjunction
or health model is persisted anywhere in the repository** (no `.pkl`/`.joblib`/`.pt` outside the
training experiment directories, verified 2026-11-06). Consequently "corrupt the input and watch the
uncertainty respond" is possible only (a) at the twin level — missing or malformed *artifacts* — and
(b) for modules whose model is re-runnable from code without training: the physics expert.

## Per module

| Module | Perturbation study | Status | Evidence / blocker |
|---|---|---|---|
| Twin orchestration | missing artifact, unavailable snapshot, partial module selection | **PASS** | `test_integration.py::test_partial_selection_runs_without_imagery_or_telemetry`, `::test_unavailable_snapshot_fails_without_writing_predictions`; full run 2026-11-06: 18,281 lifetime abstentions with reasons recorded (`outputs/phase3_uncertainty/pipeline_full/run_manifest.json`) |
| Twin outputs under *real* missingness | which objects carry which uncertainty kind; mass unknown for 75 % of uncontrolled objects | **PASS (measured)** | `scripts/twin_uncertainty_audit.py` → `outputs/phase3_uncertainty/twin_uncertainty_audit.json` |
| OPS-SAT telemetry (5 learned models) | additive Gaussian noise σ = k·std, sample dropout 0.1/0.3/0.5, no retraining | **PASS** | `telemetry/robustness.py`, `robustness_summary.csv` (archived) |
| ESA-ADB telemetry | same perturbations on the test half | **BLOCKED — needs approval (X13)** | would re-score the pre-registered test half; exploratory protocol must be declared first |
| Physics re-entry expert | F10.7 / Ap sweep (X8); monotone invariants under perigee, A/m, density | **PASS** | `outputs/reentry_space_weather_sensitivity/`, `tests/test_physics_expert.py` |
| Learned lifetime expert (quantile regression + gate + Mondrian CQR) | feature corruption / missingness at prediction time | **BLOCKED — no persisted model** | the selected learners (`kumo` at 2011, `tabm` at 2016, `mlp` at 2006) exist only as archived predictions; refitting requires the unavailable backends for two of them (`final_repro/final_reproducibility.json`: 2/7 backends present). Cost if backends were available: one origin ≈ `summary.json::seconds_total` per origin (minutes to an hour on CPU) × perturbation grid. **Not run.** The *design-time* missingness ablation `am_design Stage 2` (X6) is a different question (training without a feature) and awaits approval |
| Conjunction (Kelvins) learned arms | CDM feature corruption | **BLOCKED — no persisted model** | `conjunction/run.py` fits in-process and saves only predictions (`test_predictions.npz`); a perturbation study needs a refit (`summary.json::seconds` records the archived cost). **Not run.** The archived result already shows the deployed intervals cover only 48 % of true high-risk events (`cov90_high`), which is the operative calibration failure |
| Vision (SpotGEO) | noise / drift / background | **PASS (measured, descriptive)** | X14: recall by measured contrast, background, noise and pointing-drift strata for all ten arms, `outputs/spotgeo_difficulty/` — observational stratification of the real test set, not injected corruption |
| Noisy-OR decision layer `fusion.decide` | constructed evidence | **PASS (unit-level)** | `tests/test_fusion_properties.py` (11 tests). Note: `decide` is not on the deployed twin path — no two modules produce joinable evidence (C4) — so its propagation behaviour is a property of the legacy `cosmos.run_pipeline` chain only |

## What would be needed to close the two BLOCKED rows without approval

Nothing: both need either a refit (cost stated above, backends partly unavailable) or a re-exposure
of a pre-registered test half (X13). Both are approval items and are listed as such in the tracker.
