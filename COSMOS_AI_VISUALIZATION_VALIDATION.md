# COSMOS-AI visualisation validation report

Date 2026-11-05 · 18 figures generated, 18 inspected, 0 accepted without inspection

This records what was generated, what was checked and how, what could not be generated, and the
defects found and fixed along the way. It is a verification record, not a summary of the figures;
for the figures themselves see `COSMOS_AI_FIGURE_CATALOGUE.md`.

---

## 1. What was generated

| Group | Figures | Script | Source-data files |
|---|---|---|---|
| architecture | A1, A2 | `scripts/figures/fig_architecture.py` | 2 |
| datasets | D1, D2, D3, D4 | `scripts/figures/fig_datasets.py` | 5 |
| benchmarks | B1, B2 | `scripts/figures/fig_benchmarks.py` | 3 |
| jint | J1–J6 | `scripts/figures/fig_jint.py` | 6 |
| diagnostics | G1, G2, G3 | `scripts/figures/fig_diagnostics.py` | 6 |
| system_outputs | S1 | `scripts/figures/fig_system_outputs.py` | 1 |
| **total** | **18** | 6 scripts + 2 shared modules | **23** |

Formats: PNG at 400 dpi, plus PDF and SVG vector source for all 18 (54 image files).
Shared modules: `scripts/figures/figstyle.py` (palette, typography, export, diagram primitives) and
`scripts/figures/palette_check.py` (computable colour checks).

## 2. Datasets and artifacts used

Read-only. No artifact was modified, and nothing was recomputed that an archive already recorded.

| Artifact | Used by |
|---|---|
| `outputs/benchmarks/telemetry_esa_adb/oof_protocol/test/*.json` | J1, J3, J4, J6 |
| `outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json` | J2, J3 |
| `outputs/benchmarks/telemetry_esa_adb/results.csv` | J5, B1 |
| `outputs/benchmarks/reentry_lifetime/origin{2011,2016}_uncontrolled/*` | B1, B2, G1, G2 |
| `outputs/benchmarks/conjunction_kelvins_cac/{test_results.csv,summary.json}` | B1, D3 |
| `outputs/benchmarks/vision_spotgeo/summary.csv` | B1 |
| `outputs/benchmarks/reentry_landmark/results.csv` | B1 |
| `outputs/phase_h/coverage_table.csv` | G1 |
| `outputs/phase_e/phase_e_results.json` | A1, G3 |
| `outputs/e12_same_learner/e12_results.json` | G3 |
| `outputs/twin/as_of_2026-10-27/*` | D4, S1 |
| `data/DATASET_REPORT.json` | A1, D1, D2, D3 |
| `cosmos/ai/{adapters,fusion,contracts}.py` | A1, A2 (structure, not data) |

## 3. Values verified, and how

Verification was by recomputation from the artifact, not by reading the figure. The checks below
are in `tests/test_figures.py` (36 tests, all passing) and run on every regeneration.

| Check | Result |
|---|---|
| Six pre-registered contrasts against frozen record `09a98f5e160e` | **match to 1e−12** on point estimate, both interval bounds and verdict |
| Contrast signs (guards against the earlier M2/H6 sign error) | M1 H6 > +0.3, M2 H6 < −0.08, M1 H4 and H5 negative — **as frozen** |
| A0 from `CONFIRMATORY.json` vs `results.csv` | **identical**; the generating script aborts on disagreement |
| False-alarm ratio, two independent routes | rate 176336.9006 / 1.1427454 and runs 1,234,479 / 8 both give **154,310** |
| Annualisation period across all five alarm layers | `false_alarm_runs / false_alarms_per_year` = **7.0007 years for every layer** (spread < 1e−3) |
| Alarm-run decomposition | anomaly + rare-only + false-alarm runs **sum exactly** to `alarm_runs` for all five layers |
| Recall → whole anomalies | 0.927/0.582/0.145/0.145/0.036 × 55 give exactly **51, 32, 8, 8, 2** |
| `cov80` recomputed from raw prediction arrays | **0.716924** for `cosmos_gated`, equal to the published table; asserted for all three arms shown |
| Residual sample size vs `n_decayed` | **1,316 = 1,316**; 1,662 censored objects excluded |
| Phase H failing-cell count | **11 of 24** deviate significantly |
| L17 record recomputed from the released artifact | **123 of 13,238** incoherent `p_lifetime_*` |
| Ranking column coherence | **0 of 31,396** violations in `p_30d`/`p_90d`/`p_1yr` — verified, not assumed |
| D3 positives vs `DATASET_REPORT.json` | M2 = 6, landmark = 38, three settings below 60 — **match** |
| Space-weather feature variance | `f107_last81` and `ap_last81` have **exactly one distinct value** across 31,396 objects |
| Manuscript vs figure source data | ratio recomputed from the CSV formats to `154,310` and that string is present; `160,000` absent |

### Palette and accessibility

The categorical palette was **computed, not chosen**, by a constrained search over OKLCH space, then
checked by a Python port of the reference validator (same thresholds, same
Machado–Oliveira–Fernandes severity-1.0 colour-vision transforms). On white, **all pairs**:

```
PASS  Lightness band       all 6 inside L 0.43-0.77
PASS  Chroma floor         all 6 >= 0.1
PASS  CVD separation       worst all-pairs dE 11.6 (deutan), target 8.0
PASS  Normal-vision floor  worst all-pairs dE 15.0, floor 15.0
PASS  Contrast vs surface  all 6 >= 3.0:1
```

No warnings, which matters because the scatter and forest figures show every series against every
other, so the all-pairs gate applies rather than the weaker adjacent one. Every series additionally
carries a distinct marker or a direct label, so identity is never colour alone. The architecture
figures use a separate reserved status palette that is never used as a data series.

The previously used palette **failed** this gate (`#eb6834` ↔ `#eda100`, ΔE 13.7 against a floor of
15) and was replaced. Node was unavailable, so the validator was ported to Python rather than
skipped: `python scripts/figures/palette_check.py "<hex,...>" --mode light --pairs all`.

## 4. Inspection record

Every figure was rendered and read before being accepted. The following defects were found by
inspection and fixed — each had passed its data checks, so none would have been caught by tests.

| Figure | Defect found on inspection | Fix |
|---|---|---|
| J1 | `threshold` and `conformal_bh` plot at the identical point and overprinted; label cluster collided | merged into one marker labelled `threshold ≡ BH (primary)`, with the coincidence asserted in code before merging |
| J1 | a dashed line joined the layers, implying a tunable frontier | line removed; layers are discrete configurations |
| J1 | rotated value labels showed ACI's precision as "0.00" | horizontal bars with end labels; now reads `2.4e−5` |
| J1 | BH rolling's precision and ADTQC of 1.000 looked like a strong result | alarm-run count (2) added to every row label |
| J2 | legend overlapped the bottom row; verdict text read "no inference · replication (no inference)" | legend moved below the axes; label de-duplicated |
| J3 | panel note printed over the bars; y-axis ran past 1.0 though F0.5 ≤ 1 | note moved to the caption; axis capped at 1.0 |
| J5 | right-panel scorer names printed over the left panel's cells; lower titles collided with upper tick labels | explicit wide gutters and a dedicated colorbar axes |
| J6 | panel legend overlapped the bottom bar; count axis ran past n = 55 | legend moved below; axis capped at 55 and recall folded into the row labels |
| A1 | header and band titles overlapped the first node rows | full band re-layout on a computed grid |
| A1 | `validated` and `validated-negative` rendered identically in the legend | dash-dot border and paler fill for the negative state |
| A1 | hand-drawn "severed edge" for C4 was anchored to the wrong box and read as clutter | replaced with an explicit sentence naming the two modules and the gating flag |
| A2 | "NOT ESTABLISHED" text overflowed its box | box height derived from wrapped line count |
| A2 | an arrow implied `reported_only` flows into the combination — the opposite of what `decide()` does | band arrows restricted to the `used` side; a dashed line shows `reported_only` bypassing the combination |
| D1 | axis said "bytes" while showing MB; 0.2 MB rendered as "0 MB" | axis relabelled; small sizes get a decimal; status now on every row label |
| D3 | threshold annotation clipped; caption claimed units were shown beside each bar when they were not | annotation re-anchored; unit printed under each row label |
| D3 | SpotGEO showed "44,550 of 44,550 (100.0%)", which carries no information | recounted in frames holding at least one target (19,095 of 25,600) |
| D4 | correlation matrix had blank cells with no explanation | cells marked `n/d` and the constant-feature finding surfaced in the caption and source data |
| D4 | panel (b) coloured `design` as the favourable provenance, contradicting the project's own subgroup result | single colour, with the reason stated in the caption |
| G1 | nominal-level labels printed over the right spine | moved into the legend as line handles |
| G2 | censoring note sat on the histogram; two arm labels overlapped in panel (c) | note moved into the panel title; labels placed on opposite sides |
| G3 | verdict boxes overflowed their borders | box and cursor geometry computed from real font metrics in the axes' own coordinate space |
| S1 | `p₃₀ = 1.000` repeated on all twelve rows, implying a ranking the numbers do not support | replaced by object class and median days, with one note that the order is not meaningful |
| S1 | evidence-state boxes overflowed the panel | type size auto-selected as the largest that fits |

## 5. Scientific errors found and corrected

Three were errors in my own analysis or in the existing manuscript, not layout problems.

**5.1 Averaging over a load-bearing calibrator (B1).** My first version of the ESA-ADB rows averaged
each scorer across alarm layers, reporting the best Mission 1 learned arm as 0.144 when the best
configuration is **0.318**. This is the same class of error that earlier produced a wrong sign for
Mission 2's H6. Fixed: aggregation is now over seeds only, the winning layer is retained and named
in the source data, and `test_b1_does_not_average_over_the_alarm_layer` pins it.

**5.2 The manuscript overstated the `threshold` ≡ `conformal_bh` coincidence.** §14.3 claimed the two
layers were "identical to 17 significant figures on every event-wise metric" while its own table
showed ADTQC 0.737 against 0.738. Direct comparison of the record shows they agree exactly on
event-wise precision, recall and F0.5 and on false alarms per year, and differ in alarm-run count
(90 vs 123), ADTQC (0.737444 vs 0.738044), alarming precision (0.111 vs 0.077) and channel-level
F0.5. The manuscript and Figure J1's caption now say precisely that, and a test forbids the old
blanket claim.

**5.3 A caption asserted the wrong C1 result (G3).** My first draft said the family-feature effect
"reaches significance in neither" origin. One of four cells does reach significance after BH
correction (`tabm` at origin 2016, +0.0056, BH p = 0.011). The accurate statement — now in the
figure — is that holding the learner fixed the effect is −0.0514 at 2011 and +0.0026 at 2016,
significant at neither, so the coupling does not reproduce across origins; the one significant cell
uses the learner its own origin selected and so cannot separate the coupling from the learner.

A fourth, smaller correction: G1's caption initially asserted that the design-derived subgroup is a
small share of the calibration split. That figure comes from an earlier audit and is not shown or
recomputed in this figure, so the claim was replaced with the values the panel actually displays
(0.56–0.59 against nominal 0.80, with object class C worst at 0.54–0.56).

## 6. Requested figures not generated, and why

| Requested | Status | Reason |
|---|---|---|
| ROC / AUROC curves for anomaly detection | **not generated** | The ESA-ADB protocol records store scalar metrics at a selected operating point, not per-point score arrays. OPS-SAT's `test_scores_official.npz` is **absent from disk** (a known open defect), so the curve cannot be drawn from the archive. Drawing one would require rerunning scoring, which is outside this task's scope. |
| Precision–recall curves | **not generated** | Same cause. AUC-PR values exist as scalars for OPS-SAT and the landmark task and are reported numerically; the underlying curves are not archived. |
| Confusion matrices | **partly superseded** | For the alarm-selection study the event-wise analogue is more faithful and is drawn in J6 as the exact three-way decomposition of alarm runs plus detected/missed anomalies. A 2×2 point-level matrix would misrepresent an event-wise metric. |
| Reliability diagrams (binned predicted vs observed) | **not generated** | Would require per-object predicted probabilities paired with realised outcomes. For the twin snapshot the outcomes do not exist yet — the follow-up window has not elapsed. For lifetime, coverage against nominal is the correct calibration view under right-censoring and is drawn in G1. |
| Detection-delay distributions | **not generated** | `median_delay_steps` exists for SMAP/MSL as a scalar per arm, not as a distribution. ESA-ADB reports timing through ADTQC, which is drawn in J1(b). |
| Energy / efficiency measurements | **not generated** | No direct energy measurement exists in this project. Latency and parameter counts are archived for OPS-SAT and SpotGEO but an efficiency claim was explicitly out of scope. |
| Cross-satellite generalisation | **impossible** | One spacecraft per telemetry benchmark. No figure can show it. |
| Health → conjunction fusion demonstration | **impossible** | 0 joinable pairs. Shown as *not evaluable* in A1 and G3 rather than fabricated. |
| OPS-SAT label-efficiency curve | **not regenerated** | Already exists as an experiment-time plot at `outputs/benchmarks/figures/opssat_label_efficiency.png`. The underlying result is `IMPLEMENTED_NOT_VALIDATED` (significance only on the temporally interleaved split), so promoting it into the publication set would overstate it. |
| Prediction-vs-outcome scatter for the twin | **impossible today** | Prospective validation is blocked; the console reports it as such and so does S1. |

## 7. Residual limitations of the collection

1. **Figure J5 and the ESA-ADB rows of B1 use a different selection protocol** from J1–J4 and J6.
   This is stated on both figures, in the catalogue and in a test, but it remains the easiest way
   for a reader to misread the set.
2. **Several J5 cells rest on a single seed.** The per-cell seed count is in the source data but not
   on the heatmap.
3. **The architecture figures are not measurements.** Their component states are transcribed
   judgements with evidence pointers, not computed quantities.
4. **S1 shows predictions, not outcomes.** Nothing in it is evidence that the twin is accurate.
5. **Mission 2 appears in five figures** and in every one carries six anomalies. It is labelled
   "no inference" throughout, but its bars are visually as prominent as Mission 1's.
6. **No figure in this collection demonstrates integration advantage**, because no experiment in
   this project establishes it.

## 8. Reproducibility

```
python scripts/figures/fig_architecture.py     #  2 figures
python scripts/figures/fig_datasets.py         #  4 figures
python scripts/figures/fig_benchmarks.py       #  2 figures
python scripts/figures/fig_jint.py             #  6 figures
python scripts/figures/fig_diagnostics.py      #  3 figures
python scripts/figures/fig_system_outputs.py   #  1 figure
python -m pytest tests/test_figures.py         # 36 consistency tests
python scripts/figures/palette_check.py "#224bb2,#c26201,#15957b,#9c256e,#4a7ae4,#834105" \
       --mode light --surface "#ffffff" --pairs all
```

Deterministic: matplotlib with the Agg backend, no sampling, no random seeds in any figure, no
network access. Every script takes `--root`, `--out`, `--data` and `--only`.

Environment: matplotlib 3.11.2, scipy 1.18.1, pandas, numpy, Python 3.12. Graphviz is **not**
available in this environment, so the architecture diagrams are drawn in matplotlib rather than
regenerated from the `.dot` sources under `thesis/figures/`, which remain unchanged.

## 9. Integrity

No frozen artifact, pre-registration, historical output, published result or existing manuscript
section outside §13b and §14.3 was modified. The three previous JINT figures and the earlier
draft figures at the `paper/figures/` root are retained. The 16 pre-existing manuscript tests still
pass. **No commit, push or upload.**

| Check | Result |
|---|---|
| ESA-ADB freeze id | `09a98f5e160e` unchanged |
| `tests/test_jint_manuscript.py` | 16 passed |
| `tests/test_figures.py` | 36 passed |
| L17 record | 123 records preserved, not repaired |
| Files added | 8 scripts/tests/docs + 54 images + 23 source-data files |
| Files modified | `paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md` (§13b figures, four cross-references, one corrected claim in §14.3) |
