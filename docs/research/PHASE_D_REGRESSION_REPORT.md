# Phase D regression report — C2, C3 and T1

Date: 2026-11-04. Repository HEAD `78ee339`, working tree modified (uncommitted Phase C/D work).

Scope: trace the C2, C3 and T1 pathways, verify identity linkage, timestamps, units,
provenance, missing-data handling and uncertainty semantics, and add regression tests.

**These are software-correctness results under tested conditions. They are not scientific
validation, and they do not make T1 confirmatory.** T1 remains explicitly non-blind.

Commands run and recorded:

```bash
python -m pytest tests/test_couplings_regression.py -q   # 28 passed, exit 0
python -m pytest tests/ -q                               # 134 passed, exit 0
```

Logs: `outputs/run_phase_d/logs/test_couplings_regression.log`,
`outputs/run_phase_d/logs/full_suite.log`.

## 1. Pathway definitions, resolved from the implementation

Definitions were read from the code and its docstrings, not assumed.

### C2 — lifetime survival → debris-cloud population

`cosmos/ai/twin/couplings.py` (`c2_cloud_survival`, `c2_summary`, `c2_bootstrap`).

For breakup cloud *f* with at least 30 fragments, at `k` ∈ {1..5} years after the cloud's
first catalogued fragment (`D_k = min(t0) + 365.25k`), the expected number still in orbit is
`Σ_i S_i(D_k − t0_i)` over fragments catalogued by `D_k`, compared with the catalogue count.

- **Inputs**: `outputs/benchmarks/reentry_lifetime/origin{2016,2011}_uncontrolled/test_predictions.npz`
  and `tuneB_predictions.npz`; cohort split from `cosmos.ai.lifetime.run.split`.
- **Identity**: fragments keyed by cohort row, grouped by `breakup_family` (GCAT `Parent`).
  **Not** NORAD-linked to the dated twin snapshot — a different population.
- **Outputs**: `outputs/benchmarks/twin_couplings/c2_{cloud_survival,summary,bootstrap}.csv`.
- **Two readings**: *raw* (interpolated quantile function) and *calibrated* (isotonic maps of
  `P(T ≤ a)` fitted on **tune-B** fragments over `AGE_GRID`, 25 ages from 10 to 1826.25 d).
- **Leakage control**: fragments come from the lifetime **test** folds, so no fragment outcome
  was used in fitting; calibration uses tune-B, a disjoint set.

### C3 — catalogue operational status → re-entry regime

`cosmos/ai/twin/couplings.py` (`c3_dataset`, `previous_window_rate`, `c3_run`).

- **As-of** `TAU_C3 = 2026-08-16`; **outcomes** from `FOLLOW_C3 = 2026-10-27`; horizon 72 d.
- **Population**: Earth-orbiting payloads, perigee < 600 km, launched ≤ τ, not already decayed.
- **Identity**: `NORAD_CAT_ID`, joined between the 2026-08-16 and 2026-10-27 snapshots.
- **Rule**: an operational payload (`+ P B S X`) can manoeuvre, so drag physics does not
  determine its re-entry; a non-operational payload (`-`) decays naturally; missing status is
  `unknown`.
- **Three prospective policies** (information at τ only) and **two in-window diagnostics**
  (Platt maps fitted on the follow-up window's own outcomes, cross-fitted in two folds by
  launch). The in-window pair is a diagnostic of attainable calibration, not a forecast.

### T1 — as-of re-entry forecast of the whole catalogue

`cosmos/ai/twin/prospective.py`.

- **As-of** `AS_OF = 2026-08-16`; **outcomes** from `FOLLOW = 2026-10-27`; horizons 30 d, 72 d.
- **Population**: every object in orbit with perigee < 2000 km at τ.
- **Identity**: `norad`, mapped into the follow-up snapshot's `DECAY_DATE`.
- **Variants**: `physics_prior`, `physics_history`, `lifetime`, and the twin's per-regime choice.
- **Non-blind**, by its own disclosure: the aggregate decay count in this window was seen while
  diagnosing domain shift, and the window had been used by an earlier landmark benchmark.

**Critical distinction.** T1's follow-up date (2026-10-27) is the *as-of date* of the hashed
dated forecast. They are different studies, and T1's outcomes cannot score that forecast —
the window would be zero length. See
[`T1_LATER_SNAPSHOT_EVALUATION_READINESS.md`](T1_LATER_SNAPSHOT_EVALUATION_READINESS.md).

## 2. Verification results

### Identity linkage — PASS

| Check | Result |
|---|---|
| C3 payloads keyed uniquely by NORAD | PASS — `NORAD_CAT_ID` unique over 13,794 rows |
| T1 objects keyed uniquely by NORAD | PASS — `norad` unique over 30,826 rows |
| C2 cloud-years unique per (origin, cloud, years) | PASS — no duplicates in 160 rows |
| T1/C3 share one as-of window | PASS — both τ = 2026-08-16, follow-up = 2026-10-27 |
| Dated forecast kept separate from T1 | PASS — zero-length window asserted, not scored |

### Timestamps, units and censoring — PASS

| Check | Result |
|---|---|
| C3 non-events censored exactly at the window end | PASS — every `event == 0` row has `time_days == 72` |
| C3 events decay inside the window | PASS — all `event == 1` rows have `0 ≤ time_days ≤ 72` |
| C3 population respects its perigee bound | PASS — all rows `perigee < 600` km |
| C3 apogee ≥ perigee | PASS |
| T1 horizon labels nested | PASS — `y_30d ≤ y_72d` for every object |
| Follow-up snapshot holds no decay later than its data date | PASS — max decay 2026-10-26 ≤ 2026-10-27 |
| C2 ages bounded by the predictive cap | PASS — cloud-years beyond `CAP + 1` day are skipped in source |

Units are days throughout (`time_days`, `AGE_GRID`, horizons); altitudes are kilometres;
probabilities are dimensionless. No coordinate-frame transformation occurs in C2/C3/T1 —
these pathways use scalar orbital elements and times, so there is no frame to mis-convert.

### No look-ahead leakage — PASS

`previous_window_rate` is the only place where an outcome-derived base rate enters a
prospective policy. Tested against a hand-built snapshot:

- a decay **after** `end` is excluded from the numerator but stays in the denominator (it was
  in orbit at `end`) — correct;
- a decay **before** the window start is excluded entirely;
- a decay **exactly at** `end` counts (inclusive bound);
- the type / orbit-centre / perigee-band filters are applied.

Hand-computed expectation 2/4 = 0.5, measured 0.5. **PASS**.

`launch_fold` is md5-deterministic and assigns a launch's siblings to the same fold, so the
C3 cross-fitting cannot split a launch across folds. **PASS**.

### Uncertainty propagation and physical semantics — PASS

| Check | Result |
|---|---|
| C2 `S(τ)` is a survival function | PASS — within [0,1] and non-increasing over 7 ages |
| C2 documented 0.51 d age floor applied | PASS — `S(0) == S(0.51)` |
| C2 calibrated survival stays a probability | PASS — within [0,1]; ages outside `AGE_GRID` clipped, not extrapolated |
| C2 calibrated survival tracks predicted lifetime | PASS — correlation 0.5 with the latent scale on a 400-object fixture |
| C3 separates prospective from in-window | PASS — disjoint key sets; no policy in both groups |
| C3 Brier/mean probability within [0,1] | PASS — all five policies |
| T1 reports launch-cluster CIs | PASS — every Brier-difference CI brackets its own mean, both horizons |
| T1 expected/observed ratio CIs bracket their ratio | PASS — all variants, both horizons |
| T1 omits rank metrics when undefined | PASS — no AUC emitted with zero events or a constant score |
| C4 rule changes action only, never risk | PASS — a health alarm below threshold does not create high risk; the return value carries no probability field |

### Missing data and abstention — PASS

| Check | Result |
|---|---|
| C3 drops payloads whose pre-τ decay was reported late | PASS (source behaviour, mirrored by the T1 test) |
| T1 `outcomes` drops a decay at or before τ | PASS — hand-built fixture: NORAD 1 removed, 2/3/4 retained with correct labels |
| T1 keeps objects still in orbit as censored zeros | PASS |
| C2 skips clouds below 30 fragments and beyond the cap | PASS (source behaviour; artifact rows all satisfy the bounds) |
| C2 excludes fragments censored before `D_k` from the predicted sum | PASS — predicted counts never exceed fragments catalogued by `D_k` |

### Outputs not silently replaced, clipped, imputed or fabricated — PASS

| Check | Result |
|---|---|
| C3 status-aware policy overrides **only** operational payloads | PASS — for every non-operational/unknown payload the policy equals `p_physics` exactly |
| C3 operational payloads all receive one base rate | PASS — a single distinct value |
| T1 controlled payloads get a base rate, not a drag forecast | PASS — ≤ 4 distinct values per horizon across controlled payloads |
| C2 predicted counts physically admissible | PASS — ≥ 0 and ≤ fragments catalogued, for all 44 prediction columns |
| C2 observed counts admissible | PASS — `0 ≤ observed_in_orbit ≤ catalogued` |
| All C3/T1 probability columns within [0,1] and non-null | PASS |
| T1 class and regime labels from the closed vocabularies | PASS — `{P,R,C,D}`, `{natural_decay, operator_controlled, unknown}` |
| T1 non-blind disclosure still present in the module | PASS — asserted by test, so deleting it fails CI |

## 3. Tests added

`tests/test_couplings_regression.py` — **28 tests, all passing**.

| Group | Count | Notes |
|---|---|---|
| C2 pure functions | 7 | survival shape, age floor, calibration bounds/clipping, summary arithmetic vs hand computation, raw-vs-calibrated separation, bootstrap CI |
| C3 pure functions | 4 | base-rate leakage, band/type filters, fold determinism, C4 rule invariance |
| T1 pure functions | 4 | horizon labelling and late-report dropping, hand-computed Brier, undefined-metric omission, non-blind disclosure |
| Saved-artifact invariants | 8 | C3 payloads and summary, C2 cloud counts and uniqueness, T1 objects and summary |
| Snapshot separation | 2 | T1/C3 window identity; follow-up snapshot data-date bound |
| Later-snapshot readiness | 3 | BLOCKED without a qualifying snapshot, READY with one, digest-mismatch detection |

Expensive fits are **not** re-run: the pure functions are driven by hand-built fixtures and
the saved artifacts are read. Artifact tests skip (never pass) when the large outputs are
absent.

## 4. Suite totals

| File | Tests |
|---|---|
| `test_ai.py` | 19 |
| `test_artifact_audit.py` | 3 |
| `test_contracts.py` | 12 |
| `test_couplings_regression.py` | **28** |
| `test_dashboard.py` | **12** |
| `test_datasets.py` | 7 |
| `test_end_to_end.py` | 10 |
| `test_experiment.py` | 3 |
| `test_integration.py` | 13 |
| `test_orchestration.py` | 6 |
| `test_twin.py` | 14 |
| `test_verify.py` | 7 |
| **Total** | **134 passed, 0 failed, exit 0** |

## 5. What remains NOT VALIDATED

These were not resolved by regression testing, and testing cannot resolve them:

1. **T1 is not blind** and therefore not confirmatory. Outcome information influenced the
   history-conditioned variant's motivation. Status: **NOT VALIDATED** as confirmatory evidence.
2. **The dated 2026-10-27 forecast has no outcomes yet.** Status: **BLOCKED**.
3. **C2's calibrated reading cannot be confidently ranked** against the raw reading: cluster
   uncertainty is wide relative to the differences (pre-existing finding, unchanged here).
4. **C3's status is a proxy** for operator control, not a telemetry-derived health measurement,
   and its gain over the status-blind policy is not significant on one window.
5. **C4 cannot be validated** on public data; it abstains in the executable pipeline.
6. **No coverage of `engine.run`/`forecast` or `c3_run`/`c2_cloud_survival` end to end.** The
   regression tests cover their components and their saved outputs, not a full dataset-backed
   re-execution, which needs the full snapshots and roughly 20 minutes of compute.

## 6. Status summary

| Item | Status |
|---|---|
| C2 pathway traced, tested, invariants hold | **PASS** (software) |
| C3 pathway traced, tested, invariants hold | **PASS** (software) |
| T1 pathway traced, tested, invariants hold | **PASS** (software) |
| No look-ahead leakage in tested components | **PASS** |
| Uncertainty preserved; physical semantics intact | **PASS** |
| Full-pipeline re-execution of C2/C3/T1 | **PARTIAL** — components and artifacts only |
| T1 as confirmatory temporal evidence | **NOT VALIDATED** (non-blind) |
| Later-snapshot evaluation of the dated forecast | **BLOCKED** |
