# Stage 1 — remaining inspections

Date 2026-11-05 · completes the pending list in `COSMOS_AI_COMPLETE_PROJECT_AUDIT.md` §8
**The original audit is preserved unchanged; corrections are recorded here and cross-referenced.**

---

## 1. Inspection ledger — pending items now closed

| # | Pending item | Status | Outcome |
|---|---|---|---|
| 1 | `thesis/audit/STAGE1_AUDIT.md` §3–§12 | **DONE** | §5 code audit, §6 ranked risks, §7 missing evidence read in full. Findings in `ESA_ADB_H6_REPLICATION_AND_GENERALISATION_AUDIT.md` |
| 2 | `thesis/audit/CLAIM_EVIDENCE_MATRIX.md` | **DONE** | Claim-strength scale (confirmatory / measured / partially supported / exploratory / proposed / unsupported); claims T1, T2 read |
| 3 | `research_design/NOVELTY_NOTE.md` | **DONE** | **Decisive** — located Brancato et al. (2026), TC-CAD and Heydari et al. See §3 |
| 4 | ESA-ADB pre-registration artifacts | **DONE** | `PREREG_TELEMETRY_V1.md` (11,420 B), `freeze.json`, `freeze_09a98f5e160e.json`, `DEVIATIONS.md`, `POSTHOC_PLAN_V2.md`, `posthoc_v2_freeze.json` — all present |
| 5 | `thesis/evidence/original_pipeline_runs.json` | **DONE** | `cosmos_version 1.1.0`, generated 2026-10-25; original-pipeline results regenerated with current code (stage tables, timings, scenario table) |
| 6 | `docs/architecture/` (6 files, 643 lines) | **DONE** | Contains an existing, conservative component-status classification. See §2 |
| 7 | `outputs/pipeline/` | **DONE** | **57 run manifests**, each with `git`, `environment`, `config_sha256`, modules, tables written. See §4 |
| 8 | `cosmos/{health,debris,reentry}` source | **DONE (inventory)** | health 5 files/1,132 LOC; debris 7/1,567; reentry 9/1,715. Entry points listed |
| 9 | Benchmarks `telemetry_smap_msl`, `reentry_landmark`, `reentry_surrogate`, `telemetry_cosmos_synthetic` | **DONE** | See §5 |
| 10 | `research_design/VENUES.md` | **DONE** | 11-journal prior analysis; EAAI first; **JIRS absent**. In `EAAI_VS_JIRS_VENUE_COMPARISON.md` |
| 11 | `notebooks/` (2 files, 3.1 MB) | **NOT DONE** | Deliberately deferred — see §7 |
| 12 | `thesis/src/` 13 chapters | **PARTIAL** | Not read line by line; the audit, claim matrix and Q1 appendix cover their claims |
| 13 | `paper/journal_v3_twin/build/numbers.json` | **NOT DONE** | Low priority; superseded track |

## 2. The project already has a component-status classification — and it is conservative

`docs/architecture/current_architecture.md` §32–60 classifies every component with deliberately
cautious labels, defining `QUANTITATIVELY_EVALUATED` as *"a reported measurement exists, not that
the result has independent scientific confirmation"*, and reserving `INDEPENDENTLY_VALIDATED` for
*"an independent dataset or authoritative ground-truth validation beyond the development
evaluation"*.

Its own conclusions:

> "No evidence found supports the labels `INDEPENDENTLY_VALIDATED` for a complete cross-domain
> system."

> "The data do not support claiming an empirically validated causal chain from satellite health
> through fragmentation to an observed re-entry footprint."

> "The guarantees are conditional on assumptions such as exchangeability; telemetry dependence,
> drift, and the re-entry temporal shift limit literal coverage guarantees. Physics Monte Carlo
> intervals in the twin are explicitly not labelled conformal."

**This substantially pre-empts Part 1's classification request, and it agrees with my independent
findings.** Two specifics worth carrying forward:

- **C4 abstains with a recorded reason, and an integration test asserts the abstention** — so an
  unlinkable coupling cannot silently produce an escalation. That is a genuine design strength.
- **Defect L17, documented 2026-11-04:** the saved per-horizon *calibrated* columns
  `p_lifetime_{30d,90d,1yr}` are **not a coherent CDF for 123 of 13,238 objects**, because
  `engine.py` calibrates each horizon with an independent isotonic regressor. The finally reported
  `p_*` columns are unaffected.

## 3. Correction — the dominant novelty risk, found in `NOVELTY_NOTE.md`

This file was on the pending list and it changes the Track 1 assessment more than anything else in
Stage 1.

| Prior work | Record | Reported |
|---|---|---|
| **Brancato, Lucchetti, Kimura, Omata, Giglio** | *Aerospace Science and Technology*, 2026-10-02, `10.1016/j.ast.2026.113957` (paywalled; abstract read by the project) | **M1 full channels: SMED 0.902, Q-GPR 0.883, out-of-limit reference 0.754**; M1 lightweight: Q-GPR 0.888, SMED 0.811 |
| **Şahin, "TC-CAD"** | Zenodo `10.5281/zenodo.23322711` (2026-10-13), under review; artefacts and pre-registrations read by the project | Telecommand conditioning **pre-registered negative**; ACI best point-level calibration but anomaly event-wise F0.5 collapses 0.090 → ~1e-5; deferral removes **29–33 pp** of automatic rare-nominal alarms at fixed budget |
| **Heydari, Mostafavi, Nyarko** | IEEE Access 2026, `10.1109/ACCESS.2026.3714708` (abstract read) | Cross-mission threshold-policy transfer under alert-workload budgets |

**Consequences recorded by the project itself:**

1. *"Abstention/deferral and operator budgets are pre-empted. TC-CAD has conformal layers, a
   deferral layer and operator budgets. Heydari has workload budgets. **Do not build the paper on
   this.**"*
2. The one distinction the project judges survives: **event-level versus point-level calibration**
   (TC-CAD calibrates point-level; the project's result is that event aggregation succeeds where
   point-level adaptive calibration fails, for a mechanical reason).
3. *"**Brancato et al.'s 0.902 remains unexplained.**"*

**The Brancato discrepancy is the single largest rejection risk in the project.** Their
*parameter-free out-of-limit reference* scores **0.754** on M1 full channels where COSMOS-AI's
scores **0.0007** — roughly three orders of magnitude on the same mission, channel scale and
nominally the same official metric. That cannot be a method effect. TC-CAD's 0.090 sits in
COSMOS-AI's range, which makes a protocol/metric variant the likeliest explanation — but it is
unresolved and blocked by a paywall.

## 4. Correction — reproducibility provenance is better than I reported

My earlier claim that *"`provenance.py` exists and is never called"* was **wrong**. The precise
position:

| Facility | Status |
|---|---|
| `cosmos/ai/provenance.py` `git_revision`, `sha256_file`, `ROOT` | **Used in production** — imported by `cosmos/ai/adapters.py:43` and used to build a provenance record for every adapter output |
| `run_metadata()` and `tracked_run()` | **Implemented and unit-tested** (`tests/test_experiment.py`) but **called nowhere outside tests.** This part of my claim stands |
| **Orchestrated pipeline runs** | **57 manifests**, each recording `git` (commit + dirty flag), `environment` (python 3.12.16, platform, host, `cpu_count` 512, numpy 2.3.5, pandas 3.1.0, torch 2.14.0+xpu, device), `config_sha256`, modules and tables written |
| Analysis / re-analysis result JSONs (`phase_e`, `e3_e5`, …) | `git` **yes**, `environment` **no** |
| **Published lifetime benchmark `summary.json`** | **`git` no, `environment` no** — my original finding, confirmed |

**Corrected statement:** environment capture exists and works for the orchestrated pipeline; it was
never applied to the published lifetime-benchmark training runs. That is narrower and more accurate
than "no environment was recorded for any published run".

## 5. The four previously uninspected benchmark sets

| Benchmark | Key measured content | Assessment |
|---|---|---|
| **`telemetry_smap_msl`** | `summary.csv`, **77 columns**: event precision/recall/F1, ESA event-wise precision/F0.5/F1, **`median_delay_steps`** (detection delay), `nominal_alarm_fraction`, three robustness protocols (**`shift`, `block`, `swap`**) each with p-values, `point_adjusted_f1` vs `event_f1`, saturation diagnostics (`channels_saturated`, `channels_alpha_raised`, `channels_near_zero_spread`), plus "attainable" and "unsaturated" channel subsets. Two superseded directories retained with reasons | **Implemented and experimentally validated.** The most thoroughly instrumented telemetry evaluation in the project — and it includes **detection delay** and the point-adjustment critique |
| **`reentry_landmark`** | τ = 2026-08-16, follow-up 2026-10-23; splits 18,914 / 8,873 / 6,371; events 140 / 57 / 38; **explicit `leakage_report` with five checks all passing** (no GP epoch after τ; no event at or before τ; launch groups in one split; no decay field in features; censoring time constant); physics c-index 0.976; h30/h68 AUC-PR, AUC-ROC, Brier, ECE | **Implemented and experimentally validated**, with real leakage controls. Limited by **38 test events** |
| **`reentry_surrogate`** | Test n = 40,000; impact classification accuracy 0.995; median position error **16.17 km**, p95 69.35 km; fall-time MAE 41.3 s; `ensemble_std` median 34.6 km; **`error_vs_std` Spearman 0.303**; 80,107 samples/s. Separate `ood_test` n = 20,000 (accuracy 0.963). `pipeline_fallback_modes.csv` compares reference vs three fallback modes | **Implemented but insufficiently validated.** Validated against the **simulator**, never against a recorded re-entry. **The uncertainty estimate is only weakly informative (ρ = 0.303)** — a stated-uncertainty claim would be weak |
| **`telemetry_cosmos_synthetic`** | `development/` and `heldout/` subdirectories | **Scientifically unsupported as external evidence** — self-generated data. A held-out split exists, which is good hygiene, but it cannot support real-telemetry claims |

## 6. Corrections register (cumulative)

| # | Claim | Source | Status |
|---|---|---|---|
| 1 | "Architecture diagram MISSING" | my JIRS audit | **WRONG** — 6 graphviz diagrams exist in `thesis/figures/` |
| 2 | ESA-ADB: "cosmos_monitor ties a trivial rule; PatchTST 2.5× better" | my JIRS audit | **INCOMPLETE** — one mission, one scale of four cells |
| 3 | "2023–2026 AD literature outstanding (rate-limited)" | my D3.1 assessment | **PARTLY WRONG** — 64 verified references in-repo incl. Liu 2024, Sehili 2023, Malhotra 2016, García 2022 |
| 4 | "Detection delay not appropriate / not measured" | my D3.1 assessment | **PARTLY WRONG** — `median_delay_steps` is measured on SMAP/MSL |
| 5 | "OPS-SAT is the strongest validated positive" | my JIRS audit | **SUPERSEDED** — the pre-registered ESA-ADB study is more rigorous |
| 6 | "C-1 intersection unoccupied" | my Phase I/O review | **RESOLVED in COSMOS-AI's favour** — Shorten et al. is manoeuvre detection; "decay" appears 0 times in 29 pages |
| 7 | "RCS missingness may explain the selection failure" | my own hypothesis | **REFUTED by the project's own ablation** — effect on point accuracy not detectable; effect is on calibration |
| 8 | "`provenance.py` is never called" | my reproducibility audit | **WRONG** — used in `adapters.py`; only `run_metadata`/`tracked_run` are test-only |
| 9 | "No environment recorded for any published run" | my reproducibility audit | **TOO BROAD** — 57 pipeline manifests record environment; the lifetime benchmark `summary.json` does not |
| 10 | "No benchmark deposit / DOI" | my audit | **STANDS** |
| 11 | "Decision layer has no outcome-scored evaluation" | my audit | **STANDS** — and `current_architecture.md` agrees ("operational prioritization is distinct and not independently established") |

## 7. Still not inspected, with reasons

| Item | Why deferred |
|---|---|
| `notebooks/COSMOS_AI_Experiments.ipynb`, `COSMOS_Demo.ipynb` (3.1 MB) | Large; built by `scripts/build_ai_notebook.py` from artifacts already inspected, so unlikely to hold unique evidence. **Flagged, not dismissed** — if a claim is traced only to a notebook, this becomes blocking |
| `thesis/src/` 13 chapters, line by line | Their claims are covered by `CLAIM_EVIDENCE_MATRIX.md`, `STAGE1_AUDIT.md` and Appendix D, all read |
| `paper/journal_v3_twin/build/numbers.json` | Superseded track |
| Full text of **Brancato et al. (2026)** | **BLOCKED — paywalled.** The decisive unresolved item (§3) |
| Full text of **Fejjari et al.** and **Dai et al.** | **BLOCKED** — flagged by the thesis itself as required reading |
| Published 5-page JSR version of Shorten et al. | **BLOCKED — paywalled.** The 29-page preprint was read instead; conclusion unaffected |
| EAAI 2023+ topical distribution | **BLOCKED — Crossref rate-limited.** Disclosed as unmeasured |
| Scopus CiteScore / rank / quartile for EAAI and JIRS | **BLOCKED — subscription-gated** |

## 8. Is Stage 1 complete?

**Substantially, with four named blockers — none resolvable from this machine.**

| Dimension | Status |
|---|---|
| Repository structure, code, configs | **Complete** |
| Experiment artifacts | **Complete** for all 13 benchmark trees |
| Research documentation | **Complete** for audits, claim matrices, novelty notes, venue analysis, architecture |
| Prior manuscript tracks | **Complete** — four superseded tracks plus the thesis identified and read at summary level |
| Reproducibility infrastructure | **Complete**, with two corrections |
| Leakage analysis | **Complete** — RCS pathway resolved; `am_design` pathway identified as unablated |
| Novelty positioning | **Blocked** on Brancato et al.'s full text |
| Venue verification | **Blocked** on Scopus access and EAAI topical measurement |
| Notebooks | Deferred, justified |

**My judgement: Stage 1 is complete enough to proceed to Part 2, provided Part 2 treats the
Brancato discrepancy as an open blocker rather than a resolved question.** Further inspection on
this machine will not resolve the four blockers; they need paywalled full texts and institutional
Scopus access, which are yours to obtain.
