# COSMOS-AI — P3-A implementation report: runtime hardening (2026-11-08)

Scope executed: **P3-A1** (manifest serialisation and parsing), **P3-A2** (telemetry metadata without
loading arrays, provenance caching with explicit invalidation, run and object caching), **P3-A3**
(readiness, structured logs, generic errors, diagnostics, report redaction) — exactly the items approved
after `COSMOS_AI_P3_ENGINEERING_ROADMAP.md`. Nothing from P3-B, P3-C, P3-D or P4 was implemented. The
system remains a **read-only evidence twin**: no methodology, frozen dataset, confirmatory result,
benchmark score, model, twin-state artifact or orchestrator graph was changed; nothing was committed.
HEAD `78ee339` throughout, 0 staged paths.

## 1. Stage 1 — baseline before any change

| Item | Value | Record |
|---|---|---|
| Protected artifacts (ESA-ADB freezes 28/28, G5d, figure release 107/107, OPS-SAT 10/10, twin digests, gate record) | all OK | `outputs/audit/protected_artifacts_p3a_before_20261108T0803*.json` |
| Archived twin state `outputs/twin/as_of_2026-10-27/twins.jsonl` | sha `19a1fede1fd4871f380ff802f285d2ad03732f6cd3179790e67336c7d202a6b5`, 31,396 records | digest file |
| Re-emitted twin state `…_reemitted_v1/twins.jsonl` | sha `6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84`, 31,396 records | digest file |
| Forecast table | sha `b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86` | run manifest digest |
| Pipeline runs | 86 directories; latest `run_20261108T072802Z`, manifest **5,226,140 bytes** (`run_manifest/1.1`) | — |
| Full test suite | **400 passed, 3 skipped** in 83 s | `outputs/audit/pytest_full_20261108_p3a_before.log` |
| Console benchmark (TestClient, one process) | see §4 "Before" column | `outputs/audit/console_benchmark_p3a_before_20261108T080412+0000.json` |

The benchmark harness is new (`scripts/benchmark_console.py`): it probes every console surface
(overview API and page, datasets, search, object API and page, twin API, run list, run manifest API, run
page, ranking, report JSON and HTML) cold and warm, times the store primitives directly
(`list_runs`, `run_manifest` parse, `repository_provenance`, `missions`, twin lookup) and records RSS.

## 2. Integrity after the changes

| Check | Result |
|---|---|
| Protected artifacts | all OK — `outputs/audit/protected_artifacts_p3a_after_20261108T082032+0000.json` |
| Archived twin state | sha `19a1fede1fd4871f…` **unchanged** |
| Re-emitted twin state | sha `6bb4871f7dedfcf1…` **unchanged** |
| Forecast table | sha `b15644aab581cd05…` unchanged |
| Historical demonstration manifest `run_20261108T072802Z/run_manifest.json` | **untouched**: 5,226,140 bytes, mtime 2026-11-08 07:28:08 UTC, sha `2cd815c0121a8a652df80e41569a1ee6216de40d6246528b2f0e32cddf05c90f` |
| `outputs/pipeline/` | 86 run directories before and after; the verification run of the new serialiser was written to a temporary directory and deleted |
| Git | HEAD `78ee339`, 0 staged, no commit, push, merge, rebase, reset or clean |
| D1–D14 demonstration protocol | **14 passed** (`outputs/audit/pytest_demo_20261108_p3a_after.log`) |
| Full test suite | **426 passed, 3 skipped** in 68 s, exit 0 (`outputs/audit/pytest_full_20261108_p3a_after.log`); the first run after the changes was 2 failed / 424 passed — both failures were P1 assertions pinning the manifest stamp at 1.1, updated to 1.2 (§8) |
| New P3-A tests | **26 passed** (three files, §6) |

## 3. P3-A1 — manifest serialisation and parsing

**Cause.** P2 made `scripts/run_pipeline.py::_jsonable` keep *any* dictionary of scalars verbatim so that
the priority rule could be recorded. Per-object maps (`name`, `regime`, `object_class`, abstention
reasons) are dictionaries of scalars too, so the demonstration manifest grew to 5.2 MB.

**Fix (allow-list, not a heuristic).**
* `cosmos/ai/schema.py`: `MANIFEST_VERBATIM_OUTPUTS = frozenset({"priority_rule"})`; `run_manifest`
  current version **1.2**, accepted `("1.0", "1.1", "1.2")`. The 1.2 validator rejects any dict output that
  is not allow-listed unless it is one of three summary forms: `{count}`, `{rows, columns}` (table
  summary) or `{module, status, reason}` (evidence record). 1.0 and 1.1 keep their contracts; nothing
  historical is rewritten.
* `scripts/run_pipeline.py::_jsonable(value, key)`: verbatim only when `key ∈ MANIFEST_VERBATIM_OUTPUTS`
  **and** the values are scalars or lists of scalars; everything else is counted. `_module_manifest` passes
  the output key. The priority rule recorded by a fresh run is byte-identical to the one in the historical
  manifest (asserted in a test), so the console's "explained from the manifest only" path is unchanged.

**Measured.**

| Manifest | Objects | Schema | Size |
|---|---|---|---|
| `outputs/pipeline/run_20261108T072802Z` (historical, preserved) | 31,396 | run_manifest/1.1 | 5,226,140 bytes |
| Verification run in a temporary directory (`--limit 300`, deleted afterwards) | 300 | run_manifest/1.2 | **16,266 bytes** |
| Test run (`--limit 60`, pytest `tmp_path`) | 60 | run_manifest/1.2 | < 100 kB asserted |

Under 1.2 the only object-scaled entries are counts and the ranking table summary (rows + column names),
so a full 31,396-object manifest would be of the same order (~16 kB). A full run under `outputs/pipeline/`
was **not** produced: it would add a run directory and was not authorised; see §9.

**Parse cache (`cosmos/product/store.py`).** `ArtifactStore._cached_json(path)` parses a manifest once per
*file identity*. The key is `(st_size, st_mtime_ns, st_ino, fingerprint)` where the fingerprint is the full
SHA-256 for files ≤ 1 MB and the SHA-256 of the first and last 64 kB for larger files — the cache therefore
never relies on the modification time alone. `run_manifest()` and `_summarise_run()` (hence `list_runs()`
and `latest_run_id()`) read through it; a malformed manifest is reported (`DataUnavailable` / `complete:
False`) and never cached or repaired. `invalidate_caches()` clears every cache; `cache_stats()` exposes
hit/miss counters (also shown by `/api/ready`). Tests prove that a manifest rewritten with the **same size and
the same mtime** is re-parsed, and that an explicit invalidation forces re-parsing.

**API sizes.** `/api/runs/{latest}` is unchanged at 3,787.5 kB and the run page at 5,127.5 kB because the
latest run is the historical 1.1 record, preserved by design. A fresh run would serve ~16 kB.

## 4. P3-A2 — telemetry metadata, provenance caching, run/object caching

* **Mission listing without the sample matrix.** `_mission_meta` read `archive["X"].shape[0]`, which
  materialised the 448 MB `X.npy` member for every cold listing. The sample count now comes from the .npy
  header through the zip container (`store._npz_member_shape`): 0.4–0.9 ms instead of 169–1,211 ms per
  mission, and the shapes are **identical** to a full load for all three missions
  (1,472,832 × 76; 919,440 × 100; 932,243 × 48). A test wraps `NpzFile.__getitem__` and fails if `X` is
  ever requested during `missions()`. The roadmap's alternative (a separate `INDEX.json` artifact) was not
  adopted: the header read needs no new artifact and cannot drift.
* **`repository_provenance()` cache.** Git state is cached under a key built from `.git/HEAD`, `.git/index`,
  `.git/packed-refs` (mtime and size) and the file of the current ref; the forecast-digest verification is
  cached by file identity including the content fingerprint (§3). Tests: same-size, same-mtime tamper of
  the verified file → `MISMATCH` on the next call; restoring the content → `verified`; a changed `HEAD` →
  git re-queried; `invalidate_caches()` → both recomputed.
* **`prospective_status()` cache** keyed by the snapshot directory listing (names and mtimes).
* **Object lookup.** The catalogue `norad → row` index is built once per snapshot and used by
  `object_record` instead of a boolean filter over 31,396 rows; unknown ids still raise `DataUnavailable`.

**Benchmark (same harness, same process layout, warm = second call).**

| Probe | Before ms | After ms | Size kB |
|---|---|---|---|
| overview api | 485 | 463 | 5.9 |
| overview api (warm) | 345 | **34** | 5.9 |
| overview page | 3,198 | **435** | 18.8 |
| overview page (warm) | 368 | **28** | 18.8 |
| datasets api | 26 | 31 | 1.5 |
| search | 34 | 28 | 9.7 |
| object api 37607 | 272 | 113 | 15.9 |
| object api 37607 (warm) | 154 | 42 | 15.9 |
| object page 37607 | 227 | 70 | 26.3 |
| twin api 23806 (index build) | 24 | 13 | 4.8 |
| twin api 25544 | 12 | 8 | 3.7 |
| runs list api | 76 | 27 | 45.8 |
| runs list api (warm) | 66 | 27 | 45.8 |
| run manifest api | 67 | 26 | 3,787.5 |
| run manifest api (warm) | 82 | 24 | 3,787.5 |
| run page | 222 | 183 | 5,127.5 |
| ranking 25 | 79 | 66 | 27.4 |
| report json 37607 | 345 | 98 | 23.8 |
| report html 37607 | 330 | 92 | 21.9 |

| Store primitive | Before | After |
|---|---|---|
| `missions()` cold | 2,508 ms | **8.5 ms** |
| `list_runs()` cold / warm | 47.1 / 35.9 ms | 50.8 / **2.9 ms** |
| `run_manifest()` parse cold / warm | 33.4 / 31.2 ms | 0.1 / 0.1 ms (served from the cache populated by `list_runs`) |
| `repository_provenance()` cold / warm | 51.0 / 49.8 ms | 48.3 / **0.3 ms** |
| twin lookup (cold, index build) | 94 ms | 59 ms |
| RSS at start / peak | 120 / **703 MB** | 128 / **294 MB** |

Records: `outputs/audit/console_benchmark_p3a_before_20261108T080412+0000.json`,
`outputs/audit/console_benchmark_p3a_after_20261108T081953+0000.json`.

**Against the roadmap's planning targets.** `list_runs` warm < 5 ms: met (2.9). Overview API warm < 100 ms:
met (34). Overview page < 400 ms: **cold 435 ms, not met by 35 ms** (the cold call includes the first
catalogue load and one git spawn; warm 28 ms). RSS < 250 MB: **peak 294 MB, not met** — the peak occurs while
serving the 5 MB historical manifest and run page; the process starts at 128 MB. Both figures are reported
as measured; no further tuning was attempted because it was not in the approved scope. The cold `list_runs`
is 4 ms slower than before because every manifest is fingerprinted (SHA-256 of a small file) on first sight;
that cost buys the invalidation guarantee.

## 5. P3-A3 — observability and safe failure

* **`GET /api/ready`** (new): `200` when the forecast table is present and the dated-forecast digest is
  `verified` (or legitimately `absent`), `503` otherwise. Body: `ready`, `checks` (forecast table present,
  digest state, git commit, complete run present, re-emitted twin state present), `latest_run`,
  `schema_versions` (every family's current version), `cache` counters, and the note that it says nothing
  about any spacecraft. No absolute path or hostname appears in it (asserted). `/api/health` stays a
  liveness probe. Tests cover the real root (200), an empty root (503) and a digest mismatch (503).
* **Request ids and structured logs.** `cosmos/product/logging_setup.py` (JSON-lines formatter,
  `configure_logging`, `log_fields`). An HTTP middleware assigns or echoes `X-Request-ID`, sets it on every
  response and writes one record per request: `ts, level, logger, event, request_id, method, path, status,
  duration_ms` — never bodies, payloads or query values. `scripts/serve_console.py --log-json` switches
  the structured format on.
* **Generic 500 without traceback.** An `Exception` handler returns `{"error": "internal", "message":
  …, "request_id": …}` (JSON) or the `error.html` page with the same id; the full traceback is logged
  server-side under that id (`cosmos.product.app`, field `traceback`). The test injects a `RuntimeError`
  carrying a secret string and a private path and asserts neither reaches the JSON or HTML response while
  both reach the server log. `DataUnavailable` (404) and `InvalidSelection` (400) keep their specific
  codes. Limitation at the time of this report: on a 500 the `X-Request-ID` *header* was not set (the exception
  leaves the middleware before the header step); the id was in the body and in both log lines. **Resolved in the
  final validation** (`COSMOS_AI_P3A_FINAL_VALIDATION_REPORT.md`): the handler now sets the header itself.
* **Diagnostics bundle.** `scripts/diagnose_console.py` (read-only; writes one JSON) gathers prerequisites,
  readiness, timed probes, cache statistics and the protected-artifact verification; the hostname is
  recorded only as a hash prefix. Run today: `outputs/audit/console_diagnostics_20261108T082033+0000.json`
  — ready `true`, protected artifacts OK, probes `/api/ready` 154 ms, `/api/overview` 292 ms,
  `/api/objects/37607` 136 ms, `/api/runs` 24 ms (cold process).
* **Report redaction.** `cosmos/product/reports.redact(document, root)` replaces the absolute repository
  path and the machine hostname wherever they occur in a string and records what it did
  (`redaction.applied`, `redacted_fields`, `preserved`, `note`); it never touches SHA-256 digests, the git
  commit, configuration digests, run ids, timestamps or values (asserted: the set of 40–64-hex strings in
  the redacted and unredacted documents is identical). `/reports/object/{norad}/download` redacts **by
  default** (`?redact=false` to keep), `/api/reports/object/{norad}?redact=true` opts in. The rendered HTML
  shows a "Redacted export" banner. Finding: the HTML rendering never carried the path or hostname; the
  JSON document's `provenance.repository` did, and that is what is redacted.

## 6. Tests

| File | Tests | What they prove |
|---|---|---|
| `tests/test_p3a_manifest.py` | 8 | allow-list semantics; 1.2 current and accepted with 1.0/1.1; validator accepts the three summary forms and rejects verbatim maps (1.1/1.0 still read); the 5.2 MB historical manifest readable and the rule intact; a fresh pipeline run (subprocess, `tmp_path`) is 1.2, < 100 kB, counts per-object maps and records the identical rule; cache hit → same-size/same-mtime content change → re-parse → explicit invalidation; malformed manifests flagged incomplete and never cached; API/store consistency |
| `tests/test_p3a_performance.py` | 9 | header shape = full-load shape; `missions()` never requests `X`; digest cache invalidated by content with unchanged size and mtime; large-file identity change recomputed; git cache follows `HEAD`; prospective status cached; run listing parsed once; catalogue index equals the filtered row and rejects unknown ids |
| `tests/test_p3a_observability.py` | 9 | ready 200 / 503 / 503-on-mismatch; request id generated and echoed with one structured line each; 500 without traceback in JSON and HTML, traceback and id in the server log; specific codes preserved; `redact` unit (path, host, nested strings; hashes, commit, run id, values preserved; input not mutated); download redacted by default, API document not; `--log-json` flag; diagnostics script compiles |
| `tests/test_demo_workflow.py` D1–D14 | 14 | unchanged protocol, all passing on the hardened code |
| Full suite | 426 passed, 3 skipped | `outputs/audit/pytest_full_20261108_p3a_after.log` (baseline before the changes: 400 passed, 3 skipped) |

## 7. Files changed or added

| File | Change |
|---|---|
| `cosmos/ai/schema.py` | `run_manifest` 1.2 current; `MANIFEST_VERBATIM_OUTPUTS`; `_MANIFEST_SUMMARY_FORMS`; 1.2 validation |
| `scripts/run_pipeline.py` | `_jsonable(value, key)` allow-list; key passed from `_module_manifest` |
| `cosmos/product/store.py` | `_file_key`, `_cached_json`, `_cached_digest`, `_git_key`, `_cached_git`, `invalidate_caches`, `cache_stats`, `cache_events`; `repository_provenance`, `run_manifest`, `_summarise_run`, `prospective_status` through the caches; `_npz_member_shape` and header-based `samples` in `_mission_meta`; catalogue norad index in `object_record` |
| `cosmos/product/api.py` | request-id middleware with structured logs; generic `Exception` handler; `GET /api/ready`; `redact` query parameter on the report JSON (default off) and download (default on) |
| `cosmos/product/reports.py` | `redact()`; "Redacted export" banner in `render_html` |
| `cosmos/product/logging_setup.py` | new |
| `scripts/serve_console.py` | `--log-json` |
| `scripts/diagnose_console.py`, `scripts/benchmark_console.py` | new |
| `tests/test_p3a_manifest.py`, `tests/test_p3a_performance.py`, `tests/test_p3a_observability.py` | new (26 tests) |
| `tests/test_p1_schema.py` | two assertions that pinned the *current* manifest stamp at `run_manifest/1.1` (lines 20 and 82) now expect 1.2; the legacy-acceptance assertions for 1.0 and 1.1 are unchanged |
| `docs/architecture/SCHEMA_VERSIONING.md` | `run_manifest` 1.2 row; 1.1 legacy note (inflation) |
| `docs/product/CONSOLE_LAUNCH.md` | `--log-json`, readiness, request ids, diagnostics, three troubleshooting rows |

No template, adapter, orchestrator, twin-engine, re-emission, dataset, benchmark or model file was
changed. No manuscript or thesis file was touched; Phase 9 remains locked.

## 8. Deviations from the roadmap wording (all within the approved scope)

1. A.1 allow-list is exactly `{"priority_rule"}`; `consequence_mass_kg` is a scalar output and is kept as
   such without being allow-listed. The roadmap's looser alternative ("dicts ≤ 32 scalar entries") was
   not adopted because it would again be a heuristic.
2. A.3's `INDEX.json` artifact was replaced by header reads (no new artifact to keep in step).
3. Cache keys never rely on mtime alone (approval requirement): size, mtime_ns, inode **and** a content
   fingerprint; full SHA-256 for files ≤ 1 MB.
4. The first full-suite run after the changes showed **2 failures, 424 passed**: both were the P1 tests above
   asserting that the current stamp is 1.1. They were updated to 1.2 (the approved version) and the suite was
   re-run; the final result is in §2 and §6.
5. Two roadmap planning thresholds were not reached (overview page cold 435 ms vs 400; RSS peak 294 MB vs
   250) and are reported in §4 rather than tuned further.

## 9. Remaining roadmap — not implemented, each needs explicit approval

* **Fresh demonstration run** — approved and executed afterwards as `run_20261108T083402Z`; see `COSMOS_AI_P3A_FINAL_VALIDATION_REPORT.md`. Original text: one `python scripts/run_pipeline.py --as-of
  2026-10-27` into a new `outputs/pipeline/run_<UTC>/` so the console's *latest* run carries a 1.2 manifest
  (~16 kB instead of 5.2 MB; `/api/runs/{latest}` and the run page shrink accordingly). It adds a run
  directory, so it was not done unasked. The historical run stays as it is.
* **P3-B** optional system improvements (twin-state module, run comparison, pagination, later-snapshot
  ingestion design, remaining observability items such as the `X-Request-ID` header on 500 responses).
* **P3-C** scientific enhancements (each an experiment; none runs without approval).
* **P3-D / P4** opt-in inference architecture (builds on the P1.5 proposal).
* Phase 9 (writing) remains locked.
