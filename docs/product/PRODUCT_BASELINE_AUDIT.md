# Product baseline audit

Date: 2026-11-04. Verified by inspection and execution, not taken from the Phase A–D reports.

## Repository state

| Item | Verified value |
|---|---|
| Branch | `main` |
| HEAD | `78ee339` "Correct the published dataset sizes to true byte counts" |
| Working tree | Modified; Phase C/D work uncommitted (14 modified tracked files, 20 untracked paths) |
| Test baseline | **134 passed, 0 failed, exit 0** (`.venv/bin/python -m pytest tests/ -q`, 33.97 s) |
| Pre-registration freeze | **INTACT** |
| Hashed forecast `twins.jsonl` | **OK** (digest re-verified) |

The Phase A–D claims checked out. Nothing in this audit contradicts them.

## Existing stack

There is **no web application today**. The current "dashboard" is a static HTML generator:

- Entry point: `python -m cosmos.ai.dashboard` → `cosmos/ai/dashboard.py`
- Behaviour: reads saved artifacts, emits one self-contained HTML file, refuses to overwrite
  without `--overwrite`, selects one pipeline run via `--run`.
- It has no server, no routing, no interactivity, no object search, and no report export.

It is a correct, conservative evidence renderer, and its guarantees (one run only, snapshot
mixing flagged, abstentions shown with reasons) are worth preserving. **It will not be
replaced or deleted** — the console reuses its logic and the static generator stays working.

### Dependencies already installed in `.venv` (no new installs needed)

| Package | Version | Use |
|---|---|---|
| fastapi | 0.162.0 | HTTP API and server-rendered pages |
| uvicorn | 0.54.0 | ASGI server |
| jinja2 | 3.1.6 | templates |
| starlette | 1.10.0 | routing, static files, test client |
| pydantic | 2.14.1 | request/response validation |
| httpx | 0.28.1 | `TestClient` transport for product tests |
| pytest | 9.2.0 | tests |
| pillow | — | SpotGEO image serving |

**Not installed**: plotly, altair, bokeh, dash, streamlit, node/npm. Consequence: charts are
generated **server-side as inline SVG from real arrays**. No build step, no CDN, works offline
in a live demo, and nothing can render a decorative chart that has no data behind it.

## Executable operations through the current pipeline

Verified by running `scripts/run_pipeline.py` and inspecting `cosmos/ai/adapters.py`.

| Module | Depends on | Executable now | Source artifact |
|---|---|---|---|
| `catalogue_state` | — | **Yes** | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` |
| `lifetime` | `catalogue_state` | **Yes** | same snapshot |
| `reentry` | `catalogue_state` | **Yes** | same snapshot |
| `collision` | — | **Yes** | `outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz` |
| `health` | — | **Yes** | `outputs/benchmarks/telemetry_esa_adb/results.csv` |
| `debris` | — | **Yes** | `outputs/benchmarks/vision_spotgeo/classical_cosmos_frontend_test_submission.json` |
| `decision_priority` | `catalogue_state`, `lifetime`, `reentry` | **Yes** | upstream modules |

A scenario run is cheap: the full 7-module run completes in **under 1 second** and writes a
new timestamped directory. This makes live scenario execution safe to demo.

## Data available per product area

| Area | Real data available | Keyed by | Honest limit |
|---|---|---|---|
| Mission overview | 31,396 catalogue objects; 2 existing runs | run ID | — |
| Satellite telemetry | ESA-ADB Mission 1 (1,472,832 × 76 ch @ 5 min from 2000-01-01), Mission 2, Mission 3; 3,589 labelled intervals for M1 with class/category | **anonymised mission + channel** | **Not NORAD-addressable.** Missions are anonymised; no catalogue object has telemetry |
| Orbital | perigee/apogee/inclination, mass, regime, class, families | **NORAD** | mean elements only — no state vectors |
| Lifetime | quantiles + horizon probabilities | NORAD | L17: 0.93 % non-coherent rows abstain |
| Debris | **32,000 SpotGEO PNGs** (5,120 test sequences × 5 frames, 640×480 grayscale); 25,600 detection records matching exactly | sequence + frame | **no confidence, no absolute UTC time** |
| Collision | 2,167 anonymised CAC events, 7 quantiles of log10 probability | positional event index | not linkable to any catalogue object |
| Re-entry | horizon probabilities + Monte-Carlo time quantiles | NORAD | **no validated impact coordinates** |
| Prospective eval | — | — | **BLOCKED**: newest outcome coverage 2026-10-26, i.e. −1 day |

### The central product constraint

**Telemetry and the catalogue cannot be joined.** ESA-ADB missions are anonymised; CAC events
are anonymised. Only `catalogue_state → lifetime → reentry → decision_priority` is
identity-linked, by NORAD, within one snapshot.

The product must therefore present **two distinct selectable entity types** rather than
pretending to one unified "satellite" record:

1. a **catalogue object**, chosen by NORAD ID — orbital, lifetime, re-entry, priority;
2. a **telemetry channel** of an anonymised ESA-ADB mission — health evidence.

Selecting a NORAD object must state plainly that no telemetry exists for it. Any UI that let a
user "open NORAD 37607 and see its telemetry" would be fabrication.

## Output classification

| Class | Examples |
|---|---|
| **Historical** | `outputs/twin/as_of_2026-10-27/` (hashed), `outputs/benchmarks/**`, the two existing pipeline runs |
| **Newly computable** | any new `outputs/pipeline/run_<ts>/` from the 7 adapters over the same artifacts |
| **Simulated** | `outputs/run_20261103T155605Z/core_pipeline/impact_predictions.csv` — legacy synthetic chain with lat/lon; **must never be shown as a validated impact location** |
| **Unavailable** | per-detection confidence, absolute observation times, telemetry for catalogue objects, state vectors |
| **Blocked** | prospective evaluation of the dated forecast |

## Risks for productization

1. **Impact-coordinate temptation.** A lat/lon CSV exists and would render as a convincing map.
   It is synthetic. Mitigation: excluded from Re-entry Intelligence; reachable only under an
   explicit simulated-scenario label.
2. **Telemetry/catalogue conflation** — see above. Mitigation: two entity types, explicit
   "no telemetry for this object" state.
3. **Green-everywhere UI.** 7/7 success is a software result. Mitigation: distinct PASS /
   PARTIAL / FAIL / BLOCKED / ABSTAIN tokens with separate colours; abstentions surfaced, not
   hidden.
4. **Memory.** Mission 1 `X` is 448 MB. Mitigation: cache at most one mission, decimate
   server-side to ~2,000 points per chart.
5. **Overwriting history.** Mitigation: reuse the existing refusal-to-overwrite behaviour; the
   API never writes outside a fresh run directory.

## Plan — highest-value vertical slice first

| Stage | Deliverable |
|---|---|
| P1.1 | `cosmos/product/`: FastAPI app, read-only data access over artifacts, Jinja2 templates, CSS, server-side SVG charts |
| P1.2 | Mission Overview + Run Explorer (historical mode) |
| P1.3 | Orbital/Lifetime/Re-entry object view by NORAD (Demo 2) |
| P1.4 | Telemetry channel view with labelled anomalies (Demo 1) |
| P1.5 | Debris imagery with real detection overlay; Risk view (Demo 3) |
| P1.6 | Scenario execution into a new run directory; prospective mode shown BLOCKED |
| P1.7 | Report export (HTML + JSON) with full provenance |
| P1.8 | Product tests (17 required scenarios) + docs + screenshots |

No second scientific engine: every number comes from `cosmos.ai.adapters`,
`cosmos.ai.orchestration` and the saved artifacts.
