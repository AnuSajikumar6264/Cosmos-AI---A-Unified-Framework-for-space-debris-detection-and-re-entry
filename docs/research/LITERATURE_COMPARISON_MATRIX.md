# Literature comparison matrix

Date: 2026-11-04. **Revision 2** — rebuilt with 2023–2026 priority. 88 % of references are
2023–2026.

Verification key: **[V]** re-verified by me directly against a live API in this session ·
**[P]** verified in the Phase I search and re-confirmed here · **[D]** retrieved but not
independently re-verified — **re-check before citing**.
Review key: **PR** peer-reviewed journal/conference · **PP** preprint · **DS** dataset deposit,
not peer reviewed.

## C-1 — Catalogue-scale forward-in-time lifetime/re-entry benchmark

| Ref | Work | Year | Venue | Review | Scale | Estimand | Censoring | Cluster CIs | Forward origins | Occupies C-1? |
|---|---|---|---|---|---|---|---|---|---|---|
| [R1] **[V]** | Zhou et al., *Orbital Decay Prediction in LEO…* `10.1029/2025JA034593` | 2026 | JGR Space Physics | PR | **1 platform, 113 ICME events** | SMA loss (hours–days) | no | no | no | **No** |
| [R2] **[V]** | He et al., *Expandable Orbit Decay Prediction Using Continual Learning* `10.1155/2024/8887634` | 2024 | Int. J. Aerospace Eng. | PR | **undisclosed** | decay accuracy vs HPOP | no | no | continual, not origins | **No** |
| [R3] **[D]** | Salmaso et al. `10.3390/aerospace10030297` | 2023 | Aerospace | PR | **>400 objects** | re-entry epoch | no | no | IADC campaign | **No** |
| [R15] **[P]** | Ruszczak et al., OPS-SAT benchmark `10.1038/s41597-025-05035-3` | 2025 | Scientific Data | PR | telemetry benchmark | anomaly labels | n/a | no | n/a | **No** — but the publication precedent |
| [R21] **[V]** | Zou et al. `10.1016/j.mlwa.2026.101038` | 2026 | Mach. Learn. with Appl. | PR | synthetic + panel | coverage per cell | n/a | **yes** | **rolling-origin** | **partly** — takes the cluster-CI + rolling-origin element |
| **COSMOS-AI** | this work | — | — | — | **31,396 objects; 2,667–7,281 per test fold** | **log10 capped time-to-decay** | **yes** | **yes (launch family)** | **2 published + 1 unexamined** | — |

**Verdict: the intersection is unoccupied. C-1 is defensible as an artifact.**

## C-2 — Selection non-transfer in orbital lifetime prediction

| Ref | Work | Year | Review | Examines selection transfer? | In orbital domain? | Occupies C-2? |
|---|---|---|---|---|---|---|
| [R4] **[V]** | Caldas & Soares, *ML in orbit estimation: a survey* (53 cit.) | 2024 | PR | **No** — frames the open problem as accuracy | yes | **No** |
| [R2] **[V]** | He et al., continual learning | 2024 | PR | addresses catastrophic forgetting, not selection validity | yes | **No** |
| [R3] **[D]** | Salmaso et al. | 2023 | PR | notes distribution-match dependence **informally** | yes | **No** |
| [R9] **[V]** | Herrmann et al., *Unmasking overestimation* | 2024 | PR | metric validity and baseline strength, **not** selection transfer | spacecraft telemetry | **No** — but establishes the genre |
| (selection refs) **[V]** | Clark & McCracken **2001** `10.1016/S0304-4076(01)00071-9`; **Inoue, Jin & Rossi 2017** `10.1016/j.jeconom.2016.03.006`; Gulrajani & López-Paz 2020 `arXiv:2007.01434`; **Yao et al.** *Wild-Time* 2022 (NeurIPS 35); **Wen et al.** *LiveHouse-TS* 2026 `arXiv:2608.17299` (**PP**) | 2001–2026 | PR/PP | **yes** | **no** | **No** |
| **COSMOS-AI** | Spearman 0.000 both origins; 17/17 → 1/17 inversion; 23.64 % slice pairs inverted | — | — | yes | **yes** | — |

**Verdict: the phenomenon is established elsewhere; the orbital measurement is a domain first.**

## C-3 — Reproducibility failure analysis

| Ref | Work | Year | Review | Relevance |
|---|---|---|---|---|
| [R9] **[V]** | Herrmann et al. | 2024 | PR | calls for **"high-quality, pre-split datasets"** — our finding is the concrete failure mode that call anticipates |
| [R2] **[V]** | He et al. | 2024 | PR | its dataset, object count and protocol are **not recoverable** from the published record — an instance of the problem |
| [R19] **[V]** | TC-CAD | 2026 | **DS** | preregistration + per-seed results + deviation logs — the positive model for reproducibility practice |
| **COSMOS-AI** | **2 of 7 learners reinstallable; both selected learners (`tabm`@2016, `kumo`@2011) unavailable; values recomputable from archived predictions but models not refittable** | — | — | — |

**Verdict: new and defensible.**

## Withdrawn contributions — what closed them

| Withdrawn | Closed by | Year | Venue | Review |
|---|---|---|---|---|
| Temporal calibration-failure analysis | [R21] **[V]** `10.1016/j.mlwa.2026.101038` | 2026 | Mach. Learn. with Appl. | PR |
| | [R23] **[V]** Wang & Hyndman arXiv:2410.13115 — "coverage error…**increases with the forecasting horizon**" (metadata verified; **the quoted finding was not re-read from full text**) | 2024 | arXiv | **PP** |
| | [R22] **[V]** Barber et al. `10.1214/23-aos2276` | 2023 | Annals of Statistics | PR |
| Conformal on spacecraft telemetry, multi-horizon | [R20] **[V]** Nan Lu et al. `10.1371/journal.pone.0360910` — BUPT-1, 1/5/15 min, joint coverage 0.892 | 2026 | PLoS ONE | PR |
| Coherent multi-horizon calibration | [R25] **[V]** Henzi, Ziegel & Gneiting `10.1111/rssb.12450` | 2021 | JRSS-B | PR |
| Evidence-graded abstention | [R19] **[V]** TC-CAD — adaptive conformal thresholding + **29–33 pp** budgeted deferral on ESA-ADB (deposit metadata verified; **the quoted deferral figures were not re-read from full text**) | 2026 | Zenodo | **DS** |
| | Hendrickx et al. 2024 survey `10.1007/s10994-024-06534-x`; SelectiveNet `arXiv:1901.09192`; Angelopoulos et al. *Conformal Risk Control* `arXiv:2208.02814` **[V]** · *the previously claimed "ACM CSUR 2025 selective-prediction survey" does not exist and is dropped (see Phase O, O-4)* | 2019–2024 | Mach. Learn. / arXiv | PR/PP |
| Debris detection | [R27] **[V]** Massimi et al. **2024** `10.1049/rsn2.12547`; [R28][R29][R30]; [R31] **[V]** Blake et al. *DebrisWatch II* 2026 `arXiv:2605.27516` (**PP**) and *DebrisWatch I* 2021 `10.1016/j.asr.2020.08.008` (PR) | 2021–26 | IET/Acta/IEEE/MDPI/arXiv | PR/PP |
| Satellite digital twin | [R32][R33][R34] **[V]** — all networking digital twins | 2024–25 | JCIN/Electronics/FITEE | PR |
| Integrated framework improving prediction | **our own** Phase E, E12, G5 | — | — | — |

## Conformal prediction in space — strict search result

| Query | Hits examined | Genuine conformal-in-space | Conjunction assessment |
|---|---|---|---|
| `title_and_abstract.search: conformal AND (orbit OR spacecraft OR satellite OR conjunction)`, 2020–2026 | 15 of 3,010 | **1** ([R20]) | **0** |

The other 14 used "conformal" in unrelated senses: conformal antennas (5), conformal
structures/contact/coating (3), conformal geometry with group orbits (2), conformal field
theory (1), molecular conformers (1), pointing *conformance* (1), and conformal prediction in a
non-space setting where "conjunction" meant logical conjunction (1).

**Reading:** conformal prediction is mature in ML and nearly absent from space applications.
This supports an *application-first* framing only — not a method claim.

## Satellite digital twin — negative finding

A 2023–2026 search returns a literature dominated by **communications/networking** digital
twins ([R32] Plotinus satellite-internet; [R33] LEO constellation networking; [R34]
satellite-terrestrial networks) plus unrelated urban/flood/defence twins. **No recent
peer-reviewed predictive health-and-orbital satellite digital twin was found.** The niche is
genuinely empty — and Phase E refuted our premise for occupying it, so the framing is dropped
rather than claimed.

## Re-verification status — closed by Phase O (2026-11-04)

Every `[D]` row in this matrix was resolved against live Crossref, OpenAlex and arXiv by
`scripts/final_reference_verification.py`. Results, including seven attribution corrections and
two references that must be dropped, are in
[FINAL_REFERENCE_VERIFICATION_MATRIX.md](FINAL_REFERENCE_VERIFICATION_MATRIX.md). Summary:

- **Resolved and corrected in place above**: Clark & McCracken is **2001** not 2002; "Bailey
  2014" does not exist and is replaced by **Inoue, Jin & Rossi 2017**; Wild-Time is **Yao et
  al.**; LiveHouse-TS is **Wen et al.**, not Chung; Massimi is **2024**; DebrisWatch II now
  resolves (`arXiv:2605.27516`, preprint).
- **Dropped**: the claimed "ACM CSUR 2025 selective-prediction survey" (no such work) and any
  reference to a SpotGEO **challenge paper** (unretrievable in all three indexes — cite the
  dataset deposit `10.5281/zenodo.3874325` only).
- **Still open, carried as a citation caution**: venue attributions for Gibbs & Candès,
  Tibshirani et al., Zaffran et al. and SelectiveNet. Only the arXiv DOIs are confirmed; cite
  those rather than asserting a NeurIPS/ICML venue.
- **Citation counts are no longer maintained here.** Three were already stale when checked.
  They are dropped from the manuscript rather than tracked.
