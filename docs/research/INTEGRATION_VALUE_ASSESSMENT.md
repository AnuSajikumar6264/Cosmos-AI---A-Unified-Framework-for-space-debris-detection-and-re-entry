# Integration value assessment

Date: 2026-11-04. Evidence: `outputs/phase_e/phase_e_results.json`,
[`PHASE_E_COUPLING_ABLATIONS.md`](PHASE_E_COUPLING_ABLATIONS.md).

## The question

> Does evidence-aware integration of satellite health, orbital lifetime, debris and risk
> intelligence provide measurable scientific or decision-making value beyond running the
> individual subsystems independently?

## The answer

**NOT DEMONSTRATED.**

No coupling produced an improvement that reproduces across independent replicates, and the one
coupling with a statistically supported effect does not show it for the system's own deployed
configuration.

| Coupling | Verdict | Reproduces? | Holds for deployed system? |
|---|---|---|---|
| C1 family → lifetime | **NOT REPRODUCIBLE** (E12) | **No** — 1 of 4 (origin, learner) cells | learner-specific |
| C2 survival → cloud forecast | PARTIALLY SUPPORTED | not tested across replicates | **No** — deployed expert n.s. |
| C3 status → decay regime | INCONCLUSIVE | single window only | not separable from a base rate |
| C4 health → escalation | NOT EVALUABLE | — | abstains by design |

## Why this is a defensible finding rather than a failure

The experiments were designed so that a null result is informative:

- arms differ in **one factor** wherever the artifacts allow;
- the **no-coupling baseline** is the same model or policy with the coupling removed, not a
  weaker strawman;
- intervals resample the **correct independent unit** (launch family, breakup cloud, launch) —
  ignoring that dependence would narrow intervals by more than 3× and would have manufactured
  significance;
- multiplicity is corrected within each family of tests;
- the **deployed** configuration is reported separately from the best-performing one.

Under that design, three of four couplings fail to show reproducible benefit. That is evidence
about the hypothesis, not an absence of evidence.

## The honest positive findings

Integration did not improve predictions, but the work produced results worth reporting:

1. **C2 mechanism.** Learned lifetime quantiles carry better rank/shape information about
   survival-at-age than drag physics, but are **miscalibrated in level**. Raw, they are *worse*
   than physics-only (+0.024 to +0.033 fractional count error); isotonically recalibrated on
   held-out fragments, `tabicl` becomes better by −0.050 (p_adj = 0.008). Recalibration helps
   the learned experts and does not help physics-only, which is already adequately calibrated.
   This is a specific, testable statement about where learned lifetime models fail.

2. **C3 decomposition.** The apparent benefit of status-aware regime assignment is dominated by
   replacing a **badly miscalibrated** drag forecast (ECE 0.027, mean p 0.039 against an event
   rate of 0.013 — over-forecasting threefold) with a well-calibrated previous-window base rate.
   Status itself carries real information (non-operational payloads decayed at **8.7×** the
   operational rate) but acting on it adds −0.0005 Brier with an interval spanning zero.

3. **Feature-importance conclusions are learner-dependent (E12).** Holding the learner
   constant, the family effect is significant at **neither** origin, and at origin 2016 two
   comparably-performing learners reach opposite conclusions. The `physics` group reverses sign
   *at the same origin* depending on learner — significant in **both** directions
   (`tabm@2016` −8.4 %, p_adj < 0.0001; `mlp@2016` +11.4 %, p_adj = 0.016). Single-learner
   feature ablations are therefore not a reliable guide to feature value in this setting, which
   is a methodological finding that applies beyond this project.

4. **C4 is structurally unevaluable,** not merely unevaluated. The two sources carrying the
   required variables are anonymised as a release condition; the only identifiable source
   carries neither. Documenting why a proposed coupling cannot be tested is a legitimate
   contribution to a literature that frequently asserts such couplings.

## What integration does provide — stated without inflation

These are **engineering and epistemic** properties, verified by tests. They are not scientific
performance claims:

- **Traceability.** Every prediction carries its source artifact digest, model identity,
  uncertainty semantics and run provenance.
- **Explicit abstention.** Where evidence is insufficient the system produces no value and
  records why, rather than substituting a plausible number. 463 of 500 objects abstained in a
  representative run, each with a stated reason.
- **Enforced separation of physical probability from operational priority**, asserted by tests
  rather than asserted in prose.
- **Detection of defects that component testing missed** — the non-coherent per-horizon
  calibration (L17, 123 objects) and the quantile pile-up at the study cap (13,756 objects)
  were both found by building the integrated views.

A reviewer may reasonably call these software-engineering virtues rather than scientific
contributions. That characterisation should be accepted rather than argued with.

## What integration does not provide

- No reproducible improvement in predictive accuracy from cross-domain coupling.
- No validated end-to-end health → lifetime → debris → risk chain. No identity-linked dataset
  spanning those domains exists (L1), so this cannot be established by any amount of work on
  the current data.
- No evidence for C4.
- No demonstrated improvement in decision quality — no decision-outcome dataset exists.

## Why no single aggregate integration score is reported

It would be straightforward to define a weighted composite of the three endpoints and report
that "integration improves the composite". This is refused.

C1 is scored by pinball loss over catalogued objects clustered by launch family; C2 by
fractional count error over cloud-years clustered by breakup cloud; C3 by Brier score over LEO
payloads clustered by launch. **Different populations, different units of analysis, different
independent units, different horizons.** Any composite's value would be determined by the
weights chosen, and favourable weights could always be found. The result would be an artefact
of the aggregation, and a competent reviewer would identify it as such.

The combined-integration arm is therefore reported as **NOT EVALUABLE**, with the reason.

## Consequence for the research contribution

The project's original framing — that evidence-aware cross-domain integration improves
intelligent space-system assessment — is **not supported by its own ablations**. A manuscript
asserting it would be refuted by the evidence in this repository.

The contribution must be narrowed. In descending order of defensibility:

1. **A catalogue-scale, forward-in-time orbital lifetime and re-entry benchmark** with
   censoring-aware targets, launch-family splits, cluster-aware intervals, and a measured
   calibration failure mode. This is the strongest asset and rests on the largest population.
2. **An evidence-graded architecture with enforced abstention and provenance**, presented as a
   systems/reproducibility contribution with the integration hypothesis reported as tested and
   not supported.
3. **The negative and mechanistic findings above**, which are specific, measured and
   falsifiable.

Framing (1) with (3) as its scientific content is substantially more defensible than the
original system claim. See the reassessment in Phase K when that phase is executed.

## Status

| Requirement | Evidence | Status |
|---|---|---|
| Couplings identified and justified | C1–C4 evaluation reports | **PASS** |
| Physical rationale examined, weak ones rejected | C3 causal reading rejected; C4 bounded to decisions | **PASS** |
| Leakage and circularity audited | per coupling; C3 in-window pair excluded | **PASS** |
| Controlled single-factor comparisons | C1, C2 | **PASS** |
| Cluster-aware intervals | all evaluable couplings | **PASS** |
| Multiplicity correction | BH within families | **PASS** |
| Independent subsystem baselines | full-vs-ablated, physics-vs-learned, status-blind | **PASS** |
| Combined integration arm | no shared endpoint exists | **NOT EVALUABLE** |
| Integration hypothesis | tested on three couplings | **NOT DEMONSTRATED** |
| C4 | required join absent from all sources | **NOT EVALUABLE** |
| Temporal replication of any coupling | C1 only, and it did not reproduce | **PARTIAL** |
| Decision-quality evidence | no decision-outcome dataset | **NOT EVALUABLE** |
