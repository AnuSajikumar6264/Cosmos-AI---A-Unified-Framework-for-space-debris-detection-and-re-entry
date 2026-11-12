# Exploratory evaluation of the decision-priority rule on the archived T1 window — results (2026-11-08)

Protocol: `T1_RANKING_UTILITY_PROTOCOL.md` (declared before computation; amended once to add the archived X7 population).
Record: `outputs/t1_ranking_utility/results.json`, `precision_at_k.csv`, `run.log`; input `outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz` (sha `a4573a00004e8869…`);
rule `priority = p_30d * (2.0 if mass_kg >= 500 else 1.0)` as recorded in run manifests; seed 20261108, B = 2000 paired cluster bootstrap over launch families.
**Exploratory and non-blind**: the T1 outcomes (forecast 2026-08-16, follow-up 2026-10-27) were analysed before. No operational effectiveness is claimed.

## Precision at k, thirty-day horizon (the rule's horizon)

| Population (n, events) | Ranking | P@10 | P@25 | P@50 | P@100 | P@250 |
|---|---|---|---|---|---|---|
| X7 uncontrolled (13186, 29) | deployed_rule | 0.60 | 0.72 | 0.56 | 0.28 | 0.11 |
| X7 uncontrolled (13186, 29) | p_30d_alone | 0.60 | 0.80 | 0.56 | 0.28 | 0.11 |
| X7 uncontrolled (13186, 29) | physics_prior | 0.50 | 0.64 | 0.48 | 0.28 | 0.12 |
| X7 uncontrolled (13186, 29) | lifetime_expert | 0.70 | 0.68 | 0.36 | 0.24 | 0.11 |
| X7 uncontrolled (13186, 29) | perigee_ascending | 0.40 | 0.16 | 0.08 | 0.06 | 0.03 |
| X7 uncontrolled | base rate | 0.0022 | 0.0022 | 0.0022 | 0.0022 | 0.0022 |
| natural decay, all (13745, 36) | deployed_rule | 0.50 | 0.68 | 0.58 | 0.34 | 0.14 |
| natural decay, all (13745, 36) | p_30d_alone | 0.60 | 0.76 | 0.58 | 0.34 | 0.14 |
| natural decay, all (13745, 36) | physics_prior | 0.50 | 0.60 | 0.50 | 0.30 | 0.14 |
| natural decay, all (13745, 36) | lifetime_expert | 0.70 | 0.68 | 0.36 | 0.24 | 0.11 |
| natural decay, all (13745, 36) | perigee_ascending | 0.40 | 0.16 | 0.08 | 0.06 | 0.04 |
| natural decay, all | base rate | 0.0026 | 0.0026 | 0.0026 | 0.0026 | 0.0026 |
| all objects (30826, 101) | deployed_rule | 0.50 | 0.64 | 0.58 | 0.34 | 0.14 |
| all objects (30826, 101) | p_30d_alone | 0.60 | 0.76 | 0.58 | 0.34 | 0.14 |
| all objects (30826, 101) | physics_prior | 0.70 | 0.84 | 0.82 | 0.73 | 0.36 |
| all objects (30826, 101) | lifetime_expert | 0.70 | 0.68 | 0.36 | 0.24 | 0.11 |
| all objects (30826, 101) | perigee_ascending | 0.40 | 0.16 | 0.08 | 0.11 | 0.13 |
| all objects | base rate | 0.0033 | 0.0033 | 0.0033 | 0.0033 | 0.0033 |

## Paired cluster-bootstrap differences in precision (rule minus comparator)

| Population | Horizon | Comparator | k | Difference | 95 % CI |
|---|---|---|---|---|---|
| X7 uncontrolled | y_30d | p_30d alone | 25 | -0.080 | [-0.160, +0.000] |
| X7 uncontrolled | y_30d | p_30d alone | 50 | +0.000 | [-0.040, +0.000] |
| X7 uncontrolled | y_30d | perigee ascending | 25 | +0.560 | [+0.320, +0.760] |
| X7 uncontrolled | y_30d | perigee ascending | 50 | +0.480 | [+0.260, +0.640] |
| X7 uncontrolled | y_72d | p_30d alone | 25 | -0.080 | [-0.200, +0.000] |
| X7 uncontrolled | y_72d | p_30d alone | 50 | +0.020 | [-0.060, +0.020] |
| X7 uncontrolled | y_72d | perigee ascending | 25 | +0.600 | [+0.320, +0.800] |
| X7 uncontrolled | y_72d | perigee ascending | 50 | +0.600 | [+0.320, +0.760] |
| natural decay, all | y_30d | p_30d alone | 25 | -0.080 | [-0.200, +0.000] |
| natural decay, all | y_30d | p_30d alone | 50 | +0.000 | [-0.060, +0.000] |
| natural decay, all | y_30d | perigee ascending | 25 | +0.520 | [+0.280, +0.720] |
| natural decay, all | y_30d | perigee ascending | 50 | +0.500 | [+0.320, +0.640] |
| natural decay, all | y_72d | p_30d alone | 25 | -0.080 | [-0.200, +0.000] |
| natural decay, all | y_72d | p_30d alone | 50 | +0.000 | [-0.060, +0.020] |
| natural decay, all | y_72d | perigee ascending | 25 | +0.560 | [+0.280, +0.760] |
| natural decay, all | y_72d | perigee ascending | 50 | +0.620 | [+0.420, +0.760] |
| all objects | y_30d | p_30d alone | 25 | -0.120 | [-0.240, +0.000] |
| all objects | y_30d | p_30d alone | 50 | +0.000 | [-0.060, +0.000] |
| all objects | y_30d | perigee ascending | 25 | +0.480 | [+0.240, +0.680] |
| all objects | y_30d | perigee ascending | 50 | +0.500 | [+0.300, +0.640] |
| all objects | y_72d | p_30d alone | 25 | -0.080 | [-0.200, +0.040] |
| all objects | y_72d | p_30d alone | 50 | -0.020 | [-0.060, +0.020] |
| all objects | y_72d | perigee ascending | 25 | +0.560 | [+0.280, +0.760] |
| all objects | y_72d | perigee ascending | 50 | +0.620 | [+0.440, +0.760] |

## Reading

1. **The forecast carries prioritisation information on this window.** On the X7 population the deployed rule places 18 re-entries in its top 25 (precision 0.72) against a base rate of 0.0022; the physics-free perigee ordering reaches 0.16, and the rule exceeds it by +0.56 (95 % CI +0.32 to +0.76) at k = 25 and +0.48 (+0.26 to +0.64) at k = 50.
2. **The mass multiplier costs a little precision at k = 25 and nothing at k = 50.** The rule promotes heavy objects with lower p above lighter objects with higher p by design (consequence weighting); against `p_30d` alone the difference is −0.08 at k = 25 (95 % CI −0.16 to 0.00: the interval touches zero) and the top 50 are identical. The rule's high-consequence capture at k = 25 is 5 re-entries totalling 28,200 kg against 4 and 19,800 kg for `p_30d` alone.
3. **Operator deorbits dominate the all-objects window and are outside the twin's forecast by design.** Of the 101 thirty-day re-entries among all 30,826 objects, 65 were operator-controlled; the twin abstains for them (coupling C3) and carries the payload base rate, so the deployed ranking cannot prioritise them. The physics prior scores many low-perigee controlled objects highly and therefore shows the highest all-objects precision at large k; that reflects deorbit campaigns at low altitude, not drag-driven forecasting skill, and must not be read as a reason to replace the twin's abstention.
4. **What this does not show.** Not calibration, not operational value, not transfer to another window; the outcomes are 29–36 events on a window analysed before; the k values are arbitrary operating points. The rule remains an operational ordering whose cost ratio between a missed re-entry and a wasted inspection is undocumented.

## Limitations

Non-blind reuse of the T1 window; small event counts; the T1 forecast is the as-of 2026-08-16 twin, not the 2026-10-27 snapshot shown in the console; the mass field is missing for many fragments (treated as below the consequence threshold, as the deployed rule does); bootstrap over launch families treats families as the independent unit, as in the lifetime benchmark.
