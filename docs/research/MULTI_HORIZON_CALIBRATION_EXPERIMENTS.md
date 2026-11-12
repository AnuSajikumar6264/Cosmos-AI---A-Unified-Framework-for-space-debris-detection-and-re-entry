# Multi-horizon calibration — G2

Date: 2026-11-04. Verdict: **the coherent reading is both coherent and better calibrated.**
Status: **exploratory** (T1 is non-blind; event counts are small).

```bash
python scripts/phase_g_multihorizon_coherence.py --n-boot 4000     # exit 0
```
Outputs: `outputs/phase_g_multihorizon/multihorizon_results.json`, `multihorizon_metrics.csv`.

## The question — framed so it does not touch L17

Limitation L17 records that `p_lifetime_{30d,90d,1yr}` are not a coherent CDF because each
horizon is calibrated by an independent isotonic regressor. **The decision not to recalibrate
stands** (master decision log entry 2), and nothing here changes any published probability.

The study already computes a *second* reading, `p_lifetime_raw_*`, by reading probabilities off
the monotone quantile function. That reading is coherent **by construction**. The answerable
question is whether it is also as well calibrated — because if it is, the fix needs no new
calibrator at all: report the coherent reading.

## Design

| Property | Value |
|---|---|
| Outcomes | T1 window, as-of 2026-08-16 → follow-up 2026-10-27 |
| Objects | 13,186 with lifetime predictions |
| Events | **29** at 30 d, **64** at 72 d (rates 0.0022, 0.0049) |
| Independent unit | launch (paired cluster bootstrap, 4000 draws) |
| Endpoint | Brier score; calibration-in-the-large and AUC reported alongside |
| Arms | `isotonic` (`p_lifetime_*`) vs `coherent_raw` (`p_lifetime_raw_*`) |

Brier at an event rate of 0.002 is dominated by true negatives, so expected/observed event
counts are reported as the more interpretable calibration summary.

## Coherence

| Reading | Cross-horizon violations | Fraction | Max drop |
|---|---|---|---|
| isotonic | **54** | 0.41 % | **0.1974** |
| coherent_raw | **0** | 0.00 % | 0.0000 |

## Calibration and discrimination

### 30-day horizon (29 events / 13,186)

| Reading | Brier | ECE | mean p | expected/observed | AUC-ROC |
|---|---|---|---|---|---|
| isotonic | 8.704e−03 | **0.0209** | 0.0231 | **10.51×** | 0.9970 |
| **coherent_raw** | **2.604e−03** | 0.0303 | 0.0325 | 14.79× | 0.9980 |

Paired Brier Δ (raw − isotonic) = **−6.100e−03**, CI [−1.006e−02, −3.135e−03], p < 0.0001 →
**coherent reading better**.

### 72-day horizon (64 events / 13,186)

| Reading | Brier | ECE | mean p | expected/observed | AUC-ROC |
|---|---|---|---|---|---|
| isotonic | 1.344e−02 | 0.0414 | 0.0462 | 9.52× | 0.9944 |
| **coherent_raw** | **4.750e−03** | **0.0375** | 0.0424 | **8.73×** | 0.9949 |

Paired Brier Δ = **−8.690e−03**, CI [−1.449e−02, −4.460e−03], p < 0.0001 → **coherent reading
better**.

## Why the isotonic reading loses on Brier despite a lower mean probability

At 30 d the isotonic reading has a *lower* mean probability (0.0231 vs 0.0325) yet a Brier
score 3.3× *worse*. The implied RMS error on the dominant negatives is 0.093 for isotonic
against 0.051 for the raw reading, so the isotonic reading must place a heavy tail of **high
probabilities on objects that did not decay**.

That is exactly the mechanism L17 identified: an isotonic map collapses a range of scores onto
a **plateau** (the worst observed case is 0.7797 at 30 days against 0.6000 at 90 days). Objects
landing on a high plateau contribute large squared error when they do not decay. The same
plateau structure causes both the incoherence and the Brier penalty — **one defect, two
symptoms.**

## The larger problem neither reading fixes

**Both readings over-forecast by roughly an order of magnitude**: expected/observed event
ratios are 8.7× to 14.8×. Choosing the coherent reading improves Brier and removes the
incoherence, but the lifetime expert's absolute probability level remains badly wrong on this
window. No claim of calibrated 30-day or 72-day re-entry probability from the lifetime expert
is defensible.

The ECE comparison is mixed (isotonic better at 30 d, raw better at 72 d), which is consistent
with both being poorly calibrated in level while differing in tail behaviour.

## Recommendation

**Report the coherent reading** (`p_lifetime_raw_*`) wherever a multi-horizon lifetime
probability is presented, and state that it over-forecasts on the T1 window.

This requires:

- **no recalibration**, **no retraining**, and **no change to any published artifact**;
- no modification to the L17 decision, which concerned whether to *alter* the isotonic
  columns. They are preserved; this is a choice about which existing column to report.

Downstream code already abstains on the non-coherent isotonic rows
(`cosmos/ai/adapters.py`), so adopting the coherent reading would also eliminate 123 object
abstentions in the catalogue snapshot — a secondary benefit, not the justification.

## Limitations

1. **Exploratory.** T1 is explicitly non-blind.
2. **Low power** — 29 and 64 events. The Brier differences are significant, but the
   calibration-in-the-large estimates have wide uncertainty at these counts.
3. The **1-year horizon has no outcome** in a 72-day window and is not evaluated; the
   recommendation is therefore untested at the longest horizon.
4. Only the lifetime expert's columns are examined; the twin's reported `p_*` forecast is a
   different quantity and was not evaluated here.
5. A purpose-built coherent calibrator (discrete-time hazard, joint monotone calibration) was
   **not** implemented; this experiment only compares two readings the study already produces.

## Not done

- Discrete-time hazard model — needs training (G6).
- Joint multi-horizon isotonic calibration under a monotonicity constraint — needs a new
  calibrator fitted on tune-B, i.e. a protocol addition.
- Confirmation on a blind window — blocked with Phase F.
