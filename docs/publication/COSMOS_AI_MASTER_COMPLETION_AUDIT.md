# COSMOS-AI master completion audit and critical path

Date 2026-11-05 · **deadline 2026-11-06 — tomorrow**

**The single most important finding: the integrated-digital-twin paper you have asked for cannot be
made experimentally defensible by tomorrow, and not because of missing software. Your own
experiments refute its central premise, and one of its four couplings is structurally impossible
with the available data. I have therefore prioritised the manuscript that is defensible today.**

---

## 1. Critical-path decision

| Objective | Achievable by 2026-11-06? | Why |
|---|---|---|
| **A submission-ready JINT manuscript** | **YES — drafted** | `paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md`, built entirely from verified archived evidence, all six pre-registered contrasts independently reproduced |
| **An integrated-architecture paper with Arms A–E** | **NO** | See §2. The premise is refuted, not unimplemented |
| **Full subsystem completion (§5 of your brief)** | **NO** | Weeks of work; and completion would not change §2 |
| **Mission Intelligence Console completion** | **NO** | Not on the manuscript critical path |

**Recommendation: submit the alarm-selection paper. Continue the engineering objective after the
deadline.** Your brief anticipated exactly this: *"If the complete integrated-system paper is not
yet experimentally defensible, do not pretend it is ready."*

## 2. Why the integrated-architecture paper is not available — evidence, not opinion

Your brief asks me to "demonstrate COSMOS-AI's advantages" over independent architectures via Arms
A–E. The project has already run that experiment. The results:

| Coupling | Hypothesis | Result | Source |
|---|---|---|---|
| **C1** family evidence → lifetime | family features improve lifetime prediction | **NOT REPRODUCIBLE.** Same-learner test: −0.0514 at origin 2011, +0.0026 at 2016, **significant at neither**, signs inconsistent | `outputs/e12_same_learner/e12_results.json` |
| **C2** survival → debris-cloud counts | learned survival improves cloud forecasts | Statistically supported overall, but **the deployed arm shows no significant gain (p = 0.364)**, the uncalibrated contrast is inconclusive (p = 0.4115), and recalibration has an effect of comparable or larger magnitude than the model choice | `outputs/phase_e/phase_e_results.json` |
| **C3** status → re-entry regime | status-aware beats status-blind | **INCONCLUSIVE** | same |
| **C4** health → conjunction | telemetry health improves conjunction priority | **NOT EVALUABLE — 0 joinable pairs** | same |

**C4 is the decisive blocker, and it is structural.** The ESA-ADB telemetry corpus is anonymised
with no spacecraft identifier; the Kelvins CAC conjunction data are anonymised by construction with
no NORAD identifier; the GCAT/CelesTrak catalogue contains neither telemetry nor conjunction
messages. **There are zero objects observable in both corpora.** No amount of engineering creates a
joinable identity that the source data do not contain. Writing a fusion layer would produce code
that cannot be evaluated.

Your brief is explicit that this must not be papered over: *"Do not claim multimodal integration
improves performance without an appropriate experiment"* and *"Do not create artificial links
between incompatible data sources."* Arms D and E require exactly such a link.

**Two prior manuscript tracks in this repository — `paper/journal_v3_twin/` and
`paper/journal_eaai/` — were already marked SUPERSEDED for asserting the digital-twin and
integrated-framework claims.** That decision was correct and I am not reversing it.

## 3. Feature status

Classification per your scheme.

| Feature | Status | Evidence |
|---|---|---|
| Telemetry anomaly detection — ESA-ADB | **SCIENTIFICALLY_VALIDATED** | Pre-registered, hash-frozen `09a98f5e160e`, official metric byte-identical to upstream `67194d3`, GlobalSTD reproduced to 0.001 in 8 configurations, Holm correction, block bootstrap |
| Telemetry anomaly detection — OPS-SAT | **IMPLEMENTED_NOT_VALIDATED** | 11 arms, 5 seeds, two protocols — but significance tests only on the temporally interleaved split, and `test_scores_official.npz` is **absent from disk** |
| Telemetry — SMAP/MSL | **SCIENTIFICALLY_VALIDATED** | 77-metric summary incl. `median_delay_steps`, three robustness protocols with p-values |
| Orbital lifetime prediction | **SCIENTIFICALLY_VALIDATED (negative)** | Three origins, verified split disjointness, exact prediction-level reproduction, selection regret significant at origin 2016 |
| Orbital decay / re-entry landmark | **SCIENTIFICALLY_VALIDATED** | τ = 2026-08-16, 5-check leakage report all passing, physics c-index 0.976 — but **38 test events** |
| Re-entry footprint surrogate | **IMPLEMENTED_NOT_VALIDATED** | n = 40,000; validated against the **simulator**, never a recorded re-entry; `error_vs_std` ρ = 0.303 |
| Debris detection — SpotGEO | **SCIENTIFICALLY_VALIDATED (negative)** | Official metric, test F1 **0.084** |
| Debris detection — synthetic | **IMPLEMENTED_NOT_VALIDATED** | mAP@50 0.780 on **self-generated data only** |
| Collision / conjunction risk | **SCIENTIFICALLY_VALIDATED (negative)** | Kelvins CAC: trivial `latest_risk_point` F2 **0.739** vs best learned arm **0.168**; six arms at exactly 0.000 |
| Multimodal evidence fusion | **BLOCKED** | §2 |
| Health monitoring (`cosmos/health`) | **PARTIALLY_IMPLEMENTED** | `cosmos_monitor` ties a trivial out-of-limits rule on M1 lightweight (0.2021 vs 0.2019) and collapses at full scale (0.0038) |
| Uncertainty quantification | **IMPLEMENTED_NOT_VALIDATED** | Mondrian CQR implemented; coverage **significantly deviates in 3 of 4 Phase H cells**; no guarantee claimable (exchangeability fails by construction) |
| Evidence contracts / orchestration | **IMPLEMENTED** | Typed contracts, dependency injection, genuine abstention; 217 tests pass |
| Mission Intelligence Console | **IMPLEMENTED_NOT_VALIDATED** | Reads real artifacts, labels coherence, renders explicit "no data". **No outcome-scored evaluation** |
| Decision support / prioritisation | **IMPLEMENTED_NOT_VALIDATED** | `priority_score` deliberately unset in the collision adapter. **No decision-quality metric, regret measure or operator study exists** |
| Integrated digital twin | **BLOCKED** | §2 |

## 4. Traceability matrix — the paper's claims

| Requirement | Source code | Dataset | Experiment | Result artifact | Tests | Status |
|---|---|---|---|---|---|---|
| H6 selection effect | `oof_benchmark.py` (frozen) | ESA-ADB v1.0 `10.5281/zenodo.12528696` | pre-registered, freeze `09a98f5e160e` | `oof_protocol/CONFIRMATORY.json` | freeze check | **VALIDATED** |
| H4/H5 refutations | `event_model.py`, `event_gbt.py` | same | same | same | freeze check | **VALIDATED** |
| Anomaly-only robustness | vendored official metric | same | pre-specified secondary | `oof_protocol/test/*.json` | — | **VALIDATED (descriptive)** |
| Alarm-layer dominance | `alarms.py`, `oof_benchmark.py` | same | archived configurations | `oof_protocol/test/*.json` | — | **VALIDATED (descriptive)** |
| ACI operator burden | same | same | same | same | — | **VALIDATED (descriptive)** |
| Mission 2 saturation | vendored metric | same | same | `results.csv` + protocol JSONs | — | **VALIDATED (descriptive)** |
| Cross-fitting optimism | `oof_benchmark.select` | same | same | `oof_protocol/test/*.json` | — | **VALIDATED (descriptive)** |
| GlobalSTD reproduction | `baselines.py` | same | vs DMLR Table 4 | `results.csv` | — | **VALIDATED** |
| Integration advantage | `adapters.py`, `orchestration.py` | multiple | Phase E / E12 | `phase_e_results.json`, `e12_results.json` | `test_couplings_regression.py` | **NOT SUPPORTED** |

## 5. Defects: status

| Defect | Status |
|---|---|
| **L17 — cross-horizon CDF incoherence** | **Diagnosed, quantified, contained at adapter and console; NOT fixed.** 123 of 13,238 objects; cause is three independent isotonic regressors with no cross-horizon constraint; max violation 0.179661. **Now also confirmed consumer-facing: 123 records in the released `twins.jsonl` carry `abstain = false`, empty `reason` and a `validation` field reading "validated-real".** Mitigation added today: `KNOWN_ISSUES.md` (§6) |
| OPS-SAT score archive missing | **Open** — `test_scores_official.npz` referenced by the reporting code and absent; a published significance test is not re-derivable |
| `am_design` missingness unablated | **Open, but Stage-1 evidence now exists** — archived `subgroups_test.csv` shows design-derived objects at **cov80 0.5625** (origin 2016) against 0.80 nominal, with half-width intervals, while the calibration split holds only 5.9 % of them |
| Training-level irreproducibility | **Open, unfixable retroactively** — 5 of 7 backends undeclared; 1 of 7 matches the recorded environment; one is a commercial vendor library |
| No public artifact / DOI | **Open — requires your accounts and licence decisions** |

## 6. Changes made today

| File | Change | Safety |
|---|---|---|
| `paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md` | **NEW** — 23-section JINT manuscript | Additive |
| `paper/jint/COSMOS_AI_JINT_SUBMISSION_CHECKLIST.md` | **NEW** | Additive |
| `docs/publication/COSMOS_AI_MASTER_COMPLETION_AUDIT.md` | **NEW** — this file | Additive |
| `outputs/twin/as_of_2026-10-27/KNOWN_ISSUES.md` | **NEW** — discloses the 123 L17 records to any consumer of the released artifact | **Additive only.** No existing byte altered; `FORECAST_SHA256.txt` still verifies |

**No frozen artifact, pre-registration, historical output, published result or existing manuscript
was modified. No commit, push or upload.**

## 7. What remains, in priority order

**Before tomorrow (yours):** the ten blocking items in the submission checklist §1 — authors,
affiliations, contributions, funding, competing interests, **AI-use disclosure**, **prior-publication
disclosure given the existing thesis**, data DOI, code licence, and confirmation that JINT accepts
this article type.

**This week:** three manuscript figures; factorial decomposition Stage 1 (minutes of CPU);
per-arm leaderboard intervals for the lifetime paper (no fitting).

**Post-deadline engineering:** OPS-SAT score archive and time-blocked significance (E1); fusion
branch ablation (E6); `am_design` Stage 2; L17 forward-only fix via a single monotone quantile
function; wire `run_metadata()` into run entry points; declare the five missing backends with
forward-pin comments; mint a Zenodo deposit.

**Permanently blocked:** C4 health→conjunction integration (zero joinable pairs); Brancato
reconciliation (paywalled); cross-satellite generalisation (one spacecraft per benchmark);
Mission 2 as a generalisation test (six anomalies).

## 8. Honest summary

The engineering objective in your brief — one coherent integrated digital twin with demonstrated
advantages over independent architectures — **is not achievable by tomorrow, and the obstacle is
evidential rather than technical.** Four couplings were tested; one is not reproducible, one shows
no gain in its deployed configuration, one is inconclusive, and one cannot be evaluated at all
because the source corpora share no object identities.

What the project does own is a **genuinely strong, pre-registered empirical result** about where
leverage sits in an intelligent monitoring system: in the alarm layer and its selection data, not
in the scorer. That result is hash-frozen, independently reproduced, metric-robust, and
accompanied by an operator-burden measurement (176,337 vs 1.1 false alarms per year) that is
directly relevant to an intelligent-systems audience.

**That is the paper. It is drafted and it is defensible. It is also narrower than the project you
set out to build, and I would rather tell you that today than have a reviewer tell you in March.**
