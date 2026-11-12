# COSMOS-AI figure catalogue

Generated 2026-11-05. Eighteen figures, each exported as PNG (400 dpi), PDF and SVG.

Every quantitative figure is produced by a script that reads an archived artifact and writes the
exact rows it plotted to `paper/figures/data/`, so any number in any figure can be checked without
rerunning an experiment. The two architecture figures are diagrams rather than plots; their boxes
carry implementation and validation states transcribed from this repository's audit records, and
those states are listed per component in the matching source-data file.

Regenerate everything:

```
python scripts/figures/fig_architecture.py
python scripts/figures/fig_datasets.py
python scripts/figures/fig_benchmarks.py
python scripts/figures/fig_jint.py
python scripts/figures/fig_diagnostics.py
python scripts/figures/fig_system_outputs.py
python -m pytest tests/test_figures.py
```

## Two protocols that must never be mixed

The ESA-ADB study ran selection two ways, and their scores are not comparable:

| Protocol | Selection data | Artifact | Alarm layers available | Figures |
|---|---|---|---|---|
| **A0** | 9-month calibration period | `telemetry_esa_adb/results.csv` | 4 (no adaptive conformal) | J5, B1 (ESA rows) |
| **A1–A3** | whole training half, cross-fitted | `oof_protocol/test/*.json` | 5 | J1, J2, J3, J4, J6 |

Arm A0 appears in Figures J2 and J3 because the contrast between the two protocols *is* hypothesis
H6. It is read from the frozen confirmatory record and cross-checked against `results.csv`; the
generating script aborts if the two disagree. `tests/test_figures.py::test_j5_is_the_other_protocol_and_says_so`
asserts the two remain distinguishable.

---

## Group A — architecture

### Figure A1 · COSMOS-AI system architecture

| | |
|---|---|
| **Image** | `paper/figures/architecture/Figure_Architecture_COSMOS_AI.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/architecture_component_status.csv` (49 components with evidence pointers) |
| **Script** | `scripts/figures/fig_architecture.py::fig_architecture` |
| **Manuscript** | §6 *COSMOS-AI Architecture — scope of this paper* |
| **Purpose** | Show the whole system as seven bands (sources → ingestion → digital state → intelligence modules → cross-module couplings → integration → application), with every component's implementation and validation state on its face. |
| **Provenance** | Band structure read from `cosmos/ai/adapters.py::default_modules()`; component states transcribed from `docs/publication/COSMOS_AI_MASTER_COMPLETION_AUDIT.md` and verified against the named output artifacts; dataset row from `data/DATASET_REPORT.json`. |
| **Validation** | **Inspected.** Legend distinguishes five states; `validated` and `validated-negative` are visually separable (dash-dot border). Flow arrows match the declared module graph. |
| **Limitations** | A diagram, not a measurement — no box asserts performance. It deliberately marks *demonstrated advantage over independent components* as NOT DEMONSTRATED, and the C4 edge as gated off, so it must not be read as a claim that the integrated architecture is validated as a whole. |

### Figure A2 · Evidence-fusion mechanism

| | |
|---|---|
| **Image** | `paper/figures/architecture/Figure_Evidence_Fusion.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/fusion_mechanism_elements.csv` (10 stages with their implementing predicate) |
| **Script** | `scripts/figures/fig_architecture.py::fig_fusion` |
| **Manuscript** | §7 *Evidence Normalisation and Digital-State Representation*, §9 *Uncertainty and Abstention* |
| **Purpose** | Document the fusion path exactly as implemented: evidence contract → five compatibility gates → sufficiency and conflict tests → noisy-OR → recorded assumptions → `Decision`. |
| **Provenance** | Every element quoted from `cosmos/ai/fusion.py` (`Evidence`, `decide`, `Decision`); gate predicates reproduced verbatim in the source-data file. |
| **Validation** | **Inspected.** Only `used` items flow into the combination; `reported_only` is drawn travelling to the output without being combined, matching `decide()`. |
| **Limitations** | The mechanism is implemented and unit-tested but **not shown to improve decisions** — no decision-quality metric, regret measure or operator study exists. Conditional independence is an assumption of the noisy-OR, not a property established for these subsystems, and the figure says so. |

---

## Group B — dataset characterisation

### Figure D1 · Data corpora: what is present and what is used

| | |
|---|---|
| **Image** | `paper/figures/datasets/Figure_D1_dataset_inventory.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/datasets_inventory.csv` |
| **Script** | `scripts/figures/fig_datasets.py::fig_d1` |
| **Manuscript** | §10 *Experimental Datasets and Protocols* |
| **Purpose** | Separate the corpora the project *names* from those actually on disk and feeding a reported experiment. |
| **Provenance** | `data/DATASET_REPORT.json`, written by `python -m cosmos.ai.data.validate` from the files on disk. Sizes are measured, not quoted from publications. Each `used_in` value names the output directory that demonstrates the use. |
| **Validation** | **Inspected.** Status (`downloaded` / `incomplete` / `not downloaded`) is printed on every row; four unused corpora are drawn rather than omitted. |
| **Limitations** | Size on disk is a crude proxy for information content. Two synthetic corpora have archived results but no data on disk, which the status label shows but the bar length cannot. |

### Figure D2 · ESA-ADB protocol structure and event composition

| | |
|---|---|
| **Image** | `paper/figures/datasets/Figure_D2_esa_adb_structure.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/esa_adb_event_structure.csv` |
| **Script** | `scripts/figures/fig_datasets.py::fig_d2` |
| **Manuscript** | §10, §16.2 *Mission 2 cannot discriminate methods* |
| **Purpose** | Show the official split, the fit/early-stop/calibration subdivision inside the training half, and the labelled-event composition that bounds what each mission can resolve. |
| **Provenance** | `data/DATASET_REPORT.json` → `esa_adb.mission{1,2}`. |
| **Validation** | **Inspected.** Anomaly counts cross-checked against the figures used throughout the manuscript (M1 test 55, M2 test 6). |
| **Limitations** | Both missions are a single spacecraft each, so nothing in this project speaks to generalisation across spacecraft. Mission identities are anonymised in the release. |

### Figure D3 · Positive events available for evaluation

| | |
|---|---|
| **Image** | `paper/figures/datasets/Figure_D3_label_scarcity.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/benchmark_label_scarcity.csv` |
| **Script** | `scripts/figures/fig_datasets.py::fig_d3` |
| **Manuscript** | §20 *Limitations and Threats to Validity* |
| **Purpose** | State the statistical ceiling on every claim in the project: three of seven settings offer fewer than 60 positives. |
| **Provenance** | `data/DATASET_REPORT.json`; `conjunction_kelvins_cac/summary.json`; `reentry_lifetime/origin2016_uncontrolled/regression_test.csv`. Per-row source string in the CSV. |
| **Validation** | **Inspected.** Unit of evaluation printed under each row label, because the rows do not share one. |
| **Limitations** | **Rows are not comparable with one another.** Lifetime "positives" are observed decays, the remainder being right-censored rather than negative; SpotGEO is counted in frames holding a target, because every annotated object is a target by construction. |

### Figure D4 · Catalogue features and missingness

| | |
|---|---|
| **Image** | `paper/figures/datasets/Figure_D4_catalogue_features.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/catalogue_feature_availability.csv`, `catalogue_feature_correlation.json` |
| **Script** | `scripts/figures/fig_datasets.py::fig_d4` |
| **Manuscript** | §10; §17 *Uncertainty Evaluation* |
| **Purpose** | Feature availability, area-to-mass provenance, perigee distribution by object class, RCS distribution, and a within-table correlation matrix. |
| **Provenance** | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz`, 31,396 objects, digest in `FORECAST_SHA256.txt`. |
| **Validation** | **Inspected.** Panel (b) is drawn in a single colour deliberately: the project's own subgroup analysis finds the design-derived group the *worse*-covered one, so colouring either provenance as favourable would mislead. |
| **Limitations** | Correlations are computed within one table and one population only; none of these objects can be matched to the telemetry or conjunction corpora, so no cross-corpus correlation is possible or attempted. The two space-weather features are constant across this snapshot and carry no cross-object information. |

---

## Group C — benchmarking

### Figure B1 · Learned methods against parameter-free references

| | |
|---|---|
| **Image** | `paper/figures/benchmarks/Figure_B1_learned_vs_reference.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/benchmark_learned_vs_reference.csv`, `benchmark_lifetime_vs_physics.csv` |
| **Script** | `scripts/figures/fig_benchmarks.py::fig_b1` |
| **Manuscript** | §11 *Baseline Architectures*, §14.4, §19 *Discussion* |
| **Purpose** | Answer the first question a reviewer asks — does the learned component beat the cheapest alternative? — across ten settings. Learning wins 7 and loses 3. |
| **Provenance** | `telemetry_esa_adb/results.csv`; `conjunction_kelvins_cac/test_results.csv`; `vision_spotgeo/summary.csv`; `reentry_landmark/results.csv`; `reentry_lifetime/origin{2011,2016}_uncontrolled/regression_test.csv`. |
| **Validation** | **Inspected.** Bounded higher-is-better metrics and the unbounded pinball loss occupy separate panels. ESA-ADB arms keep their best alarm layer and are averaged over seeds only, never over layers — the layer is named in the CSV. |
| **Limitations** | The two conjunction rows are **not the same comparison**: the learned arms gain a tuned decision threshold in the second and the reference has none to tune, which reverses the verdict. Both are shown; neither alone is reportable. ESA-ADB rows use the A0 protocol and are not comparable with J1–J4. |

### Figure B2 · Lifetime ranking does not transfer between temporal origins

| | |
|---|---|
| **Image** | `paper/figures/benchmarks/Figure_B2_rank_instability.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/lifetime_rank_instability.csv` |
| **Script** | `scripts/figures/fig_benchmarks.py::fig_b2` |
| **Manuscript** | §16 *Temporal Generalisation* |
| **Purpose** | Show why the lifetime result is reported as negative: the physics expert is 1st of 13 at origin 2011 and 13th of 13 at origin 2016; Kendall τ = −0.299. |
| **Provenance** | `reentry_lifetime/origin{2011,2016}_uncontrolled/regression_test.csv`. |
| **Validation** | **Inspected.** Restricted to the 13 arms present at both origins; learner-specific ablations excluded because the selected learner differs, so they do not exist in both leaderboards. Ranks recomputed within the comparable subset. |
| **Limitations** | With 13 arms neither rank coefficient is precisely estimated. The honest reading is that ranking carries no dependable cross-origin signal, not that it reliably inverts. |

---

## Group D — JINT manuscript figures (submission priority)

### Figure J1 · Burden–recall trade-off across alarm layers

| | |
|---|---|
| **Image** | `paper/figures/jint/Figure_J1_burden_recall.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/jint_F1_burden_recall.csv` |
| **Script** | `scripts/figures/fig_jint.py::fig_j1` |
| **Manuscript** | §13b, §14.3 *The alarm layer governs a severe burden–recall trade-off* |
| **Purpose** | The paper's headline, with **both** directions of the trade-off: point-level ACI reaches recall 0.927 at 176,337 false alarms/year; the event-level BH layer reaches 0.146 at 1.14/year — 154,310× fewer false alarms, 6.4× less recall, and worse ADTQC. |
| **Provenance** | `oof_protocol/test/m1_target_ar8.json`, arm A1, Mission 1 target channels. |
| **Validation** | **Inspected and asserted.** The script verifies every layer shares the same 7.0007-year annualisation period and that the run-count ratio equals the rate ratio, and refuses to merge the coincident markers unless the coincidence still holds. |
| **Limitations** | One scorer, one mission, one test half. **No documented false-alarm budget or missed-anomaly cost ratio exists for these missions**, so no operating point can be declared preferable. `threshold` and `conformal_bh` coincide in event-wise detection but differ in alarm volume (90 vs 123) and ADTQC. |

### Figure J2 · Pre-registered contrast forest plot

| | |
|---|---|
| **Image** | `paper/figures/jint/Figure_J2_contrast_forest.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/jint_F2_preregistered_contrasts.csv` |
| **Script** | `scripts/figures/fig_jint.py::fig_j2` |
| **Manuscript** | §13b, §14.1, §14.2 |
| **Purpose** | All six pre-registered contrasts with 95 % intervals, the declared ±0.05 minimum effect, and the confirmatory/replication distinction. |
| **Provenance** | `oof_protocol/CONFIRMATORY.json`, freeze `09a98f5e160e` — read, not recomputed. |
| **Validation** | **Inspected and asserted.** All six point estimates, interval bounds and verdicts are pinned against the frozen record to 1e−12; a separate test pins the signs so the earlier M2/H6 sign error cannot return. |
| **Limitations** | H4 and H5 are recorded as refuted on a negative point estimate even where the interval spans zero, because the hypotheses were directional — this is pre-registration logic, not a significance claim. Mission 2's intervals carry no inferential weight. |

### Figure J3 · Arm performance A0–A3

| | |
|---|---|
| **Image** | `paper/figures/jint/Figure_J3_arm_performance.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/jint_F3_arm_performance.csv` |
| **Script** | `scripts/figures/fig_jint.py::fig_j3` |
| **Manuscript** | §13b, §14.1, §14.2, §16.2 |
| **Purpose** | Per-arm scores with seed spread, both missions; shows A2's seed SD of 0.236 against a declared minimum effect of 0.05. |
| **Provenance** | A1–A3 from `oof_protocol/test/*.json`; A0 from `CONFIRMATORY.json` cross-checked against `results.csv`. |
| **Validation** | **Inspected and asserted.** A0 and A1 pinned to the frozen `B_official`/`A_official`. Axis stops at the metric maximum of 1. |
| **Limitations** | A0 and A1 are single runs (n = 1), so their bars carry no seed interval. Mission 2's panel is a replication over six anomalies. |

### Figure J4 · Selection score against held-out test score

| | |
|---|---|
| **Image** | `paper/figures/jint/Figure_J4_selection_vs_test.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/jint_F4_selection_vs_test.csv` |
| **Script** | `scripts/figures/fig_jint.py::fig_j4` |
| **Manuscript** | §13b, §16.1 *Cross-fitting optimism* |
| **Purpose** | Cross-fit optimism, per run: 10 of 11 Mission 1 runs fall below y = x. |
| **Provenance** | `oof_protocol/test/*.json`, `cv_EW_F0.5` against `anomaly_and_rare/EW_F0.5`. |
| **Validation** | **Inspected.** 22 points, 11 per mission, matching the arm × seed count. |
| **Limitations** | Arm-level correlations over three arms are not reported: |ρ| = 1 arises by chance with probability 1/6. Mission 2's points are compressed into the saturated corner, so its ρ is uninformative. |

### Figure J5 · Scorer × alarm-layer configuration sensitivity

| | |
|---|---|
| **Image** | `paper/figures/jint/Figure_J5_configuration_sensitivity.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/jint_F5_configuration_sensitivity.csv` |
| **Script** | `scripts/figures/fig_jint.py::fig_j5` |
| **Manuscript** | §13b, §14.3, §16.3 |
| **Purpose** | Compare the spread along a row (alarm layer) against the spread down a column (scorer), at both channel scales on both missions, with the parameter-free references in the same grid. |
| **Provenance** | `telemetry_esa_adb/results.csv` — **the A0 selection protocol only**. |
| **Validation** | **Inspected and asserted.** A test confirms the A0 cell for `ar8 + conformal_bh` is 0.074351 and differs from the A1 value by more than 0.3, so the protocols cannot be silently conflated; and that no ACI layer appears, since the grid was never run with them. |
| **Limitations** | **Not comparable with J1–J4 or J6.** Four layers only. Several cells rest on a single seed; the per-cell seed count is in the CSV. Trivial references admit only their native layer, hence the dashes. |

### Figure J6 · What the alarms were made of

| | |
|---|---|
| **Image** | `paper/figures/jint/Figure_J6_alarm_composition.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/jint_F6_alarm_composition.csv` |
| **Script** | `scripts/figures/fig_jint.py::fig_j6` |
| **Manuscript** | §13b, §14.3 |
| **Purpose** | Make the suppression mechanism visible: the event-level layer raises 123 alarm runs rather than 1,383,948 and finds 8 of 55 anomalies rather than 51. |
| **Provenance** | `oof_protocol/test/m1_target_ar8.json`. |
| **Validation** | **Inspected and asserted.** The script asserts the three disjoint alarm-run classes sum exactly to `alarm_runs` for every layer, and every recall converts to an integer count of anomalies (51, 32, 8, 8, 2). |
| **Limitations** | Rare events are labelled in the benchmark but are not anomalies; a run matching only a rare event is neither a detection nor an error under the anomaly-only metric, and is shown as its own class rather than folded into either. |

---

## Group E — scientific diagnostics and failure analysis

### Figure G1 · Where the uncertainty intervals do not hold

| | |
|---|---|
| **Image** | `paper/figures/diagnostics/Figure_G1_calibration_failure.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/diagnostics_phase_h_coverage.csv`, `diagnostics_subgroup_coverage.csv`, `diagnostics_temporal_coverage.csv` |
| **Script** | `scripts/figures/fig_diagnostics.py::fig_g1` |
| **Manuscript** | §9, §17 *Uncertainty Evaluation*, §20 |
| **Purpose** | All 24 Phase H cells with their recorded verdicts (11 deviate significantly), coverage by subgroup, and coverage decay across the test window. |
| **Provenance** | `outputs/phase_h/coverage_table.csv`; `reentry_lifetime/origin2016_uncontrolled/{subgroups,temporal_coverage}_test.csv`. |
| **Validation** | **Inspected and asserted.** The failing-cell count (11 of 24) is asserted, not narrated. Over-covering cells are drawn as failures too, because an interval wider than it claims is uninformative rather than safe. |
| **Limitations** | Subgroup panels are origin 2016 only. Exchangeability fails by construction under temporal shift, so **no distribution-free guarantee is claimed anywhere in this project**. |

### Figure G2 · Lifetime residuals and the uncertainty that should track them

| | |
|---|---|
| **Image** | `paper/figures/diagnostics/Figure_G2_residuals_uncertainty.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/diagnostics_lifetime_residuals.csv` |
| **Script** | `scripts/figures/fig_diagnostics.py::fig_g2` |
| **Manuscript** | §17, §20 |
| **Purpose** | Residual distributions, whether interval width tracks error (ρ = +0.18 to +0.42), and the coverage-against-width trade-off across all 19 arms. |
| **Provenance** | `reentry_lifetime/origin2016_uncontrolled/test_predictions.npz` and `regression_test.csv`. |
| **Validation** | **Inspected and asserted.** `cov80` recomputed independently from the raw prediction arrays reproduces the published table exactly (0.716924 for `cosmos_gated`), which is asserted for all three arms shown. |
| **Limitations** | Residuals use only the 1,316 objects observed to decay inside the five-year window; the other 1,662 sit at the 1826.25-day cap and are **right-censored, so no error is defined for them** — including them would manufacture accuracy. Width-against-error is only weakly positive, so a wide interval is a weak signal of a hard object. |

### Figure G3 · Cross-module couplings, as tested

| | |
|---|---|
| **Image** | `paper/figures/diagnostics/Figure_G3_coupling_failure.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/diagnostics_c1_family_effect.csv`, `diagnostics_coupling_verdicts.csv` |
| **Script** | `scripts/figures/fig_diagnostics.py::fig_g3` |
| **Manuscript** | §6, §19, §20 |
| **Purpose** | The integration claim as actually tested: C1 with per-cell intervals separating the common learner from each origin's own selection, and the recorded verdict for all four couplings. |
| **Provenance** | `outputs/e12_same_learner/e12_results.json`; `outputs/phase_e/phase_e_results.json` (verdicts and caveats quoted verbatim). |
| **Validation** | **Inspected and asserted.** Tests pin that exactly one of four cells survives BH correction, that it is an origin-selected learner, and that the two common-learner cells flip sign and neither is significant. |
| **Limitations** | Every result here is a **post-hoc re-analysis** of test sets scored by earlier studies, not a confirmatory test. C4 carries no interval because it has no data — 0 joinable pairs — so it is not evaluable rather than evaluated and failed. Caveat text is truncated where an ellipsis appears. |

---

## Group F — digital-twin system outputs

### Figure S1 · Digital-twin snapshot 2026-10-27

| | |
|---|---|
| **Image** | `paper/figures/system_outputs/Figure_S1_twin_snapshot.{png,pdf,svg}` |
| **Source data** | `paper/figures/data/twin_snapshot_summary.csv` |
| **Script** | `scripts/figures/fig_system_outputs.py::fig_s1` |
| **Manuscript** | §6 (system scope); not used for any claim in §14 |
| **Purpose** | Real outputs from one versioned run: regime mix, re-entry probability concentration, expected counts by model variant, the twelve highest-priority objects with intervals, and the evidence state including known defects. |
| **Provenance** | `outputs/twin/as_of_2026-10-27/{forecast_table.csv.gz,summary.json,top50_reentry_30d.csv}`, digests in `FORECAST_SHA256.txt`. |
| **Validation** | **Inspected and asserted.** The L17 count (123 of 13,238) and the coherence of the ranking column (0 of 31,396) are recomputed from the artifact in both the figure script and the test, not quoted. |
| **Limitations** | **These are predictions, not verified outcomes** — the follow-up window for this snapshot has not elapsed and the console marks prospective validation as blocked. The three re-entry variants disagree by 10.6× on the 30-day expected count, so a single headline count would be an artefact of the variant chosen. The twelve top objects all sit at p₃₀ = 1.000, so their relative order is not meaningful. The 123 L17 records are **preserved, not repaired**. |

---

## Pre-existing figures retained

These predate this collection and are left untouched, as original artifacts:

| Path | Note |
|---|---|
| `paper/figures/{selection_landscape,test_arms_m1,test_arms_m2}.png` | Earlier draft figures at the `paper/figures/` root, superseded by J3/J4/J5. |
| `paper/jint/figures/Figure_{1,2,3}_*.png` | The previous three-figure JINT set, superseded by J1–J6. The manuscript now references the new set. |
| `thesis/figures/*` (6 graphviz diagrams + 20 plots) | Thesis figures, unchanged. |
| `outputs/benchmarks/figures/*`, `outputs/g5_figures/*`, `outputs/g5d_origin2006/figures/*` | Experiment-time plots, unchanged. |
