# Exploratory evaluation of the decision-priority rule on the archived T1 window — protocol (declared 2026-11-08, before computation)

**Status: exploratory and non-blind.** The T1 window (forecast as of 2026-08-16, outcomes observed to 2026-10-27) was
analysed before (`outputs/benchmarks/twin_prospective_t1/`, X7); 29 re-entries occurred within 30 days and 64 within 72
days among 13,186 uncontrolled objects. No claim of operational effectiveness follows from this analysis.

**Question.** Did the deployed priority rule, `priority = p_30d × (2 if mass ≥ 500 kg else 1)` as recorded in run
manifests, place the objects that actually re-entered within the horizon higher than simple alternatives would have?

**Data.** `outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz` (sha `a4573a00…`), one row per catalogued object at
2026-08-16: `p_30d` (the reported forecast), `p_physics_prior_30d`, `p_lifetime_30d`, `mass`, `perigee`, `regime`,
`launch_family`, outcomes `y_30d`, `y_72d`. Nothing is refit; the table is read as archived.

**Populations.** (a) uncontrolled objects (`regime != operator_controlled`), the population the twin forecasts; (b) all
objects, the population the deployed ranking actually orders (operator-controlled objects carry the base rate).

**Rankings compared.** The deployed rule; `p_30d` alone; the physics prior `p_physics_prior_30d`; the lifetime expert
`p_lifetime_30d`; perigee ascending (a physics-free baseline); and the base rate (expected precision of a random order).
Ties broken by NORAD id ascending (deterministic).

**Metrics.** Precision@k and recall@k for k ∈ {10, 25, 50, 100, 250} against `y_30d` (primary, the rule's horizon) and
`y_72d` (secondary); the number and total mass of high-consequence re-entries (mass ≥ 500 kg) captured in the top k.
Differences between the rule and `p_30d` alone, and between the rule and perigee, at k = 25 and 50, with a 95 % paired
cluster bootstrap over launch families (B = 2000, seed 20261108). Rankings whose top k are identical are reported as
identical, not as a difference of zero with an interval.

**Interpretation rules.** The rule can only change the order among objects with p_30d > 0 by the mass factor; where the
top k is dominated by p_30d = 1.0 objects the rule and `p_30d` alone are expected to coincide and the analysis says so.
A higher precision at k than the physics-free baseline is evidence that the forecast carries information for
prioritisation on this window; it is not evidence of calibration, operational value or transfer to another window.

**Outputs.** `outputs/t1_ranking_utility/results.json`, `precision_at_k.csv`, `run.log`; test
`tests/test_t1_ranking_utility.py`. The script is `scripts/t1_ranking_utility.py`.

**Amendment (2026-11-08, after the first run, before interpretation).** The first run used population (a) as
`regime != operator_controlled` (14,968 objects, 36 thirty-day events). The archived X7 analysis defines "uncontrolled"
as natural-decay objects with a physics-history reading (13,186 objects, 29 events). To stay comparable with the archive,
population (a) is split into (a1) the X7 population and (a2) all natural-decay objects (13,745); population (b), all
objects, is unchanged. No metric, k, baseline or bootstrap setting changed. Observation recorded at the same time: 65 of
the 101 thirty-day re-entries in population (b) are operator-controlled objects, which the twin deliberately does not
forecast (coupling C3); any ranking that scores low-perigee controlled objects highly will "capture" these deorbits, and
that is not evidence of drag-driven forecasting skill.
