# Track 3a — event-level alarm selection and selection stability

Date 2026-11-05 · all values from archived outputs · **pre-registered protocol and verdicts
unmodified**

**Headline: the selection→test rank correlation is +1.000 on Mission 1 and −1.000 on Mission 2
(n = 3 arms each). Cross-validation over-estimated the lightweight Mission 1 subset by a factor of
21 (0.528 → 0.025). Selection stability is the finding; it is not yet an established mechanism.**

---

## 1. What "selection" means here

Two distinct selection operations are involved, and conflating them is the main interpretive risk.

| Operation | What is chosen | Where |
|---|---|---|
| **Alarm-layer selection** | the operating point of the event-level alarm layer — level, *k*, merge window — chosen by cross-fitting on labelled training data | `oof_benchmark.select`, frozen |
| **Arm selection** | which *scorer* to deploy (AR(8) vs trees vs TCN) | not part of the pre-registered protocol; examined descriptively here |

**H6 concerns the first**: A0 selects the alarm layer on a 9-month calibration period; A1 selects
it on the whole training half. §3 of this report concerns the second.

## 2. Selection stability of the alarm layer — the pre-registered result, preserved

| Contrast | Mission | Effect | 95 % CI | Holm p | Verdict |
|---|---|---|---|---|---|
| **H6: A1 − A0** | 1 (target, 58 ch.) | **+0.353** | [+0.206, +0.488] | **0.0015** | **supported** |
| H6: A1 − A0 | 2 (target, 47 ch.) | −0.089 | [−0.143, −0.049] | — | replication, no inference |

**Unchanged and authoritative.** Anomaly-only companion values: +0.3045 (M1), −0.1471 (M2).

**What it establishes:** selecting the event-level alarm layer on the whole training half
outperformed selecting it on the 9-month calibration period, on Mission 1 at full channel scale,
under the primary calibrator, by a frozen rule with a pre-declared minimum effect of +0.05.

**What it does not establish — stated wherever H6 appears:** A0 and A1 differ in **five** respects
simultaneously, so no single mechanism is attributable. The project's own independent code audit
identified the fifth difference, which the thesis had recorded as four:

| # | Difference | A0 | A1 |
|---|---|---|---|
| 1 | Forecaster fit data | `fit` period only | all nominal training samples, all 8 lags |
| 2 | **Residual scale σ** *(found by the code audit)* | out-of-sample on the 3-month `es` period | in-sample over the whole training half; per-fold σ for OOF. **Per-channel ratio median 1.007, range 0.52–4.70; 37 of 58 M1 channels at the σ floor** |
| 3 | Calibration pool | 792,000 rows, from the model that scores test | **7,364,161** OOF rows from five fold models with different σ |
| 4 | **Selection data** | **9 M1 events** (7 anomalies, 2 rare) | **105 M1 events** (+4 gaps) |
| 5 | Grid | 4 × 4 | 4 × 5 |

A post-hoc one-factor-at-a-time decomposition attributed the effect to difference 4 (selection
data). **That is not a factorial design, so interactions are unidentified**, and it was run on test
halves already seen. Attribution requires experiment 3b.

## 3. Arm selection: does the selection score predict test performance?

Descriptive, exploratory. Computed from archived `cv_EW_F0.5` (the cross-fit selection score) and
test scores, under `conformal_bh`.

### 3.1 Arm-level rank correlation

| Mission | Arm | Selection score (cv) | Test score | | Spearman(cv, test) |
|---|---|---|---|---|---|
| **1** | A2 | 0.7273 | 0.5436 | | |
| **1** | A1 | 0.6237 | 0.4278 | | **+1.000** (composite) |
| **1** | A3 | 0.5362 | 0.2054 | | **+0.500** (anomaly-only) |
| **2** | A1 | 0.9189 | 0.8735 | | |
| **2** | A3 | 0.9062 | 0.8749 | | **−1.000** (composite) |
| **2** | A2 | 0.8898 | 0.9039 | | **−0.500** (anomaly-only) |

**Per-run correlations** (all seeds, n = 11 runs per mission — better powered than n = 3 arms):

| Mission | Composite ρ | Anomaly-only ρ |
|---|---|---|
| 1 | **+0.455** | +0.364 |
| 2 | **−0.118** | −0.465 |

### 3.2 Honest statement of what this is worth

**The arm-level ±1.000 values are at chance level.** With three arms, Spearman's ρ takes only
{−1, −0.5, +0.5, +1}, and |ρ| = 1 occurs with probability 1/6 under random ordering. So "+1.000 on
Mission 1" and "−1.000 on Mission 2" are each individually unsurprising.

**The per-run correlations are the usable figures**: +0.455 on Mission 1 and −0.118 on Mission 2
(composite), over 11 runs each. Those are weak-positive and essentially null respectively, and
neither carries a confidence interval here.

**What survives:** selection score predicts test ordering **better on Mission 1 than on Mission
2**, in both the arm-level and per-run views, under both metrics. The direction of that difference
is consistent across four independent measurements. The magnitude is not established.

**What does not survive:** any claim that selection "perfectly predicts" or "anti-predicts" test
performance. Both readings are artefacts of n = 3.

## 4. Cross-fitting optimism — the strongest stability finding

Archived values for A1 under `conformal_bh`:

| Channel set | Selection score (cv) | **Test score** | Optimism ratio |
|---|---|---|---|
| M1 **target** (58 ch.) | 0.6237 | **0.4278** | 1.5× |
| M1 **lightweight** | 0.5278 | **0.0247** | **21.4×** |

**On the lightweight Mission 1 subset, cross-fitting over-estimated test performance by a factor
of 21.** The selection procedure reported 0.528 and the arm delivered 0.025.

This independently reproduces the figure recorded in the project's own risk register
(*"CV over-estimates test performance strongly for the supervised arms and for lightweight M1
(0.528 → 0.025)"*) and it is, in my assessment, **the most important selection-stability result in
the track** — more useful than H6, because:

1. It is a *within-arm* comparison, so it is not confounded by five protocol differences.
2. It quantifies the failure of the selection procedure itself, which is the paper's subject.
3. It explains the lightweight-subset reversal mechanically: the selection score did not
   collapse, the test score did.
4. It is a cautionary result a practitioner can act on.

**Caveat:** a single arm on a single subset. Forward chaining was not performed, so the optimism is
quantified but its cause (cross-fitting vs subset difficulty) is not separated.

## 5. The alarm layer dominates the scorer

A1, Mission 1, across alarm layers — the spread within one scorer:

| Layer | Composite | Anomaly-only | False alarms/year | Alarm runs |
|---|---|---|---|---|
| `threshold` | 0.4278 | 0.3361 | 1.1 | 90 |
| `conformal_bh` | 0.4278 | 0.3361 | 1.1 | 123 |
| `conformal_bh_rolling` | 0.1010 | 0.1587 | 0.0 | 2 |
| `aci_event` | 0.0085 | 0.0048 | 1,149.0 | 9,115 |
| `aci` | 0.0001 | 0.0000 | **176,336.9** | **1,383,948** |

**Within-scorer spread across layers: 0.0001 → 0.4278, a factor of ~4,000.**
**Across-scorer spread under the best layer: 0.2054 (A3) → 0.5436 (A2), a factor of ~2.6.**

So on this benchmark the choice of alarm layer moves performance about three orders of magnitude
more than the choice of scorer. That is the quantitative basis for the paper's framing, and it is
metric-robust.

**The mechanism, visible rather than asserted:** `aci` attains the **highest anomaly recall of any
configuration (0.9273)** and the lowest F0.5, because maintaining a point-level error rate over 58
channels at 30 s resolution across years yields an enormous absolute alarm count. Event aggregation
with a strictly selected operating point reduces alarm runs from 1,383,948 to 123 — a 160,000×
reduction in burden — at 50 % precision.

## 6. Protocol differences, descriptively

Because H6 cannot attribute, the useful descriptive statement is the magnitude of each candidate
difference where archived evidence allows:

| Difference | Archived evidence of its size | Can existing artifacts isolate it? |
|---|---|---|
| Selection data (9 vs 105 M1 events) | 11.7× more labelled events | Partly — the post-hoc OFAT attributed the effect here, but without interactions |
| Residual scale σ | per-channel score-ratio range **0.52–4.70**; **37 of 58 channels at the σ floor** | **No** — needs a refit with σ swapped |
| Calibration pool | **9.3×** more rows (792,000 → 7,364,161), *plus* a model mismatch (fold models vs full-fit) | **No** — and it bundles two sub-factors |
| Forecaster fit data | `fit` period vs all nominal training samples | No |
| Grid | 16 vs 20 cells | **Probably yes** — a grid-only re-selection is cheap |

**Only the grid is cleanly isolable from existing artifacts.** The other four require refits, which
is 3b.

## 7. Claim boundary for this report

| Claim | Permitted? |
|---|---|
| Selecting the alarm layer on the whole training half outperformed the calibration-period rule on M1 at full scale, +0.353 [+0.206, +0.488] | **Yes** — pre-registered |
| The deep event scorer shows no benefit over AR(8) or trees | **Yes** — pre-registered, both refutations metric-robust |
| The alarm layer moves performance ~3 orders of magnitude more than the scorer | **Yes** — descriptive, archived, metric-robust |
| Point-level ACI cannot produce a usable event-level alarm layer, and the reason is alarm volume | **Yes** — 176,337 FA/yr at 92.7 % recall |
| Cross-fitting over-estimated lightweight M1 by 21× | **Yes** — descriptive, within-arm |
| Selection score predicts test ordering better on M1 than M2 | **Yes, weakly** — four consistent measurements, none with a CI |
| Selection "perfectly predicts" / "anti-predicts" test performance | **No** — n = 3 artefact |
| *Which* protocol difference causes H6 | **No** — requires 3b |
| The selection effect generalises across missions | **No** — M2 cannot test it |
| Competitive absolute performance | **No** — Brancato unresolved |
