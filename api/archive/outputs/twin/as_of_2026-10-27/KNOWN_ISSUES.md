# Known issues — dated forecast, as of 2026-10-27

Added 2026-11-05. **This file is additive. No data file in this directory has been modified, and
`FORECAST_SHA256.txt` still verifies against `twins.jsonl` and `forecast_table.csv.gz`.**

---

## L17 — per-horizon lifetime probabilities are not a coherent CDF for 123 objects

### What is wrong

For **123 of 13,238** objects with a learned lifetime forecast, the calibrated per-horizon
probabilities violate monotonicity in the horizon:

```
P(decay <= 30 d)  <=  P(decay <= 90 d)  <=  P(decay <= 1 yr)
```

does not hold. Breakdown: **47** objects with P(30d) > P(90d), **76** with P(90d) > P(1yr).
Maximum violation magnitude **0.179661**; median **0.115385**. All values remain inside [0, 1].

### Where it appears

| File | Field | Affected |
|---|---|---|
| `forecast_table.csv.gz` | `p_lifetime_30d`, `p_lifetime_90d`, `p_lifetime_1yr` | **123 rows of 13,238** |
| `twins.jsonl` | `outputs[].values.p_reentry_{30d,90d,1yr}` where `model` begins *"physics + learned, reliability-gated"* | **123 records of 31,396** |

**These records carry `abstain = false`, an empty `reason`, and a `validation` field reading
"validated-real". Nothing in the file marks them.** That is the reason for this disclosure.

### Where it does NOT appear — use these instead

| Field family | Coherent? | Note |
|---|---|---|
| **`p_30d`, `p_90d`, `p_1yr`** (final reported) | **YES — 0 violations across all 31,396 rows** | **Recommended for any downstream use** |
| `p_lifetime_raw_30d/90d/1yr` | **YES — 0 violations** | Coherent by construction: read off a single monotone quantile function. Uncalibrated |
| `p_physics_history_*`, `p_physics_prior_*` | YES — 0 violations | |
| `twins.jsonl` other output blocks (physics expert; previous-window base rate) | YES — 0 violations | |

### Cause

Each horizon is calibrated by an **independent isotonic regressor**
(`cosmos/ai/twin/engine.py:226`, applied at `:290`). Isotonic regression is monotone in its own
input but imposes no constraint *across* horizons. Because each calibrator is fitted to a different
event rate and is piecewise-constant, an object can sit on a high plateau of the 30-day calibrator
and a low plateau of the 90-day one. The raw probabilities are coherent; the per-horizon
calibration breaks the ordering.

### Impact

- **No published scientific result in this project depends on these fields.** Leaderboards,
  selection-transfer, selection-regret and coverage analyses are computed from archived quantile
  matrices, not horizon probabilities.
- **`top50_reentry_30d.csv` ranks on `p_30d`, which is coherent.** Two affected objects
  (NORAD **23806**, **41696**) appear in that file, but their ranking value is from the clean
  column.
- **Operational risk if the affected fields are used directly:** an object can appear more likely
  to re-enter within 30 days than within a year, which would invert a triage ordering.

### Mitigations already in the codebase

| Consumer | Behaviour |
|---|---|
| `cosmos/ai/adapters.py` | **Abstains** on non-monotone rows, records the reason, and surfaces them under `noncoherent_horizon_probabilities` |
| `cosmos/product/store.py` | Computes and attaches `horizon_coherence` per object |
| `cosmos/ai/dashboard.py` | Discloses the independent-isotonic cause in the rendered page |
| `scripts/audit_horizon_coherence.py` + `tests/test_artifact_audit.py` | Automated audit with tests |

### Planned correction — forward-only

A corrected implementation will read horizon probabilities off the **single monotone quantile
function**, or apply a cross-horizon isotonic projection after per-horizon calibration, making
coherence structural rather than patched (cf. Henzi, Ziegel & Gneiting, *Isotonic Distributional
Regression*, JRSS-B 2021, `10.1111/rssb.12450`).

**This directory will not be regenerated.** Any corrected output will appear under a new dated
directory with new column names, so that this release and its digest remain verifiable.

### Affected object IDs (123)

```
1392, 14818, 19429, 22455, 23616, 23806, 24893, 25454, 25807, 26121, 26187, 26432, 27048, 27146, 27152, 28853, 29406, 35344, 35346, 35375, 35573, 35689, 36365, 36983, 38326, 38616, 38922, 39052, 39450, 39801, 39848, 40121, 40245, 41689, 41696, 41808, 41810, 42670, 43353, 43377, 43380, 43543, 43580, 43606, 43686, 43822, 43918, 44230, 44561, 44562, 44616, 44712, 44870, 44872, 44890, 45034, 45496, 45498, 45635, 45638, 45648, 45651, 45829, 45847, 45914, 45971, 45976, 46006, 48539, 48541, 48713, 54286, 54294, 54308, 54405, 54463, 54471, 54482, 54553, 54565, 54577, 54600, 54897, 54917, 54930, 54933, 55194, 55215, 55222, 55228, 55530, 55537, 55556, 55869, 55904, 55907, 56247, 56270, 56600, 56651, 56653, 60011, 60621, 60634, 60654, 60792, 60890, 60898, 60971, 61314, 61326, 61340, 61434, 61453, 61455, 61466, 61829, 64653, 65790, 660, 66515, 69736, 8978
```
