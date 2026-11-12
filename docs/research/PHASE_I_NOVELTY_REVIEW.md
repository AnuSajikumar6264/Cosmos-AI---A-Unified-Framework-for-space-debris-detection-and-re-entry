# Phase I — novelty review

> **Superseded in part (2026-11-04).** A 2023–2026-prioritised review now supplements this
> document: see [`LITERATURE_REVIEW_2023_2026.md`](LITERATURE_REVIEW_2023_2026.md),
> [`RESEARCH_GAP_ANALYSIS.md`](RESEARCH_GAP_ANALYSIS.md) and revision 2 of
> [`NOVELTY_AND_CONTRIBUTION_STATEMENT.md`](NOVELTY_AND_CONTRIBUTION_STATEMENT.md). The Phase I
> verdicts below still hold, with three additions: contribution A is **strengthened** (Zhou et
> al. 2026 is event-based on one platform, not catalogue scale); conformal-on-spacecraft-telemetry
> is now **occupied** (Nan Lu et al., *PLoS ONE*, 2026-10-13); and the negative-results genre is
> already **established** in this field by Herrmann et al. 2024 (*CEAS Space Journal*).

Date: 2026-11-04. **Outcome: two of four candidate contributions are already done, one survives
only as a mechanism, one survives only as an artifact.**

## Provenance of this review, and its verification status

A delegated literature search retrieved **76 works** live from Crossref, OpenAlex and the arXiv
API. I then **independently re-verified the five load-bearing claims myself**, because they
determine what the manuscript may assert:

| Ref | Claim it supports | My independent verification |
|---|---|---|
| **[21]** Zou, Feng, Li & Wang, *Horizon-aware group-conditional conformal prediction*, Machine Learning with Applications **26**:101038, 2026, `10.1016/j.mlwa.2026.101038` | pre-empts contribution B *and* the cluster-interval element of A | **VERIFIED** via Crossref: title, 4 authors, journal, volume 26, article 101038, Elsevier, CC BY-NC-ND, 64 references |
| **[30]** Henzi, Ziegel & Gneiting, *Isotonic Distributional Regression*, JRSS-B, 2021, `10.1111/rssb.12450` | dissolves the L17 incoherence finding | **VERIFIED** via OpenAlex: title, 3 authors, JRSS-B, 2021, 47 citations |
| **[55]** Şahin, *TC-CAD*, Zenodo, 2026-10-12, `10.5281/zenodo.23322711` | pre-empts contribution D and the ESA-ADB negative result | **VERIFIED** via OpenAlex: dataset type, date 2026-10-12, and abstract content confirming preregistered negative conditioning result, adaptive conformal inference as best-calibrated thresholding, and budgeted two-threshold deferral cutting "29–33 percentage points" of alarms |
| **[20]** Wang & Hyndman, *Online conformal inference for multi-step time series forecasting*, arXiv:2410.13115 | pre-empts the horizon-degradation finding | **VERIFIED** via arXiv: quote confirmed — "the coverage error admits an upper bound that increases with the forecasting horizon" |
| **[8]** Taggart, Loveday & Louis, *Evaluating time-to-event forecasts under fixed-horizon right-censoring*, arXiv:2603.14835 | provides the correct evaluation machinery; raises a possible correctness issue | **VERIFIED** via arXiv: quotes confirmed — "quantiles and prediction intervals whose endpoints are quantiles remain locally elicitable"; "the expectation functional is not locally elicitable" |

**The remaining ~71 references rest on the delegated retrieval and must be re-checked
individually before any of them is cited in a submission.** Four items were flagged
`UNVERIFIED` on their venue (Gibbs & Candès ACI, Tibshirani et al. covariate shift, Zaffran et
al. ACP-TS — commonly cited as NeurIPS/ICML but only arXiv DOIs confirmed), and the SpotGEO
*challenge* paper could not be retrieved at all — only the dataset deposit `10.5281/zenodo.3874325`.

## Verdicts

| Contribution | Verdict | Decisive prior work |
|---|---|---|
| **A** catalogue-scale forward-in-time lifetime/re-entry benchmark | **INCREMENTAL — survives as an artifact, not a method** | [1] Salmaso et al. 2023 (ML re-entry, >400 objects); [5] **Rodriguez-Fernandez, Sarangerel, Siew et al. 2024** `10.2514/6.2024-1673` (space-object density prediction — replaces the unresolvable "Siew et al. 2025", see Phase O); [9][10] Castet & Saleh 2009 `10.2514/1.42243` (censored satellite survival at catalogue scale); [8] **Gneiting 2011** `10.1198/jasa.2011.r10138` and **Taggart 2022** `10.1214/21-EJS1957` (point-forecast elicitability theory) |
| **B** temporal calibration-failure analysis | **ALREADY DONE** | [17] Barber et al. 2023 *Annals of Statistics* (coverage-gap bound under drift, 352 cit.); **[20]** (coverage error bound *increasing in horizon* — proved); **[21]** (multi-horizon group-conditional coverage auditing with cluster bootstrap, journal-published 2026); [14][15][19] (ACI, online conformal, conformal PID — the fixes) |
| **C** selection non-transfer across temporal origins | **phenomenon ALREADY DONE; mechanism is the only novel sliver** | [41] Clark & McCracken **2001**; [42][43] Pesaran & Timmermann; [40] **Inoue, Jin & Rossi 2017** (rolling-window selection — replaces the unresolvable "Bailey 2014", see Phase O); [35] Gulrajani & Lopez-Paz 2020; [34] **Yao et al.** *Wild-Time* 2022; [37][38] 2026 papers showing explicit **rank inversion** |
| **D** evidence-graded abstention architecture | **ALREADY DONE** | [49] Hendrickx et al. 2024 survey; [48] SelectiveNet; [53][54] Angelopoulos et al. *Conformal Risk Control*; [6] MAD-LEO "Tiered Multi-Source Evidence" (2026, same domain); **[55]** TC-CAD (budgeted two-threshold deferral + adaptive conformal, on ESA-ADB). *Phase O: the previously listed "[52] ACM CSUR 2025 survey" does not exist and is dropped; the conclusion does not depend on it.* |

### Why B is the clearest loss

Our Phase H/G5 headline — conformal intervals fail nominal coverage and degrade with time from
origin (rank trend −0.83 to −0.94) — is pre-empted three independent ways:

1. **As a theorem.** [20] bounds finite-sample coverage error as *increasing in the horizon*.
   [17] derives the coverage gap as a function of distribution drift.
2. **As a protocol.** [21] audits coverage per (group, horizon) cell with **cluster-bootstrap
   intervals** and a rolling-origin deployment protocol — which is, essentially, our Phase H and
   G5 calibration design, published in a journal in 2026.
3. **As a solved problem.** [14][15][19] are the standard fixes we did not apply.

The L17 incoherence sub-finding is additionally pre-empted by **[30]** (monotone predictive CDFs
by construction, JRSS-B 2021) and [31] (post-hoc coherent survival calibration). Our
P(≤30 d) > P(≤90 d) violation is a consequence of calibrating each horizon independently — a
known-bad design, not a discovery.

### What survives in C

I could not find prior work for the specific diagnosed cause: **target point-mass composition
shift between the selection and evaluation populations in a censored time-to-event target**.
That is the one element with no located precedent.

But our own G5 analysis found this mechanism **NOT CONFIRMED** (cap-mass/loss correlation
+0.891 at one origin, −0.158 at the other). So the surviving novel sliver is a mechanism we
have *described and measured* but **not established**. It cannot carry a paper on its own.

Note also [8]'s result that the expectation functional is not locally elicitable under
fixed-horizon censoring — a reviewer may argue that *this* is the real explanation for our
result, which would consume even the mechanism claim.

## A correctness check prompted by this review

[8] proves quantiles and quantile-endpoint intervals remain locally elicitable under
fixed-horizon right-censoring, while the **expectation functional does not**. I audited our
endpoints:

| Endpoint | Used in | Elicitability under [8] | Status |
|---|---|---|---|
| Pinball loss on quantiles | every Phase E/G+/G5 comparison | locally elicitable | **SAFE** |
| Interval coverage (quantile endpoints) | Phase H, G5 | locally elicitable | **SAFE** |
| Brier on horizon-event indicators | G2 multi-horizon | binary event score | **SAFE** |
| Expected/observed event counts | G2 | binary calibration-in-the-large | **SAFE** |
| **`rmse_log10`** | published `regression_test.csv` | **mean-elicited — NOT theoretically justified** | **FLAGGED** |

**All conclusions in Phases E, H, G+ and G5 are safe**, because every endpoint I used is
quantile-, interval- or binary-probability-based. The published study's `rmse_log10` column is
mean-elicited and should not be reported as an evaluation metric for a fixed-horizon-censored
target. It is a secondary column, never a headline, so no existing conclusion changes — but it
should be dropped or caveated.

This is a genuine benefit of the review: it validated the metric choices we had already made,
and found one column that should not be used.

## Two priority threats

1. **[21] Zou et al. 2026** — journal-published, multi-horizon group-conditional coverage
   auditing with cluster bootstrap and a rolling-origin protocol, plus a shrinkage *fix*. This
   pre-empts B and the clustered-interval element of A. **Verified by me directly.**
2. **[55] TC-CAD, 2026-10-12** — preregistered negative result on **ESA-ADB**, with adaptive
   conformal inference as the best-calibrated thresholding layer and budgeted two-threshold
   deferral. This pre-empts D, the ESA-ADB negative-result framing, and the abstention
   mechanism, simultaneously. **Verified by me directly**, including the abstract content.
   It is a Zenodo deposit with no peer review and 0 citations — which makes it *easier* for a
   reviewer to overlook but does not remove the priority problem. Its date (2026-10-12) likely
   predates our write-up; this must be checked against our own records and cited either way.

## Claims that must be dropped

1. **"An integrated framework for satellite health, lifetime, debris and collision risk."**
   Unsupported by our own ablations, and each component literature is more advanced than an
   integration paper could be.
2. **B as a contribution.** Demote to a results paragraph citing [17], [20], [21].
3. **The isotonic-incoherence finding as a discovery.** Cite [30] and [31]; report as a
   design-choice diagnostic.
4. **C as a general finding.** Keep only the mechanism, and label it unconfirmed.
5. **D entirely.** Reframe as an engineering detail of the benchmark release.
6. **Any novel conformal or calibration method.** We have none.
7. **Priority on the ESA-ADB negative result** without citing [55].

## Two defensive moves before submission

1. **Adopt [8]'s evaluation machinery** (threshold-weighted CRPS / quantile scores, Murphy
   diagrams, quantile-isotonic reliability diagrams) rather than our own censoring-aware
   metric, and drop `rmse_log10`.
2. **Add [7] ML-dSGP4** (`10.1016/j.actaastro.2024.10.063`) as the physics/hybrid baseline.
   "A physics baseline" is too weak for this field; a reviewer will name dSGP4 specifically.

## Status

| Item | Status |
|---|---|
| Literature review conducted with live verification | **PASS** — 76 works retrieved; 5 load-bearing claims re-verified independently |
| Novelty of the integrated framework | **REFUTED** |
| Novelty of B (calibration failure) | **REFUTED** |
| Novelty of D (abstention) | **REFUTED** |
| Novelty of A (benchmark artifact) | **PARTIAL** — the specific intersection appears unoccupied; artifact only |
| Novelty of C's mechanism | **PARTIAL** — no precedent located, but our own analysis did not confirm it |
| Remaining ~71 references | **NOT INDEPENDENTLY VERIFIED** — re-check before citing |
