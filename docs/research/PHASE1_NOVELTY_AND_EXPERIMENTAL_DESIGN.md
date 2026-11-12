# Phase 1 — Research novelty and experimental design specification

Date 2026-11-06. Produced under the *Complete Research, Novelty, Engineering and Validation
Directive*, §4. **This is a design specification, not a manuscript.** It decides what COSMOS-AI can
defensibly claim, what each candidate claim would require, and which experiments Phases 2–7 must
run. It does not write results.

---

## 0. How this document was produced, and what it does not rest on

**Retrieval.** `scripts/literature_retrieve.py` queried the OpenAlex works API live on 2026-11-06:
21 queries over 8 topic groups, 2023 onward, articles/preprints/chapters, 20 results per query.
Every raw API response is archived verbatim under `outputs/literature/phase1/raw/` (21 files), the
de-duplicated table is `outputs/literature/phase1/records.csv` (**368 unique records**, abstracts
reconstructed from OpenAlex's inverted index), and `query_log.json` records every URL, status and
count. Zero query errors.

**Verification.** Two independent passes, both live:

| Set | Count | Registry | Result |
|---|---|---|---|
| DOIs in the prior review `LITERATURE_REVIEW_2023_2026.md` (R1–R34) | 32 distinct | Crossref; DataCite for arXiv/Zenodo | **32/32 resolve** (30 + 2) |
| New records selected for this document (N1–N21) | 21 | Crossref; DataCite for arXiv | **21/21 resolve** → `selected_records_crossref.csv` |

Where Crossref's issue year differs from OpenAlex's online year it is shown as `online (issue)`.

**What was not done.** No paywalled full text was read. Three selected records have no abstract at
either registry and are used at **title level only** (marked †). Brancato et al. remains
abstract-only, as before. Relevance judgements below are mine and are stated as such; the archived
records allow anyone to disagree with them.

**Prior work this builds on, unchanged.** `LITERATURE_REVIEW_2023_2026.md` (R1–R34),
`research_design/NOVELTY_NOTE.md` (the ESA-ADB competitor set), `PHASE_I_NOVELTY_REVIEW.md`
(76 works; verdicts A–D), `FINAL_LITERATURE_AUDIT.md`, `RESEARCH_GAP_ANALYSIS.md` (G-A…G-E) and
`NOVELTY_AND_CONTRIBUTION_STATEMENT.md` rev 2 (C-1…C-5 retained, six withdrawn). This document
extends them to the directive's ten topics and reconciles them with the JINT manuscript's framing,
which none of them covers.

---

## 1. Structured literature review, by directive topic

Fields per record: ID · first author(s), year · venue · DOI · methodology · data · evaluation ·
limitation (as stated or evident from the abstract). Abstracts are in `records.csv`.

### 1.1 Satellite digital twins

Prior coverage: R32–R34 — the term is held by satellite-*network* digital twins (Plotinus; LEO
constellation networking; multi-layer deployment). Nothing predictive about health or orbit.

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N19 | Li, Aslam, Wileman et al., 2021 (2022) · IEEE Access · `10.1109/access.2021.3136458` | Tutorial introduction to digital twins in aerospace: definitions, product-development / design / predictive-maintenance uses | Conceptual; no evaluation protocol |
| N20 | Ferrari & Willcox, 2024 · Nature Computational Science · `10.1038/s43588-024-00613-8` | Perspective on DTs in mechanical and aerospace engineering (no abstract indexed; title-level) | † |
| N15 | Xu, Wen, Song, Zhao, 2023 · IEEE IoT Magazine · `10.1109/iotm.001.2200271` | "DT" ML orbit prediction for IoT: learns measurement/estimation/unmodelled error of traditional orbit prediction | Orbit prediction only; no health, debris or uncertainty treatment |
| N14 | Wang & Yang, 2026 (2027) · Aerospace Science and Technology · `10.1016/j.ast.2026.113753` | Integrated structural–thermal design and DT framework for a satellite payload module (title-level) | † Structural/thermal design, not operations monitoring |

**What this establishes.** In 2021–2026 "satellite digital twin" names networking, orbit-prediction
and structural-thermal work. **No predictive twin combining health, lifetime, re-entry, debris and
conjunction evidence was retrieved.** That gap is real — and the project's own Phase E shows it
cannot be filled with the available data (§2, row 1).

### 1.2 Spacecraft health monitoring

Prior coverage: R9–R14, R18 (Herrmann 2024 re-evaluation; reviews; deep clustering; explainable AD;
generic diagnostic framework; FDP review).

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N13 | Tahir, Jabbarpour, Vo, Kowalczyk, 2025 · IEEE Access · `10.1109/access.2025.3639551` | Dual benchmarking of classical and deep AD models across real telemetry and Basilisk-simulated data; explainability | Mission-specific real data; no official-split protocol stated in abstract |
| N12 | Schefels, Schlag, Helmsauer, 2025 · CEAS Space Journal · `10.1007/s12567-024-00589-1` | Synthetic satellite telemetry for ML, motivated by label scarcity (GRACE-FO thousands of parameters) | Synthetic; the same caveat applies to our `cosmos_synthetic` corpora |

**What this establishes.** Subsystem-specific (power/thermal/ADCS) health ML exists on proprietary
or simulated data. The public benchmarks we use anonymise channels (ESA-ADB `channel_N`), so
**named-subsystem attribution is not evaluable here**; ESA-ADB's `subsystem_F0.5` over anonymised
groups is the closest available measure (Phase 2.2).

### 1.3 Telemetry anomaly detection (ESA-ADB and competitors)

Prior coverage: R9, R15–R17, R19 and the full competitor set in `NOVELTY_NOTE.md` — Kotowski et al.
(ESA-ADB, DMLR 2026, arXiv `2406.17826`, DataCite-verified), Brancato et al. (AST 2026,
`10.1016/j.ast.2026.113957`, abstract only), Şahin TC-CAD (Zenodo `10.5281/zenodo.23322711`,
DataCite-verified), Heydari et al. (IEEE Access 2026), Alcarria et al., Allegrini & Pompei.

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N21 | Nguyen, Rozenberg, Zhu, Hu, 2026 · arXiv `2607.07335` | Systematic supervised vs unsupervised benchmark on ESA-ADB across two missions | Uncorrected event-wise metrics, mostly lightweight subsets (per `NOVELTY_NOTE`); not comparable with the official corrected metric |

**What this establishes.** Unchanged from `NOVELTY_NOTE` §2: telecommand gating and operator-budget
deferral are pre-empted (TC-CAD, Heydari); the distinction that survives is **event-level
calibration across channels with cross-fitted selection** against TC-CAD's per-channel point-level
ACI, which collapses the event-wise score. The pre-registered negative deep-learning result is
consistent with Herrmann 2024 (R9) and is positioned as extending that line, not discovering it.

### 1.4 Multimodal satellite data fusion

Prior coverage: none.

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N18 | Li, Xie, Li, Fang, 2023 (2024) · IEEE TGRS · `10.1109/tgrs.2023.3339522` | FedFusion: federated multi-satellite multi-modality *remote-sensing* fusion under on-orbit compute limits | Image-modality fusion for Earth observation; not spacecraft-state evidence |
| N17 | Zhang, Yin, Kuang, Huang, Peng, 2026 · Sensors · `10.3390/s26030969` | Physics-informed multimodal decision-level fusion for hypervelocity-impact damage classification | Structural damage imaging; sensors co-located on one specimen — identity is trivial |

**What this establishes.** Three queries returned **no work fusing telemetry health, orbital state,
debris imagery and conjunction evidence for the same spacecraft**. The reason is the one the
project hit itself: no public identity-linked corpus spans those modalities (limitation L1). The gap
is a *data* gap, not a method gap, and claiming it as a contribution would be claiming the absence
of a dataset.

### 1.5 Orbital lifetime and re-entry prediction

Prior coverage: R1–R8 (along-track density + ML; continual learning; ML uncontrolled re-entry
(Salmaso 2023); orbit-estimation survey; dSGP4; thermospheric density ML; solar-cycle influence).

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N10 | de Oliveira, Zesta, Garcia-Sage, 2025 · Frontiers Astron. Space Sci. · `10.3389/fspas.2025.1572313` | Tracked Starlink re-entries during rising solar cycle 25; drag response to dynamic events | Observational; one operator's fleet |
| N11 | Ocaya & Malevu, 2025 · npj Space Exploration · `10.1038/s44453-025-00007-8` | High-fidelity LEODO simulation: NRLMSISE-00 winds, wind-relative drag, Coriolis, J6; identifies narrow re-entry thresholds | Simulation; no catalogue-scale validation |

**What this establishes.** Both records confirm that solar/geomagnetic activity drives re-entry
timing at the event scale. **Our catalogue table carries F10.7 and Ap as a single value for all
31,396 objects** (evaluated at the as-of date), so the deployed lifetime models cannot represent
this driver at all — a concrete, citable limitation and a Phase 2.4 sensitivity target.

### 1.6 Space debris monitoring

Prior coverage: R27–R31 (radar/optical detection, light curves, STACK-CNN, constellation
observation, DebrisWatch II). Unchanged: SpotGEO reimplementation is infrastructure, not a
contribution (withdrawn C-10).

### 1.7 Satellite conjunction assessment

Prior coverage: none in the prior review.

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N5 | Uriot, Izzo, Simões et al., 2021 · Astrodynamics · `10.1007/s42064-021-0101-5` | Design and results of the ESA Kelvins Spacecraft Collision Avoidance Challenge: curated CDM dataset 2015–2019; task = predict final collision risk | Abstract describes the competition and "lessons learned"; baseline results are in the body — **read 2026-11-06 from the open-access arXiv copy (2008.03069)**: LRP baseline L = 0.694, 12 of 97 teams beat it, CRP L = 2.5; archived verbatim in `outputs/literature/phase1/uriot2021_baselines_arxiv2008.03069.md` (X12) |
| N2 | Sánchez, Vasile, Sanvido, Merz et al., 2024 · Advances in Space Research · `10.1016/j.asr.2024.09.014` | Dempster–Shafer treatment of epistemic uncertainty in CDM-based conjunction analysis; classification by confidence in Pc | Methodological; evaluation population not stated in abstract |
| N3 | Pavanello, De Maria, De Vittori, Maestrini et al., 2025 · Acta Astronautica · `10.1016/j.actaastro.2025.07.027` | CAMmary: review of collision-avoidance *manoeuvre design* methods | Manoeuvre design, downstream of risk prediction |
| N1 | Zerrouki, Ouari, Bouziane, Gacem, 2026 · Acta Astronautica · `10.1016/j.actaastro.2026.08.013` | Deep learning for full-horizon uncertainty-aware prediction of CDM sequences (title-level) | † |
| N4 | Tüylek Tok, Yağlıoğlu, Dağ, Kahya, 2026 · arXiv `2609.13191` | Hybrid TCN-Transformer early prediction of collision probability from CDM sequences; motivated by electric-propulsion lead times | Preprint; dataset and protocol not in abstract |

**What this establishes.** CDM-sequence risk prediction is an active line (N1, N4) with
uncertainty treatments (N2). Our Kelvins result — a last-reported-risk rule at F2 0.739 against the
best learned arm's 0.168 under the native decision rule — belongs in this conversation, and **must
be positioned against the baselines reported in N5's body before any claim is made**. No retrieved
work performs propagation/TCA screening from state vectors with ML; nor does ours (Phase 2.5).

### 1.8 Conformal prediction and uncertainty calibration

Prior coverage: R20–R26 (task-aware conformal envelopes for spacecraft; horizon-aware group
conditional CP with cluster bootstrap; beyond exchangeability; online multi-step CP; fixed-horizon
right-censoring evaluation; isotonic distributional regression; PINN review).

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N16 | Zhang & Zhou, 2025 · IEEE TII · `10.1109/tii.2025.3529920` | Conformal UQ for industrial time series under temporal dependence and drift; interval from two online components | Industrial process data; confirms the exchangeability failure mode we report |

**What this establishes.** Reinforces Phase I verdict **B — already done**: coverage failure under
drift is a theorem (R22), an audited protocol (R21) and a solved engineering problem (online CP).
We measure it; we do not discover it.

### 1.9 Temporal distribution shift

Prior coverage: R22, R23; Mou et al. MORA (preprint, `NOVELTY_NOTE`).

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N9 | Ting, Liu, Gong, Zhang, Zhu, 2024 · The VLDB Journal · `10.1007/s00778-023-00832-x` | A new distributional treatment for time-series anomaly detection (title-level) | † |
| N7 | Kwon & Kim, 2026 · Scientific Reports · `10.1038/s41598-026-40637-w` | Conformal selective prediction with cost-aware deferral under distribution shift (clinical triage); finite-sample coverage sets, defer when expected cost falls | Clinical; but it is exactly abstention + conformal + shift, generically |

**What this establishes.** Selection non-transfer across temporal origins is established as a
phenomenon in forecasting and domain generalisation (Phase I verdict C); our contribution is the
**first measurement of it in orbital lifetime prediction** (C-2), which survives. Abstention under
shift is generically occupied (N7, R19) — Phase I verdict D stands.

### 1.10 Evidence provenance and uncertainty-aware decision support

Prior coverage: Hawkins et al. 2023 (assurance case, JIRS), Spahic et al. 2023 (risk-informed
warning identification, JIRS) in the manuscript's references.

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N6 | Schlegel & Sattler, 2024 (2025) · Information Systems · `10.1016/j.is.2024.102495` | End-to-end provenance capture for ML pipelines beyond MLflow/Git; addresses incomplete traces and coarse granularity | Tooling for development workflows; not decision-time evidence provenance |
| N8 | Sørbø & Ruocco, 2023 · Data Mining and Knowledge Discovery · `10.1007/s10618-023-00988-8` | Taxonomy of TSAD evaluation metrics and their properties; guidance on metric choice | Confirms metric choice is a studied problem — relevant to any "evaluation framework" claim |

**What this establishes.** Provenance capture for ML pipelines is an established tooling line
(N6); our `contracts.Provenance`/`provenance.py` is an application of it. Evaluation-metric
methodology for TSAD is an active, occupied area (N8 plus three 2025–26 preprints in `records.csv`:
`arXiv 2510.17562`, `2603.06131`, `2511.18739`). **A "unified evaluation framework" cannot be
claimed as novel at the metric level.**

---

## 2. Research gap matrix

| Direction | Existing approaches | Their limitations | COSMOS-AI implements | Does differently | Experimentally demonstrated | Remains unvalidated | Verdict |
|---|---|---|---|---|---|---|---|
| Predictive satellite digital twin | networking DTs (R32–34); orbit-prediction DT (N15); structural-thermal DT (N14) | none predicts health + orbit + debris + risk for one object | `ObjectTwin` state, 7 typed adapters, orchestrator, regime gate, abstention | evidence contracts that reject unresolvable joins; per-module validation status carried in the state | end-to-end execution over saved artifacts (71 runs); **integration value NOT DEMONSTRATED** (Phase E: C1 learner-confounded, C2 deployed arm p = 0.364, C3 inconclusive, C4 0 joinable pairs) | any performance benefit of integration | **Engineering frame only; no scientific claim** |
| Multimodal satellite evidence fusion | remote-sensing fusion (N18); co-located sensor fusion (N17) | none spans telemetry/orbit/imagery/CDM for one spacecraft | noisy-OR `fusion.decide` with five compatibility gates | gates make the absence of a join explicit instead of fabricating one | gate behaviour unit-tested | fusion quality — **no decision-quality metric exists**; no joinable data (L1) | **Not claimable; data gap** |
| Telemetry anomaly detection at full channel scale | Kotowski (official benchmark), Brancato (SMED/Q-GPR, 0.902 M1), TC-CAD (per-channel ACI, deferral), Heydari (budgets), Alcarria, Nguyen (N21) | Brancato paywalled, protocol details unknown; TC-CAD's conformal layers collapse event-wise F0.5; Nguyen uses uncorrected metrics | AR(8) scorer; conformal p-values → BH across channels → merge; cross-fitted selection | **event-level** calibration with selection on the whole training half; pre-registered, hash-frozen; official metric byte-identical to upstream | H6 +0.353 [+0.206, +0.488] Holm p = 0.0015 (M1 confirmatory); H4/H5 refuted; burden–recall trade-off 154,310× FA vs 6.4× recall; M2 cannot discriminate (6 anomalies) | mechanism (five protocol differences; 3b not run); absolute performance vs Brancato (blocked); generalisation beyond M1 full scale | **Strongest defensible result** |
| Spacecraft health monitoring by subsystem | mission-specific / simulated subsystem ML (N13, N12) | proprietary or synthetic data | `cosmos_monitor` rule; `LearnedHealthMonitor`; legacy simulator | — | `cosmos_monitor` ties out-of-limits on M1 lightweight, collapses at full scale | named-subsystem attribution — channels anonymised | **Not evaluable as named subsystems** |
| Orbital lifetime / re-entry | R1–R8; N10, N11 (solar-driven re-entry) | few objects (R3 ~400); protocols undisclosed (R2); accuracy-only framing (R4) | catalogue-scale (31,396) censored capped target; launch-family cluster bootstrap; 3 temporal origins; Mondrian CQR | forward-in-time, censoring-aware, selection-transfer measured | selection regret 3.4 → 18.7 → 25.2 % across origins, significant at 2016; G5d H2 **SUPPORTED** at an unexamined origin; rank τ = −0.30 | space-weather sensitivity (features constant in snapshot); `am_design` missingness (Stage 2 not run); training-level reproducibility (2/7 learners) | **Defensible artifact + measurement** (C-1, C-2) |
| Re-entry footprint / corridor | N11 simulation; Starlink tracking (N10) | no public impact-state truth | legacy MC footprint chain; surrogate (n = 40,000 vs simulator) | — | surrogate matches the simulator | any real-world accuracy (L5) | **NOT EVALUABLE** |
| Conjunction assessment | Kelvins CAC (N5); CDM-sequence DL (N1, N4); DS epistemic (N2) | anonymised events; propagation not in scope | final-CDM risk prediction; gated fusion over learners | — | trivial last-risk rule F2 0.739 > best learned 0.168 (native rule); verdict reverses with a tuned threshold | positioning against N5's reported baselines (body not read); propagation/TCA — no data path | **Negative result; propagation NOT EVALUABLE** |
| Conformal / calibration under shift | R20–R26, N16 | — (well developed) | Mondrian CQR; per-horizon isotonic (L17) | — | 11/24 Phase H cells deviate; coverage decays with time from origin; coherent reading beats isotonic (G2) | nothing novel; L17 fix is a known-bad design corrected (R25) | **Confirmation, not contribution** (Phase I B) |
| Temporal selection non-transfer | forecasting/domain-generalisation literature (Phase I C); N9 | not studied in orbital prediction | rolling origins; G5d confirmatory refit | domain-first measurement | **confirmed** (G5d H2) | mechanism (cap-mass shift) **not confirmed** (G5a) | **Defensible, narrow** (C-2) |
| Provenance & decision support | N6 (pipeline provenance); Hawkins 2023 (assurance); N7, R19 (abstention) | — | typed `Provenance`, `provenance.py`, run manifests, `decide()` abstention | — | provenance recorded on 71 runs; abstention exercised | decision quality — no metric; completeness of provenance (L12) | **Application of known practice** |
| Evaluation methodology | N8 metric taxonomy; Herrmann (R9); three 2025–26 metric preprints | — | pre-registration + freeze gate; block bootstrap; declared minimum effect; official metrics; burden metrics | combination applied with a refuse-to-run gate | one pre-registered study executed to verdict | nothing novel at metric level | **Practice, not novelty** |

---

## 3. Candidate contributions — ten-field specifications

Legend for the verdict: **D** defensible on current evidence · **D-cond** defensible if the named
experiment succeeds · **ND** not defensible.

### K1 — Evidence-aware multimodal satellite digital-twin architecture · **ND as a scientific claim; D as the engineering frame**

| Field | Specification |
|---|---|
| 1 Research question | Does evidence-aware integration of health, lifetime, debris and conjunction modules improve prediction or decision quality over the same modules used independently? |
| 2 Hypothesis | Integration improves at least one pre-declared endpoint per coupling (C1–C4). |
| 3 Methodology | Typed contracts, orchestrated adapters, regime gate, noisy-OR fusion with compatibility gates, abstention. |
| 4 Required implementation | **Exists** (`contracts`, `orchestration`, `adapters`, `twin/state`, `fusion`). Missing: stale-data and version-compatibility tests; state-consistency tests (Phase 4). |
| 5 Datasets | ESA-ADB, CelesTrak/GCAT, Kelvins CAC, SpotGEO — **no identity links between them** (L1). |
| 6 Baselines | Each module alone (Phase E arms). |
| 7 Ablations | Phase E C1–C4; E12 same-learner. |
| 8 Metrics | Per-coupling endpoints (pinball, cloud-count error, Brier, —). |
| 9 Expected failure cases | **Observed**: C1 learner-confounded and sign-inconsistent; C2 deployed arm p = 0.364; C3 inconclusive; C4 0 joinable pairs. |
| 10 Acceptance | At least one coupling SUPPORTED with the deployed configuration. **Not met.** |

**Verdict.** The project's own experiments refute the premise. The architecture stays as the
thesis's engineering vehicle with the integration value reported as NOT DEMONSTRATED. The literature
gap (§1.1, §1.4) exists but is a data gap we cannot close.

### K2 — Provenance-preserving evidence fusion methodology · **ND**

| Field | Specification |
|---|---|
| 1 RQ | Does provenance-gated fusion produce better-calibrated or safer decisions than ungated fusion? |
| 2 Hypothesis | Gated fusion abstains correctly on incompatible evidence and loses nothing on compatible evidence. |
| 3 Methodology | `fusion.decide` gates + noisy-OR; `Provenance` contract. |
| 4 Required implementation | A decision-quality metric and a labelled set of decisions — **neither exists**. |
| 5 Datasets | None with joint evidence and outcomes. |
| 6 Baselines | Ungated noisy-OR; single best module. |
| 7 Ablations | Remove each gate. |
| 8 Metrics | Would need decision regret / abstention precision — undefined here. |
| 9 Expected failure | Pre-empted generically (N6 tooling; N7/R19 abstention). |
| 10 Acceptance | Measurable improvement on a decision endpoint. **Cannot be evaluated.** |

### K3 — Uncertainty-aware health and mission decision support · **ND**

Pre-empted: TC-CAD budgeted deferral on ESA-ADB (R19), Heydari workload budgets, N7 conformal
selective prediction under shift. No operational cost ratio or false-alarm budget exists for the
missions (manuscript §14.3). Fields 4–10 cannot be filled with a defensible endpoint. The
burden–recall *measurement* survives inside K6; the *decision-support* claim does not.

### K4 — Temporal calibration and reliability-aware prediction · **ND**

Phase I verdict B, reinforced by N16: theorem (R22), audited protocol (R21), and fixes (online CP)
all published. Our Phase H / G1 measurement is reported as confirmation. The L17 incoherence is a
known-bad design with a published fix (R25), handled by G2.

### K5 — Unified evaluation framework for satellite monitoring and orbital-risk assessment · **ND as novelty; D as practice**

| Field | Specification |
|---|---|
| 1 RQ | Does a common protocol (pre-registration + freeze gate, temporal-origin selection-transfer test, censoring-aware scoring, burden metrics) change which methods are preferred? |
| 2 Hypothesis | Rankings under the protocol differ from rankings under default evaluation. |
| 3 Methodology | The protocol as executed in the ESA-ADB and lifetime studies. |
| 4 Required implementation | Exists piecewise; no unified harness. |
| 5–8 | ESA-ADB, lifetime; baselines = default evaluation; metrics = rank agreement. |
| 9 Expected failure | Metric methodology is occupied (N8 and three preprints); pre-split datasets already called for (R9); pre-registration is standard elsewhere. |
| 10 Acceptance | A reviewer accepts it as a methodological contribution rather than practice. **Unlikely.** |

**Verdict.** Report as *methodology used*, prominently; do not claim as a contribution.

### K6 — Pre-registered alarm-layer selection study on ESA-ADB at full channel scale · **D**

| Field | Specification |
|---|---|
| 1 Research question | Under the official ESA-ADB protocol at full channel scale, does the data used to select an event-level alarm layer matter more to detection than the capacity of the scorer, and under what conditions does the effect hold? |
| 2 Technical hypotheses | Pre-registered, frozen `09a98f5e160e`: **H6** A1 − A0 ≥ +0.05 corrected EW F0.5 (M1, primary layer); **H4** A3 − A1 ≥ +0.05; **H5** A3 − A2 ≥ +0.05. Directional, Holm-corrected. |
| 3 Methodology | AR(8) residual non-conformity per channel → conformal p-values → Benjamini–Hochberg across channels → top-k → merge window; operating point cross-fitted on the whole labelled training half (K = 5 contiguous blocks, 1-day purge) vs on the 9-month calibration period; official metric code byte-identical to upstream `67194d3`; paired bootstrap over fixed 30-day blocks (86 M1 / 22 M2), hierarchical over seeds, B = 2000. |
| 4 Required implementation | **Confirmatory part complete.** Remaining: **3b Stage 1** — 2² re-selection over selection data × grid, no refit, minutes of CPU, *approval requested*; **3b Stage 2** — 2³ over σ × calibration pool × fit data at both selection levels, 12 AR(8) OOF fits, 3–4 h, *approval deferred to Stage 1 result*; `oof.py:126` extension only if non-AR(8) scorers are to be cross-fitted (not required). |
| 5 Datasets | ESA-ADB v1.0 (`10.5281/zenodo.12528696`): M1 target 58 channels, 30 s grid, official split 2007-01-01, **55 test anomalies** (confirmatory); M2 target 47 channels, 18 s, split 2001-10-01, **6 test anomalies** (replication, no inference). |
| 6 Baselines | A0 calibration-period selection; A2 XGBoost event model (5 seeds); GlobalSTD (reproduces published values to 0.001 ×8); out-of-limit rule; PatchTST; Chronos-Bolt probe; external: TC-CAD ACI collapse (R19), Brancato 0.902/0.883/0.754 (abstract only, **blocked**). |
| 7 Ablations | Done: metric (composite vs anomaly-only — all three verdicts hold); alarm layer (5 layers incl. point-level ACI); channel set (target vs lightweight — effect reverses); scorer class. Pending: **3b factorial** (attribution); **3d** equal tuning budget and ≥ 2 deep architectures (comparator fairness). |
| 8 Metrics | Corrected event-wise F0.5 (composite, anomaly-only), event-wise precision/recall, ADTQC, alarm runs, false-alarm runs, false alarms per year over the identical 7.0007-year period; selection score vs test score (cross-fit optimism). |
| 9 Expected failure cases | Effect reverses on M2 (**observed; M2 cannot test the question**); reverses on lightweight M1 (**observed**, 21× cross-fit optimism); 3b attributes the gain to σ or grid rather than selection data (would **reframe H6 as a protocol effect** — already how it is stated); Brancato's out-of-limit 0.754 vs our 0.0007 remains unreconciled (**blocked** — different estimator, paywalled); seed SD 0.236 (A2) makes H4/H5 underpowered. |
| 10 Acceptance criteria | (a) six confirmatory verdicts unchanged and re-derivable (`tests/test_jint_manuscript.py`, `tests/test_figures.py`); (b) 3b Stage 1 reproduces A0's and A1's selected operating points and reports F4/F5 main effects with intervals; (c) every claim sits inside the claim-boundary table (`FINAL_RESEARCH_DIRECTION_RECOMMENDATION.md` §1); (d) **no absolute-performance or cross-mission claim**; (e) burden and recall reported together, both directions. |

### K7 — Catalogue-scale forward-in-time, censoring-aware lifetime benchmark with selection-transfer measurement · **D (artifact + measurement)**

| Field | Specification |
|---|---|
| 1 Research question | On a catalogue-scale, forward-in-time, right-censored lifetime benchmark, does model ranking measured at one temporal origin carry information about the next? |
| 2 Technical hypotheses | G5d pre-registered at the unexamined origin 2006: H1 rank transfer (NOT_EVALUABLE, 2 learners), **H2 selection non-transfer — SUPPORTED**, H3 (UNDERPOWERED, closed). Secondary: selection regret > 0 at each origin. |
| 3 Methodology | `z = log10(min(t, 1826.25))`, point mass at the cap; pinball on 7 quantiles (local elicitability under fixed-horizon censoring — `rmse_log10` excluded by non-use); launch-family cluster bootstrap 4000 draws; BH within families; Mondrian CQR by `type1 × perigee band`; origins 2011/2016 (+2006 confirmatory). |
| 4 Required implementation | **Exists.** Free additions: trivial reference predictor (marginal quantiles; constant-at-cap); per-arm bootstrap intervals on the leaderboard. Pending approval: **`am_design` Stage 2** (missingness ablation; Stage 1 evidence: design-derived cov80 0.5625 vs 0.80, calibration split 5.9 % design-derived). **Not feasible**: retraining the two selected learners (backends unavailable). |
| 5 Datasets | CelesTrak SATCAT snapshots (70,288 / 71,132 objects), GCAT families and classes, NOAA/GFZ space weather; 31,396 objects in the deployed table; 2,667 / 2,978 / 7,277 scored at origins 2011 / 2016 / 2006. |
| 6 Baselines | `physics_only` (NRLMSIS expert); `equal_average`; feature-free oracle (every published arm beats it by 14–39 %). |
| 7 Ablations | Feature groups (`no_design`, `no_family`, `no_physics`, `no_space_weather`, `plus_rcs_2026`); same-learner C1 (E12); G1 selection-free blends (not promoted); G2 coherent multi-horizon reading (recommended); am_design Stage 2 (pending). |
| 8 Metrics | Pinball, MAE log10, cov80/cov90, width, Winkler, c-index; selection regret; rank τ/ρ across origins; subgroup coverage by `am_source` and class. |
| 9 Expected failure cases | Physics expert best at 2011 and worst at 2016 (**observed**); 11/24 coverage cells deviate (**observed**); cap-mass mechanism **not confirmed** (G5a); space-weather features **constant** in the deployed snapshot so storm-driven variation is unrepresentable; training-level irreproducibility (2/7 backends). |
| 10 Acceptance criteria | (a) G5d verdicts unchanged; (b) leaderboard intervals and trivial reference published from archives without refits; (c) am_design Stage 2 reported whatever its sign; (d) framed as *extending Herrmann's line into orbital prediction*, per `RESEARCH_GAP_ANALYSIS.md` §3; (e) no state-of-the-art claim. |

### K8 — OPS-SAT late-fusion calibration/stability study · **D-cond**

Conditional on **E6** (branch ablation) showing the fusion contributes calibration (ECE 0.035 vs
0.121) and seed stability (F1 SD 0.0066 vs 0.0977) rather than accuracy — `cnn` already beats
`hybrid` on the official protocol. Prerequisite: regenerate the lost per-seed score archive
(`test_scores_official.npz`; 122 archived runs, 380 s total training) and run time-blocked
significance. If E6 shows no contribution, **not a paper**.

---

## 4. Selection and reconciliation

**Selected scientific contributions.**

1. **Primary — K6.** The pre-registered alarm-layer selection study. Strongest methodology, best
   data, confirmatory result, a publishable pre-registered negative deep-learning result, and a
   quantified two-sided burden–recall trade-off. Novelty is bounded to event-level calibration
   with training-half selection against TC-CAD's point-level approach, and to the benchmark
   characterisation of Mission 2.
2. **Secondary — K7.** The censoring-aware catalogue-scale benchmark and the first measurement of
   selection non-transfer in orbital lifetime prediction (C-1, C-2), with the reproducibility
   analysis (C-3) and preserved negatives (C-5). Space venue, separate paper.
3. **Conditional — K8**, only after E6.

**Not contributions, by evidence.** K1 (integration refuted by Phase E), K2 (no metric, no data),
K3 and K4 (pre-empted), K5 (occupied at metric level). Each is retained as *engineering* or
*methodology used*, stated plainly.

**Reconciling the two framings.** `NOVELTY_AND_CONTRIBUTION_STATEMENT.md` rev 2 (C-1…C-5) and the
JINT manuscript are not in conflict; they are the two papers of
`FINAL_PRIMARY_AND_SECONDARY_PAPER_STRATEGY.md` (K7 and K6 respectively). The omission is that the
novelty statement predates the Track 3 pivot and never records the telemetry contribution. This
specification is the reconciled record: **the project's scientific output is K6 + K7; its
engineering output is K1 with integration value NOT DEMONSTRATED.** Two earlier manuscript tracks
were superseded for asserting K1 as a result; that decision stands.

One internal disagreement remains and is recorded rather than resolved by fiat: Phase I grades the
lifetime benchmark "INCREMENTAL — artifact, not method" (citing Castet & Saleh 2009, Salmaso 2023),
while the later novelty statement grades it "Defensible — intersection unoccupied" after Shorten et
al. 2023 was read in full. Both agree it is an **artifact contribution**, which is how K7 is
specified above.

**Thesis-level contribution set** (for Phase 9, locked): one confirmatory pre-registered empirical
result with a negative deep-learning finding (K6); one benchmark artifact with a domain-first
measurement and a reproducibility analysis (K7); one evidence-contracted integration system whose
integration premise was tested and not supported (K1), reported as such.

---

## 5. Experiments this selection requires — input to Phases 2–7

| # | Experiment | Serves | Cost | Approval | Phase | Notes |
|---|---|---|---|---|---|---|
| X1 | Regenerate OPS-SAT per-seed scores; compare `per_run_*.csv` to archive; add `.gitignore` exception | K8; Phase 2.1 | < 1 h (380 s training archived; Chronos embedding cache also lost, needs weights) | not a protocol change — **proceed** | 2.1 | reproducibility test in itself |
| X2 | OPS-SAT time-blocked paired bootstrap | K8 | minutes after X1 | proceed | 2.1 | |
| X3 | **3b Stage 1** — 2² re-selection (F4 × F5), new output dir | K6 | **~30 min CPU** (corrected 2026-11-08: the AR(8) score caches were lost to the `*.npy` ignore rule and must be recomputed first; 4 cells at ~5 min) | **not authorised; superseded** — P1 already delivered the validity check (c0 = A0, c5 = A1 exactly) and found the grid immaterial on both paths | 5 | — |
| X4 | **3b Stage 2** — F1 × F2 × F3 at both F4 levels | K6 | ~1–1.5 h CPU (score regeneration ≈ 6.5 min + ~5 min per cell) | **authorised 2026-11-08; executed in the exactly specified part only** — see `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/` and tracker Phase 5 | 5 | two protocol gaps block the full 2³ (recorded in the output) |
| X5 | Trivial reference predictor + per-arm leaderboard intervals (archives only) | K7 | minutes | proceed | 2.3 | no refit |
| X6 | **am_design** missingness ablation | K7 | Stage 1 free (archives); Stage 2 as specified **BLOCKED** (kumo/tabm absent), substitute learner 2–6 GPU-h | **Stage 1 authorised and executed 2026-11-08** (`outputs/am_design_stage1/`); Stage 2 not authorised | 2.3 / 3 | exploratory, declared |
| X7 | Re-entry variant decomposition (10.6×): A/m source, regime gate, history conditioning | Phase 2.4 | minutes (archived table) | proceed | 2.4 | modelled vs observed kept distinct |
| X8 | Space-weather sensitivity: perturb F10.7/Ap through the physics expert | Phase 2.4 | minutes–hour | proceed | 2.4 | features constant in snapshot |
| X9 | G2 coherent reading extended to the 13,238 twin objects, versioned separately | Phase 2.3 | minutes | proceed | 2.3 | `as_of_2026-10-27` untouched |
| X10 | E6 OPS-SAT branch comparison | K8 | **minutes CPU, no training** (corrected 2026-11-08: the single-branch arms `cnn` and `fcnn` already exist with regenerated per-seed scores, Brier and ECE) | **authorised and executed 2026-11-08** (`outputs/e6_opssat_branch/`) | 5 | decides K8 — see tracker |
| X11 | Missing/corrupted-input robustness for twin modules (predeclared) | Phase 3/6 | hours | **scoped 2026-11-06** — `X11_INPUT_ROBUSTNESS_SCOPE.md`: twin-level and physics/OPS-SAT/vision parts done; learned lifetime and conjunction parts BLOCKED (no persisted models; refit cost stated) | 3, 6 | |
| X15 | G3′ recalibration alternatives for the lifetime intervals (marginal, class-only, asymmetric, recent-window, recency-weighted) from archived tune-B/test predictions | Phase 3 | seconds | pre-declared protocol `PHASE3_RECALIBRATION_PROTOCOL.md`; **done 2026-11-06**, negative/inconclusive | 3 | added 2026-11-06 |
| X12 | Position Kelvins result against N5's reported baselines | Phase 2.5 | needs full text of N5 | open access? check | 2.5 | abstract insufficient |
| X13 | ESA-ADB input-perturbation robustness (noise / dropout on the test half, as done for OPS-SAT) | Phase 2.2 / 6 | minutes–hour CPU | **requested** — would re-score the pre-registered test half; exploratory protocol to be declared first | 2.2, 6 | added 2026-11-06 |
| X14 | SpotGEO difficulty-stratified re-scoring of the archived per-sequence submissions, covariates measured from the released frames | Phase 2.6 | 21 s CPU, no retraining | proceed (archives only) — **done 2026-11-06** | 2.6 | added 2026-11-06 once the per-sequence submissions were found in `outputs/experiments/` |

**Blocked, with the missing dependency named:** Brancato reconciliation (full text, paywalled);
prospective twin validation (SATCAT snapshot ≥ 2026-11-26); C4 (identity-linked telemetry + CDM
corpus; none public); training-level reproducibility of the selected lifetime learners (backends
unavailable); cross-satellite generalisation (one spacecraft per telemetry benchmark).

---

## 6. What this document does not do

It does not write results, abstracts or discussion; does not read paywalled full texts; does not
run any experiment; does not alter any frozen artifact or prior verdict; and does not promote any
candidate beyond what archived evidence supports today. Three records are used at title level and
are marked.
