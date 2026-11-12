# Later-snapshot evaluation of the dated 2026-10-27 forecast — readiness

Date: 2026-11-04. Status: **BLOCKED**. No snapshot was downloaded and none was fabricated.

Reproduce with:

```bash
python scripts/check_t1_later_snapshot.py --out outputs/run_phase_d
# writes outputs/run_phase_d/t1_later_snapshot_readiness.json
```

## Two different studies, which must not be conflated

| | Existing **T1** study | Proposed **later-snapshot** evaluation |
|---|---|---|
| Code | `cosmos/ai/twin/prospective.py` | not yet written |
| Forecast as-of | 2026-08-16 | **2026-10-27** |
| Outcomes from | 2026-10-27 snapshot | a snapshot **later than** 2026-10-27 |
| Horizons | 30 d, 72 d | 30 d, 90 d, 1 yr |
| Blind? | **No** — self-disclosed | **Yes**, if the protocol is fixed first |
| Status | executed, non-blind, exploratory | **BLOCKED** on data |

T1's follow-up date *is* the dated forecast's as-of date. Scoring the dated forecast with T1's
outcomes would be a **zero-length window** and is not a confirmatory evaluation. This is
asserted by `tests/test_couplings_regression.py::test_t1_and_c3_use_the_same_window_and_are_not_the_dated_forecast`.

## The hashed forecast artifact

| Property | Value |
|---|---|
| Directory | `outputs/twin/as_of_2026-10-27/` |
| Hashed file | `twins.jsonl` |
| Recorded SHA-256 | `19a1fede1fd4871f380ff802f285d2ad03732f6cd3179790e67336c7d202a6b5` |
| Digest state (2026-11-04) | **verified** — recomputed digest matches |
| Forecast as-of | 2026-10-27 |
| Horizons reported | 30 d, 90 d, 1 yr (`engine.HORIZONS`) |
| Companion table | `forecast_table.csv.gz`, 31,396 rows × 49 columns |
| Learner / seeds | `tabm`, 5 seeds |

### Forecasted population

| Breakdown | Counts |
|---|---|
| Objects | 31,396 (`norad` unique) |
| By regime | `operator_controlled` 16,386; `natural_decay` 13,787; `unknown` 1,223 |
| By class | D 10,654 / R 1,470 / C 1,114 / P 549 within natural decay (per saved summary) |
| Expected re-entries, natural decay | 24.47 at 30 d; 75.34 at 90 d; 258.09 at 1 yr |
| Expected re-entries, unknown regime | 1.03 at 30 d; 2.66 at 90 d; 11.66 at 1 yr |
| Objects with `p_30d > 0.5`, natural decay | 21 |

## Why it is blocked

Snapshots present on disk, with the latest decay date each contains (its effective outcome
coverage):

| Snapshot | Path | Rows | Max decay date |
|---|---|---|---|
| catalogue root | `data/feature2_debris/celestrak/satcat.csv` | 70,288 | 2026-08-16 |
| 2026-10-24 | `.../snapshots/2026-10-24/satcat.csv` | 71,132 | 2026-10-23 |
| 2026-10-27 | `.../snapshots/2026-10-27/satcat.csv` | 71,149 | **2026-10-26** |

The newest outcome coverage ends **2026-10-26**, which is **one day before** the forecast's own
as-of date. Outcome days available after the forecast: **−1**. No horizon can be scored:

| Horizon | Outcome window | Snapshot data date required | Qualifying snapshot | Status |
|---|---|---|---|---|
| 30 d | 2026-10-27 → 2026-11-26 | ≥ **2026-11-26** | none | **BLOCKED** |
| 90 d | 2026-10-27 → 2027-01-25 | ≥ **2027-01-25** | none | **BLOCKED** |
| 1 yr | 2026-10-27 → 2027-10-27 | ≥ **2027-10-27** | none | **BLOCKED** |

## What is needed to unblock

1. A **CelesTrak SATCAT snapshot** (`satcat.csv`) with a data date on or after **2026-11-26**
   for the 30-day horizon, placed at
   `data/feature2_debris/celestrak/snapshots/<YYYY-MM-DD>/satcat.csv`.
2. Required fields: `NORAD_CAT_ID` and `DECAY_DATE` (the existing loaders read only these for
   outcome assignment).
3. Acquisition is a **network action and requires explicit authorisation**. The readiness
   script deliberately does not download anything. Today is 2026-11-04, so the 30-day horizon
   becomes scorable 22 days from now; 90 d in January 2027; 1 yr in October 2027.

Record the snapshot's retrieval date and its own SHA-256 when it is added, so the evaluation
input is as traceable as the forecast.

## Protocol to fix *before* any outcome is inspected

### Matching

- Match by **`NORAD_CAT_ID` only**, from the hashed forecast into the later snapshot.
- **Do not** re-derive the population from the later snapshot. Doing so would admit objects
  launched after 2026-10-27, which the forecast never ranked, and would silently change the
  denominator.
- Objects absent from the later snapshot are **not** decays. Catalogue removal has several
  causes; treat them as a separate, reported category.
- Exclude any object whose `DECAY_DATE` is at or before 2026-10-27 as a **late report**, the
  rule T1 and C3 already apply (`outcomes()`, `c3_dataset`).

### Censoring

- If the snapshot's data date is **younger than the horizon**, censor at the **data date**,
  not at the horizon. Scoring a 90-day horizon on 40 days of outcomes without censoring would
  understate every probability.
- Objects with no decay by the data date are censored there, not treated as negatives beyond it.

### Metrics

Fix this set in advance, matching what the twin already reports elsewhere:

- Brier score and expected calibration error per horizon;
- expected-over-observed count ratio with a **launch-cluster** bootstrap CI (decays cluster by
  launch, so an i.i.d. interval would be too narrow);
- AUC-ROC and AUC-PR, **omitted** when there is no event or the score is constant;
- reported **separately** for uncontrolled objects (drag forecast) and operator-controlled
  payloads (previous-window base rate), because these are different estimators. Pooling them
  would mix a physics forecast with a base rate.

### Integrity

- Re-verify `FORECAST_SHA256.txt` immediately before scoring; refuse to score on mismatch
  (`verify_digest` returns `MISMATCH`, covered by a test).
- Score each object once. Log the scoring run's Git commit, config digest and the snapshot digest.
- Do not tune anything on the outcome. Any deviation goes in
  [`METHODOLOGY_DECISIONS.md`](../../research_design/METHODOLOGY_DECISIONS.md) **before** the
  result is read.

## Expected limitations even once unblocked

1. **Low event counts at 30 days.** The forecast expects ~24.5 natural-decay re-entries, and
   only 21 objects exceed `p_30d > 0.5`. Calibration estimates from tens of events carry wide
   intervals; a single window cannot establish temporal robustness.
2. **Clustered outcomes.** Fragments of one launch or breakup decay together, so the effective
   sample is far below the object count. Launch-cluster intervals are mandatory.
3. **Catalogue churn.** Reclassification, late decay reporting and removals all change
   membership between snapshots independently of orbital dynamics.
4. **Operator-controlled payloads are not a physics test.** 16,386 of 31,396 objects receive a
   base rate. Their outcomes test a base-rate policy, not the drag model.
5. **`unknown` regime objects (1,223)** have no operational status and are forecast by the
   physics prior without validation for that subgroup.
6. **Space-weather dependence.** One 30-day window samples one activity level; it cannot
   establish robustness across the solar cycle.
7. **One window is still one window.** Even a clean result would be a single prospective
   observation, not independent operational validation.

## Status

| Item | Status |
|---|---|
| Hashed forecast integrity verified | **PASS** |
| Forecast population and horizons characterised | **PASS** |
| Matching, censoring and metric protocol specified in advance | **PASS** (specified, not executed) |
| Readiness check automated and tested | **PASS** — 3 tests |
| Later snapshot available | **BLOCKED** — newest coverage ends 2026-10-26 |
| Confirmatory temporal evidence for the dated forecast | **BLOCKED** — nothing scored |
