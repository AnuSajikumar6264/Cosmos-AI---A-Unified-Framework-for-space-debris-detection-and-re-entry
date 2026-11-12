# Physics–ML hybrid experiments

Date: 2026-11-04. Status: **PARTIAL** — arms 1–3 measured from saved artifacts; arms 4–5
(learned residual) **NOT RUN**.

## The five requested arms

| # | Arm | Status | Evidence |
|---|---|---|---|
| 1 | Physics-only | **MEASURED** | `physics_only` in both origins' `regression_test.csv` |
| 2 | ML-only | **MEASURED** | `tabm`, `tabicl`, `kumo`, `mlp`, GBMs |
| 3 | Physics features + ML | **MEASURED** | the `FULL` feature set includes the `physics` group; `no_physics` ablation isolates it |
| 4 | Physics prediction + learned residual | **NOT RUN** | requires training a residual model |
| 5 | Physics prediction + calibrated learned residual | **NOT RUN** | same |

## Arms 1–3: measured results

### Physics-only versus ML-only — the ranking inverts between origins

| Origin | physics_only pinball | Best ML pinball | Verdict |
|---|---|---|---|
| 2016 | **0.089249** (worst of 9) | 0.049944 (`tabicl`) | ML wins by **44 %** |
| 2011 | **0.052676** (best of 9) | 0.059584 (`tabicl`) | **physics wins** by 12 % |

Physics is the worst model at one origin and the best at the other. Any claim that one
paradigm dominates is refuted by two origins.

### Arm 3: are physics *features* useful inside an ML model?

From the E12 2 × 2 design, the `no_physics` ablation:

| Cell | Effect of removing physics features | Relative | p_adj | Reading |
|---|---|---|---|---|
| tabm@2016 | **−0.004962** | −8.37 % | **<0.0001** | removing physics **improved** the model |
| mlp@2016 | **+0.006611** | +11.44 % | **0.0163** | removing physics **worsened** the model |
| kumo@2011 | +0.002247 | +3.65 % | 0.1700 | n.s. |
| mlp@2011 | −0.024486 | −21.35 % | 0.0575 | n.s. (weak baseline) |

**Two comparably-performing learners at the same origin give significant conclusions in
opposite directions.** Physics features are not reliably beneficial as features, and their
measured effect depends on the learner, not just the epoch.

### Indirect evidence on the prior framing (G1 blend)

The G1 robust combination includes `physics_only` as a member alongside the three recent
learners. At origin 2016 the median blend (0.048644) beats both pure physics (0.089249) and the
best single learner (`tabicl`, 0.049944); at origin 2011 it (0.057549) does **not** beat pure
physics (0.052676).

So combining physics with learners helps where physics is weak and hurts where physics is
strong — consistent with the median simply tracking the majority of members rather than
exploiting physics as a genuine prior.

## What arms 4–5 would test, and why they matter

Arms 1–3 all use physics either as a *standalone predictor* or as *input features*. Neither
tests the hypothesis the mandate actually names: **physics as a prior with ML learning the
residual**, i.e. predicting `z − z_physics` rather than `z`.

That formulation is attractive here precisely because of the sign reversals: a residual model
cannot discard the physics prediction the way a feature-based model can down-weight the physics
feature group, so it would be structurally more stable across origins.

**It was not run.** It requires training new models (a residual target, new fits per origin,
tuning at a comparable budget), which is a materially larger undertaking than the
saved-artifact re-analyses in this phase. It is logged as **G4** in the optimization plan.

Expected cost, for planning: 7 learners × 2 origins × 5 seeds, comparable to a full
`lifetime.run` pass (`tabm` ≈ 68 s/fit, `kumo` ≈ 84 s/fit on XPU per the saved
`cost_timing.json`), so on the order of a few hours including tuning.

## Honest summary

| Question | Answer |
|---|---|
| Does physics beat ML? | **Depends on the origin** — physics is worst at 2016 and best at 2011 |
| Do physics features help an ML model? | **Depends on the learner** — significant in both directions at origin 2016 |
| Does physics-as-prior-plus-residual help? | **UNTESTED** |
| Is any physics–ML hybrid claim defensible from current evidence? | **No** |

## Not done

- Arms 4 and 5 (learned residual, calibrated learned residual).
- Sensitivity of the physics expert to ballistic coefficient and atmospheric density
  assumptions (listed in the mandate's §7; not attempted this pass).
- Monte Carlo sample-count efficiency study (the physics expert uses 32 samples; whether that
  is sufficient was not measured).
