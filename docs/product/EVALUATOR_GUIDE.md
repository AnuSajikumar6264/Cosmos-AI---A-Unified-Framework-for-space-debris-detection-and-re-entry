# COSMOS-AI — Evaluator guide (release candidate `v1.0-demonstration-2026-11-08`)

Written for: examiners and reviewers who evaluate the project from the repository, without the presenter. Everything below
is read from archived files; the console runs no model at request time and connects to no live source. Nothing here is live
telemetry, an operational warning or a prospective result. Longer references: `DEMO_SCRIPT.md` (presenter's thirteen stages),
`DEMONSTRATION_PROTOCOL.md` (verified objects and expected outputs), `PRODUCT_USER_GUIDE.md` (every screen), `KNOWN_LIMITATIONS.md`;
setup and execution in full: [`COSMOS_AI_QUICKSTART.md`](COSMOS_AI_QUICKSTART.md) and [`COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md`](COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md).

## 1. Launch (five minutes)

```bash
git lfs install && git clone --branch product/mission-intelligence-console https://github.com/AnuSajikumar6264/Cosmos-AI-.git cosmos-ai
cd cosmos-ai && git lfs pull                                   # 831 LFS files ≈ 0.9 GB (see CONSOLE_LAUNCH.md §0)
python scripts/check_console_prerequisites.py                 # exit 0 = launchable; names anything missing
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh   # one archived-artifact run, ≈ 9 s (fresh clones only)
python scripts/serve_console.py                               # http://127.0.0.1:8070/  — open /demo first
curl -s http://127.0.0.1:8070/api/ready                       # {"ready": true, ...}
```

Python ≥ 3.11 with `fastapi`, `uvicorn`, `jinja2`, `pandas`, `numpy`. No learner backend is needed to serve the console.
On the project machine the working tree already holds the pipeline runs, so the `run_pipeline.py` line is unnecessary there.

## 2. What each screen demonstrates

| Screen | Route | What to look for |
|---|---|---|
| Guided demonstration | `/demo` | capability map (implemented / benchmark-only / unavailable / blocked) and the thirteen stages with live values |
| Mission overview + readiness | `/`, `/api/ready` | STALE snapshot age (2026-10-27) computed on every load; nine modules of the latest run; abstention counts; the readiness record (files and digests, never spacecraft) |
| Object explorer | `/objects`, `/objects/{norad}` | search by NORAD id or name; mean elements; lifetime, re-entry, decision-priority and twin-state panels with their evidence status |
| Lifetime estimation | object page, "Orbital lifetime assessment" | conformal interval from the archived lifetime expert; horizon relation; subgroup-coverage cue; abstention for the 123 non-coherent records (L17) |
| Re-entry prediction | object page, "Re-entry assessment" | p(30 d), Monte-Carlo quantiles, interval-quality label (zero-width, spread, at the cap, unavailable); variants side by side, never averaged |
| Health / telemetry evidence | `/telemetry` | three anonymised ESA-ADB missions: real samples and ground-truth intervals; the alarm-layer finding; no mission can be joined to an object |
| Collision / conjunction evidence | `/risk` | 2,167 held-out Kelvins events; quantile regression of log10 collision probability; the reliability gate's weight near zero; coupling C4 abstains |
| Debris / optical imagery | `/debris`, sequence pages | SpotGEO frames with the classical front end's detections (F1 0.084); the learned U-Net's scores are archived but its detections are not, so none are drawn |
| Decision priority | object page, "Decision priority" | rank among 31,396 objects; the formula read from the run manifest (`p_30d × 2` when mass ≥ 500 kg); an ordering, not a probability |
| Twin-state explorer + provenance | `/twin-state`, `?policy=archived_only` | re-emitted `twin_state/1.1` selected as primary, digest verified, 31,396 records valid and value-equivalent to the chain; the explicit archived read is amber and carries no per-output provenance |
| Run explorer and comparison | `/runs`, `/runs/{id}`, `/compare` | module lineage (code, configuration, data artifacts, model version); byte-identical tables by digest; differences by key |
| Scenario analysis | `/scenario` | the real pipeline in a child process over saved artifacts into a new run directory; module statuses, configuration digest, changed assumptions; nothing retrained |
| Reports and downloads | `/reports/object/{norad}`, `/download` | redacted export with hashes and run id preserved |
| Research results and figures | `/telemetry`, `/risk`, `/debris` methodology blocks; `paper/figures/` | benchmark tables and methodology text in the console; the frozen figure release (107 hashed files) lives in the repository, not in the console |

## 3. Example objects to select (values verified from a fresh process on 2026-11-08)

| NORAD | Object | Why it is in the demonstration | What you should see |
|---|---|---|---|
| 37607 | ARIANE 5 R/B | primary case: design-derived area-to-mass, natural decay | p(30 d) = 1.0; quantiles at 10 days (zero-width, labelled degenerate); lifetime median 27.5 d crossing the 30-day horizon; priority rank 2 of 31,396; twin equal to the chain on 20 of 20 fields |
| 23806 | TITAN 34B DEB | fragment whose lifetime record is one of the 123 non-coherent ones | lifetime marked incoherent and abstained (L17); re-entry p(30 d) = 0.72 with a 5–95 % Monte-Carlo spread; rank 21 |
| 25544 | ISS (ZARYA) | operator-controlled payload | re-entry abstention with the payload base rate (0.0053) and no quantiles; lifetime unavailable; rank 55; twin and chain represent the abstention differently and the page says so |
| 12 | VANGUARD R/B | at the prediction cap | quantiles at 1826.25 days (censored at the cap: "not expected within 1826.25 days"); lifetime entirely after the horizon; rank 13,903 |

## 4. Scientific results worth inspecting, and where their evidence is

| Result | Status | Evidence |
|---|---|---|
| K6: alarm-layer selection data dominate scorer capacity (H6 +0.353, Holm p = 0.0015; H4/H5 refuted) | pre-registered, confirmatory | `outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json`, `paper/jint/` |
| K7: lifetime benchmark; selection does not transfer (regret +18.7 % at origin 2016); coverage failure localised to the design-derived subgroup (0.5625 vs 0.80) | archived, partly pre-registered (G5d inconclusive by its own rule) | `outputs/benchmarks/reentry_lifetime/`, `outputs/am_design_stage1/`, `paper/k7_lifetime_benchmark/` |
| K8: OPS-SAT fusion withdrawn; the calibration gain comes from the feature branch (X10) | negative result, kept | `docs/research/PHASE8_APPROVED_ANALYSES_REPORT_2026-11-08.md` |
| K1 integration: health-to-conjunction fusion not supported; C4 abstains | negative result, kept | `docs/research/COSMOS_AI_ARCHITECTURE_INTEGRATION_AUDIT.md` |
| T1 ranking utility: 18 of 29 re-entries in the top 25 on the X7 population (precision 0.72 vs 0.16 for perigee ordering); the mass multiplier costs 0.08 at k = 25; 65 of 101 all-object re-entries were operator deorbits outside the twin's scope | exploratory, non-blind (window analysed before) | `outputs/t1_ranking_utility/results.json`, `docs/research/T1_RANKING_UTILITY_RESULTS.md` |
| Twin-state equivalence: 31,396 of 31,396 records value-equivalent to the runtime chain | engineering verification | `outputs/audit/twin_state_integration_check_*.json`, `/twin-state` |

## 5. How to read uncertainty and abstention

- **Intervals** are labelled by kind: a *conformal* lifetime interval (calibrated on tune-B, with a subgroup-coverage cue
  that is a frequency over a subgroup, not this object's probability); a *Monte-Carlo spread* for re-entry (not a coverage
  guarantee); a *zero-width* interval means the integrator's discretisation, not confidence; *at the cap* means "not within
  1826.25 days", not a lifetime of that length.
- **Abstention** is a first-class value. The console abstains for operator-controlled objects (drag physics does not decide),
  for the 123 L17 records (non-monotone per-horizon probabilities), for C4 (no health-to-conjunction fusion) and wherever an
  artifact is absent. An abstention is never replaced by a default number.
- **Priority** uses the point probability and the catalogued mass; it does not use the interval, and its effectiveness has
  been measured only on the non-blind T1 window (§4).
- **STALE** on every page means the snapshot is dated 2026-10-27 and the console refuses to call it current.

## 6. Archived versus benchmark-only versus not integrated

- **Archived and keyed by NORAD id (shown per object):** catalogue elements, lifetime estimates, re-entry forecasts, decision
  priority, twin state (as of 2026-10-27).
- **Benchmark-only (independent evidence roots, never attributed to an object):** ESA-ADB telemetry (anonymised missions),
  Kelvins conjunction events (anonymised), SpotGEO imagery (uncalibrated frames). The console labels these screens accordingly
  and never links them to a satellite.
- **Not operationally integrated:** live telemetry ingestion, on-demand inference, spacecraft health verdicts, collision
  warnings for named objects, debris-to-object association, `fusion.decide` as the decision path, interval-aware priority,
  persisted model weights (none exist), prospective (blind) validation (blocked until a snapshot dated ≥ 2026-11-26).
  `KNOWN_LIMITATIONS.md` lists the fifteen research limitations the console inherits.

## 7. Verifying the release yourself

```bash
python -m pytest tests/ -q -rs                        # full suite; skips name the optional artifact they need
python scripts/audit_manuscript_claims.py             # 147 manuscript checks, expected 0 FAIL
python scripts/verify_protected_artifacts.py --label evaluator   # frozen research artifacts, figure release, twin digests
python scripts/rehearse_demo.py --label evaluator     # thirteen stages from a fresh process
python scripts/twin_state_integrity.py                # twin selection, integrity and equivalence with the latest run
```
