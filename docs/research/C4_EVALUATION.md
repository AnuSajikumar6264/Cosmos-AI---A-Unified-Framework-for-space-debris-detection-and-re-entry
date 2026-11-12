# C4 evaluation — health flags → high-risk conjunction escalation

Verdict: **NOT EVALUABLE**. Date 2026-11-04.
Source: `outputs/phase_e/phase_e_results.json` (`C4`).

This is not "we did not get to it". The dataset join the hypothesis requires **does not exist**
in any source available to this project, so the hypothesis cannot be tested at all.

## Hypothesis

Telemetry-derived health flags identify conjunctions in which the operator may be unable to
manoeuvre, improving **decision priority** for those conjunctions.

## Scientific rationale, and its strict boundary

A satellite that cannot manoeuvre cannot execute a collision-avoidance manoeuvre. If health
telemetry indicates degraded manoeuvre capability, a conjunction involving that satellite
warrants different **operational handling** — earlier notification, longer lead time, or
escalation to a human decision-maker.

The boundary, which must never be crossed: a health anomaly changes **nothing** about the
physical probability of collision. The probability depends on relative geometry and state
covariance, not on the spacecraft's internal condition. The coupling may only affect
**priority, consequence assessment or decision routing**.

This separation is enforced in code, not just in prose:

- `cosmos/ai/adapters.py:collision_risk` leaves `priority_score` unset;
- `tests/test_product.py::test_12_physical_probability_is_separate_from_operational_priority`
  asserts the field stays `None`;
- `tests/test_couplings_regression.py::test_c3_escalation_rule_never_raises_physical_risk`
  asserts a health alarm below threshold cannot manufacture a high-risk conjunction;
- the console's risk table renders the priority column empty by construction.

## What the coupling would change

An **operational decision**, not a physical prediction. The evidence bar is therefore
different: it needs outcomes about decisions (was a manoeuvre needed, possible, performed?),
not about orbital dynamics.

## Required data join

| Requirement | Why |
|---|---|
| Spacecraft health telemetry with resolvable identity | to derive the health flag |
| Conjunction data messages for the **same** spacecraft | to attach the flag to a conjunction |
| Shared identifier between them | to perform the join |
| Decision or manoeuvre outcome | to score decision quality |

## Sources examined in this repository

| Source | Identity key | Spacecraft identifiable | Telemetry | CDMs | Usable for C4 |
|---|---|---|---|---|---|
| ESA-ADB (Missions 1–3) | anonymised mission + channel | **No** | Yes | No | No |
| ESA Kelvins CAC | positional event index | **No** | No | Yes | No |
| OPSSAT-AD | single spacecraft, no CDMs | partly | Yes | No | No |
| NASA SMAP/MSL | spacecraft telemetry, no CDMs | partly | Yes | No | No |
| CelesTrak / GCAT catalogue | **NORAD ID** | Yes | **No** | **No** | No |

**Joinable pairs: 0.**

The structure of the problem is that the two sources carrying the required variables are
anonymised *by construction* — ESA-ADB anonymises missions as a release condition, and the
Kelvins challenge anonymised its CDMs to permit public distribution. The only identifiable
source, the catalogue, carries neither telemetry nor conjunction messages.

No amount of engineering removes this. It is not a gap in the pipeline; it is the absence of a
dataset.

## What was deliberately not done

A superficially convincing C4 result is easy to manufacture: take the highest-risk Kelvins
event, attach it to an arbitrary non-operational catalogue payload, and report that the
escalation rule fired. The repository contains exactly such a **demonstration**
(`cosmos/ai/twin/couplings.py:c4_demo`), and its own docstring states that the conjunction
forecast and the payload states come from *different objects*.

That demonstration is **not** evidence, is never reported as evidence, and is excluded from
every quantitative claim. In the orchestrated pipeline and the product, C4 **abstains** with the
reason recorded in the run manifest and shown in the interface.

## Independent dataset search

Assessed against the project's legal and access constraints:

| Candidate | Status | Reason |
|---|---|---|
| Operator-held telemetry + CDM archives | **Not obtainable** | requires operator cooperation and a data-sharing agreement; commercially and legally restricted |
| Space-Track CDM archive | **Not obtainable here** | requires an account; redistribution restricted; and it carries no telemetry to join |
| ESA DISCOS | Not sufficient | object characteristics, not telemetry or per-event CDMs |
| Published conjunction case studies | Not sufficient | narrative accounts, not a dataset with health variables and outcomes |
| Synthetic coupled dataset | **Refused** | would test the rule's arithmetic, not the hypothesis; results on synthetic joins are not evidence about reality |

Obtaining a valid C4 dataset requires **user action**: an operator data-sharing agreement, or
licensed access to a linked archive. Neither can be initiated from this environment.

## Conclusion

**NOT EVALUABLE.** No effect, interval or p-value is reported, and
`tests/test_phase_e.py::test_c4_is_not_evaluable_and_says_why` asserts that none appears in the
results file.

For the manuscript, C4 must be presented as a **design element with an enforced safety
property** — health evidence cannot alter physical collision probability, and the system
abstains rather than guessing — and explicitly **not** as a validated or evaluated coupling.
It should not be counted among the empirical contributions.
