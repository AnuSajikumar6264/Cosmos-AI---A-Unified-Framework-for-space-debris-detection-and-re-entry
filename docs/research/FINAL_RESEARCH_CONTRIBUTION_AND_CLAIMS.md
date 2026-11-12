# Final research contribution and claims — LOCKED

Date: 2026-11-04 · revision `78ee339`
**Status: LOCKED. No claim in this document may be upgraded, reworded towards a stronger reading,
or extended during manuscript writing.**

Supersedes nothing — it *constrains* `NOVELTY_AND_CONTRIBUTION_STATEMENT.md` (rev 2) by fixing
the exact permitted wording, the evidence tier, and the artifact each claim is read from.

Every number below was re-derived from its source artifact by
`scripts/final_system_audit.py` (26/28 checks PASS, 0 critical failures). Every reference was
resolved live by `scripts/final_reference_verification.py`.

---

## 0. Assessment of the proposed framing

You proposed: *"Model-selection instability and generalisation under temporal distribution shift
in orbital lifetime prediction."* You asked whether this accurately represents the evidence.

**It does, with one correction and one caution.**

**It fits.** The three strongest measurements all sit inside it: Spearman(tune-A, test) = 0.000
at both published origins; `physics_only` 1st of 17 at one origin and 17th of 17 at the other;
23.64 % of evaluation-slice pairs rank-inverted. G5d then adds the only confirmatory element the
project has — H2 SUPPORTED on a fold that had never been constructed before the experiment. That
is a coherent single-topic paper, and it is the part of COSMOS-AI that survived scrutiny.

**Correction — "generalisation" overreaches.** The project measures **selection** failure, not
**generalisation** failure. Those differ: models do produce usable forward predictions (the
origin-2011 leaderboard is not degenerate), but the *protocol used to choose among them* carries
no forward information. The project never refitted models per temporal slice, so it cannot speak
to whether retraining would restore transfer. Recommended framing:

> **Model-selection instability under temporal distribution shift in orbital lifetime
> prediction: a catalogue-scale benchmark and a reproducibility failure.**

"Generalisation" should appear only where the evidence is about prediction quality, not about
ranking.

**Caution — the reproducibility finding is a second contribution, not a footnote.** C-3 is
independent of the selection result and, in a benchmark-release paper, is arguably the more
actionable of the two. It belongs in the title or the abstract's first three sentences, not in a
limitations paragraph. Demoting it would also be the self-serving choice, which is reason enough
to keep it visible.

**What the framing must not absorb**: the other six COSMOS-AI modules. Per your instruction, the
health, debris, conjunction, vision and console work appears only as the source of the negative
integration result (C-5), not as claimed contributions.

## 0b. Amendment after independent review (2026-11-04)

This lock was drafted before an independent adversarial review of the manuscript. The review
found real errors, I verified its principal claims against the artifacts, and **every claim I
checked was correct**. Four amendments to this claim set follow, all in the conservative
direction:

1. **C1 is NOT REPRODUCIBLE**, not "partially supported" — its own de-confounding experiment
   (E12) refutes it. An earlier draft reported the favourable single-origin result and cited E12
   without stating its verdict.
2. **The headline selection-transfer correlation is over n = 7 learners, not 17 arms**, which
   bounds it only to roughly [−0.77, +0.77]. The permitted claim is "no detectable transfer", not
   "carries no information".
3. **H2's pre-registered SUPPORTED verdict stands but must not be called a confirmation** —
   chance level 0.199.
4. **C2 carries two disqualifying caveats** that an earlier draft omitted, one of which it
   contradicted.

See [FINAL_JOURNAL_READINESS_REPORT.md](FINAL_JOURNAL_READINESS_REPORT.md) for the full list of 25
findings and their verification status.

## 1. Evidence tiers

Each claim carries a tier. The tier governs the verb the manuscript may use.

| Tier | Meaning | Permitted verbs |
|---|---|---|
| **CONFIRMATORY** | Pre-registered before the evidence existed, evaluated on a never-scored fold | "shows", "demonstrates" |
| **MEASURED** | Computed from archived predictions on forward test folds; not pre-registered | "we measure", "we find", "we report" |
| **EXPLORATORY** | The test leaderboard was inspected before the analysis was designed | "suggests", "is consistent with" — **never** "shows" |
| **NEGATIVE** | A hypothesis the project's own evidence failed to support | "we did not find", "was not demonstrated" |
| **PENDING** | Registered, hash-verified, not yet scoreable | `[PENDING EVIDENCE]` marker, no verb |

A claim may never be stated at a tier above the one assigned here.

## 2. Locked claim set

### C-1 · Catalogue-scale forward-in-time lifetime benchmark — **artifact, MEASURED**

**Permitted statement**: We release a catalogue-scale, forward-in-time benchmark for orbital
lifetime and re-entry prediction with a censoring-aware quantile target
(`z = log10(min(time_days, 1826.25))`, point mass at `z = 3.2616`) and launch-family-clustered
confidence intervals (paired cluster bootstrap, 4000 draws, seed 20261027; Benjamini-Hochberg
within each ablation family).

**Scale**: cohort of **64,516 rows**; test folds 2,680 / 2,993 / 7,281 objects, of which
2,667 / 2,978 / 7,277 are scored, across 435 / 621 / 440 launch families; selection splits
**248 / 1,741 / 211**. Two published temporal origins plus one previously unexamined origin.
*(31,396 is the digital twin's live snapshot, not the benchmark cohort, and must not be quoted as
benchmark scale.)*

**Artifacts**: `outputs/benchmarks/reentry_lifetime/origin{2011,2016}_uncontrolled/`,
`outputs/g5d_origin2006/`.

**Must accompany it**: training-level irreproducibility (§4), and the fact that the benchmark's
own evidence shows its selection protocol carries no forward information (C-2).

### C-2 · Selection non-transfer in orbital lifetime prediction — **domain-first, MEASURED**

**Permitted statement**: On this benchmark, the model-selection protocol standard in this field
carries no information about forward performance.

| Evidence | Value | Artifact |
|---|---|---|
| Spearman(tune-A rank, test rank) | **0.000** at origin 2011 and **0.000** at origin 2016 | `phase_g_lifetime_results.json` |
| `physics_only` rank among 17 point-forecast arms | **1st of 17** at origin 2011; **17th of 17** at origin 2016 | `regression_test.csv` |
| Pairwise rank inversion across 11 launch-epoch slices | **23.64 %** of slice pairs have negative rank correlation | `g5_rolling_results.json` |

**Convention that must be stated**: "17 arms" counts point-forecast arms. The full published
leaderboard has **19** rows including two `marginal_conformal` interval variants, under which
`physics_only` is 1st of 19 and 19th of 19. Both figures are correct; the manuscript must fix one
convention and state it.

**What C-2 does not claim**: that selection non-transfer is a new phenomenon. It is established
outside this domain by Clark & McCracken 2001 (`10.1016/S0304-4076(01)00071-9`), Inoue, Jin &
Rossi 2017 (`10.1016/j.jeconom.2016.03.006`), Gulrajani & López-Paz 2020 (`arXiv:2007.01434`) and
Yao et al. *Wild-Time* 2022. **The measurement in the orbital domain is the contribution.**

### C-3 · Reproducibility failure analysis — **methodological, MEASURED**

**Permitted statement**: Of the seven learners in the published benchmark, two can be refitted in
the declared environment. Five — including the learner **selected at each origin** (`kumo` at
2011, `tabm` at 2016) — cannot: their backends are not declared in any requirements file, and no
software environment was recorded for any published benchmark run. All published values remain
recomputable from archived per-object predictions to exact agreement.

**Strengthened by Phase P**: the five missing backends are all currently on PyPI, so this is a
**declaration failure, not a package-availability failure**; the single environment snapshot
(`venv_freeze_2026-10-24.txt`) does not contain four of them and therefore cannot be the fitting
environment; `cosmos/ai/provenance.py` provides `run_metadata()` and `tracked_run()` and **neither
is called anywhere**. Tuned hyperparameters and seeds *are* recorded per learner.

**Artifact**: `outputs/final_repro_phase_p/final_reproducibility.json`;
`docs/research/FINAL_REPRODUCIBILITY_AND_ARTIFACT_AUDIT.md`.

### C-4 · Narrow measured findings — **MEASURED**

**Permitted statement (a)**: For the deployed expert `cosmos_gated`, pinball loss concentrates
**4.13×** (origin 2011) and **6.60×** (origin 2016) more heavily on objects below the 1826.25-day
cap than on objects at the cap. **The arm must be named**: across all arms the ratio spans roughly
1.8× to 42×. The qualitative direction is general; these two figures are not.
Artifact: `g5_censoring/g5_causal_results.json`.

**Correction locked in**: this supersedes the earlier attribution of the origin-2016 degradation
to a `known5` prevalence difference. `known5` ≈ 1.000 in every split; the real difference is the
at-cap point mass. The superseded attribution must not reappear.

**Permitted statement (b)**: Feature-ablation effects reverse sign **between learners at a single
origin**: the `no_physics` ablation is significant with opposite signs for `mlp` (+0.00661,
q = 0.0163) and `tabm` (−0.00496, q < 0.00025). This same-origin, two-learner result from E12 is
the evidence for C-4(b). The weaker cross-origin version (+0.00225 at 2011, **q = 0.17, not
significant**, against −0.00496 at 2016) must **not** be presented as a demonstrated reversal.

### C-5 · Preserved negative results — **NEGATIVE**

These must be reported, not buried. Each is a result.

| Finding | Exact status | Artifact |
|---|---|---|
| Cross-domain integration provides measurable predictive value | **NOT DEMONSTRATED.** C1 **NOT REPRODUCIBLE** — the E12 same-learner test returns −0.0514 @2011 and +0.0026 @2016, significant at neither origin, signs inconsistent. C2 statistically supported but the **deployed arm shows no gain (p = 0.364)**, the uncalibrated contrast is INCONCLUSIVE (p = 0.4115), and recalibration has a comparable or larger effect. C3 INCONCLUSIVE. C4 **NOT EVALUABLE** (0 joinable pairs). | `phase_e_results.json`, `e12_same_learner/e12_results.json` |
| Point-mass composition shift explains ranking instability | **UNDERPOWERED and CLOSED.** G5d H3: 3 arms against a pre-registered floor of 5; with 3 arms ρ = 1.0 arises by chance with probability 1/6. Do not upgrade. | `g5d_analysis.json` |
| Selection transfers at a third origin | **NOT EVALUABLE** (G5d H1): only two learners had a tune-A score, below the minimum for a rank correlation. | same |
| Ranking is stable across temporal origins | **G5d H2 SUPPORTED as pre-registered**, but with a **chance level of 0.199** at the realised arm counts (Monte Carlo, 400,000 draws) — above the 0.167 at which H3 was closed as underpowered. The verdict stands as pre-registered; it must **not** be described as a confirmation. `physics_only` ranks 1st of 4 / 4th of 4 / 1st of 3. | same |
| G5d overall | **INCONCLUSIVE** per the pre-registered classification table. | same |
| Deployed fusion is the best combiner | **No.** `cosmos_gated` ranks best in **0 of 11** slices (mean rank 5.73, range 2–9) and is beaten by **19.4 %** at origin 2016 by a parameter-free median blend (0.060376 → 0.048644). | `g5_rolling_results.json` |

### C-6 · Registered prospective forecast — **PENDING**

**Permitted statement**: A forecast for the population as of 2026-10-27 is registered and
hash-verified (`outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt`, digest verified intact) and
**has not been scored**. The earliest scoreable horizon (30 days) requires a catalogue snapshot
dated **≥ 2026-11-26**; the latest outcome coverage available is 2026-10-26, giving **−1 outcome
days**. Mark `[PENDING EVIDENCE]`.

**Separately reportable, MEASURED**: prospective evaluation at the earlier **2026-08-16** origin
did complete, with follow-up 2026-10-27 over 13,186 uncontrolled objects. 30-day horizon,
`physics_history`: 29 events against 43.75 expected, Brier **0.00127**, ECE **0.00130**, AUC-ROC
**0.982**, AUC-PR **0.714**. Artifact:
`outputs/benchmarks/twin_prospective_t1/t1_summary.json`.

**The distinction is load-bearing**: the project *has* prospective evidence, at an earlier origin.
It does not have prospective evidence for the registered 2026-10-27 forecast. Conflating the two
would be a misrepresentation.

## 3. Explicitly EXPLORATORY — never stated as findings

These were designed after the test leaderboard had been inspected. They may appear, labelled, in
a discussion section only.

| Observation | Why exploratory |
|---|---|
| XGBoost's tune-A-last / test-first pattern across three origins | leaderboard inspected first |
| Neural degradation 1.75×–2.10× vs XGBoost 0.97×–1.63× | leaderboard inspected first |
| `robust_median_blend` / `robust_mean_blend` improvements | combiners motivated by a diagnosed mechanism after seeing test; **both verdicts are DO NOT PROMOTE** — they fail the accuracy *and* coverage criteria (median blend over-covers at 80 % in 7 of 11 slices) |
| Coverage degrades with distance from the forecast origin | an instance of a published bound (Wang & Hyndman, **preprint**), not an independent finding |
| Per-horizon independent isotonic calibration harms coherence and Brier | design diagnostic; Henzi, Ziegel & Gneiting 2021 is the principled fix |

**Locked constraint**: the rolling-origin analysis did **not** refit models per slice, the slices
are sub-populations of already-scored folds, and slice sizes (198–841 objects) limit power. The
manuscript must say so wherever slice results appear.

## 4. Mandatory accompanying limitations

Every one of these must appear in the manuscript. None may be relegated to supplementary
material.

1. **Training-level irreproducibility** (C-3) — 5 of 7 learners, including both selected
   learners; no environment recorded for any published run.
2. **No prospective evidence for the registered forecast** (C-6) — blocked until 2026-11-26.
3. **G5d arm-set deviation** — 4 arms fitted against 7 pre-registered, which is *why* H1 is
   NOT_EVALUABLE and H3 UNDERPOWERED. Logged in `research_design/G5D_DEVIATIONS.md`; the
   pre-registration itself was never edited and still hashes to `9ea4bf4171cad1b8…`.
4. **Post-hoc status of Phases E, G and H** — all test sets were already scored by earlier
   studies, so these are re-analyses. Recorded in each result file's
   `post_hoc_disclosure` field.
5. **C4 not evaluable** — no object is observed in both the telemetry and conjunction corpora.
6. **Mean-elicited scores excluded** — `rmse_log10` is not locally elicitable under fixed-horizon
   right-censoring (Gneiting 2011; Taggart 2022). The column remains in the published CSVs and
   was deliberately not deleted; exclusion is enforced by non-use and verified mechanically.
7. **Quoted findings from cited works were not re-read from full text** (Phase O §5) — resolve at
   proof stage or paraphrase without the figure.
8. **Four closures rest partly on preprints or deposits** — Wang & Hyndman, ML-dSGP4,
   LiveHouse-TS, DebrisWatch II, and the TC-CAD deposit. State which closure rests on what.

## 5. Withdrawn — may not be revived

| Withdrawn | Closed by |
|---|---|
| Temporal calibration-failure analysis | Zou et al. 2026 (PR); Wang & Hyndman 2024 (PP); Barber et al. 2023 (PR) |
| Evidence-graded abstention | TC-CAD 2026 (deposit); Hendrickx et al. 2024; SelectiveNet; Angelopoulos et al. *Conformal Risk Control* |
| Coherent multi-horizon calibration | Henzi, Ziegel & Gneiting 2021 |
| Integrated cross-domain framework | **our own** Phase E / E12 / G5 |
| Debris detection | Massimi et al. 2024; Blake et al. DebrisWatch I (2021) / II (2026, PP) |
| Satellite digital twin | the 2023–2026 "satellite digital twin" literature is networking work |

**Five contributions retained, six withdrawn.** The user's standing instruction applies: *Phase E
did not demonstrate reproducible predictive value from cross-domain integration. Do not reverse
this conclusion through manuscript wording.*

## 6. Explicitly not claimed

- No novel conformal, calibration or abstention method.
- No priority on overestimation, baseline-beats-complex, or metric-validity findings.
- No validated end-to-end health → lifetime → debris → risk chain.
- No calibrated re-entry probabilities (both readings over-forecast).
- No validated impact-location prediction.
- No independent or external validation.
- No demonstrated benefit from cross-domain coupling.
- No digital-twin or debris-detection contribution.
- No live satellite tracking in the console beyond the real data feeds it reads.
- No Scopus rank or quartile claim unless officially confirmable.
- No claim that the project is "reproducible" without the two-level qualification.

## 7. Paper type

A **benchmark release plus negative-results and reproducibility study**. This is narrower than
the original COSMOS-AI vision and is the form the evidence supports. Both halves have precedent
in this field: Ruszczak et al. 2025 (*Scientific Data*) for the benchmark release, Herrmann et
al. 2024 (*CEAS Space Journal*) for the negative-results and metric-validity genre.

## 8. Lock conditions

This claim set is frozen as of 2026-11-04. It may change only if:

- the user explicitly authorises a change, or
- a new **confirmatory** experiment is pre-registered, executed and analysed, or
- Phase F becomes scoreable on or after 2026-11-26 — which can only *add* C-6 evidence, and
  could equally refute the registered forecast.

Manuscript drafting may select from, compress, and reorder these claims. It may not add to them.
