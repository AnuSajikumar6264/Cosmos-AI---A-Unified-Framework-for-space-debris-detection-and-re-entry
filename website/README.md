# COSMOS-AI website and hosted demonstration

Two independently deployable pieces, both free to host:

| Piece | What it is | Vercel project root | Cost |
|---|---|---|---|
| **Website** | 9 static pages describing the project | `website/` | Hobby, free |
| **Hosted demo** | the existing FastAPI console as a serverless function | repository root | Hobby, free |

Neither needs a database, a paid API or a container host.

---

## 1. Website

### Local run

```bash
python website/build.py --check          # generate the pages, verify assets and links
cd website/public && python -m http.server 8099
# open http://127.0.0.1:8099/index.html
```

`build.py` is the single source of truth: page content, navigation and metadata all live in it, and
it writes plain HTML into `website/public/`. There is **no npm, no bundler and no CDN** — the same
choice the console itself makes, so the site cannot fail on a missing build step. Re-run `build.py`
after any edit.

To embed the live console on the Demonstration page, set the URL before building:

```bash
COSMOS_DEMO_URL=https://your-demo.vercel.app python website/build.py
```

Without it, that page shows an explicit "not published yet" notice plus the eight screen captures.

### Files

```
website/
  build.py                 page content + generator (edit this)
  vercel.json              static config: outputDirectory, cache and security headers
  README.md                this file
  public/                  generated output — the deploy artifact
    *.html                 9 pages
    assets/css/site.css    hand-written stylesheet
    assets/js/site.js      starfield + mobile nav (no dependencies)
    assets/img/shots/      8 console screenshots, from outputs/product/screenshots/
    assets/img/fig/        5 figures, from paper/figures/ and the journal figure set
```

### Deploy to Vercel

```bash
npm i -g vercel && vercel login
cd website && vercel --prod
```

Or through the dashboard: **Add New → Project → import the GitHub repo**, then set

- **Root Directory:** `website`
- **Framework Preset:** Other
- **Build Command:** leave empty (or `python build.py`)
- **Output Directory:** `public`

`website/vercel.json` already sets `outputDirectory`, `cleanUrls`, immutable caching for
`/assets/*` and the security headers.

---

## 2. Hosted demonstration

`api/index.py` imports the existing console unchanged and applies the two adjustments a serverless
platform requires. It is a thin wrapper, not a fork:

1. `POST /api/scenario` returns **501** with an explanation. It spawns `scripts/run_pipeline.py` and
   writes a new run directory, which a read-only serverless filesystem cannot do.
2. A banner is injected into every HTML page saying this is the hosted demonstration, that nothing
   runs at request time, and which screens are unavailable here — so no visitor is misled.

### Why `api/archive/` exists

Two problems made the naive deployment fail, and both are solved by that directory:

- **Git LFS.** `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` is LFS-tracked, and Vercel's
  build clone does **not** smudge LFS, so the file would arrive as a ~130-byte pointer and the
  console would show an empty catalogue. `api/archive/` holds a plain copy with an identical
  SHA-256, and the path is deliberately not rooted at `outputs/` so the `outputs/**/*.gz` rule in
  `.gitattributes` does not match it.
- **`/evidence` crashed.** With only the two artifacts the prerequisite checker calls *required*,
  `/evidence` returns 500 (`UndefinedError: 'dict object' has no attribute 'records_compared'`) and
  `/api/ready` returns 503. Including the twin-state record and one pipeline run fixes both. See
  "Known issue" below.

`api/archive/` is 43 MB:

| Contents | Size | Why |
|---|---|---|
| `forecast_table.csv.gz`, `FORECAST_SHA256.txt` | 1.8 MB | required; the catalogue itself |
| `twins.jsonl` (archived twin state) | 41 MB | `/evidence`, `/twin-state`, readiness |
| one pipeline run | 276 KB | the equivalence comparison on `/evidence` |
| `summary.json`, `c2_clouds.csv`, `top50_reentry_30d.csv`, `KNOWN_ISSUES.md` | 13 KB | overview and object pages |
| `am_design_stage1`, `t1_ranking_utility`, `telemetry_esa_adb/results.csv` | 124 KB | subgroup-coverage and benchmark panels |

Deliberately **not** included: `mission1.npz` (78 MB telemetry arrays) and the SpotGEO frames
(3.3 GB). Those two screens report their built-in "unavailable" state, and `/api/ready` records the
missing re-emitted twin state as a warning rather than pretending it is there.

### Local run

The hosted entry point can be exercised exactly as Vercel will:

```bash
python -c "
from fastapi.testclient import TestClient
import sys; sys.path.insert(0,'.')
from api.index import app
c = TestClient(app)
print(c.get('/').status_code, c.post('/api/scenario', json={}).status_code)"
```

For normal local use, run the real console instead — nothing is disabled there:

```bash
python scripts/check_console_prerequisites.py
python scripts/serve_console.py            # http://127.0.0.1:8070
```

### Deploy to Vercel

```bash
vercel --prod                    # from the repository root
```

Or in the dashboard: **Add New → Project →** same GitHub repo, a **second** project with

- **Root Directory:** `.` (repository root)
- **Framework Preset:** Other
- **Build/Install Command:** leave empty

`vercel.json` rewrites every path to `/api/index`, so all 121 GET routes reach FastAPI.
`api/requirements.txt` pins only the console's eight runtime packages — the repository's main
`requirements.txt` (torch, xgboost, scipy …) is **not** installed, because the console runs no model.
`.vercelignore` keeps `data/`, `outputs/`, `docs/`, `tests/`, `website/` and the virtual environment
out of the upload.

Then rebuild the website with the demo URL so the iframe appears:

```bash
COSMOS_DEMO_URL=https://<your-demo>.vercel.app python website/build.py
cd website && vercel --prod
```

### Environment variables

| Variable | Used by | Required | Value |
|---|---|---|---|
| `COSMOS_DEMO_URL` | `website/build.py`, at build time | no | the deployed demo URL; omitted ⇒ screenshots and a notice |
| `COSMOS_PRODUCT_ROOT` | the console, if the archive moves | no | defaults to `api/archive` when present, else the repo root |

No secrets, tokens or keys are needed by either project.

---

## 3. Architecture

```
                    ┌────────────────────────────────────────────┐
  visitor ─────────►│  website  (Vercel Hobby, static)           │
                    │  9 pages · 3.6 MB assets · no JS framework │
                    └───────────────┬────────────────────────────┘
                                    │ iframe + link (COSMOS_DEMO_URL)
                                    ▼
                    ┌────────────────────────────────────────────┐
                    │  demo  (Vercel Hobby, Python function)     │
                    │  api/index.py → cosmos.product.api         │
                    │  FastAPI · 121 GET routes · Jinja2 · SVG   │
                    │  ~137 MB deps + 43 MB archive              │
                    └───────────────┬────────────────────────────┘
                                    │ reads only
                                    ▼
                    ┌────────────────────────────────────────────┐
                    │  api/archive/  (plain blobs, in-repo)      │
                    │  dated forecast table · twin state · 1 run │
                    │  no model, no database, no network calls   │
                    └────────────────────────────────────────────┘
```

Both projects build from the same GitHub repository and deploy independently: pushing a website
change does not redeploy the demo, and vice versa.

## 4. Sitemap

| Path | Page | Content source |
|---|---|---|
| `/` | Home | overview, capabilities, the three headline findings and the negative result |
| `/problem` | Problem Statement | debris, lifetime uncertainty, censoring, drift, outcome-dependent missingness |
| `/objectives` | Objectives | the five project objectives, each with its status and artifact |
| `/methodology` | Methodology | architecture, data pipeline, drag physics, the ten models, fusion and calibration |
| `/demonstration` | Demonstration | the live console (or captures), with how to read it |
| `/progress` | Project Progress | 16 workstreams with status and evidence; the full benchmark record |
| `/documentation` | Documentation | links to the repository's reports and the five diagrams |
| `/videos` | Demonstration Videos | four labelled placeholders — no recordings exist |
| `/team` | Team | the author, the supervisor, the institution, the authorship statement |

External: the GitHub repository is linked from the navigation, the footer and the Home page.

## 5. Known issue in the console (pre-existing, not introduced here)

`cosmos/product/templates/evidence.html` line 90 renders
`twin.equivalence.records_compared | fmt(0) if twin.equivalence.records_compared is not none`.
When `store.py` sets `equivalence` to its `{"status": "unavailable", ...}` form, that key is absent;
in Jinja a missing key yields `Undefined`, which is *not* `None`, so the filter runs and
`float(Undefined)` raises. The page then returns 500 instead of showing "unavailable".

It does not affect a full local checkout, where the artifacts are present. It is worked around here
by shipping the twin-state record. A one-line fix in the template (`is defined and ... is not none`,
or `| default(none, true)`) would make the page degrade as intended. **Not changed**, since the
console source was outside the scope of this task.
