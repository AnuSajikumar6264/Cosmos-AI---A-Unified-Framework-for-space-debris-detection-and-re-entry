# Phase E — controlled coupling ablations

Date: 2026-11-04. Branch `product/mission-intelligence-console`. Baseline HEAD `78ee339`.

```bash
python scripts/phase_e_coupling_ablations.py --n-boot 4000     # exit 0
python -m pytest tests/test_phase_e.py -q                      # 18 passed, exit 0
```

Outputs: `outputs/phase_e/phase_e_results.json`, `outputs/phase_e/coupling_ablation_table.csv`.

## Headline answer to the central research question

> **Does evidence-aware integration of satellite health, orbital lifetime, debris and risk
> intelligence provide measurable value beyond running the subsystems independently?**

**NOT DEMONSTRATED.**

No coupling shows a benefit that reproduces across independent replicates, and the one
coupling with a statistically supported effect does not show it for the system's own deployed
model. This is a negative-to-mixed result and is reported as such.

| Coupling | Verdict | Basis |
|---|---|---|
| C1 family statistics → lifetime | **NOT REPRODUCIBLE** (revised by E12) | significant in 1 of 4 (origin, learner) cells; with the learner held constant, significant at neither origin |
| C2 survival → debris-cloud forecast | **PARTIALLY SUPPORTED** | significant for `tabicl` (p_adj = 0.008) but **not for the deployed `cosmos_gated`** (p_adj = 0.387); effect contingent on recalibration |
| C3 operational status → decay regime | **INCONCLUSIVE** | both prospective contrasts have intervals including zero |
| C4 health flags → conjunction escalation | **NOT EVALUABLE** | the required identity join does not exist in any available dataset |
| Combined chain | **NOT EVALUABLE** | no shared endpoint exists across the three couplings' populations |

## Method, and what is new here

This is a **re-analysis of saved predictions**. No model was retrained, refitted or rescored,
so nothing published was altered. What Phase E adds beyond the original studies:

1. **Real bootstrap p-values.** The original `ablation_effects_test.csv` stores intervals but
   no p-values, and an interval alone cannot be multiplicity-corrected. Per-object pinball
   losses were recomputed from the saved test quantiles using the study's own `loss_vec`
   definition, then paired-bootstrapped by launch family.
2. **Multiple-comparison correction.** Benjamini-Hochberg within each family of related tests.
   The original studies reported each contrast's interval without correcting for how many
   contrasts were examined.
3. **Cluster-aware paired contrasts** for C2, replacing the single stored comparison which
   mixed model choice with calibration treatment.
4. **A deployed-model check** for C2, asking whether the effect holds for the expert the
   system actually uses.

Every addition is **more conservative** than the original report. A reproducibility test
(`test_saved_c1_reproduces_the_original_study_interval`) asserts the recomputed effects match
the published values to 1e-9, so the re-analysis is measuring the same thing.

**Post-hoc status.** All of these test sets were scored by the earlier studies. Everything here
is a post-hoc re-analysis, not a confirmatory test, and must be reported that way.

## Experimental design

| Property | C1 | C2 | C3 |
|---|---|---|---|
| Primary endpoint | pinball loss of log10 capped lifetime | abs. error of expected in-orbit count ÷ fragments catalogued | Brier score of P(re-entry ≤ 72 d) |
| Unit of analysis | catalogued object | cloud-year | payload |
| Independent unit | launch family | breakup cloud | launch |
| Resampling | paired cluster bootstrap, 4000 draws | paired cluster bootstrap, 4000 draws | launch-cluster bootstrap (study's own) |
| No-coupling baseline | same learner, family features removed | physics-only survival, same reading | status-blind policy, same information |
| Correction | BH across 5 ablations per origin | BH within family (coupling / deployed / calibration) | BH across 2 prospective contrasts |
| Replicates | 2 temporal origins (2011, 2016) | 2 origins pooled by cloud | 1 window |
| Sample | 2,667 / 2,978 objects; 435 / 621 families | 160 cloud-years, 32 clouds | 13,794 payloads, 182 events, 1,070 launches |

Arms differ in exactly one factor wherever the saved artifacts allow it. The one unavoidable
exception is C1, where the selected learner differs between origins — stated as a confound,
not averaged away.

## C1 — family statistics → lifetime

Positive effect = the ablation is worse, i.e. family features help.

| Origin | Learner | Effect | 95 % CI | p | p_adj (BH) | Significant |
|---|---|---|---|---|---|---|
| 2016 | tabm | **+0.005567** | [+0.001475, +0.010169] | 0.0065 | **0.0108** | **yes** |
| 2011 | kumo | +0.002381 | [−0.005765, +0.010294] | 0.6060 | 0.6060 | no |

The sign is consistent (both positive) but only one origin reaches significance, and the
magnitude at 2016 is 9.4 % of that arm's full-model pinball loss (0.00557 / 0.0593).

**Verdict: NOT REPRODUCIBLE** after E12 held the learner constant — originally PARTIALLY
SUPPORTED on origin replication alone. See [`C1_EVALUATION.md`](C1_EVALUATION.md) and
[`E12_SAME_LEARNER_C1.md`](E12_SAME_LEARNER_C1.md).

### Incidental finding — physics features reverse sign across origins

| Origin | `no_physics` effect | 95 % CI | p_adj | Reading |
|---|---|---|---|---|
| 2016 | **−0.004962** | [−0.008459, −0.002143] | **<0.0001** | removing physics features **improved** the model |
| 2011 | +0.002247 | [+0.000218, +0.003908] | 0.1700 | physics helped, not significant after correction |

This is a sign reversal on a feature group central to the project's framing, and it is
significant in the direction *against* the physics features at origin 2016. It is not part of
the coupling hypothesis but it is a material finding about temporal instability of the feature
set, and it belongs in any manuscript that claims physics-informed features help.

## C2 — survival → debris-cloud forecast

Mean absolute fractional count error; negative difference = the first model is better.

| Family | Contrast | Error A | Error B | Difference | 95 % CI | p_adj |
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

Three things must be read together:

1. **Every raw contrast goes the wrong way.** Without recalibration the learned survival
   readings are *worse* than physics-only (+0.024 to +0.033, all inconclusive). The learned
   lifetime quantiles are miscalibrated for this task.
2. **The primary contrast is calibration-controlled.** Both arms of
   `predcal_tabicl − predcal_physics_only` get the same isotonic treatment from the same
   tune-B fragments, so the learned model genuinely wins when both are calibrated.
   Recalibration helps `tabicl` (−0.058) but not physics-only (+0.016, n.s.), which identifies
   the *mechanism*: the learned quantiles carry better rank/shape information but are
   miscalibrated in level, and recalibration releases that advantage.
3. **The deployed expert does not show the effect** (p_adj = 0.387). The significance is
   carried by `tabicl` and, marginally, `kumo` — neither of which is the system's choice.

So the honest statement is: *with both arms recalibrated, `tabicl` survival produces better
cloud-population forecasts than physics-only survival; the advantage requires recalibration,
and the deployed expert does not realise it.*

**Verdict: PARTIALLY SUPPORTED.** See [`C2_EVALUATION.md`](C2_EVALUATION.md).

## C3 — operational status → decay regime

Prospective policies only (information available at the as-of date).

| Policy | Brier | ECE | Mean p |
|---|---|---|---|
| physics, status-blind | 0.017926 | 0.02674 | 0.03916 |
| previous-window base rate, status-blind | 0.013020 | 0.00054 | 0.01265 |
| **twin, status-aware** | **0.012522** | 0.00084 | 0.01343 |

| Contrast | Mean ΔBrier | 95 % CI | Verdict |
|---|---|---|---|
| status-aware − physics status-blind | −5.40e−03 | [−1.20e−02, +6.41e−04] | INCONCLUSIVE |
| status-aware − base-rate status-blind | −4.98e−04 | [−1.23e−03, +8.31e−05] | INCONCLUSIVE |

Both intervals include zero. The status-aware policy's entire advantage over the physics
policy is reproduced by a status-blind base rate, and the residual gain over that base rate is
−0.0005 Brier with an interval spanning zero.

Observed event rates do differ by status (non-operational 0.106 vs operational 0.012), so the
status variable carries real information — but with 182 events across 1,070 launches, the
design has insufficient power to show that acting on it beats a simple base rate.

**Verdict: INCONCLUSIVE.** See [`C3_EVALUATION.md`](C3_EVALUATION.md).

## C4 — health flags → conjunction escalation

**NOT EVALUABLE**, and this is a property of the data, not of the effort spent.

| Source | Identity key | Spacecraft identifiable | Holds telemetry | Holds CDMs |
|---|---|---|---|---|
| ESA-ADB telemetry | anonymised mission + channel | **no** | yes | no |
| ESA Kelvins CAC | positional event index | **no** | no | yes |
| CelesTrak/GCAT catalogue | NORAD ID | yes | **no** | **no** |

Joinable pairs: **0**. The two sources holding the needed variables are anonymised by
construction; the only identifiable source holds neither variable. The hypothesis cannot be
tested — not merely that it has not been tested.

A plausible-looking escalation could be produced by pairing unrelated health and conjunction
records. That would be fabricated evidence and is not done. In the orchestrated pipeline and
the product, C4 abstains with a recorded reason, and physical collision probability is never
modified by health evidence.

See [`C4_EVALUATION.md`](C4_EVALUATION.md).

## Why there is no combined-integration arm

A joint C1+C2+C3 arm is **not evaluable on any single endpoint**:

- C1 is scored by pinball loss over catalogued objects, clustered by launch family;
- C2 by fractional count error over cloud-years, clustered by breakup cloud;
- C3 by Brier score over LEO payloads, clustered by launch.

Different populations, different units of analysis, different independent units. No metric
exists that all three could jointly improve. **Constructing a single aggregate score to declare
integration successful would make the result an artefact of the aggregation**, and is refused.

What can be said is bounded: each coupling was tested on its own endpoint against its own
no-coupling baseline, and none produced a reproducible improvement.

## Threats to validity

| Threat | Status |
|---|---|
| Post-hoc analysis of already-scored test sets | **Present and disclosed.** Everything here is exploratory re-analysis. |
| Learner confounded with temporal origin (C1) | **Present.** The two origins are not exchangeable replicates. |
| Model selection within C2 | Mitigated: several learned experts reported, not just the best; the deployed one reported separately. |
| Small number of independent clusters (C2: 32 clouds) | **Present.** Only a large effect could reach significance. |
| Low event count (C3: 182 events) | **Present.** The design cannot resolve small Brier differences. |
| Multiplicity | Mitigated by BH within families. |
| Dependence between observations | Mitigated by cluster bootstrap; `test_paired_bootstrap_widens_when_observations_are_clustered` shows ignoring it would narrow intervals >3×. |
| Circularity in C3's in-window recalibration | Mitigated: the in-window pair is reported as a diagnostic and is excluded from the coupling verdict. |

## What this means for the contribution

The cross-domain coupling hypothesis — the project's original framing — is **not supported by
reproducible evidence on the available data**. A manuscript claiming that COSMOS-AI's
integration improves prediction would be refuted by its own ablations.

The defensible contribution is narrower:

1. A catalogue-scale, forward-in-time orbital lifetime and re-entry benchmark with
   censoring-aware targets and cluster-aware intervals.
2. An evidence-graded architecture that abstains where evidence is insufficient, with typed
   contracts, provenance digests and the physical/operational separation enforced in code and
   verified by tests.
3. A set of honest negative and mixed findings: C1's temporal instability, C2's dependence on
   recalibration rather than the learned model, C3's non-superiority to a base rate, C4's
   unevaluability, and the sign reversal of the physics feature group.

Point 3 has genuine scientific value. "We built the coupling, measured it properly, and it did
not reproduce" is a publishable finding, and it is much harder for a reviewer to disprove than
an unsupported positive claim.

See [`INTEGRATION_VALUE_ASSESSMENT.md`](INTEGRATION_VALUE_ASSESSMENT.md).
