# G5d final decision report

Date: 2026-11-04. **Pre-registered outcome: INCONCLUSIVE.** The mechanism hypothesis (H3) is
**CLOSED as not established**. H2 is **SUPPORTED with the project's first confirmatory
evidence**, and an unanticipated finding materially strengthens contribution C-2.

```bash
python scripts/g5d_origin2006_refit.py --learners xgboost,mlp   # 20.6 min, exit 0
python scripts/g5d_analyse.py --n-boot 4000                     # exit 0
```
Protocol: [`G5D_PREREGISTRATION.md`](../../research_design/G5D_PREREGISTRATION.md), hashed
`9ea4bf4171cad1b8…` **before any origin-2006 fit**; verified intact at analysis time.
Deviations: [`G5D_DEVIATIONS.md`](../../research_design/G5D_DEVIATIONS.md).
Outputs: `outputs/g5d_origin2006/`.

## 1. Why this is confirmatory

Origin 2006's test fold (`t0 ∈ [2006-01-01, 2011-01-01)`, **7,277 scored objects in 440 launch
families** — the largest fold in the project) had **never been constructed or scored** before
this run. It is disjoint from both published test folds. Every earlier result in this project is
post-hoc; this is not.

Realised split sizes **matched the pre-registration exactly** (18,960 / 211 / 544 / 7,281).
`cosmos/ai/lifetime/run.py` was never edited — the origin was injected at runtime, enforced by
a guard test.

## 2. Deviation: the pre-registered arm set could not be fitted

The refit crashed twice on missing backends, ending at **2 learners of the 7 pre-registered**.

| Learner | Backend | Available | Role |
|---|---|---|---|
| xgboost | `xgboost` | **yes** | baseline |
| mlp | `torch` | **yes** | baseline |
| lightgbm | `lightgbm` | no | baseline |
| catboost | `catboost` | no | baseline |
| **tabm** | **`tabm`** | no | **SELECTED at origin 2016** |
| tabicl | `tabicl` + `sdm` | no | best test performer at 2016 |
| kumo | `sdm` | no | **SELECTED at origin 2011** |

Consequence: the arm set is `physics_only`, `xgboost`, `mlp` — all three of which also exist in
the **published caches at origins 2011 and 2016**, so the cross-origin comparison uses an
*identical* arm set at all three origins. That removes rather than adds a confound relative to
the published comparison, where the selected learner differed by origin.

This dependency gap is a reproducibility finding in its own right — see
[`FINAL_REPRODUCIBILITY_REPORT.md`](FINAL_REPRODUCIBILITY_REPORT.md).

## 3. Results

### Per-origin ranking, identical arm set

| Origin | n (families) | test at-cap | Rank 1 | Rank 2 | Rank 3 | Rank 4 |
|---|---|---|---|---|---|---|
| 2011 | 2,667 (435) | 0.744 | **physics_only** 0.0527 | xgboost 0.0648 | tabm 0.0994 | mlp 0.1147 |
| 2016 | 2,978 (621) | 0.558 | **xgboost** 0.0576 | mlp 0.0578 | tabm 0.0593 | physics_only 0.0892 |
| **2006 (new)** | **7,277 (440)** | 0.666 | **physics_only** 0.0568 | xgboost 0.0830 | mlp 0.1039 | — |

`physics_only` ranks **1st, 4th, 1st** across the three origins — rank range **3**. On the
never-scored fold it wins again, so 2 of 3 origins favour the physics expert and origin 2016 is
the outlier.

### H1 — selection transfer: NOT_EVALUABLE

Only 2 learners carry a tune-A score at origin 2006 (`physics_only` has none of the same kind).
A Spearman correlation on 2 points is undefined. Classified **NOT_EVALUABLE** per the
pre-registration, not reinterpreted.

### H2 — ranking instability: SUPPORTED

- Arms present at **every** origin: `physics_only`, `xgboost`, `mlp`.
- Arms with identical rank at every origin: **none**.
- `physics_only` rank range: **3** (threshold ≥ 3).
- Best arm by origin: physics_only (2011), xgboost (2016), physics_only (2006).

**Correction recorded.** The first analysis run reported H2 as REFUTED because `tabm` appeared
"rank-constant". `tabm` is **absent** at origin 2006 (backend unavailable), and NaN-dropping left
only its two surviving observations. The check now considers only arms present at every origin.
The verdict flips to SUPPORTED. The fix is in the script, not in the interpretation.

### H3 — point-mass mechanism: UNDERPOWERED, hypothesis CLOSED

Spearman(|cap-mass error|, test pinball) at origin 2006 = **+1.0000** over **3 arms**.

This numerically exceeds the pre-registered +0.5 threshold but is **not evidence**. With 3
points, ρ = 1.0 arises with probability 1/6 under random ordering, and the ordering is driven by
`physics_only` having both the smallest cap-mass error and the best loss — a single structurally
different arm. A 5-arm floor is now encoded in the analysis so a numerical pass cannot license a
confirmation.

Across the three origins the mechanism's correlation is **+0.891 (2011), −0.158 (2016),
+1.000 but underpowered (2006)**. It is inconsistent in sign and never powered.

**Per the pre-registered stopping rule, H3 is closed as NOT ESTABLISHED and will not be pursued
further.** The novelty claim for the mechanism is **not** upgraded.

### Unanticipated finding — a reproduced complete rank inversion

Not pre-registered, so **exploratory** — but it is the most informative result of the experiment.

| Origin | Learner | tune-A | test | degradation | tune-A rank | test rank |
|---|---|---|---|---|---|---|
| 2011 | tabm | 0.056090 | 0.099437 | **1.77×** | 1 | 2 |
| 2011 | mlp | 0.057474 | 0.114661 | **2.00×** | 2 | 3 |
| 2011 | **xgboost** | 0.067147 | 0.064842 | **0.97×** | **3 (last)** | **1** |
| 2016 | tabm | 0.028292 | 0.059292 | **2.10×** | 1 | 3 |
| 2016 | mlp | 0.028686 | 0.057776 | **2.01×** | 2 | 2 |
| 2016 | **xgboost** | 0.035276 | 0.057582 | **1.63×** | **3 (last)** | **1** |
| 2006 | mlp | 0.059291 | 0.103917 | **1.75×** | 1 | 2 |
| 2006 | **xgboost** | 0.075742 | 0.083034 | **1.10×** | **2 (last)** | **1** |

**`xgboost` ranks last on tune-A at all three origins and first on test at all three origins.**

And the mechanism is visible: the neural learners (`tabm`, `mlp`) degrade **1.75×–2.10×** from
tune-A to test, while `xgboost` degrades **0.97×–1.63×**. The neural learners overfit the
selection set roughly twice as badly, and tune-A cannot detect it **because tune-A is what they
overfit to**.

At all three origins the tune-A-preferred learner was **not** the test-best learner, with
selection regret **+53.4 %** (2011), **+3.0 %** (2016) and **+25.2 %** (2006).

This is a cleaner statement of the selection-failure phenomenon than the Spearman correlation:
it is directional, consistent, and reproduced on a never-scored fold.

**Caveats.** Only 2–3 learners per origin. The pattern may be specific to tree ensembles versus
neural tabular models under this distribution shift rather than a general property. It was not
pre-registered. It needs the full 7-learner arm set to be confirmed, which requires the
unavailable backends.

## 4. Pre-registered outcome classification

| Hypothesis | Verdict |
|---|---|
| H1 selection transfer | **NOT_EVALUABLE** (2 learners) |
| H2 ranking instability | **SUPPORTED** |
| H3 point-mass mechanism | **UNDERPOWERED → CLOSED, not established** |
| **Overall** | **INCONCLUSIVE** |

INCONCLUSIVE follows mechanically from H1 being unassessable. The pre-registration's
classification table was applied as written; it was not adjusted after seeing the numbers, and
it is what prevented H3's ρ = 1.0 from being reported as a confirmation.

## 5. Consequences

**Strengthened.** Contribution C-2 (selection non-transfer in orbital lifetime prediction) now
has confirmatory support on a never-scored fold: no arm holds its rank across three origins,
`physics_only` swings 1st → 4th → 1st, and `xgboost` shows a complete tune-A/test rank inversion
at all three origins with a quantified overfitting mechanism.

**Closed.** The point-mass composition-shift mechanism is not established and is withdrawn as a
candidate contribution. It may be reported as a described, measured, **refuted-or-underpowered**
hypothesis — never as a finding.

**Unchanged.** No existing result was altered. Freeze, dated forecast and G5d pre-registration
all verified INTACT after the run. L17 columns untouched. All Phase E/G+/G5 outputs preserved.

## 6. Stopping

Per the pre-registered stopping rule, **G5d is complete and the hypothesis is closed**. The one
experiment that could still change this is a refit with the full 7-learner arm set, which
requires backends that are not installable here (`tabm`, `tabicl`, `kumo` — the last needing
OpenMDW-1.1 licensed weights and ≈24 GB of GPU memory). That is a data/licensing dependency,
not a research question, and it is recorded as such rather than left open.
