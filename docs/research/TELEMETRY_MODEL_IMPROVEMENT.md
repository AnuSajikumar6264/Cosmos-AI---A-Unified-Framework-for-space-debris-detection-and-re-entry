# Telemetry model improvement

Date: 2026-11-04. Status: **NOT RUN.** No telemetry experiment was executed in this phase.

This document records why, and what the audit of the existing evidence shows, so that the
absence is explicit rather than implied.

## Why no experiment was run

1. **The pre-registration freeze constrains the confirmatory path.** `oof_benchmark.test`
   refuses to score the held-out telemetry half if any file in
   `research_design/preregistration/freeze.json` changes. Any improvement to the frozen
   modules (`oof.py`, `event_model.py`, `event_gbt.py`, `alarms.py`, `esa_eval.py`,
   `forecasting.py`, `models.py`, the ESA metrics package) would either break that gate or
   require a logged deviation and a re-freeze. A new exploratory arm must therefore live
   **outside** the frozen modules, which is a non-trivial restructuring rather than a tweak.
2. **The test halves are already scored.** Both mission test halves were scored under the
   confirmatory protocol, and again by post-hoc analyses P1–P8. There is no clean held-out
   telemetry population left for a confirmatory improvement claim.
3. **Priority.** The mandate directs that lifetime prediction is the highest priority and that
   effort should follow expected scientific value. The lifetime subsystem had a diagnosable,
   fixable defect (selection non-transfer, multi-horizon incoherence) reachable from saved
   artifacts. The telemetry subsystem's known weaknesses are mostly *evaluation-protocol*
   weaknesses, which new models would not fix.

## Audit of existing telemetry evidence

From `outputs/benchmarks/telemetry_esa_adb/results.csv` and the Phase A–D audits:

| Property | State |
|---|---|
| Official event-wise F0.5 metric | implemented via the official ESA-ADB metrics package |
| Forward-chaining validation | present in the post-hoc set (P2) |
| Alarm-selection ablation | present (P5/P8) |
| Exact-metric replication | present (P3) |
| Fair ACI comparator | present (P4) |
| Seed extension | present (P6) — 10 tree seeds, **9** TCN seeds (seed 9 not completed, logged) |
| Operational metrics | present (P7) |
| Mission/channel heterogeneity | reported; Mission 1 calibration has only **9 labelled events** |
| Seed counts | **uneven** — several benchmark rows are single-seed |
| Irregular sampling | resampled; benchmark requirement R8 **not met** |

### Weaknesses that a better model would not fix

- **Mission 1's calibration period holds 9 labelled events.** Alarm-threshold selection on 9
  events is irreducibly noisy regardless of the detector.
- **Single-seed rows** mean small differences between nearby arms are not interpretable.
- **A0 versus A1 differ in five respects simultaneously** (selection data, calibration pool,
  forecaster fitting period, grid, and residual scale — documented in `DEVIATIONS.md`), so the
  headline H6 comparison is confounded by design. This is an experimental-design issue, not a
  modelling one.
- **Anonymised missions** mean no operational validation is possible, and no link to any
  catalogued object exists (this is also why coupling C4 is unevaluable).

## What a defensible telemetry experiment would look like

If undertaken later, it must:

1. live entirely **outside** the frozen modules, in a new exploratory package;
2. be labelled **exploratory**, since no unscored test half remains;
3. hold the alarm-selection procedure fixed when comparing detectors, and vice versa — the
   existing A0/A1 confound shows what happens otherwise;
4. report event-wise precision, recall, F0.5, false-alarm runs per year, detection delay and
   alarm duration **per mission and per channel**, not pooled;
5. use ≥ 5 seeds for every arm, with per-arm variation reported;
6. correct for multiplicity across arms;
7. never re-freeze the pre-registration to accommodate it.

## Status

| Item | Status |
|---|---|
| Telemetry improvement experiment | **NOT RUN** |
| Existing telemetry evidence audited | **PASS** (documentary) |
| Pre-registration freeze | **INTACT** — unchanged by this phase |
| Original telemetry methodology | **UNCHANGED** |
| Claim of telemetry improvement | **none made** |
