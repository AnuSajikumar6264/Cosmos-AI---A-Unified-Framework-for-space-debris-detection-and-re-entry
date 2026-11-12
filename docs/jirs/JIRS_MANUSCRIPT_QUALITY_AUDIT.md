# JIRS manuscript quality audit (Phase 6 / Parts 7–8)

Date 2026-11-04 · subject: `paper/journal/manuscript.md`, 1,355 lines, 17 sections, 7 numbered
tables, 6 figures, 38 references

**Verdict: the manuscript is a competent orbital-prediction benchmark report. It is not an
intelligent-systems research paper, and for JIRS that is the governing problem.**

Numerical accuracy is now good — the prior review round corrected 13 numerical errors and all
headline values re-derive from their artifacts (27/28 audit checks PASS). The remaining issues are
**framing, scope and completeness for this venue**, not arithmetic.

---

## 1. The central verdict, stated directly

You asked whether the manuscript reads like an intelligent-systems paper or an orbital-prediction
benchmark report. **It reads unambiguously as the latter.**

Evidence from the manuscript's own structure:

- The title names "Orbital Lifetime Prediction".
- §3 (Introduction) motivates from atmospheric drag, ballistic coefficients and thermospheric
  density — physics, not intelligent systems.
- §6 is a catalogue-data description; §7 an estimand definition; §9 a temporal split protocol.
- **The words "intelligent system", "decision support", "autonomy" and "operator" appear nowhere
  as load-bearing concepts.**
- Of 38 references, **zero are from JIRS**, and the venue precedents cited (Scientific Data, CEAS
  Space Journal) are data and aerospace venues.
- The project's one positive intelligent-monitoring result — the OPS-SAT anomaly detector that
  beats a time-series foundation model — **is not mentioned at all**.

A JIRS editor reading this will see a space-science benchmark paper submitted to a robotics and
intelligent-control journal. The likely outcome is desk rejection on scope before review.

## 2. Section-by-section assessment

| § | Section | Q1 quality | JIRS suitability | Key issue |
|---|---|---|---|---|
| 1 | Abstract | **Good** | **Poor** | Correctly hedged after revision, but frames the work as a lifetime benchmark; no intelligent-systems framing; does not mention anomaly detection |
| 2 | Keywords | Adequate | **Poor** | "orbital lifetime", "space debris", "re-entry" — none maps to a JIRS category. No "intelligent systems", "fault diagnosis", "condition monitoring", "model reliability" |
| 3 | Introduction | **Good** | **Poor** | Motivates from orbital physics. A JIRS introduction must motivate from the reliability of machine-learned components in autonomous/engineering systems |
| 4 | Related Work | **Good** | **Poor** | Thorough and verified, but **no JIRS papers cited**. [J1]–[J5] exist and are directly relevant |
| 5 | RQs and contributions | Adequate | **Poor** | Four RQs, all about lifetime prediction and reproducibility. RQ4 is also mis-scoped: three of its four couplings do not have lifetime prediction as their endpoint (the manuscript now admits this) |
| 6 | Dataset | **Good** | Moderate | Cohort now correct (64,516); provenance strong. Does not describe the telemetry datasets at all |
| 7 | Problem formulation | **Strong** | Moderate | Pinball loss, elicitability argument, cluster structure, Mondrian CQR — the most rigorous section. Would need an added formulation for the selection-transfer statistic |
| 8 | Methodology | **Good** | Moderate | Now discloses tuning disparity, untuned ablations and the vendor dependency. Honest and complete |
| 9 | Temporal protocol | **Strong** | **Good** | Table 1 split sizes, verified disjointness, hash-sealed pre-registration. This section is genuinely above field norm and transfers well to JIRS |
| 10 | Results | **Good** | **Poor** | Accurate and well-hedged. But reports **only lifetime** results; omits OPS-SAT, ESA-ADB, conjunction and debris entirely |
| 11 | Exploratory | **Strong** | Moderate | Exemplary segregation of exploratory material, including the `tabicl` counterexample that undercuts its own observation |
| 12 | Discussion | **Good** | **Poor** | Interprets within orbital prediction; no engineering-systems implications, no operator or deployment framing |
| 13 | Threats to validity | **Strong** | **Good** | Candid: n = 7, tune-A size, H2 power, baseline inadequacy, unlogged literature search. This is the manuscript's best section |
| 14 | Reproducibility and data | **Good** | **Good** | Two-level distinction is well made. Carries a `[PENDING EVIDENCE]` marker for the missing deposit — correct, but it is a blocker |
| 15 | Limitations | Adequate | Adequate | 13 items; four duplicate findings the paper elsewhere argues are contributions. Register confusion |
| 16 | Conclusion | **Good** | **Poor** | Supported and appropriately hedged; entirely lifetime-framed |
| 17 | References | **Good** | **Poor** | 38, all Crossref/OpenAlex-verified, preprint status marked, citation counts correctly omitted. **Zero JIRS references** |

## 3. Numerical and consistency verification

I re-checked the manuscript's load-bearing values against artifacts.

| Claim | Manuscript | Artifact | Status |
|---|---|---|---|
| Cohort size | 64,516 rows | 64,516 | ✓ |
| Audit checks | 27 of 28 PASS, 1 FAIL | `counts: {PASS: 27, FAIL: 1}` | ✓ |
| Spearman ρ, both origins | 0.000, n = 7 | `n_models_compared: 7`, ρ = 0.0 | ✓ |
| Split sizes (Table 1) | 20,811/248/332/2,680 · 25,371/1,741/1,560/2,993 · 18,960/211/544/7,281 | matches both summaries and the G5d manifest | ✓ |
| Slice sizes | 198–841 | min 198, max 841 | ✓ |
| Bootstrap draws | 4,000 couplings / 2,000 rolling | `n_boot` 4000 / 2000 | ✓ |
| H2 chance level | 0.199 | **exact enumeration: 686/3456 = 0.1985** | ✓ (and now exact) |
| E12 verdict | NOT REPRODUCIBLE, −0.0514 / +0.0026 | matches `e12_results.json` | ✓ |
| C2 caveats | deployed p = 0.364; uncalibrated p = 0.4115 | matches `phase_e_results.json` | ✓ |
| Loss ratio, arm named | `cosmos_gated` 4.13× / 6.60× | matches `deployed_expert_decomposition` | ✓ |
| T1 over-forecast | 1.51× [1.24, 2.00] | 1.5086 [1.2407, 1.9983] | ✓ |
| Degradation ratios | mlp/tabm 1.75–2.10; xgboost 0.97–1.63; `tabicl` 1.03/1.36 counterexample | recomputed, matches | ✓ |
| Reference list | 38 entries, contiguous, all cited | verified by script | ✓ |

**No numerical discrepancy found. Internal consistency is good.** The abstract, results, discussion
and conclusion now agree, the 17-vs-19-arm convention is stated, and selection failure is
consistently distinguished from generalisation failure (§12.1 explicitly corrects the stronger
phrasing).

**One residual presentation defect:** figures are referenced by filename in a table rather than
embedded with numbered captions, and the caption text lives in `figure_inventory.md` rather than in
the manuscript.

## 4. Presentation assessment (Part 8)

| Dimension | Assessment |
|---|---|
| Abstract quality | **Good** — problem, gap, method, findings, limitation. Well hedged |
| Research motivation | Good for a space venue; **wrong frame for JIRS** |
| Technical depth | **Strong** — estimand, elicitability, cluster inference, conformal construction |
| Mathematical formulation | **Strong** for the lifetime estimand. **Absent** for the selection-transfer statistic, which would be the lead contribution |
| **Architecture diagram** | **MISSING** — and for JIRS this is a real omission. An intelligent-systems paper is expected to show the system |
| **Experimental workflow figure** | **MISSING** — the three-regime temporal protocol would benefit greatly from one |
| Baseline comparison tables | Present for lifetime; **the strong OPS-SAT eleven-arm table is absent** |
| Ablation tables | Present but structurally biased (untuned arms), now disclosed |
| Statistical reporting | **Good** after revision — CIs, BH correction, exact H2 null, power stated |
| Figure readability | Good; Figure 1 verified at 300 dpi with redundant marker/dash encoding for CVD and greyscale |
| Figures from verified data | **✓ Confirmed.** All six generated by scripts from named result JSONs; all postdate their sources. **No manually reconstructed numbers** |
| Units and notation | Consistent; `z`, `CAP`, quantile levels defined |
| Citation quality | **Strong** — all verified, preprints marked, counts omitted. **But zero JIRS citations** |
| Limitations / threats | **Strong** |
| Reproducibility statement | **Good**, two-level |
| Data availability | Present but blocked on the missing DOI |
| Supplementary material | **Strong** — 14 indexed sections, all pointing at real artifacts |

### Recommendations for the six existing figures

| Fig | Current | Recommendation |
|---|---|---|
| 1 | Rank across three origins (slope chart) | **Keep.** Well constructed; the `tabm` exclusion annotation is exactly right. Embed with a numbered caption |
| 2 | Selection transfer, val vs test | **Keep and promote.** With OPS-SAT panels added at ρ = +1.000 and +0.800, this becomes the paper's headline figure |
| 3 | Rank by slice | **Keep**, but add `physics_only` (range 10) and `robust_median_blend` — currently the most and least stable arms are missing from the figure that argues instability |
| 4 | Coverage by slice | **Keep.** Add nominal reference lines |
| 5 | Cap-mass shift | **Demote to supplementary.** It supports a mechanism (H3) that is closed as underpowered; keeping it prominent invites the mechanism reading |
| 6 | Promotion outcomes | **Revise caption** — the binding failure is non-replication at origin 2011, not the coverage criterion |

### Figures that should be added (not decorative)

| New | Content | Justification |
|---|---|---|
| **A** | System architecture: modules, typed contracts, abstention paths, where uncertainty is produced **and where it stops** | JIRS expects a system figure; and drawing where uncertainty stops makes gap U2 visible and honest |
| **B** | Temporal-displacement ladder: ρ against selection→test gap, across regimes | This *is* the lead contribution; it needs a figure |
| **C** | OPS-SAT eleven-arm comparison: AUC-PR with CIs, plus params/latency on a second panel | The positive result, with the compute characterisation JIRS values |

I recommend **no other new figures.** Three additions for three distinct scientific purposes.

### Recommendations for the seven tables

Keep Tables 1 (splits), 2 (selection transfer), 4 (ranks), 5 (refittability) — all load-bearing.
Table 3 should gain the two missing arms. Table 6 (couplings) is correct post-revision. Table 7
(T1, all three arms) is now honest. **Add** an OPS-SAT leaderboard table and a selection-regret
table.

## 5. Ethics, transparency and integrity (Part 9)

| Item | Status |
|---|---|
| Originality / prior-publication overlap | **REQUIRES YOUR CONFIRMATION.** I cannot determine whether any of this has appeared in a thesis, conference paper or preprint |
| Conference-paper overlap | **REQUIRES YOUR CONFIRMATION** |
| Dataset licensing | Recorded for 12 of 15; redistribution rights **must be re-verified at release** |
| Third-party model licensing | **Flagged:** `ultralytics` is AGPL-3.0 (licence-boundary question); Chronos weights must not be redistributed; **`kumo` depends on a commercial vendor library** |
| Author contributions | **REQUIRES YOUR CONFIRMATION** — none fabricated |
| Funding disclosure | **REQUIRES YOUR CONFIRMATION** — none fabricated |
| Conflicts of interest | **REQUIRES YOUR CONFIRMATION** — none fabricated |
| Data availability | Blocked on the DOI |
| Code availability | GitHub repository exists; **visibility unconfirmed**; no licence |
| **AI-tool disclosure** | **REQUIRES YOUR ACTION.** JIRS's author instructions were not retrievable (SSO). Springer Nature requires disclosure of AI use in manuscript preparation and prohibits listing AI as an author. **This project was developed with substantial AI assistance, and that must be disclosed accurately under whatever JIRS's current policy specifies.** You must read the policy and write the disclosure |
| Statistical transparency | **Strong** — power stated, exact nulls given, exploratory material segregated, negative results reported |
| Research integrity | **Strong** — pre-registration sealed and verified, deviations logged separately, four self-corrections recorded including ones that weaken the paper |

**I have fabricated no author details, funding statement, ethical approval or declaration.**

## 6. Summary of required changes

| Severity | Count | Nature |
|---|---|---|
| **Blocking for JIRS** | 3 | Scope reframing; missing OPS-SAT evidence; missing artifact DOI |
| Major | 6 | No JIRS citations; no architecture figure; no intelligent-systems framing in abstract/intro/discussion/conclusion/keywords; selection-transfer statistic unformalised |
| Moderate | 4 | Figures not embedded with captions; Table 3 incomplete; Figure 5 demotion; limitations/contributions register confusion |
| Administrative | 6 | AI disclosure, authorship, funding, conflicts, licences, prior-publication check — **all require you** |

The manuscript's scientific quality is now solid. Its problem is that it is the wrong paper for the
venue you have chosen, and the fix is a reframing supported by evidence the project already owns
plus the two essential experiments. That is the subject of `JIRS_MANUSCRIPT_REVISION_PLAN.md`.
