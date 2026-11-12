# Novelty and contribution statement

Date: 2026-11-04. **Revision 2** — supersedes the Phase I statement, updated against a
2023–2026-prioritised literature review (88 % of references from 2023–2026).

Evidence base: [`LITERATURE_REVIEW_2023_2026.md`](LITERATURE_REVIEW_2023_2026.md),
[`RESEARCH_GAP_ANALYSIS.md`](RESEARCH_GAP_ANALYSIS.md). Experimental evidence unchanged.

## What changed in this revision

| Change | Cause |
|---|---|
| Added a **positioning constraint**: our negative-results genre is already established in this field | **[R9]** Herrmann et al. 2024, *CEAS Space Journal* — spacecraft-telemetry AD results are "overestimated", simple baselines sometimes win, field needs "high-quality, pre-split datasets" |
| Removed the conformal-on-spacecraft-telemetry novelty | **[R20]** Nan Lu et al., *PLoS ONE*, 2026-10-13 — task-aware conformal, multi-horizon, real BUPT-1 telemetry, joint coverage |
| **Strengthened** contribution A | **[R1]** Zhou et al. 2026 (*JGR Space Physics*) is event-based on a single GRACE platform predicting SMA loss — it does **not** occupy catalogue-scale time-to-decay |
| Added a required citation for temporal adaptation | **[R2]** He et al. 2024 — continual learning for orbit decay, i.e. a *solution* where we provide a *diagnosis* |
| Added a new contribution: the reproducibility failure | our own Phase M audit — 2 of 7 learners reinstallable, **both** selected learners missing |
| Dropped the "digital twin" framing | the 2023–2026 "satellite digital twin" literature is networking work ([R32]–[R34]); the predictive niche is empty but Phase E refuted our premise for occupying it |

## The claim

> We release a catalogue-scale, forward-in-time benchmark for orbital lifetime and re-entry
> prediction with censoring-aware quantile targets and launch-family-clustered intervals, and
> use it to show that the model-selection protocol standard in this field carries no information
> about forward performance: the selection-set ranking and the test-set ranking are
> rank-independent at both temporal origins (Spearman = 0.000), a physics baseline ranks last of
> 17 at one origin and first of 17 at the other, and model ordering inverts in 23.64 % of
> pairwise comparisons across 11 launch-epoch evaluation slices.

Every number above was **verified against its source artifact** in this session.

## Positioning sentence for the introduction

> The orbital-prediction literature optimises accuracy against benchmarks whose selection
> protocol has never been validated [R4]. Following calls in spacecraft telemetry research for
> less accuracy-inflating evaluation and high-quality pre-split datasets [R9], we release such a
> benchmark for orbital lifetime and report what it reveals about selection validity.

This positions us as **extending [R9]'s established line into orbital lifetime prediction** —
which is both honest and the strongest available framing.

## Contribution-by-contribution

| # | Contribution | Type | Status | Key citations to position against |
|---|---|---|---|---|
| **C-1** | Catalogue-scale forward-in-time lifetime/re-entry benchmark, censoring-aware | **artifact** | **Defensible** — intersection unoccupied | [R1][R2][R3] scale/estimand; [R15] precedent for publishing a benchmark |
| **C-2** | First measurement of selection non-transfer in orbital lifetime prediction | **domain-first measurement** | **Defensible** | [R4] (field frames its problem as accuracy only); phenomenon established elsewhere |
| **C-3** | Reproducibility failure analysis of a published orbital-ML pipeline | **methodological** | **Defensible, new** | [R9]'s call for pre-split datasets; [R2]'s undisclosed protocol |
| **C-4** | Narrow measured findings: loss concentration 4.1–6.6× below the cap; learner-dependent feature sign reversals | **measurement** | **Defensible, narrow** | [R9] genre |
| **C-5** | Preserved negative results: coupling adds nothing; point-mass mechanism unconfirmed; C4 unevaluable | **negative** | **Defensible** | no competing positive claim located |
| ~~C-6~~ | ~~Temporal calibration-failure analysis~~ | — | **WITHDRAWN** | [R21][R22][R23] |
| ~~C-7~~ | ~~Evidence-graded abstention~~ | — | **WITHDRAWN** | [R19] + two surveys |
| ~~C-8~~ | ~~Coherent multi-horizon calibration~~ | — | **WITHDRAWN** | [R25] |
| ~~C-9~~ | ~~Integrated cross-domain framework~~ | — | **WITHDRAWN** | refuted by our own Phase E/E12/G5 |
| ~~C-10~~ | ~~Debris detection~~ | — | **WITHDRAWN** | [R27]–[R31] |
| ~~C-11~~ | ~~Satellite digital twin~~ | — | **WITHDRAWN** | [R32]–[R34] occupy the term |

**Five contributions retained, six withdrawn.**

## Secondary findings reportable as confirmations, not discoveries

1. Coverage degrades with time from the forecast origin (rank trend −0.83 to −0.94) — an
   instance of [R23]'s proved bound; corroborated by [R20]'s own sub-nominal 0.892.
2. The deployed fusion is beaten by 19.4 % by a parameter-free median blend and ranks best in
   **none** of 11 slices — an instance of [R9]'s "simple baselines sometimes win".
3. Per-horizon independent isotonic calibration harms both coherence and Brier — a design
   diagnostic, with [R25] as the principled fix.

## Explicitly not claimed

- No novel conformal, calibration or abstention method.
- No priority on overestimation, baseline-beats-complex, or metric-validity findings ([R9]).
- No validated end-to-end health → lifetime → debris → risk chain.
- No calibrated re-entry probabilities (both readings over-forecast 8.7×–14.8×).
- No validated impact-location prediction.
- No prospective or independent validation (Phase F blocked until 2026-11-26).
- No demonstrated benefit from cross-domain coupling.
- No digital-twin or debris-detection contribution.
- No Scopus rank or Q1 claim — unverifiable from accessible sources.

## Required citations the manuscript cannot omit

| Ref | Why it is mandatory |
|---|---|
| **[R9]** Herrmann 2024 | establishes our genre; omitting it would look like unawareness of the closest prior work |
| **[R19]** TC-CAD 2026 | priority on the ESA-ADB negative result and budgeted abstention; cite with unreviewed status stated |
| **[R20]** Nan Lu 2026 | conformal + multi-horizon + real spacecraft telemetry |
| **[R21]** Zou 2026 | multi-horizon coverage auditing with cluster bootstrap |
| **[R23]** Wang & Hyndman 2024 (**preprint**) | horizon-increasing coverage-error bound |
| **[R24]** **Gneiting 2011** `10.1198/jasa.2011.r10138` and **Taggart 2022** `10.1214/21-EJS1957` | the evaluation theory our estimand requires (Phase O: previously mis-dated as "Taggart 2026") |
| **[R25]** Henzi 2021 | monotone CDFs; dissolves the L17 discovery claim |
| **[R1][R2][R3]** | the orbital decay/re-entry ML state of the art |
| **[R4]** Caldas & Soares 2024 | the field's own framing of its open problem |
| **[R5]** ML-dSGP4 | the physics baseline we assessed and excluded |
| **[R15]** OPS-SAT | precedent for publishing a benchmark in this domain |

## Recommended paper type

A **benchmark release plus negative-results and reproducibility study**. [R15] (*Scientific
Data*) and [R9] (*CEAS Space Journal*) establish that both halves are publishable in this
field. This is narrower than the original COSMOS-AI vision and is the form the evidence
supports.

Venue fit is assessed separately in [`FINAL_JOURNAL_POSITIONING.md`](FINAL_JOURNAL_POSITIONING.md);
the 2023–2026 review reinforces its conclusion that a space/astrodynamics or data-benchmark
venue fits this contribution better than an intelligent-systems journal.
