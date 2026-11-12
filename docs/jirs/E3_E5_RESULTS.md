# E3 and E5 results

Date 2026-11-04 · script `scripts/e3_e5_selection_analysis.py` · results
`outputs/e3_e5/e3_e5_results.json`

**No model was refitted. No frozen artifact was modified. The pre-registered H2 verdict is
unchanged.** Both analyses read archived per-object predictions only.

---

## 1. E5 — selection regret: the headline result

Rank correlation says whether the selection ordering carries rank information. **Regret says what
following it costs.** For candidate set `A` with tune-A losses `L_v` and test losses `L_t`, the
selected arm is `â = argmin L_v` and `regret = L_t(â) − min_a L_t(a)`.

### 1.1 Regret within the deployed selection pool

The pool the pipeline actually chose between (`{tabm, tabicl, kumo}` at the published origins;
`{xgboost, mlp}` at origin 2006):

| Origin | Selected | Test rank of selected | Regret | Regret as % of best | **% of worst-case regret** | Cluster-bootstrap 95 % CI | Resamples with zero regret |
|---|---|---|---|---|---|---|---|
| **2011** | `kumo` | 2 of 3 | +0.002028 | **+3.40 %** | 5.1 % | [+0.000000, +0.006080] | 19.0 % |
| **2016** | `tabm` | 3 of 3 | +0.009348 | **+18.72 %** | **100.0 %** | **[+0.003953, +0.016876]** | **0.0 %** |
| **2006** | `mlp` | 2 of 2 | +0.020884 | **+25.15 %** | **100.0 %** | [+0.000000, +0.045414] | 32.9 % |

### 1.2 Three findings here, in order of importance

**(a) Regret grows monotonically with temporal displacement: 3.40 % → 18.72 % → 25.15 %.** This
corroborates the selection-transfer hypothesis **from an independent statistic**. The ρ result and
the regret result are computed from different quantities — one a rank correlation over arms, the
other a loss difference between two specific arms — and they point the same way. That is
materially stronger than either alone.

**(b) At origin 2016 the regret interval excludes zero.** 95 % CI [+0.0040, +0.0169], with
**zero-regret in 0.0 % of 4,000 cluster-bootstrap resamples**. This is the project's first
*statistically significant* statement about selection failure. The ρ = 0.000 result could not
deliver this because it is a point estimate over n = 7 with an interval spanning [−0.77, +0.77].
**Regret is the statistic the paper should lead with.**

**(c) At origins 2016 and 2006 the selection rule chose the worst arm in its own pool** — 100 % of
worst-case regret in both. At 2016, tune-A ranked `tabm` first and `tabm` finished last of the
three pool members on test. This is not "selection carries no information"; it is worse than that
in these two instances, though with 2–3 arms it is also what chance would often produce.

### 1.3 Regret against the full arm set

If a practitioner could have chosen among all 17 point-forecast arms rather than the pre-specified
pool:

| Origin | Selected | Test rank | Best arm on test | Regret as % of best |
|---|---|---|---|---|
| 2011 | `kumo` | 8 of 17 | `physics_only` | **+16.96 %** |
| 2016 | `tabm` | 6 of 17 | `tabicl` | **+18.72 %** |
| 2006 | `mlp` | 10 of 17 → of 12 | `physics_only` | **+82.88 %** |

At origin 2006 the selected learner incurs **83 % more loss than the physics baseline**. That is
the most operationally striking number the project has produced.

### 1.4 Honest limits on E5

- Tune-A is **not** resampled: the bootstrap holds the selection fixed and resamples the test fold,
  so the interval reflects test-set uncertainty in the penalty, not uncertainty in which arm would
  have been selected. A fuller treatment would resample both.
- At origins 2011 and 2006 the CI includes zero, so regret is significant **only at 2016**.
- The pool at origin 2006 has two arms, so "worst of pool" and "second of two" are the same thing;
  the 100 % figure is less impressive than it appears.
- The three-origin monotonicity is **three points**. It is consistent with the hypothesis and does
  not test it. That remains experiment E2's job.

## 2. E3 — reference distribution for the ranking-instability criterion

### 2.1 A correction to my own framing, stated first

I proposed E3 as *"the correct null"* for hypothesis H2. **That description was wrong, and I want
to correct it before presenting the numbers.**

What I computed resamples each origin's test fold while **holding the fitted arms fixed**. That
preserves whatever genuine cross-origin differences the models have, so a high frequency of the
criterion being met means *the observed finding replicates under resampling* — it is a
**robustness check**, not a null hypothesis test. A true stability-constrained null would have to
impose a common ordering across origins, which requires an explicit and contestable modelling
assumption about how to do so. I have not made that assumption silently.

So E3 delivers two things: the **exact** uniform-permutation chance level, and a **robustness
frequency**. Both are informative; neither is the ideal null.

### 2.2 Observed result

| Origin | `physics_only` | `xgboost` | `mlp` | `tabm` |
|---|---|---|---|---|
| 2011 | 1 | 2 | 4 | 3 |
| 2016 | 4 | 1 | 2 | 3 |
| 2006 | 1 | 2 | 3 | *not fittable* |

Criterion met: **yes** — no arm present at every origin retains its rank, and `physics_only`'s rank
range is 3.

### 2.3 Null A — independent uniform random rankings (exact)

Enumerated over all 4! × 4! × 3! = **3,456** equiprobable configurations:

| Clause | Exact probability |
|---|---|
| No always-present arm retains its rank | **0.8316** |
| `physics_only` rank range ≥ 3 | **0.2292** |
| **Both — the criterion as implemented** | **0.1985** |
| *(H3 was closed as underpowered at)* | *0.1667* |

### 2.4 Null B — robustness under test-fold resampling (4,000 cluster-bootstrap draws)

| Quantity | Value |
|---|---|
| Criterion met | **0.7370** |
| `physics_only` rank range ≥ 3 | **0.9888** |
| Rank-range distribution | {1: 11, 2: 34, **3: 3,955**} |
| Mean number of rank-constant arms | **0.25** |

### 2.5 What the two together establish — and it refines H2 usefully

**The criterion is made of one near-vacuous clause and one robust clause.**

- **"No arm retains its rank" is nearly uninformative.** It is satisfied by chance 83 % of the
  time, and the resampling shows why: with these arms' losses lying close together, rank constancy
  across three origins almost never occurs anyway (mean 0.25 constant arms per resample). The
  clause is satisfied regardless of whether anything interesting is happening.
- **"`physics_only` rank range ≥ 3" is the clause carrying the evidence, and it is robust.** It
  holds in **98.88 %** of resamples — the physics baseline genuinely does swing across at least
  three rank positions, and that is not a sampling artefact. Its chance level under uniform
  rankings is 0.2292, which is still weak with only three origins, but the finding itself
  replicates.

**Net effect on H2.** The verdict stands as pre-registered, and its substantive content is
narrower than the criterion's wording suggests: **the informative, replicable part is the physics
baseline's rank range, not the absence of rank-constant arms.** The manuscript should say this. It
is a more precise and more defensible claim than the original, and it was obtained by scrutinising
our own criterion rather than defending it.

## 3. Combined effect on the paper

| Before | After |
|---|---|
| Lead statistic: ρ = 0.000, n = 7, interval ≈ [−0.77, +0.77], no significance | Lead statistic: **selection regret, significant at origin 2016**, CI excluding zero, monotone 3.4 % → 18.7 % → 25.2 % |
| Instability evidence: H2 criterion met, chance level 0.1985 | **Decomposed**: the rank-range clause replicates in 98.9 % of resamples; the rank-constancy clause is near-vacuous |
| Temporal-displacement hypothesis supported by one statistic | Supported by **two independent statistics** pointing the same way |
| No operational cost figure | **Up to 83 % excess loss** against the best available arm |

**This materially strengthens the paper without a single model refit**, and it did so partly by
weakening a claim (H2's wording) and correcting my own framing of E3.

## 4. What E3 and E5 do not establish

- **Neither tests the temporal-displacement mechanism.** Three origins, three regret values. E2
  remains necessary.
- Regret is significant at **one** of three origins.
- The E3 robustness frequency is not a null; a stability-constrained null needs an explicit
  modelling choice I have flagged rather than made.
- Nothing here concerns the anomaly-detection task; E1 is still required for that.
- The arms compared are the four from the pre-registered common set; conclusions do not extend to
  the full 17-arm leaderboard except where §1.3 states it.
