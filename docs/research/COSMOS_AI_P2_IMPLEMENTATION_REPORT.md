# COSMOS-AI — P2 implementation report: console integration and demonstration readiness (2026-11-08)

Scope executed: P2.1–P2.6 of `COSMOS_AI_P2_IMPLEMENTATION_PLAN.md`, as approved, with the six additional
acceptance requirements. The system remains a **read-only evidence twin**: no model runs at request time,
no live source, no prediction regenerated, no methodology, frozen artifact or archive changed, nothing
committed. HEAD `78ee339` throughout.

## 1. Integrity verification

| Check | Before (07:24 UTC) | After (07:36 UTC) |
|---|---|---|
| Protected artifacts (ESA-ADB freezes, G5d, figure release 107/107, OPS-SAT 10/10, twin digests, gate record) | all OK — `outputs/audit/protected_artifacts_p2_before_20261108T072417+0000.json` | all OK — `outputs/audit/protected_artifacts_p2_after_20261108T073624+0000.json` |
| Archived twin state | sha `19a1fede1fd4871f…` | unchanged |
| Re-emitted twin state | sha `6bb4871f7dedfcf1…` | unchanged |
| Git | HEAD `78ee339`, 0 staged | HEAD `78ee339`, 0 staged |
| Full test suite | 386 passed, 3 skipped (after P1) | **400 passed, 3 skipped** in 83 s (`outputs/audit/pytest_full_20261108_p2.log`) |
| `outputs/pipeline/` | 85 run directories | 86: one deliberate **demonstration run** `run_20261108T072802Z` (full snapshot, `run_manifest/1.1`, records the priority rule); the test suite itself added none |

## 2. What was implemented

### P2.1 — Twin-state reader, panel and API (acceptance requirement 1)
* `store.py`: `TWIN_STATE_REEMITTED` / `TWIN_STATE_ARCHIVED` paths, `_twin_index()` (one-time byte-offset
  index per file, cached; the 78 MB file is read once, then records are fetched by seek),
  `twin_record(norad)`. The re-emitted `twin_state/1.1` record is preferred; the archived
  `twin_state/1.0` record is read **only as a labelled fallback**: `source ∈ {"reemitted","archived"}`,
  `fallback {used, reason}`, `schema_version`, `artifact`, `artifact_recorded_sha256` (from the digest
  files, never recomputed per request), `provenance_on_outputs`, `source_record`, the re-emission manifest
  subset (method, transformation digest, code revision, equivalence 31,396/31,396), `model_version:
  unavailable`. Every record is validated against the schema before use; a malformed record is reported,
  never repaired.
* `GET /api/objects/{norad}/twin`; object-page panel "Twin state" with badge `RE-EMITTED · twin_state/1.1`
  or `HISTORICAL ARCHIVE · twin_state/1.0 (fallback)`, the outputs table (module, model, validation,
  values, uncertainty, per-output provenance digests or `NONE (archived record)`), the source-row pointer
  and "no prediction was regenerated and no model executed". Report section 6a.
* Fallback verified on a synthetic root holding only the archived file (D3): API `source: "archived"`,
  `fallback.used: true`, reason names the missing re-emitted file, note "HISTORICAL ARCHIVE", page badge
  "(fallback)".

### P2.2 — Decision priority explained from the run manifest (requirement 2)
* `adapters.decision_priority` now **records** its rule as metadata in its outputs (`priority_rule`:
  formula string, inputs, `consequence_mass_kg`, `consequence_multiplier`, semantics, interval use); the
  calculation itself is unchanged (`CONSEQUENCE_MULTIPLIER = 2.0` replaces the literal; values identical —
  the determinism and priority tests pass). `run_pipeline._jsonable` keeps plain-metadata dicts verbatim
  so the manifest carries the rule.
* `store.priority_for_object(run_id, norad)`: the object's row from the run's `decision_ranking.csv`, its
  rank, the rule **from that run's manifest**, the C4 escalation record, and an explanation assembled from
  those recorded values only. For runs written before today the rule is reported **unavailable**
  ("the priority rule itself is not recorded in this run's manifest … not reconstructed here") — verified
  on `run_20261106T055638946809Z`. Blocked/failed module → `status: blocked` with the manifest's reason.
* Object-page panel "Decision priority" (RANK n / N, recorded inputs, recorded score, rule from manifest or
  `RULE NOT RECORDED`, C4 ABSTAIN) and report section 6b; `/api/objects/{norad}.decision_priority`.

### P2.3 — Health-screen relabelling (requirement 3)
* Nav "Satellite Intelligence" → **"Telemetry Benchmarks"**; telemetry heading "Health model evidence" →
  **"Anomaly-detection benchmark arms — saved ESA-ADB detection scores; not spacecraft health"** with an
  explanatory note; object section "Telemetry and health" → **"Spacecraft health — not determinable"**
  ("no subsystem health state exists for it and no health score is synthesised"); overview module-status
  table gains an evidence-class column. No health value, score or claim was introduced anywhere.

### P2.4 — Evidence-availability strip (requirement 4)
* `store.evidence_availability(record, run_id)` classifies ten capabilities per object with the vocabulary
  **implemented / archived_only / benchmark_only / blocked / unavailable**, driven by the referenced run's
  module statuses and the object's own record (e.g. lifetime abstention → unavailable; module failed or
  blocked → blocked). Rendered at the top of the object page with the vocabulary explained; in the API and
  report section 6c.

### P2.5 — Acceptance tests (requirement 5)
`tests/test_demo_workflow.py`, **14 tests, all passing** on the four demonstration objects (37607, 23806,
25544, 12) with synthetic roots only for failure modes (labelled "FIXTURE" in their manifests):

| D | Status | Evidence |
|---|---|---|
| D1 object selection | PASS | search by name and id; unknown id → explicit absence |
| D2 twin-state retrieval | PASS | re-emitted record for all four objects **value-equal to the archived record** (exact, store side); API record equal after JSON's NaN→null |
| D3 versioned provenance display + labelled fallback | PASS | digest prefixes on page; fallback root → `source: archived`, badge "(fallback)" |
| D4 interval vs horizon | PASS | 37607 CROSSES/BEFORE; 23806 CROSSES/CROSSES; 25544 NO INTERVAL; 12 AFTER/AT CAP |
| D5 subgroup under-coverage | PASS | 0.5625 [0.512, 0.614] vs 0.80; class-prior object flag false |
| D6 unknown A/M source | PASS | fixture with blank source → "unknown (not recorded; not inferred)", NO SUBGROUP EVIDENCE |
| D7 missing provenance | PASS | fixture run without config → lineage "unavailable"; model version unavailable |
| D8 stale / missing evidence | PASS | archive time missing; fixture without epoch → MISSING |
| D9 re-entry availability | PASS | 25544 abstention with base rate, no quantiles, capability UNAVAILABLE |
| D10 decision priority | PASS | rank and score equal the run table; explanation contains the manifest's formula; old run → rule unavailable |
| D11 archived vs synthetic | PASS | HISTORICAL badge; "re-emitted from the archived forecast table"; evidence policy |
| D12 API/UI consistency | PASS | page values formatted with the console's own formatter equal the API; report rows equal run tables |
| D13 unavailable modules | PASS | fixture with lifetime failed / priority blocked → BLOCKED, reason names lifetime, nothing substituted |
| D14 health semantics | PASS | "not determinable", no synthesised score, relabelled nav and heading |

### P2.6 — Demonstration protocol
`docs/product/DEMONSTRATION_PROTOCOL.md`: prerequisites and the four launch commands (including the D-tests),
the four objects and why, a ten-step navigation table with the API behind each step, the artifact read and
the expected output (each backed by a D-test), the limitations to state aloud, how to verify provenance
live, and reproducibility. `DEMO_SCRIPT.md` §3 "Satellite health assessment" is retired with a pointer.

## 3. API contracts (new or extended; all stamped `api/1.1` where applicable)

| Endpoint | Addition |
|---|---|
| `GET /api/objects/{norad}` | `twin_state` (source, fallback, schema_version, artifact, recorded sha, provenance_on_outputs, source_record, reemission, model_version, record), `decision_priority` (status, run_id, rank, ranked_objects, row, rule{status,…}, health_escalation, explanation), `evidence_availability` (list of {capability, status, detail}) |
| `GET /api/objects/{norad}/twin` | the twin-state block alone; 404-class error for unknown objects |
| `GET /api/overview` | `module_evidence_class` |
| `GET /api/reports/object/{norad}` | `twin_state` (without the raw record; outputs summarised), `decision_priority`, `evidence_availability`; HTML sections 6a–6c |
| run manifest (`run_manifest/1.1`) | `modules.decision_priority.outputs.priority_rule` recorded verbatim |

## 4. UI behaviour

Object page order: evidence-availability strip → identity → elements/physical → re-entry (+ horizon cue)
→ lifetime (+ horizon cue, subgroup cue, coherence) → **twin state** → **decision priority** → spacecraft
health (not determinable) / conjunction (unsupported) → report export → evidence freshness → snapshot
provenance (incl. model version). Badges: RE-EMITTED / HISTORICAL ARCHIVE (fallback), RANK n / N, BLOCKED,
UNAVAILABLE, IMPLEMENTED / ARCHIVED ONLY / BENCHMARK ONLY. Nothing on the page recomputes a value; the rule
and inputs are the run's records.

## 5. Changed-file inventory

| File | Change |
|---|---|
| `cosmos/ai/adapters.py` | `CONSEQUENCE_MULTIPLIER`, `PRIORITY_RULE` metadata recorded in `decision_priority` outputs (calculation unchanged) |
| `scripts/run_pipeline.py` | `_jsonable` keeps plain metadata dicts |
| `cosmos/product/store.py` | twin-state constants and reader (`_twin_index`, `_twin_line`, `twin_record`), `priority_for_object`, `evidence_availability`, `CAPABILITY_STATUSES`; `object_record` attaches the three blocks |
| `cosmos/product/api.py` | `/api/objects/{norad}/twin`; `module_evidence_class` in overview |
| `cosmos/product/reports.py` | `twin_state`, `decision_priority`, `evidence_availability` blocks; HTML 6a–6c |
| `cosmos/product/templates/object.html` | availability strip, twin-state and decision-priority panels, health section relabelled |
| `cosmos/product/templates/base.html`, `telemetry.html`, `overview.html` | relabelling; evidence-class column |
| `tests/test_demo_workflow.py` | new, 14 tests |
| `docs/product/DEMONSTRATION_PROTOCOL.md` (new), `docs/product/DEMO_SCRIPT.md` (§3 retired) | protocol |
| `outputs/pipeline/run_20261108T072802Z/` | demonstration run (new directory; nothing overwritten) |

Not changed: orchestrator, contracts, study code, any archive, any frozen file, the JINT manuscript.

## 6. Known limitations

* The twin state shown is **re-emitted from the archive**; it is not read by the runtime pipeline
  (capability status "archived only" says so).
* Model version is unavailable everywhere; this is truthful until the P1.5 persistence work and backends exist.
* The priority rule is explained only for runs that recorded it (from today); older runs show "rule not
  recorded" rather than a reconstruction.
* Ties in the ranking (e.g. 32730 and 37607 both at 2.0) are ordered by the run's stable sort; the page
  shows the recorded rank.
* JSON APIs serialise NaN as `null` (JSON has no NaN); the store-side record keeps the archive's NaN.
* Spacecraft health is "not determinable" for every real object — by evidence, not by omission.

## 7. Remaining roadmap (unchanged from the plan; none started)

**P3:** runtime reader of the re-emitted state in the orchestrator; run-comparison diffing; pagination;
later SATCAT snapshot for prospective evaluation; SpotGEO cache rebuild; remaining 3b cells / am_design
Stage 2 after decisions; visual regression (needs a headless browser).
**Future inference (separately approved):** model persistence per the P1.5 proposal, backend installation
under a recorded environment, an explicit opt-in adapter inference mode with digest verification — only then
may the console show a recorded model version or any prediction-time execution.
