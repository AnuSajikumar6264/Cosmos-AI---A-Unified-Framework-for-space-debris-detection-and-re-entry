# JIRS novelty and contribution assessment (Phase 3)

Date 2026-11-04. Assesses the seven candidate contributions you listed, each against the evidence
the project actually owns and against JIRS's own recent output.

**Status vocabulary, applied strictly:**

| Term | Meaning |
|---|---|
| **Implemented** | Code exists, runs, passes software tests. Establishes nothing scientific. |
| **Validated** | Measured against an external benchmark with appropriate statistics. |
| **Confirmatory** | Pre-registered before the evidence existed, evaluated on a never-scored fold. |
| **Exploratory** | The outcome was inspected before the analysis was designed. |
| **Inconclusive** | Evaluated; the evidence does not decide. |
| **Not demonstrated** | Tested and the hypothesis was not supported. |
| **Unsupported** | Claimed with no corresponding evidence. |

---

## Contribution 1 — Evidence-aware model selection

**Research problem.** When an ML component is chosen for a spacecraft system by held-out
validation, does that choice predict which component will actually perform best in deployment?

**Gap.** [J1] (Hawkins et al., JIRS 2023) argues that a machine-learned satellite component needs
a safety-assurance case built from evidence about its behaviour. It does not say what evidence
establishes that the *selection procedure* was sound. No JIRS paper in 282 records from 2023
onward measures selection→deployment rank transfer.

**What exists already.** Gulrajani & López-Paz (2020) showed the selection criterion dominates
domain-generalisation rankings; Inoue, Jin & Rossi (2017) showed window choice changes
out-of-sample conclusions in econometrics; Yao et al. (2022) built a temporal-shift benchmark.
All outside aerospace, none measuring the transfer directly in an engineering system.

**What COSMOS-AI adds.** A direct measurement in one system, across three regimes of temporal
displacement:

| Regime | Spearman(validation rank, test rank) | n | p |
|---|---|---|---|
| OPS-SAT, official split (temporally adjacent) | **+1.000** | 5 | < 0.001 |
| OPS-SAT, time-blocked | **+0.800** | 5 | 0.104 |
| Orbital lifetime, forward origins (multi-year gap) | **0.000** | 7 | not computed |

**Supporting evidence.** `outputs/benchmarks/telemetry_opssat/per_run_{official,time_blocked}.csv`
(`val_auc_pr` vs `auc_pr`, 5 seeds); `outputs/phase_g_lifetime/phase_g_lifetime_results.json`
(`n_models_compared: 7`, ρ = 0.000 at both origins). All verified.

**Contradicting evidence, stated.**
- The three regimes differ in **dataset, task, metric and model family** as well as in temporal
  displacement. The ordering is **confounded**; temporal gap is one of several possible causes.
- n = 5 and n = 7. The +0.800 is **not significant** (p = 0.104). At n = 7 the 95 % interval around
  ρ̂ = 0 spans roughly [−0.77, +0.77].
- I computed this diagnostic during the audit, after all outcomes were known. It is **post hoc**.
- The lifetime selection split holds only 248 objects at origin 2011, so selection noise is a live
  rival explanation for ρ = 0.

**Limitations.** No per-regime confidence interval; no permutation test; no controlled variation of
the temporal gap with everything else held fixed.

**Novelty assessment.** **Genuinely novel as a measurement, and the right question for JIRS** —
but currently **EXPLORATORY**. The phenomenon (selection fragility) is established elsewhere; the
contribution is measuring *when it bites* inside a working spacecraft-analytics system, which
nobody has done.

**JIRS suitability.** **High** — it converts [J1]'s assurance question into a measurable property.
**Not submittable in its current exploratory state as a lead claim.**

## Contribution 2 — Temporal reliability of predictive intelligent systems

This is Contribution 1 generalised, and the honest framing of the whole project. Assessment is the
same: the measurement is real, the interpretation is exploratory, and the mechanism is unestablished.

One addition the project does own at confirmatory status: **ranking instability across temporal
origins was pre-registered and tested on a never-scored fold** (G5d H2, SUPPORTED as
pre-registered). But its criterion has a chance level of **0.199** under random rankings at the
realised arm counts — above the 0.167 at which H3 was closed as underpowered — so it is a sealed
replication with low power, not a confirmation. That assessment is already locked in
`docs/research/FINAL_RESEARCH_CONTRIBUTION_AND_CLAIMS.md` and is unchanged here.

**Novelty: moderate-to-high. Status: part confirmatory-but-underpowered, part exploratory.**

## Contribution 3 — Physics-based versus learned model comparison

**What the evidence shows.** A physics-only analytic drag baseline ranks **1st of 17** arms at
orbital-lifetime origin 2011 and **17th of 17** at origin 2016, and moves between rank 1 and rank
11 across eleven evaluation slices. On collision risk, a trivial `latest_risk_point` rule achieves
F2 = 0.739 against the best learned arm's 0.168. On ESA-ADB, a trivial out-of-limits rule ties the
project's own monitor (0.202 each).

**What this is and is not.** It is a well-evidenced demonstration that **simple and physics-based
baselines are competitive or superior in three of this project's four prediction domains**. It is
*not* a physics-informed machine-learning contribution: I verified that the OPS-SAT `hybrid` is a
late fusion of a 1-D CNN over the raw signal and a feature MLP
(`cosmos/ai/telemetry/models.py:109`) — **architectural**, not physics-informed. The manuscript
must not use "physics-informed" of it.

**Novelty: low as a method, moderate as evidence.** It instantiates Herrmann et al. (2024). JIRS
fit: moderate; valuable as a sanity-check section, not as the contribution.

## Contribution 4 — Uncertainty-aware orbital lifetime prediction

**What exists.** Mondrian conformalised quantile regression (Romano et al. 2019 per Mondrian
group, Vovk 2013), groups = object class × perigee band with a documented fallback hierarchy;
empirical coverage reported per evaluation slice; capped log-lifetime quantile target with a point
mass; pinball loss justified by elicitability (Gneiting 2011) and mean-elicited scores excluded by
non-use and mechanically guarded.

**What the evidence shows.** Coverage is **unstable**: 0.572–0.960 at the 80 % level across eleven
slices (3 at nominal, 4 under, 4 over); better at 90 % (8 of 11 at nominal, 0.812–0.978).

**Assessment.** The *methodology* is sound and more careful than the field norm, but it is
**standard method correctly applied**, not new method. The *finding* — that conformal coverage
degrades under temporal displacement — is an instance of a published bound (Wang & Hyndman 2024,
preprint), observed at one of two origins, with no trend test.

**Critically: no distribution-free guarantee may be claimed.** Split-conformal guarantees require
exchangeability between calibration and test. Our test folds are **forward in time** from
calibration, so exchangeability fails by construction, and the empirical coverage figures above
confirm it fails in practice. **Any statement of a coverage guarantee would be mathematically
unjustified.** The honest claim is *finite-sample coverage targeted by construction, measured
empirically, and observed to be unstable under temporal shift.*

**Novelty: low-moderate. JIRS fit: moderate** (JIRS's 5 % uncertainty-themed output mostly concerns
control-theoretic uncertainty, not predictive calibration — the terminology gap in
`JIRS_SCOPE_AND_RECENT_PUBLICATIONS.md` §1.1 applies).

## Contribution 5 — Intelligent decision support for satellite operations

**Status: UNSUPPORTED. This cannot be claimed.**

- `cosmos/ai/adapters.py:358` — `priority_score` deliberately unset by the `collision_risk`
  adapter.
- `cosmos/ai/dashboard.py:247` — dashboard states the field "is deliberately empty".
- `cosmos/ai/adapters.py:514` — a `decision_priority` adapter does compute and sort by a priority.
- **No artifact in the repository scores any decision against any outcome.** No decision-quality
  metric, no regret, no utility model, no operator study, no baseline ordering comparison.

The architecture has real merits — typed contracts, genuine abstention, unavailable evidence
declared rather than imputed, explicit "no data" rendering instead of placeholder values. Those are
engineering virtues and they are **[6] already satisfactory** as engineering. They are not
scientific validation of decision quality.

**This is the largest gap relative to JIRS**, because decision support under uncertainty is
precisely what [J2] and [J6] do and what the journal rewards. See experiments plan **E4**.

## Contribution 6 — Reliability assessment under temporal distribution shift

Overlaps Contributions 1–2. The distinct asset here is the **methodological apparatus**:
hash-sealed pre-registration with a refuse-to-run guard, a separate deviations log, mechanically
verified temporal ordering and launch-family disjointness, cluster-aware bootstrap with BH
correction, an audit harness that re-derives every headline number from its artifact (27/28 PASS),
and prediction-level reproducibility verified to exactly **0.000e+00** deviation.

**This apparatus is, in my assessment, the project's most transferable and least appreciated
asset** — and it maps directly onto [J1]'s assurance-case argument: these are the evidence
artifacts an assurance case for a machine-learned space component would need.

**Novelty: moderate (process contributions are harder to publish). JIRS fit: high, via [J1].**

## Contribution 7 — Satellite digital-twin intelligence and monitoring

**Status: NOT DEMONSTRATED, and partly REFUTED by the project's own experiments.**

- C1 **NOT REPRODUCIBLE** — the same-learner de-confounding test gives −0.0514 at origin 2011 and
  +0.0026 at 2016, significant at neither, signs inconsistent.
- C2 statistically supported overall but the **deployed** arm shows no significant gain
  (p = 0.364), the uncalibrated contrast is inconclusive (p = 0.4115), and recalibration has an
  effect of comparable or larger magnitude than the model choice.
- C3 **INCONCLUSIVE**. C4 **NOT EVALUABLE** — 0 joinable pairs.
- The dated 2026-10-27 twin forecast is registered and hash-verified but **unscored** until
  2026-11-26.

[J4] (Harbaoui et al.) demonstrates benefit from fault-tolerant multi-*sensor* fusion. We measured
none from cross-*domain* fusion. These are different propositions and ours must not be presented as
contradicting theirs.

**Any digital-twin contribution claim would be unsupported.** Report as a negative result.

---

## Overall novelty verdict

| # | Contribution | Status | Novelty | JIRS fit | Claimable now? |
|---|---|---|---|---|---|
| 1 | Evidence-aware model selection | **Exploratory** | **High** | **High** | **No — needs confirmatory design** |
| 2 | Temporal reliability of predictive systems | Mixed: underpowered-confirmatory + exploratory | Moderate-high | **High** | Partly, with power disclosed |
| 3 | Physics vs learned comparison | Validated | Low (method) / moderate (evidence) | Moderate | Yes, as supporting evidence |
| 4 | Uncertainty-aware lifetime prediction | Validated; coverage unstable | Low-moderate | Moderate | Yes — **with no guarantee claimed** |
| 5 | Intelligent decision support | **Unsupported** | — | Would be highest | **No** |
| 6 | Reliability-assessment apparatus | Validated | Moderate | **High via [J1]** | Yes |
| 7 | Digital-twin intelligence | **Not demonstrated / refuted** | — | High if true | **No** |

**Plus one contribution you did not list, which is the project's strongest validated positive
result:**

| # | Contribution | Status | Novelty | JIRS fit | Claimable now? |
|---|---|---|---|---|---|
| **8** | **Spacecraft telemetry anomaly detection**: late-fusion `hybrid` attains AUC-PR 0.9719 time-blocked / 0.9855 official, beating a `chronos-bolt` time-series foundation model by +0.0316 AUC-PR (95 % CI [0.0134, 0.0558], p < 0.001), at 74k parameters and 0.0045 ms/fragment, with ECE 0.035 and a label-efficiency sweep — **while the same project's monitor ties a trivial out-of-limits rule on ESA-ADB** | **VALIDATED positive + validated negative** | Moderate | **High** | **Yes** |

## Recommended contribution set for JIRS

**Lead with 1+2 (reframed as a single reliability question), evidenced by 8 as the positive case
and F/lifetime as the negative case, with 3, 4, 6 as supporting material, 7 reported as a negative,
and 5 excluded entirely.**

Working title in that framing:

> **When can validation-based model selection be trusted in spacecraft intelligent systems?
> Evidence from anomaly detection and orbital lifetime prediction.**

That paper is an intelligent-systems reliability paper, not an orbital-prediction benchmark report.
It has a positive and a negative case. It answers a question JIRS's own [J1] raises. And — the
decisive constraint — **it requires contribution 1 to be moved from exploratory to confirmatory
before it can lead.** That is the subject of the experiments plan.

## What must not be claimed

- No validated intelligent decision-support system (5).
- No validated digital twin or cross-domain fusion benefit (7).
- No distribution-free coverage guarantee — exchangeability fails by construction (4).
- No physics-informed machine learning — the `hybrid` is CNN+MLP late fusion (3).
- No confirmation of the temporal-displacement mechanism (1) — it is exploratory and confounded.
- No claim that the pre-registered H2 result is a confirmation — chance level 0.199.
- No real-time or operational-deployment claim; latency was measured, deployment was not.
