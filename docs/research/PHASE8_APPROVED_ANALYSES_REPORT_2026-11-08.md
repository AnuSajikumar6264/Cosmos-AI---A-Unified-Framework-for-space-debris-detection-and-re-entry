# Phase 8 — report on the three authorised analyses (2026-11-08)

Written for the project record (examiner-facing). Gate accepted as PASS WITH LIMITATIONS on
2026-11-08; authorised: X4 (3b Stage 2), X6 Stage 1 (archive-only), X10 (E6, archive-only). Not run,
as prohibited: X3, X6 Stage 2, X13, twin-state regeneration. No frozen artifact, pre-registration
file, manuscript or thesis file was modified; nothing was committed or pushed. Machine records:
`outputs/audit/protected_artifacts_{before,after}_x4_x6_x10_*.json`, `outputs/audit/phase8_approved_analyses_manifest.json`.

## 1. X4 — 3b Stage 2, the exactly specified cells (exploratory)

**Question.** Which of A0→A1's protocol differences carries the pre-registered H6 gain (+0.353 corrected
event-wise F0.5, Mission 1, 58 target channels, conformal-BH layer)?

**What was run.** The AR(8) residual-score caches had been lost to the `*.npy` ignore rule. They were
regenerated with the frozen code into a new directory (353 s) and reproduce the archived score sample
hash exactly. The P1 cell runner was reused unmodified. Seven cells: the validity endpoints c0 (= A0)
and c5 (= A1), the P1 cells c2–c4, and the two defined cells P1 had not run — (Sh, P_half, D_cal) and
(Sh, P_half, D_half), where Sh is A1's model with A0's residual scale. Paired 30-day-block bootstrap,
B = 2,000, seed 20261024.

**Validity gate.** c0 = 0.074351 = A0; c5 = 0.427806 = A1; c2, c3, c4 identical to the archived P1
cells in value and operating point. Both ESA-ADB freezes verified before and after.

**Results (corrected event-wise F0.5 on the M1 test half).**

| Factor | Contrast | Δ | 95 % CI | Reading |
|---|---|---|---|---|
| F2 residual scale | S1 − Sh at P_cal, D_cal | 0.000 | [0, 0] | identical alarms |
| F2 residual scale | S1 − Sh at P_half, D_cal | −0.004 | [−0.013, 0.000] | immaterial |
| F2 residual scale | S1 − Sh at P_half, D_half (the A1 configuration) | 0.000 | [0, 0] | same operating point, same score |
| F3 calibration pool | half − cal at Sh, D_cal | +0.047 | [+0.019, +0.087] | positive, below the +0.05 threshold |
| F3 calibration pool | half − cal at S1, D_cal | +0.043 | [+0.016, +0.081] | positive, below the +0.05 threshold |
| F4 selection data | half − cal at Sh, P_half | +0.297 | [+0.152, +0.444] | **material** |
| F4 selection data | half − cal at S1, P_half | +0.301 | [+0.160, +0.443] | **material**; ≈ 85 % of +0.353 |
| F2 × F3 | interaction at D_cal | −0.004 | — | none |

**Interpretation.** Within the Mission-1 / AR(8) / conformal-BH cell space, the gain is carried by the
selection data (105 training-half events versus 9 calibration-window events); the calibration pool adds
a small positive amount; the residual scale adds nothing at any level; and these conclusions do not
depend on the residual-scale level. This agrees with the archived one-factor-at-a-time record for the
target channel set (D material; P, F, σ not material; G order-dependent). It supersedes an incorrect
statement in the decision analysis of 2026-11-08, which quoted the *lightweight* channel-set record.

**What X4 does not establish.** The full 2³ main effects of the proposal were not estimated: the fit-data
factor at the half-pool level is undefined for A0's fit-period model (no out-of-fold scores exist for
it over the training half), and the (P_cal, D_half) combination is defined in neither protocol
document. The grid factor was not re-tested. The result is exploratory (the test half had already been
scored post hoc) and specific to Mission 1 and the AR(8) scorer.

## 2. X6 Stage 1 — am_design missingness (archives only)

**Question.** Is the under-coverage of the deployed lifetime intervals at origin 2016 associated with
objects whose area-to-mass ratio is design-derived, and is the missingness→outcome association stable
over time?

**Method.** Area-to-mass source re-derived per object with the physics rule (reproduces the archived
per-split counts exactly). Coverage of the archived 80 %/90 % intervals by subgroup with a
launch-family cluster bootstrap (4,000 draws, seed 20261027). Adjusted odds ratio of 30-day decay given
design-A/M missing with the archived design matrix and cluster-robust errors; `statsmodels` is not
installed, so the identical model was re-implemented in numpy and validated against the archived
`leak_check.json` values (agreement to 1e-13) before use.

**Results.**

| Origin | `cosmos_gated` 80 % coverage, design-derived | class-prior | Δ design − class-prior | 90 % Δ |
|---|---|---|---|---|
| 2016 | **0.5625** [0.512, 0.614] (n 656) | 0.761 [0.646, 0.857] (n 2,322) | **−0.198 [−0.306, −0.072]** | −0.022 [−0.094, +0.081] |
| 2011 | 0.792 [0.747, 0.833] (n 404) | 0.947 [0.910, 0.969] (n 2,263) | **−0.154 [−0.205, −0.098]** | −0.083 [−0.119, −0.044] |

The same under-coverage of design-derived objects appears for `physics_only` and for the selected
learners, so it belongs to the physics input and to the Mondrian grouping (class × perigee band, which
does not see the A/M source), not to one learner. At origin 2016 the conformal calibration split holds
5.9 % design-derived objects against 22.4 % in the test split — the under-covered subgroup is 3.8×
under-represented where the correction is fitted. The pre-specified subgroup rule (A3) is met at 80 %
at both origins and not at 90 % at 2016.

Odds ratios: training windows 2.2 (all uncontrolled classes) / 3.4–3.6 (components, equal to the
archive); test windows 7.1 [2.1, 24.0] at 2016 and 1.25 [0.33, 4.65] at 2011; the two-year tune windows
are degenerate (separation) and are flagged. The training-versus-test difference (A4) is **not
established** at either origin — the test intervals are wide.

**Interpretation.** A plausible mechanism for the 2016 under-coverage is now supported descriptively:
the intervals are too narrow for design-derived objects, and that subgroup is scarce in the
calibration split. Nothing here is causal, and Stage 2 (which would separate value from missingness
by refitting) was not run; as specified it is blocked by the absent `kumo`/`tabm` backends.

## 3. X10 — E6 OPS-SAT branch comparison (archives only)

**Question.** Does the late fusion (`hybrid`) contribute calibration or seed stability beyond its two
branches trained alone (`cnn` on the raw fragment, `fcnn` on the engineered features)?

**Method.** Regenerated per-seed scores (five seeds, both protocols); the X2 statistical protocol
(seed-averaged scores, paired bootstrap n = 2,000 seed 0, Holm within metric over the three
contrasts); metrics AUC-PR, F1 at 0.5, Brier, ECE (10 bins). Per-seed metrics reconcile with the
regeneration's own table to 0.0.

**Results.**

| Protocol | ECE hybrid / cnn / fcnn | hybrid − cnn (Holm p) | hybrid − fcnn (Holm p) | F1 SD hybrid / cnn |
|---|---|---|---|---|
| official | 0.0099 / 0.0384 / 0.0159 | −0.026 [−0.039, −0.015] (< 0.001) | −0.003 [−0.014, +0.002] (0.19) | 0.0059 / 0.0104 |
| time-blocked | 0.0317 / 0.0541 / 0.0252 | −0.039 [−0.050, −0.014] (0.006) | +0.006 [−0.015, +0.016] (0.99) | 0.0132 / 0.0198 |

Brier: no contrast significant after Holm (closest hybrid − fcnn −0.0049, Holm 0.054, official).
Accuracy: hybrid − cnn not significant on either protocol; hybrid − fcnn AUC-PR +0.0074 (Holm 0.033)
on the official split only. Seed stability: the regenerated `cnn` F1 SD is 0.010 / 0.020, not the
0.0977 of the lost archive; the hybrid/cnn SD ratio is 0.57 / 0.67 with five-seed intervals spanning 1.

**Interpretation.** The fusion is better calibrated than the CNN branch alone, significantly, on both
protocols — but not better than the feature-MLP branch alone, which is where its calibration comes
from. The stability advantage claimed for K8 rested on one unstable archived CNN seed and is not
reproduced. K8's conditional premise is therefore **not supported**; by its own rule, K8 is not a paper.

## 4. Updated claim boundaries

| Claim | Before | Now |
|---|---|---|
| "The data used to select the alarm layer carries the H6 gain" | forbidden (five-way confound) | **available as an exploratory, Mission-1, AR(8)-specific attribution**: selection data ≈ +0.30 of +0.353; residual scale 0; pool +0.04–0.05 (below threshold); no σ interaction. Must be stated as exploratory; the grid and fit-data factors are not attributed |
| "The protocol gain is not an artefact of the residual-scale choice" | forbidden | available, same conditions |
| K8 — "late fusion contributes calibration and stability" | conditional on E6 | **not supported**; calibration gain is the feature branch's; stability claim not reproduced. K8 withdrawn as a contribution; OPS-SAT remains a benchmark chapter |
| Phase H under-coverage at 2016 | unexplained; no construction fixes it (G3′) | **descriptive mechanism**: design-derived objects under-covered at both origins; subgroup 3.8× under-represented in the 2016 calibration split. Not causal; Stage 2 not run |
| Missingness→outcome stability (A4) | untested | not established (wide test-window intervals) |

## 5. Documentation corrections

`PHASE8_GATE_ADDENDUM_2026-11-08.md`: X3 is ~30 min CPU and not refit-free (caches lost), X10 is
minutes with no training, X6 Stage 2 and twin-state regeneration are BLOCKED as specified
(`kumo`/`tabm` absent); `statsmodels` absent. The original gate record and its hash are unchanged.

## 6. Tests and integrity

Protected artifacts verified before and after execution (28/28 frozen; original freeze 27/28 with the
expected pre-registration-document difference; G5d; 107/107 figure-release files; 10/10 OPS-SAT
archive; twin digests; accepted gate record hashes `83b1150215020e0e…` / `86ae2e8c828e3e18…`); HEAD
`78ee339` unchanged, nothing staged. Confirmatory verdicts untouched (CONFIRMATORY.json sha
`fc2223d6ffe23881…`). New regression tests: `tests/test_track3b_stage2.py` (3),
`tests/test_am_design_stage1.py` (4), `tests/test_e6_branch.py` (4). Full-suite result:
`outputs/audit/pytest_full_20261108_after_x4_x6_x10.log`.

## 7. Files created or modified

Listed with hashes in `outputs/audit/phase8_approved_analyses_manifest.json`. Created: five scripts
(`verify_protected_artifacts.py`, `e6_opssat_branch_analysis.py`, `am_design_stage1.py`,
`cluster_logit.py`, `track3b_stage2_cells.py`, `phase8_approved_analyses_manifest.py`), three tests,
this report, the addendum, and the output directories `outputs/e6_opssat_branch/`,
`outputs/am_design_stage1/`, `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/`. Modified living
documents: `MASTER_COMPLETION_TRACKER.md`, `PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md`.

## 8. Remaining limitations

X4 is partial (two protocol gaps) and exploratory; X6 is descriptive, Stage 2 blocked; X10 uses
separately trained branches, five seeds, and a CNN that is not seed-reproducible; `statsmodels`,
`kumo`, `tabm`, `tabicl`, `lightgbm`, `catboost` are absent from the environment; the regenerated
OOF arrays (3.4 GB) sit under an ignored pattern and will be lost again unless an exception is added
(not done — a repository decision).

## 9. Next engineering tasks for the working COSMOS-AI demonstration

1. Add `.gitignore` exceptions (or an explicit archive step) for `track3b_stage2/oof_regen/*.npy` and
   any future score caches, so that re-selection studies stop needing regeneration.
2. Decide the two 3b protocol gaps (how A0's model would supply a half pool; how cross-fitting works
   with a calibration-window pool) if the remaining Stage 2 cells are wanted.
3. Console: display A/M source alongside each lifetime interval and flag design-derived objects as
   under-covered (an evidence-quality cue, not a recalibration), reading the X6 Stage 1 artifact.
4. Record the K8 withdrawal in the OPS-SAT console screen text ("calibration from the feature branch").
5. Persist fitted lifetime/conjunction models in future runs so prediction-time robustness studies
   become possible (currently only predictions are archived).
