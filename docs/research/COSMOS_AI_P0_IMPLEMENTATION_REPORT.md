# COSMOS-AI — P0 engineering implementation report (2026-11-08)

Scope: the five P0 items of `COSMOS_AI_ARCHITECTURE_INTEGRATION_AUDIT.md` §7. Nothing scientific
changed: no interval was recalibrated, no model trained or run, no benchmark score regenerated, no
frozen or protected artifact touched, no manuscript or thesis file opened for writing, nothing
committed. HEAD `78ee339` throughout.

## 1. Baseline and integrity

| Check | Before (06:44 UTC) | After (06:56 UTC) |
|---|---|---|
| Protected artifacts (ESA-ADB freezes 28/28 and 27/28-expected, G5d, figure release 107/107, OPS-SAT archive 10/10, twin digests) | all OK — `outputs/audit/protected_artifacts_p0_before_20261108T064434+0000.json` | all OK — `outputs/audit/protected_artifacts_p0_after_20261108T065601+0000.json` |
| Accepted gate record | `83b1150215020e0e…` / `86ae2e8c828e3e18…` | unchanged |
| Git | HEAD `78ee339`, 0 staged | HEAD `78ee339`, 0 staged |
| Test suite | 352 passed, 3 skipped (start of day) | **371 passed, 3 skipped** in 58.5 s (`outputs/audit/pytest_full_20261108_p0.log`); `outputs/pipeline/` unchanged (85 run directories) |

## 2. What was implemented

### P0.1 — Subgroup-coverage reliability cue (X6 Stage 1 evidence)

* `cosmos/product/store.py`: `AM_DESIGN_STAGE1` (path of the X6 record), `AM_SOURCE_LABELS`
  (design / class_prior_sbm / class_prior_design / **unknown**), `ArtifactStore.subgroup_coverage_evidence()`
  (reads the record; `None` when absent), `subgroup_coverage_cue(am_source, evidence)`.
  `object_record` now sets `physical.area_to_mass_source` to the recorded code or **`"unknown"`**
  (never inferred), adds `physical.area_to_mass_source_label`, and attaches
  `lifetime.subgroup_coverage` with: the object's subgroup, `design_derived`, the observed coverage
  of the deployed interval construction (`cosmos_gated`) for that subgroup at **both** archived
  evaluation origins and both levels — e.g. design-derived, origin 2016, 80 %: **0.5625 (95 % CI
  0.512–0.614, n = 656) against nominal 0.80**; origin 2011: 0.7921 — the nominal level, an
  `under_coverage_flag` (design-derived and the 80 % CI entirely below nominal), and three fixed
  sentences: *evidence* ("observed subgroup-level coverage … descriptive evidence, not a causal
  explanation"), *not_individual* ("not this object's probability of being covered"), *scope*
  ("the deployed 2026-10-27 snapshot has no outcomes … nothing is extrapolated to it or to other
  datasets"). Interval values are untouched.
* `templates/object.html`: the cue renders under the lifetime interval (`SUBGROUP UNDER-COVERAGE` /
  `SUBGROUP COVERAGE` / `NO SUBGROUP EVIDENCE`), and the physical-properties row shows the source
  code with its label.
* `cosmos/product/reports.py`: the report's `uncertainty.lifetime` sentence carries the observed
  figures; a dynamic limitation is appended for design-derived objects (or for unknown source); the
  HTML report gains a "subgroup coverage evidence" table and a banner.
* Unknown source → "unknown (not recorded in the snapshot; not inferred)", no figures.
  Missing evidence file → explicit absence, no figures.

### P0.2 — Lineage and model version, honestly

* `scripts/run_pipeline.py::_module_manifest`: every module with provenance now also records a
  `lineage` block with four separate notions — `code_version.git_commit`,
  `configuration_version.config_sha256`, `data_artifacts` (SHA-256 of every file read, or the
  upstream outputs a derived module used), and `model_version` with
  `status "unavailable"`, `digest null`, the reason ("no fitted model is persisted for this
  module; its values were read from the archived prediction artifact(s)"), `registry_card null`
  and the note that none is inferred. `model_digest` is written only when a provenance actually
  carries one (none does today).
* `cosmos/product/store.py`: `lineage_for_module(record)` derives the same block for **old**
  manifests, reporting "unavailable" for anything not recorded; `model_version_unavailable()`;
  `VERIFIED_MODEL_CARD_ASSOCIATIONS = {}` and `registry_association()` — the explicit, empty table
  of verified output→card relationships. The object record's provenance gains `model_version`.
* `cosmos/product/api.py`: `GET /api/runs/{id}` returns `lineage` and `evidence_class` per module
  (computed; the manifest file is never rewritten); the run page shows a "Evidence class and
  lineage per module" table with `UNAVAILABLE` badges; `GET /api/datasets` gains per-dataset
  `evidence_class` and an `evidence_policy` block.
* `cosmos/product/reports.py`: provenance block gains `model_version` and a `lineage_note` that
  names the four notions as distinct; `git_commit` falls back to "unavailable".
* No `Provenance` dataclass change; adapters unchanged.

### P0.3 — Wording

* `cosmos/ai/registry.py`: every OPS-SAT card states it is a benchmark arm, not a spacecraft health
  assessment; the `opssat_hybrid` card carries the E6/X10 finding verbatim (ECE advantage over
  CNN-only only; not better than the feature-MLP branch; Brier n.s.; stability claim not
  reproduced; **no fusion contribution claimed**). No card or template contains an unqualified
  "fusion improves/contributes" statement (tested).
* `templates/overview.html`: new paragraphs — COSMOS-AI is a **read-only evidence twin** (no model
  at prediction time, no live telemetry/tracking/CDM feed); telemetry, conjunction and imagery are
  **independent benchmark roots**, not combined into a health assessment; the console serves
  **archived real-data evaluations only**, and the legacy chain's **synthetic demonstration data** is
  never mixed in.
* `templates/run.html`: evidence class per module ("health: archived benchmark-arm detection scores
  — not a spacecraft health state", …).
* X4 and X6 wording checked in the research documents (exploratory / Mission-1 AR(8)-specific;
  descriptive, not causal); the console carries the X6 cue with that wording and never mentions X4.

### P0.4 — Launch path

* `scripts/check_console_prerequisites.py` (read-only): Python version, required packages,
  required artifacts, optional artifacts (each with its degradation), optional backends flagged
  `needed_to_serve_console: False`; prints the launch command and URL; exit 0 ⇔ launchable.
  Result here: launchable; absent optional backends `statsmodels, lightgbm, catboost, tabm,
  tabicl, kumo, pymsis` (not installed — none is needed to serve).
* `docs/product/CONSOLE_LAUNCH.md` (new) and a pointer in `PRODUCT_USER_GUIDE.md` §Starting it.

**Launch:** `python scripts/check_console_prerequisites.py && python scripts/serve_console.py` →
<http://127.0.0.1:8070/> (API docs `/docs`).

### P0.5 — Score-cache preservation

* Finding: `.gitignore` line 31 (`*.npy`) ignores the regenerated AR(8) caches
  (`track3b_stage2/oof_regen/m1_target_ar8/scores_{train_oof,test}.npy`, 1.7 GB each) and the
  seven per-cell alarm bitmaps (0.9 MB each).
* Strategy implemented (narrowest safe): the two large arrays **stay ignored**; they are preserved by
  `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/SCORE_CACHE_MANIFEST.json` (size and SHA-256
  of all 14 files, 3.42 GB) written by `scripts/score_cache_manifest.py` (`--verify` re-checks), by
  the deterministic regeneration recipe recorded in it (frozen `oof.run(1, 'target')`, 353 s,
  archived sample hash `02455519984c` reproduced), and by one narrow `.gitignore` exception for the
  small alarm bitmaps (`!…/track3b_stage2/alarms/**/*.npy`, 6.4 MB total). Ordinary pipeline
  outputs and other generated arrays are unaffected (tested with `git check-ignore`). Nothing was
  committed; no external copy was made (an off-repository copy of the 3.4 GB remains an option for
  you to approve).

## 3. Tests added (19, all passing) and full-suite result

| File | Covers requirement |
|---|---|
| `tests/test_p0_subgroup_coverage.py` (5) | 1 design-derived warning; 2 unknown source; 3 coverage values and CI rendering (API, page, report) |
| `tests/test_p0_lineage.py` (5) | 4 missing model digest; 5 incomplete provenance (empty / partial / synthetic run without git); 6 registry association safeguard |
| `tests/test_p0_wording.py` (4) | 7 K8 wording; 8 archived vs synthetic labels; no positive live-feed claim in any template |
| `tests/test_console_launch.py` (3) | 9 launch prerequisites, document and server defaults |
| `tests/test_score_cache_preservation.py` (2) | 10 manifest verification and narrow ignore rules |

Full suite: **371 passed, 3 skipped** (`outputs/audit/pytest_full_20261108_p0.log`).

## 4. Files changed

| File | Change |
|---|---|
| `cosmos/product/store.py` | constants, `subgroup_coverage_evidence`, `subgroup_coverage_cue`, `lineage_for_module`, `model_version_unavailable`, `registry_association`, `MODULE_EVIDENCE_CLASS`; `object_record` additions |
| `cosmos/product/api.py` | lineage + evidence class in `/api/runs/{id}` and the run page; evidence policy in `/api/datasets` |
| `cosmos/product/reports.py` | subgroup sentence/limitations/table; model version and lineage note in provenance |
| `cosmos/product/templates/{object,run,overview}.html` | cue, lineage table, framing paragraphs |
| `cosmos/ai/registry.py` | OPS-SAT card limitations (benchmark-arm statement; X10 qualification on `opssat_hybrid`) |
| `scripts/run_pipeline.py` | per-module `lineage` block in `run_manifest.json` |
| `scripts/check_console_prerequisites.py`, `scripts/score_cache_manifest.py` | new |
| `docs/product/CONSOLE_LAUNCH.md` (new), `docs/product/PRODUCT_USER_GUIDE.md` | launch path |
| `.gitignore` | one narrow exception + comment |
| `outputs/benchmarks/telemetry_esa_adb/track3b_stage2/SCORE_CACHE_MANIFEST.json` | new record |
| `tests/test_p0_*.py`, `tests/test_console_launch.py`, `tests/test_score_cache_preservation.py` | new |

Not changed: adapters, contracts, orchestrator, any study code, any archive, any frozen file.

## 5. Residual limitations after P0

Model version remains **unavailable** everywhere, truthfully — making it available needs persisted
models (P1.3). The cue reports coverage of the interval *construction* at the evaluation origins;
the deployed snapshot's own coverage is unmeasurable until outcomes exist. The console still does
not show the 30-day-horizon interval straddle in the ranking (P1.1) or snapshot age at object level
(P1.5). `statsmodels` and the learner backends remain absent.

## 6. Proposed P1 plan (not executed)

| # | Task | Files / functions | Depends on | Tests | Acceptance | Risk | Effort |
|---|---|---|---|---|---|---|---|
| P1.1 | Interval-vs-horizon cue in the ranking, display only | `adapters.decision_priority` (+`q05_days`, `q95_days`, `interval_straddles_30d`), `run_pipeline._write_tables`, `templates/run.html`, `reports.py` | — | extend `test_twin_uncertainty_audit` (priority formula unchanged), new column test | priority byte-identical; 23/50 straddle figure reproduced on the full run | low | 0.5 d |
| P1.2 | Twin-state re-emission with provenance (no refit) | `cosmos/ai/twin/engine.py` → factor `emit_state(table, out_dir)`; `--out` | forecast table | by-value equality with the archive except `provenance`; archive untouched | low | 1 d |
| P1.3 | Persist fitted models in future study runs + model digest | `conjunction/run.py`, `lifetime/run.py` (xgboost/mlp/persistence only; absent backends recorded as such), `adapters._provenance` (`model_digest` when a model file exists) | none for available backends | round-trip reproduces archived predictions; manifest `model_version.status == "recorded"` | none to archives | 2–3 d |
| P1.4 | Schema versioning | `adapters._load_snapshot` (`SNAPSHOT_SCHEMA`), `run_pipeline` manifest `schema_version`, `store` readers | P0.2 | `test_schema_drift…` + version-mismatch case | low | 0.5 d |
| P1.5 | Object-level freshness | `store.object_record` (`snapshot_age`), `object.html`, `reports.py` | overview code | `test_console_staleness` extended | none | 0.25 d |
| P1.6 | Health screen semantics in the run directory | label consumers of `health_benchmark_arms.csv`; overview `module_status` label | — | `test_01b`, `test_08` extended | none | 0.25 d |

P1 starts only on your instruction.
