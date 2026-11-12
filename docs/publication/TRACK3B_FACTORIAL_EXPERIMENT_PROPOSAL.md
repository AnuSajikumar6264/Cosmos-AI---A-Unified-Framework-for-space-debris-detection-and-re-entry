# Track 3b — factorial experiment proposal

Date 2026-11-05 · **PROPOSAL ONLY. Nothing executed. Awaiting your explicit approval.**
**The pre-registered A0/A1 protocol, its freeze and its verdicts are unmodified and will remain so.**

---

## 1. The problem 3b solves

H6 establishes that protocol A1 beats protocol A0 on Mission 1 at full channel scale by
**+0.353 [+0.206, +0.488]**, Holm p = 0.0015. It establishes nothing about *why*, because A0 and A1
differ in **five** respects at once.

Without 3b the paper can say *"this protocol beats that protocol"*. With 3b it could say
*"the data used to select the alarm layer is what matters"* — a transferable finding rather than a
configuration report.

## 2. The five factors and their levels

From the independent code audit (`STAGE1_AUDIT.md` §5.1). Note the thesis and deviation log record
four; the audit found the fifth.

| # | Factor | Level **−** (as in A0) | Level **+** (as in A1) | Isolable? |
|---|---|---|---|---|
| **F1** | Forecaster fit data | `fit` period only; nominal check on the target and lag 8 (`forecasting.py:288`) | all nominal training samples, all 8 lags nominal (`oof.py:52–55, 114`) | requires refit |
| **F2** | **Residual scale σ** | out-of-sample residuals on the 3-month `es` period (`forecasting.py:391–393`) | in-sample residuals over the whole training half; per-fold in-sample σ for OOF scores (`oof.py:112–115`) | requires refit |
| **F3** | Calibration pool | 792,000 rows from the 9 months before test, **from the model that scores test** (`oof_benchmark.py:293–296`) | **7,364,161** OOF rows from five fold models with different σ, while test scores come from the full-fit model (`oof_benchmark.py:238–240`) | requires refit |
| **F4** | **Selection data** | **9 M1 events** (7 anomalies, 2 rare) | **105 M1 events** (+4 gaps) | **re-selection only — no refit** |
| **F5** | Selection grid | {1e-2, 1e-3, 3e-4, 1e-4} × {1, 3, 10, 30} (`alarms.py:139–142`) | {1e-2 … 1e-5} × {1, 3, 10, 30, 100} (`oof_benchmark.py:54–57`) | **re-selection only — no refit** |

**Magnitudes worth noting.** F2's per-channel score ratio has median 1.007 but ranges **0.52–4.70**,
and **37 of 58 M1 channels sit at the σ floor** — so F2 is not a cosmetic difference. F3 bundles a
**9.3× pool-size change** *with* a model mismatch (fold models vs full-fit model); strictly it is
two sub-factors, and I treat it as one with that caveat recorded.

## 3. Design

### 3.1 Recommended: 2⁵⁻² fractional factorial, resolution III → augmented

| Option | Runs | Estimates | Verdict |
|---|---|---|---|
| Full 2⁵ | **32** | all main effects + all interactions | Scientifically ideal, **too expensive** |
| **2⁵⁻¹ (resolution V)** | **16** | all 5 main effects, all 10 two-factor interactions, unconfounded | **RECOMMENDED** |
| 2⁵⁻² (resolution III) | 8 | 5 main effects, **confounded with two-factor interactions** | Cheap but main effects are aliased — risky given F3 is itself composite |
| **Staged: 4 + 12** | **16 total** | cheap factors first, then the expensive block | **RECOMMENDED SEQUENCING** |

**I recommend a 2⁵⁻¹ resolution-V design in 16 runs, executed in two stages.**

Resolution III is tempting at 8 runs, but with five factors each main effect is aliased with a
two-factor interaction. Given that F3 already bundles two mechanisms and F2 varies by up to 4.7×
per channel, interactions are plausible, and an aliased result would not support the attribution
claim the experiment exists to make. **8 runs would risk producing a confident wrong answer.**

### 3.2 Stage 1 — the two free factors (4 runs, no refitting)

F4 and F5 are **selection-only**: they change which operating point is chosen, not the scores.
With the frozen scores already archived, a 2² design over F4 × F5 is a **re-selection**, not a
refit.

| Run | F4 selection data | F5 grid |
|---|---|---|
| S1 | 9 events | A0 grid |
| S2 | 9 events | A1 grid |
| S3 | 105 events | A0 grid |
| S4 | 105 events | A1 grid |

**Cost: minutes of CPU.** S1 should reproduce A0's selected operating point and S4 A1's — a
built-in validity check on the whole design.

**This stage alone may settle the question.** The project's existing one-factor-at-a-time
decomposition attributed the effect to F4. If Stage 1 shows F4's main effect accounts for most of
+0.353 with F5 negligible and no F4×F5 interaction, the attribution is substantially established
for the two factors that do not require refitting — and Stage 2 becomes a confirmation rather than
a necessity.

### 3.3 Stage 2 — the three expensive factors (12 further runs)

Conditional on Stage 1. A 2³ design over F1 × F2 × F3 at each of the two F4 levels, reusing F5 at
the A1 level: **8 + 4 = 12 runs**, completing a resolution-V picture across all five factors.

## 4. Runs, cost and feasibility

| Item | Estimate |
|---|---|
| Stage 1 runs | **4**, re-selection only |
| Stage 1 cost | **minutes of CPU**; no GPU; no refit |
| Stage 2 runs | **12** AR(8) fits + OOF scoring over the M1 training half |
| Stage 2 cost | AR(8) ridge, horizon 16, K = 5 blocks over 58 channels. The pre-registration records that a sequential pass over ~20 arms takes **5–6 h**, so 12 runs ≈ **3–4 h wall-clock** with the existing parallel driver |
| Backends required | `numpy`/`scipy` only for AR(8) — **no unavailable backend**. Deliberately excludes A2/A3, which need XGBoost (available) and torch (available) but add seed variance |
| Storage | < 5 GB |
| **Feasibility** | **HIGH.** The frozen code reproduces saved A0 and A1 alarms **bit for bit**, so the pipeline is known to be deterministic and re-runnable |

## 5. Estimable effects

**Under 2⁵⁻¹ resolution V (16 runs):**

| Estimable | Count |
|---|---|
| Main effects F1…F5 | 5, unconfounded |
| Two-factor interactions | all 10, unconfounded with main effects |
| Three-factor and higher | aliased — assumed negligible |

**Interactions of specific scientific interest:**

- **F2 × F3** — residual scale and calibration pool. A1's OOF pool is built from fold models with
  *different* σ while test scores come from the full-fit model. If these interact, the A1
  configuration is internally inconsistent in a way that matters, which would be a finding in its
  own right.
- **F3 × F4** — pool size and selection-data size. Both scale with "use more of the training half",
  so they are the most likely pair to interact and the hardest to disentangle conceptually.
- **F4 × F5** — selection data and grid. A finer grid may only help when there are enough events to
  select on. Estimable **free** in Stage 1.

## 6. Statistical analysis

| Element | Specification |
|---|---|
| Response | Corrected event-wise F0.5, **anomaly-and-rare** (primary, matching the pre-registration) and **anomaly-only** (secondary), via the vendored official metric |
| Effect estimation | Standard factorial contrasts on the 16-run design |
| Uncertainty | **Paired bootstrap with fixed 30-day blocks** (86 on M1), matching the pre-registered procedure, B = 2,000 |
| Multiplicity | **Holm** across the 5 main effects; interactions reported descriptively without correction, and labelled as such |
| Pre-declared threshold | **+0.05**, the same minimum effect as the pre-registration, so results are comparable to H6 |
| Validity check | S1 must reproduce A0's operating point and S4 A1's. **If they do not, the design is invalid and must not be interpreted** |
| Reporting | Effect size with CI for every factor; an explicit statement of which fraction of +0.353 is attributed |

## 7. Confounding and threats

| # | Threat | Mitigation |
|---|---|---|
| 1 | **F3 is composite** — pool size *and* model mismatch | Report as one factor with the caveat stated. A follow-up could split it; do not claim it is a single mechanism |
| 2 | **Test-half exposure.** Both M1 test halves were already scored in 128 configuration–layer combinations | **3b cannot be confirmatory.** Label it **exploratory** throughout. Do not pre-register it as a confirmatory test on a seen fold |
| 3 | Deep/tree arms excluded | Deliberate — keeps the design to one deterministic scorer and avoids ±0.1 seed variance swamping a +0.05 threshold. **The attribution will therefore be about the AR(8) protocol only** |
| 4 | Single mission, single channel set | M2 cannot support it (6 anomalies; every learned arm at 0.0000 anomaly-only). **The attribution will be Mission-1-specific** |
| 5 | Bootstrap is an approximation of the official metric | Already characterised: exact for A1; differences change no verdict. Report point estimates from the official metric and intervals from the re-implementation, as the pre-registration does |
| 6 | Multiplicity across 5 main effects + 10 interactions | Holm on main effects; interactions descriptive. **Do not** declare a significant interaction without correction |
| 7 | Re-running frozen code could alter frozen outputs | **Write to a new directory. Do not touch `oof_protocol/`.** Verify the freeze hash before and after |

## 8. What becomes possible if 3b succeeds

| Claim | Currently | After 3b |
|---|---|---|
| "Selecting the alarm layer on more labelled training events is what improves detection" | **Forbidden** | **Available**, with an effect size and CI, if F4 carries the effect |
| "Pool size and residual-scale choices are second-order" | Forbidden | Available if F2, F3 are small |
| "The protocol gain is not an artifact of the finer grid" | Forbidden | **Available free from Stage 1** |
| Title claim *"alarm-layer selection matters more than model capacity"* | Compatible only with heavy conditioning | **Defensible**, conditioned on Mission 1 and the AR(8) scorer |
| A transferable design recommendation for practitioners | Not available | **Available** — the paper could tell a reader which part of the protocol to spend effort on |

## 9. What remains impossible without 3b

| Claim | Status without 3b |
|---|---|
| Any attribution of H6 to a mechanism | **Impossible.** Five simultaneous differences |
| *"Alarm-layer selection matters more than model capacity"* as a general claim | **Impossible** — it conflates five protocol changes with the scorer comparison |
| A practitioner-facing recommendation about *what to do* | **Impossible.** The paper can only report that one whole configuration beat another |
| Rebutting *"you changed five things at once"* | **Impossible.** It is disclosed and unanswered |

**What survives without 3b** (and this matters, because it means 3b is not existential): H6 as a
protocol comparison; H4/H5's pre-registered refutations, both metric-robust; the alarm-layer
dominance result (~3 orders of magnitude, archived); the point-level ACI failure with its visible
mechanism (176,337 false alarms/year at 92.7 % recall); the Mission 2 saturation characterisation;
and the 21× cross-fitting optimism on lightweight M1.

## 10. Is 3b essential or optional?

**Optional for publication. Essential for the strongest version of the paper.**

- **Without 3b** the paper is a careful pre-registered protocol comparison with a negative
  deep-learning result and a well-evidenced alarm-layer finding. **Publishable**, with the
  five-way confound disclosed as a stated limitation.
- **With 3b** it becomes a paper with an attributed mechanism and a transferable recommendation.

**My assessment: Stage 1 is close to free and should be approved regardless.** It may resolve the
attribution for the two factors that need no refitting, and it provides the design's own validity
check. **Stage 2 should be decided after Stage 1's result**, because if F4's main effect dominates
in Stage 1 the expensive block becomes a confirmation rather than a necessity.

## 11. Approval requested

| Item | Cost | Request |
|---|---|---|
| **Stage 1** — 2² over F4 × F5, re-selection only, new output directory | **minutes of CPU** | **Approval requested** |
| **Stage 2** — 2³ over F1 × F2 × F3 at two F4 levels, 12 runs | **3–4 h wall-clock** | **Approval deferred** pending Stage 1 |

**Nothing will run until you approve. The frozen protocol, its hashes and its verdicts will not be
touched; all output goes to a new directory, and the freeze hash will be verified before and
after.**
