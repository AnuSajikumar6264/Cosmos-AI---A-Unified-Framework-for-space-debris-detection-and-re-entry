# Research gap analysis (2023–2026 literature vs COSMOS-AI evidence)

Date: 2026-11-04. Derived from [`LITERATURE_REVIEW_2023_2026.md`](LITERATURE_REVIEW_2023_2026.md).
**Literature findings are kept strictly separate from experimental evidence; no experimental
result was changed to fit this analysis.**

## 1. Gaps that are real, and whether we occupy them

| Gap | Established by | Do we occupy it? | Strength |
|---|---|---|---|
| **G-A** No catalogue-scale, forward-in-time, time-to-decay benchmark with censoring | [R1] event-based on one platform; [R3] ~400 objects; [R2] protocol undisclosed; [R4] survey silent on evaluation | **Yes** — 31,396 objects, 2 published origins + 1 unexamined, censored capped target, launch-family clusters | **Strongest remaining claim** |
| **G-B** Model-selection validity unexamined in orbital prediction | [R4] (53 cit.) frames the open problem as accuracy only; no orbital paper tests selection transfer | **Yes** — Spearman 0.000 at both origins; rank inversion 17/17 → 1/17 | **Defensible as a domain first** |
| **G-C** Conformal coverage behaviour unstudied under *orbital* temporal shift | strict search: 1 of 15 genuine conformal-in-space hits ([R20]); 0 for conjunction | **Partly** — we measure it, but the phenomenon is a theorem ([R23]) and the audit design is published ([R21]) | **Weak — application only** |
| **G-D** Evaluation-population composition effects for censored orbital targets | no precedent located | **Partly** — measured (cap-mass shift reverses; loss 4.1–6.6× below cap) but the mechanism is **NOT CONFIRMED** by our own G5 test | **Weak — unconfirmed** |
| **G-E** No predictive health-and-orbital satellite digital twin in recent literature | [R32][R33][R34] — the term is occupied by networking work | Nominally yes | **Not a contribution** — Phase E refuted the integration premise |

## 2. Gaps we previously claimed that are now closed

| Previously claimed | Closed by | Action |
|---|---|---|
| Novel temporal calibration-failure analysis | [R21] (journal, 2026, cluster bootstrap, rolling-origin), [R23] (bound increasing in horizon), [R22] (coverage-gap theorem) | **Remove the novelty claim; cite all three** |
| Novel coherent multi-horizon calibration | [R25] Isotonic Distributional Regression (JRSS-B 2021) | **Report as a design diagnostic with the fix cited** |
| Novel evidence-graded abstention | [R19] TC-CAD (budgeted deferral + adaptive conformal on ESA-ADB), plus the general abstention literature | **Remove entirely** |
| Conformal prediction on spacecraft telemetry at multiple horizons | **[R20]** Nan Lu et al., PLoS ONE, 2026-10-13 | **Remove novelty; cite** |
| Integrated cross-domain framework improving prediction | refuted by **our own** Phase E/E12/G5 results | **Remove** |
| Debris-detection contribution | [R27]–[R31] are radar/optical detection papers well beyond our SpotGEO reimplementation | **Present as infrastructure only** |

## 3. The newly discovered positioning constraint

**[R9] Herrmann et al. 2024 (CEAS Space Journal, ESA-funded, 23 citations)** already established,
in a peer-reviewed space journal, that:

- deep anomaly-detection performance on spacecraft telemetry is **overestimated**;
- **simple baselines sometimes beat complex models**;
- metric choice matters and should be "less accuracy-inflating";
- the field needs **"high-quality, pre-split datasets"**.

This cuts both ways and both must be stated:

**Helps us.** It proves the negative-results-and-benchmark genre is publishable in this field,
that "a parameter-free combination beats the deployed fusion by 19.4 %" is the kind of finding
this community accepts, and that releasing a pre-split benchmark is a recognised contribution.

**Constrains us.** We cannot present overestimation, baseline-beats-complex, or metric-validity
as discoveries. We are **extending an established line into orbital lifetime prediction**, and
the manuscript must say so in the introduction, not bury it in related work.

## 4. What the field thinks its problem is, versus what we studied

[R4] Caldas & Soares (53 citations) frames the open problem as **accuracy**: km-scale 7-day
errors from initial-state uncertainty, environment prediction error, and unmeasured physical
properties.

We studied none of those. We studied **evaluation validity** — whether the measured ranking
means anything out of sample. That is a different axis, and it is unoccupied in this field.

This is the sharpest available framing: *the orbital-prediction literature optimises accuracy
against benchmarks whose selection protocol has never been validated; we show that on a
catalogue-scale forward-in-time benchmark the selection protocol carries no information, so
reported rankings do not transfer.*

## 5. Unresolved in the literature **and** unresolved by us

Honesty requires listing these separately from our contributions:

1. Whether a censoring-matched or survival-aware selection objective fixes the transfer failure
   — our G5d/G6 arms were not run (G5d was blocked by missing dependencies).
2. Whether adaptive/windowed conformal ([R23]'s AcMCP, ACI) restores coverage on orbital data —
   our G3 arm was not run.
3. Whether physics-as-prior-plus-learned-residual is more stable than physics-as-features —
   our G4 arm was not run.
4. Whether the cap point-mass mechanism is real — our own test **refuted** its prediction
   (+0.891 vs −0.158).
5. Whether any coupling adds value — **no**, on our data, and no competing positive claim found.

## 6. Defensible contribution set, final

In descending order of strength:

1. **A catalogue-scale, forward-in-time orbital lifetime/re-entry benchmark** with censoring-aware
   quantile targets and launch-family-clustered intervals. *Artifact contribution.* Precedent for
   publishing it: [R15] in *Scientific Data*.
2. **A first measurement of model-selection non-transfer in orbital lifetime prediction**:
   Spearman 0.000 at both origins, rank inversion 17/17 → 1/17, 23.64 % of evaluation-slice
   pairs inverted. *Domain-first measurement of a phenomenon established elsewhere.*
3. **A reproducibility failure analysis**: 2 of 7 learners reinstallable, including **both**
   selected learners; published values recomputable from archived predictions but models not
   refittable. *Directly answers [R9]'s call for high-quality pre-split datasets by showing what
   goes wrong without one.*
4. **Narrow measured findings**: loss concentration 4.1–6.6× below the cap; learner-dependent
   feature sign reversals significant in both directions.
5. **Preserved negative results**: coupling does not improve prediction; the point-mass mechanism
   is not confirmed; C4 is structurally unevaluable.

## 7. Claims that must not appear

- "novel conformal/calibration method" — none exists ([R20]–[R25])
- "first to show coverage degrades with horizon" — a theorem ([R23])
- "novel evidence-graded abstention" — [R19] and two surveys
- "integrated framework improves prediction" — refuted by our own ablations
- "novel digital twin" — drop the framing
- "debris-detection contribution" — [R27]–[R31] are far beyond it
- "we discovered that simple baselines beat complex models" — [R9] established it
- any Scopus rank or Q1 claim — unverifiable from available sources
