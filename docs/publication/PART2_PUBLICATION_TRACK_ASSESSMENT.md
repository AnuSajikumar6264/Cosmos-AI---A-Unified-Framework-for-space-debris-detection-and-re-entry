# Part 2 — publication track assessment

Date 2026-11-05

**Three tracks scored on eleven dimensions. Scoring is 1–5 with the reasoning stated for every
cell; weights are declared before the scores and justified. I have deliberately not let H6's
statistical significance decide the outcome — see §4, where Track 3 loses points on the two
dimensions significance cannot help.**

---

## 1. Weights, declared and justified

| Dimension | Weight | Why this weight |
|---|---|---|
| Scientific novelty | **3** | What a journal buys. Highest weight |
| Experimental validity | **3** | A novel claim on invalid experiments is worthless |
| Baseline competitiveness | **3** | The dimension that most often decides rejection in applied-ML venues, and the project's known exposure |
| Statistical strength | 2 | Necessary, not sufficient — deliberately *not* dominant, so H6 cannot carry the decision alone |
| Generalisation | 2 | Reviewers press on it; limited generalisation is survivable if disclosed |
| Methodological contribution | 2 | Distinct from novelty: transferable method vs new finding |
| Journal suitability | 2 | Determines desk-rejection risk |
| Dataset quality | 1 | All three use real, externally-sourced data |
| Reproducibility | 1 | Important, but correctable and not usually a rejection ground on its own |
| Remaining experiments (inverse: fewer = higher) | 1 | A cost, not a quality |
| Reviewer-objection exposure (inverse) | 1 | Captured largely by other dimensions; avoids double-counting |

Maximum weighted total = 5 × 21 = **105**.

## 2. Scores with reasoning

### Scientific novelty (×3)

| Track | Score | Reasoning |
|---|---|---|
| 1 OPS-SAT | **2** | Best claim classifies as *incremental engineering*. Beating a foundation model on 529 supervised fragments is solid but not a methodological advance, and transformer-based satellite AD is crowded (Fejjari 2026, 7 cites; Dai 2026, 3 cites). The fusion claim is **unsupported** |
| 2 Lifetime | **4** | A benchmark artifact with **no competitor located** (Shorten et al. verified not to occupy it), plus a *significant* selection-regret result. Docked one point because the uncertainty methodology has uncited direct prior art (Candès 2023, Gui 2024) |
| 3 ESA-ADB | **4** | Pre-registration with a frozen rule and declared minimum effect is genuinely distinctive, and a pre-registered **negative** deep-learning result is under-supplied. Docked because abstention/budgets are pre-empted by TC-CAD and Heydari, and Brancato et al. occupies the same benchmark-evaluation space |

### Methodological contribution (×2)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **2** | Standard architectures, standard protocol. The time-blocked protocol is good practice, not a contribution |
| 2 | **3** | Forward-in-time multi-origin protocol with verified launch-family and test-fold disjointness; cluster-aware inference; elicitability-based metric exclusion. Transferable, but assembled from known components |
| 3 | **5** | Hash-frozen pre-registration with a refuse-to-run gate, vendored official metric verified byte-identical to upstream `67194d3`, gated test scoring, 30-day block bootstrap hierarchical over seeds, Holm correction, separate deviation log and post-hoc plan. **The best methodology in the project** |

### Dataset quality (×1)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **4** | OPS-SAT AD, a published benchmark (Ruszczak et al. 2025, Scientific Data). **But only 529 test fragments** and one spacecraft |
| 2 | **4** | 64,516-row cohort from GCAT + CelesTrak; test folds 2,680/2,993/7,281. Real, large. Docked for a single snapshot and no sensitivity to snapshot date |
| 3 | **5** | ESA Anomalies Dataset v1.0 (Zenodo 12528696), expert-annotated, official splits and grids, official metric code. Two usable missions. **The highest-quality data in the project** |

### Experimental validity (×3)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **3** | Protocol fixed before any test number was seen; 5 seeds; two protocols; label-efficiency sweep. **But** significance tests exist only for the temporally-interleaved official protocol, and the score archive `test_scores_official.npz` is **missing**, so a published comparison is not re-derivable |
| 2 | **4** | Mechanically verified temporal ordering, zero launch families straddling tune-A/tune-B, zero objects shared across test folds, exact prediction-level reproduction (0.000e+00), and an explicit leakage analysis with cluster-robust odds ratios. **Docked:** ablation arms untuned; tuning depth unequal (1 vs 6 hyperparameters) |
| 3 | **4** | Independent code audit found **no path by which test labels reach any model, score, calibration pool or selection**; all residual flows input-only and quantified; no event crosses any boundary. **Docked hard for test-half exposure:** both test halves were scored in 128 configuration–layer combinations *before* the pre-registered protocol was designed, and the project states *"the pre-registration was motivated by a test result"* |

### Baseline competitiveness (×3)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **4** | Eleven arms across five families on one protocol with 5 seeds, including a 2024-generation foundation model. **Docked:** no reconstruction-based arm, no published satellite-specific method on this benchmark |
| 2 | **2** | **Every reference point is internal.** No external published method, no trivial reference predictor (marginal quantiles, constant-at-cap). Absolute losses are uninterpretable to a reader. ML-dSGP4 omission is justified, but that does not supply a baseline |
| 3 | **3** | Strongest set in the project — official GlobalSTD **reproduced to within 0.001 in 8 configurations**, published PatchTST re-implemented, foundation model, label-free rules. **Docked to 3** because the ACI comparator's γ was tuned to a point rate not the event objective, **neither supervised scorer had a tuning budget, only one deep architecture was tried**, and the headline comparison against the published state of the art is **blocked** |

### Generalisation (×2)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **2** | One spacecraft. Time-blocked protocol controls temporal interleaving within the mission but **cannot** support cross-satellite claims. The one cross-corpus signal available is unfavourable |
| 2 | **3** | Three temporal origins, one hash-sealed and never previously scored. Effects reverse across origins — which is the finding, not a failure. Docked: single catalogue, uncontrolled LEO only |
| 3 | **2** | **The selection effect reverses on Mission 2 and on the lightweight M1 subset; only 1 of 8 cells is confirmatory.** And M2 cannot serve as a generalisation test — 6 anomalies in its test half, every learned arm at exactly **0.0000** on the anomaly-only metric. No third usable mission exists |

### Reproducibility (×1)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **4** | **Training-level reproducible** — needs only `torch` and `xgboost`, both installed. Docked: the score archive is missing |
| 2 | **2** | Prediction-level **exact** (0.000e+00), but training-level absent: 5 of 7 backends undeclared, 1 of 7 matches the recorded environment, one is a **commercial vendor library**, and no environment was recorded for the published runs |
| 3 | **4** | Frozen hashes, code public, vendored official metric, one-command rebuild, an evidence file. Docked: the freeze gate covers **code only** — not the freeze record, selection JSONs, test driver or library versions; and A1 selection files predate the frozen code |

### Statistical strength (×2)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **3** | Paired bootstrap with CIs and p-values, 5 seeds. **But** only on the official protocol; 529 test fragments; the headline margin over `fcnn` is +0.0059 with CI lower bound 0.0004 |
| 2 | **3** | Cluster bootstrap over launch families, BH correction, exact enumeration of the H2 null (0.1985), **significant selection regret at origin 2016** (CI excluding zero, 0/4,000 zero-regret resamples). **But** headline ρ over n = 7 with no permutation test, and no per-arm leaderboard intervals |
| 4 | — | — |
| 3 | **5** | Paired bootstrap with 30-day blocks (86 M1, 22 M2), hierarchical over seeds, B = 2,000, **Holm correction with a pre-declared minimum effect of +0.05**. H6 Holm p = 0.0015. The bootstrap is a documented approximation of the official metric that changes no verdict. **Docked nothing — this is the strongest statistics in the project, even though §4 explains why it does not decide the outcome** |

### Journal suitability (×2) — assessed against EAAI and JIRS

| Track | Score | Reasoning |
|---|---|---|
| 1 | **4** | Applied AI on real engineering data is **core EAAI scope**. For JIRS: anomaly/fault is 1.8 % of its 2023+ output |
| 2 | **2** | Fits neither well. Catalogue-scale orbital prediction belongs in a space venue (Acta Astronautica, Advances in Space Research) or a data venue. **No space ASJC category in either EAAI or JIRS** |
| 3 | **5** | **Best fit.** Applied AI + rigorous evaluation on real spacecraft telemetry is squarely EAAI. The project's own prior venue analysis independently ranked EAAI first of eleven. Also fits Aerospace Science and Technology — which published Brancato et al., cutting both ways |

### Remaining experiments (×1, inverse — fewer required scores higher)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **3** | E1 time-blocked significance (2–6 GPU-h) + E6 branch ablation (2–4 GPU-h) + reconstruction baseline. **E6 is existential** — without it there is no architectural claim |
| 2 | **4** | Stage-1 subgroup analyses are free; a trivial baseline is nearly free; leaderboard intervals cheap. Nothing existential, and the two main results already exist |
| 3 | **2** | Fractional factorial decomposition of H6 (essential for attribution), equal tuning budgets, more seeds, anomaly-only reporting throughout — and **Brancato reconciliation, which is blocked** |

### Reviewer-objection exposure (×1, inverse)

| Track | Score | Reasoning |
|---|---|---|
| 1 | **3** | *"Your fusion doesn't beat its own CNN branch"* — currently unanswerable |
| 2 | **3** | *"No external baseline, so I cannot judge your absolute numbers"*; *"n = 7"* |
| 3 | **2** | *"A published paper reports 0.902 where you report 0.09"* — **the strongest single objection in the project**; plus five-way confound, test-half exposure, M2 reversal |

## 3. Weighted totals

| Dimension | W | T1 | T2 | T3 |
|---|---|---|---|---|
| Scientific novelty | 3 | 2 → 6 | 4 → 12 | 4 → 12 |
| Methodological contribution | 2 | 2 → 4 | 3 → 6 | 5 → 10 |
| Dataset quality | 1 | 4 → 4 | 4 → 4 | 5 → 5 |
| Experimental validity | 3 | 3 → 9 | 4 → 12 | 4 → 12 |
| Baseline competitiveness | 3 | 4 → 12 | 2 → 6 | 3 → 9 |
| Generalisation | 2 | 2 → 4 | 3 → 6 | 2 → 4 |
| Reproducibility | 1 | 4 → 4 | 2 → 2 | 4 → 4 |
| Statistical strength | 2 | 3 → 6 | 3 → 6 | 5 → 10 |
| Journal suitability | 2 | 4 → 8 | 2 → 4 | 5 → 10 |
| Remaining experiments (inv.) | 1 | 3 → 3 | 4 → 4 | 2 → 2 |
| Reviewer exposure (inv.) | 1 | 3 → 3 | 3 → 3 | 2 → 2 |
| **TOTAL (of 105)** | | **63** | **65** | **80** |

**Track 3: 80 · Track 2: 65 · Track 1: 63**

## 4. Did H6's significance decide this? No — and here is the check

You asked me not to favour Track 3 automatically because H6 is significant. Two tests of that:

**Test 1 — remove statistical strength entirely.** Totals become T1 57, T2 59, **T3 70**. Track 3
still leads by 11. Its margin comes from **methodological contribution (10 vs 4 and 6)**,
**dataset quality** and **journal suitability (10 vs 8 and 4)** — none of which is H6.

**Test 2 — where Track 3 scores worst.** It is **last on generalisation (2)**, **last on remaining
experiments (2)**, and **last on reviewer exposure (2)**. Significance does not help any of these,
and they are precisely the dimensions that make Track 3 *not yet* submittable:

- The selection effect **reverses on M2 and the lightweight subset**; 1 of 8 cells is confirmatory.
- H6 is **confounded five ways**, so it attributes nothing.
- **Brancato's 0.902 is unexplained** and blocks any performance claim.
- Both test halves were scored 128 ways **before** the pre-registration was designed.

So Track 3 wins on *methodology and venue fit*, and simultaneously carries the project's largest
unresolved blocker. That is the honest outcome, and it is why §5 recommends it as the primary
paper **conditional on specified work**, not as ready.

## 5. Track classification

| Track | Classification |
|---|---|
| **Track 3 — ESA-ADB** | **B. Promising but requiring specified experiments** |
| **Track 2 — Lifetime** | **B. Promising but requiring specified experiments** (closest to A; its two main results already exist) |
| **Track 1 — OPS-SAT** | **B/C boundary.** B *only if* E6 supports a calibration/stability claim; **C** if E6 shows the fusion contributes nothing, because then the track has no contribution beyond "a tuned CNN does well on 529 fragments" |

**No track is A.** None is ready for manuscript development today.

## 6. Minimum experiments per track

### Track 3 (primary candidate)

| # | Experiment | Status | Cost |
|---|---|---|---|
| **3a** | **Report the anomaly-only metric alongside the composite everywhere** | **FREE — already in `results.csv`.** Removes the M2 saturation misreading | zero |
| **3b** | **Fractional factorial decomposition of H6** over residual scale σ, calibration pool and selection data (8 cells), pre-registered, labelled exploratory if test halves are reused | **Essential** — without it H6 attributes nothing | moderate (refits) |
| **3c** | **Reconcile Brancato et al.** | **BLOCKED — paywalled.** Needs channel set, hierarchy level, metric variant, event-matching rule, out-of-limit definition | blocked |
| 3d | Equal tuning budgets for ACI, XGBoost, TCN; ≥ 2 deep architectures | Closes the fairness objection | moderate |
| 3e | More seeds (currently 5/3 against ±0.1 arm-mean uncertainty) | H4/H5 underpowered vs the +0.05 threshold | moderate |
| 3f | Forward-chaining control instead of cross-fitting | Quantifies optimism (lightweight M1: 0.528 → 0.025) | moderate |

### Track 2

| # | Experiment | Status | Cost |
|---|---|---|---|
| **2a** | **Trivial reference predictor** (empirical marginal quantiles, constant-at-cap) | **Essential** — makes absolute losses interpretable | **near-free from archives** |
| **2b** | **Per-arm bootstrap intervals + paired tests on the main leaderboard** | **Essential** — the paper is about rankings and reports none | low |
| 2c | Bootstrap CI + exact permutation p-value for every ρ | Closes the n = 7 objection | low |
| 2d | `am_design` Stage-1 subgroup coverage analysis | Tests the calibration mechanism | **free** |
| 2e | Cite Candès et al. 2023, Gui et al. 2024, Shorten et al. 2023 | Closes uncited prior art | zero |

### Track 1

| # | Experiment | Status | Cost |
|---|---|---|---|
| **1a** | **E6 branch ablation** (CNN-only, MLP-only, fusion) on accuracy **and** calibration **and** seed variance, with significance tests | **EXISTENTIAL** — determines whether the track has a contribution | 2–4 GPU-h |
| **1b** | **E1 time-blocked significance tests; persist the score archive** | **Essential** — the headline is tested on the wrong protocol, and fixes the missing archive | 2–6 GPU-h |
| 1c | Reconstruction-based baseline, both fair variants | Closes the missing-family objection | 2–4 GPU-h |
| 1d | Threshold sweep / matched-false-alarm comparison | Operational evaluation without inventing a threshold | low, after 1b |

## 7. Reviewer objections, by track

| Track | Most likely objection | Answerable today? |
|---|---|---|
| 1 | "The fusion does not beat its own CNN branch — what is the contribution?" | **No.** Needs 1a |
| 1 | "Significance is only on the temporally interleaved split" | **No.** Needs 1b |
| 2 | "Every baseline is your own; I cannot judge these numbers" | **No.** Needs 2a |
| 2 | "ρ over seven models with no interval or permutation test" | Partly — regret is significant; needs 2c |
| 2 | "Conformalized survival analysis already exists" | **Yes** — cite and reframe as application |
| 3 | **"Brancato reports 0.902 where you report 0.09"** | **No — BLOCKED** |
| 3 | "H6 compares two protocols differing in five ways" | **Disclosed but not answered.** Needs 3b |
| 3 | "The effect reverses on Mission 2" | **Yes** — M2 is near-saturated; anomaly-only metric shows every learned arm at 0.0000 |
| 3 | "The pre-registration was motivated by a test result" | **Disclosed, not answerable.** A caveat the paper must carry |
