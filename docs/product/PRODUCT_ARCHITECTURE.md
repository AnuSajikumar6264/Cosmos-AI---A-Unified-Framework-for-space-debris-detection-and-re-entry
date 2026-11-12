# Product architecture — Mission Intelligence Console

Written for: engineers maintaining or extending the console.

## Principle

The console is a **presentation and orchestration layer**. It holds no scientific engine. Every
number it shows is either read from a saved artifact or produced by the existing
`cosmos.ai` code. Where a value does not exist, the console reports its absence rather than
estimating it.

```text
                 ┌──────────────────────────────────────────────┐
 browser ───────▶│  cosmos/product/api.py        FastAPI app    │
                 │    HTML pages (Jinja2) + JSON API            │
                 └───────┬───────────────┬──────────────┬───────┘
                         │               │              │
              ┌──────────▼────┐  ┌───────▼──────┐  ┌────▼─────────┐
              │ store.py      │  │ charts.py    │  │ reports.py   │
              │ read-only     │  │ server-side  │  │ assessment   │
              │ accessors     │  │ SVG          │  │ documents    │
              └──────┬────────┘  └──────────────┘  └────┬─────────┘
                     │                                   │
     ┌───────────────┴───────────────────────────────┐    │
     │ EXISTING SCIENTIFIC CODE (unchanged)          │◀───┘
     │  cosmos/ai/adapters.py    contracts.py        │
     │  cosmos/ai/orchestration.py  provenance.py    │
     │  scripts/run_pipeline.py  check_t1_later_…py  │
     └───────────────┬───────────────────────────────┘
                     │
     ┌───────────────▼───────────────────────────────┐
     │ ARTIFACTS ON DISK (read-only, except new runs)│
     │  outputs/twin/as_of_2026-10-27/  (hashed)     │
     │  outputs/benchmarks/**                        │
     │  outputs/pipeline/run_<ts>/                   │
     │  data/feature1_health/… feature2_debris/…     │
     └───────────────────────────────────────────────┘
```

## Stack, and why

| Layer | Choice | Reason |
|---|---|---|
| HTTP | FastAPI 0.162 | already installed; gives typed validation and free OpenAPI docs at `/docs` |
| Server | uvicorn 0.54 | already installed |
| Templates | Jinja2 3.1 | already installed; server-rendered HTML needs no build step |
| Validation | pydantic 2.14 | already installed; rejects malformed scenario input before execution |
| Charts | **server-side inline SVG** | no plotting library is installed, and no npm/node exists. A chart cannot be drawn without the array behind it, which suits the no-fabrication rule, and the console works fully offline |
| Tests | pytest + `TestClient` (httpx) | already installed |

**Zero new dependencies were added.** There is no build step, no CDN and no network requirement.

## Modules

### `cosmos/product/store.py` — read-only accessors

Single class `ArtifactStore`, constructed with a repository root (so tests can point it at a
synthetic root). Raises two typed errors:

- `DataUnavailable` → HTTP 404 with the reason shown to the user;
- `InvalidSelection` → HTTP 400.

Neither is ever swallowed into a default value. Helper `_finite()` returns `None` for absent or
non-finite numbers so a missing mass can never render as `0`.

Notable behaviours:

- **Two entity types, never joined.** A catalogue object (NORAD) and a telemetry channel
  (anonymised mission + channel) are separate. `object_record()` always returns
  `telemetry.available = False` with the reason.
- **Telemetry decimation.** `channel_series()` takes a strided subsample and reports
  `decimation_stride` and `total_samples`, so a chart is never mistaken for the full series.
  `_mission_samples` is `lru_cache(maxsize=1)` because Mission 1 alone is 448 MB.
- **`interval_quality()`** classifies a time interval as `at_cap`, `degenerate`, `spread` or
  `unavailable`. This exists because 91.7 % of zero-width intervals in the snapshot sit at the
  1826.25-day study cap; displaying those as a precise median would be misleading.
- **Path safety.** `debris_image_path()` resolves and checks the path stays inside the dataset
  directory, and restricts frames to 1–5.

### `cosmos/product/charts.py` — server-side SVG

Each function takes real values and returns a labelled placeholder when they are absent.
Specific anti-misleading choices:

- telemetry gaps are **breaks in the path**, not interpolated segments;
- a missing horizon probability renders as `n/a`, not a zero-height bar;
- `detection_overlay` uses fixed-size rings — this detector reports no confidence, so no
  visual channel may imply one;
- lifetime intervals use a log axis, since lifetimes span decades.

### `cosmos/product/reports.py` — assessment documents

`object_report()` returns a JSON document; `render_html()` renders a self-contained printable
page with no external assets. The document separates three classes and never lets one stand in
for another: `computed_outputs` (from a named run), `historical_outputs` (saved artifacts, with
SHA-256), `unsupported_assessments` (with the reason). It always carries `abstentions`,
`uncertainty`, `limitations` and an `interpretation.not_established` list.

### `cosmos/product/api.py` — routes

Pages: `/`, `/objects`, `/objects/{norad}`, `/telemetry`, `/telemetry/{mission}/{channel}`,
`/debris`, `/debris/{sequence}`, `/risk`, `/runs`, `/runs/{run_id}`, `/compare`, `/scenario`,
`/prospective`, `/reports/object/{norad}`.

API: `/api/health`, `/api/datasets`, `/api/overview`, `/api/objects/search`,
`/api/objects/{norad}`, `/api/telemetry/*`, `/api/debris/*`, `/api/risk/collision`,
`/api/runs`, `/api/runs/{id}`, `/api/runs/{id}/tables/{name}`, `/api/prospective`,
`POST /api/scenario`, `/api/reports/object/{norad}`. Full schema at `/docs`.

## Operating modes

| Mode | Writes? | Behaviour |
|---|---|---|
| **Historical** | no | Loads a saved run. A test asserts the manifest bytes are unchanged after loading. |
| **Scenario** | a new run directory only | Delegates to `scripts.run_pipeline.main()` with an explicit `--out` that is guaranteed not to exist. A console run and a CLI run therefore produce identical artifacts — there is no duplicated writer to drift. |
| **Prospective** | no | Disabled while `check_t1_later_snapshot.assess()` reports BLOCKED. The scoring control is rendered `disabled`, not hidden, and the fixed protocol is shown. |

## Safeguards enforced in code

| Rule | Where |
|---|---|
| No fabricated value | `_finite()` returns `None`; charts show placeholders; templates print `—` |
| No invented identity | `object_record()` hard-codes telemetry/conjunction unavailability with reasons |
| No overwrite of history | `run_pipeline.main()` raises on a non-empty output directory; the API picks a fresh microsecond-stamped directory |
| No run/snapshot mixing | one run rendered at a time; differing module `as_of` dates raise an explicit "Inconsistent snapshots" panel; `/compare` flags non-comparable runs |
| Physical probability ≠ priority | `collision_events()` sets `operational_priority = None`; the risk table column is empty by construction |
| No conformal claim | re-entry uncertainty text states "not a conformal interval" everywhere it appears |
| Input validation | `ScenarioRequest` pydantic bounds; regex on run IDs, mission IDs, channel names and table names |
| Structured errors | `DataUnavailable` / `InvalidSelection` handlers return JSON for `/api/*` and an error page otherwise |

## Extending it

- A new data source: add an accessor to `store.py` that raises `DataUnavailable` when absent,
  then a route and a template panel. Never add a fallback value.
- A new chart: add to `charts.py`, returning `_placeholder()` when the array is empty.
- A new pipeline module: add it to `cosmos/ai/adapters.py` `default_modules()`. The console
  picks it up automatically in the run views and the scenario module list.

Do **not** compute a scientific quantity in `cosmos/product/`. If a number needs deriving, it
belongs in `cosmos/ai/` with tests, where the contracts and provenance apply.
