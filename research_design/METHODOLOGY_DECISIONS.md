# Methodology decision log (lifetime / re-entry / twin studies)

Chronological record of methodology decisions for the catalogue lifetime, re-entry and twin
work. It is the counterpart of `preregistration/DEVIATIONS.md`, which is scoped to
`PREREG_TELEMETRY_V1.md` and must not be used for other studies.

This file is **not** part of any freeze, so it can be appended to without affecting a
pre-registration hash. Entries are append-only: correct an entry by adding a new one.

| Date (UTC) | ID | Decision | Rationale | Effect on existing results | Outcomes seen? |
|---|---|---|---|---|---|
| 2026-11-04 | L18 | Restore `cosmos/ai/experiment.py` to its frozen bytes and move run-provenance recording to the unfrozen `cosmos/ai/provenance.py`, attaching through the existing public `Run.extra` mapping. | Provenance code added to a pre-registration-frozen file tripped `oof_benchmark.check_freeze()`, which closes the held-out telemetry half. Re-freezing to accommodate non-scientific plumbing would weaken the pre-registration for no scientific gain. | None. No scientific computation changed; the frozen file is byte-identical to the freeze and `research_design/preregistration/freeze.json` verifies intact. Provenance output is unchanged in content. | Not applicable (no scoring performed). |
| 2026-11-04 | L17 | **Do not** change the independent per-horizon isotonic calibration of the learned lifetime expert, and do not regenerate the calibrated artifacts. Document the cross-horizon monotonicity defect and make downstream consumers abstain on the affected rows. | The twin's reported `p_*` forecast does not use `p_lifetime_*`, so the defect does not alter any reported re-entry probability. Recalibrating would change an already-published artifact and require re-running the dated twin. The affected columns are a secondary comparison. | None. `p_lifetime_30d/90d/1yr` are preserved exactly as published; 123 of 13,238 objects (0.93 %, worst drop 0.1797) are now excluded downstream with a recorded reason instead of being silently repaired. | The violation counts were measured during the audit before this decision; no forecast outcome was scored. |

## Standing constraints

- Pre-registration-frozen files (`research_design/preregistration/freeze.json`) must not be
  edited for engineering or plumbing reasons. `tests/test_experiment.py::test_preregistration_freeze_is_intact`
  fails if one changes.
- Existing experiment outputs are never overwritten. `scripts/run_pipeline.py` refuses to
  write into a non-empty run directory.
- A decision to *preserve* methodology is recorded here as explicitly as a decision to change
  it, so that silence is never read as approval.

## Full records

- L17: [`docs/research/L17_METHODOLOGY_DECISION.md`](../docs/research/L17_METHODOLOGY_DECISION.md)
- L18: [`docs/research/limitations_register.md`](../docs/research/limitations_register.md)
