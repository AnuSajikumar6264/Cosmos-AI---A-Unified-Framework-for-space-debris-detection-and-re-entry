# COSMOS-AI Mission Intelligence Console — demonstration protocol (P2.6, 2026-11-08; revised for the completion mandate, Phase B)

Repeatable, read-only demonstration on real archived evidence. Every expected output below is asserted
by `tests/test_demo_workflow.py` (D1–D14); run that file before presenting. The console is a **read-only
evidence twin**: no model runs at request time, no live telemetry, tracking or conjunction feed exists,
and nothing shown is a current forecast — the snapshot is dated 2026-10-27.

## 1. Prerequisites, launch and readiness verification

```bash
cd /data2/anupa/Final_Year_Project
python scripts/verify_protected_artifacts.py --label demo      # frozen evidence intact (exit 0)
python -m pytest tests/test_demo_workflow.py -q                 # D1-D14 must pass (14 tests, ~5 s)
python scripts/check_console_prerequisites.py && python scripts/serve_console.py
#                                                               # http://127.0.0.1:8070/  (API docs /docs)
```

Readiness verification (second terminal, or `scripts/diagnose_console.py` offline):

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8070/api/ready      # 200 = ready, 503 = not ready
curl -s http://127.0.0.1:8070/api/ready | python -m json.tool | head -20
```

Expected `200` with `"ready": true` and these checks: `forecast_table_present: true`, `dated_forecast_digest_state:
"verified"`, `git_commit` (40 hex), `complete_run_present: true`, `twin_state_reemitted_present: true`,
`twin_state_source: {selected: "reemitted", status: "primary", policy: "prefer_reemitted"}`, `latest_run`
naming the run below, and `schema_versions.run_manifest: "1.2"`. Readiness describes the console's artifacts
only; it says nothing about any spacecraft. A `503` body names the failing check.

Required: Python ≥ 3.11, fastapi/uvicorn/jinja2/pandas/numpy, `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz`
(sha `b15644aab581cd05…`). Needed for the twin-state step: `outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl`
(sha `6bb4871f7dedfcf1…`, 31,396 records); if absent the console falls back to the archived record and labels it
"HISTORICAL ARCHIVE · twin_state/1.0 (fallback)". Needed for the subgroup cue: `outputs/am_design_stage1/results.json`.
A complete pipeline run must exist. The **validated demonstration run is `outputs/pipeline/run_20261108T121517Z`**
(2026-11-08 12:15 UTC; full snapshot; `run_manifest/1.2`, 23 kB; nine modules including the twin-state root
`twin_state` and its check `twin_equivalence`; records the priority rule; accepted in
`docs/research/COSMOS_AI_P3B_FINAL_ACCEPTANCE_REPORT.md`). Its seven catalogue and benchmark tables are
byte-identical to those of the earlier runs `run_20261108T083402Z` (1.2, seven modules) and `run_20261108T072802Z`
(1.1, historical 5.2 MB manifest), which are kept as records. To create a fresh run — the console then shows it as
latest; no existing run is ever overwritten:

```bash
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh      # ≈ 9 s, new directory
```

## 2. Demonstration objects and why

| Object | Why |
|---|---|
| **NORAD 37607 — ARIANE 5 R/B** (primary) | design-derived A/M (so the X6 under-coverage cue applies), natural decay, p₃₀ = 1.0, re-entry quantiles 10/10/10 d (BEFORE HORIZON), lifetime 6.9/27.5/95.3 d (CROSSES HORIZON), rank 2 of 31,396 (tied at 2.0 with NORAD 32730), mass 5,000 kg ≥ 500 kg |
| NORAD 23806 — TITAN 34B DEB | class-prior fragment; re-entry interval 1.1–202.5 d crosses the horizon; its lifetime record is one of the 123 L17-incoherent ones → lifetime abstention, no substitution |
| NORAD 25544 — ISS (ZARYA) | operator-controlled payload → re-entry abstention with the previous-window base rate; no quantiles; NO INTERVAL |
| NORAD 12 — VANGUARD R/B | re-entry quantiles censored at the 1826.25-day cap (AT CAP); lifetime entirely after the horizon |

## 3. Navigation sequence, APIs and artifacts

| Step | Navigate | API behind it | Artifact read | Expected output |
|---|---|---|---|---|
| 1 Open | `/` | `/api/overview` | forecast table, latest run manifest, X6 record | evidence boundary; "read-only evidence twin"; STALE finding with the snapshot age; module status with evidence class |
| 2 Select | `/objects` → search `37607` | `/api/objects/search?q=37607` | forecast table | one hit, ARIANE 5 R/B |
| 3 Identity & availability | `/objects/37607` top panel | `/api/objects/37607` → `evidence_availability` | forecast table + run manifest | IMPLEMENTED: catalogue, lifetime, re-entry, decision priority, **versioned twin state** ("read by the runtime pipeline as an additional evidence root … 31396 of 31396 compared records equal"; runs that predate the twin modules show ARCHIVED ONLY instead); BENCHMARK ONLY: telemetry, conjunction, debris; UNAVAILABLE: spacecraft health, state vector/impact |
| 4 Source & freshness | "Evidence freshness" panel | `freshness` block | — | snapshot 2026-10-27, orbit epoch 2011-05-23 (RECORDED), archive time MISSING (stated), processing = run start, STALE, consistent, live: no |
| 5 Twin state | "Twin state" panel | `/api/objects/37607/twin` | `as_of_2026-10-27_reemitted_v1/twins.jsonl` + `REEMISSION_MANIFEST.json` | RE-EMITTED · twin_state/1.1; two outputs (physics-history re-entry, lifetime comparison) each with provenance (source sha, code, transformation digest, model none); "value-equivalent to the archived record on 31396 of 31396"; model version UNAVAILABLE |
| 6 Lifetime vs horizon | "Orbital lifetime assessment" | `lifetime.horizon_relation` | — | 6.9–95.3 d, CROSSES HORIZON, "not a probability of survival … the ranking uses p(30 d) alone" |
| 7 Subgroup reliability | same panel | `lifetime.subgroup_coverage` | `am_design_stage1/results.json` | SUBGROUP UNDER-COVERAGE: design-derived; origin 2016, 80 %: 0.5625 (CI 0.512–0.614, n 656) vs 0.80; 2011: 0.7921; descriptive, not individual, not extrapolated |
| 8 Re-entry | "Re-entry assessment" | `reentry` | — | p 1/1/1; quantiles 10 d; BEFORE HORIZON; Monte-Carlo spread, not conformal; variants |
| 9 Decision priority | "Decision priority" panel | `decision_priority` | run `decision_ranking.csv` + manifest `priority_rule` | RANK 2 / 31396; recorded inputs p = 1.0, mass 5,000 kg, high_consequence True; score 2.0; the rule **as recorded in the manifest**; C4 ABSTAIN |
| 10 Provenance & model version | "Snapshot provenance" + report | `provenance`, `/api/reports/object/37607`, `/reports/object/37607` | run manifest lineage | artifact sha `b15644…`, run id `run_20261108T121517Z`, the run's code revision `78ee339` (the commit the run was produced at; the checkout itself may be at a later checkpoint commit), config digest; model version UNAVAILABLE with reason; the download is redacted (no hostname, no absolute path) |
| Edge paths | `/objects/23806`, `/objects/25544`, `/objects/12` | same | same | lifetime ABSTAIN (L17) / re-entry abstention with base rate / AT CAP |
| Health semantics | nav "Telemetry Benchmarks" → `/telemetry` | `/api/telemetry/missions` | prepared anonymised arrays | heading "Anomaly-detection benchmark arms … not spacecraft health"; object page "Spacecraft health — not determinable" |

### 3a. Twin-state evidence root (added by P3-B, 2026-11-08; asserted by `tests/test_p3b_twin_state.py`)

Open **Twin State** (`/twin-state`). Expected: badge `RE-EMITTED · twin_state/1.1 · verified`; selection
`PRIMARY` under policy `prefer_reemitted` with both candidates listed (re-emitted: valid, digest verified,
31,396 records; archived: valid, "no per-output provenance"); integrity `OK` (31,396 valid, 0 malformed, 0
duplicates); equivalence `EQUIVALENT` — 31,396 records compared, 31,396 equal, 0 different, with the
not-compared fields listed by reason (operator-controlled abstention representation, 16,386; no chain time
quantiles for those objects, 16,386; 123 non-coherent lifetime abstentions). Switch to
`?policy=archived_only`: the badge turns amber (`HISTORICAL ARCHIVE · twin_state/1.0 · explicit`) — an archived
read is never shown as a green primary. On an object page the "Twin state" panel now also states the source
selection and the per-object equivalence with the latest run (`EQUAL n of n shared values`). Model version stays
UNAVAILABLE everywhere: nothing was regenerated.

### 3b. Expected API responses (shapes asserted by `tests/test_demo_workflow.py` and `tests/test_phase_b_console.py`)

| Request | Status | Expected content |
|---|---|---|
| `GET /api/ready` | 200 | `ready: true`; checks as in §1; `latest_run: "run_20261108T121517Z"`; `cache` counters |
| `GET /api/overview` | 200 | `schema_version: "api/1.2"`; `latest_run.run_id`; `module_status` with nine `success`; `findings[0].level: "STALE"`; `snapshot_age.as_of: "2026-10-27"` |
| `GET /api/objects/search?q=37607` | 200 | one hit, `name: "ARIANE 5 R/B"` |
| `GET /api/objects/37607` | 200 | `schema_version: "object_record/1.1"`; `decision_priority.rank: 2`; `evidence_availability` ten rows; `provenance.model_version.status: "unavailable"`; `twin_state.source: "reemitted"`, `twin_state.equivalence.status: "equal"` (20 of 20) |
| `GET /api/objects/37607/twin?policy=archived_only` | 200 | `source: "archived"`, `schema_version: "twin_state/1.0"`, `fallback.used: false`, `selection.status: "explicit_archived"` |
| `GET /api/objects/37607/twin?policy=nonsense` | 422 | validation error (JSON) |
| `GET /api/twin-state` | 200 | `overall.status: "primary_verified"`; `equivalence`: 31,396 compared / 31,396 equal / 0 different; `not_comparable_reasons` with 16,386 · 16,386 · 123 |
| `GET /api/objects/999999999` | 404 | `error: "data_unavailable"` (JSON) |
| `GET /no-such-page` (browser) | 404 | HTML error page "NOT FOUND" with navigation; `X-Request-ID` header |
| `GET /api/no-such-route` | 404 | JSON `{"detail": "Not Found"}` |

## 4. Expected limitations to state aloud

Nothing is live; the snapshot is dated 2026-10-27 and its age is computed on every load. No object has telemetry, conjunction or imagery
evidence attributable to it. No model version exists because no fitted model is persisted. The twin state
is re-emitted from the archive, not regenerated. The interval cues and the subgroup figures are display
only; the ranking uses the point probability. Design-derived objects were under-covered at 80 % in the
archived evaluations — a subgroup frequency, not this object's probability.

## 5. Verifying provenance during the demonstration

* Object page → Snapshot provenance: artifact path and SHA-256; compare with
  `sha256sum outputs/twin/as_of_2026-10-27/forecast_table.csv.gz`.
* Twin state panel → source sha, transformation digest, code revision; compare with
  `outputs/twin/as_of_2026-10-27_reemitted_v1/REEMISSION_MANIFEST.json` and `TWINS_SHA256.txt`.
* Run page → "Evidence class and lineage per module" (code / configuration / data artifacts / model);
  compare with `outputs/pipeline/<run>/run_manifest.json`.
* `python scripts/verify_protected_artifacts.py --label demo_end` after the session: unchanged.

## 6. Reproducing

The demonstration is deterministic: the pipeline is byte-deterministic across runs
(`tests/test_pipeline_determinism.py`), the re-emission is byte-deterministic (`tests/test_p1_reemission.py`),
and every expected output above is asserted by `tests/test_demo_workflow.py`. Run the commands of §1 on any
checkout holding the listed artifacts; a checkout without `outputs/pipeline/` runs produces the demonstration run with the
single `run_pipeline.py` command in §1 (about 9 s).
