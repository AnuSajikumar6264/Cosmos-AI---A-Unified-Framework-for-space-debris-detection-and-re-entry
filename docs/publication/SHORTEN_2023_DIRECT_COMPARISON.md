# Shorten et al. (2023) — direct comparison

Date 2026-11-05

**Conclusion: Shorten et al. does NOT occupy COSMOS-AI's orbital-lifetime contribution. The
novelty concern I raised is resolved in COSMOS-AI's favour. The paper must nevertheless be
cited.**

---

## 1. Retrieval record

| Attempt | Outcome |
|---|---|
| `arc.aiaa.org/doi/10.2514/1.A35642` | **HTTP 403** — paywalled |
| `doi.org/10.2514/1.A35642` | 302 → AIAA (403) |
| Crossref API | HTTP 429 after repeated backoff; metadata not retrieved this session |
| **arXiv search** | **Found: `arXiv:2212.08662v1`, submitted 16 Dec 2022, CC BY-NC-ND 4.0** |
| Semantic Scholar | Confirmed DOI ↔ arXiv linkage (`CorpusId 254854333`), open-access PDF status GREEN |
| **arXiv full text** | **Retrieved and extracted locally: 29 pages, 75,995 characters** |

**What I read:** the complete 29-page arXiv preprint (v1).
**What I did not read:** the published *Journal of Spacecraft and Rockets* 60(6):2003–2007
version, which is a **5-page condensation**. Any claim specific to the published version — final
wording, added or removed content, peer-review changes — **cannot be verified** from what I have.
The comparison below rests on the preprint.

**Bibliographic record (verified):** Shorten, D. P., Yang, Y., Maclean, J., & Roughan, M.
*Wide-scale Monitoring of Satellite Lifetimes: Pitfalls and a Benchmark Dataset.* Journal of
Spacecraft and Rockets 60(6):2003–2007, 2023. DOI `10.2514/1.A35642`. Preprint
`arXiv:2212.08662`. Authors at University of Adelaide and UNSW.

## 2. The decisive evidence — term frequency in the full text

| Term | Occurrences in the 29-page full text |
|---|---|
| "decay" | **0** |
| "re-entry" / "reentry" | **0** |
| "time-to-decay" | **0** |
| "quantile" | **0** |
| "uncertainty" | **0** |
| "lifetime" / "lifetimes" | 8 |
| "manoeuvre detection" | 3 |
| "benchmark" | 12 |

**"Lifetimes" in this paper does not mean time-to-decay.** The Introduction fixes the sense:

> "The ability to recover the manoeuvre history of satellites is important for the analysis of
> their lifetimes. In particular, it is of significant interest to know whether a satellite has
> already reached its end of life and if its last manoeuvre has been performed in accordance with
> the Inter-Agency Space Debris Coordination Committee (IADC) mitigation [guidelines]"

So "satellite lifetimes" = **operational life and end-of-life determination inferred from
manoeuvre history**, not the remaining orbital lifetime of an object under atmospheric drag.

## 3. Direct comparison

| Dimension | **Shorten et al. (2023)** | **COSMOS-AI lifetime track** |
|---|---|---|
| **Research objective** | (i) Document TLE-specific pitfalls that mislead researchers from adjacent fields; (ii) release a shared benchmark to fix non-comparability across manoeuvre-detection methods | Measure whether validation-based model selection predicts forward performance in catalogue-scale time-to-decay prediction; release a forward-in-time benchmark |
| **Dataset** | NORAD **Two-Line Element (TLE)** data for **15 satellites**, with curated ground-truth manoeuvre timestamps | **GCAT canonical orbits + CelesTrak SATCAT + CelesTrak space-weather indices**, snapshot 2026-10-27; derived cohort of **64,516 objects**; no TLEs used |
| **Prediction target** | **Manoeuvre occurrence** (detect behavioural change in the orbit record) | **Capped log-lifetime** `z = log10(min(time_days, 1826.25))`, a continuous target with a point mass at the horizon |
| **Methodology** | **None.** A pitfalls analysis plus a dataset release. No models, no training procedure, no algorithms | 17 model arms: physics baseline, 3 gradient-boosting, 3 neural/tabular-deep, gated fusion, simple combiners, feature ablations, conformal variants |
| **Temporal evaluation** | Not a forecasting task; no train/test temporal protocol reported | Strictly ordered temporal splits at **three origins** (2006, 2011, 2016); one hash-sealed before any fit; verified launch-family and test-fold disjointness |
| **Baselines** | None reported. Prior manoeuvre-detection work referenced generically as evaluated on mismatched satellite sets | Physics-only analytic drag baseline, trivial combiners, 6 learned families, feature ablations |
| **Uncertainty evaluation** | **Absent** — the word does not appear | Mondrian conformalised quantile regression; empirical vs nominal coverage per origin and per slice; interval widths |
| **Main findings** | TLE quirks are under-documented and actively hazardous, especially for non-specialists; existing manoeuvre ground truth is often poor or subjective, sometimes "based on subjective human assessment"; a curated 15-satellite benchmark is released | Selection and test rankings are rank-independent at both published origins (ρ = 0.000, n = 7); selection regret 3.4 % → 18.7 % → 25.2 % across origins, significant at 2016; physics baseline 1st of 19 at one origin and 19th of 19 at another |
| **Limitations** | Not stated in the abstract; the preprint's framing is a service contribution rather than a hypothesis test | Extensive and documented: n = 7 for the headline ρ; H2 chance level 0.1985; 5 of 7 learners not refittable; no external baseline |
| **Venue** | Journal of Spacecraft and Rockets (AIAA), Technical Note | — |

## 4. COSMOS-AI's genuinely distinct contribution relative to this paper

There is **no overlap in prediction target, dataset family, methodology, or evaluation
construct.** Specifically:

1. **Different task.** Manoeuvre *detection* (a change-point/classification problem on an orbit
   record) versus time-to-decay *forecasting* (a censored continuous-target regression problem).
2. **Different data.** TLEs for 15 satellites versus a 64,516-object GCAT/CelesTrak catalogue
   cohort. COSMOS-AI explicitly does **not** use TLEs — and documents that as the reason an
   ML-dSGP4 comparison was not attempted.
3. **Different scientific question.** Shorten et al. ask *"what traps does this data type set, and
   can we standardise evaluation?"* COSMOS-AI asks *"does the standard model-selection protocol
   predict forward performance?"*
4. **Shorten et al. contribute no predictive method or result**, so they cannot be outperformed or
   contradicted; they are not a competing method.

## 5. Why it must still be cited — three reasons

1. **Title adjacency is a real reviewer-perception risk.** A paper titled *"Wide-scale Monitoring
   of Satellite Lifetimes: Pitfalls and a Benchmark Dataset"* in a peer-reviewed AIAA journal,
   uncited by a manuscript releasing a satellite-lifetime benchmark with a pitfalls argument, will
   look like an incomplete literature search. The distinction is easy to state in one sentence and
   costs nothing.
2. **It supports a COSMOS-AI decision.** Shorten et al. warn that TLE quirks make it "a
   particularly hazardous data type for researchers from adjacent disciplines (such as anomaly
   detection or machine learning)". COSMOS-AI's documented decision **not** to attempt a
   TLE/B\*-based ML-dSGP4 comparison is directly supported by this. Citing it converts an apparent
   gap into a justified scope decision.
3. **Shared framing precedent.** It establishes that "pitfalls + benchmark release" is a
   publishable contribution shape in this domain — useful positioning for a benchmark paper.

**Suggested citation sentence:**

> Benchmark releases addressing data-quality pitfalls have precedent in this domain: Shorten et
> al. [ref] document under-documented quirks of Two-Line Element data that mislead researchers
> from adjacent disciplines, and release a curated 15-satellite manoeuvre-detection benchmark with
> high-quality ground truth. Their target — manoeuvre detection from TLEs — is distinct from the
> censored time-to-decay forecasting addressed here, and their stated TLE hazards are among the
> reasons we build on catalogue orbital elements rather than TLEs.

## 6. Claims that cannot yet be verified

| Claim | Status |
|---|---|
| The **published** JSR 5-page version's exact content, wording and any peer-review additions | **Unverified** — paywalled; the 29-page preprint was read instead |
| Whether the published version added any decay or lifetime-prediction material absent from the preprint | **Unverified.** Low risk: the title, abstract and task are unchanged between versions, and the preprint contains zero occurrences of "decay" |
| The benchmark's exact time span and manoeuvre count | Not extracted; the preprint's dataset section was not read line by line (the 15-satellite figure and ground-truth timestamps are confirmed from the abstract) |
| Citation count | Not retrieved (Crossref rate-limited) |

**None of these affects the conclusion.** The decisive facts — zero occurrences of "decay",
"re-entry", "quantile" and "uncertainty" in 29 pages, and an Introduction that defines "lifetimes"
as end-of-life via manoeuvre history — come from the full preprint text, not from an abstract.

## 7. Effect on the audit

| Earlier status | Updated status |
|---|---|
| "C-1 novelty **IN DOUBT** pending Shorten et al." | **RESOLVED.** Shorten et al. does not occupy the lifetime-prediction contribution |
| "Blocks any novelty claim for Track 2" | **Unblocked by this paper.** Track 2's novelty is no longer in doubt *on these grounds*; it remains subject to the separate finding that Candès et al. (2023) and Gui et al. (2024) on conformalized survival analysis are uncited methodological prior art |
