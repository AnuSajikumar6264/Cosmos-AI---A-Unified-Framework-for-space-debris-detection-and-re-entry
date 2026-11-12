# JIRS Q1 readiness report

Date 2026-11-04 · revision `78ee339` · target: Journal of Intelligent and Robotic Systems

---

## DECISION: **C — Not yet suitable for JIRS**, convertible to **B**

**C applies to the manuscript as it stands.** It is not a Q1-competitive JIRS submission, and the
deficiency is not presentational. Submitted unchanged, the predicted outcome is desk rejection on
scope.

**B is reachable.** With the reframing and four experiments, the project has the material for a
credible JIRS paper — because the evidence it needs already exists and is simply not in the
manuscript.

I did not reach this by assuming JIRS is Q1-classified and declaring the work ready. Every
conclusion below is evidenced.

### Why C, precisely

| Deficiency | Evidence |
|---|---|
| **The manuscript contains no intelligent system** | No agent, controller, autonomy or decision component is evaluated. "Intelligent system", "decision support" and "operator" appear nowhere as load-bearing concepts. **Zero of 38 references are from JIRS** |
| **Scope mismatch is structural, not cosmetic** | JIRS's official Scopus categories (ID 24360) are Mechanical, Industrial/Manufacturing, Control and Systems Engineering, Software, AI, Electrical/Electronic. **There is no space, aerospace, astrodynamics or planetary category.** Of the complete set of **282 JIRS records since 2023**, **56.4 % are explicitly robotics and 2.1 % are space-related** |
| **The one in-scope component is unvalidated** | The decision layer has **no outcome-scored evaluation of any kind** — no decision-quality metric, regret measure, utility model, operator study or baseline-ordering comparison. `priority_score` is deliberately unset in the collision adapter |
| **The artifact does not exist** | No DOI, deposit, release or licence. A benchmark paper whose benchmark cannot be obtained is desk-rejectable |
| **The project's strongest positive result is absent from the paper** | The OPS-SAT anomaly detector that beats a time-series foundation model is not mentioned |

### Why B is reachable

The project owns, already measured and verified:

- A **positive, significance-tested intelligent-monitoring result**: a 74k-parameter late-fusion
  detector at AUC-PR **0.9719** time-blocked / 0.9855 official, beating `chronos-bolt-small` by
  **+0.0316** (95 % CI [0.0134, 0.0558], **p < 0.001**), with ECE 0.035, 0.0045 ms/fragment latency
  and a label-efficiency sweep across five seeds.
- A **cross-task selection-reliability measurement** — ρ(validation, test) = **+1.000** on adjacent
  splits, **+0.800** time-blocked, **0.000** across multi-year forward origins — which answers the
  evidential question JIRS's own [J1] (Hawkins et al. 2023) raises about assuring machine-learned
  satellite components.
- **Honest negatives with direct JIRS comparators**: learned collision risk loses to a trivial
  baseline (F2 0.168 vs **0.739**) against [J5]; cross-domain fusion not demonstrated against [J4].
- **Methodological apparatus above the field norm**: hash-sealed pre-registration, verified
  temporal separation, cluster-aware inference with BH correction, exact prediction-level
  reproducibility (0.000e+00), and an audit harness that re-derives claims (27/28 PASS).

---

## Current readiness assessment

| Dimension | Status |
|---|---|
| Scientific rigour | **Strong** — three simulated reviewers independently found **no unsupported claim** |
| Statistical reliability | **Adequate but thin where it matters** — headline ρ over n = 7; H2 criterion met by chance with probability **0.1985** (exact enumeration, 686/3456); no leaderboard intervals |
| Experimental depth | **Insufficient for Q1** — two decisive gaps (E1, E2) |
| Reproducibility | **Split**: prediction-level exact; training-level absent for lifetime, **present for telemetry** |
| Data availability | **BLOCKED** — no DOI |
| Manuscript quality | **Good as a space paper, poor as a JIRS paper** |
| Scope fit | **Poor** — 2.1 % of JIRS output |
| Q1 eligibility of the venue | **UNVERIFIED** — Scopus CiteScore and rank are subscription-gated |
| Ethics and transparency | **Strong on statistics; 6 administrative items require you**, including the AI disclosure |

## Strongest scientific contribution

**Not the one in the manuscript.** It is the measurement that validation-based model selection
transfers almost perfectly when selection and test are temporally adjacent and not at all across
multi-year forward origins — measured within one system, across two tasks, with a monotone ordering
in temporal displacement.

That is a reliability property of machine-learned engineering components, it is what [J1]'s
assurance argument needs and lacks, and no JIRS paper in 282 records measures it.

**It is currently EXPLORATORY**: n = 5 and 7, the +0.800 is not significant (p = 0.104), the three
regimes differ in data, task, metric and model family as well as temporal gap, and I computed it
post hoc during this audit. **Experiment E2 is what converts it into a contribution.** Without E2
there is no lead claim appropriate to JIRS.

Runner-up, and already validated: the anomaly-detection result above, which supplies the positive
case.

## Biggest rejection risk

> **The manuscript contains no intelligent system, and cites no paper from the journal.**

Two of three simulated reviewers reject on scope alone, and the editor sees scope before the
reviews exist. This cannot be fixed by revising the present manuscript — only by building the
different paper the evidence supports.

Second-largest: **the artifact does not exist.** Third: the headline statistic rests on n = 7.

## Essential remaining experiments

| ID | What | Cost | Why essential |
|---|---|---|---|
| **E3** | Cluster-bootstrap reference distribution for the instability criterion | **minutes, no fitting** | Replaces a straw-man null; defuses the main statistical attack |
| **E5** | Selection regret from archives | **hours, no fitting** | Converts an abstract correlation into an operational cost |
| **E1** | Time-blocked significance test for the detector; persist the score archive | 2–6 GPU-h | The best positive result is currently tested only on the temporally dishonest protocol |
| **E2** | **Pre-registered temporal-displacement ladder** | 6–20 GPU-h | **Creates the lead contribution.** Without it there is no JIRS paper |
| **E4** | Decision-layer evaluation, pre-registered before scoring | 1–2 days | Required *only* if a decision-support claim is wanted; otherwise that claim must be dropped |

Recommended but not blocking: E6 (fusion ablation), E7 (missing-data robustness — connects directly
to JIRS [J3]).

**Total essential: ~8–26 GPU-hours plus 2–3 days of analysis.** None touches a frozen artifact.

## Reproducibility status

| Level | Status |
|---|---|
| Prediction-level, lifetime benchmark | **COMPLETE — verified to 0.000e+00 deviation** |
| Training-level, **telemetry** | **PRESENT** — needs only `torch` + `xgboost`, both installed |
| Training-level, lifetime benchmark | **ABSENT** — 5 of 7 backends undeclared; **1 of 7** matches the only recorded environment; no environment recorded for any published run; `provenance.py` exists and is **never called**; `kumo` requires a commercial vendor library |
| OPS-SAT prediction archive | **MISSING** — `test_scores_official.npz` referenced but absent; E1 will restore it |
| Integrity | **ALL INTACT** — 28-file freeze, G5d hash, dated-forecast digest, 10/10 artifacts, 217/217 tests |

**The reproducibility gap had a scientific cost, not merely an administrative one**: it cut the
pre-registered experiment from seven learners to two, which is why H1 is NOT_EVALUABLE, H3 is
UNDERPOWERED and the outcome is INCONCLUSIVE. That belongs in the paper as a finding.

## Data and DOI status

| Item | Status |
|---|---|
| **DOI** | **NONE. No DOI exists and none has been invented** |
| Archival deposit | **NONE** |
| GitHub repository | Exists (`AnuSajikumar6264/Cosmos-AI-`); **visibility unconfirmed** |
| Code licence | **NONE FOUND** |
| Data licence | **NONE STATED** for derived products |
| Upstream provenance | 15 manifests; 12 with licence/URL; redistribution rights **must be re-verified at release** |
| Licence conflict | **`ultralytics==8.4.185` is AGPL-3.0** — boundary question against a permissive repository licence |
| Vendor constraint | **`kumo` checkpoint must not be released** without written vendor permission |
| Restricted data | None included; SPARK was never obtained — correctly documented |

## Estimated remaining work

| Phase | Effort |
|---|---|
| Statistical hardening (E3, E5, intervals, permutation tests) | 1 day |
| Essential experiments (E1, E2) | 1 week |
| E4, if decision support is claimed | +2 days |
| Release, licences, DOI | 1–2 days + your decisions |
| Manuscript rewrite (~60 % of text) | 1–2 weeks |
| Verification and independent re-review | 3 days |
| **Total** | **≈ 3–4 weeks of focused work** |

## Exact next action

**Tell me whether you approve:**

1. **D1 — the reframing** to model-selection reliability in spacecraft intelligent systems, led by
   the anomaly-detection and selection-transfer evidence, with lifetime prediction demoted to the
   negative case.
2. **D2 — experiments E1, E2, E3, E5.**
3. **D3 — whether to claim decision support** (and therefore run E4), or to drop that claim.

**If you approve D2, I will start with E3 and E5**: no model fitting, no frozen artifact touched,
results within hours, and E5's regret magnitudes will tell us how strong E2's ladder is likely to be
before any GPU time is spent.

---

## Three things I want to be direct about

**1. I have not concluded that the project is weak.** The scientific discipline here is better than
most of what gets published in this area — verified temporal separation, sealed pre-registration,
cluster-aware inference, exact prediction-level reproducibility, and a record of self-corrections
that weaken the authors' own claims. Three simulated reviewers independently failed to find an
unsupported claim. That is unusual.

**2. The problem is a mismatch between a good project and a chosen venue.** You fixed JIRS, which
is your call, and I have assessed against JIRS's real standards rather than re-arguing the venue.
The honest finding is that JIRS has no space category and publishes ~2 % space work — but also that
**the project contains a genuine intelligent-systems paper it has not yet written.** That is a
better outcome than I expected when I started this audit.

**3. The most valuable thing I found was not in the manuscript.** The ρ = +1.000 → +0.800 → 0.000
ordering came from a diagnostic nobody had computed. It is exploratory and confounded today. If E2
confirms it, it is a real contribution to how machine-learned components should be assured in
engineering systems — which is a better paper than either the lifetime benchmark or the
anomaly-detection result alone.

**No commit, push, release or submission has been made. The manuscript is unchanged. No experiment
has been started.**
