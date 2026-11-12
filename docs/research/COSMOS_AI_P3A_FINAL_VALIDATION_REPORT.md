# COSMOS-AI — P3-A final validation and fresh demonstration run (2026-11-08)

Scope executed, as approved: pre-run integrity verification, **one** fresh demonstration run with the
documented command, end-to-end validation, the `X-Request-ID` header correction, repeated performance
measurements against the **original** targets, and this report. Nothing from P3-B, P3-C, P3-D, P4 or
Phase 9 was started. No commit, push, merge, rebase, reset or clean; no dependency installed, no data
downloaded, no model trained, no twin-state archive regenerated, no scientific method, prediction or
ranking calculation altered. Work stops here pending explicit approval.

## 1. Git and working tree

| Item | Start of this step (08:33 UTC) | End (08:38 UTC) |
|---|---|---|
| HEAD | `78ee33962007203bcfc829fc743a663b350373e1` | unchanged |
| Staged paths | 0 | 0 |
| Modified tracked files | 18 (all pre-existing, uncommitted by instruction) | same set |
| Untracked paths | 251 | + the new run directory, this report, and the audit records listed below |

## 2. Pre-run integrity (before the fresh run)

| Check | Result | Record |
|---|---|---|
| Protected artifacts (ESA-ADB freezes 28/28, G5d, figure release 107/107, OPS-SAT 10/10, twin digests, gate record) | all OK | `outputs/audit/protected_artifacts_p3a_final_before_20261108T083319+0000.json` |
| Archived twin state `outputs/twin/as_of_2026-10-27/twins.jsonl` | sha `19a1fede1fd4871f380ff802f285d2ad03732f6cd3179790e67336c7d202a6b5`; **31,396 records** | matches `FORECAST_SHA256.txt` |
| Re-emitted twin state `outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl` | sha `6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84`; **31,396 records** | matches `TWINS_SHA256.txt` |
| Forecast table | sha `b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86` | — |
| Historical manifest `outputs/pipeline/run_20261108T072802Z/run_manifest.json` | 5,226,140 bytes, mtime 2026-11-08 07:28:08 UTC, sha `2cd815c0121a8a652df80e41569a1ee6216de40d6246528b2f0e32cddf05c90f` | — |
| Run directories | **86** | — |

## 3. Fresh demonstration run

Command (from `docs/product/DEMONSTRATION_PROTOCOL.md` §1, unchanged):

```bash
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh
```

| Item | Value |
|---|---|
| Run id | **`run_20261108T083402Z`** (`outputs/pipeline/run_20261108T083402Z/`) |
| Wall time | 7.3 s; all seven modules `success`; seven tables written |
| Manifest | **16,311 bytes**, sha `2fa3475d91857ee8df1990ded7733ff9e2354dc10353b54b1e20f80753e0e0bd` |
| Schema | `run_manifest/1.2`; `validate_run_manifest` → `1.2` |
| Configuration | `{as_of: 2026-10-27, limit: null, collision_limit: null, debris_sequence_limit: null, health_calibrator: conformal_bh, collision_model: cosmos_gated}` — **identical** to the historical run's configuration |
| Priority rule | `decision_priority.outputs.priority_rule` **identical** (dict equality) to the historical manifest's |
| Lineage | present for all seven modules; `code_version.git_commit = 78ee339…` |
| Console | `ArtifactStore.latest_run_id()` → `run_20261108T083402Z`; `/api/ready.latest_run`, `/api/overview` latest run and `/api/runs[0]` all name it; 87 runs listed |

Compact representations of every dictionary output in the new manifest (verified programmatically):

| Module.output | Form |
|---|---|
| catalogue_state.{elements, characteristics, object_class, regime, name} | `{count: 31396}` |
| lifetime.{lifetime, abstained, noncoherent_horizon_probabilities} | `{count: 13115}`, `{count: 18281}`, `{count: 123}` |
| reentry.{reentry, abstained} | `{count: 31396}`, `{count: 0}` |
| collision.collision · health.health · debris.detections | `{count: 2167}` · `{count: 36}` · `{count: 283026}` |
| decision_priority.ranking | table summary `{rows: 31396, columns: [10 names]}` |
| decision_priority.health_escalation | evidence record `{module, status: abstain, reason}` |
| decision_priority.priority_rule | **verbatim** (the only allow-listed key) |

**Scientific outputs unchanged.** All seven tables of the fresh run are **byte-identical** (SHA-256) to
those of the historical run `run_20261108T072802Z`: `collision_risk.csv`, `debris_detections.csv`,
`decision_ranking.csv`, `health_benchmark_arms.csv`, `lifetime_estimates.csv`,
`lifetime_noncoherent_horizons.csv`, `reentry_predictions.csv`. The serialisation change touched only
the manifest.

## 4. End-to-end validation (final code, real archive, TestClient)

| Check | Result |
|---|---|
| D1–D14 demonstration protocol | **14 passed** (`outputs/audit/pytest_demo_20261108_p3a_final.log`) |
| Wording audit (`tests/test_p0_wording.py`) and observability tests | 15 passed |
| Overview | API 200 (latest run = fresh run; snapshot age 12 d, **STALE** flagged); page 200, 18.8 kB |
| Object details (NORAD 37607) | API 200, `object_record/1.1`; evidence-availability strip present with statuses `implemented` / `archived_only` / `benchmark_only` …; model version `unavailable`; page 200 |
| Ranking (fresh run, 25 rows) | 200; rank 1 NORAD-32730 BLOCK DM-SL R/B, p₃₀ = 1.0, mass 12,900 kg, priority 2.0, horizon relation attached |
| Twin-state retrieval (37607) | `source: reemitted`, `twin_state/1.1`, `fallback.used: false`, `predictions_regenerated: false`, recorded sha `6bb4871f…` |
| Archived vs re-emitted value equivalence | **re-computed** with `reemit.compare_with_archive` on the two files: 31,396 compared, 31,396 equal, 0 differing, 0 extra either side (1.4 s) — `outputs/audit/p3a_final_twin_equivalence.json` |
| Latest run through the API | `/api/runs/run_20261108T083402Z` 200, **17.7 kB** (historical run: 3,787.5 kB); run page **39.7 kB** (historical: 5,127.5 kB); lineage for all seven modules |
| Live-feed / on-demand inference claims | rendered `/`, `/objects/{37607, 23806, 25544, 12}`, `/runs/<fresh>`, `/reports/object/37607` scanned for positive claims (live feed connected, real-time inference, computed live, model runs at request time, on-demand inference): **0 hits**; the truthful negations are present on the overview, object and report pages |
| Historical manifest | unchanged (same size, mtime and sha as §2) |

Probe record: `outputs/audit/p3a_final_validation_probes.json`.

## 5. P3-A3 request-ID header correction

Implemented without architectural change: the existing generic `Exception` handler now sets
`X-Request-ID` on the response it builds (the middleware cannot, because the exception leaves it before
the header step). The generic body is retained; the HTML error page additionally shows "Request id …" in
its detail line so a user can quote it; tracebacks stay exclusively in the server log under the same id.

| Test | Result |
|---|---|
| Success: header present (generated 16-hex) and a client-supplied id echoed | pass |
| Unexpected error, JSON: 500, header = body `request_id` = client-supplied id; no secret string, no traceback | pass |
| Unexpected error, HTML: 500, header set and shown in the page; no traceback | pass |
| Server log carries the traceback and the same request id | pass |
| Readiness on an empty root: still **503**, header present | pass |
| `DataUnavailable` 404 / `InvalidSelection` 400 unchanged | pass |

Finding during this step: the first run of the extended test showed that the HTML error page did not
display the id value (only the phrase "request id"); fixed as described above before re-running.

## 6. Performance against the original targets

Same harness (`scripts/benchmark_console.py`), same process layout, run alone each time.
Before = baseline before P3-A; After = end of P3-A implementation; Final = this step (fresh run present,
header fix in place).

| Measurement | Before | After | **Final** | Original target | Met? |
|---|---|---|---|---|---|
| Overview page, cold | 3,198 ms | 435 ms | **446 ms** | 400 ms | **No** (+46 ms) |
| Overview page, warm | 368 ms | 28 ms | 37 ms | — | — |
| Overview API, cold / warm | 485 / 345 ms | 463 / 34 ms | 436 / 26 ms | — | — |
| Peak RSS | 703 MB | 294 MB | **286 MB** | 250 MB | **No** (+36 MB) |
| Mission metadata (`missions()` cold) | 2,508 ms | 8.5 ms | 8.3 ms | no array load | yes (no `X` requested; test-enforced) |
| Manifest parse (`run_manifest`, cold / warm) | 33.4 / 31.2 ms | 0.1 / 0.1 ms | 0.1 / 0.0 ms | — | cache hit on the warm call |
| `list_runs` cold / warm | 47.1 / 35.9 ms | 50.8 / 2.9 ms | 54.3 / 3.0 ms (87 runs) | — | — |
| `repository_provenance` cold / warm | 51.0 / 49.8 ms | 48.3 / 0.3 ms | 51.0 / 0.3 ms | — | — |
| Run manifest API (latest) | 67 ms, 3,787.5 kB | 26 ms, 3,787.5 kB | **9.2 ms, 17.7 kB** | — | — |
| Run page (latest) | 222 ms, 5,127.5 kB | 183 ms, 5,127.5 kB | **84.7 ms, 39.7 kB** | — | — |
| Latest manifest on disk | 5,226,140 B | 5,226,140 B | **16,311 B** | — | — |

Records: `console_benchmark_p3a_before_20261108T080412+0000.json`,
`console_benchmark_p3a_after_20261108T081953+0000.json`,
`console_benchmark_p3a_final_20261108T083657+0000.json` (all under `outputs/audit/`).

**Remaining gaps, stated as measured.** The cold overview page is 446 ms against the 400 ms target and the
peak RSS is 286 MB against 250 MB. The cold figure is dominated by one-off first-call work that the warm
figure (37 ms) does not pay: the first git invocation (~50 ms, `repository_provenance` cold), the first
run listing with fingerprinting (~54 ms), the first prospective-status assessment (~190 ms measured during P3
planning, now cached after the first call) and the first catalogue load. The RSS peak is reached at the end
of the probe sequence (report rendering) and includes the loaded catalogue and twin index. Cold-run
measurements vary by tens of milliseconds between runs (435 vs 446 ms for the same code path); neither
figure reaches the target, and the targets were **not** changed. Closing these gaps would need work
outside the approved scope (for example pre-warming at start-up or a lighter catalogue frame) and is left
for approval.

## 7. Post-run integrity

| Check | Result |
|---|---|
| Protected artifacts | all OK — `outputs/audit/protected_artifacts_p3a_final_after_20261108T083808+0000.json` |
| Archived twin state | sha `19a1fede1fd4871f…` unchanged |
| Re-emitted twin state | sha `6bb4871f7dedfcf1…` unchanged |
| Historical manifest | 5,226,140 bytes, mtime 07:28:08 UTC, sha `2cd815c0…` unchanged |
| Run directories | **87** (86 + the one approved fresh run) |
| Diagnostics bundle | ready `true`, protected artifacts exit 0 — `outputs/audit/console_diagnostics_20261108T083808+0000.json` |
| Full test suite | **427 passed, 3 skipped** in 66 s, exit 0 — `outputs/audit/pytest_full_20261108_p3a_final.log` (P3-A end: 426 passed; +1 header test) |

## 8. Failures, limitations and deviations

1. **Performance targets not met** (§6): cold overview 446 ms vs 400 ms; peak RSS 286 MB vs 250 MB.
2. **HTML error page did not show the request id** at first; found by the new test and fixed in the same
   handler before re-running (§5).
3. `/api/runs/{id}` for the historical run still serves 3.8 MB — by design, the 1.1 record is not rewritten.
4. The fresh run's `git_commit` at the manifest top level is `null` (as in the historical run); the commit
   is recorded under each module's `lineage.code_version` — pre-existing behaviour, not changed here.
5. No manuscript, thesis, pre-registration, frozen dataset, confirmatory result or benchmark score was
   touched; the twin-state archives were read, never regenerated.

## 9. Files changed in this step

| File | Change |
|---|---|
| `cosmos/product/api.py` | `X-Request-ID` header on both 500 response forms; request id shown in the HTML error detail |
| `tests/test_p3a_observability.py` | header assertions added to the 500 test; new test `test_request_id_header_on_success_on_unexpected_error_and_on_not_ready` |
| `docs/product/DEMONSTRATION_PROTOCOL.md` | the demonstration run is now `run_20261108T083402Z` (1.2); the 1.1 run is named as the historical record |
| `docs/research/COSMOS_AI_P3A_IMPLEMENTATION_REPORT.md` | header limitation marked resolved; fresh-run item marked executed |
| `docs/research/MASTER_COMPLETION_TRACKER.md` | one row for this step |
| New artifacts | `outputs/pipeline/run_20261108T083402Z/` (the approved run); audit records named above |

Work stops here. P3-B, P3-C, P3-D, P4, the performance follow-up in §6 and Phase 9 each await explicit approval.
