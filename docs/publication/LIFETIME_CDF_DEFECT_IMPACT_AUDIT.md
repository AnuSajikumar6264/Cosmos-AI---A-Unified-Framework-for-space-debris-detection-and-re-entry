# Lifetime CDF defect (L17) — impact audit

Date 2026-11-05 · **historical outputs preserved; nothing replaced or regenerated**

**Headline: reproduced exactly — 123 of 13,238 objects. The cause is three independent isotonic
regressors with no cross-horizon constraint. The defect is already contained at both consumer
boundaries, and the project's own test fixture carries the same maximum violation magnitude I
computed independently (0.1797).**

---

## 1. Reproduction

Computed directly from `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` (31,396 rows, SHA-256
verified against `FORECAST_SHA256.txt`):

| Column family | n with all three horizons | P(30d) > P(90d) | P(90d) > P(1yr) | **Any violation** |
|---|---|---|---|---|
| **`p_lifetime_*` (calibrated)** | **13,238** | 47 | 76 | **123** |
| `p_lifetime_raw_*` | 13,238 | 0 | 0 | **0** |
| **`p_*` (final reported)** | **31,396** | 0 | 0 | **0** |
| `p_physics_history_*` | 13,238 | 0 | 0 | 0 |
| `p_physics_prior_*` | 31,396 | 0 | 0 | 0 |

**Violation magnitude:** maximum **0.179661**, median **0.115385**.

`tests/test_artifact_audit.py:99` reads: *"One violation: 0.7797 > 0.600 is a drop of 0.1797."*
My independently computed maximum is **0.179661** — the project's test fixture and my
reconstruction agree to four decimal places.

**All values lie within [0, 1]** (verified: no negatives, none above 1).

## 2. Exact mathematical cause

`cosmos/ai/twin/engine.py:226`, inside a loop over horizon keys:

```python
M["iso"][hk] = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p[ok], y[ok])
```

and `engine.py:290`, applied per horizon:

```python
T.loc[iu, f"p_lifetime_{k}"] = M["iso"][k].predict(FU.horizon_prob(q1, h))
```

**Three separate isotonic regressors, each fitted on its own horizon's (raw probability, outcome)
pairs, each applied independently.**

Isotonic regression guarantees monotonicity **in its own input**, i.e. each `gₕ` is non-decreasing
in the raw probability for horizon `h`. It guarantees nothing **across** horizons. Formally: let
`a₃₀ ≤ a₉₀ ≤ a₁ᵧᵣ` be the raw horizon probabilities for one object (these *are* coherent — 0
violations in `p_lifetime_raw_*`, because they are read off a single monotone quantile function).
Applying three different monotone step functions gives

```
g₃₀(a₃₀),  g₉₀(a₉₀),  g₁ᵧᵣ(a₁ᵧᵣ)
```

and there is no constraint forcing `g₃₀(a₃₀) ≤ g₉₀(a₉₀)`. Whenever `g₃₀` rises more steeply than
`g₉₀` over the relevant interval — which happens because each calibrator is fitted to a different
event rate, and 30-day events are far rarer than 1-year events — the ordering can invert. The
isotonic step structure makes this more likely: each calibrator is piecewise-constant, so an object
can sit on a high plateau of `g₃₀` and a low plateau of `g₉₀`.

**Which CDF requirement is violated:** monotonicity of the predictive CDF in the horizon argument,
`P(T ≤ 30) ≤ P(T ≤ 90) ≤ P(T ≤ 365)`. **Range and non-negativity are not violated**, and the raw
family is coherent. So this is specifically a cross-horizon ordering failure introduced by
post-hoc calibration, not a modelling or normalisation error.

**Rate:** 123 / 13,238 = **0.93 %** of objects with a learned forecast. The 13,238 are the subset
with a fitted learned expert; the remaining 18,158 of 31,396 carry physics-only values.

## 3. Downstream consumers — all traced

| Consumer | Reads | Mitigation present? |
|---|---|---|
| **`cosmos/ai/adapters.py:191–193`** (`lifetime_estimates`) | `p_lifetime_{30d,90d,1yr}` | **YES — abstains.** Detects non-monotone rows, records an explicit reason, and surfaces them under a dedicated `noncoherent_horizon_probabilities` output |
| **`cosmos/product/store.py:306–308`** (Mission Intelligence Console) | same | **YES — labels.** `lifetime["horizon_coherence"] = _coherence(...)` is computed and attached per object |
| **`cosmos/ai/dashboard.py:73, 86`** (evidence dashboard) | same | **YES — discloses.** Line 227 tells the reader these columns "are produced by an independent isotonic" calibrator |
| `cosmos/ai/twin/engine.py:366` | writes `p_reentry_{k}` from `p_lifetime_{k}` into `twins.jsonl` (40.9 MB) | **NO explicit guard** — the affected values propagate into the per-object JSONL records |
| `scripts/phase_g_multihorizon_coherence.py` | the defect itself | **Purpose-built analysis** of it, proposing the monotone-quantile reading (`p_lifetime_raw_*`) as the fix |
| `scripts/audit_horizon_coherence.py` + `tests/test_artifact_audit.py` | the defect | **Automated audit with tests** |

The adapter comment is worth quoting, because it states the right principle:

> *"Abstaining keeps the defect visible; silently taking a running maximum here would overwrite a
> published number."*

## 4. Are historical results affected?

| Result | Uses the affected columns? | Affected? |
|---|---|---|
| **Published lifetime leaderboards** (`regression_test.csv`, both origins) | No — these score **pinball loss on quantiles**, not horizon probabilities | **No** |
| **Selection-transfer ρ, selection regret, rank instability** | No — computed from archived quantile matrices | **No** |
| **Phase H coverage table** | No — interval coverage from quantiles | **No** |
| **Final reported `p_*` columns** | — | **No — 0 violations across all 31,396 rows** |
| **T1 pseudo-prospective evaluation** | The `lifetime` arm's Brier/ECE. Rank metrics (AUC) use `p_lifetime_raw_*` by design (`engine.py:289` comment: *"for rank metrics (isotonic ties)"*) | **Marginally.** 0.93 % of rows with violations of median magnitude 0.115; the aggregate effect on Brier/ECE is bounded well below the reported precision, but it is non-zero and should be disclosed |
| **`twins.jsonl` per-object records** | `p_reentry_{k}` derived from the affected columns | **Yes, for the same 123 objects** |
| **Console / dashboard displays** | Labelled or abstained | **Contained** |

**No headline scientific claim in any of the three publication tracks depends on these columns.**
The defect is confined to per-object horizon probabilities consumed by the serving layer.

## 5. How a corrected implementation should be validated

I am **not** proposing to apply a fix — that needs your approval and would touch published
artifacts. The validation design, for when you do:

| # | Requirement | Test |
|---|---|---|
| 1 | **Do not overwrite published outputs.** Write any corrected columns under new names (e.g. `p_lifetime_coh_*`) in a new dated directory, leaving `as_of_2026-10-27/` and its SHA-256 digest untouched | Digest of the existing forecast still verifies |
| 2 | **Coherence holds universally** | 0 violations of `P(30d) ≤ P(90d) ≤ P(1yr)` over all rows, at a stated tolerance |
| 3 | **Range preserved** | all values in [0, 1] |
| 4 | **Calibration is not degraded** | Per-horizon reliability (Brier, ECE) of the corrected columns is no worse than the current calibrated columns on the same evaluation set; report both |
| 5 | **Ranking is not degraded** | Per-horizon AUC-PR / AUC-ROC unchanged within noise — the raw columns exist precisely because isotonic ties damage ranking, so a fix must not reintroduce that |
| 6 | **The fix is a projection, not a refit** | Prefer enforcing coherence as a post-processing projection of the three calibrated values onto the monotone cone (e.g. isotonic regression *across horizons* per object, or a single joint calibrator on the quantile function). Document which was chosen and why |
| 7 | **Agreement with the raw monotone reading** | Compare against `p_lifetime_raw_*`, which is already coherent by construction, and report the trade-off: raw is coherent but uncalibrated; calibrated is sharper but incoherent |
| 8 | **Regression test** | Extend `tests/test_artifact_audit.py` to assert 0 violations in the corrected family while keeping the existing assertion that the historical family still has exactly 123 |
| 9 | **Adapter behaviour** | After the fix the adapter should stop abstaining for these 123 objects; assert the abstention count drops to its non-L17 baseline |

**Recommended minimal fix** (for your decision, not applied): the project's own
`phase_g_multihorizon_coherence.py` already identifies the principled route — read horizon
probabilities off the **single monotone quantile function** rather than calibrating each horizon
independently. That makes coherence structural rather than patched. The cost is losing the
per-horizon isotonic calibration, so the trade-off in requirement 7 must be measured before
choosing.

## 6. Assessment of the project's handling

| Aspect | Status |
|---|---|
| Detected | **Yes**, dated 2026-11-04, labelled L17 |
| Root cause identified correctly | **Yes** — independent per-horizon isotonic calibration |
| Quantified | **Yes** — 123/13,238, and the max magnitude matches my independent computation |
| Contained at the adapter | **Yes** — abstains with a recorded reason, surfaces the affected objects |
| Contained in the console | **Yes** — coherence computed and labelled |
| Disclosed to the dashboard reader | **Yes** |
| Automated audit + tests | **Yes** |
| Dedicated analysis of the fix | **Yes** |
| Historical outputs preserved rather than silently patched | **Yes** — and explicitly reasoned about in the adapter comment |
| **Gap: `twins.jsonl` `p_reentry_*` carries the defect with no guard** | **No** |
| **Gap: not mentioned in any current manuscript** | **No** |

This is a well-handled defect. Its remaining exposure is that a reader of the released
`twins.jsonl` would encounter 123 incoherent per-object records with no in-file marker, and that
none of this appears in the manuscripts.
