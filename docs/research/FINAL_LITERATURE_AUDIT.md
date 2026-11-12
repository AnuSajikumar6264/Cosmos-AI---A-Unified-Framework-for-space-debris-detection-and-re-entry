# Final literature audit (Phase O)

Date: 2026-11-04 · revision `78ee339`
Evidence: `outputs/final_literature/reference_verification.json`
Harness: `scripts/final_reference_verification.py`
Per-reference results: [FINAL_REFERENCE_VERIFICATION_MATRIX.md](FINAL_REFERENCE_VERIFICATION_MATRIX.md)

**Verdict: the reference base is citable after seven corrections and two deletions. No
contribution claim changes.**

---

## 1. What the audit found

41 candidates were resolved against live Crossref, OpenAlex and arXiv. 37 verified, 3 remain
ambiguous, 1 was a harness artifact.

**Seven references carried a wrong attribution:**

| | Was | Is |
|---|---|---|
| O-1 | Clark & McCracken 2002 | **2001**, J. Econometrics |
| O-2 | Bailey 2014 | **does not exist** → Inoue, Jin & Rossi **2017** |
| O-3 | LiveHouse-TS / Chung 2026 | **Wen et al. 2026**, preprint |
| O-4 | ACM CSUR 2025 selective-prediction survey | **does not exist** |
| O-5 | Taggart 2026 | **Taggart 2022**; primary citation is **Gneiting 2011** |
| O-6 | Siew et al. 2025 | **Rodriguez-Fernandez et al. 2024**; Siew is a co-author |
| O-7 | Massimi 2023, 37 citations | **2024**, 39 citations |

**Two must be dropped rather than softened**: the claimed ACM CSUR survey (O-4) and any
reference to a SpotGEO *challenge paper* — unretrievable in all three indexes across repeated
attempts, so only the dataset deposit (`10.5281/zenodo.3874325`) is citable.

**Two were newly resolved** after previously being recorded as unretrievable: DebrisWatch II
(`arXiv:2605.27516`) and Castet & Saleh 2009 in its journal form (`10.2514/1.42243`).

All corrections have been applied in place to `LITERATURE_COMPARISON_MATRIX.md`,
`PHASE_I_NOVELTY_REVIEW.md`, `NOVELTY_AND_CONTRIBUTION_STATEMENT.md` and
`LITERATURE_REVIEW_2023_2026.md`. No experimental artifact, output or pre-registration was
touched.

## 2. The scale of the problem was smaller than feared

An earlier internal note put the unverified reference count at **~71**. That figure counted the
full Phase I search output, **most of which was never written to a file** — it existed only in a
transcript. The on-disk population needing verification was **~20 identifiers plus the
author-year citations in the positioning documents**, which is what this audit covered in full.

This is worth stating plainly because the inflated figure would have looked, in a readiness
report, like a much larger outstanding risk than it was.

## 3. Why no contribution claim changes

Each corrected reference was checked against the role it plays:

- **O-1, O-2, O-3** support contribution **C-2** by establishing that *selection non-transfer is
  a known phenomenon outside the orbital domain*. Correcting a year, replacing one econometrics
  citation with the paper actually intended, and fixing an author list does not weaken that —
  the phenomenon is still established by peer-reviewed work (Clark & McCracken 2001; Inoue, Jin
  & Rossi 2017; Yao et al. 2022), and C-2's claim is still that **the orbital measurement is a
  domain first**, not that the phenomenon is new.
- **O-4** removed a citation from the set that *closes* evidence-graded abstention. That
  contribution stays closed: Hendrickx et al. 2024 (peer reviewed, Machine Learning, 118
  citations) is a reject-option survey on its own, and the TC-CAD deposit closes the
  domain-specific version. Losing one survey from a list of four does not reopen a contribution
  that was withdrawn.
- **O-5** affects the citation for the elicitability argument that excludes `rmse_log10`. The
  argument is *strengthened*, not weakened: the correct primary citation is **Gneiting 2011**
  (JASA, 1014 citations), a far stronger foundation than a mis-dated 2026 attribution.
- **O-6, O-7** are a co-authorship and a year/count correction in supporting citations. Neither
  carries a claim.

**The direction of every correction is conservative.** Nothing was found that would license
upgrading a claim, and nothing was found that removes the support for a claim already made.

## 4. Two citation disciplines the manuscript must adopt

### 4.1 Drop citation counts entirely

Three counts were already stale when checked (Barber 352→381, Caldas & Soares 53→50, Massimi
37→39). Citation counts in a manuscript are stale by the time it is reviewed, and maintaining
them adds an error surface for no argumentative gain. They are removed.

### 4.2 Label preprints and deposits honestly, including where they close a claim

Twelve verified references are **not peer-reviewed**: Gulrajani & López-Paz, Gibbs & Candès,
Tibshirani et al., Zaffran et al., Angelopoulos et al., SelectiveNet, Wang & Hyndman, ML-dSGP4,
LiveHouse-TS, DebrisWatch II, the TC-CAD deposit, and the spotGEO deposit.

Four hold load-bearing roles. The temporal calibration-failure contribution is withdrawn on
**Zou et al. 2026 (peer reviewed) plus Wang & Hyndman (preprint)**; evidence-graded abstention is
closed partly on the **TC-CAD deposit**. The manuscript must say that, rather than presenting
these closures as uniformly peer-reviewed prior art. Withdrawing a claim on preprint evidence is
the conservative direction and the withdrawals stand — but a reader is entitled to know which
closure rests on what.

Separately, the venue attributions for **Gibbs & Candès, Tibshirani et al., Zaffran et al. and
SelectiveNet** could not be confirmed. These are commonly cited with NeurIPS/ICML venues; only
the arXiv DOIs resolve. Cite the arXiv DOI rather than assert a proceedings venue.

## 5. What Phase O does not establish

- **Metadata verification is not content verification.** Authors, year, venue and title were
  matched for every record. Specific *quoted findings* — Wang & Hyndman's "coverage error
  increases with the forecasting horizon", TC-CAD's "29–33 pp budgeted deferral", Zou et al.'s
  rolling-origin construction, Lu et al.'s "joint coverage 0.892" — were recorded during the
  Phase I search and **were not re-read from full text here**. Both the comparison matrix rows
  that carry such quotes now say so explicitly. Any quoted number that survives into the
  manuscript must be checked against full text at proof stage or paraphrased without the figure.
- **A resolvable reference is not a relevant one.** Whether these works occupy the contribution
  space is the argument in `NOVELTY_AND_CONTRIBUTION_STATEMENT.md`.
- **Absence of a record is not proof of absence of a work.** The SpotGEO challenge paper may
  exist outside all three indexes. The correct response is to cite only what resolves, which is
  what has been done — not to assert the work does not exist.

## 6. Phase O outcome

| Severity | Finding | Disposition |
|---|---|---|
| Major | O-2, O-4: two cited works do not exist | Replaced / dropped. Applied. |
| Major | O-5: elicitability citation mis-dated | Corrected to Taggart 2022 + Gneiting 2011. Applied. |
| Minor | O-1, O-3, O-6, O-7: year, author and count corrections | Applied. |
| Minor | Venue attributions unconfirmed for 4 conformal references | Carried as a citation caution; cite arXiv DOIs. |
| Informational | SpotGEO challenge paper unretrievable | Cite the dataset deposit only. |
| Informational | Quoted findings not re-read from full text | Flagged at both sites; resolve at proof stage. |

**Cleared to proceed to the reproducibility and artifact audit.** No contribution claim was
upgraded, downgraded or reopened by this phase.
