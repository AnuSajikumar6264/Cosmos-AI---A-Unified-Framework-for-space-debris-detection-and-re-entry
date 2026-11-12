# Final blockers and remaining work

Date: 2026-11-04 · revision `78ee339`

Classified by whether it blocks submission. **Nothing in this document is a critical scientific
defect** — the Phase N audit found 0 critical failures across 28 mechanical checks.

---

## 1. Hard blockers — submission cannot proceed without these

| # | Item | Why it blocks | Who resolves it |
|---|---|---|---|
| **B-1** | **Explicit approval to commit, push or submit** | The user has reserved all three. Nothing has been committed or pushed in this work | user |
| **B-2** | **Author metadata** — author list, affiliations, ORCIDs, corresponding author, funding statement, competing-interests declaration | No submission form can be completed without them. Out of scope for this work | user |
| **B-3** | **Venue choice and venue formatting** | The manuscript is venue-neutral by design. Reference style, length limits, section structure and figure format all follow from the choice | user, with `FINAL_JOURNAL_SELECTION_REPORT.md` |
| **B-4** | **Scopus category rank verification** | The stated requirement is a top-100 category rank. SCImago and Scopus both return HTTP 403 to this environment, so the rank is **UNVERIFIED** and must not be asserted. Takes a few minutes with institutional access; procedure in `FINAL_JOURNAL_SELECTION_REPORT.md` §6 | user |

## 2. Soft blockers — should be resolved before submission, but do not prevent it

| # | Item | Risk if skipped | Effort |
|---|---|---|---|
| **S-1** | **Verify quoted findings from cited works against full text.** Every reference was resolved at metadata level (author, year, venue, title). Specific numeric findings attributed to other authors — a coverage-error claim, a budgeted-deferral percentage, a joint-coverage figure — were recorded during the literature search and not re-read from full text | **This is the highest-value remaining item.** A reviewer who checks one quoted figure and finds it misquoted damages the paper's credibility far beyond the one sentence. Alternative: paraphrase without the number, which costs nothing | ~1–2 hours for the handful of quoted figures; both affected sites already carry an explicit caveat |
| **S-2** | **Fix one arm-count convention and apply it throughout.** "1st of 17 / 17th of 17" (point-forecast arms), "1st of 19 / 19th of 19" (all published rows) and "1st / 4th / 1st" (the common 4-arm set) are all correct and are **not interchangeable** | The most likely source of a visible internal inconsistency in drafting | 30 minutes of careful reading |
| **S-3** | **Generate figure F6** — the temporal split diagram | A benchmark paper without a split diagram invites avoidable methods questions. All the data exists | ~1 hour |
| **S-4** | **Generate figure F7** — the confirmatory-result slope chart (physics baseline 1st → 4th → 1st) | The paper's one confirmatory result currently has no visual and is easy to under-read as a table | ~1 hour |
| **S-5** | **Re-read the typeset text for tier violations** — no claim stated above its assigned tier, and the word "reproducible" never used unqualified | The locked claim set is the control; drafting is where tiers slip | at proof stage |
| **S-6** | **Vector figure format** if the venue requires it | Existing figures are PNG; the generator can re-emit | ~30 minutes |

## 3. Blocked by calendar time — not resolvable now

| # | Item | Unblocks | Note |
|---|---|---|---|
| **T-1** | **Scoring the registered 2026-10-27 forecast, 30-day horizon** | **2026-11-26** (22 days from today) | Latest outcome coverage is 2026-10-26, giving **−1 outcome days**. Marked `[PENDING EVIDENCE]` in the manuscript. **Do not hold the manuscript for this**, and do not substitute a retrospective fold. When scored, it may equally refute the registered forecast |
| **T-2** | 90-day horizon | 2027-01-25 | as above |
| **T-3** | 1-year horizon | 2027-10-27 | as above |

The manuscript already reports a *completed* prospective test at the earlier 2026-08-16 origin
(13,186 objects, 30-day Brier 0.00127, ECE 0.00130, AUC-ROC 0.982). The narrower claim the
evidence supports is in place; T-1 would strengthen it, not enable it.

## 4. Structurally blocked — will not be resolved by this project

| # | Item | Why |
|---|---|---|
| **X-1** | **Coupling C4 (health → conjunction)** | **0 joinable pairs.** The telemetry corpus is anonymised with no spacecraft identifier; the conjunction corpus is anonymised by construction with no NORAD identifier; the catalogue is identifiable but contains neither telemetry nor conjunction messages. No experiment can be constructed from the data available. Reported as NOT EVALUABLE, which is the correct outcome, not a gap |
| **X-2** | **Differentiable-propagator baseline comparison** | Requires TLE, B\* and ephemeris data the project does not hold. Assessed and declined; documented in `ML_DSGP4_FEASIBILITY.md`. A scope limitation, not an omission |
| **X-3** | **SPARK dataset** | Distributed on request through a contact form requiring the author's identity and acceptance of the providers' terms; the Zenodo record is access-restricted. No request was submitted on the user's behalf. The manifest also records that the dataset targets resolved spacecraft detection and pose, which does not match the unresolved point-target study. **No reported result depends on it** |
| **X-4** | **Training-level reproducibility of the published runs** | Cannot be recovered retroactively. No software environment was recorded for any published benchmark run, so the fitting environment is unreconstructable even though all five missing backends are available on the package index. Reported as a result (§5 below), not fixed |

## 5. Deliberately not fixed — fixing would misrepresent the record

These look like defects and are not. Each was considered and left alone on purpose.

| # | Item | Why it is left alone |
|---|---|---|
| **D-1** | **`rmse_log10` remains in the published CSVs** | Editing a published artifact to match a later methodological decision would be a worse defect than the inconsistency it removes. The exclusion is enforced by **non-use** and verified mechanically: no script selects, ranks or reports on it |
| **D-2** | **The five missing backends are not added to the requirements files** | Adding current-version pins would imply those versions produced the published results. They did not, and the real versions were never recorded. A forward pin is proposed separately (§6) with an explicit comment that it is **not** the publishing environment |
| **D-3** | **The five backends are not installed to force a refit** | Installing current versions would produce *a* refit, not *the* refit, and any discrepancy would be uninterpretable. It would manufacture the appearance of reproduction. The user's instruction against this is now a documented reason rather than a preference |
| **D-4** | **Phase-dated reports still state older test counts (134, 168)** | They are correctly-dated snapshots of the suite as each phase closed. Only the living tracker needed to be current, and it was corrected (213 → **217**) |
| **D-5** | **The G5d pre-registration was not amended to the 4-arm set** | A confirmatory experiment's protocol cannot be edited after the fact. The deviation is recorded separately, which is why the protocol still hashes to `9ea4bf4171cad1b8…` |
| **D-6** | **H3's favourable sign is not reported as support** | 3 arms against a pre-registered floor of 5; ρ = 1.0 arises by chance with probability 1/6. The floor is encoded in the analysis code rather than left to judgement |

## 6. Forward-only engineering work — post-submission

None of these alters a published artifact or a scientific conclusion. They prevent recurrence.

| # | Item | Effort |
|---|---|---|
| **E-1** | **Wire `provenance.run_metadata()` into the run entry points** so every future run records code revision, interpreter version and installed package versions. The function exists, is tested, and has **zero call sites** — this is the single highest-value engineering fix in the project | ~2 hours |
| **E-2** | **Declare the five missing backends** in `requirements-ai.txt`, pinned to current versions, with an explicit comment that these are **forward** pins and are **not** the versions that produced the published results | ~30 minutes |
| **E-3** | **Write a package freeze alongside every run's output directory** | ~1 hour |
| **E-4** | **State inherited upstream terms in derived-dataset manifests.** `feature3_reentry/processed` records its generator and three inputs but no licence, being locally derived; it should state the GCAT (CC-BY-4.0) and CelesTrak terms it inherits. Already stated in `data_availability_statement.md`; belongs in the manifest too | ~15 minutes |

**E-1 is the one that matters.** The reproducibility failure reported in the manuscript is, at
root, that this function was written and never called — and that failure directly underpowered the
project's one confirmatory experiment.

## 7. Future research — explicitly out of scope

Listed so the boundary is recorded, not as a plan.

| Item | Prerequisite |
|---|---|
| A properly powered test of the point-mass mechanism (H3) | the full seven-arm set at three or more origins, which requires **E-1** first |
| Selection under rolling-origin **retraining** | refitting per slice; the current slice analysis does not retrain and says so |
| Scoring the registered forecast at all three horizons | **T-1** through **T-3** |
| A standalone dataset-descriptor paper on the benchmark alone | a venue decision; `Scientific Data` is the natural outlet and is a poor fit for the present analytical paper |

## 8. Summary

| Category | Count | Blocks submission? |
|---|---|---|
| Hard blockers | 4 | **yes** — all four require the user |
| Soft blockers | 6 | no, but S-1 and S-2 are strongly advised |
| Calendar-blocked | 3 | no — the narrower claim is already in place |
| Structurally blocked | 4 | no — each is reported as a result or a documented scope limit |
| Deliberately unfixed | 6 | no — fixing them would misrepresent the record |
| Forward-only engineering | 4 | no — post-submission |

**The project is submission-ready on the scientific evidence.** What remains is venue choice,
author metadata, the Scopus rank verification the environment cannot perform, and the user's
approval.
