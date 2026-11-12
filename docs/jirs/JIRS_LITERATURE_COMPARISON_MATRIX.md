# JIRS literature comparison matrix (Phase 2)

Date 2026-11-04. Positions COSMOS-AI against **JIRS's own recent publications** (prefix `J`) and,
where JIRS has no comparator, against the external verified literature (prefix `R`) from
`docs/research/FINAL_REFERENCE_VERIFICATION_MATRIX.md`.

Verification: all `J` records Crossref-verified (DOI, title, authors, year, type). All `R` records
verified live in the prior phase. **PR** peer-reviewed · **PP** preprint · **DS** dataset deposit.

---

## 1. Candidate contribution A — evidence about when ML model selection can be trusted

| Ref | Work | Year | Venue | Rev. | Measures selection→test transfer? | Multiple temporal regimes? | Space domain? | Occupies A? |
|---|---|---|---|---|---|---|---|---|
| [J1] | Hawkins et al., *Safety Assurance Case for ML Satellite-Based Wildfire Detection* `10.1007/s10846-023-01905-3` | 2023 | **JIRS** | PR | **No** — argues what evidence is *needed*, does not measure transfer | no | **yes** | **No — it poses the question we answer** |
| [J3] | Zhou et al., *Semi-Supervised Federated Fault Diagnosis … High Missing Rate* `10.1007/s10846-023-02025-8` | 2023 | **JIRS** | PR | no | no | no | No |
| [R-G] | Gulrajani & López-Paz, *In Search of Lost Domain Generalization* `arXiv:2007.01434` | 2020 | arXiv/ICLR | PP/PR | **yes** — selection criterion dominates benchmark ranking | no (domain, not temporal) | no | No |
| [R-I] | Inoue, Jin & Rossi, *Rolling window selection …* `10.1016/j.jeconom.2016.03.006` | 2017 | J. Econometrics | PR | **yes** | yes (econometric) | no | No |
| [R-Y] | Yao et al., *Wild-Time* | 2022 | NeurIPS 35 | PR | partly — provides the benchmark, not the transfer measurement | **yes** | no | No |
| [R-H] | Herrmann et al., *Unmasking overestimation …* `10.1007/s12567-023-00529-5` | 2024 | CEAS Space J. | PR | no — metric validity and baseline strength | no | **yes (telemetry)** | No |
| **COSMOS-AI** | ρ(val, test) = **+1.000** (adjacent) → **+0.800** (time-blocked) → **0.000** (multi-year forward), measured in one system across two tasks | — | — | — | **yes** | **yes, three regimes** | **yes** | — |

**Verdict: the intersection is unoccupied, and [J1] is JIRS's own statement of the need.** [J1]
argues that an ML satellite component requires an assurance case; our measurement supplies a class
of evidence such a case needs — *whether the validation procedure used to choose the component
predicts its deployed ranking at all*.

**Status of the claim: EXPLORATORY.** n = 5 and 7, the +0.800 is not significant (p = 0.104), and
the three regimes differ in data, metric and model family as well as in temporal displacement.
This is a hypothesis with a measurement, not a demonstrated mechanism. It must not be presented
otherwise.

## 2. Candidate contribution B — spacecraft telemetry anomaly detection

| Ref | Work | Year | Venue | Rev. | Beats a foundation-model baseline? | Temporal protocol? | Calibration reported? | Compute reported? | Occupies B? |
|---|---|---|---|---|---|---|---|---|---|
| [J2] | Spahic et al., *Warning Identification for Risk-Informed Anomaly Detection* `10.1007/s10846-023-01887-2` | 2023 | **JIRS** | PR | no quantitative detector comparison | no | no | no | **Partly — owns the risk-informed framing** |
| [J3] | Zhou et al., federated fault diagnosis | 2023 | **JIRS** | PR | no | no | no | no | No |
| [R-R] | Ruszczak et al., *The OPS-SAT benchmark …* `10.1038/s41597-025-05035-3` | 2025 | Scientific Data | PR | **provides the benchmark** | official split | no | no | **Owns the dataset, not the result** |
| [R-H] | Herrmann et al., *Unmasking overestimation* | 2024 | CEAS Space J. | PR | shows simple baselines sometimes win | **yes** | no | no | **Owns the genre** |
| **COSMOS-AI (OPS-SAT)** | `hybrid` AUC-PR **0.9719** time-blocked / 0.9855 official; beats `chronos-bolt` by **+0.0316** (95 % CI [0.0134, 0.0558], p < 0.001); ECE 0.035; 74k params; 0.0045 ms/fragment; label-efficiency 0.10–1.00; 5 seeds | — | — | — | **yes** | **yes, both** | **yes** | **yes** | — |
| **COSMOS-AI (ESA-ADB)** | `cosmos_monitor` EW-F0.5 **0.202** = trivial out-of-limits rule; PatchTST **0.496**; 51× the false-alarm rate | — | — | — | **no — we lose** | official | — | — | — |

**Verdict: the positive OPS-SAT result is real, well-instrumented and JIRS-shaped — but it is a
strong result on one benchmark accompanied by a clear failure on a second.** Presenting B alone
would be selective; presenting both is the honest and more interesting paper, and it instantiates
[R-H]'s thesis using the project's own system as the subject.

**Status: VALIDATED (positive) under the official protocol; the time-blocked lead is measured but
NOT significance-tested** — see experiments plan E1.

## 3. Candidate contribution C — learned collision-risk assessment

| Ref | Work | Year | Venue | Rev. | Learned method beats the trivial baseline? | Occupies C? |
|---|---|---|---|---|---|---|
| [J5] | Huang, Petrunin & Tsourdos, *Strategic Conflict Management using Recurrent Multi-agent RL … Considering Uncertainties* `10.1007/s10846-022-01784-0` | 2023 | **JIRS** | PR | reports benefit from learned conflict management (UAM) | **Partly — the affirmative case in JIRS** |
| **COSMOS-AI** | Kelvins CAC, 2,167 events: `latest_risk_point` **F2 = 0.739**; best learned arm **0.168**; six of eleven arms **F2 = 0.000** | — | — | — | **No — every learned arm loses heavily** | — |

**Verdict: a clean negative result with a direct JIRS comparator.** This is publishable as a
counterpoint to [J5] and the learned-conflict-management literature, provided it is framed as
*"on this official challenge dataset, with these arms"* and not as a claim about learned collision
avoidance in general.

## 4. Candidate contribution D — cross-domain / multi-source evidence fusion

| Ref | Work | Year | Venue | Rev. | Demonstrates benefit from fusion? | Occupies D? |
|---|---|---|---|---|---|---|
| [J4] | Harbaoui et al., *Context Adaptive Fault Tolerant Multi-sensor Fusion* `10.1007/s10846-023-01906-2` | 2024 | **JIRS** | PR | **yes** — fail-safe localisation | **Yes, affirmatively** |
| **COSMOS-AI** | C1 **NOT REPRODUCIBLE** (same-learner: −0.0514 / +0.0026, significant at neither origin); C2's deployed arm p = 0.364; C3 INCONCLUSIVE; C4 **NOT EVALUABLE** (0 joinable pairs) | — | — | — | **No** | — |

**Verdict: we have the negative counterpart to [J4].** We must not claim a validated fusion
contribution. The defensible statement is that cross-*domain* fusion (health → lifetime → debris →
risk) showed no reproducible predictive value in our system, which is a different and weaker
proposition than [J4]'s multi-*sensor* fault-tolerant fusion and should not be presented as
contradicting it.

## 5. Candidate contribution E — intelligent decision support

| Ref | Work | Year | Venue | Rev. | Validated against outcomes? | Occupies E? |
|---|---|---|---|---|---|---|
| [J2] | Spahic et al., risk-informed warning identification | 2023 | **JIRS** | PR | framework with demonstration | **Yes** |
| [J6] | Chirala et al., *UV Mission Planning Under Uncertainty* `10.1007/s10846-023-01860-z` | 2023 | **JIRS** | PR | optimisation formulation | partly |
| **COSMOS-AI** | Decision layer implemented; abstention and evidence-gating real; **no decision-quality metric, no regret measure, no operator study, no outcome scoring anywhere** | — | — | — | **NO** | **No — cannot be claimed** |

**Verdict: E is not available as a contribution.** The architecture exists and is honest
(unavailable evidence is declared, not imputed; `priority_score` is deliberately unset where it
cannot be justified), but nothing establishes that the resulting prioritisation is good. Claiming a
validated intelligent decision-support system would be unsupported. This is the single largest gap
relative to JIRS's expectations.

## 6. Candidate contribution F — orbital lifetime benchmark (the drafted manuscript)

| Ref | Work | Year | Venue | Rev. | Occupies F? |
|---|---|---|---|---|---|
| [R-Zh] | Zhou et al., *Orbital Decay Prediction in LEO …* `10.1029/2025JA034593` | 2026 | JGR Space Phys. | PR | No — one platform, SMA loss over hours–days |
| [R-He] | He et al., *Expandable Orbit Decay Prediction Using Continual Learning* `10.1155/2024/8887634` | 2024 | Int. J. Aerospace Eng. | PR | No — proposes a solution, undisclosed protocol |
| [R-S] | Salmaso et al. `10.3390/aerospace10030297` | 2023 | Aerospace | PR | No — >400 objects, no censoring treatment |
| **COSMOS-AI** | 64,516-row cohort; three temporal origins; capped log-lifetime quantiles; launch-family-clustered intervals; archived per-object predictions | — | — | — | **Yes** |
| **JIRS comparator** | **none found in 282 records** | — | — | — | — |

**Verdict: scientifically defensible, and venue-inappropriate.** F is a real contribution with no
JIRS comparator in three years of output. It belongs in a space or data venue. Within a JIRS
submission it should appear as **supporting evidence for contribution A** — the hard end of the
temporal-displacement spectrum — not as the paper's subject.

## 7. Summary

| Contribution | Evidence status | JIRS comparator | JIRS fit | Recommendation |
|---|---|---|---|---|
| **A** selection-transfer reliability across temporal regimes | **EXPLORATORY** | [J1] poses the need | **Strong** | **Lead contribution — after confirmatory work** |
| **B** spacecraft telemetry anomaly detection | **VALIDATED positive** (official protocol) + **validated negative** (ESA-ADB) | [J2], [J3] | **Strong** | **Co-lead — supplies the positive case for A** |
| **C** learned collision risk loses to a trivial baseline | VALIDATED negative | [J5] | Moderate | Supporting section |
| **D** cross-domain fusion | **NOT DEMONSTRATED** | [J4] affirms the opposite | Moderate | Report as negative; do not claim |
| **E** intelligent decision support | **NOT VALIDATED** | [J2], [J6] | Would be strongest | **Cannot claim** — needs new work |
| **F** orbital lifetime benchmark | VALIDATED negative | **none** | **Weak** | Demote to supporting evidence for A |

**The JIRS-viable paper is A + B, with C, D and F as supporting evidence, and E excluded.** That
is a different paper from the one drafted, and it is built entirely from results the project
already owns — except that A is currently exploratory and must be made confirmatory before it can
lead.
