# Final system and scientific-integrity audit (Phase N)

Date: 2026-11-04 · revision `78ee339` · machine-readable record:
`outputs/final_audit/final_system_audit.json` (+ `.csv`)
Audit script: `scripts/final_system_audit.py` (read-only; installs nothing, modifies nothing)

**Verdict: PARTIAL — 27 of 28 automated checks PASS, 0 critical failures, 1 major.**
(First pass: 26/28. The one minor failure, a stale test count in the living tracker, was
corrected during this phase and the audit re-run.)

No critical issue was found. The project is scientifically submittable **subject to the major
limitations in §3 being stated explicitly in the manuscript**, which is what the frozen
conclusions already do.

A clarification of scope that governs this whole document: a passing audit establishes
*software and bookkeeping integrity* — that the numbers in the documents are the numbers in the
artifacts, that the splits are temporally clean, that nothing frozen has moved. It does **not**
establish that a scientific conclusion is correct. The project's central findings are negative
or inconclusive, and this audit does not change that.

---

## 1. What was checked, and how

Rather than describe the system, the audit **re-derives each load-bearing number from its source
artifact** and compares it to the published value. Every check reports PASS / FAIL /
NOT_EVALUABLE together with the measured quantity, so the audit itself is reproducible:

```
python scripts/final_system_audit.py --out outputs/final_audit
```

### 1.1 Integrity of frozen material (3 checks, all PASS)

| Check | Measured | Status |
|---|---|---|
| Pre-registration freeze (28 files) | 0 files changed | PASS |
| G5d pre-registration hash | `9ea4bf4171cad1b8…` = frozen value | PASS |
| Dated 2026-10-27 forecast digest | every hashed file matches | PASS |

The G5d protocol still hashes to the value recorded *before any model was fitted*. The
confirmatory experiment's pre-registration was never edited; the departures from it are in the
separate `research_design/G5D_DEVIATIONS.md`.

### 1.2 Temporal separation and leakage (9 checks, all PASS)

Checked at all three origins (2006, 2011, 2016), re-deriving the splits from the cohort:

- **Temporal ordering**: `train < train_end ≤ tune < tune_end` and `origin ≤ test < test_end`
  holds at every origin. No training row is dated at or after its origin.
- **Launch-family disjointness between tune-A and tune-B**: 0 families straddle the
  selection/calibration boundary at any origin. The conformal calibration set therefore shares
  no launch family with the set used to pick the model.
- **Test-fold disjointness**: 0 objects appear in two test folds across all three pairs
  (2006/2011, 2006/2016, 2011/2016). Origin 2006's test fold is genuinely new evidence.

### 1.3 Headline claims re-derived from artifacts (11 checks, all PASS)

| Claim as published | Re-derived value | Status |
|---|---|---|
| Published pinball table is recomputable from archived per-object predictions | max absolute deviation **0.000e+00** across both origins and every arm | PASS |
| `physics_only` wins the forward test fold at origin 2011 | rank **1 of 19** | PASS |
| `physics_only` does not win at origin 2016 | rank **19 of 19** (last) | PASS |
| Selection does not transfer: Spearman(tune-A, test) = 0.000 | **0.000** at origin 2011 and **0.000** at origin 2016 | PASS |
| 23.64 % of evaluation-slice pairs have negative rank correlation | **0.2364** | PASS |
| Loss concentrates 4.1×–6.6× below the cap, not at it | **4.13×** (2011), **6.60×** (2016) | PASS |
| G5d overall outcome INCONCLUSIVE | **INCONCLUSIVE** | PASS |
| G5d H2 (ranking instability) SUPPORTED | **SUPPORTED** | PASS |
| G5d H3 not promoted to a confirmation | **UNDERPOWERED** | PASS |
| `physics_only` ranks 1st / 4th / 1st on the common 4-arm set across 2011 / 2016 / 2006 | **{2011: 1, 2016: 4, 2006: 1}** | PASS |

The exact-zero pinball reproduction is the strongest single result here: it means the
leaderboard in the manuscript is arithmetically identical to what the archived predictions
imply, with no rounding, re-scoring or transcription drift.

Note the two different `physics_only` statements are both true and must not be conflated:
**19th of 19** on the full published leaderboard at origin 2016, **4th of 4** on the reduced
arm set that G5d could fit at all three origins. The manuscript must state which set it means
each time.

### 1.4 Reproducibility (2 checks, 1 FAIL)

| Check | Measured | Status |
|---|---|---|
| Prediction-level: archived per-object predictions present for every published origin | 2/2 | PASS |
| Training-level: learners refittable in this environment | **2/7** (`xgboost`, `mlp`) | **FAIL** |

See finding **M-1**.

### 1.5 Internal consistency (3 checks, 1 FAIL)

| Check | Measured | Status |
|---|---|---|
| Mean-elicited endpoint (`rmse_log10`) never drives selection, ranking or a headline | no occurrences in any analysis script | PASS |
| Historical published artifacts retain their original columns | preserved | PASS |
| Living tracker states the current suite size | stated 213, actual **217** | **FAIL** (now fixed, see m-1) |

The `rmse_log10` result deserves a word of precision. The column still exists in the published
CSVs and was deliberately **not** deleted — editing a published artifact to match a later
methodological decision would be worse than the inconsistency it removes. The exclusion is
enforced by *non-use*: no script selects, ranks or reports on it, because a mean-elicited score
is not locally elicitable under fixed-horizon right-censoring. Both properties are checked
mechanically.

### 1.6 Checks performed outside the script

- **Figure traceability**: all five G5 figures (`outputs/g5_figures/*.png`) postdate the result
  JSONs they are drawn from (sources 09:06–09:26, figures 09:27 on 2026-11-04). No figure is
  stale relative to its source.
- **Dashboard sourcing**: no numeric literal with 3+ decimals appears in any console template or
  in `cosmos/ai/dashboard.py` — every displayed metric is read from `ArtifactStore`. The only
  "placeholder" code paths in `cosmos/product/charts.py` render an explicit *"no data"* message
  when an artifact is absent or non-finite; none substitutes a fabricated value.
- **Internal documentation links**: 92 internal links across this work's deliverables
  (`docs/`, `paper/journal/`, `research_design/`) checked, **0 broken**. A further 85 broken links
  exist inside the superseded draft directories; see **M-4**.
- **Dataset provenance**: 15 dataset manifests present. 12 record licence and/or source URLs.
  The three without a licence field are all generated locally — two synthetic
  (`feature1_health/cosmos_synthetic`, `feature3_reentry/simulated`) and one derived
  (`feature3_reentry/processed`); each records its generator and class. See **m-2**.

---

## 2. Critical findings — prevent scientific submission

**None.**

---

## 3. Major findings — require correction or an explicit limitation

### M-1 · Only 2 of 7 learners can be refitted in this environment

**Measured**: `xgboost` and `mlp` import; `lightgbm`, `catboost`, `tabm`, `tabicl` and `kumo`
do not. This is consistent at 2/7 across every document that states it
(`FINAL_REPRODUCIBILITY_REPORT.md`, `LITERATURE_COMPARISON_MATRIX.md:45`,
`MASTER_DECISION_LOG.md:49`, `NOVELTY_AND_CONTRIBUTION_STATEMENT.md:17`,
`RESEARCH_GAP_ANALYSIS.md:86`).

**Why it is major, not critical**: the published numbers are not in doubt — §1.3 recomputes them
exactly from the archived per-object predictions, so the benchmark is fully
**prediction-reproducible**. What cannot be re-executed is *training*, and that includes the arms
that were *selected* at each origin (`kumo` at 2011, `tabm` at 2016). An independent party can
re-score and re-analyse everything; they cannot refit the selected models.

**Required action**: the manuscript must say exactly this, in these terms, and must not describe
the benchmark as fully training-reproducible. The reproducibility statement must distinguish
**prediction-level reproducibility (complete, verified)** from **training-level reproducibility
(2 of 7 learners)**. Installing arbitrary newer backend versions to force an import would not
restore reproducibility — it would silently change the learner and is not a fix.

### M-2 · G5d ran 4 arms, not the 7 pre-registered

**Measured**: `COMMON_ARMS = (physics_only, xgboost, mlp, tabm)` — the arms both present in the
published caches and fittable at origin 2006. This follows directly from M-1 and is logged in
`research_design/G5D_DEVIATIONS.md` (the pre-registration itself was not touched).

**Consequence, already reflected in the frozen conclusions**: H1 is NOT_EVALUABLE (two learners
with a tune-A score is not enough for a rank correlation), and H3 is UNDERPOWERED by the
pre-registered `H3_MIN_ARMS = 5` floor — with 3 arms, ρ = 1.0 arises by chance with probability
1/6, so a numerical pass cannot license a confirmation. The overall outcome is INCONCLUSIVE.

**Required action**: state the arm-set deviation and its power consequence wherever the G5d
result is reported. Do not present H3's favourable sign as support.

### M-3 · Phase F (prospective validation) is BLOCKED by calendar time

**Measured** (`scripts/check_t1_later_snapshot.py`): the hashed forecast is as-of 2026-10-27;
the latest outcome coverage on disk is 2026-10-26, giving **−1 outcome days**. The 30-day
horizon needs a catalogue snapshot dated ≥ **2026-11-26**; 90-day needs ≥ 2027-01-25; 1-year
needs ≥ 2027-10-27. Today is 2026-11-04, so the nearest horizon unlocks in 22 days.

**Why it is major, not critical**: an earlier prospective test **did** complete — T1, as-of
2026-08-16 with follow-up 2026-10-27, scored 13,186 uncontrolled objects (30-day:
`physics_history` Brier 0.00127, ECE 0.00130, AUC-ROC 0.982). So the manuscript is not without
prospective evidence; it is without prospective evidence for the *2026-10-27* forecast.

**Required action**: make the narrower claim that the evidence supports — prospective evaluation
at the 2026-08-16 origin, plus a *registered, hash-verified, not-yet-scored* forecast at
2026-10-27 — and mark the latter `[PENDING EVIDENCE]`. Do not substitute a retrospective fold
for it, and do not hold the manuscript for 22 days.

### M-4 · Stale manuscript drafts in the repository assert withdrawn contributions — **RESOLVED**

**Measured**: three earlier draft directories exist under `paper/`, all dated 2026-11-03 — one day
before the contribution lock. Two assert claims the locked claim set forbids:

| Directory | Withdrawn claim asserted | Occurrences |
|---|---|---|
| `paper/journal_v3_twin/` | satellite **digital twin** contribution | 15 |
| `paper/journal_eaai/` | digital twin **and** integrated cross-domain framework | 10 |
| `paper/journal_v2/` | predates the lock, the reference verification and the reproducibility audit | — |

**Why it is major**: if either draft were submitted or shared by mistake, it would assert
predictive value from cross-domain integration — directly contrary to the standing instruction
*"Phase E did not demonstrate reproducible predictive value from cross-domain integration. Do not
reverse this conclusion through manuscript wording."* The drafts also carry **85 broken figure
references** between them, including an absolute path to a different machine's filesystem, so
they would not build correctly in any case.

**Action taken**: `paper/SUPERSEDED.md` records the status of every draft directory and the
specific withdrawn claims each contains, and a `SUPERSEDED.md` notice was added inside each of
the three directories. The drafts are **retained, not deleted** — they are the record of how the
claim set narrowed as evidence accumulated, and erasing that would be worse than the hazard of
keeping them. The hazard is now explicit instead of latent.

**Link integrity, correctly scoped**: 92 internal links across this work's deliverables
(`docs/`, `paper/journal/`, `research_design/`) — **0 broken**. All 85 broken links are inside the
superseded drafts.

### M-5 · References on disk are not yet independently verified

**Measured**: 35 identifiers in `LITERATURE_REVIEW_2023_2026.md` were retrieved live from
OpenAlex/Crossref/arXiv in the previous session and carry a verification note each. Outside that
file, **~20 identifiers remain unverified**: 11 in `LITERATURE_COMPARISON_MATRIX.md` (6 still
carrying a `[D]` marker), 7 in `PHASE_I_NOVELTY_REVIEW.md`, 2 in `ML_DSGP4_FEASIBILITY.md`.

This corrects an earlier internal estimate of "~71 unverified references". That figure counted
the full Phase I search output, most of which was never written to a file — the on-disk
population needing verification is roughly 20, not 71.

**Required action**: Phase O. Every citation that survives into the manuscript must be resolved
against a live index or dropped. A reference that cannot be resolved must be removed, not
softened.

---

## 4. Minor findings — documentation or presentation

### m-1 · Living tracker stated a stale test count — **FIXED**

`MASTER_RESEARCH_TRACKER.md:4` said "213 passed"; the suite now collects and passes **217**. The
tracker is the one document that is supposed to describe the *current* state, so this was a real
staleness rather than a dated snapshot. Corrected to 217 with the breakdown
(134 pre-product + 34 product + 22 Phase E/H + 11 Phase G+ + 12 G5 + 4 final-evaluation guards).

### m-2 · Derived-dataset manifests do not state inherited upstream terms

`data/feature3_reentry/processed/MANIFEST.json` records its generator and its three inputs
(GCAT `satcat.tsv`, CelesTrak `satcat.csv`, CelesTrak `SW-All.csv`) but carries no licence field,
because it is locally derived. For a data-availability statement it should state the terms it
*inherits* from GCAT and CelesTrak. The two synthetic manifests need no licence but should say so
explicitly.

---

## 5. Informational — no action required

| Item | Note |
|---|---|
| Phase-dated reports state older test counts (134 / 168) | `PRODUCT_BASELINE_AUDIT.md`, `PRODUCT_VALIDATION_REPORT.md`, `PHASE_D_REGRESSION_REPORT.md`, `PHASE_D_STATUS_MATRIX.md`, `DEMO_SCRIPT.md`. These are correctly-dated snapshots of the suite at the time each phase closed, not errors. Only the living tracker had to be current. |
| `rmse_log10` column still present in published CSVs | Deliberate. Exclusion is enforced by non-use, verified mechanically; the published artifact is not edited retroactively. |
| Coupling C4 (health → conjunction) NOT EVALUABLE | No object is observed in both the telemetry and the conjunction corpus. Already documented in `C4_EVALUATION.md`. |
| SPARK dataset not obtained | Every SPARK release is distributed on request through a contact form, and Zenodo record 6599762 is access-restricted. No request was submitted. The manifest records the reason and how to obtain it, and the manifest also notes the dataset does not match the unresolved point-target study even if obtained. No published result depends on it. |
| ML-dSGP4 comparison not attempted | Requires TLE/B\*/ephemeris data the project does not hold. Documented in `ML_DSGP4_FEASIBILITY.md`. |
| Console placeholders | `charts.py` renders explicit "no data" text, never a substituted value. |

---

## 6. What this audit does not establish

Stated plainly so that no reader over-reads a PARTIAL verdict:

1. **Digest checks prove files are unchanged, not that they are correct.** The pre-registration
   freeze shows no one edited the protocol; it says nothing about whether the protocol was wise.
2. **Exact pinball reproduction proves arithmetic fidelity, not scientific validity.** The
   numbers in the manuscript are the numbers in the artifacts. Whether the estimand, the cap, or
   the cohort construction are the right choices is argued elsewhere and is not settled here.
3. **Clean temporal splits rule out one leakage mechanism, not all of them.** Ordering and
   family disjointness are verified; shared upstream feature engineering across origins is a
   design property of the pipeline, not something a split check can falsify.
4. **A passing software audit is not a positive scientific result.** The project's central
   findings remain: selection does not transfer across temporal origins (ρ = 0.000 at both
   published origins), model ranking is unstable (H2 SUPPORTED, `physics_only` 1st → 4th → 1st),
   cross-domain integration showed no reproducible predictive value (Phase E), and G5d is
   INCONCLUSIVE overall. Nothing in Phase N licenses upgrading any of those.

---

## 7. Phase N outcome

| Severity | Count | Disposition |
|---|---|---|
| Critical | 0 | — |
| Major | 5 | M-1, M-2 → explicit limitation; M-3 → narrower claim + `[PENDING EVIDENCE]`; **M-4 → resolved in this phase**; M-5 → Phase O |
| Minor | 2 | m-1 fixed; m-2 to fold into the data-availability statement |
| Informational | 6 | no action |

**Cleared to proceed to Phase O (reference verification).** Two changes were made during this
phase: the stale test count in the living tracker (m-1, 213 → 217), and superseded-draft notices
marking the earlier manuscript directories (M-4). No frozen artifact, published output,
pre-registration or historical result was modified, and no draft was deleted.
