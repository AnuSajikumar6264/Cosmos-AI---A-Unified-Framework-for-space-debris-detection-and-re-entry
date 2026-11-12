# JIRS simulated peer review (Phase 7 / Part 11)

Date 2026-11-04 · subject: `paper/journal/manuscript.md` as it stands, submitted **unchanged** to
JIRS

Three reviewers with distinct expertise. I have not made them agree, and I have not made them
kind. Each verdict is argued from the manuscript and the artifacts.

---

## Reviewer 1 — Intelligent-systems methodology

### Overall assessment

This is a carefully executed empirical study submitted to the wrong journal. I searched the
manuscript for an intelligent-systems contribution and could not find one. There is no algorithm,
no architecture, no agent, no control loop, no autonomy, and no decision-making component under
evaluation. What I find is a benchmark for predicting when space debris will re-enter the
atmosphere, together with an honest report that the authors' model-selection procedure does not
predict forward performance and that their own pipeline cannot be retrained.

The statistical care is above average and the authors' candour is unusual and commendable. But
JIRS publishes intelligent and robotic systems. The paper's own related-work section cites
Scientific Data and CEAS Space Journal as its venue precedents, and **cites not a single paper
from this journal.** That is itself diagnostic.

### Major concerns

1. **No methodological contribution.** The methods used — quantile regression, gradient boosting,
   conformal prediction, cluster bootstrap — are all standard and correctly applied. Correct
   application of standard methods is not a methodological contribution.
2. **The headline statistic is not credible as stated.** The central result is a Spearman
   correlation of exactly 0.000, twice. §13 concedes it is computed over **seven** learners, with
   a 95 % interval of approximately [−0.77, +0.77] and no permutation test. The authors are honest
   about this, which I appreciate, but honesty about an underpowered statistic does not make it
   load-bearing. The paper's central claim rests on a quantity that is statistically
   indistinguishable from strong positive transfer.
3. **The pre-registered experiment is inconclusive.** Of three hypotheses, one is NOT_EVALUABLE,
   one UNDERPOWERED, and the third is met by chance one time in five (§10.2). The authors say so.
   I am then left asking what the pre-registration bought.
4. **The ablations cannot support their conclusions.** §8.2 discloses that every ablation arm is
   untuned and inherits its parent's hyperparameters. Every feature-attribution claim therefore
   has a known bias in a known direction.
5. **Tuning is not comparable across arms.** Two learners carry one hyperparameter; others carry
   six. A ranking over unequally tuned models is not a ranking of the models.

### Minor concerns

- Figures are listed by filename rather than embedded with captions.
- "17 arms" versus "19 arms" requires the reader to track a convention.
- §15 lists as limitations several items §12 argues are contributions.

### Missing experiments

A controlled variation of the temporal gap with task, data and metric held fixed. The authors'
own §11 observation about degradation ratios hints at it, and then they correctly refuse to claim
it. Without that experiment there is no mechanism and no methodological result.

### Unsupported claims

None, to the authors' credit. §2 of their claims matrix is more conservative than most published
papers. I could not find an overclaim.

### Likely rejection reasons

Scope, first and decisively. Then the absence of a methodological contribution.

### Required revisions

Demonstrate an intelligent-systems contribution, or submit elsewhere. If the former: formalise the
selection-transfer problem, test it in a controlled design, and relate it to this journal's
literature on assurance and fault diagnosis.

### **Recommendation: REJECT** (resubmit elsewhere, or after fundamental reframing)

---

## Reviewer 2 — Aerospace and orbital engineering

### Overall assessment

The orbital-mechanics treatment is sound and in places better than typical for this literature.
The estimand is well chosen: capping time-to-decay at five years and modelling
`log10(min(t, 1826.25))` is the right response to a multi-decade dynamic range with a fixed
observation horizon, and the authors correctly identify the resulting point mass as the dominant
feature of the loss landscape. Clustering inference by launch family is exactly right — objects
from one launch share a ballistic family and an orbit, and most papers in this area ignore this.
The verified temporal split construction is better than the random splits common in orbital ML.

I have two substantive engineering objections and one observation about venue.

### Major concerns

1. **The physics baseline is too weak to anchor the comparison.** §13 concedes that "every
   reference point in this work is our own" and that an ML-dSGP4-class comparison was not
   attempted because TLE, B\* and ephemeris data are not held. A drag-based analytic estimate is
   not the state of the art in decay prediction. When the authors report that this baseline ranks
   first of seventeen at one origin, I cannot tell whether that is a strong result about the
   baseline or a weak result about the learned arms. **Without B\*-derived or SGP4-propagated
   baselines, the headline comparison is uncalibrated.**
2. **Area-to-mass and attitude are the dominant physical uncertainties and are handled only
   implicitly.** The feature set includes design-class and RCS proxies, which is reasonable given
   public data, but a tumbling rocket body's effective drag area varies by a factor of several and
   the paper does not characterise how much of the irreducible error this accounts for. The
   at-cap/below-cap loss decomposition is interesting but is not a substitute.
3. **Operational relevance is asserted rather than demonstrated.** The introduction motivates from
   debris mitigation, launch licensing and collision avoidance. The paper then never shows that any
   of its outputs would change an operational decision. §10.7's forecast is registered and
   unscored, and the authors correctly decline to call it prospective.

### Minor concerns

- A single catalogue snapshot (2026-10-27) with no sensitivity analysis to snapshot date.
- Controlled objects are excluded, correctly, but the consequence for population-level debris
  conclusions is not discussed.
- The solar-cycle phase of each origin window is not reported, and it plausibly explains part of
  the cross-origin instability — origins 2006, 2011 and 2016 sit at different points of the cycle.
  **This is a physical confound the paper does not address and should.**

### Missing experiments

Solar-cycle stratification of the instability result. An external propagator baseline. Sensitivity
to the five-year cap.

### Unsupported claims

The claim that loss concentrates below the cap is now correctly attributed to one named arm with
the all-arm spread given. I found no physical overclaim.

### Likely rejection reasons

For *this* journal, scope. The work has no robot and no intelligent control loop. I would be glad
to review it for Acta Astronautica, Advances in Space Research or the Journal of Space Safety
Engineering, where its baselines would be challenged harder and its temporal protocol would be
appreciated more.

### Required revisions

Add a propagator-based baseline; address the solar-cycle confound; demonstrate operational
consequence or drop the operational motivation.

### **Recommendation: REJECT for JIRS** (scope). **Major revision if submitted to an aerospace venue.**

---

## Reviewer 3 — Experimental methodology and reproducibility

### Overall assessment

Methodologically this is among the more trustworthy manuscripts I have reviewed. The authors
pre-registered a hypothesis set, sealed it by hash before fitting, logged deviations in a separate
file, verified temporal ordering and launch-family disjointness mechanically, used cluster-aware
inference with multiplicity correction, excluded a scoring function on elicitability grounds and
enforced that exclusion with a test, and re-derived every headline number from its archive to zero
deviation. Several self-corrections are recorded that weaken the authors' own claims, including a
coupling verdict reversed from "partially supported" to "not reproducible" by their own
de-confounding experiment.

I therefore have an unusual position: I trust these numbers more than most, and I still cannot
recommend acceptance.

### Major concerns

1. **The artifact does not exist.** §14 carries a `[PENDING EVIDENCE]` marker: no DOI, no deposit,
   no repository URL, no licence. This is a benchmark paper. **I cannot review a benchmark I cannot
   obtain, and it should not have been submitted in this state.**
2. **The benchmark is not training-reproducible, and the authors say so.** Five of seven learner
   backends are undeclared, one is a commercial vendor library, no environment was recorded for any
   published run, and a provenance module that would have captured it exists and is never called.
   The authors' handling is exemplary — they distinguish prediction-level from training-level
   reproducibility and refuse to install current versions to fake a refit. But the consequence is
   real: **the reproducibility gap destroyed the power of their only pre-registered experiment**,
   reducing it from seven learners to two. That is the paper's most important finding and it is
   buried in §12.2.
3. **No uncertainty on the main leaderboard.** The bootstrap machinery is applied to couplings,
   coverage and slices, but §10 reports leaderboard point values and ranks with no per-arm interval
   and no paired test. The paper's entire argument is about rankings.
4. **The H2 null is the wrong null.** The authors report that their criterion is met by chance with
   probability 0.199 under independent uniform rankings, which is admirable. But the apt null is
   sampling noise around a *stable* ordering, which requires a bootstrap of each origin's test fold
   — computable from their own archives without refitting. As it stands a weak statistic is
   defended against a straw-man null.
5. **No external baseline anywhere in the lifetime work.** Conceded in §13.

### Minor concerns

- Literature search not depositable (conceded in §13) despite six contributions withdrawn on
  located prior art.
- Runtime measurements reported without hardware, thread or batch configuration.
- Origin-2006 prediction archive is not checksummed, though every other key artifact is.

### Missing experiments

Bootstrap reference distribution for the instability criterion. Per-arm leaderboard intervals.
Selection regret, which is the operationally meaningful quantity and is absent.

### Unsupported claims

I searched for these specifically and found none. The claims matrix is more disciplined than the
manuscripts I usually review.

### Likely rejection reasons

The missing artifact, first. Then venue scope.

### Required revisions

Deposit the benchmark and cite its DOI. Add leaderboard intervals and selection regret. Replace
the instability null with a bootstrap reference. Promote the reproducibility-cost finding from the
discussion to a contribution.

### **Recommendation: MAJOR REVISION** — and I would transfer to a venue where a benchmark
contribution is in scope.

---

## Editor's synthesis

| Reviewer | Recommendation | Primary ground |
|---|---|---|
| R1 intelligent systems | **REJECT** | No intelligent-systems contribution; out of scope |
| R2 aerospace | **REJECT for JIRS** | Out of scope; baselines uncalibrated; solar-cycle confound |
| R3 methodology | **MAJOR REVISION** | Artifact unobtainable; statistical gaps — but trusts the work |

**Predicted outcome if submitted unchanged: desk rejection on scope, before these reviews are
written.** Two of three reviewers reject on scope grounds, and the editor sees it first.

## The strongest rejection argument

Not the statistics, not the reproducibility, not the artifact — all three are fixable and the
authors have already disclosed them.

> **The manuscript contains no intelligent system.** JIRS publishes intelligent and robotic
> systems; 56.4 % of its 282 records since 2023 are explicitly robotics and 2.1 % are
> space-related. This manuscript presents a statistical benchmark for atmospheric re-entry timing.
> It has no agent, no controller, no autonomy, no decision component under evaluation, and it cites
> no paper from the journal it is submitted to. The one component that would be in scope — the
> decision-support layer — is implemented but has **no outcome-scored evaluation of any kind**, so
> it cannot be claimed.

This argument cannot be answered by revision of the present manuscript. It can only be answered by
making a different paper — one built on the project's anomaly-detection evidence and its
selection-reliability measurement, which would give JIRS an intelligent-monitoring result, a
reliability contribution, and a reason to cite [J1], [J2] and [J3].

## What the reviewers agreed on

Worth recording, because it is the project's genuine standing:

- The statistical and reproducibility discipline is **above the norm** for this literature (R1, R3).
- **No unsupported claim** could be found by any reviewer (R1, R2, R3).
- The temporal-split construction and cluster-aware inference are **correct and unusually careful**
  (R2, R3).
- The self-corrections — especially the reversal of coupling C1 — **increase trust** (R3).
- The work would be **better received at an aerospace or data venue** (R2, R3).
