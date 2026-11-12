# COSMOS-AI Mission Intelligence Console — user guide

Written for: someone using the console who has not read the research code.

## What this is, and what it is not

The console lets you explore satellite intelligence assembled from verified COSMOS-AI
artifacts: catalogue objects and their orbital, lifetime and re-entry assessments; real
spacecraft telemetry; debris detections on real imagery; and conjunction risk evidence.

It is **not** a live tracking system. There is no connected satellite feed. Everything you see
describes a **dated snapshot** (2026-10-27) or a saved benchmark. The console will tell you
this on every page, and it will tell you when something is unavailable instead of guessing.

## Starting it

Check prerequisites first (read-only; exit 0 = launchable), then serve. The full launch path, required-versus-optional components and troubleshooting are in `CONSOLE_LAUNCH.md`.

```bash
cd /data2/anupa/Final_Year_Project
python scripts/check_console_prerequisites.py
python scripts/serve_console.py
```

Then open <http://127.0.0.1:8070/>. API documentation is at <http://127.0.0.1:8070/docs>.

Other options:

```bash
.venv/bin/python scripts/serve_console.py --port 9000     # different port
.venv/bin/python scripts/serve_console.py --host 0.0.0.0  # reachable from another machine
.venv/bin/python scripts/serve_console.py --reload        # auto-reload while developing
```

The console has **no authentication**. Only use `--host 0.0.0.0` on a trusted network.

## Reading the status tokens

These appear throughout and have fixed meanings. A green token is never used to make something
look better than it is.

| Token | Meaning |
|---|---|
| **PASS / SUCCESS** | the step executed and produced output |
| **PARTIAL / INCOMPLETE** | some output exists; the run did not finish cleanly |
| **FAIL / FAILED** | the step executed and failed; it wrote no output |
| **BLOCKED** | could not run because something upstream or external is missing |
| **ABSTAIN** | deliberately produced no value, with a stated reason |
| **UNAVAILABLE / UNSUPPORTED** | the data does not exist for this selection |
| **AT CAP** | a quantile sits at the 1826.25-day study horizon — read as "at least", not a precise estimate |
| **ZERO WIDTH** | the Monte Carlo produced no spread; this is discretisation, not confidence |
| **MIXED SNAPSHOTS** | a run's modules disagree on the snapshot date; do not read it as one coherent result |

## The screens

### Mission Overview (`/`)

Snapshot statistics (31,396 objects), assessment findings, module status from the latest run,
abstentions with their reasons, the conjunction probability distribution, recent runs,
provenance (Git commit, worktree state, forecast digest) and the dataset inventory.

Start here in a demonstration. The findings panel is the honest summary: it lists abstentions
and blockers, not just successes.

### Orbital Intelligence (`/objects`)

Search the catalogue by **NORAD ID** or name. Try `37607` (ARIANE 5 R/B) or `ARIANE`.
With no query, objects are ordered by 30-day re-entry probability.

Selecting an object shows: catalogue metadata, mean orbital elements, physical properties,
the re-entry assessment with horizon probabilities and Monte-Carlo quantiles, the lifetime
assessment with its **horizon-coherence status**, and — importantly — explicit panels stating
that telemetry and conjunction evidence are **unsupported for that object**.

You can export an assessment report from here.

> Orbital elements are **mean elements** (perigee/apogee/inclination). The console does not
> show a position/velocity state vector, because the catalogue does not contain one.

### Satellite Intelligence (`/telemetry`)

The ESA-ADB missions. **These are anonymised**: Mission 1/2/3 are real spacecraft telemetry
published without identity, so a channel here belongs to no named satellite and cannot be
matched to a NORAD ID. This is why selecting a catalogue object reports no telemetry.

Opening a channel shows the real series (Mission 1 is 1,472,832 samples at 5-minute cadence
spanning 2000–2013) with ground-truth anomaly and rare-event intervals shaded. The chart is a
**strided subsample**; the stride and the total sample count are both displayed. Gaps in the
line are missing samples, not interpolation.

The benchmark-arm table shows event-wise F0.5 and false-alarm counts. These are
**detection-performance measurements of a benchmark arm**, not a health score for a spacecraft.

### Debris Intelligence (`/debris`)

SpotGEO test sequences. Opening one shows a **real 640×480 frame** with the detector's own
pixel coordinates overlaid; hover a ring for its coordinates.

Two absences are shown as absences: there is **no per-detection confidence** (this front end
emits hard detections) and **no absolute UTC timestamp** (SpotGEO frames carry a frame index).
Without astrometric calibration these pixel positions cannot be matched to a catalogued object.

### Risk Intelligence (`/risk`)

Conjunction evidence from 2,167 anonymised ESA Kelvins CAC events: the distribution of
**physical collision probability**, the high-risk screening threshold at 1e-6, and the
highest-probability events with their 5–95 % bounds.

The `operational priority` column is **deliberately empty**. Priority is a decision-layer
quantity and is never computed from, or fused into, a physical probability. Coupling C4
(health-driven escalation) **abstains**, because no dataset links telemetry health to a
conjunction event.

Values at the 1e-30 reporting floor mean "below the reported floor", not an exact probability.

### Run Explorer (`/runs`)

Every pipeline run as a versioned directory. Opening one shows its manifest: configuration
digest, Git commit, worktree state, per-module status with input sources, abstentions with
reasons, and the tables it wrote. Loading a run never modifies it.

`/compare` puts two runs side by side. Runs with different snapshot dates are flagged
**NOT DIRECTLY COMPARABLE** — their artifacts are never merged.

### Scenario Analysis (`/scenario`)

Execute the supported pipeline. Set the snapshot, object limit, conjunction event count and
debris sequence count, then run. Results appear as a module status table with a link to the new
run.

Each execution writes a **new** timestamped run directory. Nothing previous is overwritten. A
scenario run re-expresses saved artifacts through the shared contracts — it does not retrain,
rescore or revalidate anything.

### Prospective Evaluation (`/prospective`)

Research-only, and currently **BLOCKED**. The dated 2026-10-27 forecast cannot be scored
because the newest catalogue outcome coverage ends 2026-10-26 — one day *before* the forecast.

The page shows the per-horizon requirement (a snapshot dated ≥ 2026-11-26 for 30 days), the
snapshots on disk, and the **fixed evaluation protocol**, published in advance so it cannot be
adjusted after seeing a result. The scoring button is disabled.

## Exporting a report

From any object page: **Download assessment report** (HTML), **Preview in browser**, or
**JSON**.

The report contains the subject, snapshot identifiers and artifact SHA-256, run ID,
configuration digest, Git commit, orbital elements, historical and computed outputs kept
separate, uncertainty, abstentions, unsupported assessments with reasons, and limitations.

Open the HTML file and print to PDF if you need a PDF; it is self-contained and needs no
network.

Samples generated from real artifacts:
`outputs/product/reports/sample_assessment_NORAD37607.html` (a near-term re-entry) and
`sample_assessment_NORAD5.html` (Vanguard 1, censored at the study cap).

## Things that will look like bugs but are not

| What you see | Why |
|---|---|
| "5–95 % spread: 1826.25 – 1826.25 days" labelled **AT CAP** | every Monte-Carlo draw exceeded the 5-year horizon. It means "not re-entering within 5 years", not a precise lifetime. |
| A zero-width interval below the cap | all draws returned the same value — integrator discretisation, not confidence. 8 objects in the snapshot. |
| Lifetime panel says **INCOHERENT** | the saved per-horizon probabilities are calibrated independently per horizon, so a few objects violate `P(30 d) ≤ P(90 d)`. Limitation L17; the final reported forecast is unaffected. |
| An object has no lifetime estimate | the learned expert abstained because the object is outside its fitted cohort. No physics value is substituted. |
| Telemetry says unsupported for every NORAD object | correct: telemetry datasets are anonymised. |
| 16,386 objects are `operator_controlled` with no drag forecast | a controlled payload can manoeuvre, so drag physics does not determine its re-entry. A previous-window base rate is reported instead. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| "No pipeline run is present" | run a scenario, or `python scripts/run_pipeline.py --as-of 2026-10-27 --limit 500` |
| Catalogue panel UNAVAILABLE | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` is missing from the checkout |
| Telemetry missions UNAVAILABLE | `data/feature1_health/external/esa_ad/prepared/*.npz` is missing |
| Debris images MISSING | the SpotGEO test images are not extracted under `data/feature2_debris/spotgeo/raw/extracted/SpotGEOv2/test/` |
| First telemetry chart is slow | Mission 1 is 448 MB; it is cached after the first load (one mission at a time) |
| Port already in use | `--port 9000` |
