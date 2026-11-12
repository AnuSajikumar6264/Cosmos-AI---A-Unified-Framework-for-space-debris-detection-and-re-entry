# JIRS simulated peer review — round 2 (Part F)

Date 2026-11-04 · conducted after E3 and E5 completed

**Subject of review:** the *reframed* paper proposed in `JIRS_MANUSCRIPT_REVISION_PLAN.md` —
model-selection reliability in spacecraft intelligent systems, led by selection regret, evidenced
by OPS-SAT anomaly detection and orbital lifetime prediction — **as it would stand today**, i.e.
with E3 and E5 complete but **without** E1, E2 or E6.

This is deliberately the hardest version of the question: what would a JIRS reviewer say if we
submitted the reframed paper now, rather than after the remaining experiments?

---

## 1. Novelty compared with recent JIRS publications

**Assessment: adequate but not strong, and dependent on an experiment not yet run.**

The reframing genuinely engages JIRS's own literature. Hawkins et al. (2023,
`10.1007/s10846-023-01905-3`) argue that a machine-learned satellite component requires a safety
assurance case; this paper supplies a class of evidence such a case needs and nobody has measured —
whether the validation procedure used to select the component predicts its deployed ranking. That
is a legitimate gap, and I verified it is not occupied in the journal's recent output.

**But the central mechanism claim is not established.** The ρ = +1.000 / +0.800 / 0.000 ordering is
exploratory, post hoc, confounded across dataset, task, metric and model family, and rests on
n = 5 and n = 7. The authors say all of this. Saying it does not make it a contribution. Without
the pre-registered ladder (their E2), what remains is an observation and a hypothesis.

The regret result is better. Selection regret of 3.40 % → 18.72 % → 25.15 % across origins, with
the origin-2016 interval excluding zero and zero-regret in 0 of 4,000 resamples, is a real,
significant, operationally legible finding. **This is the paper's strongest card and it was not in
the original manuscript.**

**Minor concern:** the paper would be the journal's only paper on orbital mechanics, and the
authors should expect reviewers without domain background.

## 2. Technical contribution of the late-fusion model

**Assessment: NOT ESTABLISHED. This is my most serious concern, and the authors have already
found it themselves.**

The hybrid is described as a late fusion of a 1-D CNN branch and a feature-MLP branch. Against its
own branches:

- `cnn` is **better** on the official protocol (AUC-PR 0.9870 vs 0.9855).
- The time-blocked margin over `cnn` is **+0.0007** — meaningless, and untested.
- The margin over `fcnn` is +0.0059 with CI lower bound 0.0004 — significant but marginal, and on
  the official protocol only.

**An architecture whose fused form does not beat its own best branch has not demonstrated that the
fusion does anything.** The authors' own assessment concedes this and restates the claim as one
about calibration (ECE 0.035 vs 0.121) and seed stability (F1 std 0.0066 vs 0.0977). Those are
large, real differences — 3.5× and 15× — and a reliability claim is more defensible than an
accuracy claim.

But as submitted today that restated claim is **also untested**: no significance test exists for
the calibration or variance differences, and no branch ablation attributes them to the fusion
rather than to one branch. **I would require their E6 before accepting any architectural claim.**

I note with approval that the authors do **not** call this physics-informed. It is CNN+MLP late
fusion and they say so.

## 3. Quality of satellite anomaly-detection evaluation

**Assessment: good data, incomplete evaluation.**

Strengths: eleven arms across five method families on one fixed protocol; a protocol fixed before
any test number was seen; five seeds; a label-efficiency sweep (10/25/50/100 %); a time-blocked
protocol that corrects the official split's temporal interleaving; calibration reported alongside
accuracy; and a modern time-series foundation model as a comparator.

Concerns:

1. **The significance tests use the wrong protocol.** Every paired comparison is computed on the
   official (temporally interleaved) split. The time-blocked protocol — the one the authors
   themselves argue is honest — carries **no significance test at all**. The headline "beats a
   foundation model" claim is therefore tested only where it matters least.
2. **The test set is small.** 529 fragments official, 531 time-blocked. An AUC-PR margin of +0.0059
   on 529 samples is fragile regardless of its p-value.
3. **One decision threshold.** All supervised arms decide at `P ≥ 0.5`. No threshold sweep, no
   matched-false-alarm comparison, no explicit missed-anomaly rate. For an operational monitoring
   paper this is a real omission, and the authors note it is computable from saved scores.
4. **The score archive is missing.** `test_scores_official.npz` is referenced by the reporting code
   and absent from disk, so the published paired comparison **cannot currently be re-derived**.
5. **No reconstruction-based baseline**, the one standard family absent from an otherwise
   comprehensive set.

## 4. Temporal robustness

**Assessment: the strongest aspect of the work.**

Verified mechanically: temporal ordering at all three origins; zero launch families straddling the
selection and calibration splits; zero objects shared between test folds; an origin whose test fold
was hash-sealed before any model was fitted, with realised split sizes matching the registration to
the object.

The time-blocked anomaly-detection protocol is the right control and the hybrid's advantage
survives it. Coverage instability is measured honestly (0.572–0.960 at the 80 % level) rather than
smoothed over.

**One residual concern the authors have not addressed:** origins 2006, 2011 and 2016 sit at
different phases of the solar cycle, which plausibly contributes to the cross-origin instability
the paper attributes to temporal displacement in general. This is a physical confound and it is not
discussed. For a paper whose thesis is about temporal shift, I would expect at least an
acknowledgement.

## 5. Statistical reliability

**Assessment: substantially improved by E3 and E5, and now above the norm for this journal.**

What I find creditable, unusually so:

- The authors computed the **exact** chance level of their own pre-registered criterion by
  enumerating all 3,456 configurations — 0.1985 — and reported that it **exceeds** the 0.1667
  threshold at which they closed a different hypothesis as underpowered. They then declined to call
  their own result a confirmation.
- They **decomposed their own criterion** and found it consists of one near-vacuous clause
  (rank-constancy, satisfied 83 % of the time by chance; mean 0.25 constant arms under resampling)
  and one robust clause (physics rank range ≥ 3, holding in **98.9 %** of resamples). They now rest
  the claim on the robust half only.
- They **corrected their own framing** of E3, having proposed it as "the correct null" and then
  reporting that what they computed is a robustness check, not a null, because it preserves the
  genuine cross-origin differences. A stability-constrained null requires a modelling assumption
  they declined to make silently.

That is better statistical conduct than I usually see.

Remaining concerns: the headline ρ still rests on n = 7 with no permutation test; the lifetime
leaderboard still carries no per-arm intervals; regret is significant at **one** of three origins;
and the three-origin monotonicity is three points.

## 6. Computational efficiency

**Assessment: good coverage, compromised measurement.**

Parameters, checkpoint size, peak memory, throughput, training time and per-fragment latency are
recorded across arms, and the result is favourable — the best detector is 74k parameters at
0.0045 ms/fragment. For an intelligent-systems venue that is a deployability argument worth making.

**But the measurement conditions are not documented.** The single latency figure conflates batch-1
and batched inference (the prediction path defaults to batch 512), no hardware, thread count or
batch size is recorded, CPU inference is not measured at all, and model-only latency is not
separated from end-to-end. Comparative efficiency claims therefore rest on undocumented conditions.

I note approvingly that no energy-efficiency and no real-time claim is made.

## 7. Reproducibility and dataset availability

**Assessment: one fatal gap, otherwise exemplary.**

**Fatal:** there is **no DOI, no archival deposit, no release and no licence.** I cannot review a
benchmark I cannot obtain. This alone justifies rejection of a benchmark paper.

Otherwise the handling is the best I have encountered in this area: prediction-level
reproducibility verified to exactly 0.000e+00; a two-level distinction maintained per module
(telemetry refittable, lifetime not); five undeclared backends disclosed, including one that is a
commercial vendor library and therefore irreproducible in principle; a provenance module that
exists and was never called, reported as the proximate cause; and the observation that the
reproducibility gap **cut their own pre-registered experiment from seven learners to two**, which
is why two of its three hypotheses are unevaluable. Most authors would have buried that.

There is also an unresolved licence question — `ultralytics` is AGPL-3.0 against an unspecified
repository licence — that must be settled before release.

## 8. Practical significance

**Assessment: materially improved, and now the paper's best argument.**

Before E5 the paper said a rank correlation was zero. After E5 it says that following the standard
selection procedure costs **18.7 % more loss than the best available arm at one origin (CI
excluding zero), up to 25 % within the deployed pool, and up to 83 % against the full arm set** —
and that at two of three origins the procedure selected the **worst** arm in its own pool.

That is a statement an engineer can act on, and it converts an abstract methodological point into
a cost. Combined with the detector's 74k-parameter footprint, the paper has two genuinely practical
findings.

The practical claim is weakened by the absence of any decision-layer evaluation: the system
produces prioritised outputs and nothing establishes the prioritisation is good. The authors
correctly refuse to claim otherwise.

---

## Overall recommendation

### **MAJOR REVISION** — not rejection, and not acceptance

The reframing moves this from "wrong journal" to "right journal, incomplete evidence". The paper
now engages JIRS's literature, has a positive intelligent-monitoring result, a significant
operational cost finding, and statistical conduct above the journal's norm.

It is not acceptable today because two of its three central claims are unestablished:

1. **The architectural contribution does not survive comparison with its own branches** (§2).
2. **The lead mechanism claim is exploratory and confounded** (§1).
3. **The artifact does not exist** (§7).

## The strongest possible rejection argument

> **The paper's two headline contributions are each undercut by the authors' own evidence.**
>
> The late-fusion architecture does not outperform its own CNN branch — `cnn` is better on the
> official protocol and the time-blocked margin is +0.0007 — so the architectural contribution is
> unsupported. And the selection-transfer mechanism that frames the paper is explicitly
> exploratory, post hoc, and confounded across dataset, task, metric and model family, on n = 5
> and n = 7. What remains established is a set of negative results about orbital lifetime
> prediction, a detector that ties its own ablation, and a benchmark that cannot be downloaded.
> The honesty is admirable; the contribution is thin.

This is the argument I would write if asked to reject, and I believe it is the strongest available.
Note that it is constructed almost entirely from the authors' own disclosures — which is a hazard
of unusually candid reporting, and not a reason to report less candidly.

## Minimum additional work to address it

Three experiments, in this order. None requires new data; none touches a frozen artifact.

| # | Work | Addresses | Cost |
|---|---|---|---|
| **1** | **E6 — fusion-branch ablation** (CNN-only, MLP-only, fusion), scored on accuracy **and** calibration **and** seed variance, with significance tests | §2, the strongest rejection ground. **Either establishes a reliability contribution for the fusion, or tells the authors to drop the architectural claim before a reviewer does** | 2–4 GPU-h |
| **2** | **E1 — time-blocked significance tests** for all arms, persisting the score archive; then **B1 — threshold sweep and matched-false-alarm comparison** | §3 concerns 1, 3, 4; §7's missing archive | 2–6 GPU-h + hours |
| **3** | **E2 — pre-registered temporal-displacement ladder** within a single dataset, holding task, metric and model family fixed | §1, the confounding objection — converts the lead claim from exploratory to confirmatory | 6–20 GPU-h |

Plus two non-experimental requirements: **deposit the benchmark and obtain a DOI** (§7), and
**acknowledge the solar-cycle confound** (§4).

**If all three experiments are completed and the artifact is deposited, I would expect to
recommend acceptance** — provided the architectural claim is restated according to whatever E6
actually shows, rather than according to what the authors hope it shows.

---

## Note on what changed between review rounds

Round 1 reviewed the original manuscript and predicted desk rejection on scope, with two of three
reviewers rejecting outright. Round 2 reviews the reframed paper with E3 and E5 complete and
reaches major revision.

The difference was produced by: the reframing, two analyses requiring **no model fitting**, and
three self-corrections that each **weakened** a claim — the H2 criterion decomposition, the E3
framing retraction, and the concession that the fusion does not beat its own branch on accuracy.

The project's trajectory is improving because its authors keep finding their own problems. The
remaining risk is that the last of those problems — the architectural claim — is settled by E6
before the manuscript is written around it.
