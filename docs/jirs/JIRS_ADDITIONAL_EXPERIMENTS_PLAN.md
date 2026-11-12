# JIRS additional experiments — minimum sufficient plan (Phase 5)

Date 2026-11-04 · **AWAITING YOUR APPROVAL. Nothing below has been started.**

Design principle: the smallest set that makes the manuscript Q1-competitive for JIRS. I have
deliberately excluded experiments that would increase the count without answering a question —
those are listed in §5 so you can see what was rejected and why.

**Four experiments are essential. Three are recommended. Two are optional. Two are infeasible.**

---

## 1. ESSENTIAL BEFORE SUBMISSION

### E1 — Temporally honest significance test for the anomaly-detection result

| Field | Detail |
|---|---|
| **Research question** | Does the `hybrid` detector's advantage survive a temporally honest evaluation, or only the official random-ish split? |
| **Hypothesis** | H: under the time-blocked protocol, `hybrid` significantly exceeds `chronos-bolt-small`, `xgboost` and `fcnn` on AUC-PR. |
| **Motivation** | This is the project's strongest positive result and the one most suited to JIRS. Its significance test currently uses `test_scores_official.npz` (official protocol only), and that archive is **absent from disk**. Under the time-blocked protocol the hybrid leads (0.9719 vs 0.9712 `cnn`, 0.9191 `chronos`) **with no significance test at all**. A Q1 reviewer will find this. |
| **Dataset** | OPS-SAT anomaly benchmark (`data/feature1_health/opssat_ad`), already held, licence and DOI recorded in its manifest. |
| **Baselines** | The existing eleven arms. No new baselines. |
| **Metrics** | Primary AUC-PR; secondary F1, MCC, false-alarm rate, ECE, Brier. |
| **Statistical method** | Paired bootstrap over evaluation fragments with BH correction across the comparison family, mirroring the existing official-protocol procedure. Report effect size + 95 % CI + adjusted p. |
| **Expected contribution** | Either promotes claim 2 to a temporally valid result, or shows the advantage is protocol-dependent — **which would itself be a finding consistent with the paper's thesis.** Both outcomes are publishable. |
| **Resources** | Refit required (score archive missing). Backends needed are `torch` + `xgboost`, both available. Models are small (≤ 74k params, 0.0045 ms/fragment); 11 arms × 5 seeds. Estimate **2–6 GPU-hours**, < 1 GB storage. |
| **Feasibility** | **High.** Only available backends are involved. |
| **Priority** | **CRITICAL** |
| **Freeze impact** | **None.** Writes to a new output directory. Also fixes reproducibility gap [4] by persisting the score archive. |

### E2 — Controlled test of selection transfer versus temporal displacement

| Field | Detail |
|---|---|
| **Research question** | Does the rank correlation between validation and test model ordering degrade as the temporal gap between selection and test increases, holding task, data and metric fixed? |
| **Hypothesis** | H1 (pre-registered): ρ(validation rank, test rank) decreases monotonically with the selection→test temporal gap. H0: ρ is independent of the gap. |
| **Motivation** | This is the **lead contribution** for JIRS and answers the evidential question [J1] (Hawkins et al., JIRS 2023) raises about assuring machine-learned satellite components. It is currently exploratory, post hoc, and **confounded** — my ρ = +1.000 / +0.800 / 0.000 observation varies dataset, task, metric and model family along with the temporal gap, so it cannot support a mechanism claim. |
| **Design — this is the point** | **Within a single dataset**, construct several selection/test configurations whose *only* systematic difference is the temporal gap. On OPS-SAT: hold the model set, the metric and the feature pipeline fixed, and vary the gap between the selection window and the test window across a ladder of increasing displacement. Compute ρ at each rung. **Pre-register the ladder, the arm set, the statistic and the decision rule before running anything**, hash-sealing the protocol with the existing machinery (`check_preregistration` refuses to run on a changed protocol). |
| **Dataset** | OPS-SAT primarily (sufficient temporal extent, cheap models, all backends available). Optionally replicate on SMAP/MSL for a second task. |
| **Baselines** | The arms with both validation and test scores — the 5 deep arms plus gradient boosting where available. |
| **Metrics** | Primary: Spearman ρ(validation rank, test rank) per rung, **with bootstrap CI and exact permutation p-value** (fixing gap S1). Secondary: **selection regret** per rung (see T1), Kendall τ as a robustness check. |
| **Statistical method** | Bootstrap CI over evaluation units at each rung; exact permutation test for each ρ; pre-registered monotonicity test across rungs (e.g. Spearman of ρ against gap, or a trend test) with a **pre-registered minimum number of rungs** so the H3 power mistake is not repeated. |
| **Expected contribution** | Converts the project's most interesting observation into a **confirmatory** finding: a measured law relating temporal displacement to the trustworthiness of validation-based model selection, in a spacecraft intelligent system. This is the paper's claim to novelty. |
| **Resources** | Same model family as E1; several rungs × 5 seeds. Estimate **6–20 GPU-hours**, < 5 GB. |
| **Feasibility** | **High** on OPS-SAT. The orbital-lifetime arm of the ladder **cannot** be extended (5 of 7 backends unavailable), so lifetime enters as a fixed observation at the extreme of the ladder, not as a varied rung — and that limitation must be stated. |
| **Priority** | **CRITICAL — without this there is no lead JIRS contribution** |
| **Freeze impact** | **None.** New pre-registration, new output directory; no existing origin, artifact or pre-registration is touched. |

### E3 — Correct reference distribution for the ranking-instability criterion

| Field | Detail |
|---|---|
| **Research question** | Is the observed cross-origin ranking instability greater than sampling noise around a stable underlying ordering would produce? |
| **Hypothesis** | H0: the arms have a stable true quality ordering and observed rank changes are sampling noise. |
| **Motivation** | The pre-registered H2 criterion is met by chance with probability **0.1985** under independent uniform rankings (exact enumeration over all 3,456 configurations; §4.3 of the gap analysis). That null answers "could pure chance do this?" but **not** the apt question, which is whether instability exceeds *noise around stability*. Without this, H2 is a weak statistic defended by a weak null. |
| **Dataset** | Archived per-object predictions at all three origins. **No refitting.** |
| **Baselines** | The four common arms, unchanged. |
| **Metrics** | Frequency with which the H2 criterion is met under a cluster bootstrap of each origin's test fold; distribution of `physics_only` rank range; distribution of the number of rank-constant arms. |
| **Statistical method** | Paired cluster bootstrap over launch families within each origin, arms held fixed, ranks recomputed per resample. Report the criterion's bootstrap frequency as the reference distribution. |
| **Expected contribution** | Replaces a contested null with the right one, and either strengthens or correctly weakens the instability claim. **Pre-empts the strongest statistical objection a reviewer can raise.** |
| **Resources** | **Minutes of CPU.** Archives only. |
| **Feasibility** | **Very high** |
| **Priority** | **CRITICAL (cost is near zero; it defuses the main statistical attack)** |
| **Freeze impact** | **None** — read-only on archives. It is a **new analysis reported alongside** the pre-registered verdict, which remains as pre-registered. It does not alter H2's recorded outcome. |

### E4 — Outcome-scored evaluation of the decision layer

| Field | Detail |
|---|---|
| **Research question** | Does the system's evidence-aware prioritisation order objects better than defensible simpler orderings? |
| **Hypothesis** | H: evidence-aware priority achieves lower decision regret than (a) a single-module ordering, (b) a trivial risk-value ordering, (c) a random ordering, at matched review budgets. |
| **Motivation** | **This is the largest gap relative to JIRS.** Decision support under uncertainty is exactly what [J2] and [J6] do. Our decision layer is implemented and **entirely unvalidated** — no decision-quality metric, regret measure, utility model or operator study exists anywhere, and `priority_score` is deliberately unset in the collision adapter. **Without E4 no decision-support contribution may be claimed at all.** |
| **Dataset** | Retrospective: objects with determined outcomes (decays within the five-year horizon; Kelvins CAC high-risk events). Uses existing labelled outcomes — no new data. |
| **Baselines** | Single-module ordering; trivial `latest_risk_point` ordering (which already beats every learned arm at F2 0.739); random ordering; oracle ordering for the regret denominator. |
| **Metrics** | Primary: **precision@k / recall@k at operationally plausible review budgets**, and **decision regret versus the oracle ordering**. Secondary: proportion of abstentions, and outcome rate among abstained items (does abstention correctly identify the cases it should decline?). |
| **Statistical method** | Cluster bootstrap over launch families / events for CIs; paired comparison against each baseline with BH correction. |
| **Expected contribution** | Either establishes the first validated claim about the decision layer, or shows that evidence-aware prioritisation does **not** beat a trivial ordering — which, given §C of the audit, is a real possibility and would still be a publishable negative consistent with the paper's thesis. |
| **Resources** | **No model fitting.** Scoring and analysis over existing predictions and outcomes. Estimate **1–2 days of analysis work**, negligible compute. |
| **Feasibility** | **High.** The main design work is specifying a defensible utility/budget model, which must be fixed **before** scoring. |
| **Priority** | **CRITICAL if a decision-support claim is wanted; otherwise MAJOR** |
| **Freeze impact** | **None** — new analysis over existing artifacts. |

**Note on E4 and honesty:** I recommend pre-registering E4's budget levels and baseline set before
scoring, precisely because the plausible outcome is unfavourable. Deciding the metric after seeing
the ordering would be the error this project has otherwise avoided.

---

## 2. RECOMMENDED FOR STRONGER Q1 COMPETITIVENESS

### E5 — Selection regret, reported throughout (gap T1)

Compute, from existing archives with no refitting, the test-loss penalty incurred by following the
validation-based selection rule rather than choosing the best arm. Already verifiable at origin
2011: selected `kumo` 0.06161 vs best achievable 0.05958 — **regret +0.00203 (3.4 %)**. Report
regret at every origin and every E2 rung. **Cost: hours. Value: converts an abstract rank
correlation into an operational cost an engineer can act on.** Priority **MAJOR**, freeze impact
none.

### E6 — Fusion-branch ablation for the `hybrid` detector (gap A1)

Three arms: CNN branch only, MLP branch only, late fusion. `cnn` and `fcnn` already exist, so this
is largely an attribution analysis plus the retuned single-branch variants. Answers whether the
fusion contributes or one branch carries the result. **The only additional ablation I consider
scientifically justified.** Priority **MAJOR**, cost low, freeze impact none.

### E7 — Robustness under induced missing data

[J3] is a JIRS paper on fault diagnosis under high missing rates; our abstention architecture is
the natural comparator and has never been tested under induced missingness. Inject missingness at
several rates into OPS-SAT inputs; measure detector degradation and abstention behaviour.
**This is the experiment that most directly connects COSMOS-AI to JIRS's existing output.**
Priority **MAJOR**, cost low–moderate, freeze impact none.

---

## 3. OPTIONAL / FUTURE WORK

| ID | Experiment | Why optional |
|---|---|---|
| E8 | Cross-mission generalisation of the anomaly detector (OPS-SAT ↔ SMAP/MSL ↔ ESA-ADB) | Scientifically interesting and JIRS-relevant, but the ESA-ADB result already indicates the answer is unfavourable, and it is not needed for any claim made |
| E9 | Epistemic/aleatoric decomposition from the existing 5-seed ensembles | Cheap, but no current claim depends on the distinction |
| E10 | Hyperparameter-sensitivity sweep to test whether ρ = 0.000 is a tuning artefact | Valuable if a reviewer challenges B1; defer unless asked |
| E11 | Retuning all ablation arms to remove the A1 bias | Scientifically ideal but expensive, and blocked for 5 of 7 lifetime learners; disclosure is the proportionate response |

---

## 4. NOT FEASIBLE WITH CURRENT DATA

| ID | Experiment | Blocker |
|---|---|---|
| N1 | Coupling C4 (telemetry health → conjunction priority) | **Structural.** Telemetry is anonymised with no spacecraft identifier; conjunction data anonymised with no NORAD ID; catalogue has neither. **0 joinable pairs.** No analysis can fix this |
| N2 | Extending the lifetime benchmark to new origins with the full learner set | 5 of 7 backends unavailable, one of them a commercial vendor library; and no environment was recorded for the original fits |
| N3 | ML-dSGP4-class comparison | Requires TLE, B\* and ephemeris data not held |
| N4 | Phase F prospective scoring of the 2026-10-27 forecast | Calendar-bound: needs a catalogue snapshot dated ≥ **2026-11-26** (22 days out). Not an experiment to plan, a date to wait for |
| N5 | Operator study of the console | Requires human participants, ethics approval and operator access |

---

## 5. SCIENTIFICALLY UNNECESSARY — deliberately rejected

Listed so you can see I did not pad the plan.

| Rejected | Reason |
|---|---|
| Additional arbitrary ablations on the lifetime models | Would not answer a research question; existing ablation coverage is already adequate in scope (the defect is tuning, not coverage) |
| More temporal origins for the lifetime benchmark | Blocked by N2, and origin 2006 already supplies the sealed fold |
| Deep-learning architecture search on OPS-SAT | Chasing a metric; the existing arm set already includes a foundation model and the result is already favourable |
| Real-time / embedded deployment benchmarking | Would invite a deployment claim the paper should not make; latency is already characterised |
| Noise-injection and outlier studies on lifetime | No claim depends on them; the capped target already bounds outlier influence |
| Re-running G5d to improve H1/H3 power | Blocked by N2 — and re-running a pre-registered experiment to obtain a better outcome is not legitimate |
| Scaling / complexity analysis | No resource-scaling claim is made |

---

## 6. Summary and recommended sequencing

| Order | ID | What | Cost | Blocks submission? |
|---|---|---|---|---|
| 1 | **E3** | Correct reference distribution for H2 | **minutes** | no, but defuses the main attack |
| 2 | **E5** | Selection regret from archives | **hours** | no |
| 3 | **E1** | Time-blocked significance test | 2–6 GPU-h | **yes** |
| 4 | **E2** | Pre-registered temporal-displacement ladder | 6–20 GPU-h | **yes — this is the lead contribution** |
| 5 | **E4** | Decision-layer evaluation | 1–2 days analysis | **yes, if claiming decision support** |
| 6 | E6, E7 | Fusion ablation; missing-data robustness | low–moderate | no |

**Total essential compute: roughly 8–26 GPU-hours plus a few days of analysis.** All of it uses
backends that are available, none of it touches a frozen artifact or a pre-registered outcome, and
E3 and E5 require no fitting at all.

**Recommended first step if you approve: E3 and E5 together.** They are nearly free, they
strengthen the statistics immediately, and E5's regret numbers will tell us how compelling E2's
ladder is likely to be before committing GPU time to it.

**Awaiting your approval. I have not started any of these.**
