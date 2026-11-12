# COSMOS-AI — P1 engineering implementation report (2026-11-08)

Scope: the authorised P1 items (P1.1 horizon cue, P1.2 versioned twin-state re-emission, P1.3
schema versioning, P1.4 object-level freshness) plus the P1.5 investigation (proposal only). The
system remains a read-only evidence twin; no model was trained, run or regenerated; no prediction
value, ranking order or threshold changed; no frozen or archived artifact was modified; nothing was
committed. HEAD `78ee339` throughout.

## 1. Baseline and integrity

| Check | Before (07:01 UTC) | After (07:12 UTC) |
|---|---|---|
| Protected artifacts (ESA-ADB freezes, G5d, figure release 107/107, OPS-SAT archive 10/10, twin digests) | all OK — `outputs/audit/protected_artifacts_p1_before_20261108T070115+0000.json` | all OK — `outputs/audit/protected_artifacts_p1_after_20261108T071208+0000.json` |
| Accepted gate record | `83b1150215020e0e…` / `86ae2e8c828e3e18…` | unchanged |
| Archived twin state `outputs/twin/as_of_2026-10-27/twins.jsonl` | sha `19a1fede1fd4871f…` (= `FORECAST_SHA256.txt`) | unchanged (file mtime 2026-11-03) |
| Git | HEAD `78ee339`, 0 staged | HEAD `78ee339`, 0 staged |
| Tests | 371 passed, 3 skipped (after P0) | **386 passed, 3 skipped** in 65 s (`outputs/audit/pytest_full_20261108_p1.log`); `outputs/pipeline/` unchanged (85 run directories) |

## 2. P1.1 — Interval-versus-horizon cue (display only)

`cosmos/product/store.py::horizon_relation(lo, median, hi, p_horizon, horizon_days=30)` classifies a
5–95 % time interval against the 30-day decision horizon as `entirely_before` (95 % quantile <
30 d), `entirely_after` (5 % quantile > 30 d), `crosses` (interval spans 30 d, boundary included),
`censored_at_cap` (all quantiles at the 1826.25-day cap) or `unavailable`, each with a neutral
explanation and a fixed sentence: *the interval is the 5–95 % quantile range of the predicted time;
it is not a probability of survival past the horizon and not a guarantee for this object; the separate
30-day probability is the quantity the ranking uses.* Attached to the object record for both the
re-entry quantiles (`reentry.horizon_relation`, with `p_30d`) and the lifetime quantiles
(`lifetime.horizon_relation`). Rendered on the object page under each interval, in the JSON/HTML
report (`horizon_relation` block), and in a new **ranking view**: `ArtifactStore.ranking_with_horizon`
joins the run's own `decision_ranking.csv` with the same run's `reentry_predictions.csv` at read time
and adds the relation per row — exposed as `GET /api/runs/{id}/ranking?limit=` and as a top-25 table
on the run page. Order, priority scores and probabilities are the run's; the tables on disk are not
touched (tested). `adapters.decision_priority` is unchanged. Example: NORAD 37607 — re-entry 10/10/10 d
→ BEFORE HORIZON (p₃₀ = 1.0); lifetime 6.9/27.5/95.3 d → CROSSES HORIZON.

## 3. P1.2 — Versioned twin-state re-emission

| Item | Value |
|---|---|
| Module / command | `cosmos/ai/twin/reemit.py`; `python -m cosmos.ai.twin.reemit --as-of 2026-10-27` |
| Source | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz`, sha `b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86`, 31,396 rows |
| Output | `outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl` (31,396 records, 78.6 MB), sha `6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84` (`TWINS_SHA256.txt`), `REEMISSION_MANIFEST.json` |
| Mapping | row-wise mirror of the engine's state builder (`engine.run`, lines 326–374): identity, orbit, physical, family, space weather; module outputs `reentry` (physics-history / physics-prior / base-rate abstention) and `reentry-comparison` (lifetime), same labels, values and uncertainty dicts. One CSV round-trip normalisation is recorded in the transformation digest: `family.breakup_parent` NaN → `""` (the engine held empty strings) |
| Provenance per output | `as_of`, `input_sources`, `input_hashes = {forecast_table: b15644…}`, `code_revision = 78ee339…`, `config_digest` = SHA-256 of the canonical transformation spec (method, schema version, horizons, cap, labels, normalisation), `model_digest = null` |
| Per record | `schema_version: "twin_state/1.1"`, `source_record {artifact, sha256, row_index, norad}`, `reemitted_from_archive: true`, `reemission_method` |
| Manifest | `generated_at`, method, transformation digest, code revision, source and archive hashes (before = after), `predictions_regenerated: false`, `model_executed: false`, `model_version: unavailable`, equivalence results |
| Equivalence | `compare_with_archive`: **31,396 of 31,396 records equal** by value (provenance and the four marker fields excluded; canonical JSON comparison so NaN tokens compare equal); 0 differing; no extra records on either side |
| Determinism | two independent runs produced byte-identical files (`6bb4871f…`); records carry no timestamps |
| Safeguards | refuses to write into the archived directory (tested); archive sha before and after recorded in the manifest |

Not claimed: no prediction was regenerated; the only new information is lineage. The archived state
remains the artifact of record for every published number.

## 4. P1.3 — Schema versioning

`cosmos/ai/schema.py` + `docs/architecture/SCHEMA_VERSIONING.md`. Families and current versions:
`forecast_table/1.0` (column set, shared with `adapters._load_snapshot`), `twin_state/1.1`
(1.0 = archive), `run_manifest/1.1` (1.0 = pre-lineage manifests), `object_record/1.1`, `report/1.1`
(was bare `"1.0"`), `api/1.1`, `freshness/1.0`. Rules: MAJOR breaks, MINOR adds; records without a
version are read as 1.0; archives are never rewritten (newer versions are produced by re-emission into
separate directories); validators (`validate_twin_record`, `validate_run_manifest`,
`validate_forecast_columns`) name the offending field and raise `SchemaError`; the console turns a
malformed or non-JSON run manifest into `DataUnavailable` with the reason (tested) instead of a server
error. New run manifests are stamped; API responses carry `schema_version` / `view_schema_version`;
every re-emitted record was validated as 1.1 on write; the archived record validates as 1.0.

## 5. P1.4 — Evidence freshness

`store.freshness(as_of, orbit_epoch, processing_started_at, artifact_sha256, today=None)` keeps three
times apart: **source observation** (catalogue snapshot date 2026-10-27 — the SATCAT data date — and
the object's GCAT canonical orbit epoch with its age at the snapshot, status recorded/missing/
unparseable), **archive** (the forecast artifact records no generation timestamp → status `missing`,
stated; identity by SHA-256), **processing** (latest run `started_at`, recorded/missing). Staleness is
judged only by the one defensible rule — a dated snapshot is current only on its own date (threshold
0 days) — and the orbit-epoch age is reported, not judged. Inconsistencies are listed (orbit epoch
after the snapshot; run started before the snapshot; snapshot dated after the evaluation day). File
modification times are never used; `live: false` always. Exposed in `/api/objects/{norad}.freshness`,
on the object page ("Evidence freshness" table), in reports (`freshness` block + HTML section) and
per run (`/api/runs/{id}.freshness`). Tests cover stale (age 12 d), current (same day), missing (no
epoch), inconsistent (future epoch; run before snapshot; evaluation day before snapshot).

## 6. P1.5 — Model persistence

Investigation delivered as `docs/research/COSMOS_AI_P1_5_MODEL_PERSISTENCE_PROPOSAL.md`: what can be
persisted (xgboost JSON, torch state_dicts, physics pools, gate, CQR tables, isotonic breakpoints,
AR(8) weights; not the absent `tabm`/`kumo`/`tabicl`), storage layout (`outputs/models/<study>/<run_id>/`
with `MODEL_MANIFEST.json`), digest definition (SHA-256 over file digests + canonical params), the
four-version association rule, safe loading (no pickle; `weights_only=True`; digest and backend-major
checks), an explicit opt-in inference mode for the adapters, required tests and storage costs. Nothing
of it was implemented.

## 7. Tests

| File | Tests | Covers |
|---|---|---|
| `tests/test_p1_horizon_cue.py` | 4 | classification incl. boundary and cap; unchanged values; ranking view preserves order/values; console, API and report rendering |
| `tests/test_p1_reemission.py` | 4 | archive untouched and hashes distinct; every record v1.1 with provenance and source pointer; value equivalence and determinism on a slice; refusal to write into the archive |
| `tests/test_p1_schema.py` | 5 | stamps and policy doc; legacy 1.0 acceptance; named rejections; shared column set; malformed manifests reported; API/manifest stamps |
| `tests/test_p1_freshness.py` | 2 | stale / current / missing / inconsistent; API, page, report and run exposure |

Full suite **386 passed, 3 skipped**.

## 8. Changed-file inventory

| File | Change |
|---|---|
| `cosmos/ai/schema.py` | new — versions, validators, shared forecast column set |
| `cosmos/ai/twin/reemit.py` | new — versioned re-emission, equivalence check, manifest |
| `cosmos/ai/adapters.py` | `_load_snapshot` reads the required column set from `schema` (behaviour and message unchanged) |
| `cosmos/product/store.py` | `horizon_relation`, `freshness`, `ranking_with_horizon`, manifest validation in `run_manifest`, schema stamp and freshness in `object_record` |
| `cosmos/product/api.py` | `/api/runs/{id}/ranking`; lineage/freshness/view stamp in `/api/runs/{id}`; stamps on overview and datasets; ranking on the run page |
| `cosmos/product/reports.py` | `horizon_relation` and `freshness` blocks; schema 1.1; HTML sections |
| `cosmos/product/templates/object.html`, `run.html`, `static/console.css` | cues, freshness table, ranking table, badge style |
| `scripts/run_pipeline.py` | manifest `schema_version` |
| `docs/architecture/SCHEMA_VERSIONING.md`, `docs/research/COSMOS_AI_P1_5_MODEL_PERSISTENCE_PROPOSAL.md` | new |
| `outputs/twin/as_of_2026-10-27_reemitted_v1/` | new artifact (3 files) |
| `tests/test_p1_*.py` | new (15 tests) |

Not changed: `decision_priority`, any model output, any archive, any frozen file, the JINT manuscript.

## 9. Remaining limitations and recommended next steps

* Model version is still "unavailable" everywhere — truthfully; P1.5 describes the path, which needs
  absent backends for the selected learners.
* The re-emitted state is not read by the runtime adapters (they read the forecast table); wiring a
  `twin_state` reader is a P2 choice, not a necessity.
* The archive's generation time is unrecoverable (no timestamp was recorded); future study runs should
  write one into their summaries.
* Freshness has one defensible threshold (snapshot date); no element-epoch threshold exists.
* The ranking cue uses the re-entry quantiles of the same run; it cannot be computed for runs that
  wrote no `reentry_predictions.csv` (shown as "no interval").
* Recommended next: P2 decisions listed in the architecture audit (remaining 3b cells, am_design
  Stage 2 substitute, later SATCAT snapshot for prospective evaluation, vision cache rebuild, backend
  installation under a recorded environment).
