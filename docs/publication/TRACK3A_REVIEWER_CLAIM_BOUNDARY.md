# Track 3a — reviewer claim boundary

Date 2026-11-05 · the exact set of statements the primary paper may and may not make

Tier: **CONF** pre-registered confirmatory · **SEC** pre-specified secondary (descriptive) ·
**DESC** descriptive from archived outputs · **EXPL** exploratory · **FORBIDDEN**.

---

## 1. Permitted claims

| # | Claim | Tier | Evidence | Required accompanying statement |
|---|---|---|---|---|
| 1 | Selecting the event-level alarm layer on the whole training half outperformed selecting it on the 9-month calibration period on Mission 1 at full channel scale: **+0.353 [+0.206, +0.488], Holm p = 0.0015** | **CONF** | `CONFIRMATORY.json`, freeze `09a98f5e160e` | "A0 and A1 differ in five respects; this is a comparison of two complete protocols and does not isolate a mechanism" |
| 2 | The effect direction and approximate magnitude hold under the **anomaly-only** metric: **+0.3045** | **SEC** | protocol test JSONs | "Point difference only; no interval or p-value computed for the secondary metric" |
| 3 | A supervised deep event scorer (EventTCN, 220,739 parameters) showed **no benefit** over an unsupervised AR(8) forecaster under the same alarm layer and selection: **−0.222 [−0.395, +0.042]** | **CONF** | same | "Refuted against a pre-declared minimum effect of +0.05; not shown to be worse. Seed SD ≈ 0.10 with 5 seeds" |
| 4 | Nor over gradient-boosted trees: **−0.338 [−0.540, −0.033], Holm p = 0.070** | **CONF** | same | Same, plus "neither supervised scorer had a tuning budget, and only one deep architecture was evaluated" |
| 5 | Both refutations hold under the anomaly-only metric (**−0.2112**, **−0.2017**) | **SEC** | protocol test JSONs | As claim 2 |
| 6 | **The alarm layer moves performance about three orders of magnitude more than the scorer.** Within A1 on M1, layers span 0.0001 → 0.4278; across scorers under the best layer, 0.2054 → 0.5436 | **DESC** | protocol test JSONs | "Descriptive across archived configurations; not a pre-registered contrast" |
| 7 | **Point-level adaptive conformal inference cannot produce a usable event-level alarm layer.** It attains the highest anomaly recall of any configuration (**0.9273**) and an F0.5 of 0.0001, because it raises **1,383,948 alarm runs** and **176,337 false alarms/year**, against 123 runs and **1.1/year** for the event-level BH layer | **DESC** | protocol test JSONs | "The γ of the ACI comparator was tuned to a point rate, not the event objective" |
| 8 | **Mission 2 cannot discriminate anomaly-detection methods.** Its test half holds 6 anomalies and 356 rare events; arm A1 raises 238 alarms and detects **zero** anomalies (anomaly-only F0.5 = 0.0000, precision 0, recall 0); every learned arm at M2 lightweight scores **exactly 0.0000** on anomaly-only | **SEC / DESC** | protocol test JSONs, `results.csv` | "Therefore the reversal of H6 on Mission 2 is not evidence against generalisation; Mission 2 cannot test it" |
| 9 | The composite metric **overstates** Mission 2 performance by roughly **6×** relative to anomaly-only (0.87–0.96 vs 0.00–0.18 across arms) | **DESC** | protocol test JSONs | — |
| 10 | A parameter-free out-of-limit rule scores **0.9648 composite but 0.0877 anomaly-only** on M2 lightweight, with 3,162 rare-event-only runs | **DESC** | `results.csv` | "Its composite success is rare-event detection" |
| 11 | **Cross-fitting over-estimated test performance on the lightweight Mission 1 subset by a factor of 21** (selection 0.528 → test 0.025) | **DESC** | protocol test JSONs | "Single arm, single subset; forward chaining was not performed, so cross-fitting and subset difficulty are not separated" |
| 12 | The identity of the best Mission 1 arm is **metric-dependent**: A2 under composite (0.5436), A1 under anomaly-only (0.3361) | **DESC** | protocol test JSONs | "Margin 0.0094, inside A2's seed spread of ±0.169; neither ordering is established" |
| 13 | Selection score predicts test ordering **better on Mission 1 than Mission 2** (per-run ρ +0.455 vs −0.118 composite; +0.364 vs −0.465 anomaly-only) | **EXPL** | protocol test JSONs | "Arm-level ρ of ±1.000 is at chance level with n = 3 arms (p = 1/6); no CI computed" |
| 14 | The ported official GlobalSTD reproduces published values to within **0.001 in all 8 configurations**, and the vendored official metric files are **byte-identical to upstream commit `67194d3`** | **DESC** | `results.csv`, DMLR Table 4, tarball comparison | — |
| 15 | An independent read-only code audit found **no path by which test-half labels reach any model, score, calibration pool or selection** | **DESC** | `STAGE1_AUDIT.md` §5.2 | "Residual input-only flows are quantified and judged negligible; the official 'restore' step moves annotated samples onto grid points, with zero effect on M1 detections" |

## 2. Forbidden claims

| # | Claim | Why forbidden |
|---|---|---|
| 1 | Any statement that COSMOS-AI's absolute performance is competitive with, or superior to, published results on ESA-ADB M1 | **Brancato et al. (AST 180:113957) report 0.902 where COSMOS-AI's best is ~0.09–0.20, and their parameter-free reference scores 0.754 against COSMOS-AI's 0.0007.** The out-of-limit gap is explained (different estimators — empirical training-range envelope vs operational limits), the **method gap is not**. Blocked on paywalled full text |
| 2 | That H6 identifies *which* design choice causes the improvement | Five simultaneous differences. The post-hoc decomposition is one-factor-at-a-time, cannot identify interactions, and was run on test halves already seen |
| 3 | That the selection effect **generalises** across missions, channel sets or layers | Reverses on M2 and on the lightweight M1 subset; **1 of 8 cells is confirmatory**. M2 cannot test it (claim 8); Mission 3 has no official split, its authors advise against it, and it holds 8 anomalies and 25 rare events in total |
| 4 | That the study is a clean confirmatory test | **Both test halves were scored in 128 configuration–layer combinations during the exploratory phase, before the pre-registered protocol was designed.** The project's own words: *"the pre-registration was motivated by a test result"* |
| 5 | Evidence-graded abstention, budgeted deferral, or operator-workload budgets as a contribution | **Pre-empted.** TC-CAD (Zenodo `10.5281/zenodo.23322711`) has conformal layers, a deferral layer and operator budgets; Heydari et al. (IEEE Access 2026, `10.1109/ACCESS.2026.3714708`) has workload budgets. The project's own novelty note: *"Do not build the paper on this"* |
| 6 | That the deep scorer is **worse** than the simpler scorers | H4 is refuted against a +0.05 minimum effect and **"not shown worse"** — its CI [−0.395, +0.042] includes zero. H5's Holm p = 0.070 does not clear 0.05 |
| 7 | That the bootstrap intervals come from the official metric | They come from a **re-implementation** that differs in three ways (events reduced to one [min, max] span although 81 of 91 M1 test events have several intervals; off-grid events undetectable; TNR from sample counts not seconds). It is exact for A1, all A3 seeds and all M2 arms, and changes **no verdict** (H5 −0.330 vs −0.338; H6 +0.352 vs +0.353) — but it must be described as an approximation |
| 8 | That the freeze guarantees provenance of everything | **The gate covers code only** — not the freeze record, selection JSONs, OOF outputs, the test driver, or library versions. The A1 selection files predate the last edit of `oof_benchmark.py` and were not re-run; their grids and argmax match the frozen rule, but provenance cannot be attested |
| 9 | Any comparison with Brancato, Fejjari or Dai on the basis of their methods | **Full texts not obtained.** Metadata verified only; no abstracts available from Crossref for any of the three |
| 10 | That the primary calibrator is the best alarm layer | For A2 on M1, `threshold` beats `conformal_bh` (0.6134 vs 0.5436 composite). `conformal_bh` is the **pre-registered primary**, not the empirical best |
| 11 | Equal-footing comparison with the ACI comparator | Its γ was tuned to a point rate, not the event objective. With γ = 0.05 each channel is silenced for 80 steps after an exceedance |

## 3. Mandatory disclosures

Every one must appear in the paper. None may be relegated to supplementary material.

1. **H6 compares two complete protocols differing in five respects; no mechanism is isolated.**
2. **The pre-registration was motivated by a test result**; both test halves had been scored in 128
   configuration–layer combinations beforehand.
3. **Only 1 of 8 cells is confirmatory**; the effect reverses on Mission 2 and on the lightweight
   Mission 1 subset.
4. **Mission 2 cannot discriminate anomaly-detection methods** — 6 anomalies, A1 at zero.
5. **The bootstrap is an approximation** of the official metric; differences stated; no verdict
   changes.
6. **Neither supervised scorer had a tuning budget**; one deep architecture; the ACI comparator's γ
   was tuned to a different objective.
7. **Seed variance is large** — trees 0.157–0.769, TCN 0.085–0.358 with 5 seeds, so arm means are
   uncertain to about ±0.1 against a +0.05 minimum effect.
8. **The freeze gate covers code only**; A1 selection files predate the frozen code.
9. **The official "restore" step** moves annotated test samples onto grid points, so test labels
   shape test inputs. Benchmark-inherent; zero effect on M1 detections; **not mentioned in the
   pre-registration**.
10. **Cross-fitting, not forward chaining**; optimism quantified at 21× on lightweight M1.
11. **No absolute-performance comparison with published results is made**, and why.

## 4. The three questions a reviewer will ask, and the answers available today

| Question | Answer available? |
|---|---|
| *"Brancato reports 0.902 — why do you report 0.09?"* | **Partial.** The out-of-limit reference gap is explained as a definitional difference between estimators. The method gap is **not**, and cannot be without their full text. **The paper must pre-empt this by making no comparative claim and stating the discrepancy openly**, including that an independent third effort (TC-CAD, 0.090) lands in COSMOS-AI's range |
| *"Your headline compares two protocols differing five ways — what causes it?"* | **No.** Disclosed, not answered. Requires 3b |
| *"Your effect reverses on Mission 2 — does it generalise?"* | **Yes, now.** Mission 2 cannot test the question: 6 anomalies; A1 detects zero while raising 238 alarms; every learned arm at exactly 0.0000 on anomaly-only. **3a converted this from a damaging reversal into a characterised limitation of the benchmark** |

## 5. Recommended framing sentence

> On Mission 1 of ESA-ADB at full channel scale, the data used to select an event-level alarm layer
> changed detection performance by +0.353 event-wise F0.5 [+0.206, +0.488] under a pre-registered
> frozen rule, while replacing an unsupervised forecaster with a 220,739-parameter supervised
> temporal convolutional scorer did not improve it. Across archived configurations the alarm layer
> accounts for about three orders of magnitude more variation than the scorer, and point-level
> adaptive conformal calibration — which attains the highest anomaly recall we measured, 0.927 —
> is unusable at the event level because it raises 176,337 false alarms per year. We make no claim
> about absolute performance relative to published results, and we report that the selection effect
> reverses on Mission 2, where the benchmark cannot discriminate methods.

Every clause is sourced, tiered and permitted above.
