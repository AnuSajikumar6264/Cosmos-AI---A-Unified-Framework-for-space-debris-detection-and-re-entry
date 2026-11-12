# Temporal generalization experiments

Date: 2026-11-04. Status: **PARTIAL** — measured on the two existing origins; rolling-origin
validation **NOT RUN** (requires refits).

## What was measured

### 1. Selection does not transfer forward

| Origin | Selected on tune-A | Its test rank | Spearman(tune-A, test) | Cost vs achievable |
|---|---|---|---|---|
| 2016 | `tabm` | 5 of 7 | **+0.000** | **+18.7 %** |
| 2011 | `kumo` | 2 of 7 | **+0.000** | +3.4 % |

### 2. Model ranking is not stable across origins

`physics_only` is **last of 9 at origin 2016** (pinball 0.0892) and **first at origin 2011**
(0.0527). `tabm` is 5th at 2016 and 8th at 2011. No model ranks in the top three at both
origins except the G1 median blend (1st, 3rd).

**There is no "best lifetime model" supported by two origins.**

### 3. Coverage degrades with time from origin (Phase H)

| Origin | Model | cov90 range | Spread | Rank trend with year |
|---|---|---|---|---|
| 2016 | physics_only | 0.732 – 0.974 | **0.242** | **−0.94** |
| 2016 | cosmos_gated | 0.812 – 0.963 | 0.151 | **−0.83** |
| 2011 | cosmos_gated | 0.929 – 0.978 | 0.049 | −0.60 |

Near-monotone decay at origin 2016; small spread at 2011.

### 4. The mechanism — a concrete exchangeability violation

`run.py:split` censors the development set at the forecast origin, so tune-A/tune-B observe at
most ~2,550 days while the test fold reaches 3,951 days (2016) and **5,778 days** (2011). Event
rates differ too (tune-A 0.343 vs test 0.533 at 2016).

This is not generic "distribution shift": the calibration and selection sets are **censored
differently from the evaluation set by construction**. It explains the selection failure, the
coverage failure, the E12 sign reversals and C1's non-reproducibility as one cause.

### 5. Training-window sizes are badly unbalanced

| Origin | train | tune-A | tune-B | test |
|---|---|---|---|---|
| 2016 | 25,371 | 1,741 | 1,560 | 2,993 |
| 2011 | 20,811 | **248** | **332** | 2,680 |

Origin 2011 selects among 7 learners on 248 objects and calibrates conformal intervals on 332.
Any conclusion drawn at origin 2011 is weakly powered for this reason alone.

## What was NOT run, and why

| Experiment | Status | Blocker |
|---|---|---|
| Rolling-origin validation | **NOT RUN** | requires refitting every learner at each new origin |
| Expanding-window validation | **NOT RUN** | same |
| Training-window sensitivity | **NOT RUN** | same |
| Additional forward origins (e.g. 2013, 2018) | **NOT RUN** | same; this is the critical gap |
| Explicit distribution-shift detector | **NOT RUN** | not attempted this pass |
| Solar/geomagnetic regime stratification | **NOT RUN** | space-weather features exist in the cohort; stratified evaluation not performed |
| Launch-family generalization | **PARTIAL** | all intervals already resample launch families, but a held-out-family evaluation was not run separately |

**Rolling-origin validation (G5) is the single highest-value remaining experiment.** Every
candidate in this phase is unconfirmed without it, and so is every claim about which model or
feature group is better.

## Discipline note

The test folds at both origins have been scored repeatedly across the project's history, and
again in Phases E, H and G+. They are **no longer a clean held-out population**. A genuine
confirmatory evaluation needs a temporal origin that has never been scored — which is exactly
what the Phase F snapshot (eligible from 2026-11-26) would provide for the dated forecast, and
what a new lifetime origin would provide for the lifetime subsystem.

## Consequence for the manuscript

Claims of the form "model X is better" or "feature group Y helps" are **not supportable** from
this evidence. The supportable claim is the instability itself:

> Across two forward temporal origins, model ranking, feature-group importance and interval
> coverage all fail to transfer, and the mechanism is a selection/evaluation censoring mismatch
> that is structural in the protocol rather than incidental to it.

That is a measured, falsifiable finding with a diagnosed cause, and it is more defensible than
any performance claim available here.
