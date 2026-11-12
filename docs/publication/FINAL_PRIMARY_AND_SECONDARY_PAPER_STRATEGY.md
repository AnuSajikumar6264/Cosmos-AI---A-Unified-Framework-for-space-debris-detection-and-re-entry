# Final primary and secondary paper strategy

Date 2026-11-05 · after Track 3a and the free Secondary-A analyses

---

## 1. Decision

### Primary paper: **READY FOR MANUSCRIPT DEVELOPMENT**, with a bounded claim set

Track 3a changed this. Before it, the primary paper's headline was exposed to *"your result is an
artifact of counting rare events"* and *"your effect reverses on Mission 2"*. Both are now
answered from archived evidence:

- **H6 is metric-robust on Mission 1**: +0.3045 anomaly-only against +0.3534 composite. Both
  refutations (H4, H5) also hold under anomaly-only.
- **Mission 2 is demonstrably unable to test the question**: 6 anomalies in its test half, arm A1
  raises 238 alarms and detects **zero**, and every learned arm scores **exactly 0.0000** on
  anomaly-only.

The remaining limitations are **disclosable rather than disqualifying** — with one exception
handled by framing (§4).

### Secondary A: **READY FOR MANUSCRIPT DEVELOPMENT** as a separate paper

The free analyses closed its largest objection. **Every published arm beats the feature-free oracle
at both origins** (worst arm 14–39 % better), so absolute losses are now externally calibrated. And
the coverage failure has a localised, archived signature.

### Secondary B (OPS-SAT): **NOT READY** — still blocked on E6

Unchanged. `cnn` beats the fusion on the official protocol and the time-blocked margin is +0.0007.
Without E6 there is no architectural claim.

---

## 2. What Track 3a establishes

| # | Established | Evidence |
|---|---|---|
| 1 | The pre-registered Mission 1 conclusions are **metric-robust**. H6 +0.3045 anomaly-only vs +0.3534 composite; H4 −0.2112 vs −0.2224; H5 −0.2017 vs −0.3383 | Protocol test JSONs; all six composite contrasts reproduce `CONFIRMATORY.md` exactly |
| 2 | **Mission 2 cannot discriminate anomaly-detection methods.** 6 anomalies; A1 at 0.0000 with 238 alarms; every learned arm at exactly 0.0000 at M2 lightweight | Protocol test JSONs, `results.csv` |
| 3 | The composite metric **overstates** Mission 2 by ~6× (0.87–0.96 vs 0.00–0.18) | Same |
| 4 | **The alarm layer dominates the scorer by ~3 orders of magnitude.** Within-A1 layer spread 0.0001 → 0.4278; across-scorer spread 0.2054 → 0.5436 | Same |
| 5 | **Point-level ACI is unusable at event level, with a visible mechanism**: highest recall of any configuration (0.9273) at **176,337 false alarms/year** and 1,383,948 alarm runs, against 1.1/year and 123 runs for the event layer — a ~160,000× burden reduction | Same |
| 6 | **Cross-fitting over-estimated lightweight M1 by 21×** (0.528 → 0.025) | Same |
| 7 | The best Mission 1 arm is **metric-dependent** (A2 composite, A1 anomaly-only; margin 0.0094, inside A2's ±0.169 seed spread) | Same |
| 8 | Selection score predicts test ordering **better on M1 than M2** (per-run ρ +0.455 vs −0.118) | Same |

## 3. What Track 3a does not establish

| # | Not established | Why |
|---|---|---|
| 1 | **Any attribution of H6** | Five simultaneous protocol differences. Requires 3b |
| 2 | **Any absolute-performance comparison** | Brancato et al. report 0.902 where COSMOS-AI's best is ~0.09–0.20. Out-of-limit gap explained (different estimators); **method gap unexplained, blocked on paywalled full text** |
| 3 | **Generalisation** across missions, channel sets or layers | 1 of 8 cells confirmatory; M2 cannot test it; M3 unusable |
| 4 | **New inference on the secondary metric** | Point differences only — no CI, no p-value for any anomaly-only contrast |
| 5 | That selection "predicts" or "anti-predicts" test performance | Arm-level ρ = ±1.000 is at chance level with n = 3 (p = 1/6) |
| 6 | Clean confirmatory status | Test halves were scored in 128 configuration–layer combinations **before** the pre-registration was designed |

## 4. Is the primary paper ready? Yes — under one framing condition

**It is ready, provided the paper makes no absolute-performance claim.**

That is not a workaround; it is the honest position, and it is also strategically sound. The
recommended central question —

> Under the official ESA-ADB protocol at full channel scale, does the data used to select an
> event-level alarm layer matter more to detection performance than the capacity of the anomaly
> scorer feeding it, and under what conditions does that effect hold?

— is a question about **relative** protocol effects. Every within-study contrast it needs is
unaffected by the Brancato discrepancy, because that discrepancy concerns absolute levels.

The paper must nonetheless **state the discrepancy openly**, including that an independent third
effort (TC-CAD, 0.090) lands in COSMOS-AI's range while Brancato reports 0.902, and that the
parameter-free reference differs by three orders of magnitude for a reason now understood
(empirical training-range envelope versus operational limits). Disclosing it pre-empts the
objection; hiding it would invite the reviewer to discover it.

## 5. What 3b would add, and whether it is essential

| | |
|---|---|
| **Adds** | Attribution. The paper could say *which* protocol element carries the +0.353, and give a practitioner a recommendation rather than a configuration report. It would also make the working title *"alarm-layer selection matters more than model capacity"* defensible rather than heavily conditioned |
| **Essential?** | **No — optional for publication, essential for the strongest version.** Without it the paper is a careful pre-registered protocol comparison with a metric-robust negative result and a well-evidenced alarm-layer finding, with the five-way confound disclosed |
| **Recommendation** | **Approve Stage 1 regardless** — 4 runs, re-selection only, **minutes of CPU**, and it carries the design's own validity check (S1 must reproduce A0, S4 must reproduce A1). It may settle attribution for the two factors needing no refit. **Defer Stage 2** (12 runs, 3–4 h) until Stage 1 reports |

## 6. Remaining major rejection risks

| # | Risk | Severity | Mitigated by 3a? | Required action |
|---|---|---|---|---|
| 1 | **Brancato et al. report 0.902 where COSMOS-AI reports ~0.09–0.20** | **Critical** | No | Make no comparative claim; disclose openly; obtain the full text. **Blocked — yours to obtain** |
| 2 | **H6 attributes nothing — five simultaneous differences** | **Major** | No | Disclose; run 3b Stage 1, then decide on Stage 2 |
| 3 | **The pre-registration was motivated by a test result**; both test halves pre-exposed in 128 combinations | **Major** | No | Disclose prominently — in the abstract or early methods, not buried |
| 4 | ~~The effect reverses on Mission 2~~ | ~~Major~~ → **Minor** | **YES** | **Largely closed.** M2 cannot test the question: 6 anomalies, A1 at zero |
| 5 | ~~The result may be an artifact of counting rare events~~ | ~~Major~~ → **Closed** | **YES** | **Closed.** H6 +0.3045 anomaly-only; both refutations hold |
| 6 | **Comparator fairness** — ACI's γ tuned to a point rate; neither supervised scorer had a tuning budget; one deep architecture | **Major** | No | Equalise budgets (3d), or state every affected claim as a lower bound |
| 7 | **Seed variance ±0.1 against a +0.05 minimum effect** | Major | No | Disclose; more seeds would help but is not free |
| 8 | **No public artifact — no DOI, deposit or licence** | **Critical for a benchmark-adjacent paper** | No | Mint a deposit. **Requires your accounts and licence decisions** |
| 9 | **Freeze gate covers code only**; A1 selection files predate the frozen code | Moderate | No | Disclose as a provenance limitation |
| 10 | **Released `twins.jsonl` carries 123 incoherent records** marked `abstain = false` and `"validated-real"` | Moderate (artifact integrity) | No | Publish `KNOWN_ISSUES.md`; fix forward-only. **Do not modify historical data** |

**Net: two Critical risks remain (1 and 8), both requiring action outside this machine. Two
previously-Major risks (4 and 5) were closed or downgraded by 3a.**

## 7. Paper portfolio

| | Primary | Secondary A | Secondary B |
|---|---|---|---|
| **Subject** | Event-level alarm selection on ESA-ADB | Catalogue-scale orbital-lifetime benchmark and selection regret | OPS-SAT detector |
| **Status** | **Ready for manuscript development** (bounded claims) | **Ready for manuscript development** | **Blocked on E6** |
| **Strongest result** | H6 +0.353, metric-robust; alarm layer dominates by ~10³; ACI unusable at 176,337 FA/yr | Selection regret up to **+82.88 %**, significant at origin 2016; every arm beats the feature-free oracle | Beats a foundation model by +0.0316 (official protocol only) |
| **Venue** | **EAAI** (Scopus 24182) | **Acta Astronautica** (12372) or Adv. Space Res. | EAAI or a workshop |
| **Blocking** | Brancato (framing); DOI | DOI | **E6** |
| **Independence** | Full | Full — different data, task, venue | Full, conditional |

**Publish separately.** Merging would recreate the integrated-framework error the project already
withdrew, and each study stands on its own data and protocol.

## 8. Recommended next actions, in order

1. **Approve 3b Stage 1** — 4 re-selection runs, minutes of CPU, new output directory, freeze hash
   verified before and after. It may settle attribution for F4/F5 free.
2. **Approve the free Track 2 statistics** — per-arm bootstrap intervals and paired tests on the
   main leaderboard; bootstrap CI and exact permutation p-value for each ρ. No fitting.
3. **Publish `KNOWN_ISSUES.md`** for the 123 `twins.jsonl` records (additive; existing digest still
   verifies).
4. **Add the uncited prior art** — Candès et al. (2023), Gui et al. (2024), Shorten et al. (2023),
   Brancato et al. (2026), Fejjari et al. (2026), Dai et al. (2026).
5. **Obtain Brancato et al.'s full text.** The only route to risk 1.
6. **Decide the deposit** — repository visibility, code licence, data licence, and the
   AGPL/`ultralytics` boundary.
7. **Then** begin the primary manuscript. Not before, because 3b Stage 1 may change what §2 claim 4
   can say.

**No manuscript text has been written. No experiment has been run. No frozen artifact,
pre-registration, G5d verdict or historical output has been modified. Nothing committed, pushed or
published.**
