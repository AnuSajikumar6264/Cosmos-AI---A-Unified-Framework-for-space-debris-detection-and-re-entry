# COSMOS-AI experimental programme

This plan separates software verification, existing benchmark measurements, and future
scientific validation. Existing results are not silently replaced or re-labelled. All
confirmatory future work must freeze the protocol before inspecting the holdout outcomes.

## Status key

- **Executed—historical:** result artifacts exist, but the result may have known exposure or
  post-hoc changes.
- **PARTIAL:** some benchmark or code checks exist; the full required evaluation does not.
- **BLOCKED:** suitable data, identity linkage, ground truth, authorization, or hardware is
  unavailable.
- **NOT RUN:** no new experiment was launched in this architecture task.

| ID | Experiment | Existing evidence/status | Required next protocol |
|---|---|---|---|
| E1 | Telemetry temporal generalization | **PARTIAL / executed historically:** ESA-ADB, OPSSAT-AD and SMAP/MSL studies, differing protocols and seed counts. | Freeze mission-wise forward/challenge splits, official event metrics, alarms and seed set; report test exposure and false-alarm run/duration distributions. |
| E2 | Alarm-selection ablation | **PARTIAL / executed historically:** OOF and alarm-policy analyses exist; calibration subsets are small and test exposure is disclosed. | Freeze forecaster, calibration, threshold, persistence and merge ablations independently; no test-based setting selection. |
| E3 | Debris detection generalization | **PARTIAL / executed historically:** SpotGEO benchmark results; synthetic image results are separate. | Add unseen sensor/condition dataset and boundary tests for scorer; block real-world generalization claims until then. |
| E4 | Lifetime prediction | **Executed—historical:** two forward origins, baselines, ablations, uncertainty and cluster-bootstrap results. | Treat existing results as exploratory due repeated test scoring and learner-set change. New confirmation needs a frozen later cohort and code/config. |
| E5 | Collision-risk calibration | **Executed—historical:** CAC anonymised-event benchmark and official metrics. | Report physical probability calibration separately from decision priority; no linked operational-priority claim. |
| E6 | Re-entry/trajectory validation | **PARTIAL:** lifetime dates are scored; simulated trajectory physics has analytic/unit tests. | Real trajectory/impact validation is **BLOCKED** by missing independent orbital history/impact ground truth. Never treat simulation checks as historical validation. |
| E7 | Coupling ablation | **PARTIAL / executed historically:** C1/C2/C3 evaluations; C4 demonstration only. | C1/C2/C3 effect sizes and dependence-aware intervals are reported; fresh prospective C3 and any C4 test require unexposed linked data. |
| E8 | Uncertainty propagation | **PARTIAL / executed historically:** conformal/CQR, Monte Carlo, calibration and risk-coverage utilities and module analyses. | Add adapter-level tests preserving method, bounds, assumptions and provenance; assess end-to-end coverage only where linked outcomes exist. |
| E9 | Distribution shift | **PARTIAL / executed historically:** forward temporal tests, time-blocked OPSSAT comparison and telemetry diagnostics. | Predefine shift strata and report calibration/drift by period; avoid test-adaptive recalibration unless explicitly an online protocol. |
| E10 | End-to-end execution | **PARTIAL:** legacy simulator run and dated re-entry twin outputs; new adapter orchestrator supports partial module execution. | Add deterministic small-fixture end-to-end tests for compatible adapters. Real linked-system scientific validation remains **BLOCKED** by unpaired datasets. |

## Run metadata and artifact integrity

New `cosmos.ai.experiment.Run` outputs now include `run_metadata.json` with seed,
configuration digest, Git HEAD/dirty-state evidence, optional model version, and the SHA-256
of a dataset manifest when available. Existing run folders are not rewritten. Set the
optional `dataset_manifest` and `model_version` arguments when creating a run if the
defaults do not describe the exact dataset or model. A failed Git query is recorded
explicitly; missing manifests are marked rather than invented.

Run `python scripts/audit_model_artifacts.py --root .` to report missing checkpoint/evidence
references in the registry. The command is read-only. It does not repair metadata or fetch
weights.

## Computational and access gates

Do not launch a full lifetime retraining or foundation-model sweep as part of routine
validation. Existing reports describe hours-long training/inference and GPU/XPU resource
requirements. Before any such run, estimate runtime, free disk, RAM/device memory, and
whether all weights/data are already available. No network download, restricted data request,
or redistribution is authorized by this experiment plan.

The later-snapshot score of the hashed 2026-10-27 forecast is high priority but **BLOCKED**
until a later, permitted snapshot is available. Preserve the forecast hash and do not adjust
the prediction from future outcomes.

## Results actually executed in this architecture task

- The focused architecture/artifact tests passed: **32 passed**. The repository-owned suite
  passed **64 tests** and failed the pre-registration integrity check because the experiment
  bookkeeping module's digest differs from the frozen value. That freeze was not refreshed;
  no scientific protocol or test result was re-frozen by this task.
- Unrestricted `pytest -q` also discovers vendored ESA-ADB upstream tests and fails during
  collection because their independent dependencies/import layout are not installed.
- The static evidence dashboard reads existing benchmark/twin artifacts. It does not run
  any model or add predictions.
- No benchmark retraining, dataset acquisition, re-entry forecast, or scientific coupling
  evaluation was launched.
