# Stage 1 — Complete project audit

Date 2026-11-04 · revision `78ee339`

**STATUS: PARTIAL. Approximately 60 % of the planned inspection is complete.** §6 lists what
remains. I am not presenting this as a finished audit.

**Headline: Stage 1 found substantial prior work I had not inspected, and it materially corrects
four conclusions in my earlier JIRS audit — including one that may undermine a novelty claim.**

---

## 1. Files and artifacts inspected in this stage

| # | Artifact | Method | Result |
|---|---|---|---|
| 1 | Repository scale | `find` / `wc` | 107 project `.py` files / 24,493 LOC in `cosmos`; 45 / 8,926 in `scripts`; 17 / 4,225 in `tests`. 348 markdown files / 58,302 lines. The 5,406-file figure is 4,563 `.venv` + 650 `data` |
| 2 | Top-level tree | `ls` | 11 directories, including **`thesis/`** and **`notebooks/`**, neither previously inspected |
| 3 | `cosmos/` per-module LOC | `find`/`wc` | telemetry 5,806; lifetime 2,487; product 2,167; reentry 1,715; debris 1,567; vision 1,274; twin 1,057; health 1,132; data 1,749; conjunction 455; survival 396 |
| 4 | `configs/` | `find` | 6 study configs: `telemetry/{esa_adb,opssat}`, `vision/{spotgeo,cosmos_synthetic}`, `reentry/{landmark,surrogate}` |
| 5 | **`paper/` full tree** | `find` | **Four manuscript tracks, not one** — see §2.1 |
| 6 | `paper/SUPERSEDED.md` + 3 per-directory markers | full read | Supersession properly documented; reasons recorded; 85 broken figure references noted |
| 7 | **`thesis/README.md`** | full read | A complete thesis with its own build, evidence and audit system — see §2.2 |
| 8 | `thesis/` subtree listing | `ls` | `src` 13 chapters, `audit` 4 docs, `evidence` 5 files, `figures` 38 files, `tools` 9 scripts, `build` 6 outputs |
| 9 | **`thesis/evidence/evidence.json`** | programmatic | **16,189 keys**: 4,576 measured, 11,502 derived, 64 config, 47 literature — each with source, kind and derivation |
| 10 | **`thesis/evidence/reference_verification_log.tsv`** | full read | **68 references, 64 verified**, 3 not found, 1 verified-as-LNCS |
| 11 | `thesis/refs.bib` (targeted) | `awk` extraction | Full entries for three previously unseen references — see §3.1 |
| 12 | **`thesis/build/Q1_Readiness_and_Roadmap.md`** | full read | **A prior Q1 readiness assessment with contribution statement, 9 evidence gaps, reviewer assessment and 7-item action plan** — see §2.3 |
| 13 | `thesis/figures/` diagram inventory | `ls` | **6 architecture diagrams** (`diag_overall`, `diag_ai_layer`, `diag_alarm_layer`, `diag_pipeline_flow`, `diag_esa_protocol`, `diag_event_tcn`) in `.dot`/`.png`/`.svg` |
| 14 | **`outputs/benchmarks/telemetry_esa_adb/results.csv` in full** | programmatic | **128 rows, 56 tags, 2 missions, 2 channel scales** — my earlier reading covered only one mission at one scale. See §3.2 |
| 15 | `paper/journal/manuscript.md` citation coverage | `grep` | Confirms three key references are **uncited** — §3.1 |
| 16 | `notebooks/` | `ls` | Two notebooks, 1.8 MB and 1.3 MB — **not yet opened** |

## 2. Evidence discovered

### 2.1 Four manuscript tracks exist, not one

| Track | Framing | Status | Scale |
|---|---|---|---|
| `paper/journal/` | Orbital lifetime benchmark | **CURRENT** | 17 sections, 7 tables, 6 figures |
| `paper/journal_v3_twin/` | **Satellite digital twin** | SUPERSEDED — withdrawn contribution (15 occurrences) | **19 main + 3 supplementary figures**, 3-part source, `numbers.json`, submission checklist, `VENUES.md` |
| `paper/journal_eaai/` | **Integrated cross-domain framework** (Engineering Applications of AI) | SUPERSEDED — withdrawn (10 digital-twin occurrences) | 16 source sections, 13 generated tables, 7 figures, full LaTeX/PDF/DOCX build |
| `paper/journal_v2/` | Predates the contribution lock | SUPERSEDED | 3 main + 3 supp figures, graphical abstract, checklist |
| `paper/manuscript.tex` + `paper/tables/` | A fifth, LaTeX-only draft (ablations, arms, baselines, confirmatory tables) | SUPERSEDED | — |

The supersession is **correctly documented**: each directory carries a marker, the reasons are
specific and tied to withdrawn claims, and `paper/SUPERSEDED.md` records the hazard explicitly —
`journal_v3_twin` and `journal_eaai` assert claims the locked claim set forbids. This is good
practice and I record it as satisfactory.

**But the tooling in those directories is not superseded.** `journal_v3_twin/tools/make_architecture.py`,
`make_figures.py`, `build_numbers.py`, and `journal_v2/figures/protocol_timeline.png` are reusable
assets.

### 2.2 A complete thesis exists, with infrastructure stronger than what I built

`thesis/` contains a built thesis (`COSMOS_Thesis.docx`/`.pdf`/`.md`, 3,605 rendered lines from 13
chapter sources) with:

- **An evidence-provenance system of 16,189 keys.** Chapter sources contain numbers only as
  `{{evidence.key}}` placeholders; `thesis/tools/render.py` **aborts if any placeholder lacks
  evidence**. Each key records `kind` (measured / derived / config / literature), `source` and a
  derivation note. This is a stronger anti-fabrication mechanism than the audit harness I wrote.
- **A reference verification log** (`reference_verification_log.tsv`): 68 references with DOI or
  arXiv ID, the source used for verification, and status.
- **`original_pipeline_runs.json`** — "original-pipeline results regenerated with the current
  code". A reproducibility artifact I was unaware of when I wrote the reproducibility audit.
- **Its own staged audit**: `thesis/audit/STAGE1_AUDIT.md` (267 lines), `CLAIM_EVIDENCE_MATRIX.md`,
  `REVISION_PLAN.md`, `CHANGELOG.md`.
- Six graphviz architecture diagrams.

### 2.3 A prior Q1 readiness assessment exists — and its contribution is not the one I assessed

`thesis/build/Q1_Readiness_and_Roadmap.md` (Appendix D) states a contribution I had **not seen**:

> A pre-registered study comparing unsupervised, tree-based and deep supervised event scorers on
> **ESA-ADB under its official protocol at full channel scale**, with the alarm layer selected on
> all training labels.

Its reported outcomes:

- the whole-training-half selection protocol is **supported on Mission 1**, under both alarm layers;
- the deep supervised scorer shows **no benefit** over simpler scorers;
- **the selection effect is conditional — it reverses on Mission 2 under BH and on the lightweight
  Mission 1 subset**;
- **event aggregation with a strict, metric-selected operating point succeeds where point-level
  adaptive calibration fails, for a mechanical reason**;
- an exploratory diagnostic shows supervised scores shift between training and test, **but the
  shift does not track test performance**.

Its own methodological self-assessment: *"official metric code, a reproduced baseline, frozen
hashes, gated test scoring, hierarchical bootstrap and Holm correction"* — and its verdict:
*"the telemetry study is publishable as a careful empirical paper. Acceptance by a Q1 venue is
plausible but not assured."*

It also records **9 unresolved evidence gaps** and a **7-item action plan**, including "Leave the
physics chain and supporting studies out of the paper" and "Archive the code and score arrays on
Zenodo with a DOI".

## 3. Findings — including corrections to my own earlier audit

### 3.1 CRITICAL — Potential direct prior art for the lifetime-benchmark contribution, uncited

**Shorten, D. P., Yang, Y., Maclean, J. & Roughan, M. (2023). "Wide-Scale Monitoring of Satellite
Lifetimes: Pitfalls and a Benchmark Dataset." *Journal of Spacecraft and Rockets* 60(6):2003–2007.
`10.2514/1.a35642`** — verified via doi.org on 2026-10-25, present in this repository's own
verified bibliography, and **cited nowhere in the current manuscript** (`grep "Shorten"` → 0).

Title-level overlap with contribution C-1 is substantial: wide-scale satellite **lifetime**
monitoring, a **benchmark dataset**, and **pitfalls** — i.e. an evaluation-critique component. My
Phase I/O literature review concluded for C-1 that *"the intersection is unoccupied; C-1 is
defensible as an artifact"* and found no comparable benchmark. **That conclusion was reached
without this reference, which was in the repository the whole time.**

I cannot determine the degree of overlap from the bibliographic entry alone — it is a five-page
AIAA Technical Note and I do not have its text. **This is the single most important unresolved
question in Stage 1** and is carried to §5.

Two further uncited methodological references, both verified in-repo:

- **Candès, E., Lei, L. & Ren, Z. (2023). "Conformalized survival analysis." *JRSS-B*
  85(1):24–45. `10.1093/jrsssb/qkac004`**
- **Gui, Y., Hore, R., Ren, Z. & Barber, R. F. (2024). "Conformalized survival analysis with
  adaptive cut-offs." *Biometrika* 111(2):459–477. `10.1093/biomet/asad076`**

These are direct methodological prior art for applying conformal prediction to censored
lifetime data — precisely what the project does. The manuscript cites Candès six times, but for
*other* papers (Barber et al. exchangeability, Gibbs & Candès, Romano et al., Tibshirani et al.);
**conformalized survival analysis is not among them.** The project's conformal treatment is not
claimed as novel, so this is less damaging than Shorten et al., but both must be cited.

### 3.2 MAJOR — My earlier ESA-ADB reporting was drawn from one mission at one channel scale

The result file holds **128 rows across 56 tags, 2 missions and 2 channel scales**. I previously
reported only `m1_lightweight` rows. The fuller picture inverts part of my conclusion.

Official EW-F0.5 (`anomaly_and_rare`), mean over available seeds:

| Arm | m1_lightweight | **m1_target (full)** | m2_lightweight | **m2_target (full)** |
|---|---|---|---|---|
| `out_of_limits` (trivial rule) | 0.2019 | 0.0007 | **0.9648** | **0.8936** |
| `cosmos_monitor` (ours) | 0.2021 | 0.0038 | 0.7881 | 0.0471 |
| `ar8` | 0.4025 ± 0.0083 | 0.0768 ± 0.0105 | 0.7741 ± 0.1627 | 0.7940 ± 0.2258 |
| `patchtst` (published) | 0.3725 ± 0.1589 | 0.0901 ± 0.0481 | 0.7028 ± 0.4156 | 0.6676 ± 0.3717 |
| `tcn` | — | 0.1587 ± 0.1834 | — | 0.6972 ± 0.3488 |
| `chronos-bolt-small` | — | 0.0215 ± 0.0205 | — | 0.6398 ± 0.3664 |

Three corrections:

1. **At full channel scale on Mission 1, every arm collapses** — the best is PatchTST at 0.0901.
   This corroborates the thesis's framing that *"full-channel results under the official protocol
   remain low for the published baselines"*. My earlier text did not mention full-channel results
   at all.
2. **On Mission 2 the trivial `out_of_limits` rule beats every learned arm** (0.9648 lightweight,
   0.8936 full) — a stronger trivial-baseline result than anything I reported, and the single most
   striking number in the telemetry work.
3. **Seed variance is very large** (e.g. `m1_target_tcn_tc_s2` 0.2022 ± 0.2264;
   `m2_lightweight_patchtst_s0` 0.7028 ± 0.4156), which matches the thesis's own judgement that
   the tree-versus-AR(8) comparison is *"inconclusive, because of the seed variance"*. My earlier
   single-row quotations (`patchtst` "0.496") were individual rows, not means, and were therefore
   unstable.

I also previously stated `cosmos_monitor` "ties a trivial out-of-limits rule" as a general finding.
It ties it on m1_lightweight (0.2021 vs 0.2019) and is **far worse** on m2_target (0.0471 vs
0.8936). The honest statement is that performance is strongly mission- and scale-dependent.

The thesis additionally records a framing caveat I omitted: *"the published baselines did not use
training labels, so comparisons with them need that context."*

### 3.3 MAJOR — My "architecture diagram MISSING" finding was wrong

`JIRS_MANUSCRIPT_QUALITY_AUDIT.md` §4 recorded an architecture diagram as **MISSING** and
recommended creating one. **Six architecture diagrams already exist** in `thesis/figures/`
(`diag_overall`, `diag_ai_layer`, `diag_alarm_layer`, `diag_pipeline_flow`, `diag_esa_protocol`,
`diag_event_tcn`), with graphviz `.dot` sources, plus generators in
`journal_v3_twin/tools/make_architecture.py` and `thesis/tools/make_diagrams.py`.

The recommendation stands only in the narrow sense that no diagram is *in the current manuscript*.
The claim that one did not exist was false, and it was false because I had not inspected `thesis/`.

### 3.4 MAJOR — The project's most methodologically rigorous study is not in any current manuscript

The pre-registered ESA-ADB alarm-selection study (§2.3) has: an official benchmark protocol,
official metric code, a reproduced published baseline, frozen hashes, gated test scoring,
hierarchical bootstrap, Holm correction, two missions, two channel scales, and both positive and
conditional-reversal findings on **selection stability** — the exact theme I proposed for the JIRS
reframing, with stronger methodology than the OPS-SAT evidence I built that proposal on.

**It is in the thesis and in no current manuscript track.**

### 3.5 Satisfactory findings

| Item | Assessment |
|---|---|
| Supersession discipline | Four superseded tracks, each marked, with specific withdrawn claims named and the hazard stated |
| Evidence-provenance system | 16,189 keys with kind and source; renderer aborts on unsupported placeholders |
| Reference verification | 68 references logged with DOI and verification source; 3 honestly marked "not found" |
| Prior self-assessment | Appendix D's reviewer-perspective table is candid, including "the main deep-learning result is negative" |
| Study configuration | Six study configs under `configs/`, separating protocol from code |

## 4. Corrections to carry forward into Stages 2–5

| # | Earlier claim | Status |
|---|---|---|
| C-1 | "The C-1 intersection is unoccupied" | **IN DOUBT** — Shorten et al. 2023 must be read |
| C-2 | Architecture diagram missing | **WRONG** — six exist |
| C-3 | ESA-ADB: `cosmos_monitor` ties a trivial rule; PatchTST 2.5× better | **INCOMPLETE** — one mission, one scale; reverses elsewhere |
| C-4 | "2023–2026 AD literature outstanding due to rate limiting" | **PARTLY WRONG** — the repo holds verified AD literature including Liu 2024 (TSB benchmark critique), Sehili 2023 (flawed evaluation), Malhotra 2016 (LSTM-AE), García 2022 (DC-VAE), Paparrizos 2022 (TSB-UAD), Wenig 2022 (TimeEval), Schmidl 2022, Huet 2022, Ruff 2021, Pang 2022 |
| C-5 | My JIRS novelty assessment ranked OPS-SAT as the strongest validated positive | **NEEDS REVISION** — the pre-registered ESA-ADB study is more rigorous and was not considered |

## 5. Unresolved questions

1. **What is the overlap between Shorten et al. (2023) and contribution C-1?** Requires the full
   text (JSR 60(6):2003–2007). **Blocks any novelty claim for the lifetime benchmark.**
2. **"The three publication tracks"** — your Stage 2 brief names these; I have found **four**
   superseded tracks plus a thesis and a current manuscript. I will not guess which three you
   mean. Please confirm, or I will interpret them as (a) telemetry/ESA-ADB alarm selection,
   (b) orbital lifetime benchmark, (c) the integrated twin.
3. **Has the thesis been submitted, deposited or examined?** This determines the prior-publication
   disclosure required by Springer. Only you can answer.
4. **Three unread references** the thesis flags as required: Brancato et al. (AST 2027) — whose
   Mission 1 numbers *"cannot be reconciled with this study without their full text and code"* —
   Fejjari et al. (Acta Astronautica), Dai et al. (Advances in Space Research).
5. **Three references marked "not found"** in the verification log, including RevIN and a Zeng et
   al. telemetry survey.
6. **Off-repository build dependencies.** `thesis/README.md` references pandoc and LibreOffice
   under `/data/anupa/COSMOS_work/.tools*` — note `/data/`, not `/data2/`, a different filesystem
   root. Reproducibility implication not yet assessed.
7. **Does the ESA-ADB study's pre-registration exist as a frozen artifact**, comparable to the G5d
   seal? Not yet located.

## 6. Pending inspection — Stage 1 is NOT complete

| Artifact | Why it matters | Priority |
|---|---|---|
| `thesis/audit/STAGE1_AUDIT.md` (267 lines) | A prior staged audit; may duplicate or contradict this one | **High** |
| `thesis/audit/CLAIM_EVIDENCE_MATRIX.md`, `REVISION_PLAN.md`, `CHANGELOG.md` | Prior claim/evidence mapping | **High** |
| `thesis/src/` 13 chapters | The actual scientific content of the thesis | **High** |
| `research_design/VENUES.md` | Prior venue analysis, referenced by Appendix D | **High** |
| `thesis/evidence/original_pipeline_runs.json` | Reproducibility evidence | **High** |
| ESA-ADB pre-registration / freeze artifacts | Confirms the study's confirmatory status | **High** |
| `docs/architecture/` (6 files) | Architecture and dataflow documentation | Medium |
| `outputs/pipeline/` (309 files) | End-to-end run records | Medium |
| `cosmos/health`, `debris`, `reentry`, `survival`, `conjunction`, `vision`, `twin` source | Module-level correctness | Medium |
| Benchmarks `telemetry_smap_msl`, `reentry_landmark`, `reentry_surrogate`, `telemetry_cosmos_synthetic` | Four result sets never inspected | Medium |
| `paper/journal_v3_twin/build/numbers.json` | A numbers-provenance mechanism | Medium |
| `notebooks/` (2 notebooks, 3.1 MB) | May contain analyses not represented elsewhere | Low |
| `thesis/figures/` 38 files individually | Reusable assets | Low |

**Estimate: Stage 1 is about 60 % complete.** The high-priority items above would take one further
pass.

## 7. Next steps

**Immediate (to finish Stage 1):** inspect the seven high-priority pending items in §6,
particularly `thesis/audit/STAGE1_AUDIT.md` and the ESA-ADB pre-registration artifacts.

**Before Stage 2 can be done honestly:** resolve unresolved question 1 (Shorten et al. overlap)
and question 2 (which three publication tracks). Stage 2 asks me to recommend the strongest
defensible contribution; I cannot do that while the lifetime benchmark's novelty is in doubt and
while the strongest-methodology study (ESA-ADB) has only just been discovered.

**I have started no experiment and modified no artifact in this stage.** All inspection was
read-only.

---

## Stage 1 summary for the record

| | |
|---|---|
| Artifacts inspected | 16 groups |
| Major discoveries | 4 (four manuscript tracks; a complete thesis; a 16,189-key evidence system; a prior Q1 roadmap) |
| Corrections to my own prior audit | **5** |
| Critical findings | 1 (potential uncited prior art for C-1) |
| Unresolved questions | 7 |
| High-priority inspections pending | 7 |
| Stage 1 completeness | **~60 %** |
