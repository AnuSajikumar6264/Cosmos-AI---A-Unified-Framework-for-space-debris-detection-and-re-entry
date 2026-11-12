# COSMOS-AI complete project audit

Date 2026-11-04 · revision `78ee339` · repository `AnuSajikumar6264/Cosmos-AI-`
Local: `/data2/anupa/Final_Year_Project`

**Deliverable 1 of 12. Parts 2–10 are not attempted here**, per your staged-execution
instruction. §8 records what remains.

**Status: this audit supersedes my earlier JIRS-focused audit, which was materially incomplete.**
Five of its conclusions are corrected below, and one of my own hypotheses is refuted by evidence
the project had already produced.

---

## 1. What was inspected in this pass

Verified by direct inspection of code, artifacts and logs — not from README text or prior
summaries.

| # | Artifact | Finding |
|---|---|---|
| 1 | Project code scale | 107 `.py` / 24,493 LOC in `cosmos`; 45 / 8,926 in `scripts`; 17 / 4,225 in `tests`. (The 5,406-file count includes 4,563 `.venv` and 650 `data`) |
| 2 | **Current test status** | **217 passed, 0 failed, 42.76 s — verified now, not quoted** |
| 3 | `outputs/phase_h/coverage_table.csv` | **All four of your coverage figures confirmed exactly**; see §4 |
| 4 | **`outputs/benchmarks/reentry_lifetime/leak_check.json`** | **A leakage analysis I had never seen** — see §3, the most important finding in this audit |
| 5 | `cosmos/ai/lifetime/leak_check.py` | The generating code; computes cluster-robust adjusted odds ratios |
| 6 | `cosmos/ai/lifetime/catalogue.py` | Line 17 explicitly flags `rcs_m2` as **not an input known at `t0`** |
| 7 | `docs/RESULTS_AND_ANALYSIS.md` §273–281 | The project's own documented conclusion on that covariate |
| 8 | `outputs/benchmarks/telemetry_esa_adb/results.csv` **in full** | 128 rows, 56 tags, **2 missions × 2 channel scales** — my earlier reading covered one mission at one scale |
| 9 | `thesis/audit/STAGE1_AUDIT.md` §1–2 | The pre-registered ESA-ADB hypothesis table with Holm-corrected outcomes |
| 10 | `thesis/build/Q1_Readiness_and_Roadmap.md` | A prior Q1 assessment with 9 evidence gaps and a 7-item plan |
| 11 | `thesis/evidence/evidence.json` | 16,189 keys (4,576 measured / 11,502 derived / 64 config / 47 literature) |
| 12 | `thesis/evidence/reference_verification_log.tsv` | 68 references, 64 verified with DOI/arXiv and source |
| 13 | `research_design/VENUES.md` | Prior venue analysis — **JIRS is absent from it** |
| 14 | `outputs/benchmarks/reentry_landmark/results.json` | Explicit 5-check `leakage_report`, all passing |
| 15 | `outputs/benchmarks/reentry_surrogate/results.json` | Simulation-surrogate metrics incl. an OOD test |
| 16 | `outputs/benchmarks/telemetry_smap_msl/summary.csv` | **77 columns, including `median_delay_steps`** — detection delay *is* measured |
| 17 | `paper/` tree + 4 supersession records | Four superseded manuscript tracks, each properly marked |
| 18 | `configs/` | 6 study configs separating protocol from code |

## 2. Component classification

Using your seven categories. **Implementation and integration are not validation.**

| Component | Classification | Evidence |
|---|---|---|
| **Telemetry anomaly detection — ESA-ADB** | **Implemented and experimentally validated** | Pre-registered, hash-frozen, official metric code, official splits, full channel scale (58/47 channels), 2 missions, paired block bootstrap (86/22 blocks), hierarchical over seeds, B = 2,000, Holm correction, minimum effect +0.05. H6 supported (+0.353 [+0.206, +0.488], Holm p = 0.0015); H4, H5 refuted |
| **Telemetry anomaly detection — OPS-SAT** | **Implemented but insufficiently validated** | 11 arms, 5 seeds, official + time-blocked protocols, label-efficiency sweep, calibration and compute metrics. But significance tests exist **only for the official protocol**, and the score archive `test_scores_official.npz` is **absent from disk**, so the published comparison is not re-derivable |
| **Telemetry — SMAP/MSL** | **Implemented and experimentally validated** | 77-column summary incl. event precision/recall/F1, ESA event-wise metrics, `median_delay_steps`, three robustness protocols (`shift`, `block`, `swap`) each with p-values, point-adjusted vs event F1, saturation diagnostics |
| **Orbital lifetime prediction** | **Implemented and experimentally validated (negative)** | Three temporal origins, 17 arms, verified split disjointness, cluster bootstrap, exact prediction-level reproduction (0.000e+00), selection regret significant at origin 2016 |
| **Orbital decay / re-entry — landmark** | **Implemented and experimentally validated** | τ = 2026-08-16, follow-up 2026-10-23, splits 18,914/8,873/6,371, events 140/57/38, **explicit 5-check leakage report all passing**, physics c-index 0.976. Limited by 38 test events |
| **Re-entry footprint surrogate** | **Implemented but insufficiently validated** | n = 40,000 test + 20,000 OOD; impact classification 0.995; median position error 16.2 km, p95 69.4 km; 80,107 samples/s. **Validated against the simulator, never against a recorded re-entry.** `error_vs_std` Spearman only **0.303** — the uncertainty estimate is weakly informative |
| **Debris detection — SpotGEO** | **Implemented and experimentally validated (negative)** | Official challenge metric; test F1 **0.084** |
| **Debris detection — synthetic** | **Scientifically unsupported by current evidence** | mAP@50 0.780 on **self-generated data only**; not external validation |
| **Collision / conjunction risk** | **Implemented and experimentally validated (negative)** | Kelvins CAC, 2,167 events; trivial `latest_risk_point` **F2 0.739** vs best learned arm **0.168**; six of eleven arms at exactly 0.000 |
| **Multimodal evidence fusion** | **Blocked / scientifically unsupported** | C1 not reproducible under the same-learner test; C2's deployed arm not significant (p = 0.364); C3 inconclusive; **C4 unevaluable — 0 joinable pairs** |
| **Satellite health monitoring (`cosmos/health`)** | **Partially implemented** | 1,132 LOC; `cosmos_monitor` benchmarked on ESA-ADB where it ties a trivial rule on one mission and is far worse on another |
| **Uncertainty quantification** | **Implemented but insufficiently validated** | Mondrian split-CQR with documented fallback; coverage measured and **significantly deviating in 3 of 4 cells**; no distribution-free guarantee available (§4) |
| **Mission Intelligence Console** | **Implemented but insufficiently validated** | 2,167 LOC; versioned runs, evidence tracking, abstention, explicit "no data" rendering. **No outcome-scored evaluation of any kind** |
| **Decision support / prioritisation** | **Scientifically unsupported by current evidence** | `priority_score` deliberately unset in the collision adapter (`adapters.py:358`); dashboard states it "is deliberately empty" (`dashboard.py:247`). **No decision-quality metric, regret measure, utility model or operator study exists** |
| **Integrated digital twin** | **Designed but not validated** | Registered 2026-10-27 forecast is hash-verified and **unscored** until ≥ 2026-11-26; integration premise refuted by the project's own Phase E/E12 |
| **Orchestration, typed contracts, abstention** | **Implemented and validated as software** | 217 tests pass; typed contracts; genuine abstention. Engineering quality, not a scientific result |

## 3. CRITICAL FINDING — an outcome-associated, non-stationary covariate, already diagnosed by the project

This is the most important thing in this audit, and the project found it first.

`cosmos/ai/lifetime/leak_check.py` computes, per origin and split, the association between
**radar-cross-section missingness** and 30-day decay, with cluster-robust standard errors by
launch family.

| Split | share RCS missing | P(decay30 \| missing) | P(decay30 \| present) | Adjusted OR [95 % CI] |
|---|---|---|---|---|
| o2016 train | 0.271 | **0.759** | 0.172 | **3.594 [2.094, 6.169]** |
| o2016 tuneB | 0.017 | 0.889 | 0.055 | — |
| **o2016 test** | **0.682** | **0.134** | 0.041 | — |
| o2011 train | 0.324 | **0.764** | 0.191 | **3.625 [2.076, 6.327]** |
| o2011 tuneB | 0.099 | 0.576 | 0.171 | — |
| **o2011 test** | **0.019** | 0.840 | 0.065 | — |

A parallel check on **design area-to-mass** missingness gives OR 3.437 [2.638, 4.477] (2016) and
3.594 [2.766, 4.670] (2011).

**Three facts combine into a serious construct-validity problem:**

1. **Missingness is strongly outcome-associated** — adjusted OR ≈ 3.6, cluster-robust, CI
   excluding 1 at both origins.
2. **The missingness rate is wildly non-stationary across splits** — 27 % → 1.7 % → **68 %** at
   origin 2016, and 32 % → 9.9 % → **1.9 %** at origin 2011.
3. **`rcs_m2` is not an input knowable at `t0`.** The code says so itself
   (`catalogue.py:17`): whether a value was ever published is a property of the *catalogue
   publication process*, not of the object at entry time. `share_rcs_missing_t0_from_2018 = 0.9995`
   at o2016 test — objects entering from 2018 essentially never have published RCS yet.

So a model can learn "no published RCS ⇒ likely to decay soon", which is partly a statement about
*how recently the object was catalogued* rather than about orbital dynamics.

**What the project found, which refutes a hypothesis I had formed.** On seeing this I hypothesised
that RCS-missingness explains the selection-transfer failure (ρ = 0.000) and the physics
baseline's 1st-to-17th rank swing. **The project had already tested it and the answer is no.**
`docs/RESULTS_AND_ANALYSIS.md` §278–280 records an ablation:

> "The association between availability and outcome is clear, and **using the covariate breaks
> calibration when that association changes. Its effect on point accuracy was not detectable
> here.**"

With the covariate, 90 % coverage at origin 2016 falls from 87.7 % to 76.8 % (and from 89.2 % to
72.1 % with the first learner set). Point accuracy — which drives the pinball ranking — showed no
detectable effect.

**Therefore:**
- My RCS hypothesis for the *ranking* instability is **not supported**. I withdraw it.
- But this is a **mechanistically explained cause of the calibration failure** in §4, with an
  ablation behind it. That is stronger evidence than the "temporal distribution shift" framing I
  previously proposed, because it identifies a mechanism and tests it.

**Reviewer exposure:** a reviewer who finds `leak_check.json` will ask whether an input unknowable
at `t0` should have been in the feature set at all. The project's answer — that it was measured,
ablated, and its harm localised to calibration — is defensible, but it **must be in the
manuscript**. It currently is not.

## 4. Uncertainty and calibration audit (Part 3D)

**Your table is confirmed exactly** from `outputs/phase_h/coverage_table.csv`:

| Origin | Nominal | Observed | Deviation | 95 % CI | p | Artifact verdict | Mean width (log₁₀ days) |
|---|---|---|---|---|---|---|---|
| 2016 | 80 % | **0.71692** | −0.0831 | [−0.1777, −0.0023] | **0.0415** | **UNDER-COVERS** | **0.433** |
| 2016 | 90 % | **0.87408** | −0.0259 | [−0.0991, +0.0251] | 0.4095 | CONSISTENT WITH NOMINAL | 0.671 |
| 2011 | 80 % | **0.92313** | +0.1231 | [+0.0829, +0.1478] | **0.0** | **OVER-COVERS** | **0.877** |
| 2011 | 90 % | **0.95913** | +0.0591 | [+0.0336, +0.0740] | **0.0** | **OVER-COVERS** | 1.214 |

**Your characterisation "three of four cells significantly deviated" is correct.** The exception is
2016/90 % (p = 0.4095).

**Two things your table does not show, which strengthen the finding:**

1. **The direction of miscalibration reverses between origins** — over-covering at 2011,
   under-covering at 2016. Not a uniform bias; a sign flip.
2. **Interval width halves** between origins at the 80 % level (0.877 → 0.433). The model became
   *more confident* at the origin where it was *less* correct. That is the operationally dangerous
   failure mode, and it is the clearest single statement available about whether these uncertainty
   estimates are usable.

Per-arm context: at 2016/80 % `physics_only` (0.738) and `tabm` (0.728) are **consistent with
nominal**, while `cosmos_gated` significantly under-covers — so this is a property of the deployed
fusion, not of the task.

**On distribution-free guarantees — none is available.** Split-conformal coverage requires
exchangeability between calibration and test. The test folds are forward in time from
calibration, so exchangeability fails by construction, and the table confirms it fails in
practice. **No distribution-free or finite-sample coverage guarantee may be claimed.**

## 5. Corrections to my earlier audit

| # | Earlier claim | Correction |
|---|---|---|
| 1 | "Architecture diagram MISSING" | **WRONG.** Six graphviz diagrams exist in `thesis/figures/` (`diag_overall`, `diag_ai_layer`, `diag_alarm_layer`, `diag_pipeline_flow`, `diag_esa_protocol`, `diag_event_tcn`) with `.dot` sources and generators |
| 2 | ESA-ADB: "`cosmos_monitor` ties a trivial rule; PatchTST 2.5× better" | **INCOMPLETE.** Drawn from one mission at one scale. At full channel scale on M1 **all arms collapse** (best PatchTST 0.0901). On M2 the **trivial `out_of_limits` rule beats every learned arm** (0.9648 lightweight, 0.8936 full). Seed SDs reach ±0.42 |
| 3 | "2023–2026 anomaly-detection literature outstanding (rate-limited)" | **PARTLY WRONG.** The repo holds verified AD literature: Liu 2024 (TSB benchmark critique), Sehili 2023 (flawed evaluation), Malhotra 2016 (LSTM-AE), García 2022 (DC-VAE), Paparrizos 2022 (TSB-UAD), Wenig 2022 (TimeEval), Schmidl 2022, Huet 2022, Ruff 2021, Pang 2022 |
| 4 | "Detection delay is not appropriate / not measured" | **PARTLY WRONG.** `median_delay_steps` **is** computed for SMAP/MSL. It remains inapplicable to whole-fragment OPS-SAT classification, but the capability exists |
| 5 | OPS-SAT ranked as the strongest validated positive | **NEEDS REVISION.** The pre-registered ESA-ADB study is more rigorous and was not in scope of that assessment |
| 6 | C-1 "intersection is unoccupied" | **IN DOUBT.** **Shorten et al. (2023), "Wide-Scale Monitoring of Satellite Lifetimes: Pitfalls and a Benchmark Dataset", J. Spacecraft & Rockets 60(6):2003–2007, `10.2514/1.a35642`** — verified in the repo's own bibliography, **cited nowhere in the manuscript** |

Also uncited and verified in-repo: **Candès, Lei & Ren (2023), "Conformalized survival analysis",
JRSS-B 85(1):24–45, `10.1093/jrsssb/qkac004`** and **Gui et al. (2024), Biometrika 111(2),
`10.1093/biomet/asad076`** — direct methodological prior art for conformal prediction on censored
lifetimes.

## 6. Reproducibility status (Part 3E, partial)

| Level | Status |
|---|---|
| **Test suite** | **217 passed, 0 failed — verified now** |
| Prediction-level, lifetime | **COMPLETE** — recomputes to 0.000e+00 |
| Training-level, telemetry (OPS-SAT) | **Available** — needs only `torch` + `xgboost`, both installed |
| Training-level, lifetime | **ABSENT** — 5 of 7 backends undeclared; **1 of 7** matches the only recorded environment (`torch 2.13.0+xpu` in the freeze vs `2.14.0+xpu` now); `kumo` requires a **commercial vendor library**; no environment recorded per run; `provenance.py` exists and is **never called** |
| OPS-SAT score archive | **MISSING** (`test_scores_official.npz`) — a published significance test is not re-derivable |
| **Evidence provenance (thesis)** | **Strong and previously unknown to me** — 16,189 keys with kind/source/derivation; `render.py` **aborts** if a placeholder lacks evidence |
| Integrity | Pre-registration freeze (28 files) intact; G5d hash intact; dated-forecast digest intact |
| **Public artifact** | **NONE** — no DOI, deposit, release or licence |

## 7. Prior work I had not accounted for

- **Four superseded manuscript tracks**, each correctly marked with the specific withdrawn claims
  it asserts: `journal_v3_twin` (digital twin, 19 figures), `journal_eaai` (integrated framework,
  16 sections, full build), `journal_v2`, and a LaTeX-only draft.
- **A complete thesis** (13 chapters, built to DOCX/PDF) with its own staged audit, claim–evidence
  matrix, revision plan and changelog.
- **A prior Q1 readiness assessment** (`Q1_Readiness_and_Roadmap.md`) listing 9 unresolved
  evidence gaps and a 7-item action plan, whose own verdict is: *"the telemetry study is
  publishable as a careful empirical paper. Acceptance by a Q1 venue is plausible but not
  assured."*
- **A prior venue analysis** (`research_design/VENUES.md`) recommending **Engineering Applications
  of Artificial Intelligence** first, then Acta Astronautica, then Aerospace Science and
  Technology. **JIRS does not appear on it.**

## 8. Pending — this audit is not complete

| Artifact | Why it matters | Priority |
|---|---|---|
| `thesis/audit/STAGE1_AUDIT.md` §3–§12 | Test-half exposure timeline, code audit, the H6 five-way confound, novelty risks, readiness verdict | **High** |
| `thesis/audit/CLAIM_EVIDENCE_MATRIX.md` | Prior claim→evidence mapping | **High** |
| `research_design/NOVELTY_NOTE.md` | Prior novelty analysis vs TC-CAD, Brancato, Heydari | **High** |
| ESA-ADB pre-registration artifacts | Confirms the study's frozen status independently | **High** |
| `thesis/evidence/original_pipeline_runs.json` | Reproducibility evidence | **High** |
| `thesis/src/` 13 chapters | The thesis's scientific content | Medium |
| `docs/architecture/` 6 files | Architecture and dataflow docs | Medium |
| `outputs/pipeline/` 309 files | End-to-end run records | Medium |
| `cosmos/{health,debris,reentry,vision,twin,survival,conjunction}` source | Module-level correctness | Medium |
| `notebooks/` 2 notebooks, 3.1 MB | May hold analyses not represented elsewhere | Low |

**Estimated completeness: ~75 %.**

## 9. Unresolved questions requiring your input

1. **Shorten et al. (2023) overlap with the lifetime benchmark.** Needs the full text (5-page AIAA
   Technical Note). **This blocks any novelty claim for Track 2.**
2. **Has the thesis been submitted, deposited or examined?** Determines the prior-publication
   disclosure Springer requires. Only you can answer.
3. **Three references the thesis flags as required but unread:** Brancato et al. (AST 2027) — whose
   Mission 1 figure *"cannot be reconciled with this study without their full text and code"* —
   Fejjari et al. (Acta Astronautica), Dai et al. (Advances in Space Research).
4. **Was the RCS covariate retained in the published runs, or removed after the ablation?** The
   docs show the ablation; I have not yet confirmed which configuration produced the headline
   leaderboards.
5. **Off-repository build dependencies** under `/data/anupa/COSMOS_work/.tools*` — note `/data/`,
   not `/data2/`. Reproducibility implication unassessed.

## 10. Early signal on the three tracks — not yet a recommendation

Recorded because it emerged from this pass, and subject to Part 4's proper evaluation.

| Track | Current evidence strength | Note |
|---|---|---|
| **Track 1 — health monitoring** | **Strongest** | Contains two studies. The **ESA-ADB pre-registered study** has the best methodology in the project (hash-frozen, official metric, Holm, block bootstrap, two missions). Its own audit warns H6's gain is **confounded with four other protocol differences**, specific to Mission 1 at full scale, and **reversed on Mission 2** |
| **Track 2 — lifetime + uncertainty** | Moderate, mostly negative | Rigorous negatives, significant selection regret, exact prediction reproducibility, and a mechanistically explained calibration failure (§3–§4). **Novelty in doubt pending Shorten et al.** |
| **Track 3 — integrated digital twin** | **Weakest** | Integration premise refuted by the project's own experiments; decision layer unvalidated; twin forecast unscored. **Not currently defensible** |

**I am not yet recommending a track.** Part 4 requires the pending high-priority inspections in §8
and an answer on Shorten et al.

---

**Nothing was committed, pushed, released or modified. No experiment was started. All inspection
was read-only. No frozen artifact or pre-registration was touched.**
