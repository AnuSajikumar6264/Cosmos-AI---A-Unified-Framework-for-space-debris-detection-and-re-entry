# Claims and evidence matrix — JIRS framing

Date 2026-11-04. Every claim available to a JIRS submission, with its artifact, its verification
status, and the evidence that argues against it.

Tier: **CONF** confirmatory (pre-registered, never-scored fold) · **VAL** validated against an
external benchmark · **MEAS** measured, not pre-registered · **EXPL** exploratory (outcome seen
first) · **NEG** negative · **PEND** pending · **UNSUP** unsupported.

---

## 1. Claims that may be made

| # | Claim | Tier | Value | Artifact | Counter-evidence |
|---|---|---|---|---|---|
| 1 | A late-fusion CNN+MLP detector attains AUC-PR 0.9719 under a time-blocked protocol on OPS-SAT | **VAL** | 0.9719 (5 seeds) | `telemetry_opssat/summary_time_blocked.csv` | lead over `cnn` (0.9712) is within noise; **no significance test under this protocol** |
| 2 | It beats a time-series foundation model | **VAL** | +0.0316 AUC-PR, 95 % CI [0.0134, 0.0558], **p < 0.001** | `telemetry_opssat/paired_comparisons.csv` | test is on the **official** protocol only |
| 3 | It beats XGBoost and an FCNN | **VAL** | +0.0254 (p = 0.002); +0.0059 (p = 0.036) | same | official protocol only; FCNN margin is small |
| 4 | It is calibrated | **VAL** | ECE 0.035 time-blocked, 0.013 official | `summary_*.csv` | `cnn` ECE 0.121 — calibration varies sharply by arm |
| 5 | It is small and fast | **VAL** | 74,371 params; 0.0045 ms/fragment | `per_run_*.csv` | single hardware configuration; **no runtime reproducibility record** |
| 6 | It degrades gracefully with fewer labels | **VAL** | AUC-PR 0.910 at 10 % of labels | `summary_official.csv` | official protocol only |
| 7 | The project's own monitor ties a trivial rule on ESA-ADB | **VAL, NEG** | `cosmos_monitor` 0.202 = `out_of_limits` 0.202; PatchTST 0.496; 14.7 vs 0.29 false alarms/yr | `telemetry_esa_adb/results.csv` | — (this is the counter-evidence) |
| 8 | Every learned arm loses to a trivial baseline on collision risk | **VAL, NEG** | F2 0.168 vs **0.739**; six arms at 0.000 | `conjunction_kelvins_cac/test_results.csv` | learned arms have better precision (0.84) and reasonable interval coverage |
| 9 | Debris detection fails on the real benchmark | **VAL, NEG** | SpotGEO test F1 **0.084** | `vision_spotgeo/summary.csv` | synthetic mAP@50 0.78 — but on self-generated data, not external |
| 10 | Validation→test rank transfer is perfect on adjacent splits and absent across forward origins | **EXPL** | ρ = +1.000 / +0.800 / 0.000 | `telemetry_opssat/per_run_*.csv`; `phase_g_lifetime_results.json` | n = 5, 7; +0.800 **not significant** (p = 0.104); regimes **confounded** by data/task/metric; computed post hoc |
| 11 | Selection does not transfer on orbital lifetime | **MEAS** | ρ = 0.000 at both origins, n = 7 | `phase_g_lifetime_results.json` | 95 % interval ≈ [−0.77, +0.77]; tune-A is only 248 objects at origin 2011 |
| 12 | Physics baseline ranks 1st of 17 at one origin, 17th of 17 at another | **MEAS** | 1/17, 17/17 | `regression_test.csv` ×2 | leaderboards not rank-comparable (different ablation families) |
| 13 | Model ordering inverts across evaluation slices | **MEAS** | 23.64 % of pairs; mean between-slice ρ **+0.33** | `g5_rolling_results.json` | rankings agree more often than not; slices 198–841 objects; no refitting per slice |
| 14 | Ranking instability recurs on a pre-registered never-scored fold | **CONF, low power** | H2 SUPPORTED; **chance level 0.199** | `g5d_analysis.json` + own Monte Carlo | chance level exceeds the 0.167 at which H3 was closed; **not a confirmation** |
| 15 | Cross-domain integration not demonstrated | **NEG** | C1 NOT REPRODUCIBLE (−0.0514 / +0.0026, significant at neither); C3 inconclusive; C4 0 joinable pairs | `phase_e_results.json`, `e12_results.json` | C2's primary contrast p = 0.002 — but deployed arm p = 0.364 |
| 16 | Published values recompute exactly from archives | **VAL** | max deviation **0.000e+00** | `final_audit/final_system_audit.json` | covers the lifetime benchmark; **not** the OPS-SAT paired comparison |
| 17 | 2 of 7 learners refittable | **MEAS** | 2/7 importable; **1/7** matches the recorded environment | `final_reproducibility.json`; `venv_freeze_2026-10-24.txt` | — |
| 18 | Temporal separation is clean | **VAL** | 0 straddling launch families; 0 shared test objects; ordering holds at all 3 origins | `final_system_audit.json` | rules out one leakage mechanism, not all |
| 19 | Conformal coverage is unstable under temporal displacement | **MEAS** | 80 %: 0.572–0.960 across 11 slices | `g5_rolling_results.json` | monotone degradation at **one of two** origins; no trend test |
| 20 | Prospective forecast registered and unscored | **PEND** | −1 outcome days; needs ≥ 2026-11-26 | `check_t1_later_snapshot.py` | — |

## 2. Claims that may NOT be made

| # | Claim | Why not |
|---|---|---|
| 21 | Validated intelligent decision support | **UNSUP.** No decision-quality metric, regret measure, utility model, operator study or baseline-ordering comparison exists. `priority_score` is deliberately unset in the collision adapter |
| 22 | Validated satellite digital twin | **NOT DEMONSTRATED.** Integration premise refuted by the project's own de-confounding experiment |
| 23 | Distribution-free coverage guarantee | **Mathematically unjustified.** Split-conformal requires exchangeability; test folds are forward in time from calibration, and measured coverage confirms the failure |
| 24 | Physics-informed machine learning | **False.** The `hybrid` is a late fusion of a 1-D CNN and a feature MLP (`models.py:109`) |
| 25 | The temporal-displacement mechanism is established | **EXPL and confounded.** Regimes differ in data, task, metric and model family |
| 26 | H2 confirms ranking instability | **Chance level 0.199**, above H3's 0.167 closure threshold |
| 27 | Real-time or operational deployment | Latency measured on one configuration; deployment never demonstrated |
| 28 | Uncertainty propagates across modules | Intervals are produced per module and **not** propagated into the decision layer |
| 29 | The ablations isolate component contributions | Every ablation arm is **untuned** and inherits its parent's hyperparameters |
| 30 | Learners were comparably tuned | `tabicl` and `kumo` carry **one** hyperparameter; others 4–6 |
| 31 | The benchmark is publicly available | **No DOI, deposit, release or licence exists** |
| 32 | Anomaly detection generalises across missions | Never tested cross-mission; and the ESA-ADB result argues against it |

## 3. Traceability

| Property | Result |
|---|---|
| Claims in §1 with a named artifact | **20 / 20** |
| Claims independently re-derived during this audit | 12 (including the ρ diagnostic and the H2 Monte Carlo) |
| Claims stated above their tier | **0** |
| Claims in §2 appearing anywhere as assertions | **0** — all are recorded as prohibited |
| Counter-evidence recorded for every §1 claim | **18 / 20** (2 are themselves counter-evidence) |

## 4. The two claims that carry the paper, and their weaknesses

**Claim 2** (beats a foundation model) is the strongest positive result: significance-tested, with
a confidence interval, five seeds, and a published-architecture comparator. Its weakness is that
the test is on the protocol that is **not** temporally honest. Fixing this is experiment **E1**.

**Claim 10** (selection transfer varies with temporal displacement) is the most interesting and the
most fragile: exploratory, confounded, small-n, computed post hoc. Making it confirmatory is
experiment **E2**. Without E2, the paper has no lead contribution appropriate to JIRS — only a good
anomaly-detection result and several honest negatives.
