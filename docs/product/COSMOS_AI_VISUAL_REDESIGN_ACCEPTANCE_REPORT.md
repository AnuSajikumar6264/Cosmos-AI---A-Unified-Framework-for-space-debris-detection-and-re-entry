# COSMOS-AI — Visual redesign: acceptance report (2026-11-09, second pass)

Written for: the project owner. Everything below was measured in a **real browser** driving the
**running console**, not inferred from code. HEAD is `727ecec95fbb8ec3ac47b23df569dc5c376318f4`
(release commit D). Nothing is committed, tagged or pushed; no archived scientific output was
modified; the protected-artifact verifier reports `all_protected_ok: True` and the manuscript claim
audit is unchanged at 0 FAIL.

Evidence files: `outputs/product/screenshots/` (36 PNG at 1440 × 900 plus full-page variants, and
`report.json` with per-screen browser measurements) and
`outputs/audit/console_interactions_accept_20261109T054133Z.json` (27 interaction checks).

## 1. Root causes of the previous failure

The first pass passed every content test while being, in a browser, exactly what you described. I
had no browser and no JavaScript engine, so I shipped a layout I could not see. Measured causes:

| # | Root cause | Measurement that proved it | Fix |
|---|---|---|---|
| 1 | **The globe was a card, not the subject.** It sat in a normal document flow below a paragraph, 797 × 358 px, starting at y = 417 | 22 % of a 1440 × 900 viewport, **4.7 % of the page area**; the page was 5,044 px tall | A viewport-sized CSS grid (`.dash`) with the globe as the dominant cell: now **852 × 481 px = 50 % of the dashboard area**, page 961 px |
| 2 | **A five-line text wall owned the top of the screen.** The "Evidence boundary" scope note was always expanded | 10,092 characters of body text on the overview | The prose is now a one-line `<details class="scope">` disclosure. Text on the overview: **3,270 characters**. Nothing was deleted; it is one click away, and the content tests still pass |
| 3 | **Heavy evidence tables pushed everything below the fold** (readiness, findings, module status, abstentions, datasets) | page height 5,044 px | They moved into a collapsed "Full evidence tables" disclosure. The whole dashboard now fits one 900 px viewport |
| 4 | **The explorer's three-column grid squeezed the globe** to 530 × 628 | 26 % of the viewport | Two columns: a 286 px aside (filters, object list, selected object) and the globe filling the rest — **851 × 662 px = 69 % of the dashboard area** |
| 5 | **The digital twin page opened with a status table and a vocabulary paragraph**; the 3D view and charts were below the fold | hero at y ≈ 1,100 | The orbit view, both probability charts and both interval plots are now the **first** block; the vocabulary is a disclosure |
| 6 | **Analysis pages had no charts at all.** `/intelligence`, `/telemetry`, `/debris`, `/decisions` rendered CSS meters and tables only | browser counted `svg.chart` = 0 on all four | A new `charts.category_bars()` helper (vertical and horizontal, missing values drawn as `n/a`) now draws **11 new charts** across those pages, all from archived numbers |
| 7 | **A real bug widened `/evidence` to 2,314 px** and caused horizontal scrolling: `twin.integrity` is a record, not the string `"ok"`, and a whole dict was being rendered inside a `white-space: nowrap` status badge. The twin source was also read from a non-existent key (`selected` instead of `selected_source`), so it displayed blank | `document.scrollWidth` 2,681 vs `clientWidth` 1,440 | Correct field names, record rendered as chips, `overflow-wrap` on table cells. **No horizontal overflow on any screen now** |
| 8 | **A latent WebGL-1 bug would have rendered the Earth black on real hardware**: the 1440 × 720 texture is not a power of two, so `generateMipmap` and `REPEAT` wrapping are invalid | found by hand review, then confirmed by the headless-browser probe | The texture is built at 2048 × 1024 and the renderer guards the non-power-of-two case |
| 9 | **The debris index buried its images** behind a 48-row table | — | A real SpotGEO frame with the real detection rings is now the first panel |

Not a cause: the globe itself. It was rendering all along — the browser reports 83–193 frames drawn
per page load — but it was too small and too far down the page to read as the subject of the screen.

## 2. How I can now see the UI (the tooling gap, closed)

No browser, screenshot tool or JavaScript engine exists in this environment (`node`, `deno`,
`quickjs`, `playwright`, `selenium`, `wkhtmltoimage` all absent). I installed Playwright and
headless Chromium into a **throwaway environment**, so the project's own `.venv` is untouched and
Chromium is not a project dependency:

```bash
python3.12 -m venv /tmp/cosmos_shot_venv
/tmp/cosmos_shot_venv/bin/python -m pip install playwright
PLAYWRIGHT_BROWSERS_PATH=/tmp/cosmos_pw_browsers /tmp/cosmos_shot_venv/bin/python -m playwright install chromium
```

Headless Chromium renders WebGL through SwiftShader (`ANGLE (Google, Vulkan 1.3.0 (SwiftShader
Device (Subzero)), SwiftShader driver)`), so the globe in these captures is drawn by the same code
path a desktop browser uses, on the CPU. Two new scripts use it:

| Script | What it does |
|---|---|
| `scripts/capture_console_screenshots.py` | opens every screen at 1440 × 900, captures PNG (viewport and full page), and records console messages, uncaught errors, failed requests, element geometry, text volume, chart counts, horizontal overflow and the renderer's own diagnostics |
| `scripts/verify_console_interactions.py` | drives drag, wheel, reset, pause, list click, marker click, the four demonstration objects, navigation, and a WebGL-disabled run, asserting the state the renderer reports |

## 3. Files changed in this pass

**Modified** — `cosmos/product/api.py` (chart wiring for five routes, `_p30_bands`, page titles, the
debris featured frame), `cosmos/product/charts.py` (+`category_bars`), `cosmos/product/store.py`
(unchanged in this pass apart from the earlier read-only method), `console.css` (dashboard grid,
full-height stage, disclosures, chart frames, badge/table overflow guards, hero sizing),
`templates/base.html`, `overview.html` (rebuilt as a dashboard), `object.html` (visual-first hero),
`explorer.html` (two columns), `telemetry.html`, `risk.html`, `debris.html`, `intelligence.html`,
`decisions.html`, `evidence.html`, `cosmos/product/static/js/cosmos-globe.js` (preserveDrawingBuffer,
richer `info()`, power-of-two guard), `cosmos-explorer.js` (diagnostics hook, single-object scene),
`scripts/build_globe_texture.py` (power-of-two output), `tests/test_visual_console.py` (+17 tests).

**Added** — `scripts/capture_console_screenshots.py`, `scripts/verify_console_interactions.py`,
this report, 36 screenshots and `report.json`, two interaction records under `outputs/audit/`.

## 4. Components and libraries

| Component | Implementation | Library |
|---|---|---|
| 3D Earth globe, atmosphere, orbits, markers, picking, camera | `cosmos/product/static/js/cosmos-globe.js` (~580 lines) | **none** — hand-written WebGL 1. Three.js is deliberately not used: it would have to be downloaded and vendored, and the console must keep working offline |
| Dashboard wiring, selection, panels, filters, tooltip | `cosmos-explorer.js` (~410 lines), text nodes only (no `innerHTML`) | none |
| Orbit geometry | `cosmos/product/geometry.py`, unit-tested against closed-form two-body results | none |
| Earth texture | `scripts/build_globe_texture.py` → 2048 × 1024 PNG, 44 kB, from the archived GHS-POP/Natural Earth land mask already in the repository, with an eight-point orientation guard | pillow (already a dependency) |
| All 2D charts | server-rendered inline SVG in `cosmos/product/charts.py` | none |
| Screenshot and interaction verification | `scripts/capture_console_screenshots.py`, `verify_console_interactions.py` | Playwright + Chromium, in a throwaway venv, **development-time only** |

## 5. Screenshots (captured from the running application at 1440 × 900)

All in `outputs/product/screenshots/`; each also has a `_full.png` full-page variant.

| File | Screen | What is visible |
|---|---|---|
| `01_mission_overview.png` | Mission Overview | top bar with snapshot and status, six KPI tiles, globe at 50 % of the dashboard area, selected-object panel, three bottom tiles (re-entry spread, collision probability, mission activity) |
| `02_earth_explorer.png` | Earth & Orbit Explorer | globe 851 × 662 with 122 orbits, filters and object list, selected-object panel, renderer identified |
| `03_twin_37607.png` … `06_twin_12.png` | Satellite Digital Twin ×4 | orbit view beside re-entry and lifetime horizon bars and interval plots, derived geometry table, "how to read the orbit" |
| `07_orbital_intelligence.png` | Lifetime & Re-entry | six KPIs and three distribution charts (probability, lifetime, inclination) plus the priority queue chart |
| `08_health_monitoring.png` | Health & Telemetry | alarm-layer benchmark bars, ground-truth intervals per mission, and the explicit statement that power/thermal/ADCS views are not available |
| `09_telemetry_channel.png` | Telemetry channel | real series with ground-truth intervals shaded |
| `10_conjunction_analysis.png` | Conjunction & Collision | log-probability distribution with the high-risk threshold marked, event table |
| `11_debris_monitoring.png` | Debris Detection | **real SpotGEO frame with the real detection rings**, detector comparison chart |
| `12_debris_detections.png` | Debris frame detail | full-frame overlay |
| `13_decision_intelligence.png` | Decision Intelligence | recorded rule, C4 abstention, queue chart, precision-at-k chart |
| `14_evidence_validation.png` | Evidence & Provenance | readiness checks, digests, module lineage, twin integrity |
| `15`–`18` | Twin State, Guided Demo, Run Explorer, Scenario | unchanged screens in the new shell |

## 6. Tests executed

| Check | Command | Result |
|---|---|---|
| Full suite | `python -m pytest tests/ -q -rs` | **570 passed, 3 skipped, 0 failed** in 137 s (`outputs/audit/pytest_visual_redesign_accept.log`). Before this pass: 553 |
| New layout regression tests | `pytest tests/test_visual_console.py` | **62 passed** (geometry, payload contracts, texture orientation, JS static checks, and 17 new layout assertions: dashboard grid, tiles, collapsed prose, chart counts per screen, debris overlay before the table, visual-first object page, titles, no record in a badge) |
| Browser capture of every screen | `capture_console_screenshots.py` | 18 screens, **0 with problems**, 0 console errors, 0 page errors, 0 failed requests |
| Browser interaction verification | `verify_console_interactions.py` | **27 of 27 passed** |
| Protected artifacts | `verify_protected_artifacts.py --label visual_redesign` | `all_protected_ok: True` |
| Manuscript claims | `audit_manuscript_claims.py` | 147 checks, 0 FAIL (unchanged) |

## 7. Visual acceptance criteria

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Main dashboard loads without frontend errors | **PASS** | 0 console errors, 0 page errors, 0 failed requests on all 18 screens |
| 2 | Earth globe is visibly rendered | **PASS** | 117–193 frames drawn per load; `readPixels` reports lit fraction 1.0 with 340 distinct colours; visible in `01` and `02` |
| 3 | Globe is genuinely interactive | **PASS** | drag changed azimuth −0.958 → −2.084 and elevation 0.420 → 0.720; wheel changed distance 3.400 → 1.655; reset restored 3.400; camera orbit pauses |
| 4 | Satellite selection works | **PASS** | list click selected 25544 and loaded its record; **marker click on the canvas** selected 23806; dashboard selection updated the right panel |
| 5 | At least one meaningful orbital/schematic visualisation | **PASS** | 122 orbit ellipses, 15,616 orbit vertices, 122 markers, labelled schematic |
| 6 | Lifetime chart renders actual project data | **PASS** | horizon bars 0.780 / 0.929 / 0.988 for 37607 and the catalogue-wide lifetime distribution (23 / 55 / 163 / 6,555 / 6,442) |
| 7 | Re-entry visualisation renders actual project data | **PASS** | p(30/90/1yr) = 1.000 for 37607, interval plot, and the catalogue distribution (17,496 / 13,848 / 15 / 15 / 4 / 18) |
| 8 | Telemetry and debris pages show available evidence | **PASS** | 224 channels, 3.32 M samples, 17,342 ground-truth intervals, benchmark F0.5 bars; real SpotGEO frame with 6 detection rings, detector F1 comparison |
| 9 | Conjunction page displays available benchmark information | **PASS** | 2,167 held-out events, distribution with the 1e-6 threshold, 5 above it, C4 abstention |
| 10 | Navigation works across every screen | **PASS** | every sidebar link navigated; all 18 routes returned 200 |
| 11 | Four demonstration objects load correctly | **PASS** | 37607, 23806, 25544, 12 all select and show archived fields; unavailable fields read "not available" (1, 1, 5, 1 occurrences respectively) |
| 12 | No fabricated scientific values | **PASS** | no endpoint returns a position, velocity, sub-satellite point or ground track (enforced by test); the schematic orientation is labelled on screen, in the payload and in the images |
| 13 | Layout works at a normal desktop resolution | **PASS** | 1440 × 900: dashboard 961 px tall, no horizontal overflow on any screen |
| 14 | No blank chart containers or invisible canvases | **PASS** | every `#globe-canvas` measured non-zero and drawing; every chart container contains an SVG or an explicit "not available" state |

## 8. Remaining limitations

1. **GPU rendering is still unverified.** The captures use SwiftShader (CPU). The code path is the
   same, but frame rate on your GPU is not measured here. Open `/explorer` and confirm.
2. **No satellite 3D models.** Markers are points coloured by object class: no geometry or attitude
   data exists for any catalogued object.
3. **No ground tracks, no positions at a time, no orbit animation in time.** The catalogue publishes
   mean elements only; the orbit orientation about the pole and each marker's phase are a declared
   screen layout. The Earth is held fixed on purpose.
4. **No power, thermal or ADCS panels.** ESA-ADB channels are anonymised (`channel_1`,
   `subsystem_1`) with no units or physical meaning; inventing that mapping is the one thing the
   screen must not do, so it states the absence instead.
5. **Conjunction geometry between two named objects is impossible** — Kelvins CAC events are
   anonymised.
6. **Learned debris detectors' detections are not drawn** (only their scores are archived); the
   frames show the served classical front end's detections.
7. **The object detail pages are still long** (about 5,900 px). That is deliberate: the visual hero
   leads, and the technical evidence follows on a detail page.
8. `/evidence` pays the one-off twin-archive streaming cost (≈ 1.5 s) on first load, like
   `/twin-state`.
9. **Playwright and Chromium live in `/tmp`,** not in the project. Re-create them with the three
   commands in §2 if the machine is reset; they are needed only to re-capture screenshots.

## 9. How to see it

```bash
cd /data2/anupa/Final_Year_Project
source .venv/bin/activate
python scripts/check_console_prerequisites.py && python scripts/serve_console.py
```

Open `http://127.0.0.1:8070/` (dashboard) and `http://127.0.0.1:8070/explorer` (full globe). Over
SSH, forward port 8070 (VS Code **PORTS** panel, or `ssh -L 8070:127.0.0.1:8070 <user>@<host>`).
To re-capture the evidence in this report:

```bash
PLAYWRIGHT_BROWSERS_PATH=/tmp/cosmos_pw_browsers /tmp/cosmos_shot_venv/bin/python \
    scripts/capture_console_screenshots.py --out outputs/product/screenshots --full-page
PLAYWRIGHT_BROWSERS_PATH=/tmp/cosmos_pw_browsers /tmp/cosmos_shot_venv/bin/python \
    scripts/verify_console_interactions.py --out outputs/audit --label check
```
