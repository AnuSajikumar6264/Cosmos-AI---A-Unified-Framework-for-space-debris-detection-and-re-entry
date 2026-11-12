# C2 evaluation — object survival probabilities → debris-cloud population forecast

Verdict: **PARTIALLY SUPPORTED** (post-hoc). Date 2026-11-04.
Source: `outputs/phase_e/phase_e_results.json` (`C2`).

## Hypothesis

Per-object survival probabilities produced by the **learned** lifetime module give better
forecasts of how many of a breakup cloud's fragments remain in orbit than the **physics**
expert's survival alone.

## Scientific rationale

A breakup cloud's population at time `D_k` is the sum of its fragments' survival
probabilities. If the lifetime module estimates per-fragment survival better than drag physics
alone, that improvement should aggregate into a better cloud count. This is a genuine
cross-domain use: a per-object lifetime output is consumed by a population-level debris
forecast.

## Mathematical formulation

For cloud `f` with fragments catalogued by `D_k = min_i(t0_i) + 365.25k`:

```
E[N_f(D_k)] = Σ_i S_i(D_k − t0_i)     over fragments i catalogued by D_k,
                                       excluding those censored before D_k
```

`S_i(τ) = P(T_i > τ)` is read two ways (`cosmos/ai/twin/couplings.py`):

- **raw** — linear interpolation of the predicted quantile function
  (`survival_from_quantiles`);
- **calibrated** — isotonic maps of `P(T ≤ a)` fitted on **tune-B** fragments over
  `AGE_GRID` (25 ages, 10 → 1826.25 d), interpolated in log-age (`calibrated_survival`).

Compared against the observed catalogue count. Endpoint: `|E[N] − N_obs| / N_catalogued`.

## Variables, units, identity

| Role | Variable | Units |
|---|---|---|
| Input | per-fragment lifetime quantiles | log10 days |
| Input | fragment age at `D_k` | days |
| Output | expected in-orbit fragment count | count |
| Reference | observed in-orbit count | count |
| Identity | fragment NORAD within cohort; cloud key = GCAT `Parent` | — |

## Assumptions

1. Fragment survival events are independent given their predicted distributions — used only
   for the **expected count** (which needs no independence) not for an interval on it, so this
   assumption is weak here.
2. The catalogue's in-orbit status at `D_k` is accurate (late decay reporting would bias it).
3. Isotonic calibration fitted on tune-B fragments transfers to test fragments.
4. Cloud membership via `Parent` is correct.
5. Ages are within the 5-year predictive cap; cloud-years beyond it are excluded in source.

## What the coupling changes

A **physical prediction** (expected population), not a decision.

## Leakage and circularity audit

- Fragments come from the lifetime study's **test** folds, so no fragment outcome was used in
  fitting the lifetime model. **PASS**.
- Isotonic calibrators are fitted on **tune-B** fragments, disjoint from test. **PASS**.
- Cloud-level comparison uses observed catalogue counts, independent of the lifetime model.
- Fragments censored before `D_k` are excluded from the predicted sum, matching the observed
  count's definition. Verified by `test_c2_saved_cloud_counts_are_physically_admissible`.

## Design

| Property | Value |
|---|---|
| Primary endpoint | mean absolute fractional count error |
| Primary contrast | `predcal_tabicl` − `predcal_physics_only` (same reading, model varies) |
| Unit of analysis | cloud-year (160) |
| Independent unit | breakup cloud (32) |
| Statistic | paired mean difference of absolute fractional error |
| Interval | paired cluster bootstrap by cloud, 4000 draws, seed 20261027 |
| Correction | BH within family: `coupling`, `deployed`, `calibration` |

Families are separated so that diagnostics neither dilute nor inflate the hypothesis test.

## Results

Negative difference = first model better.

| Family | Contrast | Error A | Error B | Δ | 95 % CI | p_adj |
|---|---|---|---|---|---|---|
| coupling | `predcal_tabicl` − `predcal_physics_only` | 0.0949 | 0.1452 | **−0.0503** | [−0.0805, −0.0190] | **0.0080** |
| coupling | `predcal_kumo` − `predcal_physics_only` | 0.1013 | 0.1452 | −0.0439 | [−0.0887, −0.0018] | 0.0770 |
| coupling | `pred_tabicl` − `pred_physics_only` | 0.1532 | 0.1295 | +0.0238 | [−0.0374, +0.0825] | 0.4115 |
| coupling | `pred_kumo` − `pred_physics_only` | 0.1628 | 0.1295 | +0.0333 | [−0.0287, +0.0902] | 0.3540 |
| **deployed** | `predcal_cosmos_gated` − `predcal_physics_only` | 0.1220 | 0.1452 | −0.0232 | [−0.0710, +0.0262] | **0.3870** |
| deployed | `pred_cosmos_gated` − `pred_physics_only` | 0.1547 | 0.1295 | +0.0253 | [−0.0333, +0.0829] | 0.3870 |
| calibration | `predcal_tabicl` − `pred_tabicl` | 0.0949 | 0.1532 | −0.0583 | [−0.0824, −0.0339] | **<0.0001** |
| calibration | `predcal_cosmos_gated` − `pred_cosmos_gated` | 0.1220 | 0.1547 | −0.0327 | [−0.0552, −0.0068] | **0.0300** |
| calibration | `predcal_physics_only` − `pred_physics_only` | 0.1452 | 0.1295 | +0.0158 | [−0.0121, +0.0406] | 0.2375 |

## Interpretation — three findings that must be read together

**1. The raw coupling is not better; it is worse.** Every raw contrast is positive (+0.024 to
+0.033): learned survival read directly off the quantile function underperforms physics-only
survival. None is significant, but the direction is uniform across models.

**2. The primary contrast is calibration-controlled, and recalibration is what unlocks the
learned model.** Both arms of `predcal_tabicl − predcal_physics_only` receive the *same*
isotonic treatment fitted on the same tune-B fragments, so that contrast is **not** confounded
with calibration — the learned model genuinely wins when both are calibrated.

What the calibration family adds is the *mechanism*: recalibration improves `tabicl` by
−0.0583 (p_adj < 0.0001) but does **not** help physics-only (+0.0158, n.s., physics survival
is already adequately calibrated at these ages). Combined with finding 1, the reading is that
the learned quantiles carry better **rank/shape** information about survival-at-age but are
**miscalibrated in level**; isotonic recalibration fixes the level and releases the advantage.
Without recalibration the learned model is unusable for this task.

**3. The deployed expert does not show the effect.** `cosmos_gated`, the system's own fused
expert, gives −0.0232 with p_adj = 0.387. The significance is carried by `tabicl` and
marginally `kumo`, neither of which is the deployed choice. **As configured, the system does
not realise this coupling benefit.**

## Statistical power

32 independent clouds. Only a large effect can reach significance; the surviving effect
(−0.050, roughly a 35 % relative reduction from 0.145 to 0.095) is large. Conversely, the
inconclusive contrasts cannot be read as evidence of no effect.

## Model-selection control

`tabicl` was not chosen after the fact: the original study's `C2_PAIRS` already named it. Two
additional learned experts and the deployed expert are reported so the result is not a
best-of-many selection.

## Limitations

1. Post-hoc analysis of already-scored test folds.
2. 32 clouds is a small number of independent units.
3. The benefit requires isotonic recalibration fitted on tune-B fragments; the raw
   reading is worse than physics-only.
4. The deployed expert does not show it.
5. Expected counts carry no interval of their own; only the error across clouds is resampled.
6. Observed counts inherit catalogue late-reporting error.
7. Two temporal origins pooled by cloud; not an independent temporal replication.

## Conclusion

**PARTIALLY SUPPORTED.** After recalibration, some learned lifetime experts forecast cloud
populations significantly better than physics-only survival (best: −0.050 fractional error,
p_adj = 0.008). But the raw readings are worse, most of the gain is recalibration rather than
the learned model, and the deployed expert shows no significant benefit.

Defensible claim: *with both arms isotonically recalibrated on the same held-out fragments,
learned survival from `tabicl` improves breakup-cloud population forecasts over physics-only
survival across 32 clouds (−0.050 fractional error, p_adj = 0.008); the advantage requires
recalibration, and it does not hold for the deployed `cosmos_gated` expert.*

Not defensible: *the lifetime module improves debris-cloud forecasting* — as deployed, it does
not.

### Recommended next experiments

1. **Promote or re-fuse the deployed expert.** The gated expert underperforms `tabicl` on this
   endpoint. Determining whether the gate is the cause requires re-fitting the fusion, which is
   a methodology change and needs approval.
2. **Independent temporal replication.** The two origins are pooled by cloud rather than
   treated as replicates. Scoring a third origin would test whether −0.050 reproduces.
3. **Calibration sensitivity.** Vary the `AGE_GRID` resolution and the tune-B fragment pool to
   check the recalibration is not over-fitted to one grid choice.
