# E12 — same-learner ablation: does C1's family effect depend on origin or on learner?

Date: 2026-11-04. Conclusion: **NOT REPRODUCIBLE — the C1 family effect is learner-specific.**

```bash
python scripts/e12_same_learner_c1.py --n-boot 4000      # exit 0
```

Outputs: `outputs/e12_same_learner/e12_results.json`, `e12_ablation_table.csv`.

## Objective

Phase E found the family-feature effect significant at origin 2016 (learner `tabm`) and not at
2011 (learner `kumo`). Origin and learner were confounded. E12 breaks that confound.

## Method — no refit was required

The lifetime study cached per-seed predictions for `mlp` **and its complete ablation set at
both origins**. Reconstructing the study's seed ensemble from that cache
(`np.sort(np.mean(seeds, 0), 1)`, exactly as `run.py` does) reproduces the **published**
`mlp__q` arrays with a maximum absolute difference of **0.0** at both origins.

A re-analysis was therefore preferred to the approved refit: it introduces no methodology
change, cannot diverge from the published protocol, and consumes no compute. The approval for
E12 is satisfied more conservatively than requested.

### Fairness conditions

| Requirement (from the approval) | Status |
|---|---|
| Same learner for both origins | **met** — `mlp` at 2011 and 2016 |
| Consistent feature definitions | **met** — features differ only by the `family` group, 53 → 45 columns |
| Identical preprocessing | **met** — same `matrices()` construction |
| Equivalent training/selection procedure | **met** — ablated arm has `tuned=False` and inherits the full arm's tuned hyperparameters, verified from `fit_json`; identical for all four cells |
| Consistent evaluation protocol | **met** — same target, same `known5` censoring mask, same pinball definition |
| Comparable tuning budget | **met** — same `n_trials`, same 5 seeds (0–4) |
| Temporal and launch-family separation preserved | **met** — unchanged study splits; folds grouped by launch family |
| Seeds and configurations recorded | **met** — in `e12_results.json`, with each arm's SHA-256 |
| Per-object losses and cluster-aware intervals | **met** — paired cluster bootstrap by launch family, 4000 draws, seed 20261027 |
| Multiple-comparison correction | **met** — Benjamini-Hochberg across the 5 ablations within each cell |
| No overwriting of historical experiments | **met** — new directory; caches read only |

### The one limitation, stated not hidden

`mlp`'s **tuned hyperparameters differ between origins** (2016: depth 4, width 512; 2011:
depth 3, width 128) because each origin tuned on its own tune-A fold, as the published protocol
prescribes. The learner **algorithm** is held constant; its tuned settings are not. Forcing
identical settings across origins would depart from the protocol that produced every other
published arm, so it was not done.

## Results — the 2 × 2 design

`no_family` effect; positive = removing family features is worse = family features help.

| Cell | Full pinball | Effect | Relative | 95 % CI | p | p_adj | Significant |
|---|---|---|---|---|---|---|---|
| **tabm@2016** (published) | 0.05929 | **+0.005567** | +9.39 % | [+0.001475, +0.010169] | 0.0065 | **0.0108** | **yes** |
| **mlp@2016** (same origin, other learner) | 0.05778 | +0.002635 | +4.56 % | [−0.002530, +0.006804] | 0.2500 | 0.2500 | no |
| **kumo@2011** (published) | 0.06161 | +0.002381 | +3.86 % | [−0.005765, +0.010294] | 0.6060 | 0.6060 | no |
| **mlp@2011** (same learner, other origin) | 0.11466 | −0.051372 | −44.80 % | [−0.112111, +0.000681] | 0.0775 | 0.1937 | no |

**1 of 4 cells is significant.** Signs are not consistent.

### With the learner held constant (`mlp`): the family effect is significant at neither origin

- `mlp@2016`: +0.00264, p_adj = 0.250 — not significant.
- `mlp@2011`: −0.0514, p_adj = 0.194 — not significant, and **opposite in sign**.

### The most informative single comparison

At **origin 2016**, two learners of **comparable quality** (`mlp` pinball 0.0578, `tabm`
0.0593 — `mlp` is marginally *better*) reach **opposite conclusions** about family features:
`tabm` says they help significantly (+9.4 %), `mlp` says they do not (+4.6 %, n.s.). Same data,
same split, same protocol, same target. The difference is the learner.

### `mlp@2011` has low diagnostic value — and this must be stated

Its full-arm pinball is 0.1147, nearly **2×** `kumo@2011`'s 0.0616, and **every** feature-group
removal improved it (−21 % to −45 %). That pattern is the signature of a poorly-fitted model
that cannot exploit the full feature set, not evidence that the features are harmful. The
−44.8 % `no_family` point estimate should **not** be read as "family features hurt". It should
be read as "this cell's baseline is too weak to be informative".

Excluding that cell does not rescue C1: the two remaining non-published cells
(`mlp@2016`, `kumo@2011`) are both non-significant.

## Incidental finding — feature-importance conclusions are learner-dependent

The `no_physics` group reverses sign **at the same origin** depending on the learner:

| Cell | `no_physics` effect | Relative | p_adj | Reading |
|---|---|---|---|---|
| tabm@2016 | **−0.004962** | −8.37 % | **<0.0001** | removing physics features **improved** the model |
| mlp@2016 | **+0.006611** | +11.44 % | **0.0163** | removing physics features **worsened** the model |

Two comparably-performing learners, the same data, and **two significant conclusions in
opposite directions** about the same feature group.

This is a methodological result in its own right: **single-learner feature ablations are not a
reliable guide to feature value in this setting.** Any claim of the form "feature group X
improves orbital lifetime prediction" needs replication across learners, not only across
temporal origins. The published C1 result rested on one learner per origin and is therefore
not robust in this sense.

## Full ablation detail

| Cell | no_family | no_physics | no_design | no_space_weather | plus_rcs_2026 |
|---|---|---|---|---|---|
| tabm@2016 | **+9.39 %*** | **−8.37 %*** | **+11.91 %*** | +6.46 % | +12.05 % |
| mlp@2016 | +4.56 % | **+11.44 %*** | **+10.93 %*** | **+12.05 %*** | +5.65 % |
| kumo@2011 | +3.86 % | +3.65 % | +1.34 % | +1.42 % | −6.13 % |
| mlp@2011 | −44.80 % | −21.35 % | −25.98 % | −28.05 % | +6.51 % |

`*` significant after BH within the cell. Relative to each cell's own full-arm pinball.

The only group significant in a consistent direction across both origin-2016 cells is
`no_design` (+10.9 % to +11.9 %), i.e. design features (mass, dimensions) help — which is
physically unsurprising and is the most robust feature finding available.

## Consequence for C1

C1's verdict is **downgraded**:

| Stage | Verdict |
|---|---|
| Phase E (origin replication only) | PARTIALLY SUPPORTED |
| **E12 (learner held constant)** | **NOT REPRODUCIBLE** |

Defensible claim: *in one of four (origin, learner) cells, removing family features
significantly worsened lifetime prediction (+9.4 %, p_adj = 0.011). The effect did not
reproduce with a comparably-performing learner at the same origin, and feature-group
conclusions in this setting are learner-dependent.*

Not defensible: *family statistics improve orbital lifetime prediction.* The evidence does not
support it.

## Limitations

1. Post-hoc: all these test folds were scored by the original study.
2. Only one common learner (`mlp`) has a full ablation set at both origins; a third learner
   would strengthen the conclusion.
3. `mlp`'s tuned settings differ between origins (protocol-mandated).
4. `mlp@2011` is a weak baseline and contributes little information.
5. Two temporal origins only.
6. No external dataset.

## Status

| Item | Status |
|---|---|
| Learner/origin confound resolved | **PASS** |
| Same-learner comparison achieved without refitting | **PASS** — cache verified against published arrays to 0.0 |
| Fairness conditions met | **PASS**, with the tuned-settings limitation documented |
| C1 hypothesis | **NOT REPRODUCIBLE** |
| Historical experiments preserved | **PASS** — caches read only, new output directory |
