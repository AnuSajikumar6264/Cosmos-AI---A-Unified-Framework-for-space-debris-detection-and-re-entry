# COSMOS-AI master research tracker

Last updated: 2026-11-04. Branch `product/mission-intelligence-console`. Baseline HEAD `78ee339`.
Verified test state: **341 passed, 3 skipped, exit 0** (2026-11-06, after the directive-C phases; see `MASTER_COMPLETION_TRACKER.md`). Earlier state at this tracker's creation: 217 passed (134 pre-product + 34 product + 22 Phase E/H + 11 Phase G+ + 12 G5 + 4 final-evaluation guards).

Status vocabulary: PASS · PARTIAL · FAIL · BLOCKED · NOT IMPLEMENTED · NOT VALIDATED · NOT EVALUABLE.

## Research questions

| ID | Question | Status | Evidence |
|---|---|---|---|
| RQ1 | Does cross-domain coupling improve prediction beyond independent subsystems? | **NOT DEMONSTRATED** | [`INTEGRATION_VALUE_ASSESSMENT.md`](INTEGRATION_VALUE_ASSESSMENT.md) |
| RQ2 | Do family statistics improve orbital lifetime prediction? | **NOT REPRODUCIBLE** | [`E12_SAME_LEARNER_C1.md`](E12_SAME_LEARNER_C1.md) |
| RQ3 | Does learned survival improve debris-cloud forecasts? | **PARTIALLY SUPPORTED** | [`C2_EVALUATION.md`](C2_EVALUATION.md) |
| RQ4 | Does operational status improve decay-regime assignment? | **INCONCLUSIVE** | [`C3_EVALUATION.md`](C3_EVALUATION.md) |
| RQ12 | Does model ranking transfer across temporal origins? | **NO — confirmatory** on a never-scored fold: no arm holds rank across 3 origins; `physics_only` 1st→4th→1st; `xgboost` last on tune-A and first on test at all 3 origins | [`G5D_FINAL_DECISION_REPORT.md`](G5D_FINAL_DECISION_REPORT.md) |
| RQ5 | Do health flags improve conjunction decision priority? | **NOT EVALUABLE** | [`C4_EVALUATION.md`](C4_EVALUATION.md) |
| RQ6 | Does the dated forecast generalise prospectively? | **BLOCKED** | [`T1_LATER_SNAPSHOT_EVALUATION_READINESS.md`](T1_LATER_SNAPSHOT_EVALUATION_READINESS.md) |
| RQ7 | Is the framework's novelty defensible against current literature? | **PARTLY** — 5 contributions retained, 6 withdrawn after a 2023–2026 review; benchmark artifact + selection-non-transfer measurement + reproducibility analysis survive | [`NOVELTY_AND_CONTRIBUTION_STATEMENT.md`](NOVELTY_AND_CONTRIBUTION_STATEMENT.md) rev 2 |
| RQ9 | Why are lifetime results weak and unstable? | **PARTIALLY ANSWERED; mechanism CLOSED as not established after G5d** — earlier attribution CORRECTED — the phenomenon is confirmed (Spearman +0.000 at both origins) but it is **not** caused by censoring (`known5` ≈ 1 in all splits) and **not** fully explained by the cap point-mass shift (ρ = +0.891 vs −0.158) | [`CENSORING_MISMATCH_CAUSAL_ANALYSIS.md`](CENSORING_MISMATCH_CAUSAL_ANALYSIS.md) |
| RQ10 | Can a selection-free combination beat the deployed expert? | **NOT PROMOTED** — better in 6/11 slices and worse in none, but **degrades 90 % coverage** (4/11 vs 8/11 at nominal) | [`G5_MODEL_COMPARISON.md`](G5_MODEL_COMPARISON.md) |
| RQ11 | Is a coherent multi-horizon reading as well calibrated as the incoherent one? | **YES, better** — 0 vs 54 violations and lower Brier at both horizons (p < 0.0001) | [`MULTI_HORIZON_CALIBRATION_EXPERIMENTS.md`](MULTI_HORIZON_CALIBRATION_EXPERIMENTS.md) |
| RQ8 | Do the conformalised intervals attain their nominal coverage? | **NO** — 3 of 4 deployed cells deviate significantly | [`PHASE_H_UNCERTAINTY_AUDIT.md`](PHASE_H_UNCERTAINTY_AUDIT.md) |

## Experiments

| ID | Experiment | Status | Command | Output | Result |
|---|---|---|---|---|---|
| E1 | Telemetry benchmark (ESA-ADB) | **PASS** (pre-existing) | `python -m cosmos.ai.telemetry.oof_benchmark` | `outputs/benchmarks/telemetry_esa_adb/` | arm-level event-wise F0.5; some arms single-seed |
| E2 | Alarm-selection ablation | **PASS** (pre-existing) | `scripts/posthoc_v2/p5_p8_selection.py` | `outputs/benchmarks/telemetry_esa_adb/posthoc_v2/` | post-hoc; see Phase G when run |
| E3 | Debris detection (SpotGEO) | **PASS** (pre-existing) | `python -m cosmos.ai.vision.spotgeo` | `outputs/benchmarks/vision_spotgeo/` | benchmark only; no unseen-condition set |
| E4 | Lifetime prediction | **PASS** (pre-existing) | `python -m cosmos.ai.lifetime.run` | `outputs/benchmarks/reentry_lifetime/origin{2011,2016}_uncontrolled/` | pinball 0.0593 (2016) / 0.0616 (2011) |
| E5 | Collision risk (Kelvins CAC) | **PASS** (pre-existing) | `python -m cosmos.ai.conjunction.run` | `outputs/benchmarks/conjunction_kelvins_cac/` | held-out split; not independently validated |
| E6 | Re-entry T1 window | **PARTIAL** | `python -m cosmos.ai.twin.prospective` | `outputs/benchmarks/twin_prospective_t1/` | **not blind** — exploratory only |
| **E7** | **Coupling ablations** | **PASS** | `python scripts/phase_e_coupling_ablations.py --n-boot 4000` | `outputs/phase_e/` | **RQ1 NOT DEMONSTRATED** |
| E8 | Uncertainty propagation audit | **PASS** | `python scripts/phase_h_uncertainty_audit.py --n-boot 4000` | `outputs/phase_h/` | **nominal conformal coverage NOT attained** in 3 of 4 deployed cells |
| E9 | Distribution-shift evaluation | **PARTIAL** | included in Phase H | `outputs/phase_h/` | coverage degrades with time from origin (rank trend −0.83 to −0.94 at 2016) |
| E10 | End-to-end scenario | **PASS** | `python scripts/run_pipeline.py --as-of 2026-10-27` | `outputs/pipeline/run_*/` | 7/7 modules; software only |
| E11 | Prospective scoring of dated forecast | **BLOCKED** | `python scripts/check_t1_later_snapshot.py` | `outputs/run_phase_d/` | needs snapshot ≥ 2026-11-26 |
| E12 | C1 same-learner replication | **PASS** | `python scripts/e12_same_learner_c1.py --n-boot 4000` | `outputs/e12_same_learner/` | **NOT REPRODUCIBLE** — effect is learner-specific; no refit needed (cache verified to 0.0) |
| E13 | C2 deployed-expert re-fusion | **NOT STARTED** | requires re-fitting the gate | — | methodology change; needs approval |
| E14 | C3 additional windows | **BLOCKED** | depends on later snapshots | — | coupled to E11 |

| G1 | Selection-free robust combination (median / mean blend) | **PASS** (not promoted) | `python scripts/phase_g_lifetime_optimization.py --n-boot 4000` | `outputs/phase_g_lifetime/` | −19.4 % vs deployed at 2016, inconclusive at 2011 → **DO NOT PROMOTE** |
| G2 | Coherent multi-horizon reading vs isotonic | **PASS** | `python scripts/phase_g_multihorizon_coherence.py --n-boot 4000` | `outputs/phase_g_multihorizon/` | coherent reading better: 0 vs 54 violations, Brier p < 0.0001 → **recommended for reporting** |
| G3 | Windowed / weighted conformal calibration | **NOT RUN** | — | — | needs new calibration fits |
| G4 | Physics prior + learned residual | **NOT RUN** | — | — | needs model training (~hours) |
| G5 | Rolling-origin / expanding-window validation | **NOT RUN** | — | — | **critical gap** — all G+ candidates unconfirmed without it |
| G6 | Survival formulations (RSF, discrete-time hazard, Cox) | **NOT RUN** | — | — | needs model training |
| G7 | Telemetry improvement | **NOT RUN** | — | — | frozen modules; no unscored test half remains |

| G5a | Censoring-mismatch causal analysis | **PASS** | `python scripts/g5_censoring_causal_analysis.py --n-boot 4000` | `outputs/g5_censoring/` | censoring **refuted** as the cause; cap point-mass shift confirmed and reverses, but does **not** explain the failure |
| G5b | Rolling evaluation across 11 launch-epoch slices | **PASS** | `python scripts/g5_rolling_origin.py --n-boot 2000` | `outputs/g5_rolling/` | **no candidate promoted** — accuracy/calibration trade-off; rank agreement mean Spearman +0.327, 24 % of slice pairs negative |
| G5c | G5 figures | **PASS** | `python scripts/g5_figures.py` | `outputs/g5_figures/` | 5 figures from executed results |
| G5d | Rolling-origin **refit** at new origins | **NOT RUN** | — | — | ~1–3 h GPU per origin; the remaining confirmatory gap |
| G5e | Arm B consistent censoring / Arm C survival-aware selection | **NOT RUN** | — | — | protocol change + refits |

| I1 | Literature and novelty review | **PASS** | delegated live search + independent re-verification | `docs/research/PHASE_I_*`, `LITERATURE_COMPARISON_MATRIX.md`, `NOVELTY_AND_CONTRIBUTION_STATEMENT.md` | B and D **already done**; C phenomenon already done; A artifact-only. Two priority threats verified: [21] Zou 2026, [55] TC-CAD |

| G5d | **Confirmatory refit at unexamined origin 2006** | **PASS** (outcome INCONCLUSIVE) | `python scripts/g5d_origin2006_refit.py --learners xgboost,mlp` then `scripts/g5d_analyse.py --n-boot 4000` | `outputs/g5d_origin2006/` | 20.6 min. **H1 NOT_EVALUABLE** (2 learners), **H2 SUPPORTED** (first confirmatory evidence), **H3 UNDERPOWERED → CLOSED**. Unanticipated: `xgboost` ranks **last on tune-A and first on test at all 3 origins** |
| L-dsgp4 | ML-dSGP4 as physics baseline | **NOT_EVALUABLE** | — | `docs/research/ML_DSGP4_FEASIBILITY.md` | **fair comparison impossible** — no TLE/B*/ephemeris inputs (L4); target is state vector not time-to-decay; B* would leak the outcome |
| M-rmse | Exclude mean-elicited `rmse_log10` | **PASS** | `python -m pytest tests/test_final_evaluation_guards.py` | guard test | enforced by non-use; published CSV preserved unmodified |
| F-recheck | Phase F eligibility re-check | **BLOCKED** | `python scripts/check_t1_later_snapshot.py` | `outputs/run_phase_d/` | outcome days available **−1**; needs snapshot ≥ 2026-11-26 |
| O-journal | JIRS verification | **PARTIAL** | OpenAlex source record | `docs/research/FINAL_JOURNAL_POSITIONING.md` | ISSN/publisher/metrics **verified**; **Scopus rank NOT verifiable** (SCImago 403, Springer auth-gated) |

| O-lit | **2023–2026 prioritised literature review** | **PASS** | live OpenAlex/Crossref/arXiv retrieval | `docs/research/LITERATURE_REVIEW_2023_2026.md`, `RESEARCH_GAP_ANALYSIS.md` | 34 refs, **88 % from 2023–2026**; 6 contributions withdrawn, 5 retained |
| M-fix | Correct the learner-backend map | **PASS** | `python scripts/final_reproducibility_audit.py` | `outputs/final_repro/` | **2 of 7** learners reproducible (was reported 3/7); **both** selected learners unavailable |

## Dependencies and data requirements

| Need | For | Status |
|---|---|---|
| CelesTrak SATCAT snapshot, data date ≥ 2026-11-26 | E11, E14, RQ6 | **BLOCKED** — needs download authorisation; earliest useful date 2026-11-26 |
| Identity-linked telemetry + CDM dataset | RQ5 / C4 | **BLOCKED** — operator agreement or licensed access; not obtainable here |
| Independent debris imagery under different conditions | Phase G3 | **BLOCKED** — no such public set identified |
| Impact-state ground truth | Phase G5 | **BLOCKED** — does not exist for these objects |
| Web access for literature verification | RQ7 / Phase I | **USED 2026-11-04** — AVAILABLE — verified 2026-11-04 against the Crossref REST API (`api.crossref.org/works`), which returns real DOIs, containers and years. Phase I is feasible and must use verified records, never memory. |
| OPSSAT checkpoint weights | Phase J / L13 | **BLOCKED** — absent by `.gitignore` design; metrics remain traceable |

## Phase status

| Phase | Scope | Status |
|---|---|---|
| A | Audit | **PASS** |
| B | Target architecture | **PASS** |
| C | Contracts, orchestration, adapters | **PASS** |
| D | C2/C3/T1 regression, L13, L17, dashboard, T1 readiness | **PASS** |
| P1 | Mission Intelligence Console | **PASS** |
| **E** | **Coupling ablations** | **PASS** — RQ1 answered NOT DEMONSTRATED |
| F | Prospective temporal validation | **BLOCKED** — infrastructure ready, data absent |
| G | Component-level scientific validation | **NOT STARTED** |
| H | Uncertainty and evidence framework audit | **PASS** — coverage measured empirically; conformal claims must be withdrawn |
| I | Novelty and literature review | **PASS** — 76 works retrieved live; 5 load-bearing claims independently re-verified. Integrated-framework, calibration-failure and abstention novelty all **refuted** |
| J | Full-system validation and reproducibility | **PARTIAL** — tests and provenance exist; clean-environment procedure not written |
| K | Final research position and journal strategy | **NOT STARTED** — must follow G–I |
| L | Manuscript | **NOT STARTED** — blocked on K |
| M | Figures, tables, supplementary | **NOT STARTED** |
| N | Submission package | **NOT STARTED** |

## Scientific limitations register (pointers)

Full register: [`limitations_register.md`](limitations_register.md). Critical entries:

- **L1** no identity-linked dataset across domains → bounds RQ1 and blocks RQ5 permanently.
- **L2/L3** T1 is not blind → temporal evidence is exploratory.
- **L3b** dated forecast has −1 days of outcome coverage → RQ6 blocked.
- **L17** per-horizon lifetime calibration is not a coherent CDF → preserved by decision.
- **New (Phase E)** physics feature group reverses sign between origins → see C1 report.

## Next concrete actions, in priority order

1. **Phase G** — component validation. Unblocked, uses existing artifacts. Highest value now.
2. **Phase I** — literature and novelty review. Crossref verified reachable; must not be
   written from memory.
4. **E12** — C1 same-learner replication, to resolve the learner/origin confound. Needs a new
   model fit, therefore approval and compute.
5. **Phase K → L → M → N** once G, H and I are complete.
6. **E11** on or after 2026-11-26, with download authorisation.
