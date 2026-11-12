# Phase 1 — Structured literature review (ten directive topics)

Assembled 2026-11-06T06:28:06+00:00 by `scripts/literature_review_build.py` from archived retrieval artifacts; nothing was fetched when this file was built. Scope and rules: abstract-level review of records retrieved on 2026-11-06 through the OpenAlex API (verbatim responses in `outputs/literature/phase1/raw/`), each cited record's DOI resolved live against Crossref or DataCite, no paywalled full text read except where an open-access copy is archived (`uriot2021_baselines_arxiv2008.03069.md`). Relevance judgements are the auditor's and are reversible against the archived records. Records without an indexed abstract are marked **title-level**.

## 0. Retrieval record

* Queries: **21** across **8** retrieval topics, all HTTP [200]; **407** results returned, **368** unique records kept (`records.csv`, sha256 `a535de6b2e7b1a7f…`).
* Abstracts indexed for **348** of 368 records; **95** preprints; publication years 2023–2026.
* Records cited below: **21**, every DOI resolved live — crossref 19, datacite 2 (`selected_records_crossref.csv`); **3** of them entered through Crossref directly rather than an OpenAlex query (10.1007/s42064-021-0101-5, 10.1109/access.2021.3136458, 10.1038/s43588-024-00613-8); **4** are title-level (no abstract available to the review).
* Prior review `LITERATURE_REVIEW_2023_2026.md`: **34** records (R1–R34), 32/32 DOIs re-verified live on 2026-11-06 (30 Crossref + 2 DataCite); its coverage is referenced per topic below and not repeated.
* Two further sources read in full because they were open access and load-bearing: Uriot et al. 2021 (arXiv 2008.03069; baselines L = 0.694 LRP, L = 2.5 CRP, 12 of 97 teams beat LRP) and the OPS-SAT-AD benchmark paper (PMC12041257; nine channels = 3 magnetometer + 6 photodiode).

### Retrieval by topic

| Retrieval topic | Queries | Records | With abstract | Years | Open access | Preprints |
|---|---|---|---|---|---|---|
| Satellite conjunction assessment (`conjunction_assessment`) | 3 | 42 | 37 | 2023–2026 | 39 | 16 |
| Satellite digital twins (predictive) (`digital_twin_predictive`) | 3 | 56 | 55 | 2023–2026 | 54 | 3 |
| Telemetry anomaly detection: evaluation and benchmarks (`evaluation_framework`) | 2 | 26 | 26 | 2023–2026 | 26 | 12 |
| Spacecraft health monitoring (subsystem level) (`health_monitoring_subsystem`) | 2 | 34 | 32 | 2023–2026 | 34 | 6 |
| Multimodal satellite data fusion (`multimodal_fusion`) | 3 | 59 | 55 | 2023–2026 | 57 | 8 |
| Evidence provenance and uncertainty-aware decision support (`provenance_decision_support`) | 3 | 59 | 55 | 2023–2026 | 58 | 21 |
| Orbital lifetime and re-entry prediction (`reentry_variants`) | 2 | 37 | 36 | 2023–2026 | 37 | 10 |
| Temporal distribution shift and conformal coverage (`temporal_shift`) | 3 | 55 | 52 | 2023–2026 | 54 | 19 |

### Queries

| Topic | Query | Results |
|---|---|---|
| `digital_twin_predictive` | satellite digital twin health monitoring prediction | 20 |
| `digital_twin_predictive` | spacecraft digital twin anomaly detection telemetry | 20 |
| `digital_twin_predictive` | digital twin space situational awareness orbit | 20 |
| `multimodal_fusion` | multimodal data fusion satellite telemetry imagery | 20 |
| `multimodal_fusion` | space situational awareness sensor fusion machine learning | 20 |
| `multimodal_fusion` | evidence fusion spacecraft health orbital data | 20 |
| `conjunction_assessment` | spacecraft conjunction assessment machine learning collision probability | 20 |
| `conjunction_assessment` | collision avoidance conjunction data message prediction | 20 |
| `conjunction_assessment` | Kelvins collision avoidance challenge CDM | 7 |
| `provenance_decision_support` | data provenance machine learning pipeline reproducibility | 20 |
| `provenance_decision_support` | uncertainty-aware decision support abstention selective prediction | 20 |
| `provenance_decision_support` | evidence provenance digital twin trustworthiness | 20 |
| `temporal_shift` | distribution shift time series anomaly detection evaluation | 20 |
| `temporal_shift` | temporal distribution shift conformal prediction coverage | 20 |
| `temporal_shift` | concept drift spacecraft telemetry | 20 |
| `health_monitoring_subsystem` | satellite power subsystem health monitoring machine learning | 20 |
| `health_monitoring_subsystem` | spacecraft thermal attitude control anomaly detection telemetry | 20 |
| `reentry_variants` | uncontrolled reentry prediction uncertainty atmospheric density | 20 |
| `reentry_variants` | orbital decay prediction ballistic coefficient solar activity | 20 |
| `evaluation_framework` | benchmark evaluation framework satellite monitoring anomaly detection metrics | 20 |
| `evaluation_framework` | event-wise metrics anomaly detection time series evaluation | 20 |

## 1. Cited records — verification and abstract availability

| ID | Year | Title | DOI | Registry | In OpenAlex corpus | Abstract | Cited by (OpenAlex) |
|---|---|---|---|---|---|---|---|
| N5 | 2021 | Spacecraft collision avoidance challenge: Design and results of a machine learning competition | `10.1007/s42064-021-0101-5` | crossref | no (Crossref direct) | Crossref-direct — abstract read at verification, not archived in the corpus |  |
| N19 | 2022 | Digital Twin in Aerospace Industry: A Gentle Introduction | `10.1109/access.2021.3136458` | crossref | no (Crossref direct) | Crossref-direct — abstract read at verification, not archived in the corpus |  |
| N8 | 2023 | Navigating the metric maze: a taxonomy of evaluation metrics for anomaly detection in time series | `10.1007/s10618-023-00988-8` | crossref | yes | indexed | 66 |
| N15 | 2023 | A DT Machine Learning-Based Satellite Orbit Prediction for IoT Applications | `10.1109/iotm.001.2200271` | crossref | yes | indexed | 8 |
| N18 | 2024 | FedFusion: Manifold-Driven Federated Learning for Multi-Satellite and Multi-Modality Fusion | `10.1109/tgrs.2023.3339522` | crossref | yes | indexed | 45 |
| N20 | 2024 | Digital twins in mechanical and aerospace engineering | `10.1038/s43588-024-00613-8` | crossref | no (Crossref direct) | **title-level** |  |
| N9 | 2024 | A new distributional treatment for time series anomaly detection | `10.1007/s00778-023-00832-x` | crossref | yes | **title-level** | 5 |
| N2 | 2024 | Treatment of epistemic uncertainty in conjunction analysis with Dempster-Shafer theory | `10.1016/j.asr.2024.09.014` | crossref | yes | indexed | 9 |
| N16 | 2025 | Uncertainty Quantification Based on Conformal Prediction for Industrial Time Series With Distribution Shift | `10.1109/tii.2025.3529920` | crossref | yes | indexed | 17 |
| N13 | 2025 | Toward Explainable AI in Spacecraft Health Monitoring: Comparative Benchmarking of Anomaly Detection Models and Open-Source Datasets | `10.1109/access.2025.3639551` | crossref | yes | indexed | 7 |
| N11 | 2025 | Uncontrolled reentry of Low Earth Orbit Decaying Objects: a hidden threat to global safety and legal frameworks | `10.1038/s44453-025-00007-8` | crossref | yes | indexed | 1 |
| N12 | 2025 | Synthetic satellite telemetry data for machine learning | `10.1007/s12567-024-00589-1` | crossref | yes | indexed | 4 |
| N10 | 2025 | Tracking reentries of Starlink satellites during the rising phase of solar cycle 25 | `10.3389/fspas.2025.1572313` | crossref | yes | indexed | 26 |
| N6 | 2025 | Capturing end-to-end provenance for machine learning pipelines | `10.1016/j.is.2024.102495` | crossref | yes | indexed | 37 |
| N3 | 2025 | CAMmary: A review of spacecraft collision avoidance manoeuvre design methods | `10.1016/j.actaastro.2025.07.027` | crossref | yes | indexed | 18 |
| N7 | 2026 | Conformal selective prediction with cost aware deferral for safe clinical triage under distribution shift | `10.1038/s41598-026-40637-w` | crossref | yes | indexed | 15 |
| N21 | 2026 | Toward Deployable Satellite Anomaly Detection: A Benchmark Study on Large-Scale ESA-ADB Telemetry | `10.48550/arxiv.2607.07335` | datacite | yes | indexed | 1 |
| N17 | 2026 | A Multi-Modal Decision-Level Fusion Framework for Hypervelocity Impact Damage Classification in Spacecraft | `10.3390/s26030969` | crossref | yes | indexed | 1 |
| N1 | 2026 | Deep learning for full-horizon uncertainty-aware prediction of CDM sequences in spacecraft collision avoidance | `10.1016/j.actaastro.2026.08.013` | crossref | yes | **title-level** | 0 |
| N4 | 2026 | Early Prediction of Satellite Collision Probability Using a Hybrid TCN-Transformer Model for a CDM-Based Conjunction Analysis Framework | `10.48550/arxiv.2609.13191` | datacite | yes | indexed | 0 |
| N14 | 2027 | Integrated structural-thermal design and digital twin framework for satellite payload module | `10.1016/j.ast.2026.113753` | crossref | yes | **title-level** | 0 |

## 2. Review by directive topic

The ten subsections below are the auditor's review, reproduced verbatim from `PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md` §1 (written from the archived abstracts on 2026-11-06). Each table gives methodology / data / evaluation and the limitation for this project's purpose; † marks title-level records. One update is appended to §2.7 below, because the body text of N5 has since been read.

Fields per record: ID · first author(s), year · venue · DOI · methodology · data · evaluation ·
limitation (as stated or evident from the abstract). Abstracts are in `records.csv`.

### 2.1 Satellite digital twins

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

### 2.2 Spacecraft health monitoring

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

### 2.3 Telemetry anomaly detection (ESA-ADB and competitors)

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

### 2.4 Multimodal satellite data fusion

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

### 2.5 Orbital lifetime and re-entry prediction

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

### 2.6 Space debris monitoring

Prior coverage: R27–R31 (radar/optical detection, light curves, STACK-CNN, constellation
observation, DebrisWatch II). Unchanged: SpotGEO reimplementation is infrastructure, not a
contribution (withdrawn C-10).

### 2.7 Satellite conjunction assessment

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

### 2.8 Conformal prediction and uncertainty calibration

Prior coverage: R20–R26 (task-aware conformal envelopes for spacecraft; horizon-aware group
conditional CP with cluster bootstrap; beyond exchangeability; online multi-step CP; fixed-horizon
right-censoring evaluation; isotonic distributional regression; PINN review).

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N16 | Zhang & Zhou, 2025 · IEEE TII · `10.1109/tii.2025.3529920` | Conformal UQ for industrial time series under temporal dependence and drift; interval from two online components | Industrial process data; confirms the exchangeability failure mode we report |

**What this establishes.** Reinforces Phase I verdict **B — already done**: coverage failure under
drift is a theorem (R22), an audited protocol (R21) and a solved engineering problem (online CP).
We measure it; we do not discover it.

### 2.9 Temporal distribution shift

Prior coverage: R22, R23; Mou et al. MORA (preprint, `NOVELTY_NOTE`).

| ID | Record | Methodology / data / evaluation | Limitation for our purpose |
|---|---|---|---|
| N9 | Ting, Liu, Gong, Zhang, Zhu, 2024 · The VLDB Journal · `10.1007/s00778-023-00832-x` | A new distributional treatment for time-series anomaly detection (title-level) | † |
| N7 | Kwon & Kim, 2026 · Scientific Reports · `10.1038/s41598-026-40637-w` | Conformal selective prediction with cost-aware deferral under distribution shift (clinical triage); finite-sample coverage sets, defer when expected cost falls | Clinical; but it is exactly abstention + conformal + shift, generically |

**What this establishes.** Selection non-transfer across temporal origins is established as a
phenomenon in forecasting and domain generalisation (Phase I verdict C); our contribution is the
**first measurement of it in orbital lifetime prediction** (C-2), which survives. Abstention under
shift is generically occupied (N7, R19) — Phase I verdict D stands.

### 2.10 Evidence provenance and uncertainty-aware decision support

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

**Update to 2.7 (2026-11-06, after the OA full text was read).** N5's body reports the organisers' baselines on the complete test set: the Latest Risk Prediction (clipped naive) baseline scores L = 0.694 and only 12 of 97 teams beat it; many failed to beat its F2; the Constant Risk Prediction baseline scores L = 2.5. The project's archived `latest_risk_point` row reproduces the LRP baseline to three decimals (L_clip = 0.693961), so the Phase 2.5 negative result is the benchmark's expected outcome, not an implementation artefact (`outputs/literature/phase1/uriot2021_baselines_arxiv2008.03069.md`; tracker row 2.5 / X12).

## 3. What the review does not do

It does not read paywalled full texts (Brancato et al. 2026 remains abstract-only); it does not rank venues or weigh citation counts as evidence of quality; it does not claim completeness beyond the 21 queries logged above; and it makes no novelty claim itself — those are argued, record by record, in `PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md` §§2–4.

## 4. Provenance

* `outputs/literature/phase1/query_log.json` — sha256 `5ab03f73a131261540c83550f98f1c03cbc856e787ba311b391ae3c2d1e1eb2f`
* `outputs/literature/phase1/records.csv` — sha256 `a535de6b2e7b1a7f32b8f6b29039c6f8c73b27467fa9088577124db12e6c12f4`
* `outputs/literature/phase1/selected_records_crossref.csv` — sha256 `7c9f6658f9f008e109263f35db8ffc89d7ec53c8461ec546a706e91d836c3ff0`
* `docs/research/PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md` — sha256 `b9db4853c4c6462e3b90252101b894cbbfd1e5c0f6e53347220b823373b3d316`
* `outputs/literature/phase1/uriot2021_baselines_arxiv2008.03069.md` — sha256 `7686cc1826e1c7f4196c015641538b063ad22bd61d6bcbea237feb1159a7c525`
* `outputs/literature/phase1/opssat_channels_PMC12041257.md` — sha256 `28e0fa5e5bd9eda576137f49558b2bcb86995454310af9a92cc5c4af2542f10e`
