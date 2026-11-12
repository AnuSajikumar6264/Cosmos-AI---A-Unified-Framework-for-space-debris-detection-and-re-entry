# JIRS manuscript revision plan

Date 2026-11-04 · **NOT YET APPLIED. The manuscript is unchanged pending your approval**, per your
instruction to complete the audit first.

Objective: the minimum structural and technical change that makes the manuscript a credible JIRS
submission, using evidence the project already owns plus experiments E1–E4.

---

## 1. The decision you have to make first

The revision depends on one choice, and I cannot make it for you.

**Option R1 — Reframe around model-selection reliability in spacecraft intelligent systems.**
Lead with the selection-transfer question (contribution A), evidenced by the OPS-SAT
anomaly-detection result as the positive case and orbital lifetime as the negative case. Requires
experiments **E1 + E2** and a substantial rewrite of §1–§5, §10, §12, §16.

**Option R2 — Keep the lifetime paper and bolt on an intelligent-systems framing.**
Cheaper, and in my assessment likely to fail: a reviewer who reads a catalogue-benchmark paper with
an intelligent-systems abstract will see the seam. It also leaves the project's best positive
result unused.

**My recommendation: R1.** It is more work, but it is the only version that is both honest and
plausibly in scope. The rest of this plan assumes R1.

## 2. Proposed title and framing

> **When can validation-based model selection be trusted in spacecraft intelligent systems?
> Evidence from telemetry anomaly detection and orbital lifetime prediction.**

The paper becomes a **reliability study of machine-learned components in a spacecraft analytics
system**, with:

- a **positive case** — anomaly detection, where selection transfers (ρ = +1.000 adjacent,
  +0.800 time-blocked) and a small late-fusion model beats a time-series foundation model;
- a **negative case** — orbital lifetime, where selection does not transfer (ρ = 0.000) and a
  physics baseline swings from 1st to 17th of 17;
- a **mechanism hypothesis** — transfer degrades with selection→test temporal displacement, tested
  confirmatorily by E2;
- **supporting negatives** — collision risk loses to a trivial baseline; cross-domain fusion not
  demonstrated;
- the **assurance framing** from [J1] (Hawkins et al., JIRS 2023): this is the class of evidence an
  assurance case for a machine-learned satellite component requires.

## 3. Section-by-section revision

| § | Action | Detail |
|---|---|---|
| Title | **Replace** | As above |
| 1 Abstract | **Rewrite** | Lead with the reliability question, not the benchmark. Report both cases. Keep every existing hedge (n = 7, interval, H2 chance level). Name anomaly detection in the first three sentences |
| 2 Keywords | **Replace** | *model selection; temporal distribution shift; condition monitoring; anomaly detection; spacecraft health management; predictive reliability; uncertainty quantification; machine-learning assurance* — mapping to Control and Systems Engineering / AI, not to space science |
| 3 Introduction | **Rewrite** | Motivate from: ML components are entering spacecraft operations; [J1] argues they need assurance cases; assurance requires evidence that the selection procedure predicts deployed behaviour; nobody measures this. Keep the orbital-physics material but **demote it to §6/§7** as task background |
| 4 Related work | **Restructure + add** | New subsection on intelligent-systems reliability citing **[J1] Hawkins 2023, [J2] Spahic 2023, [J3] Zhou 2023, [J4] Harbaoui 2024, [J5] Huang 2023**. Keep the verified external literature. **Add Romano et al. 2019 and Vovk 2013** (already added). Retain preprint markings |
| 5 RQs | **Replace** | RQ1: does validation-based selection predict deployed ranking? RQ2: does transfer degrade with temporal displacement? RQ3: how do a strong learned detector and a trivial/physics baseline compare across tasks? RQ4: what is reproducible, at which level? **Drop the mis-scoped integration RQ**; report integration as a negative result in the discussion |
| 6 Datasets | **Expand** | Add OPS-SAT, ESA-ADB and Kelvins CAC alongside the catalogue data. Keep provenance tables. Keep the 31,396 disclaimer |
| 7 Problem formulation | **Add** | Formalise the selection-transfer statistic: given arms $a$, validation loss $L_v(a)$ and test loss $L_t(a)$, define $\rho = \mathrm{Spearman}(\mathrm{rank}\,L_v, \mathrm{rank}\,L_t)$ and **selection regret** $R = L_t(\hat a) - \min_a L_t(a)$ where $\hat a = \arg\min_a L_v(a)$. Keep the pinball/elicitability material for the lifetime task |
| 8 Methodology | **Expand** | Add the OPS-SAT arms and protocols. Keep the tuning-disparity, untuned-ablation and vendor disclosures |
| 9 Temporal protocol | **Keep and generalise** | This is the strongest section. Generalise to the three-regime ladder (adjacent / time-blocked / forward origins) and add the E2 pre-registration |
| 10 Results | **Restructure** | 10.1 selection transfer across regimes (E2) with CIs and permutation tests; 10.2 selection regret (E5); 10.3 anomaly detection with the time-blocked significance test (E1); 10.4 lifetime instability (existing); 10.5 ranking instability on the sealed fold, with the exact 0.1985 null and the E3 bootstrap reference; 10.6 collision risk vs trivial baseline; 10.7 reproducibility; 10.8 integration negative |
| 11 Exploratory | **Keep** | Retain the `tabicl` counterexample. Move any E2 material that fails pre-registration here |
| 12 Discussion | **Rewrite** | Implications for assuring ML components in spacecraft systems; when a validation split can be trusted; what an assurance case should demand. Connect to [J1]/[J2]. Retain the honest statement that we show absence of reassurance, not absence of signal |
| 13 Threats | **Keep and extend** | Already the best section. Add the E2 confounding discussion and the decision-layer gap |
| 14 Reproducibility | **Revise** | Per-module two-level statement (telemetry refittable; lifetime not). **Insert the DOI** once minted |
| 15 Limitations | **Restructure** | Remove the four items that duplicate findings argued as contributions. Add: decision layer unvalidated; no distribution-free guarantee; no robotics/autonomy loop |
| 16 Conclusion | **Rewrite** | Both cases, the hypothesis, the honest power statement, and the assurance recommendation |
| 17 References | **Extend** | Add [J1]–[J5]. Target ≥ 5 JIRS citations — currently zero |

## 4. Figures and tables

**Add three figures** (justified in the quality audit §4): **A** system architecture showing where
uncertainty is produced *and where it stops*; **B** the temporal-displacement ladder; **C** the
OPS-SAT eleven-arm comparison with compute on a second panel.

**Revise**: Figure 2 gains OPS-SAT panels and becomes the headline; Figure 3 gains `physics_only`
and `robust_median_blend`; Figure 5 moves to supplementary; Figure 6's caption is corrected.
**Embed all figures with numbered captions in the manuscript**, not by filename.

**Add two tables**: OPS-SAT leaderboard (eleven arms, AUC-PR/F1/ECE/params/latency); selection
regret by regime. **Complete Table 3.**

## 5. What must not change

These survived a prior adversarial review and must be preserved verbatim in substance:

- Every power disclosure: n = 7, the ≈[−0.77, +0.77] interval, the tune-A size rival explanation,
  the H2 chance level (now **exactly 0.1985**).
- The E12 **NOT REPRODUCIBLE** verdict refuting coupling C1.
- C2's three caveats, including the retraction of the "calibration-controlled" sentence.
- The corrected promotion reason (non-replication at origin 2011, not coverage).
- The `tabicl` counterexample in the exploratory section.
- The pseudo-prospective terminology and the T1 over-forecast ratio with its CI.
- The §10.5 self-correction about `known5` prevalence.
- The statement that selection failure is **not** generalisation failure.
- The prohibition on claiming a distribution-free coverage guarantee.
- All frozen conclusions: G5d INCONCLUSIVE, H1 NOT_EVALUABLE, H2 SUPPORTED-as-pre-registered
  (never "confirmed"), H3 UNDERPOWERED and CLOSED, and both exploratory labels.

## 6. Sequencing

| Stage | Depends on | Output |
|---|---|---|
| 0 | **Your approval of R1 and of the experiments plan** | — |
| 1 | E3, E5 (near-free) | Corrected H2 reference distribution; regret numbers |
| 2 | E1 | Time-blocked significance test; OPS-SAT score archive persisted |
| 3 | **E2 pre-registration sealed before any fitting** | Protocol hash |
| 4 | E2 executed | The lead contribution |
| 5 | E4 (only if claiming decision support) | Decision-layer evaluation or an honest negative |
| 6 | Stages 1–4 | Manuscript rewrite per §3 |
| 7 | Release plan | DOI inserted, `[PENDING EVIDENCE]` cleared |
| 8 | You | AI disclosure, authorship, funding, conflicts, prior-publication check |

**Do not begin stage 6 before stage 4.** Rewriting around a contribution that E2 has not yet
established would mean writing claims before the evidence exists — the error this project has
otherwise consistently avoided.

## 7. Honest estimate

| | |
|---|---|
| Experiments (E1–E5) | 8–26 GPU-hours + 2–3 days analysis |
| E4, if decision support is claimed | 1–2 days |
| Manuscript rewrite | substantial — roughly 60 % of the text changes |
| Release and DOI | 1 day, plus your licence decisions |
| Administrative | your time |

**This is a major revision of the manuscript, not a polish.** I would not describe the current
document as close to JIRS-ready, and I would not recommend submitting a reframed version before
E1 and E2 have run.
