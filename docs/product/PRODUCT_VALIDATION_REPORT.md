# Product validation report

Date: 2026-11-04. Branch `product/mission-intelligence-console`. Baseline HEAD `78ee339`.

Everything below was executed. Exit codes and counts are actual.

## Test results

```bash
.venv/bin/python -m pytest tests/ -q
# 168 passed in 42.99s     exit 0
```

| Suite | Tests | Note |
|---|---|---|
| Pre-existing (Phase A–D) | **134** | unchanged — not one assertion was weakened |
| `tests/test_product.py` | **34** | new |
| **Total** | **168 passed, 0 failed** | log: `outputs/product/logs/full_suite.log` |

Baseline before product work was 134 passed, exit 0. The product added 34 and broke none.

### Coverage of the seventeen required behaviours

| # | Requirement | Test | Status |
|---|---|---|---|
| 1 | Dashboard loading | `test_01_dashboard_pages_load`, `test_01b_app_health_is_not_a_satellite_health_claim` | **PASS** |
| 2 | Object search and selection | `test_02_object_search_and_selection`, `test_02b_unknown_object_reports_absence_not_a_guess` | **PASS** |
| 3 | Historical run loading | `test_03_historical_run_loads_without_recomputation` | **PASS** |
| 4 | Correct run provenance | `test_04_run_provenance_is_complete_and_displayed` | **PASS** |
| 5 | Scenario execution | `test_05_scenario_execution_creates_a_new_run`, `test_05b_scenario_rejects_invalid_input` | **PASS** |
| 6 | Failed module handling | `test_06_failed_module_is_shown_with_blocked_dependants` | **PASS** |
| 7 | Optional module absence | `test_07_optional_module_absence_is_neutral`, `test_07b_absent_datasets_are_reported_as_unavailable` | **PASS** |
| 8 | Missing telemetry | `test_08_catalogue_object_reports_no_telemetry`, `test_08b_telemetry_is_real_and_anonymised` | **PASS** |
| 9 | Missing debris confidence | `test_09_debris_confidence_and_timestamp_absent`, `test_09b_debris_image_is_served_and_path_traversal_refused` | **PASS** |
| 10 | Lifetime horizon incoherence | `test_10_lifetime_horizon_incoherence_is_surfaced`, `test_10b_capped_and_zero_width_intervals_are_not_shown_as_precision` | **PASS** |
| 11 | C4 abstention | `test_11_c4_escalation_abstains_with_a_reason`, `test_11b_c4_abstention_appears_in_the_run_and_overview` | **PASS** |
| 12 | Physical probability vs operational priority | `test_12_physical_probability_is_separate_from_operational_priority`, `test_12b_decision_priority_does_not_alter_upstream_probabilities` | **PASS** |
| 13 | Snapshot mismatch | `test_13`, `test_13b`, `test_13c`, `test_13d` | **PASS** |
| 14 | Report generation | `test_14_report_generation`, `test_14b_report_separates_computed_historical_and_unsupported` | **PASS** |
| 15 | Report provenance | `test_15_report_provenance_is_traceable`, `test_15b_report_records_an_unavailable_run_instead_of_omitting_it` | **PASS** |
| 16 | No overwrite of historical artifacts | `test_16_scenario_does_not_overwrite_historical_artifacts`, `test_16b_run_directory_collision_is_refused` | **PASS** |
| 17 | Prospective disabled when blocked | `test_17_prospective_evaluation_is_disabled_while_blocked`, `test_17b_overview_reports_the_prospective_blocker` | **PASS** |

## Execution evidence

### Routes

All 22 page and API routes return 200 on real artifacts; all seven malformed or absent
selections return the correct non-200 code:

| Request | Code |
|---|---|
| `/objects/999999999` (absent object) | 404 |
| `/telemetry/9/channel_1` (bad mission) | 400 |
| `/telemetry/1/channel_9999` (bad channel) | 404 |
| `/debris/9999999` (absent sequence) | 404 |
| `/runs/run_nope` (absent run) | 404 |
| `/runs/not-a-run` (malformed id) | 400 |
| `/api/objects/abc` (non-integer) | 422 |
| `/api/debris/1/frame/99.png` (out-of-range frame) | 400 |
| `POST /api/scenario` with `as_of: "nonsense"` | 422 |
| `POST /api/scenario` with `limit: -1` | 422 |
| `POST /api/scenario` with unknown module | 400 |

### Scenario execution

```
run directory: outputs/pipeline/run_20261104T062420055852Z
  catalogue_state success · lifetime success · reentry success · collision success
  health success · debris success · decision_priority success
exit code 0 · 7 tables written
new directories: exactly one · all prior runs preserved
```

### Screen captures

```bash
.venv/bin/python scripts/capture_console_screens.py
# 14/14 screens captured     exit 0
```

Written to `outputs/product/screens/` with `index.json`. Each file is the **actual server
response** for that route with the stylesheet inlined, so it opens without the server.

**Limitation — no PNG screenshots.** No headless browser (playwright, selenium, chromium,
firefox, wkhtmltoimage) is installed in this environment, and installing one requires a large
network download that was not authorised. **Status: BLOCKED** for image screenshots. The HTML
captures are real rendered screens, not mock-ups, and are the honest substitute. To produce
PNGs later: install playwright, then screenshot each route from the running server.

### Sample reports

Generated from real artifacts against run `run_20261104T063314427147Z`:

| File | Case |
|---|---|
| `outputs/product/reports/sample_assessment_NORAD37607.html` | ARIANE 5 R/B — near-term re-entry, zero-width interval |
| `outputs/product/reports/sample_assessment_NORAD5.html` | Vanguard 1 — censored at the study cap |
| plus `.json` for each | machine-readable form |

## Scientific safeguards — verified after the work

| Safeguard | Check | Result |
|---|---|---|
| Frozen pre-registration files unmodified | `freeze.json` recomputed | **INTACT** |
| `engine.py` calibration untouched | `git diff` for `iso`/`p_lifetime`/`horizon_prob` | **no changes** |
| Hashed forecast unmodified | `sha256sum -c FORECAST_SHA256.txt` | **twins.jsonl: OK** |
| No historical experiment output overwritten | `git status` + test 16 | **no `outputs/` file modified** |
| No new scientific engine | all values read via `store.py` / `cosmos.ai` | **confirmed** |
| No new dependencies | nothing installed | **confirmed** |

Files modified by this phase are **only** new product files plus the branch itself. The 14
tracked files showing as modified in `git status` were already modified before this phase
began (Phase C/D work) and were not touched here.

## Findings discovered during productization

Building a UI over the data exposed two presentation-correctness problems that the pipeline
tests could not have caught.

### 1. Zero-width intervals would read as extreme precision — fixed

91.7 % of objects with time quantiles (13,765 of 15,010) have `lo90 == median == hi90`. Of
those, **13,756 sit exactly at the 1826.25-day study cap**: every Monte-Carlo draw exceeded the
horizon, so the correct reading is "not re-entering within five years", not a precise lifetime.
A further 8 objects are degenerate *below* the cap (e.g. NORAD 37607 at exactly 10.0 days),
where all draws agreed — integrator discretisation, not confidence.

Displaying "5–95 %: 1826.25 – 1826.25 days" as a normal interval would materially mislead.
`store.interval_quality()` now classifies every interval as `at_cap`, `degenerate`, `spread` or
`unavailable`; the object page and the report both show an explicit warning, and
`test_10b` locks the behaviour in.

This is a **product display fix**. No scientific value was changed.

### 2. A template crashed on a manifest missing an optional key — fixed

`run.html` accessed `record.duration_s` directly, which raised `UndefinedError` for a
`not_requested` module whose manifest omitted the key. Found by `test_07`. All manifest lookups
in that template now tolerate absence.

## Honest product status

| Area | Status | Basis |
|---|---|---|
| Mission Overview | **PASS** | real snapshot statistics, findings, module status, abstentions, provenance |
| Orbital Intelligence | **PASS** | 31,396 objects searchable; mean elements only; no state vector |
| Satellite Intelligence | **PARTIAL** | real telemetry and benchmark evidence, but **anonymised** — no per-object health assessment is possible, by data constraint |
| Debris Intelligence | **PASS** | real imagery with real detections; confidence and timestamp correctly absent |
| Risk Intelligence | **PARTIAL** | real physical probabilities; operational priority genuinely unavailable; C4 abstains |
| Re-entry Intelligence | **PARTIAL** | real probabilities and quantiles; **no** trajectory, corridor or impact location exists |
| Evidence and Run Explorer | **PASS** | manifests, provenance, comparison, abstentions |
| Reports | **PASS** | computed/historical/unsupported separated, digests and commit recorded |
| Historical mode | **PASS** | verified non-mutating |
| Scenario mode | **PASS** | new run per execution, no overwrite |
| Prospective mode | **BLOCKED by design** | disabled; protocol published; nothing scored |
| Screenshots (PNG) | **BLOCKED** | no headless browser available |
| Trajectory / ground-track visualisation | **NOT IMPLEMENTED** | no validated trajectory data exists; an illustrative globe was deliberately not built |
| Live tracking | **NOT IMPLEMENTED** | no data feed; explicitly disclaimed throughout |

## What this validation does not establish

- These are **software** results. Not one of them is evidence that a prediction is accurate.
- No coupling (C1–C4) has demonstrated scientific benefit; that needs ablations, which are out
  of scope here and were not run.
- Benchmark numbers displayed by the console are the pre-existing saved results. The console
  did not re-evaluate them and cannot improve them.
- No prospective or independent validation was performed; the blind test remains blocked.
- The acceptance criterion — a newcomer can select an object, understand the evidence, inspect
  uncertainty and limitations, and export a traceable report without touching Python — is met
  for **catalogue objects** and for **anonymised telemetry channels**, which are the two entity
  types the data actually supports.
