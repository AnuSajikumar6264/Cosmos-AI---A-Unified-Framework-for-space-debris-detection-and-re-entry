# C3 evaluation — operational status → decay regime

Verdict: **INCONCLUSIVE** (post-hoc, single non-blind window). Date 2026-11-04.
Source: `outputs/phase_e/phase_e_results.json` (`C3`), `outputs/benchmarks/twin_couplings/c3_summary.json`.

## Hypothesis

Catalogue operational status improves 72-day re-entry probability for LEO payloads over
status-blind policies using the same information.

## Scientific rationale — and the claim deliberately *not* made

Operational status is **not** a causal driver of atmospheric drag. The defensible rationale is
narrower and conditional: an operationally controlled payload has its orbit actively
maintained, so **drag physics does not determine its re-entry date**. Status is therefore a
proxy for *operator control*, and the coupling works by **withholding** a drag forecast from
objects whose orbit is maintained, substituting a population base rate.

This is a **conditioning decision about model applicability**, not a claim that status changes
decay physics. The Phase A audit flagged the causal reading as indefensible; this evaluation
retains only the conditional reading.

## Variables, units, time references

| Role | Variable | Values / units | Time reference |
|---|---|---|---|
| Input | CelesTrak `OPS_STATUS_CODE` | `+ P B S X` → operational, `-` → non-operational, missing → unknown | as of τ = 2026-08-16 |
| Input | perigee, apogee, inclination, design data, space weather | km, deg, sfu | as of τ |
| Policy output | P(re-entry within 72 d) | probability | τ → 2026-10-27 |
| Outcome | `DECAY_DATE` in the follow-up snapshot | date | ≤ 2026-10-27 |
| Identity | `NORAD_CAT_ID`, joined across two snapshots | — | — |

Population: Earth-orbiting payloads, perigee < 600 km, launched ≤ τ, not already decayed.
Payloads whose pre-τ decay was reported late are dropped.

Implementation: `cosmos/ai/twin/couplings.py:c3_dataset`, `previous_window_rate`, `c3_run`.

## Assumptions

1. `OPS_STATUS_CODE` at τ reflects control status at τ (it is a catalogue field, updated
   irregularly).
2. The follow-up snapshot's decay dates are complete for the window.
3. The previous-window base rate is a valid prior for the next window of equal length —
   it uses only outcomes **before** τ.
4. Launches are the dependence unit.

## What the coupling changes

A **conditional prediction**: which model applies to which object. It does not modify a
physical probability, and it does not alter a decision priority.

## Leakage audit

- `previous_window_rate` uses only decays in `(τ − H, τ]`. Verified by hand computation in
  `tests/test_couplings_regression.py::test_c3_previous_window_rate_excludes_outcomes_after_the_window`
  (a decay after τ stays in the denominator but not the numerator). **PASS**.
- The three prospective policies use information available at τ only. **PASS**.
- The two **in-window recalibrations** (Platt maps) are fitted on the follow-up window's own
  outcomes, cross-fitted in two folds by launch. They are **circular with respect to the
  forecast question** and are reported only as a diagnostic of attainable calibration. They are
  excluded from the verdict. **Disclosed, not used.**
- The window was analysed earlier in the project, so this is **not a blind test**.

## Design

| Property | Value |
|---|---|
| Primary endpoint | Brier score of P(re-entry ≤ 72 d) |
| Secondary | expected calibration error, AUC-ROC, AUC-PR |
| Unit of analysis | payload |
| Independent unit | launch |
| Arms | physics status-blind; base-rate status-blind; **twin status-aware** |
| Interval | launch-cluster bootstrap |
| Correction | BH across the 2 prospective contrasts |
| Population | 13,794 payloads, 182 events (rate 0.0132), 1,070 launches, 86 with events |

## Results

### Prospective policies

| Policy | Brier | ECE | Mean p |
|---|---|---|---|
| physics, status-blind | 0.017926 | 0.02674 | 0.03916 |
| previous-window base rate, status-blind | 0.013020 | 0.00054 | 0.01265 |
| **twin, status-aware** | **0.012522** | 0.00084 | 0.01343 |

### Contrasts

| Contrast | Mean ΔBrier | 95 % CI | Verdict |
|---|---|---|---|
| status-aware − physics status-blind | −5.404e−03 | [−1.198e−02, +6.414e−04] | INCONCLUSIVE |
| status-aware − base-rate status-blind | −4.984e−04 | [−1.229e−03, +8.306e−05] | INCONCLUSIVE |

### Event rate by status — the information is real

| Status group | n | Events | Event rate | Mean p(physics) |
|---|---|---|---|---|
| non-operational | 161 | 17 | **0.1056** | 0.0755 |
| operational | 13,478 | 164 | 0.0122 | 0.0390 |
| unknown | 155 | 1 | 0.0065 | 0.0167 |

Non-operational payloads decay at **8.7×** the operational rate. The status variable carries
genuine information.

### In-window diagnostic (NOT a forecast, excluded from the verdict)

| Policy | Brier | ECE |
|---|---|---|
| physics recalibrated, status-blind | 0.008479 | 0.00350 |
| twin status-aware recalibrated | 0.008079 | 0.00297 |

## Interpretation

Status is informative, but **acting on it does not beat a status-blind base rate**:

- The status-aware policy's whole advantage over the physics policy (ΔBrier −0.0054) is
  essentially reproduced by the status-blind base rate (0.01302 vs 0.01252).
- The residual gain over that base rate is −0.0005 Brier with an interval spanning zero.
- The physics policy is **badly calibrated** here (ECE 0.0267, mean p 0.039 vs event rate
  0.013 — over-forecasting by 3×). Most of the apparent "coupling gain" is really the base
  rate's superior calibration, not the use of status.

So the honest reading is that C3's benefit is dominated by replacing a miscalibrated drag
forecast with a well-calibrated base rate, and the status-aware refinement on top of that is
not resolvable at this sample size.

## Statistical power

182 events across 1,070 launches, with only 86 launches containing any event. The
status-aware/base-rate difference is ~4 % of the base-rate Brier. Detecting that reliably would
need substantially more events or a longer window. The inconclusive result should **not** be
read as evidence of no effect.

## Limitations

1. **Not blind** — the window was analysed earlier in the project.
2. Single 72-day window; no temporal replication.
3. Status is a proxy for control, not a telemetry-derived health measurement.
4. Non-operational group is small (161 payloads, 17 events).
5. Catalogue status fields are updated irregularly and may be stale at τ.
6. Post-hoc re-analysis.

## Conclusion

**INCONCLUSIVE.** Operational status carries real information about decay (8.7× event-rate
difference), but the status-aware policy is not demonstrably better than a status-blind
previous-window base rate on this window.

Defensible claim: *non-operational LEO payloads decayed at 8.7× the operational rate in this
window, and withholding the drag forecast from controlled payloads improves Brier score over
applying it to all payloads; the improvement is not separable from that of a status-blind base
rate at this sample size.*

Not defensible: *operational status improves re-entry prediction*, and emphatically not
*operational status drives orbital decay*.

### Recommended next experiment

Score additional non-overlapping windows with the protocol fixed in advance, giving genuine
temporal replicates. This also requires later snapshots and is coupled to Phase F.
