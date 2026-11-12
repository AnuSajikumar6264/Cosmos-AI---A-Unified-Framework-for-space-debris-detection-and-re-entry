# COSMOS-AI — Post-P2 review and P3 engineering roadmap

Date 2026-11-08 · HEAD `78ee339` · **planning only: no application code was changed.** Every number below
was measured on this checkout today or read from an artifact; benchmarks on enlarged collections used
synthetic replications in a temporary directory that was deleted afterwards and are labelled as such.

---

## 1. Stage 1 — revalidation of the P2 system

| Check | Result |
|---|---|
| Git | HEAD `78ee339`; 0 staged; 18 modified tracked / 246 untracked entries, all uncommitted by instruction |
| Full suite | **400 passed, 3 skipped** in 86 s (`outputs/audit/pytest_full_20261108_p3_plan.log`) |
| Protected artifacts | all OK (`outputs/audit/protected_artifacts_p3_plan_20261108T075403+0000.json`): ESA-ADB freezes 28/28 and 27/28-expected, G5d, figure release 107/107, OPS-SAT 10/10, twin digests, gate record `83b115…`/`86ae2e…` |
| Twin state | archived `19a1fede1fd4871f…` 31,396 records 40.9 MB; re-emitted `6bb4871f7dedfcf1…` 31,396 records 78.6 MB; both equal their digest files |
| D1–D14 | 14 passed (11.9 s) |
| Protocol commands | `check_console_prerequisites.py` → launchable; `run_pipeline.py --list` → 7 modules |
| Runtime behaviour | orchestrator graph unchanged (`catalogue_state → lifetime/reentry → decision_priority`; collision, health, debris independent roots); all probed routes 200 |

**Discrepancies between the P2 report and the implementation**

1. **Manifest inflation (P2.2 side effect).** `run_pipeline._jsonable` now keeps *every* dict of scalars
   verbatim, so the demonstration run's manifest holds 31,396 names, regimes and classes and 18,281
   abstention reasons: `run_20261108T072802Z/run_manifest.json` = **5,226,140 bytes** vs 8,946 bytes for
   the 2026-11-06 run. `GET /api/runs/{id}` returns 3.8 MB and the run page 5.1 MB; `list_runs()` parses
   this file on every overview/object request. The P2 report described the rule change but not this
   consequence. Correctness is unaffected (tests pass; the priority rule is recorded as intended). Fix is
   P3-A.1. The existing manifest is a historical record and is not rewritten; a fresh run after the fix
   will be small again.
2. Nothing else: API contracts, UI behaviour, fallback labelling and acceptance results match the report.

## 2. Measured bottlenecks (real archive, TestClient, warm process)

| Operation | Latency | Payload / memory | Cause |
|---|---|---|---|
| `/` overview **page** | **3,089 ms**, RSS 203 → 622 MB | 18.8 kB | `store.missions()` loads the prepared telemetry arrays (`mission{1,2,3}.npz`, up to 448 MB) just to list missions: **2,453 ms, +440 MB** |
| `/api/overview` | 330–460 ms | 5.9 kB | `prospective_status()` 180–190 ms per call (scans snapshot CSVs); `repository_provenance()` 54–61 ms (re-hashes the 40 MB `twins.jsonl` and spawns `git` each call); `list_runs()` 38–44 ms (parses 86 manifests, one of them 5.2 MB) |
| `/api/objects/{norad}` | 140–210 ms | 15.9 kB | `latest_run_id()` → `list_runs()` each call; `run_manifest()` parsed twice (priority + availability); `object_record` 7 ms when no runs exist |
| `/api/objects/{norad}/twin` | 16 ms (index build 79 ms once) | 3.7–4.8 kB | offset index: 31,396 entries ≈ 4 MB; seek + parse 8 ms |
| `/api/runs/{id}` · run page | 60 ms · 203 ms | **3.8 MB · 5.1 MB** | manifest inflation (above) |
| `/api/runs/{id}/ranking?limit=1000` | 62 ms | 935 kB | fine; limit capped at 1,000 |
| `/api/runs/{id}/tables/…?limit=20000` | 85 ms | 4.9 MB | no pagination beyond `limit` |
| `catalogue()` | 69–80 ms | 14.7 MB DataFrame | one gz CSV read, cached |
| `/reports/object/{norad}` | 350–380 ms | 22–24 kB | object_record + run tables + git |

**Scalability (synthetic ×3 / ×10 replications of the forecast table, temporary root, deleted):**
catalogue load 69 → 191 → 651 ms; DataFrame 14.7 → 44 → 147 MB; search 8 → 13 → 46 ms; object record
7 → 14 → 39 ms; overview aggregate 2 → 4 → 10 ms. Linear in rows; a 300k-object catalogue stays
interactive if the table stays in memory (≈150 MB). The twin offset index is a single sequential scan
(79 ms per 31k records; **extrapolated** ≈ 0.25 s / 0.8 s at ×3 / ×10 — not measured, the replication
script failed on a parsing detail and was not retried).

## 3. Stage 2 — P3.1 runtime architecture

### A. Orchestrator ⇄ versioned twin state

**Contracts today.** `ModuleContext(inputs, outputs, config, config_sha256)`; a module returns
`ModuleResult(outputs, provenance)`; `catalogue_state`, `lifetime_estimates`, `reentry_predictions` each
re-read `forecast_table.csv.gz` (`_load_snapshot`, required-column check) and build contract objects per
NORAD. The console's `twin_record()` reads the re-emitted `twin_state/1.1` file through an offset index
and labels any fallback to the archived 1.0 file.

**Should the orchestrator consume `twin_state/1.1` directly?** Assessment:

| Aspect | Finding |
|---|---|
| Data contract | the record carries exactly what the three catalogue-chain adapters derive from the table (identity, orbit, physical, family, space weather, two outputs with 80/90 % intervals), **plus** per-output provenance — but *not* the lifetime 80 % bounds nor `p_lifetime_raw_*`, and not the operator-controlled base-rate quantiles (none exist). A `twin_state` module could therefore replace `catalogue_state` + `reentry` but not `lifetime` without widening the record (schema 1.2) |
| Adapter architecture | fits as a **new root module** `twin_state` (`ModuleSpec("twin_state", twin_state_records)`) whose outputs are the records; `lifetime`/`reentry` could optionally `depends_on=("twin_state",)` and read from it — a design choice, not a scientific one |
| Reader performance | index build 79 ms + 8 ms per record; a full-snapshot run would stream the 78.6 MB file once (≈ 1 s) — comparable to the current 7 s run |
| Provenance | per-output provenance would flow into `ModuleResult.provenance` (`input_hashes = {twins.jsonl: 6bb4871f…, forecast_table: b15644…}`), and `lineage.data_artifacts` would list both; model version stays unavailable |
| Fallback | the archived 1.0 file must be treated as **a different artifact**: `source: archived`, `provenance_on_outputs: false`; the orchestrator must record which one it read, never substitute silently |
| Consistency | the console and the orchestrator must share one reader (`cosmos/ai/twin/reader.py`, moved out of `store.py`) so that a value shown on the object page and a value in a run table come from the same code path |
| Backward compatibility | old runs (no `twin_state` module) stay valid (`run_manifest/1.0–1.1`); new runs stamp `run_manifest/1.2` with the module |
| Failure behaviour | missing both files → module `failed` with `ArtifactUnavailable`, dependants `blocked`; a record failing `validate_twin_record` → that object abstained with the validation message, never repaired |

**Recommendation:** implement as an *additional* root module that validates equivalence at run time
(`twin_state` values vs `catalogue_state`/`reentry` values for every object → recorded in the manifest) rather
than replacing the table readers — this makes every run a live equivalence check of the re-emission and
keeps the published chain untouched. Classified **P3-B.1** (optional; the demonstration does not need it).

### B. Run comparison

Today `/compare` is status-level only. Design (`cosmos/product/compare.py`, read-only):

| Dimension | Join key | Comparable when | Change types reported |
|---|---|---|---|
| Decision priority | `object_id` across `decision_ranking.csv` | both runs wrote the table and `as_of` equal | `priority_score` delta, rank delta, `high_consequence` flip; **missing** (object in one run only, e.g. `--limit`); |
| Re-entry outputs | `object_id` across `reentry_predictions.csv` | as above | p₃₀/p₉₀/p₁yr deltas, quantile deltas, `uncertainty_kind` change |
| Lifetime intervals | `object_id` across `lifetime_estimates.csv` | as above | quantile deltas, abstention appearing/disappearing (`lifetime_noncoherent_horizons.csv`) |
| Twin state | `object_id` across the twin files named in each run's lineage | both runs record a twin artifact | per-field diff of the record; **incomparable** when the two runs read different twin versions (1.0 vs 1.1) |
| Evidence availability | capability list | always | status transitions (implemented → blocked, …) |
| Provenance / sources | `lineage.data_artifacts` | always | same vs different artifact SHA-256; code revision; config digest; model version (both unavailable today) |

Rules: (1) identical `as_of` and identical data-artifact digests ⇒ differences are **implementation/
configuration** differences, never "model improvements"; (2) different `as_of` ⇒ runs are *not
comparable* for values (already flagged); (3) a record present in one run only is **missing**, not
"changed"; (4) numeric deltas are reported with the recorded values, no significance claim; (5) the
comparison carries both runs' lineage blocks. API `GET /api/compare?a=…&b=…&limit=…` and a table on
`/compare`. **P3-B.2.**

### C. Pagination and indexing

| Change | Acceptance criterion (measurable) |
|---|---|
| Cursor pagination on `/api/objects/search` and `/api/runs/{id}/tables/{name}` (`offset`, `limit ≤ 1000`, `total`, `next`) | any page ≤ 1,000 rows served in < 100 ms at ×10 scale; payload ≤ 1 MB |
| `list_runs()` summary cache keyed by (path, mtime, size) | overview/object requests stop re-parsing 86 manifests: `list_runs` < 5 ms warm |
| `run_manifest()` cache keyed by (path, mtime) + fix of the manifest inflation (P3-A.1) | `/api/runs/{id}` < 50 kB for a full run; object page < 60 ms warm |
| `missions()` metadata from a sidecar index (`prepared/INDEX.json`, written once) instead of loading arrays | overview page < 400 ms; RSS stays < 250 MB without a telemetry chart open |
| `repository_provenance()` digest cache keyed by (path, mtime, size) | < 5 ms warm; the digest is still verified on first load |
| `prospective_status()` cached per process with explicit invalidation when `snapshots/` changes | < 5 ms warm |
| Catalogue index: `norad → row` dict built with the DataFrame | object lookup O(1) (today a boolean mask over 31k rows, 7 ms) |
All are **display/serving** changes; no value changes. **P3-A.2–A.4.**

### D. Later-snapshot ingestion (design only; no download authorised)

Today: `cosmos/ai/data/download.py::fetch_celestrak(date)` writes `data/feature2_debris/celestrak/snapshots/<date>/`
with `retrieved_utc` and digests in `MANIFEST.json`; two snapshots exist (2026-10-24, 2026-10-27);
`scripts/check_t1_later_snapshot.py` lists them and reports readiness (needs data date ≥ 2026-11-26).

Design `scripts/ingest_snapshot.py`:
1. **Never replace**: refuse if `snapshots/<data_date>/` exists; write to it only when complete; a
   `SNAPSHOT_MANIFEST.json` per snapshot with `source_url`, `retrieved_utc` (ingestion time),
   `data_date` (observation/publication date read from the file header, not from the clock), `sha256`,
   `bytes`, `row_count`, `schema_version: catalogue_snapshot/1.0`, `retrieved_by` (code revision).
2. Append to a `snapshots/INDEX.json` (one line per snapshot, never edited in place); the forecast and
   twin directories stay keyed by `as_of_<data_date>`.
3. Observation time vs ingestion time vs processing time are separate fields everywhere (the freshness
   block already has the slots).
4. Validation on ingest: column set, row count sanity, monotone data date, digest recorded before any
   reader may use it; a failed validation leaves a `*.rejected/` directory with the reason.
5. Prospective evaluation of the dated forecast remains a **separately approved** scoring step
   (`cosmos/ai/twin/prospective.py` is non-blind history; a new later snapshot would be the first blind test).
**P3-B.4 (implementation) + approval gate for any actual download.**

### E. Observability

| Area | Today | Recommendation |
|---|---|---|
| Logging | `orchestration.py` logs module completion/failure via `logging`; FastAPI/uvicorn default access logs; no structured fields | JSON lines logger with `run_id`, `module`, `duration_s`, `status`, `artifact_sha256` prefixes; request id per API call; log level configurable; **no payload values** in logs |
| Error reporting | `DataUnavailable` → 404 JSON/HTML with message+detail; `InvalidSelection` → 400; other exceptions → uvicorn 500 with traceback in server log only | add a generic handler that returns `{"error": "internal", "request_id"}` without the traceback; keep the traceback server-side |
| Health check | `/api/health` liveness only (correctly "unrelated to satellite health") | add `/api/ready`: required artifacts present, digests verified once, latest run id, schema versions — no secrets |
| Diagnostics | `scripts/check_console_prerequisites.py`, `verify_protected_artifacts.py`, run manifests | `scripts/diagnose_console.py` bundling both plus the benchmark probes above into one JSON |
| Sensitive data | manifests record `environment.host` (hostname) and absolute repository path in reports (`provenance.repository`); no credentials anywhere (Space-Track credentials are never read by the console) | make hostname and absolute paths optional (`--redact-host`), default redacted in exported reports; keep in local manifests |
**P3-A.5 (generic error handler, readiness endpoint), P3-B.5 (structured logs, diagnostics bundle).**

## 4. Stage 3 — P3.2 scientific enhancement assessment (no experiments run)

| Enhancement | Research question | Data requirements | Scientific risks | Validation strategy | Effort |
|---|---|---|---|---|---|
| **Vision front-end cache reconstruction** | Does the registration front end's negative result (X14: `raw ≥ both > diff`) hold at other operating points and seeds? | the 4.23 GB SpotGEO release (present); ~1 h CPU to rebuild `processed/front_end_f16` for 6,400 sequences | none to frozen results; new seeds would be new training (**not authorised**); only the classical arm can be re-run without training | re-score with the vendored official scorer; compare against the archived per-sequence submissions (X14 machinery) | 0.5 d + 1 h CPU; approval for compute |
| **Remaining 3b factorial cells** | Does the selection-data effect (+0.30 of +0.353) interact with the fit-data factor or the pool at the F4⁺ level? | regenerated AR(8) caches (present, manifest-verified); **two protocol decisions** — how A0's fit-period model supplies a half pool; how cross-fitting works with a calibration-window pool | each cell re-scores the pre-registered M1 test half (exploratory, disclosed); aliasing if the design stays partial | the P1/P3 machinery (validity gate c0/c5 exact); paired block bootstrap; Holm across main effects per proposal §6 | ~5 min/cell + 0.5 d; user decision first |
| **Additional subgroup calibration analysis** | Is the design-derived under-coverage explained by class × perigee × A/M-source cells the Mondrian grouping does not condition on, and does a Mondrian grouping that includes A/M source reach nominal on the archived tune-B/test predictions? | archived `tuneB_predictions.npz` / `test_predictions.npz` (present) + cohort split; no refit | **this is a methodology change if adopted**: re-grouping the conformal calibrator alters published intervals — admissible only as a pre-declared exploratory G3″ with "nothing adopted" stated, like G3′ | reproduce R0 exactly first; coverage by subgroup with cluster bootstrap; compare constructions on the pre-declared criterion | 1 d; **approval + protocol first** |
| **Satellite identity linkage** | Can any telemetry, conjunction or imagery evidence be attributed to a catalogued object? | identified telemetry (none public: ESA-ADB and OPS-SAT are anonymised or single-spacecraft without NORAD-linked events), CDMs with object ids (Kelvins is anonymised), astrometrically calibrated imagery with time (SpotGEO has neither) | fabricating joins is the cardinal risk (C4 rule); any linkage must come from a dataset that carries identifiers | a linkage is accepted only with an external identifier present in the source; unit tests asserting `identity_linkable` flips only when such a source exists | **blocked by data**; 0 engineering until a source exists |
| **Real subsystem-health monitoring** | Can a per-spacecraft subsystem health state be estimated and validated against labelled faults? | labelled, identified subsystem telemetry (power/thermal/ADCS) with fault ground truth — none public here; the legacy simulator is synthetic | presenting benchmark detection scores as health (forbidden); synthetic-to-real transfer claims without real data | none possible on present data; the console must keep "not determinable" | **blocked by data** |

## 5. Stage 4 — future opt-in inference architecture (not implemented; builds on the P1.5 proposal)

```text
study run  ──(fit)──►  outputs/models/<study>/<run_id>/MODEL_MANIFEST.json + files   (P1.5 §3–4)
                              │ model_digest = sha256(file digests ‖ canonical params ‖ learner)
                              ▼
run_pipeline --mode inference --model-manifest <path>
   adapters (inference mode): load → verify every file digest + backend major → build design matrix with
   the persisted contract → predict → gate → CQR tables → isotonic → Uncertainty(...) + Provenance(
   model_digest=…, input_hashes={cohort, model files}, config_digest) ; lineage.model_version.status="recorded"
                              ▼
outputs/pipeline/run_<ts>/ (mode: inference)  +  optional twin_state/1.2 records:
   {…, "prediction_provenance": {model_digest, model_manifest, inputs_sha256, mode: "inference"},
        "supersedes": {"artifact": …, "sha256": …}, "equivalence_with_archive": {…}}  — new directory, never a rewrite
```

| Element | Design decision |
|---|---|
| Model persistence | per P1.5: xgboost JSON, torch `state_dict` (loaded `weights_only=True`), arrays `allow_pickle=False`, JSON tables; **no pickle** |
| Digests | model digest as above; data digest = cohort file SHA-256 + split spec; config digest = canonical params; code = git commit; all four in `MODEL_MANIFEST.json` and in the run's `lineage` |
| Backend availability | `scripts/check_console_prerequisites.py` gains an `--inference` section; a model manifest declares `backend_versions`; loading refuses a major mismatch; absent backend ⇒ module `failed` with the reason, never a silent substitute |
| Safe loading | digest verification before deserialisation; vendor loaders only; models from an untrusted path refused unless listed in a local allow-list file |
| Inference API contracts | `POST /api/inference/runs {model_manifest, as_of, limit}` → new run directory with `mode: inference` (409 if the directory exists); `GET /api/models` lists manifests with digests and backend status; every response stamped `api/1.2`; the console labels inference-mode runs distinctly ("INFERENCE · model <digest>") |
| Twin-state update semantics | append-only: a new `as_of_<date>_inference_<model-digest-prefix>/twins.jsonl` (`twin_state/1.2`) with `prediction_provenance` and a `supersedes` pointer; the archived and re-emitted states are never modified; the console shows which state is displayed |
| Prediction provenance | `Provenance.model_digest` set; `lineage.model_version = {status: recorded, digest, manifest path}`; registry card linked **only** through `VERIFIED_MODEL_CARD_ASSOCIATIONS` populated from the manifest's declared card id *and* digest match |
| Validation | round trip on the archived predictions (exact for xgboost/physics/gate/CQR; float32 tolerance for torch); an inference run on the 2026-10-27 inputs must reproduce the archived forecast for the available learner or record the deviation per object; D-tests extended with an inference-mode object |
| Rollback | runs are immutable directories; the console's "latest complete run" selection gains an explicit pin file `outputs/pipeline/CURRENT_RUN` (optional) so a bad inference run can be de-selected without deletion |
| Honesty boundary | the system stays a dated-snapshot twin; inference mode re-derives predictions from persisted models on archived inputs — not a live feed. Any claim beyond that needs new data and approval |

Prerequisites before any of this: approval to install backends (and a new environment lock), the P1.5
persistence work in future *study* runs, and a protocol stating what an inference-vs-archive deviation
means.

## 6. Stage 5 — prioritised roadmap

### P3-A — essential runtime hardening

| # | Task | Files / functions | Depends on | Acceptance | Risks | Tests | Effort |
|---|---|---|---|---|---|---|---|
| A.1 | **Fix manifest inflation**: keep verbatim only an allow-list of metadata keys (`priority_rule`, `consequence_mass_kg`) or dicts ≤ 32 scalar entries; count everything else | `scripts/run_pipeline.py::_jsonable`; manifest `schema_version` → `run_manifest/1.2` | — | fresh full-run manifest < 50 kB; priority rule still recorded; old manifests untouched | none to values | `test_p0_lineage` (rule present), new size assertion, `test_p1_schema` version bump | 0.25 d |
| A.2 | Cache `list_runs()` / `run_manifest()` by (path, mtime, size); `latest_run_id` from the cache | `store.py` | A.1 | `list_runs` < 5 ms warm; object API < 60 ms warm | stale cache if a run is written mid-process → key includes mtime | perf test with thresholds; existing product tests | 0.5 d |
| A.3 | `missions()` metadata index (`prepared/INDEX.json` written once by a script; arrays loaded only for charts) | `store.py::missions`, new `scripts/index_telemetry_prepared.py` | — | overview page < 400 ms, RSS < 250 MB without charts | index drift → key by file size+mtime | `test_product` telemetry tests; perf test | 0.5 d |
| A.4 | Cache `repository_provenance()` digest and `prospective_status()` per process with mtime keys | `store.py` | — | `/api/overview` < 100 ms warm | — | existing + perf | 0.25 d |
| A.5 | Generic 500 handler without traceback; `/api/ready`; redaction option for hostname/absolute paths in exported reports | `api.py`, `reports.py`, `scripts/serve_console.py` | — | no traceback in any response body (test); `/api/ready` lists required artifacts and digests | — | new tests | 0.5 d |

### P3-B — optional system improvements

| # | Task | Files | Depends on | Acceptance | Risks | Tests | Effort |
|---|---|---|---|---|---|---|---|
| B.1 | `twin_state` root module with run-time equivalence check against the catalogue chain; shared reader module | `cosmos/ai/twin/reader.py` (from `store.py`), `adapters.py`, `run_pipeline.py` | A.1 | run manifest records `twin_state` artifact digest, source (reemitted/archived) and 31,396/31,396 equivalence; dependants unaffected | adapter change — keep `catalogue_state` chain as is | integration + D2 | 1 d |
| B.2 | Run comparison (§3B) | `cosmos/product/compare.py`, `api.py`, `compare.html` | A.2 | missing vs changed vs incomparable distinguished; no causal wording; lineage shown | — | new tests on two real runs + a `--limit` run | 1 d |
| B.3 | Cursor pagination (§3C) | `api.py`, `store.py`, templates | — | thresholds in §3C | API shape change → `api/1.2`, old params still accepted | new tests | 1 d |
| B.4 | Snapshot ingestion script and index (§3D) — **code only; downloads need approval** | `scripts/ingest_snapshot.py`, `cosmos/ai/data/download.py` | — | refuses to replace; manifest fields; validation; rejected directory | — | tests on a copied snapshot in tmp | 1 d |
| B.5 | Structured JSON logging + diagnostics bundle | `cosmos/ai/orchestration.py`, `api.py`, `scripts/diagnose_console.py` | A.5 | one log line per module/request with run id; no values in logs | — | log-capture tests | 0.5 d |
| B.6 | Visual regression of rendered screens | needs a headless browser (**install approval**) | — | pixel/DOM snapshots per screen | — | — | 0.5 d |

### P3-C — scientific research enhancements (each needs approval; none runs now)

| # | Item | Prerequisite | Effort |
|---|---|---|---|
| C.1 | Vision front-end cache rebuild (~1 h CPU) then classical-arm re-scoring at other operating points | compute approval | 0.5 d |
| C.2 | Remaining 3b cells | two protocol decisions by the user | 0.5 d + minutes/cell |
| C.3 | Subgroup-aware conformal grouping as a pre-declared exploratory study (G3″) | protocol + approval; **methodology-adjacent — nothing adopted** | 1 d |
| C.4 | Prospective evaluation of the dated forecast | a SATCAT snapshot with data date ≥ 2026-11-26 (download approval) | 1 d after data |
| C.5 | am_design Stage 2 with the substitute learner | approval; 2–6 GPU-h | 1 d |
| C.6 | Identity linkage / real subsystem health | **blocked by data**; no engineering until an identified dataset exists | — |

### P4 — future prediction-time inference (§5)

| # | Item | Prerequisite |
|---|---|---|
| P4.1 | Model persistence in future study runs (P1.5) | approval to run studies that fit xgboost/mlp/physics/AR(8) |
| P4.2 | Backend installation under a recorded environment lock | explicit approval |
| P4.3 | Inference-mode adapters, `/api/inference/*`, `twin_state/1.2` | P4.1–P4.2, protocol for deviations |
| P4.4 | Registry association through manifest digests | P4.3 |

## 7. Explicit approval requirements

| Needs approval | Why |
|---|---|
| Any P3 implementation (A, B) | this document is planning only |
| C.1 compute (1 h CPU), C.2 protocol decisions, C.3 protocol, C.4 download, C.5 GPU-hours | compute / data / methodology-adjacent |
| Installing any backend or a headless browser (B.6, P4.2) | environment change against the recorded lock |
| Any new snapshot download (B.4 use, C.4) | new data; freshness semantics depend on it |
| Any inference-mode execution (P4.3) | prediction-time model execution changes the system's description |
| Committing or pushing | standing constraint |

Not changed by this review: scientific methodology, frozen artifacts, confirmatory results, both twin-state
files, the JINT manuscript; no backend installed; no data downloaded.
