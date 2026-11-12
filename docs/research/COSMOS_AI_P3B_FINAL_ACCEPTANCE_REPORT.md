# COSMOS-AI — P3-B final acceptance: fresh pipeline run with the twin-state evidence root (2026-11-08)

Scope executed, as approved: baseline checks, **one** fresh pipeline run with the documented command, validation
of the twin-state modules in the actual latest output, the semantic-consistency audit, acceptance checks,
performance under both definitions, and this report. No commit, push, merge, rebase, reset, clean or discard; no
frozen artifact, pre-registration, manuscript or thesis touched; no retraining, download, methodology change or
additional run; P3-C, P3-D, P4 and Phase 9 not started. Work stops here pending explicit approval.

## 1. Baseline (12:14 UTC, before the run)

| Item | Value |
|---|---|
| Git | HEAD `78ee33962007203bcfc829fc743a663b350373e1`, branch `product/mission-intelligence-console`, 0 staged, 18 modified tracked files (pre-existing), 258 untracked paths |
| Protected artifacts | all OK — `outputs/audit/protected_artifacts_p3b_fresh_before_20261108T121432+0000.json` |
| Archived / re-emitted twin state | `19a1fede1fd4871f…` / `6bb4871f7dedfcf1…`; 31,396 records each |
| Forecast table | `b15644aab581cd05…` |
| Historical manifest `run_20261108T072802Z` | 5,226,140 bytes, mtime 07:28:08 UTC, sha `2cd815c0121a8a65…` |
| Seven tables of `run_20261108T083402Z` | full SHA-256 recorded in `outputs/audit/seven_tables_sha256_run_20261108T083402Z.json`; byte-identical to `run_20261108T072802Z` |
| Run directories | **87** |
| Approved command (from `docs/product/DEMONSTRATION_PROTOCOL.md` §1) | `python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh` — default `--twin-source-policy prefer_reemitted`; module graph lists the nine modules including `twin_state` (root) and `twin_equivalence` |

## 2. Fresh run

| Item | Value |
|---|---|
| Run id | **`run_20261108T121517Z`** — 9.0 s wall, all nine modules `success` |
| Manifest | **`run_manifest/1.2`** (validated), 23,191 bytes, sha **`98b7350ff311714b6d5d2b1a10844563cbe33cc0c5dbbc39e9cffc71ab10832a`** |
| Configuration | identical to the previous run plus `twin_source_policy: prefer_reemitted` |
| Tables | the seven catalogue-chain / benchmark tables **byte-identical** to `run_20261108T083402Z` (and therefore to `run_20261108T072802Z`); new `twin_equivalence.csv` (31,396 rows, all `equal`) |
| Priority rule | identical to the previous manifest |
| Run directories after | **88** |

### 2.1 `twin_state` module record (manifest `modules.twin_state`)

| Field | Recorded value |
|---|---|
| status | success |
| source / selection_status / policy / fallback_used | **reemitted / primary / prefer_reemitted / false** — "re-emitted twin_state/1.1 archive present and valid (preferred source)" |
| schema_version · original_or_reemitted | twin_state/1.1 · reemitted |
| artifact | `outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl` |
| artifact_sha256 = artifact_recorded_sha256 | `6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84` — digest_state **verified** |
| transformation_digest_sha256 · method · code revision | `da9724148c7d056d…` · `cosmos.ai.twin.reemit.emit_records v1 (row-wise mapping of forecast_table.csv.gz; no model executed)` · `78ee339…` |
| record_count / recorded / state | 31,396 / 31,396 / matches |
| provenance_on_outputs · provenance_complete | true · true |
| predictions_regenerated · model_executed · model_version_status | **false · false · unavailable** |
| integrity | status ok; 31,396 total, 31,396 valid, 0 malformed, 0 schema-invalid, 0 duplicates, 0 value problems; `twin_state/1.1: 31396` |
| lineage.model_version | `unavailable` — "no fitted model is persisted for this module …"; `data_artifacts` = the archive digest |

Re-emission is recorded as a row-wise mapping of the archived forecast table with no model executed; nothing in
the manifest, API or console presents it as fresh model inference. A fallback would have been recorded as
`source: archived, selection_status: fallback, fallback_used: true` with the reason (exercised by tests).

### 2.2 `twin_equivalence` module record

| Field | Recorded value |
|---|---|
| status | success; upstream `twin_state, catalogue_state, lifetime, reentry`; data artifacts = twin archive digest + forecast table digest; model_version unavailable |
| twin_records / records_compared / equal / different | 31,396 / **31,396 / 31,396 / 0** |
| records_not_comparable / missing_in_chain / missing_in_twin | 0 / 0 / 0 |
| fields_compared / equal / different | 452,690 / 452,690 / 0 → `equivalent: true` |
| not_comparable_reasons_summary | operator-controlled abstention representation (16,386) · no chain time quantiles for those objects (16,386) · lifetime abstained, per-horizon probabilities not monotone (123) |

## 3. Semantic consistency audit

**Operator-controlled payloads (16,386 objects; e.g. ISS, NORAD 25544).** The twin record's `reentry` output
is `abstain: true`, model "previous-window payload base rate", reason "operational payload: operator-controlled
regime, drag physics does not determine re-entry (C3)", with the base-rate probabilities and the drag-only
probabilities attached. The chain's `reentry_predictions.csv` row for the same object carries those same
probabilities (p₃₀ 0.005277, p₉₀ 0.015774, p₁yr 0.077723) as a prediction, `uncertainty_kind: score`, regime as
an assumption; the object record states "operator-controlled payload: drag physics does not determine re-entry,
so no drag forecast is given". Neither representation was rewritten. The comparator reports
`reentry.abstained` as **not comparable** with the reason "representations differ, values are compared", and the
probabilities as compared and equal (10 of 10 shared values). `twin_equivalence.csv` row NORAD-25544:
`status equal, fields 10/10, not_comparable_fields reentry.abstained;reentry.time_quantiles`. The API
(`/api/objects/25544/twin`, `/api/twin-state`), the object page ("ABSTAIN … Not compared: reentry.abstained
(…representations differ…)") and the Twin State page ("Fields not compared, by reason") all show it.

**Numerical agreement is not presented as semantic agreement.** The `equivalent` flag is defined as "0 records
different among records with at least one shared value"; the Twin State page and API carry 32,895 field-level
not-comparable entries with reasons beside it and the sentence "fields with differing semantics are listed as not
comparable, not forced equal".

**123 non-coherent lifetime records (L17).** Kept as a separate limitation on every surface: manifest
`lifetime.abstentions` (123 "not monotone across horizons"), `noncoherent_horizon_probabilities: 123`,
`lifetime_noncoherent_horizons.csv`, the overview ABSTAIN finding, the `twin_equivalence` reason (123), and the
Twin State page / API. One correction was made in this step: the console's tables path previously attributed
these 123 only as "abstained in the run; reason not tabulated"; it now reads the run's own
`lifetime_noncoherent_horizons.csv` and states the L17 reason (`reader.L17_REASON`), on the whole-archive and the
per-object paths alike. No value changed; the test
`test_non_comparable_and_missing_records_are_reported_separately` asserts the 123 (L17) and the 16,386 (C3)
as distinct reasons and the table in `chain_tables`.

## 4. Fresh-run acceptance

| Check | Result |
|---|---|
| Latest run | `ArtifactStore.latest_run_id()`, `/api/ready.latest_run`, `/api/overview`, `/api/runs[0]` → **`run_20261108T121517Z`** (88 runs) |
| Both twin modules present and successful | yes (manifest, `/api/runs/{id}` lineage with nine modules, run page shows both with their evidence classes) |
| Source selection and validation recorded | yes (§2.1) |
| Equivalence computed and reported | yes (§2.2; API/page/`twin_equivalence.csv`) |
| Seven tables unchanged | byte-identical to `run_20261108T083402Z`; that run's tables unchanged since baseline (full hashes) |
| D1–D14 | **14 passed** — `outputs/audit/pytest_demo_20261108_p3b_fresh.log` |
| P3-A tests | **27 passed** — `outputs/audit/pytest_p3a_20261108_p3b_fresh.log` |
| P3-B tests | **28 passed** — `outputs/audit/pytest_p3b_20261108_fresh.log` |
| Full suite | **455 passed, 3 skipped**, exit 0 — `outputs/audit/pytest_full_20261108_p3b_fresh.log` |
| Console | overview 200 (latest = fresh run, all nine module statuses), object 37607 (decision priority and twin equivalence both on the fresh run; `EQUAL 20 of 20`), object 25544 (abstention and representation note), ranking (25 rows, rank 1 NORAD-32730, run id = fresh run), run view 24.7 kB, run page, Twin State page (`RE-EMITTED · twin_state/1.1 · verified`, both reasons listed), `archived_only` policy page amber |
| Capability row "versioned twin state" | now **implemented**: "read by the runtime pipeline as an additional evidence root: source reemitted (twin_state/1.1), digest verified, 31396 records; run-time equivalence with the catalogue chain: 31396 of 31396 compared records equal, 0 not comparable, 0 different" |
| Live-feed / on-demand inference claims | 0 hits on `/`, `/objects/37607`, `/objects/25544`, the run page, `/twin-state`, the report; downloads redacted |

## 5. Performance — both definitions retained

**Benchmark sequence** (`scripts/benchmark_console.py --label p3b_fresh`, one process, overview API probe
before the page probe — the definition under which the original 446 ms / 286 MB were reported):

| Probe | P3-A final | P3-B final | **Fresh run (this step)** | Target |
|---|---|---|---|---|
| Overview page cold / warm | 446 / 37 ms | 56 / 27 ms | **61 / 26 ms** | 400 ms — met under this definition |
| Overview API cold / warm | 436 / 26 ms | 464 / 32 ms | 460 / 22 ms | — |
| Object API cold / warm | 119 / 28 ms | 279 / 37 ms | 284 / 29 ms | — |
| Twin API 25544 | 10 ms | 28 ms | 26 ms | — |
| Run manifest API (latest) | 17.7 kB | 17.7 kB | 24.7 kB (nine modules) | — |
| Peak RSS | 286 MB | 235 MB | **234 MB** | 250 MB — met under this definition |

**Fresh process** (`scripts/profile_console_cold.py --runs 5 --label p3b_fresh`, medians, uninstrumented; one
separate traced run for attribution):

| Step | ms | RSS after |
|---|---|---|
| import `cosmos.product.api` | 547 | 132 MB |
| git + digest · run list · **first prospective assessment** · catalogue · manifest · telemetry metadata | 58 · 53 · **192** · 58 · 3 · 10 | 181 MB |
| first `GET /` remaining | 65 | 184 MB |
| **first-overview path (sum, import excluded)** | **≈ 439 ms** | — |
| P3-B twin selection (once per process) | 100 | — |
| first `/api/twin-state` (streams the archive) | 1,504 | 225 MB |
| object page first / warm | 146 / 37 | 245 MB |
| RSS peak over the sequence (includes twin-state streaming) | — | **278 MB** |

Verdict, stated plainly: under the benchmark definition both targets are met (61 ms, 234 MB). Under the
fresh-process definition the first overview costs ≈ 439 ms (**not** met; the first prospective assessment is
192 ms of it) and the sequence including twin-state streaming peaks at 278 MB (**not** met). Neither definition
replaces the other, the targets were not changed, the prospective-assessment research script was not modified
and no broad performance change was made. Records: `outputs/audit/console_benchmark_p3b_fresh_20261108T121847+0000.json`,
`outputs/audit/console_cold_profile_p3b_fresh_20261108T121916+0000.json`.

## 6. Integrity after

| Check | Result |
|---|---|
| Protected artifacts | all OK — `outputs/audit/protected_artifacts_p3b_fresh_after_20261108T122145+0000.json` |
| Archived / re-emitted twin state | `19a1fede1fd4871f…` / `6bb4871f7dedfcf1…` unchanged |
| Forecast table | `b15644aab581cd05…` unchanged |
| Historical 5.2 MB manifest | 5,226,140 bytes, mtime 07:28:08 UTC, sha `2cd815c0…` unchanged |
| Seven tables of `run_20261108T083402Z` | unchanged (full hashes) |
| Run directories | **88** = 87 + the one approved run |
| Git | HEAD `78ee339`, 0 staged; no tracked file touched in this step |
| Files changed in this step (untracked) | `cosmos/ai/twin/reader.py` (L17 attribution; `L17_REASON`, `noncoherent` parameter), `cosmos/product/store.py` (reads `lifetime_noncoherent_horizons.csv` on both paths), `tests/test_p3b_twin_state.py` (assertions), this report, tracker |

## 7. Outstanding limitations

1. The operator-controlled payload **representation difference** between the twin engine (C3 abstention with
   base-rate values) and the runtime chain (prediction under a regime assumption) remains; values agree. Aligning
   the two is a methodological decision for the owner; nothing was rewritten here.
2. The 123 non-coherent lifetime records (L17) remain a stated limitation of the saved per-horizon calibration.
3. Fresh-process cold overview ≈ 439 ms and sequence peak 278 MB with twin-state streaming remain above the
   targets; the dominant items (prospective assessment script, pandas import) are outside the approved scope.
4. The first `/api/twin-state` request streams the 78 MB archive (≈ 1.5 s), then is cached by file identity.
5. The console's per-object abstention reasons are read from run tables; apart from the L17 list, abstention
   reasons are not tabulated per object by the pipeline and are reported as such.
6. Model version is unavailable everywhere; no fitted model is persisted, none inferred.

Work stops here. P3-C, P3-D, P4, any further run and Phase 9 await explicit approval.
