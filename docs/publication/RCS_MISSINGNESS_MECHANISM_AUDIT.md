# RCS missingness mechanism audit

Date 2026-11-05 · read-only inspection · no artifact modified

**Headline: the project handled this correctly, and my earlier concern was largely unfounded.
`rcs_m2` was never a feature of any evaluated model. One secondary pathway remains and is worth
disclosing.**

Inspected: `outputs/benchmarks/reentry_lifetime/leak_check.json`, `cosmos/ai/lifetime/leak_check.py`,
`cosmos/ai/lifetime/catalogue.py`, `cosmos/ai/lifetime/models.py`, `cosmos/ai/lifetime/run.py`,
`cosmos/ai/lifetime/physics.py`, `docs/RESULTS_AND_ANALYSIS.md`, the archived `test_predictions.npz`
for both published origins, and `regression_test.csv` for both.

---

## 1. Your seven questions, answered

### Q1 — Was `rcs_m2` retained in the actual evaluated model runs?

**No.** The feature set is defined at `run.py:51`:

```python
FULL = ("orbit", "age", "design", "space_weather", "family", "physics", "class")
```

`rcs` is **not** in `FULL`. It exists as a separate group, `NUMERIC["rcs"] = ["log_rcs"]`
(`models.py:24`), carrying the inline comment:

> `# 2026 snapshot; availability depends on the outcome (leak demonstration only)`

and it enters only through one ablation (`run.py:56`):

```python
ABLATIONS["plus_rcs_2026"] = FULL + ("rcs",)
```

with the preceding comment (`run.py:52–55`):

> *"'plus_rcs_2026' adds the radar cross-section of the 2026 catalogue snapshot, whose
> availability depends on the outcome: a labelled leak demonstration, **never a candidate for
> selection**"*

### Q2 — Was it removed before the final deployed model?

**It was never in it.** The deployed `cosmos_gated` fuses arms drawn from the selection pool
`{tabm, tabicl, kumo}`, all of which use `FULL`. No `plus_rcs` arm is in any selection pool at any
origin.

**One secondary pathway does exist and should be disclosed.** The physics expert derives a
class-level size prior from RCS (`physics.py:325–338`):

```python
def class_prior_from(train: pd.DataFrame, min_n: int = 50) -> dict:
    """Training-set pools per object class: radar-derived characteristic length L_c [m] ..."""
    lc = np.sqrt(4 * train["rcs_m2"] / np.pi)
```

This is **training objects only**, pooled **per object class**, used only for fragments and
components lacking design values, requiring ≥ 50 members per class. No test object's own RCS is
used. That is a defensible design.

The residual issue is second-order but real: because RCS availability depends on how long an
object survived, the training pool over-represents longer-lived objects of each class. The size
prior is therefore conditioned on survival — a survivorship-style selection effect in the prior,
not target leakage. **It affects `physics_only` specifically**, which matters because
`physics_only` is the arm that ranks 1st of 19 at origin 2011 and 19th of 19 at origin 2016.

### Q3 — Which exact runs used it?

| Run | Origin | Role |
|---|---|---|
| `kumo_plus_rcs_2026` | 2011 | labelled leak demonstration |
| `tabm_plus_rcs_2026` | 2016 | labelled leak demonstration |
| `mlp_plus_rcs_2026` | 2006 | labelled leak demonstration |
| `physics_only` (and every arm using physics features) | all | class-level size prior, train-only (Q2) |

Ablation arms are refitted with the best learner's tuned settings and are explicitly excluded from
selection.

### Q4 — Target leakage, temporal leakage, non-causal availability, or a combination?

**Primarily non-causal feature availability, with a temporal component. It is not target leakage in
the strict sense, and it is not present in the evaluated models.**

| Mechanism | Present? | Reasoning |
|---|---|---|
| **Target leakage** (the label or a function of it enters features) | **No** | `rcs_m2` is a physical measurement, not a function of the decay label |
| **Non-causal feature availability** (*informative missingness*) | **Yes — the dominant mechanism** | Whether a value was ever published depends on how long the object stayed in orbit. `catalogue.py:17–21` states this. Adjusted OR for 30-day decay given missing RCS: **3.594 [2.094, 6.169]** at origin 2016 and **3.625 [2.076, 6.327]** at 2011, cluster-robust by launch family |
| **Temporal leakage / non-stationarity** | **Yes — compounding** | The missingness rate is wildly non-stationary across splits: 27.1 % → 1.7 % → **68.2 %** (train → tuneB → test) at origin 2016; 32.4 % → 9.9 % → **1.9 %** at 2011. `share_rcs_missing_t0_from_2018 = 0.9995` at origin 2016 test — objects catalogued from 2018 essentially never have published RCS |
| **Duplicate or entity leakage** | No | Separately verified: 0 launch families straddle tune-A/tune-B; 0 objects shared across test folds |

The parallel check on design area-to-mass missingness gives OR 3.437 [2.638, 4.477] (2016) and
3.594 [2.766, 4.670] (2011) — the same mechanism in a second covariate, and `am_design` **is** in
`FULL` via the `design` group. **That is the pathway that remains in the evaluated models**, and it
is the one the paper must discuss. The project tracks it: `run.py` records
`am_source_{train,tuneA,tuneB,test}` and `test_weight_by_am_source`.

### Q5 — Does the ablation establish a causal mechanism, or only an association?

**Stronger than association, weaker than an established mechanism.**

It is a genuine **interventional contrast**: the covariate group is added while the learner and its
tuned hyperparameters are held fixed. That is a manipulation, not an observation, so it supports a
causal claim *about the effect of adding this covariate in this pipeline*.

What it does **not** establish:

- **n = 2 origins.** Two interventional observations.
- **No dose–response.** The missingness rate is not varied systematically; it is whatever each
  origin's catalogue gives.
- **Confounded with origin.** The learner differs between origins (`kumo` at 2011, `tabm` at
  2016), so "adding RCS" and "changing learner and origin" move together.
- **The mechanism is inferred, not measured.** That coverage breaks *because* the
  availability–outcome association shifts is a plausible and well-motivated reading, but no
  experiment isolates the association shift from the rate shift.

### Q6 — Can the calibration reversal and interval-width change be reproduced from saved predictions?

**Yes, and I did.** Computed directly from the archived per-object quantile matrices
(`test_predictions.npz`), using `QUANTILES = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]`, taking the
80 % interval as [q0.10, q0.90] and the 90 % interval as [q0.05, q0.95]:

| Origin | Test missingness | Arm | 80 % coverage | 80 % width | 90 % coverage | 90 % width |
|---|---|---|---|---|---|---|
| **2011** | 1.9 % | `kumo` | 0.9209 | 0.9436 | 0.9580 | 1.3244 |
| **2011** | 1.9 % | `kumo_plus_rcs_2026` | 0.9265 | **0.8006** | 0.9580 | **1.1401** |
| **2016** | 68.2 % | `tabm` | 0.6749 | 0.3477 | 0.8083 | 0.5239 |
| **2016** | 68.2 % | `tabm_plus_rcs_2026` | **0.5769** | 0.3952 | **0.6891** | 0.5937 |

**The documented effect reproduces, and its direction tracks the test missingness rate:**

- **Origin 2011** (covariate mostly *present* in test, matching training): coverage essentially
  unchanged (0.921 → 0.927 at 80 %), **width shrinks 15 %** (0.944 → 0.801). The leak buys genuine
  sharpening at equal coverage — which is why pinball improves and the arm moves from rank 9 to
  rank **3** of 19.
- **Origin 2016** (covariate mostly *absent* in test, breaking the training association):
  coverage **collapses** by **−9.8 pp** at 80 % (0.675 → 0.577) and **−11.9 pp** at 90 %
  (0.808 → 0.689), while width *increases*. Strictly worse on both axes — the arm falls from rank
  6 to rank **16** of 19.

**One honest discrepancy.** `docs/RESULTS_AND_ANALYSIS.md` reports the origin-2016 90 % coverage
falling "from 87.7 % to 76.8 %". My figures are 80.8 % → 68.9 %. The **drop magnitude agrees**
(−10.9 pp documented vs **−11.9 pp** measured), but the absolute levels differ by about 7 pp,
because the archived arrays are **raw learner quantiles** while the documented figures are
**post-conformal** (Mondrian CQR). The effect replicates; the calibration stage differs. This must
be stated if the numbers are published.

### Q7 — Does this justify a separate scientific research question?

**Yes — and in my assessment it is a stronger and more defensible research question than the
"temporal distribution shift" framing I previously proposed.**

Proposed question:

> When a covariate's **availability** depends on the outcome, and the availability rate is
> non-stationary across deployment periods, what does including it do to a predictive model's
> **sharpness** and **calibration** — and does accuracy-based model selection detect the harm?

Why it is strong:

1. **It has an identified mechanism**, not just a correlation: informative missingness with a
   non-stationary rate.
2. **It has an interventional test** already run, with a **sign reversal** between origins that
   the mechanism predicts.
3. **It is operationally important and under-reported.** Catalogue-derived covariates whose
   presence depends on object fate are common in space-situational-awareness datasets; the field
   does not routinely audit them.
4. **It explains a failure that accuracy metrics miss.** The project's own ablation found the
   effect on point accuracy "not detectable" while coverage moved by ~11 pp — so a practitioner
   selecting on accuracy would ship the harmful covariate. That connects directly to the
   project's selection-validity theme.
5. **The analysis apparatus already exists** (`leak_check.py` with cluster-robust ORs).

**What it would need to become publishable:** a dose–response design (vary the test missingness
rate systematically on a held-fixed learner and origin), and separation of the *association* shift
from the *rate* shift. Both are feasible from archived predictions plus controlled resampling.

## 2. Explicit limitation — I am not claiming this explains the calibration failure

Per your instruction. The Phase H calibration failure is:

| Origin | Nominal | Observed | Verdict |
|---|---|---|---|
| 2016 | 80 % | 0.71692 | UNDER-COVERS (p = 0.0415) |
| 2016 | 90 % | 0.87408 | consistent (p = 0.4095) |
| 2011 | 80 % | 0.92313 | OVER-COVERS (p = 0.0) |
| 2011 | 90 % | 0.95913 | OVER-COVERS (p = 0.0) |

These are for `cosmos_gated`, which **does not use RCS**. So RCS missingness **cannot** be the
cause of the deployed model's miscalibration. What the ablation shows is that *adding* an
outcome-dependent covariate *worsens* coverage in the same direction the deployed model already
fails — consistent with, but not demonstrative of, a shared mechanism.

The `am_design` missingness pathway (OR ≈ 3.4–3.6) **is** in the deployed feature set and is the
candidate worth investigating. **It has not been ablated.** That is a specific, testable gap.

## 3. Assessment of the project's handling

| Aspect | Assessment |
|---|---|
| Identified the pathway | **Yes**, with cluster-robust adjusted odds ratios |
| Documented it in code | **Yes** — `catalogue.py:17–21` and `models.py:24` both state it explicitly |
| Excluded it from the feature set | **Yes** — `rcs` absent from `FULL` |
| Excluded it from selection | **Yes** — "never a candidate for selection" |
| Quantified the harm by intervention | **Yes** — the `plus_rcs_2026` arms |
| Reported the result honestly | **Yes** — including that point accuracy showed no detectable effect |
| **Gap: the analogous `am_design` pathway, which IS in the feature set, is not ablated** | **No** |
| **Gap: none of this appears in the current manuscript** | **No** |

This is good scientific practice that is currently invisible to a reader. It should be in the
paper — both because it is a genuine contribution and because a reviewer who finds
`leak_check.json` independently will ask why it was not mentioned.
