# COSMOS-AI — P3-B design and implementation report: twin-state evidence root and bounded performance investigation (2026-11-08)

Scope executed, as approved: **P3-B** twin-state integration (explicit source selection, provenance and
integrity, record validation and equivalence, API and console exposure, failure handling, chain preserved) and
the **bounded performance investigation** (profiling, attribution, three narrowly scoped optimisations with
regression tests, measurements against the unchanged targets). Not started: P3-C, P3-D, P4, Phase 9, any new
dataset, retraining, methodology change, or edit to pre-registrations and frozen artifacts. No commit, push,
merge, rebase, reset, clean or discard. COSMOS-AI remains an **archived-evidence, read-only digital twin**: no
live telemetry, no operational control, no on-demand model inference; the twin-state root reads a saved archive.

## 1. Baseline repository state (before any edit, 08:48 UTC)

| Item | Value |
|---|---|
| Git | HEAD `78ee33962007203bcfc829fc743a663b350373e1`, branch `product/mission-intelligence-console`, 0 staged, 18 modified tracked files (all pre-existing, uncommitted by instruction), 251 untracked paths |
| Protected artifacts | all OK — `outputs/audit/protected_artifacts_p3b_before_20261108T084858+0000.json` |
| Archived twin state `outputs/twin/as_of_2026-10-27/twins.jsonl` | sha `19a1fede1fd4871f380ff802f285d2ad03732f6cd3179790e67336c7d202a6b5`, 31,396 records |
| Re-emitted twin state `…_reemitted_v1/twins.jsonl` | sha `6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84`, 31,396 records |
| Forecast table | sha `b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86` |
| Historical manifest `run_20261108T072802Z/run_manifest.json` | 5,226,140 bytes, mtime 07:28:08 UTC, sha `2cd815c0121a8a652df80e41569a1ee6216de40d6246528b2f0e32cddf05c90f` |
| Latest run `run_20261108T083402Z` | `run_manifest/1.2`, 16,311 bytes, seven tables (hashes recorded) |
| Run directories | **87** |
| Full test suite | **427 passed, 3 skipped** (`outputs/audit/pytest_full_20261108_p3b_before.log`) |
| P3-A implementations identified | `cosmos/ai/schema.py` (`run_manifest` 1.2, `MANIFEST_VERBATIM_OUTPUTS`, summary forms), `scripts/run_pipeline.py::_jsonable`, `cosmos/product/store.py` caches (`_file_key`, `_cached_json`, `_cached_digest`, git / prospective / catalogue-index caches, `invalidate_caches`), readiness, logging, redaction |

The code matched the P3-A reports with one documented exception found while reading: the reports describe the
console's twin reader as "preferring the re-emitted file and labelling fallback"; the P2 implementation also fell
back *per object* when a record was absent from the re-emitted file. P3-B replaces that with a source-level policy
(§3); a record absent from the selected source is now reported as such, never fetched from the other archive.

## 2. Architecture before and after

**Before.** Runtime chain `catalogue_state → lifetime → reentry → decision_priority` reading
`forecast_table.csv.gz`; independent roots `collision`, `health`, `debris`. The twin state was read only by the
console (`store.twin_record`, offset index) and classified *archived-only, not read by the runtime pipeline*.

**After.** The chain is byte-for-byte unchanged (§6, acceptance 13). Two modules were **added**:

```
catalogue_state ─┬─ lifetime ──┐
                 └─ reentry ───┼─ decision_priority          (unchanged)
collision · health · debris    (independent roots, unchanged)
twin_state (root) ─────────────┼─ twin_equivalence           (new: depends on twin_state, catalogue_state, lifetime, reentry)
```

* `cosmos/ai/twin/reader.py` — **one shared reader** for the console and the orchestrator: source selection,
  candidate verdicts, streaming validation, equivalence (so a value on the object page and a value in a run table
  come from the same code path).
* `cosmos/ai/twin/modules.py` — `twin_state` (selects, verifies, indexes; publishes provenance as flat manifest
  fields) and `twin_equivalence` (compares every indexed record with the chain's outputs of the run; writes
  `twin_equivalence.csv`). Registered in `adapters.default_modules()`; `--twin-source-policy` on the pipeline.
* Console: `GET /api/twin-state`, page `/twin-state` (nav "Twin State"), `policy` on `/api/objects/{norad}/twin`,
  selection and per-object equivalence on the object page, readiness reports the selected source, the
  "versioned twin state" capability row is driven by the run manifest.

## 3. Twin-state source-selection policy

| Policy | Behaviour | Status values |
|---|---|---|
| `prefer_reemitted` (default) | select `twin_state/1.1` when valid; otherwise the archived `twin_state/1.0` **as a labelled fallback**; otherwise unavailable | `primary` · `fallback` · `unavailable` |
| `reemitted_only` | select 1.1 when valid; **no fallback** (archived candidate reported `not_evaluated`, reason "fallback not permitted") | `primary` · `unavailable` |
| `archived_only` | select 1.0 explicitly — reported as `explicit_archived`, **not** as a fallback | `explicit_archived` · `unavailable` |

A candidate is **valid** only when present, non-empty, its first record parses and passes `validate_twin_record`,
its schema is accepted (`twin_state/1.0`, `1.1`), its SHA-256 equals the recorded digest when one exists
(`verified`; `MISMATCH` rejects), and its record count equals the count recorded by the re-emission manifest when
one exists. Every candidate carries `reasons` (why it is invalid or missing) and `warnings` (e.g. no recorded
digest, no per-output provenance). A present-but-empty file is `invalid` with the reason "present but empty …
not a missing one, and not a valid one" — never confused with a missing source. The selection object (policy,
selected, status, `fallback_used`, `fallback_permitted`, reason, candidates) is returned on every API response,
shown on the object page and the Twin State page, and recorded in run manifests (`source`, `selection_status`,
`policy`, `fallback_used`, `selection_reason`).

## 4. Provenance and integrity design

Exposed for the selected source (API `provenance` block, manifest fields, Twin State page): schema version
(detected and expected), artifact path, recorded and computed SHA-256 with `digest_state`, transformation digest,
method and code revision (from `REEMISSION_MANIFEST.json`), record count vs recorded count, `original_or_reemitted`
(`reemitted` / `original_archive`), `predictions_regenerated` and `model_executed` as recorded (both `false`),
`provenance_on_outputs` (1.1 only), `artifact_provenance_complete`, `provenance_complete` (artifact **and**
output level — always false for the 1.0 archive), and `model_version` — `unavailable` unless the re-emission
manifest genuinely records a digest (tested with a synthetic manifest; never inferred). A manifest claiming
regeneration is flagged, not believed.

Streaming validation (`reader.validate_archive`, one pass, nothing retained): records total / valid, malformed
JSON lines, schema-invalid records (including 1.1 records missing output provenance), duplicate identities (first
occurrence kept in the index, duplicates counted with line numbers), records with invalid or unavailable values
(None/NaN/±inf probabilities or probabilities outside [0, 1]) — each with up to five examples.

## 5. API and UI changes

| Surface | Change |
|---|---|
| `GET /api/twin-state?policy&as_of&run_id` | selection, provenance, integrity, equivalence, `model_version`, `overall` verdict (`primary_verified` ok · `primary_with_findings` warn · `fallback` / `explicit_archived` warn · `unavailable` bad); first call streams the archive (~1.5 s), then cached by the identity of every candidate file and run table |
| `GET /twin-state` | page with the overall badge, selection table (both candidates, verdicts, reasons), provenance table, integrity table, equivalence tables (counts, not-comparable reasons, differing fields, examples); policy switcher. A fallback or explicit archived read is amber; a primary with integrity or equivalence findings is amber; green only for `primary_verified` |
| `GET /api/objects/{norad}/twin?policy` | `selection`, `equivalence` (per-object shared-value comparison with the latest run), `artifact_sha256`, `digest_state`, `record_count`, `original_or_reemitted`, `transformation_digest_sha256`; `missing_record` when the object is absent from the selected source |
| Object page, "Twin state" panel | source-selection line and equivalence line (`EQUAL n of n` / `DIFFERENT fields` / `NOT COMPARABLE` / `NOT IN RUN`, with not-compared fields and reasons) |
| `GET /api/ready` | `checks.twin_state_source {selected, status, policy}` (informational) |
| Capability strip | "versioned twin state" = `implemented` only when the run's manifest carries a successful `twin_state` module (detail names source, digest state, records, fallback, run-time equivalence counts); `blocked` when the module failed; `archived_only` for runs predating the module |
| Run pages | the two modules appear with lineage and evidence classes (`MODULE_EVIDENCE_CLASS` extended) |
| `api` schema | `1.1 → 1.2` (additive: readiness, redaction block, twin-state endpoint, selection/equivalence blocks); three pins in `tests/test_p1_schema.py` updated; `SCHEMA_VERSIONING.md` row updated |

No claim of integrated spacecraft health, collision prediction or live status was added; the Twin State page states
"archived evidence only … no live feed, no prediction regenerated, no model executed at request time" (scanned, §6).

## 6. Test coverage and results

| File | Tests | Acceptance items |
|---|---|---|
| `tests/test_p3b_twin_state.py` | 22 | 1 valid 1.1 selected (real root and slice); 2 explicit fallback and `archived_only`; 3 fallback visible in API, object page and Twin State page (never green); 4 invalid 1.1 never a clean primary — hash mismatch, malformed first line, unsupported schema, count mismatch, empty file (selection level) and mid-file malformed record (integrity level → FINDINGS); 5 missing primary / fallback / both, with module failure and blocked dependant while the chain succeeds; 6 hash mismatch; 7 unsupported schema; 8 duplicates and malformed records, value problems; 9 provenance fields equal the artifacts' values; 10 model provenance unavailable, surfaced only when a manifest records it, incomplete provenance flagged; 11 equivalence equal on an untouched slice and one changed value detected (field, example, page badge); 12 missing-in-chain and not-comparable reported separately (operator-controlled representation, non-coherent lifetime); 13 chain graph and slice outputs unchanged, manifest 1.2 valid; availability row; API policy validation and cache invalidation; run-table copies |
| `tests/test_p3b_chain_unchanged.py` | 1 | 13 — a **full** pipeline run with the new modules reproduces the seven tables byte-for-byte against `run_20261108T083402Z`; manifest 1.2 < 100 kB; twin modules success; equivalence 31,396 / 31,396 |
| `tests/test_p3b_performance.py` | 5 | the three optimisations (§10): debris availability by presence, overview/datasets never parse detections, debris screens still do, indexed single-object chain view equals the full-table comparison and is cheap, caches cleared by `invalidate_caches` |
| `tests/test_p3a_*.py` (14) | 27 passed | `outputs/audit/pytest_p3a_20261108_p3b_after.log` |
| `tests/test_demo_workflow.py` D1–D14 (15) | 14 passed | `outputs/audit/pytest_demo_20261108_p3b_after.log` |
| P3-B files together | **28 passed** | `outputs/audit/pytest_p3b_20261108.log` |
| **Full suite** | **455 passed, 3 skipped**, exit 0 (+28 tests over the 427-passed baseline; 0 failures) | `outputs/audit/pytest_full_20261108_p3b_after.log` (baseline 427 passed, 3 skipped) |

Fixtures are slices of the **real** archives (first N records, matching forecast-table rows, digest files and a
re-emission manifest adjusted to the slice); tampering is applied to copies only. Wording scan of `/twin-state`
(both policies), `/`, four object pages, the run page and the report: **0** live-feed / on-demand-inference claims.

## 7. Record-equivalence results (real archives, run `run_20261108T083402Z`)

| Measure | Re-emitted `twin_state/1.1` | Archived `twin_state/1.0` |
|---|---|---|
| Twin records read | 31,396 | 31,396 |
| Records compared / equal / different | 31,396 / **31,396** / **0** | 31,396 / 31,396 / 0 |
| Records not comparable (no shared field) | 0 | 0 |
| Missing in chain / missing in twin | 0 / 0 | 0 / 0 |
| Shared values compared / equal / different | 452,690 / 452,690 / 0 | 452,690 / 452,690 / 0 |
| `equivalent` | true | true |

Shared values: name, regime, object class, perigee, apogee, inclination, mass; re-entry abstention flag,
p(30 d / 90 d / 1 yr), and the 5 / 50 / 95 % time quantiles; for uncontrolled D/R/C objects the lifetime
comparison output against the chain's lifetime estimate (probabilities and quantiles). Fields **not compared, by
reason** (reported, never forced):

| Field: reason | Records |
|---|---|
| `reentry.abstained`: the twin marks operator-controlled objects as abstaining (C3) with the payload base-rate probabilities attached; the chain's `reentry` module records those same forecast-table probabilities as a prediction with the regime as an assumption — representations differ, values compared | 16,386 |
| `reentry.time_quantiles`: the chain has no time quantiles for these objects (bounds missing or non-positive) | 16,386 |
| `lifetime`: the chain's lifetime expert abstained (per-horizon probabilities not monotone, L17) | 123 |

Semantic normalisations applied, each stated in code: unknown mass is `NaN` in the twin and `None` in the chain
(both "unavailable"); raw non-monotone quantiles would be reported not comparable because the chain applies
monotone ordering (none occurred). The same figures were produced by the orchestrator modules in a full
temporary-directory run (`twin_equivalence.csv`: 31,396 rows, all `equal`) and by the offline script
(`outputs/audit/twin_state_integration_p3b_20261108T091101+0000.json`, computed in 1.37 s).

**Finding for the owner (not changed here):** the twin-state engine and the runtime chain represent
operator-controlled payloads differently (abstention with base-rate values vs. prediction with a regime
assumption). The values agree; the representation does not. Aligning them would be a methodological decision.

## 8. Failure-mode behaviour (all exercised by tests on tampered copies)

| Condition | Selection | Integrity / module | Visible as |
|---|---|---|---|
| Primary archive missing | `fallback` to 1.0 under `prefer_reemitted` (reason names the path); `unavailable` under `reemitted_only` | module reads the archive, `fallback_used: true` | amber FALLBACK on object and Twin State pages; readiness `twin_state_source.status = fallback` |
| Fallback archive missing, primary valid | `primary`; archived candidate `missing` | — | green only if integrity and equivalence are clean |
| Both missing | `unavailable` with both paths in the reason | `twin_state` **failed** (`TwinStateUnavailable`), `twin_equivalence` **blocked**, chain modules **success** | red NO TWIN-STATE SOURCE; API `available: false` |
| Malformed first line | candidate `invalid` ("not valid JSON") | — | fallback / unavailable, reason shown |
| Malformed record mid-file | `primary` (artifact is the recorded one) | `records_malformed_json = 1`, status `issues` | amber FINDINGS; module `integrity_status: issues` |
| Duplicate identity | valid (if recorded as such) | `duplicate_identities = 1` with lines; index keeps first | FINDINGS |
| Hash mismatch (file changed after digest) | `invalid`, `digest_state: MISMATCH` | — | fallback / unavailable |
| Unsupported schema (`twin_state/9.0`) | `invalid` ("not supported") | — | fallback / unavailable |
| Record-count mismatch vs manifest | `invalid` | — | fallback / unavailable |
| Re-emission manifest absent | valid, `provenance_complete: false`, warning | — | provenance "incomplete", never green |
| 1.1 record without output provenance | — | `records_schema_invalid` with the record's error | FINDINGS |
| One changed value | `primary` | equivalence `records_different = 1`, field and example | amber DIFFERENCES; object page DIFFERENT with the field |
| Present but empty file | `invalid` ("present but empty") — distinct from missing | — | reason shown |
| Object absent from the selected source | — | `missing_record` reason; no other source consulted per object | "No twin-state record" with the selection shown |

Nothing is repaired, filled or substituted in any of these cases.

## 9. Performance investigation — methodology

* **Harness A (`scripts/benchmark_console.py`)** — one process, TestClient, the P3-A probe sequence (overview
  API then page, datasets, search, object API/page, twin API, runs, run manifest, run page, ranking, reports), cold
  and warm, RSS per probe, peak RSS. This is the methodology under which the 446 ms / 286 MB figures were reported.
* **Harness B (`scripts/profile_console_cold.py`, new)** — **five fresh Python processes**, uninstrumented,
  `perf_counter` per step in the order the overview needs them (import, `create_app`, git subprocess, run-list
  fingerprinting, first prospective assessment, catalogue load, manifest parse, telemetry metadata, P3-B twin
  selection, first `GET /`, warm `GET /`, `/api/overview`, first `/api/twin-state`, first and warm object page), RSS
  from `/proc/self/statm` after each step, peak RSS from `getrusage`; medians / min / max across runs; **one
  separate tracemalloc-instrumented run** for allocation attribution only (its timings are discarded — a first
  attempt that traced the timing runs inflated them 5–10× and was discarded, record deleted).
* **Attribution runs** — every `ArtifactStore` method wrapped with a timer during the first page render in a fresh
  process; per-library import RSS in fresh processes; `cProfile` of a warm `twin_record`.
* Environment: Python 3.12, Linux 6.17 (Intel), pandas / numpy versions recorded in the profile JSON; same checkout,
  same machine, no other heavy job running during measurements (measurements were run alone and sequentially).

Records: `outputs/audit/console_cold_profile_p3b_20261108T091752+0000.json` (before optimisations),
`…_p3b_after_…T115246`, `…_p3b_final_…T115451`, `…_p3b_final_v2_…T115826` (final);
`console_benchmark_p3b_after_…T115216`, `…_p3b_final_…T115421`, `…_p3b_final_v2_…T115826`.

### Attribution of the cold overview (fresh process, medians, before optimisation)

| Step | ms | ΔRSS MB | Note |
|---|---|---|---|
| import `cosmos.product.api` | 508 | +115 (→132 MB) | pandas 92.5 MB / 284 ms, fastapi+starlette+pydantic 31 MB / 189 ms, jinja2 11 MB, numpy 16 MB |
| `create_app` | 15 | +0.7 | |
| git subprocess + forecast digest check | 61 | +0.1 | `repository_provenance` |
| run-list fingerprinting + parse (87 manifests) | 49 | +14 | the 5.2 MB historical manifest's parsed objects were retained |
| first prospective assessment | **196** | **+31** | `scripts.check_t1_later_snapshot.assess`: reads SATCAT CSVs (`usecols`) via pandas, git, digest — cached afterwards |
| catalogue load | 58 | +11 | |
| manifest parse (latest) | 3 | 0 | cached |
| telemetry metadata | 9 | +3 | header reads (P3-A) |
| P3-B twin selection | 111 | +0.1 | SHA-256 of the 78 MB archive + line count, once per process |
| first `GET /` after the above | **433** | **+78** | **375 ms / +74 MB = `_datasets` → `debris_sequences(limit=1)` parsing the whole SpotGEO detections JSON just to report availability**; templates compile 21 ms; rest < 40 ms |
| first `/api/twin-state` | 1,416 | +37 | streams the archive once, then cached |
| object page first / warm | 141 / 43 | +17 / 0 | P3-B per-object overhead ≈ 27 ms warm (second run listing 6.6 ms; pandas single-row slicing of three frames ≈ 9 ms; serialisation of the larger payload) |

## 10. Optimisations implemented (narrow, display-only, tested) and before/after measurements

1. **Debris availability by artifact presence** (`store.debris_available`, used by `_datasets`): the overview and
   datasets listings no longer parse the SpotGEO detections. Tests: row content unchanged, listings never call the
   parser, debris screens still parse it.
2. **Indexed single-object chain view** (`_frame_row_dict`, `_catalogue_rows`, `reader.chain_view_for_object`
   sharing `_chain_entry` with the full view) and **run id passed through** from the object record: the P3-B
   per-object comparison uses scalar lookups instead of three 31,396-row scans and one extra run listing. Test:
   indexed result equals the full-table comparison; `invalidate_caches` clears the indexes.
3. **Large manifests not retained** (`JSON_RETAIN_MAX_BYTES = 1 MB`; run summaries cached separately by file
   identity): the 5.2 MB historical manifest is parsed on demand (~30 ms when its page is opened) instead of
   holding ~14 MB of objects. Tests: P3-A cache tests (updated expectation documented), historical manifest still
   readable.

Nothing scientific changed: the three changes touch listing availability, lookup mechanics and cache retention.

### Harness A (benchmark; same probe sequence as the P3-A reports)

| Probe | P3-A final (before P3-B) | After P3-B + opt. 1 | **Final (opt. 1–3)** | Original target | Met? |
|---|---|---|---|---|---|
| Overview page, cold | 446 ms | 62 ms | **56 ms** | 400 ms | **yes, under this definition** (see caveat) |
| Overview page, warm | 37 ms | 35 ms | 27 ms | — | |
| Overview API, cold / warm | 436 / 26 ms | 464 / 29 ms | 464 / 32 ms | — | unchanged: git + run list + prospective + catalogue |
| Peak RSS over the sequence | 286 MB | 241 MB | **235 MB** | 250 MB | **yes, under this definition** (see caveat) |
| Object API, cold / warm | 119 / 28 ms | 292 / 55 ms | 279 / **37 ms** | — | P3-B overhead: cold +160 ms (twin digest 108 + first run-table loads), warm **+9 ms** |
| Object page | 73 ms | 74 ms | 74 ms | — | |
| Twin API (25544) | 10 ms | 40 ms | 28 ms | — | larger payload (selection + equivalence) |
| Run manifest API (latest) | 9.2 ms, 17.7 kB | 16.6 ms | 8.8 ms | — | |
| Run page | 85 ms | 46 ms | 43 ms | — | |
| Report JSON / HTML | 81 / 93 ms | 64 / 60 ms | 45 / 36 ms | — | |
| `missions()` cold | 8.3 ms | 8.7 ms | 12.7 ms | no array load | yes (test-enforced) |
| `list_runs` cold / warm | 54 / 3.0 ms | 61 / 3.3 ms | 64 / 2.5 ms | — | |

(The intermediate `p3b_final` record — index without the scalar path — measured object API warm 45 ms and peak
252 MB; superseded by the final build.)

### Harness B (fresh process, medians of 5)

| Step | Before opt. | **Final** |
|---|---|---|
| import `cosmos.product.api` | 508 ms, 132 MB | 546 ms, 132 MB |
| git + digest | 61 ms | 58 ms |
| run list | 49 ms, +14 MB | 55 ms, **+10 MB** |
| first prospective assessment | 196 ms, +31 MB | 213 ms, +27 MB |
| catalogue | 58 ms, +11 MB | 64 ms, +11 MB |
| first `GET /` remaining | **433 ms, +78 MB** | **69 ms, +3 MB** |
| **first-overview path from a fresh process** (sum of the store steps + page, excluding import) | **≈ 809 ms** | **≈ 472 ms** |
| RSS after the first overview | 269 MB | **185 MB** |
| `GET /` warm | 37 ms | 25 ms |
| first `/api/twin-state` | 1,416 ms, +37 MB | 1,537 ms, +38 MB |
| object page first / warm | 141 / 43 ms | 154 / 36 ms |
| RSS end / peak (sequence incl. twin-state streaming and object page) | 325 / 311 MB | 249 / **274 MB** |

### Against the original targets — stated plainly

* **Cold overview 400 ms.** Under the methodology that produced the 446 ms figure (Harness A, page probe after
  the API probe), the page now takes **56 ms: met**. Under the stricter fresh-process definition (every shared
  primitive cold, import excluded) the first overview costs **≈ 472 ms: not met**; 213 ms of it is the first
  prospective assessment, which lives in the research script `scripts/check_t1_later_snapshot.py` (pandas reads of
  SATCAT CSVs) and was not changed because it is outside the approved scope; git (58), run-list fingerprinting (55)
  and the catalogue load (64) are the rest. Python import adds ~546 ms before any request in either definition.
* **Peak RSS 250 MB.** Harness A peak **235 MB: met**. Harness B, which additionally streams the twin-state
  archive (+38 MB) and renders an object page (+26 MB for three run tables and their indexes), peaks at **274 MB:
  not met** under that broader sequence; the process sits at 132 MB after imports (pandas 92 MB) and 185 MB after
  the overview. Removing pandas or the twin-state streaming cache would be a broad change and was not attempted.
* Targets were **not** changed. P3-B overhead is quantified above (one-off 108 ms digest, 1.5 s first
  twin-state request, +9 ms warm per object request, +38 MB when the twin-state page has been visited).

## 11. Known limitations

1. The console's equivalence uses the run's **tables** (per-object abstention reasons are not tabulated by the
   pipeline, so an object absent from a table is "abstained; reason not tabulated"); the orchestrator module uses
   the live outputs and carries the reasons. Both use the same comparator.
2. The operator-controlled abstention **representation difference** (§7) is recorded as not comparable, not
   resolved.
3. Selection validates the first record only; full integrity is the streaming pass (≈ 1.4 s for 31,396 records),
   computed on the first `/api/twin-state` request and cached by file identity.
4. The current latest run (`run_20261108T083402Z`) predates the `twin_state` module, so object pages report the
   capability "versioned twin state" as `archived_only` for that run (correct, and tested); a run carrying the
   module exists only in a deleted temporary directory. **Producing a new run under `outputs/pipeline/` needs approval.**
5. Fresh-process cold overview ≈ 472 ms and sequence peak 274 MB remain above the targets (§10).
6. The row indexes add ≈ 9 MB RSS once an object page has been served; the historical 1.1 manifest is re-parsed
   on demand (~30 ms) when its run page is opened.
7. The `api` family moved to 1.2 (additive); any external reader pinned to `api/1.1` should accept 1.2.

## 12. Protected artifact integrity (after)

| Check | Result |
|---|---|
| Protected artifacts | all OK — `outputs/audit/protected_artifacts_p3b_after_20261108T120018+0000.json` |
| Archived / re-emitted twin state | `19a1fede1fd4871f…` / `6bb4871f7dedfcf1…` **unchanged**; 31,396 records each |
| Forecast table | `b15644aab581cd05…` unchanged |
| Historical 5.2 MB manifest | 5,226,140 bytes, mtime 07:28:08 UTC, sha `2cd815c0…` **unchanged** |
| Latest run manifest and seven tables | hashes identical to the baseline list |
| Run directories | **87** (unchanged; the verification run was written to a temporary directory and deleted) |
| Git | HEAD `78ee339`, branch unchanged, 0 staged; **no tracked file was touched by P3-B** (the console, adapters, schema and scripts are untracked on this branch; the 18 modified tracked files pre-date P3-B) |
| Untracked files written or modified by P3-B | `cosmos/ai/twin/reader.py`, `cosmos/ai/twin/modules.py` (new); `cosmos/ai/adapters.py`, `cosmos/ai/schema.py`, `cosmos/product/store.py`, `cosmos/product/api.py`, templates `base.html`, `object.html`, `twin_state.html` (new); `scripts/run_pipeline.py`, `scripts/twin_state_integrity.py` (new), `scripts/profile_console_cold.py` (new); tests `test_p3b_twin_state.py`, `test_p3b_chain_unchanged.py`, `test_p3b_performance.py` (new), `test_p1_schema.py` (api 1.2 pins), `test_p3a_manifest.py` (cache expectation); docs `SCHEMA_VERSIONING.md`, `CONSOLE_LAUNCH.md`, `DEMONSTRATION_PROTOCOL.md`, `COSMOS_AI_ARCHITECTURE_INTEGRATION_AUDIT.md` (addendum), this report, tracker |

## 13. Features that remain independent, archived-only, blocked or unavailable

| Feature | Status | Why |
|---|---|---|
| Catalogue chain (elements, lifetime, re-entry, decision priority) | implemented, archived evidence | reads the dated forecast table; unchanged |
| Twin-state root (`twin_state`, `twin_equivalence`) | **implemented, archived evidence** | reads the re-emitted archive (or the labelled 1.0 fallback); nothing regenerated; model version unavailable |
| Twin state for runs predating the module | archived-only | not read by those runs; reported as such |
| Telemetry anomaly evidence (ESA-ADB) | benchmark-only, independent | anonymised missions; no identity linkage to any object |
| Conjunction / collision risk (Kelvins CAC) | benchmark-only, independent | anonymised events; none attributable |
| Debris detections (SpotGEO) | benchmark-only, independent | pixel positions without identity or time |
| Health ↔ object, collision ↔ object linkage | blocked | no executable identity-linkage evidence |
| Spacecraft subsystem health, impact location / footprint, live feeds, operational control | unavailable | not determinable from the archives; none connected |
| Prospective (dated-forecast) evaluation | BLOCKED | no later snapshot ingested (download not authorised) |
| Model version / model digest | unavailable everywhere | no fitted model is persisted; never inferred |
| New pipeline run under `outputs/pipeline/`, P3-C, P3-D, P4, Phase 9 | not authorised | awaiting the owner's approval |

Work stops here.
