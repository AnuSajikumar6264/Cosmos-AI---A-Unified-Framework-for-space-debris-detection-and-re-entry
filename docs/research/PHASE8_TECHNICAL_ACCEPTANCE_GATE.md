# Phase 8 — Technical acceptance gate

Evaluated 2026-11-06T06:34:17+00:00 at HEAD `78ee33962007` by `scripts/phase8_acceptance_gate.py`. 
Machine record: `outputs/audit/phase8_acceptance_gate.json`. Nothing was modified by the gate.

## Verdict: **PASS WITH LIMITATIONS**

## Checks

| Group | Check | Status | Detail |
|---|---|---|---|
| integrity | ESA-ADB pre-registration freeze | **PASS** | 28/28 frozen files hash-identical (freeze_id 681cc7ddec86) |
| integrity | original confirmatory freeze | **PASS** | freeze 09a98f5e160e (CONFIRMATORY.json): 27/28 files identical; differing: ['research_design/preregistration/PREREG_TELEMETRY_V1.md'] (expected only the pre-registration document, whose section 9 was filled in afterwards — DEVIATIONS.md 2026-10-24 22:00) |
| integrity | G5d pre-registration | **PASS** | research_design/G5D_PREREGISTRATION.md hash matches |
| integrity | figure release manifest | **PASS** | 107/107 files (figures, source data, scripts, documents, upstream artifacts) unchanged |
| integrity | OPS-SAT historical archive | **PASS** | 10/10 archived files unchanged |
| integrity | dated twin state and forecast | **PASS** | twins.jsonl = recorded digest; forecast_table = run-manifest digest |
| git | HEAD unchanged, nothing committed | **PASS** | HEAD 78ee33962007 (directive start 78ee33962007) |
| git | nothing staged | **PASS** | 0 staged paths |
| git | working tree | **INFO** | 17 modified tracked files, 1605 untracked paths — all uncommitted by instruction |
| writing | JINT manuscript untouched | **PASS** | paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md = release-manifest hash |
| writing | no manuscript/thesis file modified since the directive day | **PASS** | 0 files modified on/after 2026-11-06 |
| tests | full suite | **PASS** | 341 passed, 3 skipped in 55.72s |
| tracker | Phase 0-7 rows with a non-terminal status | **PASS** | 0 of 93 rows still IN PROGRESS / NOT STARTED / VALIDATION PENDING |
| tracker | rows limited by data, approval or external dependency | **LIMIT** | 14 rows |
| audit | latest Phase N system audit | **INFO** | PARTIAL: 27 PASS, 1 FAIL (learner training-reproducibility) |

## Limitations carried into the writing phase

Rows in the completion tracker whose status is BLOCKED, NOT EVALUABLE or awaiting approval (Phases 0-7):

- Phase 2: 2.1 OPS-SAT reproduction (X1) — PASS WITH LIMITATIONS / untouched 10/10 / 122/122 + 47/47 / Exact to 0.0000 on every metric / fcnn, transformer / Not reproducible at seed level: `cnn` / < 0.001 / not separable at 5 seeds
- Phase 2: 2.2 Named-subsystem health monitoring (power / thermal / attitude / propulsion) — PASS WITH LIMITATIONS — simulation only / NOT EVALUABLE on real data
- Phase 2: 2.2 Anomaly evidence → health-state / priority updates — PASS (correct behaviour = abstention) / NOT EVALUABLE
- Phase 2: 2.4 Re-entry — corridor / impact validation — NOT EVALUABLE — BLOCKED BY INPUT, not by truth
- Phase 2: 2.5 Conjunction — propagation, screening, closest approach — NOT EVALUABLE
- Phase 2: 2.6 Vision — association to satellites — NOT EVALUABLE
- Phase 3: Uncertainty under missing / corrupted inputs (X11) — PASS WITH LIMITATIONS / BLOCKED
- Phase 4: Shared state `ObjectTwin` — PASS WITH LIMITATIONS
- Phase 4: Cross-dataset fusion where joinable — NOT EVALUABLE
- Phase 5: Ablations not evaluable or awaiting approval — recorded
- Phase 6: Training-level reproducibility — BLOCKED — EXTERNAL DEPENDENCY
- Phase 6: Cross-satellite generalisation — NOT EVALUABLE
- Phase 6: Missing modalities / corrupted telemetry / noisy imagery — PASS WITH LIMITATIONS / BLOCKED
- Phase 6: Prospective validation — BLOCKED — EXTERNAL DEPENDENCY

## Experiments not run — awaiting explicit approval

| Id | What | Cost |
|---|---|---|
| X3 | ESA-ADB 3b Stage 1 — 2x2 re-selection (F4 x F5), new output dir | minutes CPU |
| X4 | ESA-ADB 3b Stage 2 — 12 AR(8) OOF fits | 3-4 h |
| X6 | lifetime am_design Stage 2 missingness ablation (design-time) | per protocol doc |
| X10 | OPS-SAT E6 branch ablation (decides K8) | hours of training, 5 seeds x branches |
| X13 | ESA-ADB input-perturbation robustness — re-exposes the pre-registered test half | minutes-hour CPU |
| twin-state | regenerate twins.jsonl with the current engine into a NEW directory (provenance + forecast reproduction check) | ~1,250 s |

## Test suite

`341 passed, 3 skipped in 55.72s` (return code 0).

## Phase N system audit

`outputs/final_audit/final_system_audit.json`: verdict PARTIAL; failures: learner training-reproducibility (measured 2/7 (mlp, xgboost), expected 7/7)

## What the gate means

PASS WITH LIMITATIONS: every frozen artifact verifies, no code was committed, the manuscript and thesis files are untouched, the full suite passes, and every Phase 0-7 row has reached a terminal status. The limitations above are data, approval or external-dependency boundaries recorded in the tracker; they are to be *stated* in the writing, not resolved by it. Phase 9 (writing) remains locked until the user confirms this gate.
