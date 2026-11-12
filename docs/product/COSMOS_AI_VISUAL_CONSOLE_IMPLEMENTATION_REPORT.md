# COSMOS-AI — Visual digital-twin console: implementation report (2026-11-09)

Written for: the project owner and anyone reviewing the visual layer before it is committed. Everything below was
executed on 2026-11-09 on the project machine at HEAD `727ecec95fbb8ec3ac47b23df569dc5c376318f4` (release commit D).
Nothing is committed, tagged or pushed. The frozen research evidence is untouched: the protected-artifact verifier
reports `all_protected_ok: True` after the work, and the manuscript claim audit is unchanged at 0 FAIL.

## 1. Existing architecture, as inspected

| Aspect | What was already there |
|---|---|
| Frontend | Server-rendered Jinja2 (17 templates), one stylesheet `cosmos/product/static/console.css`, server-generated inline SVG charts (`charts.py`). **No JavaScript framework, no build step, no npm, no CDN** — a deliberate choice recorded in `requirements-product.txt` so the console runs offline and a demonstration cannot fail on a missing bundle |
| JavaScript before this work | about 25 lines inline in `base.html` (theme toggle, navigation progress bar) and a form helper in `scenario.html` |
| Backend | FastAPI app factory `cosmos/product/api.py`; read-only `cosmos/product/store.py` over archived artifacts; `reports.py` for redacted exports; 17 page routes and 23 JSON operations (`api/1.2`) |
| Data sources | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` (31,396 objects) and the twin-state archives; `outputs/pipeline/run_*/`; ESA-ADB prepared missions; Kelvins CAC predictions; SpotGEO frames and saved detections |
| Orbital parameters actually published | **perigee altitude, apogee altitude, inclination** (catalogue columns `perigee`, `apogee`, `inc`). No RAAN, no argument of perigee, no epoch, no anomaly, no eccentricity column, no state vector (limitation P5) |
| Visualisation libraries | none installed by design; matplotlib exists for offline figure generation only |

Consequence for this task: a 3D view is possible and worth building, but a *physically positioned* satellite or a
ground track is not, and the project had deliberately not built one ("Deliberately not built: a 3-D globe or orbit
animation — needs state vectors the catalogue does not publish", `KNOWN_LIMITATIONS.md`). The design below keeps the
visual ambition and removes the false claim.

## 2. What was built

### 2.1 Technology choice: hand-written WebGL, not Three.js

Three.js would have to be downloaded and vendored, which contradicts the project's offline-by-construction rule and
needs a network fetch that is not authorised. The globe is therefore **about 570 lines of hand-written WebGL 1** with
no dependency: `cosmos/product/static/js/cosmos-globe.js`. It provides a textured Earth sphere, an additive
atmospheric shell, orbit polylines, point markers with a soft sprite, drag-rotate, wheel zoom, keyboard control,
hover, click-to-select, occlusion-correct picking, a reset camera, device-pixel-ratio scaling, context-loss handling
and a power-of-two texture guard. `cosmos-explorer.js` (about 395 lines) wires it to the API and writes every value as
a text node, never as markup.

### 2.2 The geometry is computed server-side, in Python, and is unit-tested

`cosmos/product/geometry.py` (248 lines) turns the three archived quantities into drawable geometry and labels what it
is. This is the heart of the data-integrity design: the browser receives vertices and a statement, and computes
nothing.

| Quantity | Status | How |
|---|---|---|
| semi-major axis, eccentricity, periapsis and apoapsis radii | **derived from the archive** | closed-form two-body relations on perigee and apogee altitudes |
| Keplerian period | **derived from the archive** | `T = 2π√(a³/μ)` with the project's own `MU_EARTH`, `R_EARTH` from `cosmos/common.py` |
| orbit size, shape and tilt as drawn | **archive-derived** | ellipse sampled in eccentric anomaly, rotated by the archived inclination |
| ascending node, argument of perigee, phase | **screen layout, declared non-physical** | deterministic golden-angle sequence keyed to the NORAD id, so nothing moves between page loads |
| position at a time, velocity, sub-satellite point, ground track | **not produced at all** | the archive cannot support them; the payload lists them under `not_available_and_not_invented` |

Every response carries a `geometry_basis` block with that table in words, so a client cannot present the drawing as a
propagated trajectory without contradicting its own data. The explorer page, the object page and the evidence page
repeat the statement on screen.

### 2.3 The Earth texture is real geography, built offline from the repository

`scripts/build_globe_texture.py` builds `cosmos/product/static/earth-land-mask.png` (2048 × 1024, 43 kB) from
`land_fraction` in `data/feature3_reentry/external/population_grid_0p25deg.npz`, already in the repository:
GHS-POP E2020 R2023A (JRC, CC BY 4.0) with Natural Earth 1:50m land (public domain). Land, ocean, coastline and a
30° graticule are drawn from that one array in the console palette. Nothing is downloaded and no geography is
invented. The build **asserts eight known land/ocean coordinates before writing**, so the map cannot be produced
flipped or shifted, and writes a provenance sidecar with the source digest, the palette and the output SHA-256. The
raster is a power of two because WebGL 1 rejects mipmaps and `REPEAT` wrapping otherwise (this was a real bug, found
and fixed during review; an NPOT texture would have rendered the Earth black).

### 2.4 New API, kept minimal

| Route | Purpose |
|---|---|
| `GET /api/globe/objects` | scene geometry: `limit` (20–300), `regime`, `object_class`, `include`, `sort`, `as_of`; returns objects, what was excluded and why, and `geometry_basis` |
| `GET /api/globe/object/{norad}` | one object at higher resolution (193 points), same basis |

No other endpoint was added: the new screens are server-rendered from the existing store, and the selected-object
panel reuses `GET /api/objects/{norad}` unchanged. One read-only store method was added, `ranking_utility_evidence()`,
mirroring the existing `subgroup_coverage_evidence()`.

### 2.5 Design language

`console.css` kept every class the 17 existing templates use (so the restyle cannot change what any page *says*) and
gained a deeper midnight-navy palette, cyan and violet accents, panel depth with hairline glow, an application status
bar, KPI tiles, the globe stage with HUD/legend/controls/tooltip, an object list, the selected-object panel, a mission
timeline and distribution meters. The sidebar gained 15 inline SVG icons (no icon font, no request). Status colour
still comes from the single existing vocabulary (`PASS / PARTIAL / FAIL / BLOCKED / ABSTAIN / UNAVAILABLE`); the globe
adds one legend for object class and nothing else.

## 3. Screens delivered

| # | Mandated screen | Route | Data source | Honesty control on screen |
|---|---|---|---|---|
| 1 | Mission Overview | `/` | `_overview`, `_readiness`, catalogue overview, run list | KPI row, compact globe, mission timeline added **above** the existing panels; "archived, not live"; snapshot age STALE |
| 2 | 3D Earth and Satellite Explorer | `/explorer` | `GET /api/globe/objects` | geometry basis stated in the scope note, the legend, a dedicated panel and the API payload; excluded objects listed with reasons |
| 3 | Satellite Digital Twin | `/objects/{norad}` | `store.object_record` (unchanged) + `GET /api/globe/object/{norad}` | new "Orbit geometry" panel with the schematic-orientation note; all existing panels and `data-test` hooks preserved |
| 4 | Lifetime and Re-entry Intelligence | `/intelligence` | counts over `forecast_table.csv.gz`; run ranking | every figure is a count of archived columns; run-derived table labelled with its run id |
| 5 | Satellite Health and Anomaly Analysis | `/telemetry` (+ channel pages) | ESA-ADB prepared missions, benchmark arm table | KPI row **plus an explicit statement that power, thermal and attitude views are not available** because the channels are anonymised (`channel_1`, `subsystem_1`) |
| 6 | Conjunction and Collision Analysis | `/risk` | Kelvins CAC archived predictions | 2,167 held-out events; `identity_linkable: false`; C4 abstains; "a benchmark label, not a warning" |
| 7 | Space Debris Detection | `/debris`, `/debris/{id}` | SpotGEO frames and the saved classical submission | detection confidence "not reported", absolute time "not available", learned detectors' scores shown but their detections not drawn |
| 8 | Mission Decision Intelligence | `/decisions` | run manifest `priority_rule`, ranking, `outputs/t1_ranking_utility/results.json` | rule read not reimplemented; the T1 evidence is labelled exploratory and **non-blind** with its own caveat block |
| 9 | Evidence, Provenance and Validation | `/evidence` | readiness, catalogue provenance, twin integration, repository provenance, module lineage, schema versions | digests shown; "model version unavailable for every module because no fitted model is persisted" |

Navigation was regrouped (Start here / Mission picture / Analysis / Operate / Reference) with the label
"Health & Telemetry Benchmarks" retained because the demonstration test links by that string.

## 4. Testing and results

| Check | Command | Result |
|---|---|---|
| Full suite, final | `python -m pytest tests/ -q -rs` | **553 passed, 3 skipped, 0 failed** in 138 s (`outputs/audit/pytest_visual_console_accept.log`). Before this work: 508 passed |
| New tests | `python -m pytest tests/test_visual_console.py -q` | **45 passed** (geometry against closed-form physics, payload contracts, screens, texture orientation, JavaScript static checks) |
| Skips | unchanged | the same three optional-artifact skips as before |
| Known-physics checks | in the new tests | period 92.56 min at 400 km circular, 1436.07 min geostationary, 84.49 min surface-grazing; drawn radii equal periapsis/apoapsis; plane tilt equals the archived inclination to 1e-6 before rounding and 0.01° after |
| Cross-screen agreement | in the new tests | for all four demonstration objects, the globe's `archived_elements` equal the digital twin page's `elements` |
| No fabricated state | in the new tests | no endpoint returns latitude, longitude, sub-satellite point, ground track, velocity or a state vector; `state_vector` stays `null` |
| Real server, fresh process | `scripts/serve_console.py --log-json` + curl sweep | 21 pages and all API routes 200 with correct content types; 400/404/422 paths correct; `X-Request-ID` on every response; **zero 5xx and zero tracebacks** in the server log (`outputs/audit/serve_console_visual_20261109.log`) |
| Four demonstration objects | real server | 37607, 23806, 25544, 12 all render with the orbit panel; after restoring a full-snapshot run their ranks are again 2, 21, 55 and 13,903 of 31,396 |
| Protected artifacts | `scripts/verify_protected_artifacts.py --label visual_console` | `all_protected_ok: True` |
| Manuscript claims | `scripts/audit_manuscript_claims.py` | 147 checks, 139 PASS, 8 NOT_EVALUABLE, **0 FAIL** (unchanged) |
| Twin integrity | `scripts/twin_state_integrity.py` | `primary_verified`, 31,396 / 31,396 equal (unchanged) |
| Screens captured | `scripts/capture_console_screens.py` | 20 self-contained HTML captures incl. the five new screens, `outputs/product/screens/` |
| Globe images | `scripts/render_globe_preview.py` | five PNG previews rendered server-side from the live payload |

### Regressions found and fixed during this work

1. Renaming the "Telemetry Benchmarks" navigation label broke `test_d14_health_semantics`, which links by that
   string. The label is now "Health & Telemetry Benchmarks" and the test passes.
2. The new overview KPI row raised a Jinja `UndefinedError` on a fixture root with no catalogue
   (`test_07b_absent_datasets_are_reported_as_unavailable`). The hero is now guarded and degrades to "not available".
3. Six demonstration tests were failing **before** this work because two 500-object scenario runs (one created while
   testing the scenario API on 2026-11-08, one created at 03:37 on 2026-11-09) had become the *latest* run, so the
   console correctly showed ranks out of 500 and equivalence over 500 records. A new full-snapshot run
   (`run_20261109T041153Z`, nine modules successful, 8.9 s) restores the documented state. Nothing was deleted.

## 5. Performance (both documented definitions, before and after)

| Measurement | Before (release candidate) | After (visual layer) | Target | Met |
|---|---|---|---|---|
| Benchmark sequence: overview page cold | 180 ms | **224 ms** | 400 ms | yes |
| Benchmark sequence: overview page warm | 37 ms | 45 ms | — | — |
| Benchmark sequence: peak RSS | 225 MB | **225 MB** | 250 MB | yes |
| Fresh process: import | 534 ms | 509 ms | — | — |
| Fresh process: total scripted sequence | 2,915 ms | 2,849 ms | — | — |
| Fresh process: peak RSS | 273 MB | **273 MB** | 250 MB | no (unchanged) |
| `GET /api/globe/objects?limit=120` | — | 54 ms, 266 kB | — | — |
| `GET /api/globe/objects?limit=300` | — | 84 ms, 664 kB | — | — |
| `GET /api/globe/object/{norad}` | — | 31 ms, 6.4 kB | — | — |
| `/explorer`, `/decisions` | — | 31 ms, 48 ms | — | — |
| `/intelligence` | — | 117 ms (aggregates over 31,396 rows) | — | — |
| `/evidence` first load | — | 1.5 s, then cached | — | the same one-off twin-archive streaming as `/twin-state` |

The +44 ms on the overview is the KPI aggregates and the run-history timeline. Records:
`outputs/audit/console_benchmark_visual_console_*.json`, `console_cold_profile_visual_console_*.json`.

## 6. Images

Server-side previews rendered from the exact payload the browser receives, with the same land mask, the same vertices
and the same occlusion rule, in an orthographic camera (`scripts/render_globe_preview.py`):

| File | What it shows |
|---|---|
| `outputs/product/screens/globe_preview_scene_20261109T041743Z.png` | 92 schematic orbits over the textured Earth, markers coloured by object class |
| `globe_preview_leo_20261109T041745Z.png` | 47 orbits, low viewing elevation, ISS-like object highlighted |
| `globe_preview_object37607_20261109T041609Z.png` | NORAD 37607 alone: eccentric, near-equatorial orbit with correct occlusion behind the globe |
| `globe_preview_object23806_20261109T041747Z.png` | NORAD 23806 alone |
| `globe_preview_polar_20261109T041610Z.png` | high-elevation view showing the inclination spread |

HTML captures of all 20 screens (real server responses with the stylesheet inlined) are in the same directory and
open without the server running.

## 7. What could not be done, and why

| Item | Reason | Consequence |
|---|---|---|
| **PNG screenshots of the running console, and confirmation that the WebGL canvas renders** | No headless browser and **no JavaScript engine at all** is installed (node, deno, quickjs and the Python bindings are all absent; installing one needs an unauthorised download). Limitation P15 | The 3D canvas has **not** been seen rendering. The geometry it receives is verified by 45 tests and by the server-side previews; the shaders, the camera and the interaction were reviewed by hand and statically checked (strict mode, balanced delimiters, no `innerHTML`, no `eval`, no external origin). **The owner must confirm the globe visually in a browser.** A WebGL-less browser gets a labelled fallback and every value remains reachable |
| Satellite positions, ground tracks, orbit animation in time | The catalogue publishes mean elements only: no node, epoch or anomaly (P5) | Orbits are drawn with archived size, shape and tilt in a declared screen layout; only the camera moves |
| Satellite 3D models | No geometry or attitude data exists for any catalogued object | Markers are points, coloured by object class |
| Power, thermal and ADCS panels | ESA-ADB channels and subsystems are anonymised with no units or physical meaning | The health screen states this and serves the real series, their ground-truth intervals and the benchmark arms instead |
| Conjunction geometry between two named objects | Kelvins CAC events are anonymised and carry no identity | The risk screen shows the probability distribution and the abstention |
| Live anything | No live source is connected and no model runs at request time | Every screen says "archived" and the snapshot date is in the status bar on every page |

## 8. Known limitations of the visual layer

1. The globe's orbit **orientation and marker phase carry no physical meaning**; this is stated on the explorer page,
   the object page, the evidence page, the API payload, the preview images and in `geometry.py`'s docstring.
2. No ground track, sub-satellite point, latitude or longitude is produced anywhere, and a test enforces that.
3. The Earth is held fixed: rotating it under these orbits would imply a ground-track relationship the archive cannot
   support.
4. The scene draws at most 300 orbits (664 kB payload); the catalogue has 31,396 objects, so the globe is always a
   selection, ordered by 30-day re-entry probability unless filtered.
5. Objects whose snapshot row lacks perigee, apogee or inclination are **not drawn**, listed with the reason, and
   never given a default orbit.
6. `/evidence` pays the one-off twin-archive streaming cost (1.5 s) on first load, exactly as `/twin-state` does.
7. The aggregate screens count the catalogue; any run-derived table is labelled with its run id, because a scenario
   run may cover a subset. If the latest run is a subset, object ranks are out of that subset — produce a full run
   (`python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh`) before a demonstration.
8. Responsive layout collapses the three-column explorer at 1400 px and 980 px; it was verified by inspecting the CSS
   breakpoints, not in a browser.

## 9. Exact launch instructions

```bash
cd /data2/anupa/Final_Year_Project
source .venv/bin/activate
python scripts/check_console_prerequisites.py            # exit 0 = launchable
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh   # only if the latest run is a subset
python scripts/serve_console.py                          # http://127.0.0.1:8070/
```

Then open, in this order: `/` (mission picture with the compact globe), `/explorer` (full globe: drag to rotate,
wheel to zoom, click a marker, `r` resets, arrow keys steer), `/objects/37607` (digital twin with its own orbit
panel), `/intelligence`, `/telemetry`, `/risk`, `/debris`, `/decisions`, `/evidence`.

Browsing from a laptop over SSH: forward the port (VS Code **PORTS** panel, add `8070`) or
`ssh -L 8070:127.0.0.1:8070 <user>@<host>`, then open `http://localhost:8070/explorer`. Rebuild the texture only if it
is ever missing: `python scripts/build_globe_texture.py`. Render preview images:
`python scripts/render_globe_preview.py --limit 90 --label scene`.

## 10. Files added and changed

**Added** — `cosmos/product/geometry.py` (248), `cosmos/product/static/js/cosmos-globe.js` (569),
`cosmos/product/static/js/cosmos-explorer.js` (395), `cosmos/product/static/earth-land-mask.png` + provenance
sidecar, templates `explorer.html` (170), `intelligence.html` (166), `decisions.html` (185), `evidence.html` (179),
`tests/test_visual_console.py` (397), `scripts/build_globe_texture.py` (155), `scripts/render_globe_preview.py` (198),
this report.

**Changed** — `cosmos/product/api.py` (two globe endpoints, four page routes, `_globe_rows`, `_intelligence`,
`_decisions`, `_evidence`, `_timeline`, `_mission_bar`, overview and object context), `cosmos/product/store.py` (one
read-only method), `console.css` (palette and new components, all existing selectors kept), `base.html` (app shell,
icons, status bar), `overview.html` (hero added above the existing panels), `object.html` (orbit panel),
`telemetry.html`, `risk.html`, `debris.html` (KPI rows with explicit unavailability),
`scripts/capture_console_screens.py` (six more screens).

Nothing under `data/`, `outputs/twin/`, `outputs/benchmarks/`, `paper/`, `thesis/` or `research_design/` was modified.
The release commits A–D are untouched, no tag exists, and nothing has been pushed.
