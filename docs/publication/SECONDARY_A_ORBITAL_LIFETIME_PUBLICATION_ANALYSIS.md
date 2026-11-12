# Secondary A — orbital lifetime publication analysis

Date 2026-11-05 · free analyses from archived outputs only · **no new fitting, no historical result
modified**

**Headline: two new free results materially strengthen this track. Every published arm beats every
trivial feature-free baseline at both origins — closing the "no external calibration" objection.
And the coverage failure localises to a subgroup: design-derived objects get half-width intervals
and cov80 of 0.5625 at origin 2016 against 0.80 nominal, while the calibration split contains only
5.9 % of them.**

This is a **separate publication candidate**, not part of the ESA-ADB manuscript.

---

## 1. NEW: trivial reference predictors — the missing external calibration

Computed from archived predictions and the cohort; **no model fitted**. Pinball loss of capped
log-lifetime on `known5` objects, the published endpoint.

| Predictor | Origin 2011 (n = 2,667) | Origin 2016 (n = 2,978) |
|---|---|---|
| `constant_at_cap` (always predict the 5-year cap) | 0.172892 | 0.232879 |
| `train_marginal_quantiles` (feature-free, fitted on train) | 0.231209 | 0.200591 |
| **`test_marginal_quantiles` (ORACLE — best possible feature-free predictor)** | **0.133180** | **0.146946** |
| **Published best** | **0.052676** (`physics_only`) | **0.049944** (`tabicl`) |
| **Published worst** | **0.114661** (`mlp`) | **0.089249** (`physics_only`) |

### 1.1 The result

**Every published arm beats the feature-free oracle at both origins.**

- Origin 2011: the **worst** published arm (`mlp`, 0.1147) still beats the oracle (0.1332) by
  **14 %**. The best beats it by **60 %**.
- Origin 2016: the worst published arm (`physics_only`, 0.0892) beats the oracle (0.1469) by
  **39 %**. The best beats it by **66 %**.

The oracle is a genuine upper bound on feature-free performance: it uses the *test set's own*
marginal quantiles, which no honest predictor could know. So the margin above it is a lower bound
on the signal every arm extracts from features.

**This closes the single largest objection to Track 2** — *"every baseline is your own, so I cannot
judge whether these numbers are good."* The answer is now quantitative and favourable, and it cost
no compute.

### 1.2 Honest limits

- A feature-free baseline is a **floor**, not a competitive method. It establishes that the arms
  are doing something, not that they are state of the art.
- It does **not** substitute for an external *published* method. No reimplementation of Zhou et al.
  (2026), He et al. (2024) or Salmaso et al. (2023) exists, and an ML-dSGP4-class comparison
  remains infeasible (no TLE, B\* or ephemeris data).
- `train_marginal_quantiles` is *worse* than `constant_at_cap` at origin 2011 (0.2312 vs 0.1729),
  which reflects the train/test distribution shift the paper is about — worth a sentence, not a
  claim.

## 2. NEW: the coverage failure localises to an identifiable subgroup

From archived `subgroups_test.csv` — already computed, never reported. Coverage and interval width
split by `am_source`, the provenance of each object's area-to-mass ratio.

| Origin | Arm | `am_source` | n | **cov80** | cov90 | width80 | pinball |
|---|---|---|---|---|---|---|---|
| **2011** | `cosmos_gated` | class_prior_sbm (imputed) | 2,263 | **0.9465** | 0.9717 | 0.9430 | 0.0604 |
| **2011** | `cosmos_gated` | **design (real)** | 404 | **0.7921** | 0.8886 | **0.5060** | 0.0465 |
| **2016** | `cosmos_gated` | class_prior_sbm (imputed) | 2,322 | **0.7606** | 0.8790 | 0.4428 | 0.0591 |
| **2016** | `cosmos_gated` | **design (real)** | 656 | **0.5625** | 0.8567 | **0.3980** | 0.0647 |

Same pattern for other arms at origin 2016: `physics_only` 0.7799 → **0.5899**; `tabm`
0.7679 → **0.5854**.

### 2.1 What this shows

1. **A large, consistent coverage gap by covariate provenance:** 0.154 at origin 2011 and
   **0.198** at origin 2016, always in the same direction — real design data gives *worse*
   coverage.
2. **Interval width is roughly halved for design-derived objects** (0.506 vs 0.943 at 2011). The
   model is far more confident where it has real design data, and that confidence over-reaches.
3. **At origin 2016, design-derived objects reach cov80 = 0.5625 against 0.80 nominal — a
   24-point shortfall**, much worse than the aggregate 0.7169 reported in Phase H. The aggregate
   under-coverage is substantially driven by this subgroup.
4. **A candidate mechanism, already documented:** tune-B — the conformal calibration split — holds
   only **5.9 %** design-derived objects at origin 2016, while the test split holds **22.4 %**.
   The calibration set barely contains the subgroup that fails worst.

### 2.2 Status — this is a descriptive subgroup analysis, not a causal test

It is consistent with the calibration-composition mismatch hypothesis and does not establish it.
Confounds not separated: design-derived objects are predominantly intact payloads and rocket
bodies, a different and plausibly harder subpopulation, so provenance and object class move
together. **The `am_design` ablation protocol (Stage 2) is what would separate them.**

**But Stage 1 of that protocol is now effectively complete and positive**, which strengthens the
case for Stage 2 considerably — I had expected the subgroup signal might be absent.

## 3. Positioning against Shorten et al. (2023) — resolved

Full 29-page preprint read (`arXiv:2212.08662`; published as J. Spacecraft and Rockets
60(6):2003–2007, `10.2514/1.A35642`).

| Dimension | Shorten et al. | COSMOS-AI lifetime track |
|---|---|---|
| Task | **Manoeuvre detection** from TLEs | **Time-to-decay forecasting** |
| Data | NORAD TLEs, **15 satellites** | GCAT + CelesTrak, **64,516-row cohort** |
| Target | Manoeuvre occurrence | Capped log-lifetime with a point mass |
| Methods | **None** — pitfalls analysis plus dataset release | 17 arms |
| Uncertainty | **Absent** — the word does not appear | Mondrian CQR, coverage reported |
| Term counts in 29 pages | "decay" **0**, "re-entry" **0**, "quantile" **0**, "uncertainty" **0** | — |

**"Satellite lifetimes" in that paper means operational life and end-of-life determination via
manoeuvre history**, fixed by its own Introduction. **It does not occupy this contribution.**

**It must still be cited**, for three reasons: title adjacency is a reviewer-perception risk; it
independently documents TLE hazards, which *supports* COSMOS-AI's decision to build on catalogue
elements rather than TLEs; and it establishes "pitfalls + benchmark release" as a publishable shape
in this domain.

## 4. Temporal evaluation and forecast-origin differences

| Property | Evidence |
|---|---|
| Three temporal origins | 2006 (sealed, never previously scored), 2011, 2016 |
| Strict ordering verified | `train < train_end ≤ tune < tune_end`, `origin ≤ test < test_end` at all three |
| Launch families straddling tune-A/tune-B | **0** at all three origins |
| Objects shared between test folds | **0** across all three pairs |
| Split sizes | train 20,811 / 25,371 / 18,960; tune-A **248 / 1,741 / 211**; tune-B 332 / 1,560 / 544; test 2,680 / 2,993 / 7,281 |
| Origin-2006 realised sizes | **Match the pre-registration exactly** — 0 deviations |

**The tune-A asymmetry is load-bearing**: 248 objects at origin 2011 against 1,741 at 2016. It is
the leading rival explanation for the ρ = 0.000 result and must be stated prominently.

## 5. Model-selection and calibration findings

| Finding | Value | Tier |
|---|---|---|
| Spearman(tune-A rank, test rank) | **0.000** at both origins, n = 7 learners | Measured; 95 % interval ≈ [−0.77, +0.77] |
| **Selection regret, deployed pool** | **+3.40 %** (2011), **+18.72 %** (2016), **+25.15 %** (2006) | Measured; **significant at 2016** — CI [+0.0040, +0.0169], zero-regret in **0 of 4,000** resamples |
| Regret against all 17 arms | +16.96 % / +18.72 % / **+82.88 %** | Measured |
| Selection chose the **worst arm in its own pool** | at origins 2016 and 2006 | Measured (2–3 arm pools) |
| `physics_only` rank | **1st of 19** at 2011, **19th of 19** at 2016; range **1 → 11** across 11 slices | Measured |
| Slice-pair rank inversion | **23.64 %**; mean between-slice ρ **+0.33** | Measured |
| Ranking instability on the sealed fold | H2 **SUPPORTED** as pre-registered; **chance level 0.1985** (exact enumeration, 686/3,456) | Confirmatory, low power |
| Coverage | 2016/80 % **0.71692** under-covers (p = 0.0415); 2011/80 % **0.92313** over-covers (p = 0.0) — **direction reverses**; width halves 0.877 → 0.433 | Measured |

**Selection regret is the strongest result in this track** — it is the only statistically
significant statement about selection failure, and it is operationally legible.

## 6. RCS missingness and uncertainty findings

| Finding | Status |
|---|---|
| `rcs_m2` is **not** in the deployed feature set | Verified — `FULL` excludes `rcs`; it enters only via the labelled `plus_rcs_2026` demonstration arm, *"never a candidate for selection"* |
| Missingness is outcome-associated | Adjusted OR **3.594** [2.094, 6.169] at 2016; **3.625** [2.076, 6.327] at 2011, cluster-robust |
| Missingness rate is non-stationary | 27.1 % → 1.7 % → **68.2 %** (train → tuneB → test) at 2016 |
| Adding the covariate **sharpens** intervals when the test pattern matches training | Origin 2011: width 0.944 → **0.801** at equal coverage; arm rises rank 9 → **3** |
| Adding it **destroys coverage** when the pattern diverges | Origin 2016: 90 % coverage 0.808 → **0.689** (−11.9 pp); arm falls rank 6 → **16** |
| Effect on point accuracy | **Not detectable** — the project's own ablation |
| `am_design` (which **is** deployed) missingness | OR **3.44–3.59**; **never ablated**; §2 above provides the first subgroup evidence |

**The publishable form of this:** a covariate whose *availability* depends on the outcome improves
sharpness while the availability pattern is stable and silently destroys calibration when it
shifts — and **point-accuracy-based model selection does not detect the harm**. That connects the
calibration failure to the selection-validity theme through an identified mechanism.

## 7. Lifetime CDF defect — implications for this track

| Question | Answer |
|---|---|
| Does any Track 2 result depend on it? | **No.** All results come from archived quantile matrices, not horizon probabilities |
| Must it be disclosed? | **Yes** — the released `twins.jsonl` carries 123 incoherent records marked `abstain = false` and `"validated-real"` |
| Does it bear on the paper's argument? | **Yes, supportively.** It is a second instance of post-hoc calibration damaging coherence, and **Henzi, Ziegel & Gneiting (2021)** is both the principled fix and already cited for the L17 methodology |

Full detail: `LIFETIME_CDF_DOWNSTREAM_IMPACT_REPORT.md`.

## 8. Reproducibility evidence

| Level | Status |
|---|---|
| **Prediction-level** | **COMPLETE** — every published value recomputes to **0.000e+00** |
| **Training-level** | **ABSENT** — 5 of 7 backends undeclared; **1 of 7** matches the only recorded environment (`torch 2.13.0+xpu` in the freeze vs 2.14.0+xpu now); `kumo` requires a **commercial vendor library**; no environment recorded for published runs |
| Configuration | **Recorded** — tuned hyperparameters per learner, seeds `(0,1,2,3,4)`, MD5 fit fingerprints |
| Integrity | 28-file freeze intact; G5d hash intact; dated-forecast digest verifies; 217/217 tests pass |
| Public artifact | **NONE** — no DOI, deposit, release or licence |

## 9. Track 2 standing after these free analyses

| Dimension | Before | After | Why |
|---|---|---|---|
| **Baseline competitiveness** | **2 / 5** | **3.5 / 5** | Trivial feature-free baselines now bound performance from below, and every arm clears them. Still no external *published* method |
| Scientific novelty | 4 / 5 | 4 / 5 | Unchanged; Shorten et al. resolved in COSMOS-AI's favour |
| Experimental validity | 4 / 5 | **4.5 / 5** | The coverage failure now has a localised, archived subgroup signature |
| Statistical strength | 3 / 5 | 3 / 5 | Unchanged — ρ still n = 7 with no permutation test |

**Remaining essential work for Track 2, all cheap:** per-arm bootstrap intervals and paired tests on
the main leaderboard; bootstrap CI and exact permutation p-value for each ρ; and citing Candès et
al. (2023), Gui et al. (2024) and Shorten et al. (2023). None requires fitting.

**Recommended framing:** a catalogue-scale forward-in-time benchmark, the measured cost of
following the standard selection rule (up to **+82.88 %** excess loss), and a localised,
mechanistically-motivated calibration failure. Venue: a space journal — Acta Astronautica (Scopus
12372) or Advances in Space Research. **Neither EAAI nor JIRS has a space ASJC category.**
