# Phase D final status matrix

Date: 2026-11-04. HEAD `78ee339`, working tree modified (uncommitted Phase C/D work).
Suite: **134 passed, 0 failed, exit 0** (`python -m pytest tests/ -q`).
Logs: `outputs/run_phase_d/logs/`.

Status terms are used as specified: PASS, PARTIAL, FAIL, BLOCKED, NOT VALIDATED,
NOT IMPLEMENTED. **Software correctness is reported separately from scientific validity
throughout.** No test result in this table is evidence that a prediction is accurate.

## 1. Phase D work items

| Item | Status | Evidence | Unresolved blocker |
|---|---|---|---|
| L17 decision recorded and enforced | **PASS** | [L17_METHODOLOGY_DECISION.md](L17_METHODOLOGY_DECISION.md); [decision log](../../research_design/METHODOLOGY_DECISIONS.md); 5 tests | None. Calibrated columns remain **NOT VALIDATED** as a coherent CDF, by decision |
| `engine.py` isotonic calibration untouched | **PASS** | `git diff` shows no change to `iso`, `p_lifetime` or `horizon_prob` lines | None |
| Calibrated lifetime artifacts preserved | **PASS** | No twin re-run; `run_pipeline.py` refuses to overwrite a run directory | None |
| C2 pathway traced and regression-tested | **PASS** (software) | 7 pure-function + 2 artifact tests | Calibrated-vs-raw ranking still **NOT VALIDATED** (cluster uncertainty) |
| C3 pathway traced and regression-tested | **PASS** (software) | 4 pure-function + 2 artifact tests | Status is a proxy, not telemetry health; one non-significant window |
| T1 pathway traced and regression-tested | **PASS** (software) | 4 pure-function + 2 artifact tests | T1 is **NOT VALIDATED** as confirmatory — self-disclosed non-blind |
| No look-ahead leakage in tested components | **PASS** | `previous_window_rate` hand-computed 0.5; late-report dropping verified | Full dataset-backed re-execution not covered |
| Uncertainty preserved, physical semantics intact | **PASS** | survival bounds/monotonicity, CI bracketing, undefined-metric omission, C4 invariance | None |
| Full re-execution of `c2_cloud_survival`/`c3_run`/`engine.forecast` | **PARTIAL** | Components and saved artifacts tested; no end-to-end re-run | Needs full snapshots and ~20 min compute; not run to avoid touching outputs |
| L13 checkpoint audit | **PASS** | [L13_CHECKPOINT_AUDIT.md](L13_CHECKPOINT_AUDIT.md); `outputs/run_phase_d/l13_checkpoint_audit.json`; 3 tests | Weights **BLOCKED** (absent by `.gitignore` design) |
| OPSSAT checkpoint identity verifiable | **NOT VALIDATED** | No `.pt`/`.pth`/`.ckpt` anywhere in the repo | Do not claim exact weight reproduction for `opssat_{hybrid,fcnn,cnn}` |
| Evidence artifacts locatable | **PASS** | 10/10 resolve at the identical repo-relative suffix | None |
| Dashboard reads versioned pipeline runs | **PASS** | [DASHBOARD_INTEGRATION_REPORT.md](DASHBOARD_INTEGRATION_REPORT.md); 12 tests; rendered from `run_20261104T053528Z` | Live/operational dashboard **NOT IMPLEMENTED** (out of scope) |
| Dashboard scenario coverage (6 requested) | **PASS** | All six plus four more, in `tests/test_dashboard.py` | None |
| Run/snapshot mixing prevented | **PASS** | One run rendered; inconsistent `as_of` reported explicitly | None |
| T1 later-snapshot readiness | **PASS** (preparation) | [T1_LATER_SNAPSHOT_EVALUATION_READINESS.md](T1_LATER_SNAPSHOT_EVALUATION_READINESS.md); 3 tests | Evaluation itself **BLOCKED** |
| Later-snapshot evaluation executed | **BLOCKED** | Newest outcome coverage 2026-10-26, i.e. **−1 day** relative to the forecast | Needs a snapshot dated ≥ 2026-11-26 (30 d); acquisition needs authorisation |
| Hashed forecast integrity | **PASS** | `twins.jsonl: OK` re-verified 2026-11-04 | None |
| Pre-registration freeze | **PASS** | `freeze.json` verifies INTACT; guarded by a test | None |

## 2. Research-integrity compliance

| Requirement | Status | Evidence |
|---|---|---|
| No frozen pre-registration file modified | **PASS** | Freeze INTACT; `experiment.py` byte-identical to the freeze |
| No methodology or hyperparameter change | **PASS** | Only additive adapters/tests/docs; calibration untouched |
| No existing experiment output overwritten | **PASS** | New artifacts under `outputs/run_phase_d/`, `outputs/pipeline/run_*`, `outputs/audit/`; `git status` shows no modified `outputs/` file |
| Original artifacts and hashes preserved | **PASS** | Forecast digest OK; `model_cards.json` not regenerated |
| Software correctness separated from scientific validity | **PASS** | Stated in every report and in each test module's docstring |
| Actual commands, exit codes, test counts recorded | **PASS** | This matrix and the reports; logs in `outputs/run_phase_d/logs/` |
| No independent-validation claim without evidence | **PASS** | No module is marked `INDEPENDENTLY_VALIDATED` |
| No Q1 journal claim | **PASS** | JIRS remains unverified (Springer HTTP 406, SCImago HTTP 403) |

## 3. Test inventory

| File | Tests | Scope |
|---|---|---|
| `test_ai.py` | 19 | AI primitives, protocols, pre-registration freeze gate |
| `test_artifact_audit.py` | 3 | registry audit, foreign-workspace classification, horizon-coherence audit |
| `test_contracts.py` | 12 | typed contracts, incl. non-coherent CDF rejection |
| `test_couplings_regression.py` | **28** | C2 / C3 / T1 regression, later-snapshot readiness |
| `test_dashboard.py` | **12** | run rendering and six failure/abstention scenarios |
| `test_datasets.py` | 7 | dataset discovery, status, validation |
| `test_end_to_end.py` | 10 | Level 3 pipeline execution |
| `test_experiment.py` | 3 | run provenance, freeze integrity |
| `test_integration.py` | 13 | Level 2 adapter integration |
| `test_orchestration.py` | 6 | dependency/partial-run semantics |
| `test_twin.py` | 14 | twin state, C3 regime rule, C2 survival conversion |
| `test_verify.py` | 7 | legacy physics verification |
| **Total** | **134** | **0 failed, exit 0** |

## 4. Unresolved blockers, ranked

1. **No later snapshot** — blocks the only genuinely blind temporal evaluation available.
   Needs a CelesTrak SATCAT snapshot dated ≥ 2026-11-26 and explicit download authorisation.
   This is the single highest-value outstanding item.
2. **No identity-linked dataset** spanning telemetry, conjunctions and catalogue outcomes (L1).
   Keeps C4 permanently a demonstration and bounds any end-to-end claim. Not solvable by code.
3. **T1 is not blind** (L2/L3). Existing temporal results stay exploratory regardless of test
   coverage.
4. **OPSSAT weights absent** (L13). Blocks exact weight reuse only; metrics stay traceable.
5. **No full re-execution** of the C2/C3/T1 drivers. Components and artifacts are covered;
   a dataset-backed re-run remains unverified by CI.
6. **Calibrated lifetime columns are not a coherent CDF** (L17) — now a documented, bounded,
   enforced decision rather than an open defect.

## 5. Explicitly not done

Per instruction, Phase D stopped before coupling ablations and manuscript claims. Not started:
coupling ablation experiments (E7), uncertainty-propagation experiments (E8),
distribution-shift evaluation (E9), novelty assessment, and any manuscript text. The central
research question — whether cross-domain coupling adds measurable value over independent
subsystems — is **not answered by this phase** and remains the next substantive step.
