# Track 3a — anomaly-only metric analysis

Date 2026-11-05 · all values verified against archived outputs · **no frozen artifact, protocol or
pre-registered verdict modified**

**Headline: the pre-registered conclusions survive the metric change. H6's effect is +0.3045 under
anomaly-only versus +0.3534 under the composite on Mission 1, and H4/H5 remain negative. Mission 2
is shown to be unusable for anomaly detection: arm A1 raises 238 alarms and detects exactly zero
of its 6 anomalies.**

---

## 0. Status of this analysis, stated first

| Aspect | Status |
|---|---|
| **The anomaly-only metric is pre-specified, not post-hoc** | `PREREG_TELEMETRY_V1.md` §3 states: *"the `anomaly` log-odds of A2 and A3 is a **secondary arm, scored on the anomaly-only metric**"*. Both metrics are written to every archived result record |
| **Confirmatory status** | The **composite** metric remains the **primary** endpoint. The anomaly-only values below are **descriptive / secondary**. No hypothesis is re-tested, no verdict is changed |
| **Inference** | Point differences only. **No bootstrap, no CI, no p-value** is computed for the anomaly-only contrasts — the block-bootstrap machinery is tied to the primary metric, and running it on a secondary metric would be a new inferential test, which is out of scope here |
| **Preserved** | H4 refuted · H5 refuted · H6 supported (+0.353 [+0.206, +0.488], Holm p = 0.0015) — unchanged and authoritative |

## 1. Verification against the archived record

Every composite value below was reproduced from
`outputs/benchmarks/telemetry_esa_adb/oof_protocol/test/*.json` and `results.csv`, and checked
against `oof_protocol/CONFIRMATORY.md`:

| Contrast | Archived confirmatory | My reproduction | Match |
|---|---|---|---|
| M1 H4 (A3 − A1) | −0.222 | **−0.2224** | ✓ |
| M1 H5 (A3 − A2) | −0.338 | **−0.3383** | ✓ |
| M1 H6 (A1 − A0) | +0.353 | **+0.3534** | ✓ |
| M2 H4 | +0.001 | **+0.0014** | ✓ |
| M2 H5 | −0.029 | **−0.0290** | ✓ |
| M2 H6 | −0.089 | **−0.0889** | ✓ |

**All six reproduce.** Arm identification: A0 = `m{m}_target_ar8_s0` (calibration-period rule),
A1 = `m{m}_target_ar8` (training-half OOF selection), A2 = `m{m}_target_gbt_ar8_s{0..4}_event`
(XGBoost, 5 seeds), A3 = `m{m}_target_event_ar8_all_c3_s{0..4}_event` (EventTCN, 5 seeds), primary
calibrator `conformal_bh`.

*(An initial extraction averaged across calibrators and produced the wrong sign for M2 H6; it was
corrected by restricting to `conformal_bh`. Recorded because it is exactly the kind of error
verification exists to catch.)*

## 2. Arm performance under both metrics

**Mission 1, target channels (58), `conformal_bh`:**

| Arm | Description | Composite EW-F0.5 | **Anomaly-only EW-F0.5** | Anomaly precision | Anomaly recall | Seeds |
|---|---|---|---|---|---|---|
| **A0** | AR(8), 9-month calibration-period selection | 0.0744 | **0.0316** | 0.0258 | 0.3091 | 1 |
| **A1** | AR(8), whole-training-half OOF selection | 0.4278 | **0.3361** | 0.5000 | 0.1455 | 1 |
| **A2** | XGBoost event model | 0.5436 ± 0.2108 | **0.3267 ± 0.1689** | 0.4374 | 0.2145 | 5 |
| **A3** | EventTCN (220,739 params) | 0.2054 ± 0.1021 | **0.1250 ± 0.0702** | 0.1215 | 0.2145 | 5 |

**Mission 2, target channels (47), `conformal_bh`:**

| Arm | Composite EW-F0.5 | **Anomaly-only EW-F0.5** | Anomaly precision | Anomaly recall | Alarm runs |
|---|---|---|---|---|---|
| A0 | 0.9624 | **0.1471** | 0.1428 | 0.1667 | — |
| **A1** | 0.8735 | **0.0000** | **0.0000** | **0.0000** | **238** |
| A2 | 0.9039 ± 0.0443 | **0.1288 ± 0.0740** | 0.1300 | 0.1333 | — |
| A3 | 0.8749 ± 0.0521 | **0.1797 ± 0.2087** | 0.3067 | 0.1333 | — |

## 3. Pre-registered contrasts under both metrics

| Contrast | Mission | Composite (**primary, confirmatory**) | Anomaly-only (**secondary, descriptive**) | Direction preserved? |
|---|---|---|---|---|
| **H6: A1 − A0** | **1** | **+0.3534** · Holm p = 0.0015 · **supported** | **+0.3045** | **YES** |
| H4: A3 − A1 | 1 | −0.2224 · p = 0.101 · refuted | −0.2112 | **YES** |
| H5: A3 − A2 | 1 | −0.3383 · Holm p = 0.070 · refuted | −0.2017 | **YES** |
| H6: A1 − A0 | 2 | −0.0889 (replication, no inference) | **−0.1471** | YES (still reversed) |
| H4: A3 − A1 | 2 | +0.0014 | +0.1797 | sign agrees, magnitude differs greatly |
| H5: A3 − A2 | 2 | −0.0290 | +0.0509 | **NO — sign flips** |

**The three Mission 1 conclusions are metric-robust.** The selection-protocol effect, and both
refutations of the deep scorer, hold in direction and approximate magnitude when rare events are
excluded. This is the single most useful outcome of 3a: it removes "your result is an artifact of
counting rare events" as a reviewer objection on Mission 1.

**Mission 2 is not metric-robust**, and H5's sign flips there. That is a property of Mission 2, not
of the protocol — see §4.

## 4. Why Mission 2 cannot support generalisation claims

Three independent lines of archived evidence, all under the anomaly-only metric.

### 4.1 The label composition makes the composite metric nearly uninformative

Mission 2's test half contains **6 anomalies and 356 rare events**. The composite
`anomaly_and_rare` metric is therefore ~98 % determined by rare events. Across arms the composite
sits at **0.87–0.96** while anomaly-only sits at **0.00–0.18** — a factor of roughly six on the
same predictions.

### 4.2 Arm A1 detects zero anomalies while raising 238 alarms

Under the primary calibrator on Mission 2, A1 records anomaly-only EW-F0.5 **0.0000**, anomaly
precision **0.0000**, anomaly recall **0.0000**, with **238 alarm runs**. It is not that A1 detects
anomalies poorly; it detects **none of the six**.

In the broader benchmark the same pattern holds for every learned arm at M2 lightweight:
`cosmos_monitor`, `ar8` and `patchtst` all score **exactly 0.0000** on anomaly-only.

### 4.3 The trivial rule's apparent success is rare-event detection

`out_of_limits` on M2 lightweight scores **0.9648 composite but 0.0877 anomaly-only**, with 3,162
rare-event-only runs. Its composite success is a statement about out-of-limit excursions, which is
close to what "rare event" operationally means.

### 4.4 Conclusion

**With six anomalies in the test half and every learned arm at or near zero anomaly-only F0.5,
Mission 2 has no power to discriminate anomaly-detection methods.** Its composite metric measures
a materially different quantity from Mission 1's. The project reached the same conclusion
independently — its own claim register states *"Mission 2 is near-saturated."*

**Consequence for claims:** the reversal of H6 on Mission 2 must **not** be presented as evidence
that the selection effect fails to generalise across missions, and equally must **not** be hidden.
The correct statement is that Mission 2 cannot test the question. Mission 3 cannot either — it has
no official split, its authors advise against benchmarking on it, and it contains 8 anomalies and
25 rare events in total.

## 5. A metric-dependent rank flip on Mission 1

| Metric | Best arm on M1 | Value | Second |
|---|---|---|---|
| Composite | **A2** (XGBoost) | 0.5436 | A1 0.4278 |
| **Anomaly-only** | **A1** (AR(8)) | **0.3361** | A2 0.3267 |

The identity of the best-performing arm on Mission 1 **changes with the metric**. The margin is
small (0.0094) and well inside A2's seed spread (± 0.1689), so neither ordering is established —
but it is a concrete demonstration that metric choice is not cosmetic on this benchmark. It should
be reported, not resolved by picking the favourable metric.

## 6. The alarm layer dominates everything else

Archived values for A1 on Mission 1 across all five alarm layers:

| Alarm layer | Composite | Anomaly-only | Anomaly precision | Anomaly recall | **False alarms/year** | Alarm runs |
|---|---|---|---|---|---|---|
| `threshold` | 0.4278 | 0.3361 | 0.5000 | 0.1455 | **1.1** | 90 |
| **`conformal_bh`** (primary) | **0.4278** | **0.3361** | 0.5000 | 0.1455 | **1.1** | 123 |
| `conformal_bh_rolling` | 0.1010 | 0.1587 | 1.0000 | 0.0364 | 0.0 | 2 |
| `aci_event` | 0.0085 | 0.0048 | 0.0039 | 0.5818 | 1,149.0 | 9,115 |
| **`aci`** (point-level) | **0.0001** | **0.0000** | 0.0000 | **0.9273** | **176,336.9** | **1,383,948** |

**This is the clearest single result in the track.** Point-level adaptive conformal inference
achieves **92.7 % anomaly recall** — the highest of any configuration — and is useless, because it
raises **1,383,948 alarm runs** and **176,337 false alarms per year**, driving precision to zero.
The event-level BH layer achieves 50 % precision at 14.6 % recall with **1.1 false alarms per
year**: an alarm burden roughly **160,000× lower**.

The mechanism is visible in the numbers rather than asserted: maintaining a *point-level* error
rate across 58 channels sampled at 30 s over years produces an enormous *absolute* alarm count,
however correct the rate. Aggregating to events and selecting a strict operating point converts
that into an operationally usable layer.

**This holds under both metrics**, and it is the project's best-supported mechanistic claim.

Two further observations from the same table:

- **The primary calibrator is not always the best.** For A2 on M1, `threshold` beats
  `conformal_bh` (composite 0.6134 vs 0.5436; anomaly-only 0.3708 vs 0.3267).
- **A3's ranking depends on the layer**: with `conformal_bh_rolling` A3 reaches 0.3234 composite
  against 0.2054 under `conformal_bh`.

Both reinforce that the alarm layer, not the scorer, carries most of the variation — which is the
paper's thesis, and which §7 of the stability report quantifies.

## 7. What 3a establishes and does not establish

**Establishes:**

1. The three Mission 1 pre-registered conclusions (H6 supported; H4, H5 refuted) are **robust to
   excluding rare events** — H6 +0.3045 anomaly-only against +0.3534 composite.
2. **Mission 2 cannot support anomaly-detection generalisation claims**, quantitatively: 6
   anomalies, A1 at exactly 0.0000 with 238 alarms, every learned arm at or near zero.
3. The composite metric **overstates** Mission 2 performance by roughly 6× relative to
   anomaly-only.
4. **The alarm layer dominates the scorer**, with a visible mechanism: point-level ACI reaches
   92.7 % recall and 176,337 false alarms/year; the event layer reaches 1.1/year.
5. The best Mission 1 arm is **metric-dependent**.

**Does not establish:**

1. **No new inference.** Point differences only; no CI or p-value for any anomaly-only contrast.
2. **No attribution.** H6 still compares two whole protocols differing in five respects.
3. **No absolute-performance claim.** The Brancato discrepancy is untouched by this analysis.
4. **No generalisation.** Mission 1 at full channel scale remains the only informative cell.
5. **Nothing about the lightweight subset's reversal**, which is covered in the stability report.
