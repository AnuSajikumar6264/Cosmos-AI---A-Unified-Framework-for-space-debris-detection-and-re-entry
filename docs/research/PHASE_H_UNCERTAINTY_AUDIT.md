# Phase H — uncertainty and evidence audit

Date: 2026-11-04. Verdict: **nominal conformal coverage is NOT attained consistently.**

```bash
python scripts/phase_h_uncertainty_audit.py --n-boot 4000     # exit 0
```

Outputs: `outputs/phase_h/phase_h_results.json`, `outputs/phase_h/coverage_table.csv`.

## What was measured, and why that distinction matters

A conformal construction has a **nominal** coverage level by design. Whether a deployed
interval **observes** that level on held-out data is a different, empirical question. This
phase measures the second.

Per-object interval coverage was recomputed from the saved test predictions
(`<model>__lo90/__hi90/__lo80/__hi80` against the target `z`, on objects with a known
five-year outcome), and the deviation from nominal was bootstrapped **by launch family**.
Coverage is a mean of indicator variables over dependent observations; an independence
interval would be too narrow and would call deviations significant when they are not.

No model was refitted. No published number was altered.

## Headline result — the deployed expert

`cosmos_gated`, the system's deployed expert:

| Origin | Level | Nominal | Empirical | Deviation | 95 % CI (cluster) | Verdict |
|---|---|---|---|---|---|---|
| 2016 | 80 % | 0.80 | **0.7169** | −0.0831 | [−0.1777, **−0.0023**] | **UNDER-COVERS** |
| 2016 | 90 % | 0.90 | 0.8741 | −0.0259 | [−0.0991, +0.0251] | consistent with nominal |
| 2011 | 80 % | 0.80 | **0.9231** | +0.1231 | [**+0.0829**, +0.1478] | **OVER-COVERS** |
| 2011 | 90 % | 0.90 | **0.9591** | +0.0591 | [**+0.0336**, +0.0740] | **OVER-COVERS** |

**Three of four (origin, level) cells deviate significantly from nominal, in opposite
directions.** The 80 % interval is too narrow at origin 2016 and too wide at 2011; the 90 %
interval is too wide at 2011.

### A correction worth recording

Read naively, `cosmos_gated`'s 90 % coverage at origin 2016 is 0.874 — apparently a 2.6 pp
shortfall. With launch-family clustering the interval is [−0.099, +0.025] and **includes
zero**: that shortfall is *not* statistically distinguishable from nominal. The cluster
bootstrap prevented an overclaim here, and the same machinery is what makes the three
significant deviations credible.

## All audited models

Origin 2016 (2,978 objects, 621 launch families):

| Model | 80 % empirical | verdict | 90 % empirical | verdict |
|---|---|---|---|---|
| cosmos_gated (deployed) | 0.7169 | **UNDER** | 0.8741 | consistent |
| physics_only | 0.7381 | consistent | 0.8764 | consistent |
| tabm | 0.7277 | consistent | 0.8768 | consistent |
| kumo | 0.9459 | **OVER** | 0.9738 | **OVER** |
| tabicl | 0.9019 | **OVER** | 0.9621 | **OVER** |
| mlp | 0.7774 | consistent | 0.8915 | consistent |

Origin 2011 (2,667 objects, 435 launch families):

| Model | 80 % empirical | verdict | 90 % empirical | verdict |
|---|---|---|---|---|
| cosmos_gated (deployed) | 0.9231 | **OVER** | 0.9591 | **OVER** |
| physics_only | 0.9438 | **OVER** | 0.9738 | **OVER** |
| kumo | 0.9329 | **OVER** | 0.9655 | **OVER** |
| tabm | 0.8774 | consistent | 0.9175 | consistent |
| tabicl | 0.8211 | consistent | 0.9194 | consistent |
| mlp | 0.8196 | consistent | 0.8519 | consistent |

A model's coverage behaviour **flips with the origin**: `kumo` and `tabicl` over-cover at 2016
and `tabm`/`tabicl`/`mlp` are nominal at 2011 while the deployed expert over-covers. Coverage
is not a stable property of a model here; it is a property of the model-origin pair.

## Temporal distribution shift — quantified

Per-year 90 % coverage, from the study's saved `temporal_coverage_test.csv`:

| Origin | Model | Range | Spread | Worst year | Rank trend with year |
|---|---|---|---|---|---|
| 2016 | **physics_only** | 0.732 – 0.974 | **0.242** | 2021 | **−0.94** |
| 2016 | cosmos_gated | 0.812 – 0.963 | **0.151** | 2020 | **−0.83** |
| 2016 | tabm | 0.817 – 0.963 | 0.146 | 2020 | −0.54 |
| 2011 | cosmos_gated | 0.929 – 0.978 | 0.049 | 2013 | −0.60 |
| 2011 | kumo | 0.929 – 0.982 | 0.052 | 2013 | −0.50 |
| 2011 | physics_only | 0.957 – 0.980 | 0.024 | 2014 | −0.60 |

At origin 2016, coverage **degrades near-monotonically with time from the origin** — rank
correlation −0.94 for the physics expert and −0.83 for the deployed expert, with coverage
falling from ~0.96 in the first year to ~0.81 by 2020.

This is the direct empirical signature of the exchangeability violation that limitation L8
anticipated. **Conformal validity depends on calibration and test data being exchangeable; a
forward-in-time test fold with evolving space weather and cohort composition is not
exchangeable with its calibration period.** The degradation is measured, not hypothesised.

## Mechanism inventory

| Mechanism | Type | Status |
|---|---|---|
| Quantile regression over 7 levels | aleatoric | **PASS** — coverage measurable and measured |
| Mondrian CQR | distribution-free interval | **MEASURED** — verdict differs by origin and level; nominal not attained consistently |
| Marginal conformal variant | distribution-free interval | **MEASURED** |
| Isotonic calibration per horizon | probability calibration | **FAIL** — non-coherent CDF for 123/13,238 objects (L17) |
| Isotonic survival recalibration (C2) | calibration of S(age) | **PASS** — materially improves cloud counts for learned experts |
| Monte-Carlo propagation (drag, A/m, space weather) | aleatoric + input | **PARTIAL** — intervals measured; the sampling distribution is not validated against truth |
| Missing-data handling / abstention | evidence coverage | **PASS** — enforced, no imputation, test-asserted |
| Model disagreement across seeds | epistemic | **PARTIAL** — recorded but not propagated downstream |
| Cross-module uncertainty propagation | semantic | **PARTIAL** — semantics preserved and test-enforced; no end-to-end numerical propagation |
| Conformal p-values / BH / Simes for telemetry alarms | multiple testing | **NOT VALIDATED here** — point-level alarm-rate control was checked under drift by `tests/test_ai.py`, which is not a coverage claim |

### On "aleatoric vs epistemic"

The project implements **aleatoric** uncertainty (quantile regression, Monte-Carlo sampling over
area-to-mass and space weather) and a limited form of **epistemic** uncertainty (5-seed
ensembles). It does **not** implement a principled epistemic measure — no posterior over
parameters, no deep ensemble treated as a predictive distribution, no out-of-distribution
detector. Seed spread is recorded but is not propagated to any consumer, so a downstream
module cannot distinguish "this model is uncertain" from "this outcome is variable". That gap
should be stated in the manuscript rather than papered over with the aleatoric/epistemic
vocabulary.

### Cross-module propagation — what "preserved" means

`contracts.Uncertainty` carries `kind`, `method`, `level` and `assumptions` through every
adapter, and tests assert the representation is not collapsed into a scalar confidence. That
is **semantic** preservation and it is real.

It is **not** numerical propagation. No end-to-end numerical uncertainty is computed, because
the chain's endpoints are not joined by a shared quantity — the same structural reason the
combined-integration arm is NOT EVALUABLE in Phase E. Claiming "uncertainty propagates through
the system" without that qualification would overstate what exists.

## Consequences for claims

| Claim | Status after Phase H |
|---|---|
| "Conformalised intervals provide distribution-free coverage" | **Must be removed.** Nominal coverage is not attained in 3 of 4 deployed cells. |
| "Intervals are calibrated" | **Must be qualified** by origin and level, with the measured numbers. |
| "Uncertainty is propagated across modules" | **Must be narrowed** to semantic preservation. |
| "The framework is uncertainty-aware" | Defensible in the weak sense (uncertainty is represented, carried and abstained on) — not in the sense of validated coverage. |
| "Coverage degrades under temporal shift" | **Newly supported**, with rank trends −0.83 to −0.94 at origin 2016. |

## Limitations

1. Post-hoc: these test folds were scored by the original study.
2. Coverage is measured only on objects with a known five-year outcome; **censored objects are
   excluded and their coverage is unknown**. This is a selection that could bias coverage in
   either direction.
3. Two origins; coverage behaviour already differs between them, so two is too few to
   characterise the dependence.
4. Telemetry-side conformal machinery is not audited here.
5. The per-year drift table is the study's own and is not re-derived with cluster intervals,
   so the rank trends are descriptive.

## Recommended next work

1. Report coverage **per origin and per level** in the manuscript; never a single number.
2. Investigate why Mondrian grouping under-covers at 80 % while the marginal variant is closer
   to nominal at origin 2016 — the grouping may be too fine for the calibration set.
3. Measure coverage on censored objects via a censoring-aware criterion, closing limitation 2.
4. Propagate seed disagreement as an explicit epistemic field in `contracts.Uncertainty`, or
   state plainly that epistemic uncertainty is not available to consumers.
