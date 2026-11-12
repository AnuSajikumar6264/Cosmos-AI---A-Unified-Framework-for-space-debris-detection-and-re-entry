# Known limitations — Mission Intelligence Console

Date: 2026-11-04. Product limitations only; the scientific limitations register
([`../research/limitations_register.md`](../research/limitations_register.md)) still applies in
full and is referenced by ID below.

## Hard data constraints — cannot be engineered away

| ID | Limitation | Consequence in the product |
|---|---|---|
| P1 | **No live data feed.** Nothing connects to a real-time tracking source. | Every page describes a dated snapshot (2026-10-27) or a saved benchmark. The console says so on each screen. **Never describe this as live tracking.** |
| P2 | **Telemetry is anonymised** (ESA-ADB Mission 1/2/3) — see L1. | No catalogue object has telemetry. Every object page reports health as UNSUPPORTED with the reason. A per-spacecraft health assessment is impossible from this data. |
| P3 | **Conjunction events are anonymised** (Kelvins CAC) — see L1. | Collision evidence is never attributed to a named object. Coupling C4 abstains rather than escalating. |
| P4 | **No validated impact location, ground track, corridor or footprint** — see L5. | No map or trajectory view exists. A legacy lat/lon file from the synthetic chain is in the repository and is **deliberately not surfaced**; it is simulated, not an impact prediction. |
| P5 | **Catalogue publishes mean elements, not state vectors.** | No position/velocity is shown or derived. No 3-D orbit animation was built, since it would need a state vector the data lacks. |
| P6 | **Prospective evaluation is blocked** — see L3b. | The mode is disabled; outcome coverage ends 2026-10-26, one day before the forecast. Needs a snapshot dated ≥ 2026-11-26 and explicit download authorisation. |
| P7 | **Debris detections have no confidence and no absolute time.** | Markers are fixed-size rings; the confidence column reads "not reported"; no timestamp is shown. Pixel positions cannot be matched to a catalogued object without astrometric calibration. |

## Display and interpretation hazards — mitigated, worth knowing

| ID | Limitation | Mitigation |
|---|---|---|
| P8 | **Zero-width intervals.** 13,765 of 15,010 objects have `lo90 == median == hi90`; 13,756 of those sit at the 1826.25-day study cap. Shown naively this reads as extreme precision. | `interval_quality()` labels each interval `AT CAP`, `ZERO WIDTH` or a normal spread, with an explicit "do not read as precision" warning on the page and in the report. |
| P9 | **Incoherent per-horizon lifetime probabilities** (L17). 123 of 13,238 objects violate `P(30 d) ≤ P(90 d) ≤ P(1 yr)`. | The object page shows `INCOHERENT` with the cause; the pipeline abstains for those objects. The decision not to recalibrate is recorded in `L17_METHODOLOGY_DECISION.md`. |
| P10 | **Benchmark F0.5 is not a spacecraft health score.** | Labelled as a detection-performance measurement of a benchmark arm wherever shown. |
| P11 | **Monte-Carlo spread is not a conformal interval** (L8). | The phrase "not a conformal interval and not a distribution-free coverage guarantee" accompanies every re-entry interval. |
| P12 | **Labelled telemetry intervals are ground truth, not detections.** | The channel page states this; no per-sample anomaly score exists in the artifact and none is drawn. |
| P13 | **Telemetry charts are strided subsamples.** | The stride and total sample count are displayed; gaps are drawn as breaks, never interpolated. |
| P14 | **A dirty worktree may mean outputs do not match the named commit.** | Overview and run pages flag `MODIFIED` with that wording. |

## Engineering limitations

| ID | Limitation | Detail / workaround |
|---|---|---|
| P15 | **No PNG screenshots.** No headless browser is installed and installing one needs an unauthorised network download. **BLOCKED.** | `scripts/capture_console_screens.py` saves the real rendered pages as self-contained HTML in `outputs/product/screens/`. For PNGs, install playwright and capture from the running server. |
| P16 | **No authentication or authorisation.** | Default host is loopback. Only use `--host 0.0.0.0` on a trusted network. Do not expose to the internet. |
| P17 | **Telemetry memory footprint.** Mission 1's array is 448 MB; one mission is cached at a time. | First chart load takes ~1–2 s. Switching missions evicts the previous one. |
| P18 | **Scenario runs are synchronous.** The 7-module run takes under a second, so no job queue exists. | A much larger `--limit` would block the request. Use the CLI for bulk runs. |
| P19 | **Single-user, single-process.** No session state, no concurrency control beyond uvicorn's defaults. | Adequate for a demonstration; not a multi-tenant deployment. |
| P20 | **`lru_cache` on store methods pins the instance.** | Harmless for one app-level store; would leak if many stores were created per request. |
| P21 | **Run comparison is status-level only.** It does not diff table contents. | Use `/api/runs/{id}/tables/{name}` to compare values manually. |
| P22 | **No pagination.** Searches cap at 60 results and tables at a few hundred rows. | Use the JSON API with a higher `limit` for more. |
| P23 | **Charts are static SVG.** No zoom, pan or brush. | Deliberate: no plotting library is installed, and server-side SVG cannot render a chart without data behind it. |

## Deliberately not built

Each of these was technically possible and was rejected because the data does not support it
honestly.

- **A 3-D globe or orbit animation** — needs state vectors the catalogue does not publish (P5).
- **A re-entry ground-track or impact map** — no validated impact location exists (P4). The
  synthetic lat/lon file was left unsurfaced rather than labelled "illustrative" on a map,
  because a map of plausible impact points is the single most misleading artefact this product
  could contain.
- **A per-satellite health score for catalogue objects** — telemetry is anonymised (P2).
- **A health-driven collision escalation** — C4 cannot be computed (P3). It abstains instead.
- **Decorative charts** that fill empty panels — panels state UNAVAILABLE instead.
- **A unified "satellite record"** merging telemetry and catalogue — the two cannot be joined.

## Research limitations the console inherits (consolidated 2026-11-08)

These fifteen limitations hold for the system as deployed; each is stated on the relevant screen and in
`docs/research/COSMOS_AI_FINAL_COMPLETION_AUDIT.md` §5.

1. ESA-ADB anonymisation prevents any join between a telemetry mission and a catalogued object.
2. Kelvins CAC anonymisation prevents any join between a conjunction event and a NORAD id.
3. Space-weather features (F10.7, Ap) are constant across the objects of the current snapshot.
4. Cross-satellite generalisation is not established (one spacecraft per telemetry mission).
5. Health-to-conjunction fusion is not established; coupling C4 abstains.
6. Re-entry model variants disagree substantially (up to 10.6× in expected 30-day counts, X7); the variants are shown side by side.
7. The historical L17 lifetime records (123) contain cross-horizon incoherence; the chain abstains for them.
8. Isotonic per-horizon probabilities disagree with the quantile outputs on some objects; the coherent reading is reported separately.
9. Some uncertainty-coverage strata are under-covered (design-derived area-to-mass objects at origin 2016: 0.5625 vs 0.80; the high-risk conjunction stratum).
10. Several learner backends (kumo, tabm, tabicl, lightgbm, catboost, statsmodels) and all persisted model weights are unavailable; model version is unavailable throughout.
11. `fusion.decide` is implemented and unit-tested but is not the deployed decision path.
12. The priority ranking uses the point probability and the GCAT mass, not the uncertainty interval.
13. The deployed runtime performs no on-demand model inference; it re-expresses archived artifacts.
14. Live satellite telemetry and live data ingestion are not established; the snapshot is dated 2026-10-27.
15. Prospective (blind) validation is pending a catalogue snapshot dated on or after 2026-11-26.

## Claims that must never be made about this product

- that it tracks satellites live, or in real time;
- that it performs validated collision avoidance;
- that it predicts validated impact locations;
- that a historical run is a real-time assessment;
- that passing tests constitutes scientific validation;
- that the four couplings have demonstrated scientific benefit (no ablations have been run);
- that any result here is independently or prospectively validated.
