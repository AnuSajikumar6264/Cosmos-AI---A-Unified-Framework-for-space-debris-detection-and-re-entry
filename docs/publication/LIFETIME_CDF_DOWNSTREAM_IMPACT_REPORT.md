# Lifetime CDF defect — downstream impact report

Date 2026-11-05 · **historical data and published results preserved; nothing modified**

**Headline: yes, this is an actual consumer-facing defect. 123 records in the released
`twins.jsonl` carry non-monotone re-entry probabilities with `abstain = false`, an empty `reason`,
and a `validation` string reading "validated-real". A consumer reading the released artifact has no
in-file signal that these values are incoherent.**

This corrects my own earlier statement that the adapter mitigation contained the defect. It
contains it for *adapter* consumers. It does not contain it in the released file.

---

## 1. Is it consumer-facing? Yes — verified directly

Scanning all **31,396** records of `outputs/twin/as_of_2026-10-27/twins.jsonl`:

| Output block (`model`) | Records with a `p_reentry_*` triplet | Incoherent |
|---|---|---|
| `previous-window payload base rate` | 16,386 | 0 |
| `physics expert, area-to-mass conditioned on the ca…` | 13,238 | 0 |
| **`physics + learned, reliability-gated (lifetime pip…`** | **13,238** | **123** |
| `physics expert (NRLMSIS 2.1, Monte-Carlo A/m from …)` | 1,772 | 0 |

**123 incoherent triplets**, all in the `physics + learned, reliability-gated` block — i.e. exactly
the `p_lifetime_*` family identified as L17. The count matches the forecast-table audit exactly.

Examples:

| `object_id` | p_reentry_30d | p_reentry_90d | p_reentry_1yr | Violation |
|---|---|---|---|---|
| 660 | **0.7797** | **0.7500** | 0.9875 | 30d > 90d by 0.0297 |
| 1392 | **0.7797** | **0.7500** | 0.9875 | 30d > 90d by 0.0297 |
| 8978 | 0.0323 | **0.2847** | **0.1923** | 90d > 1yr by 0.0924 |

### 1.1 Why this is worse than the forecast-table exposure

All 123 affected output blocks carry:

| Field | Value |
|---|---|
| `abstain` | **`false`** |
| `reason` | **`""`** (empty) |
| `validation` | **`"validated-real: GCAT temporal tests (origins 2011, 2016) at canonical-…"`** |
| `values` keys | `p_reentry_30d`, `p_reentry_90d`, `p_reentry_1yr`, `median_days` |

So the released file presents these values as non-abstained, reason-free and
**explicitly labelled "validated-real"**. A downstream consumer parsing `twins.jsonl` — which is
the natural machine-readable interface, 40.9 MB and hashed into `FORECAST_SHA256.txt` — receives a
probability triplet that violates monotonicity with no accompanying signal.

This is a different situation from the three mitigated consumers:

| Consumer | Mitigation | Status |
|---|---|---|
| `cosmos/ai/adapters.py` | **Abstains**, records the reason, surfaces affected objects under `noncoherent_horizon_probabilities` | **Contained** |
| `cosmos/product/store.py` | Computes `lifetime["horizon_coherence"]` per object | **Labelled** |
| `cosmos/ai/dashboard.py` | Discloses the independent-isotonic cause in the rendered page | **Disclosed** |
| **`twins.jsonl`** (released artifact) | **none** | **EXPOSED** |

## 2. Affected downstream outputs

| Output | Affected? | Detail |
|---|---|---|
| `twins.jsonl` (released, hashed) | **YES** — 123 of 31,396 records | The only unguarded consumer |
| `forecast_table.csv.gz` → `p_lifetime_*` | **YES** — 123 of 13,238 | Source of the defect; raw and final `p_*` families are clean |
| `forecast_table.csv.gz` → `p_*` (final reported) | No | **0 violations across all 31,396 rows** |
| `forecast_table.csv.gz` → `p_lifetime_raw_*` | No | 0 violations — coherent by construction, read off a single monotone quantile function |
| `top50_reentry_30d.csv` | **Needs checking before release** — it ranks on a 30-day probability, and 47 of the 123 violations are `P(30d) > P(90d)`, which inflates the 30-day value | See §4 action 2 |
| `summary.json`, `c2_clouds.csv` | Not assessed | Low risk; aggregate quantities |
| Published lifetime leaderboards, selection-transfer ρ, selection regret, Phase H coverage | **No** | All computed from archived quantile matrices, not horizon probabilities |
| T1 pseudo-prospective Brier/ECE for the `lifetime` arm | **Marginally** | 0.93 % of rows, median violation magnitude 0.115. Rank metrics use `p_lifetime_raw_*` by design (`engine.py:289`) |

**No headline scientific claim in any publication track depends on the affected columns.** The
exposure is in the released serving artifact, not in the science.

## 3. Severity assessment

| Dimension | Assessment |
|---|---|
| Scientific impact on claims | **None** — no track's results use these columns |
| Artifact-integrity impact | **Moderate** — the released, hashed file contains 123 internally inconsistent records marked "validated-real" |
| Operational impact if the file were used | **Potentially material** — an object can appear more likely to re-enter within 30 days than within a year, which inverts a triage ordering |
| Detectability by a consumer | **Low without checking** — nothing in the record flags it. Trivial *with* a monotonicity check |
| Reviewer/reproducibility impact | **Moderate** — a reviewer who downloads the artifact and runs a sanity check will find 123 violations in a file the paper describes as released evidence |

**Classification: a real but bounded consumer-facing defect in a released artifact, with no effect
on reported scientific results.**

## 4. Recommended safe correction — not applied

Historical data must not be modified, so every action below is additive.

| # | Action | Why safe |
|---|---|---|
| **1** | **Publish a `KNOWN_ISSUES.md` alongside the artifact**, naming L17, the 123 affected `object_id`s, the mechanism (independent per-horizon isotonic calibration), and directing consumers to the coherent `p_lifetime_raw_*` or final `p_*` families | Adds information; changes no byte of existing data; the existing `FORECAST_SHA256.txt` still verifies |
| **2** | **Check `top50_reentry_30d.csv` against the 123 object IDs** and, if any appear, state that in `KNOWN_ISSUES.md` | Read-only check |
| **3** | **Add a coherence flag in any *future* dated release** — e.g. `horizon_coherence: "coherent" / "non_monotone"` inside each output block, and set `abstain = true` with a reason for non-monotone blocks, matching the adapter's existing behaviour | Forward-only; a new dated directory, leaving `as_of_2026-10-27/` untouched |
| **4** | **Fix at source in future runs:** read horizon probabilities off the single monotone quantile function (the route `scripts/phase_g_multihorizon_coherence.py` already identifies), or apply a cross-horizon isotonic projection after per-horizon calibration | Structural rather than patched. **Cite Henzi, Ziegel & Gneiting (2021), `10.1111/rssb.12450`** — isotonic distributional regression yields monotone predictive CDFs by construction, which is the principled form of this fix |
| **5** | **Extend `scripts/audit_horizon_coherence.py` to cover `twins.jsonl`**, not only the forecast table | The audit already exists with tests; this closes the gap that let the exposure through |
| **6** | **Regression test:** assert the historical artifact still has exactly 123 violations (so the record is preserved), and that any new release has 0 | Pins both the history and the fix |

**Validation criteria for a corrected implementation** are set out in
`LIFETIME_CDF_DEFECT_IMPACT_AUDIT.md` §5: universal coherence, range preserved, calibration not
degraded, ranking not degraded, agreement with the raw monotone reading, and the adapter's
abstention count dropping to its non-L17 baseline.

## 5. Correction to my own earlier statement

| Earlier claim | Corrected |
|---|---|
| *"The defect is already contained at both consumer boundaries"* | **Incomplete.** It is contained at the **adapter** and **console** boundaries, and disclosed in the dashboard. It is **not** contained in the released `twins.jsonl`, where 123 records carry `abstain = false`, an empty `reason`, and a `validation` field reading `"validated-real"` |
| *"`twins.jsonl` carries it unguarded"* (flagged as a gap) | **Confirmed and now quantified** — 123 records, with the specific flag values that make it invisible to a consumer |

An initial scan of mine reported 0 violations in `twins.jsonl`; that was because I searched for
top-level `p_reentry_*` keys, while the values are nested inside `outputs[].values`. Recorded
because it is the kind of false negative that makes an artifact look clean when it is not.
