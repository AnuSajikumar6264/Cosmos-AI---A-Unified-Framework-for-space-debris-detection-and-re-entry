# Final journal-readiness report

Date 2026-11-04 · revision `78ee339`

**Verdict: MAJOR REVISION — now applied. One blocker remains (no benchmark deposit).**

An independent adversarial review was run against the drafted manuscript. It was given the
manuscript and the artifact paths, and deliberately **not** told what I believed the strengths and
weaknesses were. It recomputed the load-bearing numbers from the artifacts itself.

It found real errors. I verified its principal claims independently before acting on any of them,
and **every claim I checked was correct**. The manuscript has been corrected accordingly.

---

## 1. What the review found, and what I verified

| # | Finding | Verified by me | Was | Is |
|---|---|---|---|---|
| 1 | **Cohort size wrong** | ✅ counted the cohort file | 31,396 | **64,516 rows**. 31,396 was the digital twin's live snapshot, 16,386 of which are operator-controlled payloads the manuscript explicitly *excludes* |
| 2 | **Audit count wrong** | ✅ read the audit JSON | 26 of 28 PASS | **27 of 28 PASS, 1 FAIL** |
| 3 | **Headline ρ has the wrong n** | ✅ `n_models_compared: 7` | "over 17 arms" | **n = 7 learners**; 95 % interval ≈ [−0.77, +0.77] |
| 4 | **tune-A sizes never reported** | ✅ read both summaries | absent | **248 / 1,741 / 211** — now Table 1, and named as the leading rival explanation |
| 5 | **Bootstrap draws conflated** | ✅ `n_boot: 2000` | "4,000 draws" blanket | **4,000** couplings/G5d, **2,000** rolling-origin |
| 6 | **E12 refutes C1 and was omitted** | ✅ `conclusion: NOT REPRODUCIBLE` | C1 "PARTIALLY SUPPORTED", E12 cited without its verdict | **C1 NOT REPRODUCIBLE**, reported in the main text |
| 7 | **C2's disqualifying caveats dropped** | ✅ read all three caveats | "is calibration-controlled" | **Retracted.** Deployed arm p = 0.364; uncalibrated contrast p = 0.4115; recalibration effect comparable or larger |
| 8 | **Promotion reason wrong** | ✅ read both criteria sets | "over-covers at 80 %" | **Binding failure is non-replication at origin 2011**; the coverage criterion fails at 90 %, and at 80 % the candidate is *better* |
| 9 | **`tabicl` contradicts the degradation claim** | ✅ computed all seven ratios | "neural and tabular-deep show the opposite pattern" | `tabicl` 1.03/1.36 and `kumo` 1.13/1.17 are **tabular-deep counterexamples**; claim narrowed to `mlp`/`tabm` |
| 10 | **"Prospective" is not prospective** | ✅ only the 2026-10-27 forecast is sealed | "a prospective test" | **pseudo-prospective** — analysis authored after outcomes were available |
| 11 | **T1's over-forecast omitted** | ✅ ratio 1.509, CI [1.241, 1.998] | Brier/ECE/AUC only, one arm | **All three arms**, over-forecast ratio with CI, and the all-zeros Brier reference (0.00220) |
| 12 | **Loss ratio is arm-specific** | ✅ decomposition is the deployed expert's | presented as general | named as `cosmos_gated`; all-arm spread ≈ **1.8×–42×** |
| 13 | **Slice sizes wrong** | ✅ 198…841 | "150–843" | **198–841** |
| 14 | **Ablation arms not retuned** | ✅ `tuned: false` on every ablation | undisclosed | disclosed, with the bias direction stated |
| 15 | **`tabicl`/`kumo` barely tuned** | ✅ `params_n = 1` | "each learner is tuned" | disclosed |
| 16 | **`kumo` is a commercial vendor library** | ✅ `sdm.models.KumoTabular` | undisclosed | disclosed — that arm is irreproducible *in principle* without vendor access |
| 17 | **Mondrian grouping misdescribed** | ✅ `type1 × perigee band` + fallback | "groups defined by orbital regime" | corrected, fallback hierarchy stated |
| 18 | **Romano et al. (2019) uncited** | ✅ the code names it as the method used | absent | cited (verified `arXiv:1905.03222`), plus Vovk (2013) |
| 19 | **Inversion fraction reported one-sided** | ✅ mean between-slice ρ = +0.33 | 23.64 % only | both reported |
| 20 | **Rank table omitted the two key arms** | ✅ `physics_only` range 10, best in 1 | omitted | `physics_only` (range **10**) and `robust_median_blend` (most stable) added |
| 21 | **`mlp` not refittable by the paper's own standard** | ✅ freeze has `torch 2.13.0`, current is `2.14.0` | "2 of 7" | 2 of 7 importable, **1 of 7 matching the recorded environment** |
| 22 | **9 references uncited; citation note unsourced** | ✅ surname scan | 9 uncited | all cited or removed; citation note rewritten from the verification artifact |
| 23 | **No benchmark deposit** | ✅ no DOI/URL/licence anywhere | "are released" | `[PENDING EVIDENCE]` marker; logged as **blocker B-2** |
| 24 | **No external baseline** | ✅ every reference point is internal | undisclosed | disclosed as a material weakness |
| 25 | **RQ4 not answerable by C2–C4** | ✅ their endpoints are not lifetime | implied | scoping admission added; RQ4 rests on C1 alone |

## 2. One place the review overstated, corrected

The review reported the H2 criterion's chance level as **0.83**. That is the probability of the
first clause alone ("no always-present arm retains its rank"). The implemented H2 criterion
requires **both** clauses — no constant arm **and** `physics_only` rank range ≥ 3. My own Monte
Carlo (400,000 draws, realised arm counts 4/4/3):

| Condition | Chance probability |
|---|---|
| No always-present arm retains its rank | 0.833 |
| `physics_only` rank range ≥ 3 | 0.230 |
| **Both — the actual H2 criterion** | **0.199** |

So the correct figure is **0.199**, not 0.83. The review's *conclusion* nevertheless stands and is
the more important point: **0.199 is above the 0.167 at which H3 was closed as underpowered.** The
work applied a power floor to H3 and none to H2, and benefited from the asymmetry.

## 3. How the H2 problem was handled

This needed care, because the H2 verdict was explicitly frozen by the user and was fixed in a
hash-sealed pre-registration.

**What was not done:** the pre-registered verdict was not changed. Reclassifying a pre-registered
outcome after seeing a power calculation that was not pre-specified would defeat the purpose of
sealing the protocol, and would itself be a protocol violation.

**What was done:** the verdict is reported as pre-registered (SUPPORTED), accompanied by the
chance-level calculation, with the manuscript's *prose* corrected so it no longer claims more than
the statistic supports. Specifically removed: "confirmed", "materially stronger epistemic status",
and the framing of origin 2006 as converting the claim "from post-hoc to confirmatory". Replaced
with: a sealed replication of a pattern, with low power to distinguish it from chance, and an
explicit statement that the missing H2 power floor is a defect in our own pre-registration.

This keeps the freeze intact, keeps the pre-registration intact, and removes the inflation.

## 4. The review's recommendation and its reasoning

> **Major revision, and only just.** Reject is defensible today; I would not accept.

Its four reasons for not accepting were: (1) both abstract claims fail on inference rather than
arithmetic; (2) the benchmark's size was quoted from the wrong artifact; (3) a benchmark paper
that does not say where the benchmark is cannot be published; (4) the de-confounding experiment
refutes C1 and was not reported while C1 kept a favourable verdict.

**(1), (2) and (4) are now fixed in the manuscript. (3) is blocker B-2 and requires the author** —
minting a deposit and choosing a licence are not decisions I should make unilaterally.

The review also judged what is genuinely publishable, and I record it because it is the fairest
summary of the project's standing: three strictly ordered temporal origins with archived
per-object predictions; a sealed pre-registration that verifiably predates every fit with splits
matching to the object; mechanically verified temporal ordering and disjointness; a prediction-level
recompute to exactly zero deviation; the prediction-level/training-level reproducibility
distinction; and the honest C4 "joinable pairs: 0" and the §10.5 self-correction. Its assessment
was that "the engineering integrity of the artifact layer is well above the norm for this field",
and that the paper's value "is the artifact plus the discipline, not the strength of the negative
result."

## 5. Readiness status after revision

| | |
|---|---|
| Critical issues preventing submission | **1** — no benchmark deposit (B-2) |
| Numerical errors found by review | **13** |
| Numerical errors remaining | **0** found |
| Omissions that cut against the paper, now reported | **4** (E12/C1, C2 caveats, T1 over-forecast, `tabicl` counterexample) |
| Claim-inflation instances corrected | **7** |
| Automated checks | **27 / 28 PASS**, 0 critical |
| Tests | **217 / 217 PASS** |
| Independent review recommendation | major revision → **applied** |

## 6. What a second review round should check

I did not re-run the adversarial review after applying the corrections, so these are unverified by
an independent reader:

1. Whether the softened §10.1 and §12.1 now *under*-claim — the review warned about over-hedging
   as well, and the corrections moved substantially in the hedging direction.
2. Whether §15's limitations list now duplicates findings the paper argues are contributions. The
   review flagged this (four of ten items); I did not restructure it.
3. Whether the abstract is still within a typical word limit after the added qualifications.
4. Whether the figures should be embedded with numbered captions rather than listed by filename.
5. The two items the review raised that I judged out of scope to fix without the author: the
   deposit (B-2) and a depositable literature-search log (B-3).

## 7. Honest summary

The manuscript I drafted contained errors that an attentive reviewer would have found, and four
of them ran in the direction that flattered the work. The most serious was reporting coupling C1
as partially supported while the experiment designed to test it had returned NOT REPRODUCIBLE and
was cited without its verdict. For a paper whose argument is that the field should report what its
own evidence shows, that was the worst possible error to make, and it was caught by a review
rather than by me.

All of it is now corrected and the corrections are traceable to the artifacts. The paper is
weaker in its claims than the draft was, and better supported.
