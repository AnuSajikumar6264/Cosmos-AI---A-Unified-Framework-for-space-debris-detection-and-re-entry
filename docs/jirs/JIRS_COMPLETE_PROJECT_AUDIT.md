# JIRS complete project and research audit (Phase 1)

Date 2026-11-04 · revision `78ee339` · repository `AnuSajikumar6264/Cosmos-AI-`

**Headline: the project is substantially larger and more validated than the drafted manuscript
represents — and the modules that JIRS would most want are the least validated ones.**

Classification key: **[1]** critical scientific issue · **[2]** major research limitation ·
**[3]** experimental gap · **[4]** reproducibility gap · **[5]** minor improvement ·
**[6]** already satisfactory.

---

## 1. Module-by-module validation status

The governing distinction, applied throughout: *implemented* ≠ *integrated* ≠ *passes tests* ≠
**scientifically validated**. 217 software tests pass; that establishes none of the below.

| Module | Implemented | Externally benchmarked | Validation verdict | Direction | Class |
|---|---|---|---|---|---|
| Telemetry anomaly detection — OPS-SAT | yes | **yes, official benchmark** | **VALIDATED** | **POSITIVE** | **[6]** |
| Telemetry anomaly detection — ESA-ADB | yes | **yes, official metrics** | VALIDATED | **NEGATIVE** | **[2]** |
| Telemetry — SMAP/MSL | yes | yes | partial | mixed | [3] |
| Orbital lifetime prediction | yes | self-constructed benchmark | VALIDATED | **NEGATIVE** | [2] |
| Collision-risk / conjunction (Kelvins CAC) | yes | **yes, official challenge data** | VALIDATED | **STRONGLY NEGATIVE** | **[2]** |
| Debris detection — SpotGEO | yes | **yes, official metric** | VALIDATED | **STRONGLY NEGATIVE** | **[2]** |
| Debris detection — synthetic | yes | **no — self-generated data only** | NOT EXTERNALLY VALIDATED | positive, uninformative | **[2]** |
| Re-entry surrogate / landmark | yes | simulation only | NOT VALIDATED against real re-entries | — | [2] |
| Cross-domain couplings (C1–C4) | yes | yes | **NOT DEMONSTRATED**; C1 NOT REPRODUCIBLE; C4 not evaluable | NEGATIVE | [2] |
| Digital twin / dated forecast | yes | registered, **unscored** | PENDING | — | [3] |
| **Intelligent decision support** | yes | **no** | **NOT VALIDATED — no outcome-scored metric exists** | — | **[1]** |
| Mission Intelligence Console | yes | software tests only | NOT VALIDATED — no user or decision study | — | [2] |
| Orchestration / typed contracts | yes | software tests | **[6]** engineering, not science | — | [6] |

### 1.1 The strongest result in the project is not in the manuscript — **[3]**

**OPS-SAT anomaly detection.** `outputs/benchmarks/telemetry_opssat/`. A late-fusion
`hybrid` model (1-D CNN embedding of the raw signal + feature MLP, 74,371 parameters) is the
best arm under **both** evaluation protocols:

| Model | AUC-PR (time-blocked) | AUC-PR (official) | F1 (time-blocked) | ECE | params | latency ms/fragment |
|---|---|---|---|---|---|---|
| **hybrid** | **0.9719** | 0.9855 | **0.9096** | 0.035 | 74,371 | 0.0045 |
| cnn | 0.9712 | **0.9870** | 0.8672 | 0.121 | 67,713 | 0.0030 |
| fcnn | 0.9666 | 0.9800 | 0.9069 | 0.025 | 13,249 | 0.0019 |
| xgboost | 0.9639 | 0.9607 | 0.8941 | 0.035 | — | — |
| transformer | 0.9418 | 0.9483 | 0.8800 | 0.053 | 71,297 | 0.0049 |
| **chronos-bolt-small** (foundation model) | **0.9191** | 0.9553 | 0.8078 | 0.064 | — | — |
| cosmos_robust_z (classical) | 0.6732 | 0.4712 | 0.3153 | — | — | — |
| iforest | 0.3313 | 0.3462 | 0.1721 | — | — | — |

Paired bootstrap comparisons with CIs and p-values exist: hybrid beats `chronos` by +0.0316
AUC-PR (95 % CI [0.0134, 0.0558], **p < 0.001**), `xgboost` by +0.0254 ([0.0078, 0.0460],
p = 0.002), `fcnn` by +0.0059 ([0.0004, 0.0127], p = 0.036). Five seeds throughout; a label-
efficiency sweep at train fractions 0.10 / 0.25 / 0.50 / 1.00; calibration and compute reported.

**This is a positive, statistically supported, uncertainty-aware, compute-characterised
intelligent-monitoring result that beats a modern time-series foundation model.** It is the most
JIRS-suitable evidence the project owns, and the manuscript does not mention it.

**[3] Gap:** the paired significance tests are computed **only on the official protocol**
(`cosmos/ai/report.py:247` reads `test_scores_official.npz`, keyed `official|1.0|…`). Under the
temporally honest *time-blocked* protocol the hybrid leads on AUC-PR but **no significance test
exists**. Also **[4]**: the score archive `test_scores_official.npz` is **not present on disk**,
so the published paired comparison cannot currently be re-derived without refitting.

### 1.2 A finding that reframes the whole contribution — **[3], exploratory**

I computed a diagnostic that does not exist in the repository: the rank correlation between
**validation** and **test** model ordering, on the same system, across tasks of increasing
temporal displacement.

| Task | Protocol | Spearman(val, test) | n | p |
|---|---|---|---|---|
| OPS-SAT anomaly detection | official (random-ish split) | **+1.000** | 5 | < 0.001 |
| OPS-SAT anomaly detection | **time-blocked** | **+0.800** | 5 | 0.104 |
| Orbital lifetime | **forward origins, multi-year gap** | **0.000** | 7 | not computed |

Selection transfers **perfectly** when selection and test are temporally adjacent, **strongly**
when time-blocked, and **not at all** across multi-year forward origins. That is a monotone
ordering in the severity of temporal displacement, measured within one codebase.

**This is the project's strongest candidate intelligent-systems contribution** (see
`JIRS_NOVELTY_AND_CONTRIBUTION_ASSESSMENT.md`). It is currently **exploratory**: I computed it
post hoc, n is 5 and 7, the +0.800 is not significant, and the three settings differ in data,
metric and model family as well as in temporal displacement — so the ordering is **confounded**
and is a hypothesis, not a demonstrated mechanism.

### 1.3 Collision risk — strongly negative, and honestly so — **[2]**

`outputs/benchmarks/conjunction_kelvins_cac/test_results.csv`, ESA Kelvins CAC, 2,167 held-out
events, 150 high-risk:

| Model | F2 | precision | recall |
|---|---|---|---|
| **`latest_risk_point` (trivial baseline)** | **0.739** | 0.646 | 0.767 |
| kumo / cosmos_gated / stack_constant | 0.168 | 0.840 | 0.140 |
| tabicl | 0.057 | 0.778 | 0.047 |
| xgboost, lightgbm, catboost, mlp, tabm, persistence | **0.000** | 0.000 | 0.000 |

**Every learned arm is dramatically worse than simply reading the latest reported risk value.**
Six of eleven arms score exactly zero F2. Interval coverage is reasonable (cov80 0.83–0.91) and
the ranking by pinball favours `kumo`, but on the operational decision metric the module fails.
This is a real result and must not be omitted.

### 1.4 Debris detection — strongly negative on the real benchmark — **[2]**

| Benchmark | Metric | Result |
|---|---|---|
| **SpotGEO** (official challenge data) | test F1 | **0.084**; official MSE 94.8 per sequence |
| COSMOS synthetic | mAP@50 | 0.780 |

The module performs acceptably **only on data the project generated itself** and essentially
fails on the real unresolved point-target benchmark. **[2]** Reporting the synthetic 0.78 without
the SpotGEO 0.084 beside it would be misleading; the synthetic number is not external evidence.

### 1.5 ESA-ADB anomaly detection — the project's own monitor is no better than a trivial rule — **[2]**

`outputs/benchmarks/telemetry_esa_adb/results.csv`, official ESA-ADB event-wise metrics,
mission 1 lightweight track:

| Encoder | `anomaly_and_rare/EW_F0.5` | ADTQC | false alarms/year |
|---|---|---|---|
| **patchtst** (published architecture) | **0.496** | 0.889 | **0.286** |
| ar8 | 0.407 | 0.856 | 3.57 |
| global_std5 (trivial) | 0.253 | 0.688 | 3.86 |
| **cosmos_monitor** (ours) | **0.202** | 0.769 | **14.7** |
| out_of_limits (trivial rule) | 0.202 | 0.778 | 12.4 |
| global_std3 (trivial) | 0.001 | 0.770 | 4571 |

**`cosmos_monitor` scores identically to a trivial out-of-limits rule (0.202) and is less than
half of PatchTST, with 51× the false-alarm rate.** This directly instantiates the
overestimation-correction genre the project cites. It is a legitimate negative result and it is a
necessary counterweight to §1.1 — **performance is dataset-dependent, and on the harder official
benchmark the project's own design loses to published baselines and ties a trivial rule.**

### 1.6 Intelligent decision support — not validated at all — **[1] CRITICAL for JIRS**

This is the most serious finding for a JIRS submission, because decision support is JIRS's
territory.

- `cosmos/ai/adapters.py:358` — `priority_score` is **deliberately left unset** by the
  `collision_risk` adapter: *"priority is a decision-layer"* concern.
- `cosmos/ai/dashboard.py:247` — the dashboard states `priority_score` *"is deliberately
  empty"*.
- `cosmos/ai/adapters.py:514` — a `decision_priority` adapter does compute a priority and sorts
  by it.
- **No artifact anywhere scores decision priority against any outcome.** There is no
  decision-quality metric, no regret measure, no utility model, no operator study, no comparison
  against an operational ordering baseline.

So the system **produces** prioritised decisions and **nothing establishes that the
prioritisation is good**. The architecture is defensible (abstention is real, uncertainty is
surfaced, unavailable evidence is declared rather than imputed) — but architecture is not
validation. **Any claim of a validated intelligent decision-support system is unsupported.**

### 1.7 Cross-domain integration — not demonstrated — **[2]**

Established in prior phases and re-verified: C1 **NOT REPRODUCIBLE** (E12 same-learner test:
−0.0514 at origin 2011, +0.0026 at 2016, significant at neither, signs inconsistent); C2
statistically supported but the **deployed** arm shows no gain (p = 0.364) and recalibration has a
comparable or larger effect; C3 INCONCLUSIVE; C4 **NOT EVALUABLE** (0 joinable pairs — the
telemetry corpus is anonymised with no spacecraft identifier, the conjunction data anonymised with
no NORAD identifier).

**The digital-twin premise — that fusing these modules yields value beyond running them
independently — is refuted by the project's own experiments**, not merely unproven.

---

## 2. Data, pipeline and statistical audit

| Area | Finding | Class |
|---|---|---|
| Dataset provenance | 15 manifests; 12 record licence and/or source URLs; 3 locally generated (2 synthetic, 1 derived) record generator and class | [6] |
| Derived-dataset terms | `feature3_reentry/processed` names its three GCAT/CelesTrak inputs but states no **inherited** licence terms | [5] |
| Restricted data | SPARK never obtained (access-gated); correctly documented; no result depends on it | [6] |
| Temporal separation | Ordering, tune-A/tune-B launch-family disjointness (0 straddling), test-fold disjointness (0 shared objects) mechanically verified at all three origins | **[6]** |
| Leakage controls | Features computed only from information available at `t0`; verified | [6] |
| Cluster-aware inference | Paired cluster bootstrap over launch families; BH correction within families | **[6]** |
| Bootstrap draws | **4,000** for couplings/G5d, **2,000** for rolling-origin — the manuscript previously stated a single blanket figure | [5] |
| Statistical power | Headline ρ over **n = 7**; H2 chance level **0.199**; slice sizes 198–841; OPS-SAT n = 5 arms | **[2]** |
| Elicitability discipline | Mean-elicited `rmse_log10` excluded by non-use and mechanically guarded | **[6]** |
| Pre-registration integrity | G5d protocol hash-sealed before any fit, verified unchanged; 28-file freeze intact; deviations in a separate file | **[6]** |
| Conformal calibration | Mondrian CQR on `type1 × perigee band` with a documented fallback hierarchy; coverage reported per slice | [6] |
| Coverage stability | 80 % empirical coverage 0.572–0.960 across slices — unstable | [2] |
| Uncertainty propagation | Intervals produced per module; **not propagated across modules** into the decision layer | **[3]** |
| Ablation validity | Every ablation arm records `tuned: false` and inherits its parent's hyperparameters | **[2]** |
| Tuning parity | `tabicl` and `kumo` carry **one** tuned hyperparameter; others 4–6 | **[2]** |
| Vendor dependency | `kumo` = `sdm.models.KumoTabular`, a **commercial vendor library** | **[2]** |
| Training reproducibility | 2 of 7 backends importable; 1 of 7 matches the only recorded environment; no environment recorded for any published run; `provenance.py` never called | **[4]** |
| Prediction reproducibility | Published pinball recomputes from archives to **0.000e+00** | **[6]** |
| OPS-SAT score archive | `test_scores_official.npz` referenced by `report.py` but **absent from disk** | **[4]** |
| Benchmark deposit | **No DOI, archive deposit, repository release or licence** | **[1]** |
| Audit harness | 27/28 checks PASS, 0 critical; re-derives headline values from artifacts | **[6]** |

---

## 3. Findings by class

### [1] Critical scientific issues

1. **Intelligent decision support is entirely unvalidated** (§1.6). For JIRS specifically this is
   fatal to the framing most likely to interest the journal.
2. **No benchmark deposit** — a benchmark paper whose artifact cannot be obtained is
   desk-rejectable.

### [2] Major research limitations

3. Training-level irreproducibility (5 of 7 learners; no recorded environment; one vendor-only).
4. Collision risk is beaten by a trivial baseline by a factor of 4.4 on F2.
5. Debris detection fails on the real benchmark (F1 0.084) and is only validated on self-generated
   data.
6. `cosmos_monitor` ties a trivial out-of-limits rule on ESA-ADB with 51× the false-alarm rate.
7. Cross-domain integration refuted by the project's own de-confounding experiment.
8. Statistical power throughout: ρ over n = 7; H2 chance level 0.199; OPS-SAT n = 5.
9. Ablation arms untuned, and tuning depth unequal across learners — biases every ablation.
10. Coverage unstable across slices (0.572–0.960 at the 80 % level).
11. Re-entry surrogate validated only against simulation, never against observed re-entries.
12. Console and decision layer have no user or decision-quality study.

### [3] Experimental gaps

13. **No significance test under the time-blocked protocol** for the project's best positive
    result (§1.1) — and the score archive needed to compute one is missing.
14. **The selection-transfer-versus-temporal-displacement finding (§1.2) is exploratory** and
    confounded; it needs a controlled design.
15. Phase F prospective scoring blocked until 2026-11-26.
16. Uncertainty is not propagated across modules.
17. No external or trivial baseline on the lifetime benchmark (all reference points are internal).
18. No cross-mission generalisation test for the anomaly detector (OPS-SAT ↔ ESA-ADB ↔ SMAP/MSL).

### [4] Reproducibility gaps

19. No environment recorded for any published run; `provenance.py` exists and is never invoked.
20. Five learner backends undeclared in every requirements file (all five are on PyPI).
21. `test_scores_official.npz` absent, so a published statistical comparison is not re-derivable.
22. No checksums for the origin-2006 prediction archive (the one fold where sealing matters most).

### [5] Minor improvements

23. Derived-dataset manifest lacks an inherited-terms note.
24. Bootstrap draw counts should be stated per analysis.
25. Phase-dated reports carry historical test counts (correct as snapshots).

### [6] Already satisfactory

26. Temporal separation and leakage control — mechanically verified, better than field norm.
27. Cluster-aware inference with multiplicity correction.
28. Pre-registration machinery with hash sealing and refusal-to-run guards.
29. Prediction-level reproducibility — exact.
30. Elicitability discipline, mechanically enforced.
31. Typed contracts, abstention semantics, and explicit "no data" rendering rather than imputation.
32. The audit harness itself, which re-derives claims rather than restating them.
33. Honest negative reporting throughout the research documentation.

---

## 4. The central structural finding

**The project's validated evidence and the drafted manuscript point in different directions.**

The manuscript is a lifetime-benchmark paper whose results are negative. Meanwhile the project
owns a *positive*, significance-tested, calibration- and compute-characterised intelligent-
monitoring result (§1.1) that beats a foundation model, plus a cross-task selection-transfer
contrast (§1.2) that is the most intellectually interesting thing in the repository — and neither
appears in the manuscript.

Simultaneously, the components JIRS would most want to see — decision support, digital-twin
intelligence, cross-module fusion — are respectively **unvalidated**, **pending**, and **refuted**.

This defines the revision problem: not polishing the existing paper, but deciding which of the
project's real results constitutes the JIRS contribution. That is taken up in
`JIRS_NOVELTY_AND_CONTRIBUTION_ASSESSMENT.md` and
`JIRS_Q1_EXPERIMENTAL_GAP_ANALYSIS.md`.

**No frozen artifact, published output or pre-registration was modified during this audit.** The
one new computation (§1.2) is a read-only diagnostic over saved metrics; no model was refitted.
