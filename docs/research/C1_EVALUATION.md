# C1 evaluation — breakup/launch-family statistics → orbital lifetime prediction

Verdict: **NOT REPRODUCIBLE** (post-hoc). Date 2026-11-04.

> **Superseded by E12.** This report's original verdict was PARTIALLY SUPPORTED, based on
> replication across temporal origins only. [`E12_SAME_LEARNER_C1.md`](E12_SAME_LEARNER_C1.md)
> held the learner constant and found the effect significant at **neither** origin, and found
> that a comparably-performing learner at origin 2016 does **not** reproduce it. The verdict
> below is downgraded accordingly; the numbers are unchanged.
Source: `outputs/phase_e/phase_e_results.json` (`C1`).

## Hypothesis

Family-level statistics available **before** the prediction epoch — how many siblings of an
object's launch or breakup family have already decayed, and their decay statistics — improve
orbital lifetime prediction over the same model trained without them.

## Scientific rationale

Objects from one launch or one fragmentation event share release conditions, construction and
an initial orbit. The observed decay of already-decayed siblings is therefore an empirical
proxy for the family's effective area-to-mass distribution and drag environment — information
not otherwise available for an object whose own mass and dimensions are unknown or flagged.
This is a **statistical** rationale (shared latent parameters), not a claim that one object's
decay physically influences another's.

## Variables, units and time references

| Role | Variable | Units | Time reference |
|---|---|---|---|
| Input | `launch_family_*`, `breakup_family_*` sibling counts and decay statistics | counts, days | computed only from outcomes **before** the prediction epoch `t0` |
| Input | orbit, age, design, space weather, physics features | km, days, sfu, — | as of `t0` |
| Target | log10 capped time-to-decay | log10 days, cap 1826.25 d | from `t0` |
| Identity | GCAT `JCAT` / NORAD; family key `Launch_Tag` or `Parent` | — | — |

Implementation: `cosmos/ai/lifetime/catalogue.py:family_features`; feature group `"family"` in
`cosmos/ai/lifetime/run.py:FULL`; ablation arm `ABLATIONS["no_family"]`.

## Assumptions

1. Family membership is correctly assigned by the catalogue (`Launch_Tag`, `Parent`).
2. Sibling outcomes used as features are restricted to times before `t0` — enforced by
   `family_features` operating on the pre-`t0` cohort. This is the leakage-critical assumption.
3. Objects within a family share latent drag parameters to a useful degree.
4. The capped target treats "survives past 5 years" as censored at the cap, not as an exact
   lifetime.

## What the coupling changes

It changes a **physical prediction** (time-to-decay), not a decision. It therefore requires the
strongest evidence standard of the four couplings.

## Leakage and circularity audit

- Family features use only pre-`t0` sibling outcomes. **PASS** by construction.
- Train/tune/test folds are split **by launch family** (`run.py` folds families, not objects),
  so an object's siblings cannot straddle the split. **PASS** — this is essential: an
  object-level split would leak family outcomes directly.
- The ablation refits with the selected learner's tuned settings, so hyperparameter tuning is
  not re-run on the ablated feature set. This slightly **favours the full model** and is a
  conservative direction for the hypothesis. Disclosed.
- The repository's own `leak_check.json` exists at
  `outputs/benchmarks/reentry_lifetime/leak_check.json`.

## Design

| Property | Value |
|---|---|
| Primary endpoint | pinball loss of log10 capped lifetime, objects with a known 5-year outcome |
| Arms | full feature set vs `no_family` (one factor removed) |
| Unit of analysis | catalogued object |
| Independent unit | launch family |
| Statistic | paired per-object loss difference, mean |
| Interval | cluster bootstrap by launch family, 4000 draws, seed 20261027 |
| Correction | Benjamini-Hochberg across the 5 ablation arms within each origin |
| Replicates | two temporal origins: 2011 and 2016 |

## Results

Positive effect = ablation worse = family features help.

| Origin | Learner | Objects | Families | Full pinball | `no_family` effect | 95 % CI | p | p_adj | Significant |
|---|---|---|---|---|---|---|---|---|---|
| 2016 | tabm | 2,978 | 621 | 0.05929 | **+0.005567** | [+0.001475, +0.010169] | 0.0065 | **0.0108** | **yes** |
| 2011 | kumo | 2,667 | 435 | 0.06161 | +0.002381 | [−0.005765, +0.010294] | 0.6060 | 0.6060 | no |

Relative effect at origin 2016: **9.4 %** of the full model's pinball loss.

### Full ablation family (context for the correction)

| Origin | Ablation | Effect | 95 % CI | p_adj | Significant |
|---|---|---|---|---|---|
| 2016 | no_design | +0.007064 | [+0.003580, +0.012249] | <0.0001 | yes |
| 2016 | **no_family** | +0.005567 | [+0.001475, +0.010169] | 0.0108 | **yes** |
| 2016 | no_physics | **−0.004962** | [−0.008459, −0.002143] | <0.0001 | yes (**wrong direction**) |
| 2016 | no_space_weather | +0.003831 | [−0.005473, +0.012467] | 0.4215 | no |
| 2016 | plus_rcs_2026 | +0.007147 | [−0.001039, +0.015550] | 0.1031 | no |
| 2011 | no_design | +0.000824 | [−0.000072, +0.001657] | 0.1925 | no |
| 2011 | no_family | +0.002381 | [−0.005765, +0.010294] | 0.6060 | no |
| 2011 | no_physics | +0.002247 | [+0.000218, +0.003908] | 0.1700 | no |
| 2011 | no_space_weather | +0.000872 | [−0.001632, +0.003734] | 0.6060 | no |
| 2011 | plus_rcs_2026 | −0.003774 | [−0.007249, +0.001049] | 0.2050 | no |

## Statistical analysis

Effects are paired per-object loss differences, so the two arms see identical objects. Launch
families are the resampling unit because objects within a family are dependent; treating rows
as independent would narrow the interval substantially (demonstrated in
`tests/test_phase_e.py::test_paired_bootstrap_widens_when_observations_are_clustered`).

BH correction is applied across the 5 ablation arms per origin. At origin 2016 `no_family`
survives correction (0.0065 → 0.0108). At origin 2011 it does not come close (0.606).

## Confounds

- **Learner is confounded with origin.** Origin 2016 used `tabm`, origin 2011 used `kumo`,
  because each origin's learner was selected on its own tuning fold. The two origins are
  therefore **not exchangeable replicates**: a difference between them may reflect the learner,
  the epoch's space-weather regime, the cohort composition, or any combination.
- Origin 2011 has fewer families (435 vs 621) and a wider `no_family` interval, so lower power
  is a plausible partial explanation for the non-significance — but the point estimate is also
  2.3× smaller, so power alone does not account for it.

## Limitations

1. Post-hoc: both test folds were scored by the original study before this analysis.
2. Two origins only, and they are not independent replicates of one experiment.
3. The effect is measured on a capped target; behaviour beyond 5 years is censored.
4. The ablation inherits the full model's tuned hyperparameters.
5. No external dataset confirms the effect.

## Conclusion (revised after E12)

**NOT REPRODUCIBLE.** The effect is significant in 1 of 4 (origin, learner) cells. Holding the
learner constant, it is significant at neither origin; at origin 2016 a comparably-performing
learner (`mlp`, pinball 0.0578 vs `tabm` 0.0593) gives +4.6 % and is not significant.

Defensible claim: *in one of four (origin, learner) cells, removing family features
significantly worsened lifetime prediction (+9.4 %, p_adj = 0.011); the effect did not
reproduce with a different comparably-performing learner at the same origin.*

Not defensible: *family statistics improve lifetime prediction.*

### Completed follow-up

E12 resolved the confound **without refitting**: the study had cached `mlp` and its full
ablation set at both origins, and the reconstruction reproduces the published arrays to 0.0.
See [`E12_SAME_LEARNER_C1.md`](E12_SAME_LEARNER_C1.md).
