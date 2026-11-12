# ML-dSGP4 as a physics baseline — feasibility assessment

Date: 2026-11-04. **Verdict: fair comparison is IMPOSSIBLE. Not implemented, and the reason is
structural rather than a matter of effort.**

Reference [7], verified directly from the arXiv record and Crossref during this assessment:

> Acciarini G., Baydin A.G., Izzo D. — *Closing the Gap Between SGP4 and High-Precision
> Propagation via Differentiable Programming* — *Acta Astronautica* 226(1), 2025 —
> `10.1016/j.actaastro.2024.10.063` — arXiv:2402.04830v5.

## Three independent incompatibilities

### 1. Required input does not exist in this project

The abstract states the method performs "embarrassingly parallel orbital propagation across
batches of **Two-Line Element Sets (TLEs)**", and that fine-tuning uses "specific ephemeris or
high-precision numerical propagation data".

Measured in this repository:

| Required input | Present? | Evidence |
|---|---|---|
| TLEs | **No** | `find data -iname "*tle*"` returns nothing |
| B\* drag term | **No** | no column matching `bstar`/`star`/`drag` among the cohort's 51 columns |
| Ephemeris / high-precision orbit products | **No** | not in any dataset manifest |

This is limitation **L4**, recorded since Phase A: no TLE or orbital-element histories at
catalogue scale. Space-Track requires an account and restricts redistribution, so the input
cannot be obtained without credentials and a licence review.

### 2. The prediction target is a different quantity

| | ML-dSGP4 | COSMOS-AI benchmark |
|---|---|---|
| Predicts | "satellite **positions** at future times"; positions, velocities, state transition matrix, propagated covariance | `z = log10(min(time_days, 1826.25))` — **time to decay** |
| Type | instantaneous state at a requested epoch | a scalar time-to-event with a point mass at a cap |
| Evaluated by | position/velocity error against ephemeris | pinball loss on quantiles; interval coverage |

A state-vector propagator and a time-to-event predictor are not comparable on the same metric.
There is no transformation of one into the other that preserves the estimand.

### 3. Deriving a lifetime from SGP4 would be circular here

One could in principle propagate with dSGP4 until the altitude crosses a re-entry threshold and
read off a lifetime. That route fails for this benchmark:

- it needs a **TLE including B\***, which is absent (see 1);
- **B\* is itself fitted to observed orbital decay.** Using a catalogue-fitted drag term to
  predict decay time would leak the outcome into the predictor — the same category of error as
  the study's own deliberately-labelled `plus_rcs_2026` leak arm;
- SGP4's drag treatment is a simplified analytical model keyed to B\*, not an atmospheric-density
  integration, so it is not the physics baseline a reviewer would want for a decay study. The
  abstract makes no claim of validity in the decay regime.

## The project already has the appropriate physics baseline

`physics_only` is a Monte-Carlo drag expert over NRLMSIS-2.1 atmospheric density with sampled
area-to-mass ratios (`cosmos/ai/lifetime/physics.py`). It predicts **time-to-decay directly**,
consumes only catalogue mean elements and space-weather indices that the project has, and is
already present in **every** comparison at both origins.

Its measured behaviour is one of the project's headline findings:

| Origin | `physics_only` pinball | Rank of 9 |
|---|---|---|
| 2016 | 0.089249 | **9 (last)** |
| 2011 | 0.052676 | **1 (first)** |

Across the 11 G5 evaluation slices its rank spans **1 to 11**. So the benchmark already
contains a physics baseline that is competitive at one origin, worst at another, and maximally
unstable — which is a stronger and more informative result than adding a propagator that
cannot address the target.

## What would be needed to add ML-dSGP4 later

1. A licensed TLE archive with B\* covering 1957–2026 at catalogue scale (Space-Track account
   plus redistribution review) — **requires user authorisation**.
2. A re-specified estimand: either a position-error benchmark (a different paper), or a
   decay-time derivation with an explicit treatment of B\*-induced outcome leakage.
3. Installation of `dsgp4` (not currently in the environment; a network action).

None of these is a coding task, and the second is a change of research question.

## Recommendation for the manuscript

State plainly that ML-dSGP4 was **assessed and excluded** with the three reasons above, cite
[7], and present `physics_only` as the physics baseline with its instability as a finding. A
reviewer who asks "why not dSGP4?" is answered by the input-availability and estimand
arguments, not by an apology.

## Status

| Item | Status |
|---|---|
| ML-dSGP4 reference verified | **PASS** — arXiv + Crossref, inputs and outputs quoted |
| TLE / B\* / ephemeris inputs available | **FAIL** — none present (L4) |
| Target compatibility | **FAIL** — state vector vs time-to-decay |
| Fair comparison possible | **NOT_EVALUABLE** |
| Appropriate physics baseline present | **PASS** — `physics_only`, NRLMSIS-2.1 Monte Carlo |
| Implemented | **No**, with documented justification |
