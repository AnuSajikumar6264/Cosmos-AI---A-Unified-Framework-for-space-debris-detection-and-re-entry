# JIRS Q1 experimental gap analysis (Phase 4)

Date 2026-11-04

**Verdict: the existing experiments are not sufficient for a strong Q1 publication in JIRS.**
Two gaps are decisive; six are material; the remainder are improvements.

The two decisive gaps are: **(i)** the project's best positive result is significance-tested only
under its temporally dishonest protocol, and **(ii)** the measurement that would constitute the
lead intelligent-systems contribution is exploratory and confounded.

---

## 4.1 Baseline comparisons

| Question | Assessment |
|---|---|
| Scientifically appropriate? | **Mixed.** Excellent on OPS-SAT; inadequate on orbital lifetime |
| Representative of recent state of the art? | **Yes on telemetry** — includes `chronos-bolt-small`, a 2024-generation time-series foundation model, and PatchTST on ESA-ADB. **No on lifetime** — every reference point is internal |
| Fair? | **Partly.** See tuning-parity defect below |
| Hyperparameters and budgets controlled? | **No** — a material defect |
| Physics vs ML compared appropriately? | **Yes**, and this is a strength: physics/trivial baselines are included everywhere and frequently win |
| Unavailable models documented? | **Yes** — 5 of 7 backends, with roles, in the reproducibility audit |

**[GAP B1 — tuning parity, material.]** `summary.json → fits` shows `tabicl` and `kumo` carry
**one** tuned hyperparameter (`n_estimators`) while `xgboost`, `lightgbm`, `mlp` and `tabm` carry
4–6. Additionally `lightgbm` shares `learning_rate`, `subsample` and `colsample_bytree`
**digit-for-digit** with `xgboost` (0.08013861768724162, 0.7883767189289016, 0.6016239712723395),
which suggests a shared trial draw rather than independent search. A Q1 reviewer will read unequal
tuning as an unfair comparison. **Either equalise the budget or state the budget per learner and
treat the under-tuned arms as lower bounds.**

**[GAP B2 — no external or trivial baseline on the lifetime benchmark, material.]** The only
non-learned reference is the project's own analytic drag estimate. There is no SGP4/B\*-based decay
baseline, no reimplementation of a published lifetime method, and no trivial reference predictor
(empirical marginal quantiles, constant-at-cap). Absolute loss values are therefore
uninterpretable — the reader learns only how the arms rank against each other. **A trivial
marginal-quantile baseline is nearly free to compute from the archives and should be added.**

**[SATISFACTORY]** On OPS-SAT the baseline set is genuinely strong for a Q1 venue: a foundation
model, three gradient-boosting methods, logistic regression, random forest, AdaBoost, a
transformer, a classical z-score monitor and isolation forest — eleven arms, five seeds.

## 4.2 Temporal validation

| Question | Assessment |
|---|---|
| Train/validation/test separation | **[6] Verified mechanically** at all three origins |
| Multiple forecast origins | **[6] Three** (2006, 2011, 2016) |
| Unseen evaluation fold | **[6] Yes** — origin 2006, hash-sealed before any fit |
| Distribution shift characterised | Partly — at-cap mass shift quantified; covariate shift not profiled |
| Ranking stability | **[6] Measured** — rank ranges, 23.64 % inversion, mean between-slice ρ +0.33 |
| **Selection regret** | **[GAP T1] Never computed** |
| Performance degradation | Measured as test/validation ratios — but only as an exploratory aside |
| Robustness across launch families | Clustering used for inference; **not** analysed as a stratification |
| Generalisation beyond the evaluated origins | **Not established** |

**[GAP T1 — selection regret, material and cheap.]** The paper measures rank *correlation* but
never the quantity an engineer cares about: **how much worse is the selected model than the best
available one?** From archives: at origin 2011 the selected learner (`kumo`) achieves test pinball
0.06161 against the best achievable 0.05958 — a regret of **+0.00203 (3.4 %)**. Reporting regret
alongside ρ converts an abstract correlation into an operational cost, and it is computable from
existing artifacts with no refitting. **This is the single highest value-per-effort addition in
this analysis.**

**[SATISFACTORY — and important for the framing]** The project correctly separates
**selection failure** from **generalisation failure** in its locked claim set, and that distinction
must survive into the JIRS manuscript: models do produce usable forward predictions; what fails is
the procedure for choosing among them. The ρ = 0.000 result is about selection, not about accuracy.

## 4.3 Statistical reliability

| Question | Assessment |
|---|---|
| Sample sizes | Test folds 2,667–7,277 objects; but **435–621 independent clusters**, and **n = 5–7 arms** for the rank statistics |
| Statistical power | **[GAP S1] The binding weakness of the project** |
| Confidence intervals | Present for couplings, coverage, slice deltas, OPS-SAT paired comparisons. **Absent from the main lifetime leaderboard and from every ρ** |
| Bootstrap procedures | **[6]** Paired cluster bootstrap over launch families; 4,000 draws (couplings, G5d), 2,000 (rolling-origin) |
| Multiple-testing correction | **[6]** Benjamini–Hochberg within test families |
| Cluster-aware inference | **[6]** Yes — better than the field norm |
| Independence assumptions | **[6]** Correctly handled by launch-family clustering |
| Effect sizes | Reported for couplings and OPS-SAT; **not** for the headline ρ results |
| Practical significance | **[GAP T1]** — no regret, no cost framing |
| **Sensitivity to the null model** | **[GAP S2] Not examined — and it matters a great deal** |

### Independent verification of the H2 Monte Carlo and its null model

You asked for this specifically. The arm counts are small enough to **enumerate exactly** rather
than simulate, so I did both.

**Null model as implemented by the pre-registered criterion:** rankings at each origin are
independent uniform random permutations; origin 2011 and 2016 rank 4 arms, origin 2006 ranks 3
(`tabm` was not fittable); three arms are present at every origin.

**Exact enumeration over all 4! × 4! × 3! = 3,456 equiprobable configurations:**

| Event | Exact | Probability |
|---|---|---|
| No always-present arm retains its rank (clause 1) | 2,874 / 3,456 | **0.8316** |
| `physics_only` rank range ≥ 3 (clause 2) | 792 / 3,456 | **0.2292** |
| **Both — the H2 criterion as implemented** | **686 / 3,456** | **0.1985** |

My earlier Monte Carlo (400,000 draws) gave 0.1990 — confirmed to three decimal places. **The
correct figure for the full H2 criterion is 0.1985, not 0.83**; 0.83 is clause 1 in isolation. For
comparison, H3 was closed as UNDERPOWERED because ρ = 1.0 on three arms arises by chance with
probability 1/6 = **0.1667**. **H2's chance level exceeds H3's by +0.032.** The pre-registration
imposed a power floor on H3 and none on H2; that asymmetry is a defect, and the conclusion stands
that H2 must not be described as a confirmation.

**[GAP S2 — the null model is arguably the wrong one, and this is the more interesting critique.]**
The uniform-permutation null answers *"could pure chance produce this instability?"* — yes, about
one time in five. But the scientifically apt null for H2 is different: *"could **sampling noise
around a stable underlying quality ordering** produce this instability?"* Under a perfectly stable
ordering the criterion is met with probability 0; under uniform randomness, 0.1985. The truth lies
between, and where it lies is exactly what determines whether the observed instability is
evidence of anything.

The right test is a **cluster bootstrap over each origin's test fold**, holding the fitted arms
fixed, recomputing ranks per resample, and reporting how often the H2 criterion is met. That
distribution is the correct reference. **It is computable entirely from the archived per-object
predictions with no refitting**, which makes it both rigorous and cheap — experiment **E3**.

**[GAP S1 — power, material.]** Rank statistics rest on n = 5–7. No confidence interval or
permutation p-value is reported for any ρ. The lifetime leaderboard carries point values and ranks
with **no per-arm interval and no paired test between arms**, despite the bootstrap machinery
existing and being applied elsewhere. For a Q1 venue this is the most visible statistical gap.

## 4.4 Uncertainty and calibration

| Question | Assessment |
|---|---|
| Calibration methodology | **[6]** Mondrian split-CQR (Romano et al. 2019 per group; Vovk 2013), groups = object class × perigee band with a documented fallback hierarchy |
| Empirical coverage | **[6]** Reported per slice |
| Coverage deviations | **Measured and substantial**: 80 % level 0.572–0.960 across 11 slices |
| Temporal stability of calibration | **Measured — unstable**; monotone degradation at **one of two** origins, **no trend test** |
| Prediction-interval quality | Widths reported for conjunction; **not** systematically for lifetime |
| Epistemic vs aleatoric | **[GAP U1] Not separated anywhere** |
| Propagated across modules | **[GAP U2] No** |
| Distribution-free guarantees justified? | **[GAP U3] No — and none may be claimed** |

**[GAP U3 — critical if mishandled.]** Split-conformal coverage guarantees require exchangeability
between the calibration set and the test set. Here the test folds are **forward in time** from
calibration, so exchangeability fails **by construction**, and the measured coverage spread
(0.572–0.960) confirms it fails in practice. **Any statement of a distribution-free or
finite-sample coverage guarantee would be mathematically unjustified.** The defensible claim is:
coverage *targeted* by construction, *measured* empirically, and *observed to be unstable* under
temporal displacement — with Barber et al. (2023) cited for why guarantees weaken beyond
exchangeability.

**[GAP U2 — material for JIRS.]** Each module emits intervals; **none reaches the decision layer**.
For an intelligent-systems venue, uncertainty that is computed and then discarded before the
decision is a conspicuous architectural gap. This is the mechanism by which experiment **E4** would
make the decision layer meaningful.

**[GAP U1]** Epistemic and aleatoric uncertainty are never separated. Seed-ensemble spread is
available for every learner (5 seeds), so a first decomposition is cheap — but I do **not**
consider it essential, since no claim currently depends on the distinction.

## 4.5 Ablation studies

| Question | Assessment |
|---|---|
| Do existing ablations establish component contributions? | **No — they are structurally biased** |

**[GAP A1 — material.]** Every ablation arm records `tuned: false` and inherits its parent
full-feature arm's hyperparameters (verified in `summary.json → fits`: `tabm_no_physics`,
`tabm_no_family`, `tabm_no_space_weather`, `tabm_no_design`, `tabm_plus_rcs_2026` all untuned).
Hyperparameters optimised for the full feature set systematically disadvantage reduced-feature
models, biasing every ablation towards "the removed features helped". The C1 coupling result and
the C-4(b) sign-reversal finding both rest on these comparisons. **At minimum this must be
disclosed; ideally the key ablations are retuned.**

**[SATISFACTORY]** Ablation *coverage* is good — four feature groups plus an additive variant, at
two origins, with cluster-aware inference and BH correction. The E12 same-learner design is a
genuinely well-conceived de-confounding experiment, and its negative verdict is now reported.

**Recommended additional ablation: exactly one.** For the OPS-SAT `hybrid`, ablate the two fusion
branches (CNN-only, MLP-only, both). This answers a real question — *is the late fusion doing
anything, or is one branch carrying the result?* — and the comparison arms (`cnn`, `fcnn`) already
exist, so only the attribution analysis is new. **No other ablation is scientifically necessary**,
and I recommend against adding any to inflate the experiment count.

## 4.6 Robustness and sensitivity

| Dimension | Needed? | Reasoning |
|---|---|---|
| **Temporal-origin sensitivity** | **Essential** | The lead claim is about temporal displacement; it must be shown not to hinge on one origin pair |
| **Hyperparameter sensitivity** | **Recommended** | Directly addresses GAP B1/A1; a reviewer will ask whether ρ = 0.000 is a tuning artefact |
| **Data-subset sensitivity** | **Recommended** | The cluster bootstrap of E3 largely supplies this |
| Noise sensitivity | Optional | No claim depends on input-noise robustness |
| Missing-data robustness | **Recommended for JIRS** | [J3] is a JIRS paper on fault diagnosis under high missing rates; our abstention design is the natural comparator and is untested under induced missingness |
| Outlier sensitivity | Optional | The capped target already bounds outlier influence |
| Alternative baseline configurations | Covered by B1/B2 | — |
| Computational-resource sensitivity | Not needed | No resource-scaling claim is made |

## 4.7 Computational evaluation

| Question | Assessment |
|---|---|
| Training cost | **[6]** `train_time_s` recorded per arm |
| Inference latency | **[6]** `latency_ms_per_fragment`, `throughput_fragments_s` recorded |
| Memory | **[6]** `peak_memory_mb`, `size_mb` recorded |
| Model size | **[6]** `params` recorded |
| Scalability | Not assessed — and not needed |
| Complexity analysis | Absent — not needed |
| Hardware requirements | Partly (`torch 2.14.0+xpu`, Intel GPU) |
| **Runtime reproducibility** | **[GAP C1]** No hardware/thread/batch configuration recorded alongside the timings |

**[SATISFACTORY — and a genuine JIRS strength.]** The telemetry benchmarks report parameters,
model size, training time, per-fragment latency, throughput and peak memory across eleven arms.
JIRS, as an intelligent-systems venue, values exactly this, and the project has it. The result is
also favourable: the best detector is **74k parameters at 0.0045 ms/fragment**, which is a
deployability argument.

**[GAP C1]** Timings are reported without the hardware configuration, thread count or batch size
needed to reproduce them. Cheap to fix. **Do not convert these into real-time or
operational-deployment claims** — latency on one configuration is not a deployment result.

---

## Gap register, prioritised

| ID | Gap | Class | Blocks Q1? | Cost |
|---|---|---|---|---|
| **E1** | Best positive result significance-tested only under the temporally dishonest protocol; score archive missing | **Decisive** | **Yes** | Low–moderate (refit needed; backends available) |
| **E2** | Lead contribution (selection transfer vs temporal displacement) is exploratory and confounded | **Decisive** | **Yes** | Moderate |
| **E3** | H2's null model is arguably wrong; no bootstrap reference distribution | Material | No | **Low** (archives only) |
| **T1** | Selection regret never computed | Material | No | **Very low** |
| **B1** | Tuning parity unequal and undisclosed | Material | No | Low (disclose) / moderate (fix) |
| **B2** | No external or trivial baseline on lifetime | Material | No | **Very low** (trivial baseline) |
| **A1** | Ablation arms untuned — biases all ablations | Material | No | Low (disclose) / high (retune) |
| **U2** | Uncertainty not propagated to the decision layer | Material for JIRS | No | Moderate |
| **U3** | Conformal guarantee must not be claimed | Material | **Yes if mishandled** | Zero (wording) |
| **S1** | No CI or permutation test on any ρ; no leaderboard intervals | Material | No | Low |
| **D1** | Decision layer has no outcome-scored evaluation | **Critical for JIRS** | **Yes, for a decision-support claim** | Moderate–high |
| **C1** | Runtime configuration unrecorded | Minor | No | Very low |
| **U1** | Epistemic/aleatoric not separated | Minor | No | Low |

## Bottom line

The project's experimental *infrastructure* is above the field norm — verified temporal
separation, cluster-aware inference with multiplicity correction, hash-sealed pre-registration,
exact prediction-level reproducibility, and computational characterisation. Those are real Q1
assets.

What is missing is not more experiments in general, but **three specific things**: a
temporally-honest significance test for the one strong positive result (E1), a controlled design
that turns the lead measurement from exploratory into confirmatory (E2), and — only if a
decision-support contribution is to be claimed at all — an outcome-scored evaluation of the
decision layer (D1/E4).

Everything else on the register is a disclosure, a wording change, or a cheap computation on
existing archives.
