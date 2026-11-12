# am_design missingness — exploratory ablation protocol

Date 2026-11-05 · **PROPOSAL ONLY. Nothing has been run. Awaiting your approval.**
**Explicitly exploratory. This does not touch, extend or reinterpret any pre-registered
experiment, and it has no bearing on the ESA-ADB pre-registration or its verdicts.**

---

## 1. Why this is worth doing — the evidence

### 1.1 The covariate is in the deployed feature set

`models.py:23`: `NUMERIC["design"] = ["log_mass", "length", "diameter", "span",
"log_area_design", "log_am_design", "mass_uncertain"]`, and `run.py:51`
`FULL = ("orbit", "age", "design", "space_weather", "family", "physics", "class")`.

**`log_am_design` is in `FULL`, unlike `log_rcs`.** So unlike the RCS pathway — which was
confined to a labelled leak-demonstration arm — this one is in every published learned arm and in
the deployed `cosmos_gated` fusion.

### 1.2 Missingness is outcome-associated

From `leak_check.json`, `components_adjusted_or_design_missing`, cluster-robust by launch family:

| Origin | Adjusted OR for 30-day decay given design-A/M missing | 95 % CI | n | clusters |
|---|---|---|---|---|
| 2016 | **3.437** | [2.638, 4.477] | 6,226 | 2,165 |
| 2011 | **3.594** | [2.766, 4.670] | 5,915 | 2,039 |

Both intervals exclude 1 comfortably.

### 1.3 Availability is non-stationary across splits — and tune-B is the calibration set

From each origin's `summary.json`, `am_source_{train,tuneB,test}`:

| Origin | Split | `design`-derived | `class_prior_sbm` | **design share** |
|---|---|---|---|---|
| **2016** | train | 6,805 | 18,566 | **26.8 %** |
| **2016** | **tuneB (conformal calibration)** | 92 | 1,468 | **5.9 %** |
| **2016** | test | 670 | 2,323 | **22.4 %** |
| 2011 | train | 6,374 | 14,437 | 30.6 % |
| 2011 | **tuneB** | 73 | 259 | **22.0 %** |
| 2011 | test | 417 | 2,263 | 15.6 % |

**At origin 2016 the conformal calibration split contains 5.9 % design-derived objects while the
test split contains 22.4 % — a 3.8× under-representation.** At origin 2011 the mismatch is mild
(22.0 % vs 15.6 %).

**This is a candidate mechanism for the Phase H coverage failure**, which is *also* specific to
origin 2016 (80 % nominal → 0.71692 observed, UNDER-COVERS, p = 0.0415) while origin 2011
over-covers. A conformal correction calibrated on a population with a different
covariate-availability mix than the test population would be expected to miscalibrate. **This is
a hypothesis, not a finding** — nothing currently tests it.

### 1.4 Missingness is implicitly exploitable, through two different routes

- **Learners:** `design_matrix` docstring states *"NaN kept: all learners handle it"*. Tree
  learners (XGBoost, LightGBM, CatBoost) learn a default branch direction for NaN, so missingness
  is directly usable as a signal without any explicit indicator.
- **Physics expert:** when `am_design` is missing it **falls back to a class prior**
  (`am_source = class_prior_sbm`), and that prior's pool is **RCS-derived**
  (`physics.py:328–334`), inheriting the RCS availability–outcome association documented
  separately.

So two distinct pathways carry missingness into predictions, and they would need separating.

### 1.5 What the existing `no_design` ablation does and does not show

`no_design` removes the **entire seven-feature design group**. Results:

| Origin | Base arm | `*_no_design` | Effect |
|---|---|---|---|
| 2016 | `tabm` 0.059292 (rank 6) | 0.066357 (rank 15) | removing design **hurts** (+0.00706, BH q < 0.00025) |
| 2011 | `kumo` 0.061613 (rank 9) | 0.062437 (rank 11) | slight hurt (+0.00082, q = 0.1925, **not significant**) |

**It cannot answer this question.** It conflates seven features, does not isolate `log_am_design`,
does not separate value from missingness, and (per the earlier audit) the ablation arms are
**untuned**, inheriting their parent's hyperparameters — which biases ablations towards "the
removed features helped".

## 2. Research questions

**RQ-A.** Does `log_am_design` contribute predictive value beyond the other design features?

**RQ-B.** Is any contribution attributable to the **feature value** or to the **missingness
pattern**?

**RQ-C.** Is the missingness→outcome association **temporally stable**, and does its instability
track the observed calibration failure?

**RQ-D.** Does a train/calibration/test mismatch in availability degrade **conformal coverage**
specifically, as distinct from point accuracy?

## 3. Hypotheses

| ID | Hypothesis | Pre-specified decision rule |
|---|---|---|
| **A1** | Replacing `log_am_design` with a class-prior imputation that carries **no** missingness signal changes test pinball by less than the smallest BH-significant ablation effect already observed (0.00557) | If |Δ| < 0.00557 and the cluster-bootstrap CI contains 0 → the value, not the missingness, carries what little there is |
| **A2** | An explicit missingness indicator added to the imputed arm **recovers** a significant share of any loss from A1 | If the indicator's effect CI excludes 0 → the model is exploiting missingness |
| **A3** | Coverage degradation at origin 2016 is larger for objects whose A/M came from `class_prior_sbm` than for `design`-derived objects | Subgroup coverage difference with cluster-bootstrap CI excluding 0 |
| **A4** | The missingness→outcome odds ratio differs significantly between the training window and the test window | Non-overlapping cluster-robust CIs |

**All four are exploratory.** No outcome licenses a confirmatory claim. If any is suggestive, the
follow-up is a separate pre-registered experiment.

## 4. Design

Four arms, **learner and tuned hyperparameters held fixed** (matching the existing ablation
convention so results are comparable), at **both** published origins:

| Arm | `log_am_design` | Missingness signal | Purpose |
|---|---|---|---|
| **B0 — baseline** | as published (NaN kept) | implicit via NaN | reference; must reproduce the published arm exactly |
| **B1 — imputed** | class-prior imputed, **no NaN** | **removed** | RQ-A, RQ-B: value without missingness |
| **B2 — imputed + indicator** | class-prior imputed | **explicit binary indicator** | RQ-B: isolates the missingness contribution |
| **B3 — missingness only** | **dropped**; indicator retained | explicit indicator only | RQ-B: upper bound on what missingness alone buys |

**Two critical design controls:**

1. **Retune, or report as a bound.** The existing ablations are untuned. For B1–B3 either retune
   under the same budget as B0, or state explicitly that the comparison is a **lower bound on
   each arm's achievable performance**. I recommend retuning — otherwise the result is
   contaminated by the same bias that affects the existing ablations.
2. **Imputation fitted on training data only**, applied unchanged to tune-A, tune-B and test. The
   imputation must not see test rows.

**Subgroup analysis (RQ-C, RQ-D), no refitting required:**

- Coverage and interval width for B0, split by `am_source ∈ {design, class_prior_sbm}`, at both
  origins and both nominal levels — **computable from archived predictions**.
- Cluster-robust missingness→outcome odds ratio computed **per calendar window** rather than per
  split, to test temporal stability (RQ-A4).

## 5. Datasets, metrics, statistics

| Element | Specification |
|---|---|
| **Dataset** | The existing GCAT/CelesTrak cohort, snapshot 2026-10-27. **No new data.** Origins 2011 and 2016 only — origin 2006 is reserved and must not be reused for exploratory work |
| **Primary metric** | Pinball loss of capped log-lifetime on `known5` objects — the published endpoint, unchanged |
| **Secondary** | Empirical coverage at 80 % and 90 %; mean interval width; coverage by `am_source` subgroup |
| **Excluded** | Any mean-elicited score. `rmse_log10` remains inadmissible under fixed-horizon censoring |
| **Statistics** | Paired cluster bootstrap over launch families, 4,000 draws, seed 20261027 — matching the coupling analyses. Benjamini–Hochberg across the four arms within each origin |
| **Effect threshold** | 0.00557, the smallest BH-significant ablation effect already observed, so the result is interpretable against the project's existing scale |
| **Reporting** | Both origins separately. **No pooling** — the project's consistent finding is that effects reverse across origins |

## 6. Resources and feasibility

| Item | Estimate |
|---|---|
| Arms × origins | 4 × 2 = 8 fits (B0 reproduces published, so 6 new fits) |
| Learners required | `kumo` at 2011 and `tabm` at 2016 — **both backends are UNAVAILABLE** |
| **Feasibility as specified** | **BLOCKED** |
| **Feasible substitute** | Run the whole design with a **single available learner** (`xgboost` or `mlp`) at both origins. This changes the arm from the published selection but **removes the learner/origin confound** — the same logic that motivated experiment E12 |
| Compute (substitute) | ~2–6 GPU-hours or CPU-equivalent; 6 fits of a tuned XGBoost on ≤ 25,371 rows × 53 features |
| Storage | < 1 GB |
| **Subgroup analysis (RQ-C, RQ-D)** | **Zero fitting — hours of CPU on archived predictions** |
| Freeze impact | **None.** New output directory; no frozen artifact, pre-registration or published result touched |

## 7. Recommended staging

**Stage 1 — free, no fitting, run first.** Subgroup coverage and width by `am_source`, plus the
per-window odds-ratio stability check (RQ-C, RQ-D). This is computable from archived predictions
today and will tell us whether the mechanism hypothesis in §1.3 has any support **before** any
compute is spent. If coverage does *not* differ by `am_source` subgroup, the central motivation
weakens and B1–B3 are probably not worth running.

**Stage 2 — conditional on Stage 1.** The four-arm ablation with a single available learner.

## 8. Expected contribution, and the honest case against

**If the hypotheses are supported:** a documented case where a covariate with outcome-dependent
availability is in a deployed feature set, where the availability mismatch between the calibration
and test populations degrades interval coverage, and where **point-accuracy-based model selection
does not detect the harm**. That connects the project's calibration failure to its
selection-validity theme through an identified mechanism, and generalises beyond this dataset:
catalogue-derived covariates whose presence depends on object fate are common in
space-situational-awareness data.

**If they are not supported:** a clean negative that closes a live reviewer objection — the
deployed model is shown *not* to be exploiting an unstable missingness signal. That is worth
having either way, which is part of why I recommend the experiment.

**The case against running Stage 2 at all:** the RCS precedent found the effect on point accuracy
"not detectable". If `am_design` behaves the same way, B1–B3 may return a null on the primary
metric and the entire informative content will be in the Stage-1 coverage subgroups — which cost
nothing. **That is the main argument for the staging in §7.**

## 9. Constraints restated

- **Exploratory only.** No pre-registration is created or amended by this protocol.
- **Origin 2006 is not used.** It is the project's only never-scored fold and must stay that way.
- **No pre-registered verdict is revisited.** H1/H2/H3 and H4/H5/H6 are untouched.
- **No published artifact is modified.** Output goes to a new directory.
- **Nothing runs without your approval.**
