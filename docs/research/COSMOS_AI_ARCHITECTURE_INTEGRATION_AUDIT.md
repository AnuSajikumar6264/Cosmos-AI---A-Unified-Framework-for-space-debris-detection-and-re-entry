# COSMOS-AI — Architecture integration audit

Date 2026-11-08 · HEAD `78ee339` · audit only; nothing implemented. Written for the project record:
it states exactly how much of COSMOS-AI runs today as an integrated, executable satellite digital
twin, with evidence for every integration claim. Where a claim could not be verified by running
code or reading an artifact, it is marked as such.

**One-sentence answer.** COSMOS-AI today is a *read-only evidence twin*: a deterministic
orchestrator (`cosmos/ai/orchestration.py`) runs seven adapters (`cosmos/ai/adapters.py`) that wrap
**archived** predictions in typed contracts and write a versioned run directory, which a FastAPI
console (`cosmos/product/`) renders with provenance; the only identity join is NORAD within the
catalogue chain, no model runs at prediction time, no live source is connected, and the four
real-data study pipelines (telemetry, lifetime, conjunction, vision) are executable research code
whose *outputs* feed the twin — they are not called by it.

---

## 1. Baseline and integrity status

| Item | Value | Evidence |
|---|---|---|
| Git HEAD | `78ee33962007203bcfc829fc743a663b350373e1`, branch `product/mission-intelligence-console`; 0 staged; 17 modified tracked files; 231 untracked entries (all uncommitted by instruction) | `git rev-parse HEAD`, `git status --porcelain` |
| Protected artifacts | all verified: ESA-ADB freeze 28/28; original confirmatory freeze 27/28 (expected difference: the pre-registration document whose §9 was filled in afterwards); G5d pre-registration; figure release 107/107; OPS-SAT archive 10/10; twin digests; accepted gate record `83b1150215020e0e…` / `86ae2e8c828e3e18…`; CONFIRMATORY.json `fc2223d6ffe23881…` | `outputs/audit/protected_artifacts_arch_audit_20261108T063145+0000.json` |
| Tests | full suite **352 passed, 3 skipped** (2026-11-08 06:2x, `outputs/audit/pytest_full_20261108_after_x4_x6_x10.log`); integration subset re-run for this audit **88 passed** (product, integration, twin state, staleness, orchestration, contracts, twin) | `pytest tests/test_product.py tests/test_integration.py tests/test_twin_state_consistency.py tests/test_console_staleness.py tests/test_orchestration.py tests/test_contracts.py tests/test_twin.py -q` |
| Pipeline entry points | `python scripts/run_pipeline.py --as-of 2026-10-27 [--limit N --collision-limit N --debris-sequence-limit N --health-calibrator conformal_bh --collision-model cosmos_gated --select … --out DIR]`; `--list` prints the module graph | run on 2026-11-06 over all 31,396 objects in 7.1 s (`outputs/phase3_uncertainty/pipeline_full/`) |
| Console entry points | `python scripts/serve_console.py [--host --port]` → `uvicorn` on `cosmos.product.api:create_app(root)`; 34 routes (`/`, `/objects`, `/objects/{norad}`, `/telemetry…`, `/debris…`, `/risk`, `/runs…`, `/compare`, `/prospective`, `/scenario`, `/reports/object/{norad}`, and `/api/*` equivalents) | `cosmos/product/api.py` lines 100–375 |
| Legacy demonstration entry | `cosmos.run_pipeline(faults=…, n_samples=…, seed=…, backend="classical"|"learned", footprint_backend="reference"|"surrogate")` — simulated telemetry → health monitor → hazard → break-up → footprint → risk | `cosmos/pipeline.py:73`; exercised by `tests/test_ai.py` |
| Study entry points (research code) | `python -m cosmos.ai.lifetime.run`, `cosmos.ai.conjunction.run`, `cosmos.ai.telemetry.{oof,oof_benchmark,opssat,esa_benchmark,smap_msl,robustness}`, `cosmos.ai.vision.{spotgeo,train_spotgeo,cosmos_synthetic}`, `cosmos.ai.twin.{engine,couplings,prospective}`, `cosmos.ai.{surrogate,report,dashboard}`, `cosmos.ai.data.{download,validate,preprocess_telemetry}`, `scripts/prereg_analysis.py` (frozen) | `__main__` guards, 34 modules |
| Configs | `configs/telemetry/{esa_adb,opssat,opssat_regen_20261106}.yaml`, `configs/vision/{spotgeo,cosmos_synthetic}.yaml`, `configs/reentry/{landmark,surrogate}.yaml` | `find configs` |
| Datasets on disk | REAL downloaded: ESA-ADB (processed official grids present), OPS-SAT-AD (processed), SMAP/MSL, CelesTrak (SATCAT + GP files), GCAT, Kelvins CAC, SpotGEO (4.23 GB extracted; **front-end cache absent**), recovered-debris file; DERIVED: `lifetime_cohort_2026-10-27.csv.gz`, `msis21_density_table.npz`; SYNTHETIC: `cosmos_synthetic` telemetry and imagery; not downloaded: SPARK | `data/*/MANIFEST.json` (15 manifests) |
| Backends | present: torch (xpu available), xgboost, scikit-learn, scipy, numba, fastapi, jinja2, PIL. **Absent:** statsmodels, lightgbm, catboost, tabm, tabicl, kumo, pymsis, chronos-forecasting | import probes |
| Persisted models | 85 OPS-SAT checkpoints under `outputs/experiments/*/checkpoints/` (cnn/fcnn/hybrid/transformer, both protocols); **no fitted lifetime, conjunction or ESA-ADB model is persisted** (predictions only); learned-monitor and surrogate checkpoints absent (their tests skip) | `find outputs/experiments -name '*.pt'`; `tests/test_ai.py` skips |

The repository matches the reported baseline; the audit proceeded.

---

## 2. Module-by-module implementation inventory

Classes: **A** implemented and executable independently · **B** integrated into the main pipeline
(`scripts/run_pipeline.py` → orchestrator → adapters) · **C** produces archived outputs that the
pipeline or console *reads* but does not execute · **D** partially implemented or blocked by
missing dependencies · **E** planned or conceptual only. A module may carry more than one class
(e.g. A for its study code, C for how the twin consumes it). "Integrated" is asserted only where a
runtime call chain was read in code or exercised by a test.

| Module | Code | Class | Evidence of what runs, and how it reaches the twin |
|---|---|---|---|
| Telemetry ingestion & preprocessing | `cosmos/ai/data/preprocess_telemetry.py` (`prepare_esa_official`, `load_esa_split`, `official_test_labels`, `load_opssat_ad`); `cosmos/health/realdata.py` (`prepare_esa_mission` → `data/feature1_health/external/esa_ad/prepared/mission{1,2}.npz`); `forecasting.MissionData` | **A, C** | Executable (processed grids present; X4 re-ran `MissionData` and the frozen forecaster on 2026-11-08). **Not called by the orchestrator** — the twin's `health` module reads `outputs/benchmarks/telemetry_esa_adb/results.csv`. The console telemetry pages read `prepared/mission*.npz` directly (`store.py:395–468`) |
| Identity & evidence association | `cosmos/ai/contracts.py`; adapters set `identity_linkable=False` for collision/health; `adapters.decision_priority` three-branch abstention | **B (catalogue chain only); E (cross-corpus)** | NORAD is the only key: `catalogue_state → lifetime → reentry → decision_priority` join on `NORAD-<n>` at runtime (`test_catalogue_chain_is_identity_linked`). Telemetry (anonymised missions), conjunction (anonymised events) and debris (pixel detections) carry no object identity; the API states this per object (`/api/objects/37607` → `telemetry.available=false`, `conjunction.available=false`, reasons quoted in §4). No association algorithm exists, because no public corpus supports one (C4) |
| Twin state construction | `cosmos/ai/twin/state.py` (`ObjectTwin`, `ModuleOutput`, `attach` with as-of check); `cosmos/ai/twin/engine.py:run` builds `twins.jsonl` + `forecast_table.csv.gz` | **C (archived state); D (regeneration)** | Archived state verified by value on all 31,396 records (`tests/test_twin_state_consistency.py`), `provenance: null` on all 44,634 outputs (predates the provenance code). `engine.run` → `study_learner()` → `tabm` → **not importable**: the state cannot be regenerated here. At runtime the orchestrator does **not** build `ObjectTwin`s; it builds per-module contract objects keyed by object id |
| Anomaly detection & health monitoring | studies: `cosmos/ai/telemetry/*` (ESA-ADB OOF protocol — frozen; OPS-SAT; SMAP/MSL; robustness); legacy `cosmos/health/monitor.py` (simulator); `learned_monitor.py` | **A (studies, legacy); B-as-archive (twin); D (learned monitor)** | Twin `health` module = `adapters.health_estimates`: one `HealthEstimate` **per benchmark arm** (`spacecraft_id = "ESA-ADB-M1-<tag>-<calibrator>"`, `status="benchmark-arm-measurement"`), read from `results.csv`. It is a table of detection scores, **not a spacecraft health state**; no per-sample anomaly score exists in any archived artifact. Learned monitor checkpoint absent (`test_learned_telemetry_backend` skips) |
| Optical imagery processing | `cosmos/ai/vision/spotgeo.py` (registration front end via `cosmos.debris.detect`, official scorer vendored), `train_spotgeo.py`, `heatmap.py`; archived runs + per-sequence submissions | **A (scoring/validation); D (re-running detectors: cache `processed/front_end_f16` absent); B-as-archive** | Twin `debris` module reads the archived classical submission (25,600 frames) → `DebrisDetection(observed_at=None, confidence=None)`, `astrometric_calibration=False`. Console serves real SpotGEO frames with detection overlays (`/api/debris/{seq}/frame/{f}.png`). X14 (2026-11-06) re-scored all ten arms from archives |
| Orbital propagation & lifetime | `cosmos/ai/lifetime/physics.py` (King-Hele drag over cached NRLMSIS 2.1 table; `decay_times`, tested), `catalogue.py` (cohort), `run.py` (benchmark), `fusion.py` (gate + Mondrian CQR) | **A (physics, cohort, CQR; benchmark for xgboost/mlp only); D (selected learners kumo/tabm absent); B-as-archive** | Twin `lifetime` module reads `p_lifetime_*`, `lifetime_lo90/hi90`, `median_days_lifetime` from the forecast table; abstains on 123 incoherent records. **No orbit propagation of state vectors exists anywhere** — the catalogue publishes mean elements (`elements.state_vector=null` in the API) |
| Re-entry & debris trajectory | twin forecast (`engine.py`: physics prior / history posterior / lifetime fusion, archived); legacy `cosmos/reentry/*` Monte-Carlo footprint (simulator); `cosmos/ai/surrogate.py` | **C (dated forecast); A (legacy, synthetic only); D (surrogate: checkpoints absent); E (corridor/impact validation)** | Twin `reentry` module reads `p_30d/p_90d/p_1yr`, `lo90/median/hi90` per object. No footprint, ground track or impact location is produced for real objects (KNOWN_LIMITATIONS P4/P5); corridor validation blocked by missing pre-entry states |
| Conjunction & collision risk | `cosmos/ai/conjunction/{data,run}.py`; archived `test_predictions.npz` | **A (data ingest; run feasible for persistence/xgboost only); D (tabm/tabicl/kumo absent); B-as-archive** | Twin `collision` module reads quantiles per anonymised `CAC-EVENT-<i>`, `priority_score=None`, `identity_linkable=False`. No propagation / screening / TCA computation exists (quantities arrive in the CDM) |
| Uncertainty estimation & calibration | `contracts.Uncertainty`; `lifetime/fusion.MondrianCQR`; `uncertainty.py`; `evaluation.py` (frozen); console `interval_quality`, `horizon_coherence` | **B (carried through contracts and displayed); A (methods)** | Quantiles are preserved per module (`test_uncertainty_semantics_are_preserved_per_module`); the decision ranking uses the point probability only and carries the interval as a flag (`tests/test_twin_uncertainty_audit.py`). Subgroup calibration is not represented (see §6) |
| Evidence provenance & model versioning | `cosmos/ai/provenance.py` (`git_revision`, `sha256_file`); `contracts.Provenance` (`input_hashes`, `code_revision`, `config_digest` set by the orchestrator at `orchestration.py:228`, `model_digest` **never set**); `run_manifest.json`; `cosmos/ai/registry.py` (20 model cards: 16 validated-real, 2 validated-synthetic, 1 not-recommended, 1 baseline) | **B (artifact + code + config lineage); C (registry, not linked to runs)** | Every run manifest records input SHA-256, git commit, config digest and environment; the console shows them (`test_04`, `test_15`). "Model version" is a free-text label plus the artifact hash — no registry card id or model digest travels with an output |
| Mission-level decision support | `adapters.decision_priority` (priority = p₃₀ × consequence multiplier; health escalation abstains in all three branches); `cosmos/ai/fusion.decide` (noisy-OR) | **B (priority); A (noisy-OR, unit-tested, not on the twin path)** | `decision_ranking.csv` reproduces exactly as `p_30d × (2 if mass ≥ 500 kg)`; `fusion.decide` is called only by the legacy chain and tests |
| Mission Intelligence Console | `cosmos/product/{api,store,reports,charts}.py`, 15 templates, `scripts/serve_console.py` | **B** | Reads run directories and artifacts; `POST /api/scenario` executes `scripts/run_pipeline.main` into a new run directory (verified today on a disposable root, `test_05`, `test_16`); 36 behavioural tests. No live feed (templates state this on every screen) |
| Legacy simulator chain | `cosmos/pipeline.py`, `cosmos/health`, `cosmos/debris`, `cosmos/reentry` | **A (synthetic demonstration)** | `cosmos.run_pipeline` runs end to end in tests; it shares code with the AI layer only where noted (`cosmos.debris.detect` registration used by the SpotGEO front end; `cosmos.debris.catalogue.kaplan_meier` by lifetime diagnostics; `cosmos.health.realdata` by the ESA-ADB baseline and the console telemetry pages). It is not connected to any real object and must not be presented as the twin |
| Auxiliary | `cosmos/ai/dashboard.py` (`outputs/dashboard/index.html`), `cosmos/ai/report.py` (`outputs/benchmarks/SUMMARY.md`), `twin/couplings.py` (C2/C3/C4 evaluations), `twin/prospective.py` (T1 test) | **C** | Archived outputs; not executed by the pipeline or console |

**Integration summary.** Of the twelve module areas, exactly one chain is integrated at runtime —
catalogue state → lifetime → re-entry → decision priority — and it is integrated as a *reader of a
single archived table*. Three further modules (collision, health, debris) run in the same
orchestrator but are independent roots with no identity link to the catalogue chain. Everything
else is executable research code (A) or archived output (C), with regeneration of the dated
forecast, the learned lifetime/conjunction arms and the learned monitor blocked by absent backends
or checkpoints (D).

---

## 3. Actual runtime architecture and call graph

```text
scripts/run_pipeline.py main(argv)
  ├─ adapters.default_modules()                       7 ModuleSpec; graph:
  │     catalogue_state ─┬─> lifetime ──┐
  │                      └─> reentry ───┴─> decision_priority
  │     collision   (independent root)   health (independent root)   debris (independent root)
  ├─ Orchestrator(modules).run({}, selected=…, config={as_of, limit, …, root})
  │     topological order; a failed module → dependants "blocked" (reason names the module);
  │     unrequested → "not_requested"; provenance.config_digest stamped on every success
  │     ├─ catalogue_state(ctx)   _load_snapshot(root, as_of, limit): forecast_table.csv.gz,
  │     │                          required-column check → OrbitalElements, ObjectCharacteristics,
  │     │                          regime (classify_regime), names
  │     ├─ lifetime_estimates(ctx) same table → LifetimeEstimate(quantiles 5/50/95, p_30d/90d/1yr,
  │     │                          Uncertainty(kind="quantiles")); abstain on 123 incoherent rows
  │     ├─ reentry_predictions(ctx) same table → ReentryPrediction(p_*, quantiles, Uncertainty)
  │     ├─ collision_risk(ctx)    test_predictions.npz → CollisionRiskEstimate per CAC-EVENT-i,
  │     │                          identity_linkable=False, priority_score=None
  │     ├─ health_estimates(ctx)  results.csv → HealthEstimate per benchmark arm,
  │     │                          status="benchmark-arm-measurement", identity_linkable=False
  │     ├─ debris_detections(ctx) classical submission JSON → DebrisDetection (no time, no confidence)
  │     └─ decision_priority(ctx) ranking = p_30d × (2 if mass ≥ 500 kg); health escalation ABSTAIN
  └─ _write_tables → outputs/pipeline/run_<UTC>/{decision_ranking, reentry_predictions,
        lifetime_estimates, lifetime_noncoherent_horizons, collision_risk, health_benchmark_arms,
        debris_detections}.csv + run_manifest.json (input hashes, git, config sha, environment)

scripts/serve_console.py → uvicorn → cosmos.product.api.create_app(root)
  ├─ ArtifactStore(root): list_runs/run_manifest/table (outputs/pipeline/*),
  │    catalogue/object_record (forecast_table.csv.gz directly), telemetry (prepared/mission*.npz),
  │    debris (classical submission + SpotGEO frames), collision (test_predictions.npz),
  │    repository_provenance (git + dated-forecast digest), prospective_status
  ├─ GET pages/APIs (read-only)      ← every page: dated snapshot, HISTORICAL, STALE finding
  └─ POST /api/scenario → _execute_scenario → run_pipeline.main([...--out root/outputs/pipeline/run_<ts>])
```

No model is invoked anywhere in this graph: every number the twin serves was computed by a study
script before the run and is read from an artifact whose SHA-256 is recorded. The orchestrator is
deterministic (two full runs byte-identical, `tests/test_pipeline_determinism.py`).

---

## 4. End-to-end data lineage — NORAD 37607 (ARIANE 5 R/B, rank 1 in the decision ranking)

| Transition | Function / API | Input → output schema | Runtime or archive | Joinable id | Provenance | Time / freshness | Uncertainty | Missing / stale / inconsistent behaviour |
|---|---|---|---|---|---|---|---|---|
| Source data → cohort/forecast | `cosmos.ai.lifetime.catalogue` (cohort), `cosmos.ai.twin.engine.run` (forecast; **not re-runnable: tabm absent**) | SATCAT + GCAT + SW-All → `forecast_table.csv.gz` row: `norad 37607, type1 R, perigee 122, apogee 11622, mass 5000, am_source design, regime natural_decay, history_kind history (5,636 d), p_30d 1.0, median/lo90/hi90 10/10/10 d, p_lifetime_30d 0.780, lifetime 6.9/27.5/95.3 d` | archive (as-of 2026-10-27, sha `b15644aab581cd05…`) | NORAD | `FORECAST_SHA256.txt` covers `twins.jsonl` only; table hash recorded in every run manifest | `as_of` 2026-10-27; `t0_canonical` 2011-05-23 | physics Monte-Carlo quantiles (32 draws); lifetime Mondrian-CQR interval | wrong-date request fails on the path, never falls back (`test_wrong_date_snapshot…`) |
| Forecast → twin state (archived) | `engine.run` → `ObjectTwin.attach` | row → `twins.jsonl` record: identity, orbit, physical, family, space weather, 2 outputs (`reentry` physics-history T1-validated; `reentry-comparison` lifetime) | archive | NORAD (`object_id "37607"`) | `provenance: null` on both outputs (version finding) | `as_of` | `interval80/90_days`, `history_ess` | — |
| Forecast → contracts | `adapters.catalogue_state/lifetime_estimates/reentry_predictions` | row → `OrbitalElements(122, 11622, 2.46)`, `ObjectCharacteristics(mass 5000)`, `LifetimeEstimate(quantiles (6.94, 27.51, 95.32), p 0.780/0.929/0.988)`, `ReentryPrediction(p 1/1/1, quantiles 10/10/10)` | runtime read (7 s full run) | `NORAD-37607` | `Provenance(input_hashes={table: b15644…}, code_revision 78ee339, config_digest d7dd231e…)` | `as_of` timestamp `2026-10-27T00:00:00+00:00`; same-date rule enforced | `Uncertainty(kind="quantiles", method=…, assumptions=(…))` | missing columns → `ArtifactUnavailable` naming them, dependants blocked (`test_schema_drift…`); incoherent lifetime → abstain with reason |
| Contracts → decision | `adapters.decision_priority` | → `decision_ranking.csv` row: `p_reentry_30d 1.0, mass_kg 5000, high_consequence True, priority_score 2.0, lifetime_evidence True, reentry_interval_available True`; rank 1 of 31,396 | runtime | `NORAD-37607` | upstream_outputs recorded | `as_of` | **point probability only**; interval carried as a flag | health evidence present but unlinked → escalation ABSTAIN with reason |
| Run → console object record | `ArtifactStore.object_record(37607)` → `GET /api/objects/37607` | 18 keys: identity, regime, `elements` (state_vector null + note), `physical {mass 5000, rcs 25.52, area_to_mass_source "design"}`, `lifetime {…, horizon_coherence coherent, interval_quality spread}`, `reentry {…, variants, uncertainty_note "Monte-Carlo spread … not a conformal interval"}`, `telemetry {available false, reason}`, `conjunction {available false, reason}`, `provenance {artifact, sha256, as_of, objects, sources}` | archive read at request time (forecast table), plus latest run tables for the report | NORAD | artifact sha + sources | `as_of`; overview carries `snapshot_age {age_days 12, stale true}` and a STALE finding; the object page itself shows the date but no age | interval quality / coherence cues; zero-width and at-cap intervals flagged, not shown as precision | telemetry and conjunction reported as unavailable with the identity reason |
| Console → report | `GET /api/reports/object/37607` | `computed_outputs` (3: decision priority, re-entry, lifetime — each with `source` table and `run_id run_20261106T055638946809Z`), `historical_outputs` (dated twin forecast with artifact sha), `unsupported_assessments` (telemetry AD, collision probability, C4 escalation, impact location), `uncertainty` notes, 7 limitations, `interpretation.not_established` ("not real-time", "no live tracking feed") | run tables + archive | NORAD + `run_id` | `git_commit`, `config_sha256`, `dated_forecast_digest_state verified` | run `started_at`, `as_of` | per-module wording | unavailable run → `provenance.run.state = unavailable` (`test_15b`) |

**Disconnected interfaces found.** (1) Telemetry → object: no path (anonymised missions). (2)
Conjunction → object: no path (anonymised events). (3) Debris detections → object: no path (pixel
coordinates without astrometry or time). (4) Twin state (`twins.jsonl`) → runtime: the orchestrator
never reads it; the console never reads it; it is a frozen by-product. (5) `fusion.decide` → twin:
never called. (6) Registry cards → runs: never linked. **Unsupported fusion assumptions:** none are
made at runtime — every cross-modal fusion point abstains with a stated reason, which is the
correct behaviour given the data; the architecture documents (`docs/architecture/current_architecture.md`)
already say the system "is not a single, fully joined model".

---

## 5. Mission Intelligence Console — workflow audit (read-only probes, 2026-11-08)

| Step | What was exercised | Result | Archived / demo / live? |
|---|---|---|---|
| 1 Select an object | `GET /api/objects/search?q=ARIANE&limit=3` → 15166, 15388, 15562 (name match, NORAD order); search by id works (`test_02`) | **works** | archived snapshot (31,396 objects) |
| 2 Inspect evidence and source | `GET /api/objects/37607` → `provenance {artifact, sha256 b15644…, as_of, sources [SATCAT, GCAT, SW-All]}`; page shows HISTORICAL and the artifact path | **works** | archived |
| 3 Twin state and subsystem health | elements (mean elements; state vector explicitly null), physical (mass, RCS, **area-to-mass source shown**), regime, family, space weather; health → `UNSUPPORTED` with the reason "no telemetry exists for any catalogue object" | **works, truthfully**: there is no subsystem health for any real object, and the page says so | archived; health section is an explicit absence |
| 4 Trigger or retrieve predictions | retrieve: lifetime and re-entry blocks populated from the archive; trigger: `POST /api/scenario` runs the 7-module pipeline into a new run directory (verified today on a disposable root: `test_05`, `test_16`, `test_16b`) | **works** — but a scenario run **re-derives from the same archive**; no model inference happens | archived |
| 5 Uncertainty and reliability warnings | `interval_quality` (spread / degenerate / at_cap), `horizon_coherence` (INCOHERENT for the 123 L17 records), "not a conformal interval" note, overview STALE finding (12 days) | **works** for the cues that exist; **missing:** subgroup under-coverage (X6), interval straddle of the 30-day horizon, object-level snapshot age | archived |
| 6 Orbital / lifetime / re-entry information | lifetime 6.9 / 27.5 / 95.3 d, p 0.78 / 0.93 / 0.99; re-entry p 1 / 1 / 1, 10 d quantiles, variants (physics prior, history, lifetime) | **works** | archived (dated 2026-10-27) |
| 7 Mission-level assessment | `/api/overview`: findings STALE / ABSTAIN (C4) / BLOCKED (prospective); latest run's decision ranking (rank 1 = 37607) | **works** | archived; prospective evaluation disabled while blocked (`test_17`) |
| 8 Trace to source records and model versions | report: `run_id`, `git_commit`, `config_sha256`, artifact sha, `dated_forecast_digest_state verified`; model identified by a label string ("COSMOS dated twin (physics prior + history posterior + lifetime fusion)") | **works for artifact / code / config lineage; partial for model version** — no model digest, registry card id or training-run id travels with an output | archived |

Telemetry (`/telemetry`, `/api/telemetry/missions`) and debris (`/debris`, frames served) screens
work on real anonymised data and real frames; collision (`/risk`) works on anonymised events with
`identity_linkable=false`. **No screen is a live feed; none claims to be** (`objects.html`,
`overview.html`, `channel.html` say so explicitly; KNOWN_LIMITATIONS P1).

---

## 6. Scientific reliability and provenance gaps

| Check | Finding | Status |
|---|---|---|
| A/M source representation | `am_source` is in the forecast table, the twin state (`physical.area_to_mass_source`), the API, the object page ("Area-to-mass source: design") and the report | **represented** |
| Under-coverage warning for design-derived objects (X6 Stage 1) | nothing in `store.object_record`, `object.html` or `reports.py` reads `outputs/am_design_stage1/`; the 80 % interval of a design-derived object at origin 2016 covered 56 % (2011: 79 %) and the console shows the interval with no such cue | **gap — P0.1** |
| Interval calibration per subgroup | the deployed Mondrian groups are class × perigee band; coverage by A/M source is **not** nominal (X6); recalibration would be a methodology change and is out of scope here — what is in scope is *reporting* the measured subgroup coverage | **gap in reporting; methodology untouched** |
| Console presents X6 accurately | X6 is not presented at all (finished today) | **gap — P0.1** |
| X10 / K8 contribution removed or qualified | the console never mentions OPS-SAT, late fusion or `hybrid`; `docs/product/*` make no fusion claim; the K8 withdrawal is recorded in the tracker and the approved-analyses report; the registry still carries an OPS-SAT card whose text should be checked for a "fusion improves…" phrasing before any writing | **qualified in research docs; registry card wording to verify — P0.3** |
| X4 described as exploratory and AR(8)-specific | tracker row, addendum and report say "EXPLORATORY", "Mission 1, AR(8) scorer, conformal-BH layer only", "partial design, two protocol gaps" | **yes** |
| Archived vs synthetic evidence distinguished | dataset manifests carry `class` REAL/SYNTHETIC/SIM/DERIVED; registry cards carry `validated-real` vs `validated-synthetic`; the legacy simulator is documented as a separate demonstration; the console serves no synthetic data; `fusion.decide` flags synthetic validation in `assumptions` | **yes**, with one caveat: a legacy lat/lon footprint file from the synthetic chain is in the repository (KNOWN_LIMITATIONS P4) and must never be surfaced as real |
| Provenance to model / configuration / data source / run | data source and run: yes (artifact SHA-256, run id, git commit, config digest, environment); configuration: yes (`config_sha256`); **model: label only** — `Provenance.model_digest` is never set, the archived twin state has no per-output provenance, and the registry is not linked to outputs | **partial — P0.2** |
| Freshness | `snapshot_age` and STALE finding on the overview (added 2026-11-06); object pages and reports show the as-of date but not the age | **partial — P1.6** |
| Uncertainty propagated vs displayed | preserved per module as quantiles; displayed with quality cues; **not used** by the decision ranking (point probability × multiplier) | **displayed, not propagated into the decision — P1.4 (display only)** |

---

## 7. Prioritised engineering roadmap (not implemented — for decision)

Effort is engineering time on this codebase, excluding approvals. None of these tasks changes a
frozen artifact, a pre-registration, a confirmatory result, a benchmark score, or the scientific
methodology; tasks that *would* (recalibration, retraining) are listed only as decisions.

### P0 — necessary for a truthful, functional end-to-end demonstration

| # | Task | Files / functions | Dependencies | Tests | Acceptance | Risk | Effort |
|---|---|---|---|---|---|---|---|
| P0.1 | Surface measured subgroup coverage for the object's A/M source | `cosmos/product/store.py::object_record` (read `outputs/am_design_stage1/subgroup_coverage.csv`, add `lifetime.subgroup_coverage {origin, am_source, level, coverage, ci95, n}`), `templates/object.html` (reliability row), `reports.py` (limitations + uncertainty note) | X6 Stage 1 artifact (exists) | new `test_product` case: a design-derived object shows "80 % intervals covered 56 % of design-derived objects at origin 2016 (archived evaluation)"; a class-prior object shows its own figure; absence handled when the artifact is missing | low (display only) | 0.5–1 day |
| P0.2 | Model-version lineage on every output | `adapters._provenance` (set `model_digest` = SHA-256 of the artifact that holds the model's predictions; add `model_card` id from `cosmos/ai/registry.py`), `orchestration.py` (carry through), `run_pipeline._write_tables` (manifest `models` block), `store.run_manifest` / `templates/run.html` / `reports.py` | registry card ids per adapter | extend `test_provenance_records_the_artifact_digest_and_code_revision`; `test_04` shows model digest on the run page | low; manifests gain a field (schema version bump, P1.5) | 1 day |
| P0.3 | Wording audit of model cards and screens for withdrawn claims | `cosmos/ai/registry.py` (OPS-SAT card text: calibration/stability wording), console telemetry/overview copy | X10 result | a test asserting no registry card or template contains "fusion improves" / "late fusion contributes" without the qualification | none | 0.5 day |
| P0.4 | Documented launch and demo path | `README.md` / `docs/product/PRODUCT_USER_GUIDE.md`: `python scripts/serve_console.py --host 127.0.0.1 --port 8000`; `python scripts/run_pipeline.py --as-of 2026-10-27`; state that the console is a reader of a dated snapshot | — | docs only; `scripts/serve_console.py --help` works | none | 0.25 day |
| P0.5 | Decide the fate of regenerated score caches | `.gitignore` exception for `track3b_stage2/oof_regen/*.npy` (3.4 GB) **or** an archive note stating they are reproducible in 353 s | repository policy (size) | `tests/test_track3b_stage2.py` unaffected | repo size if tracked | decision |

### P1 — necessary for scientifically defensible integration

| # | Task | Files / functions | Dependencies | Tests | Acceptance | Risk | Effort |
|---|---|---|---|---|---|---|---|
| P1.1 | Interval-vs-horizon cue in the ranking (display only) | `adapters.decision_priority` (add `interval_straddles_30d`, `q05_days`, `q95_days` columns), `run_pipeline._write_tables`, `templates/run.html`, `reports.py` | none | extend `test_twin_uncertainty_audit::test_priority_score_is_exactly…` (priority unchanged), new column test | priority formula byte-identical; new columns present; 23/50 straddle figure reproduced | low | 0.5 day |
| P1.2 | Twin-state re-emission with provenance (no refit) | `cosmos/ai/twin/engine.py` (factor the `twins.jsonl` builder out of `run`; new `emit_state(table, out_dir)`; `--out`), `tests/test_twin_state_consistency.py` (by-value equality with the archive except `provenance`) | forecast table (exists) | re-emitted state equals archive on every value; provenance non-null; archive untouched | low (new directory) | 1 day |
| P1.3 | Persist fitted models in future study runs | `cosmos/ai/conjunction/run.py` (save xgboost/mlp/persistence fits + Mondrian tables), `cosmos/ai/lifetime/run.py` (save learners that support it), both with model digests into `summary.json` | none for xgboost/mlp; blocked for absent backends | round-trip test: saved model reproduces archived predictions | none to archives (new runs only) | 2–3 days |
| P1.4 | Schema versioning of artifacts and manifests | `adapters._load_snapshot` (declare `SNAPSHOT_SCHEMA = {"version": 1, "required": …}`), `run_pipeline` manifest `schema_version`, `store.py` readers | P0.2 | `test_schema_drift…` extended with a version mismatch case | low | 0.5 day |
| P1.5 | Object-level freshness | `store.object_record` (`snapshot_age`), `object.html`, `reports.py` | overview `snapshot_age` code (exists) | `test_console_staleness` extended to the object page and report | none | 0.25 day |
| P1.6 | Health screen semantics in the run directory | rename/label `health_benchmark_arms.csv` consumers so no path calls it a health state; overview `module_status` label "health (benchmark arms)" | none | `test_01b`, `test_08` extended | none | 0.25 day |

### P2 — strengthen the research contribution (each needs a decision or external data)

| # | Task | Dependency / decision | Effort |
|---|---|---|---|
| P2.1 | Remaining 3b cells after a protocol decision on the two gaps (how A0's model supplies a half pool; cross-fitting with a calibration-window pool) | user protocol decision | ~5 min per cell + review |
| P2.2 | am_design Stage 2 with the substitute learner (xgboost or mlp) | approval; 2–6 GPU-h | 1 day |
| P2.3 | Ingest a later CelesTrak SATCAT snapshot (≥ 2026-11-26) and run `cosmos.ai.twin.prospective` / `scripts/check_t1_later_snapshot.py` | external data availability | 1 day once data exists |
| P2.4 | Rebuild the SpotGEO front-end cache (~1 h CPU) so the classical arm and X14 can be re-run at new operating points | compute approval | 0.5 day |
| P2.5 | Install the missing backends in a recorded environment (statsmodels, lightgbm, catboost, tabm, tabicl, kumo) and re-run training-level reproducibility | environment decision; new lock file | 1–2 days |

### P3 — optional

Pagination and server-side filtering in the console; screenshot-based visual regression (blocked:
no headless browser); interactive charts; multi-user deployment hardening (KNOWN_LIMITATIONS P16–P23).

---

## 8. Explicit limitations and blocked components

- **No live data.** Nothing connects to a tracking, telemetry or CDM feed; every screen is a dated
  snapshot (2026-10-27) or a saved benchmark. The console states this on every screen.
- **No identity across corpora.** Telemetry (ESA-ADB), conjunction (Kelvins) and imagery (SpotGEO)
  cannot be attributed to any catalogued object; the twin's health, collision and debris modules
  are independent roots and the decision layer abstains from any cross-modal escalation (C4).
- **No model inference at runtime.** All predictions are archived; regeneration of the dated
  forecast, the selected lifetime and conjunction learners and the learned monitor is **blocked**
  (`tabm`, `kumo`, `tabicl`, `lightgbm`, `catboost` absent; learned-monitor and surrogate
  checkpoints absent). Only `xgboost`/`mlp`/persistence arms and the AR(8) telemetry scorer can be
  refit here.
- **No orbit propagation of state vectors**, no footprint or impact location for real objects, no
  conjunction screening; those quantities either do not exist in the data (mean elements only,
  CDMs carry the result) or lack ground truth (corridor validation blocked by missing pre-entry
  states).
- **Twin state lacks per-output provenance** (archived before the provenance code) and is not read
  by the runtime.
- **Decision ranking uses point probabilities only**; intervals are displayed, not used.
- **Subgroup calibration is not reported**: design-derived objects are under-covered at 80 % at both
  origins (X6), and the console does not yet say so.
- **Environment:** `statsmodels` absent (X6 used a validated numpy re-implementation); vision
  front-end cache absent; `*.npy` ignore rule still removes score caches from version control.
- **Legacy simulator chain** (`cosmos.run_pipeline`) is synthetic end to end and is a separate
  demonstration, not the twin.

---

## 9. Verification commands and results (2026-11-08)

```text
git rev-parse HEAD                                   78ee33962007203bcfc829fc743a663b350373e1
git diff --cached --name-only | wc -l                0
python scripts/verify_protected_artifacts.py --label arch_audit
                                                     all_protected_ok: True
                                                     -> outputs/audit/protected_artifacts_arch_audit_20261108T063145+0000.json
python scripts/run_pipeline.py --list                7 modules; graph as in §3
pytest tests/test_product.py tests/test_integration.py tests/test_twin_state_consistency.py \
       tests/test_console_staleness.py tests/test_orchestration.py tests/test_contracts.py \
       tests/test_twin.py -q                         88 passed in 21.13 s; outputs/pipeline unchanged (85 dirs)
full suite (06:2x, after the approved analyses)      352 passed, 3 skipped (outputs/audit/pytest_full_20261108_after_x4_x6_x10.log)
TestClient(create_app(ROOT)) GET probes              /api/objects/search, /api/objects/37607, /objects/37607,
                                                     /api/reports/object/37607, /api/runs, /api/risk/collision,
                                                     /api/telemetry/missions, /api/overview, /api/debris/sequences
                                                     — all 200; values quoted in §4–§5 (GET only; no run written)
import probes                                        torch/xgboost/sklearn/scipy/numba/fastapi/jinja2/PIL present;
                                                     statsmodels/lightgbm/catboost/tabm/tabicl/kumo/pymsis absent
```

Nothing was modified by this audit except the creation of this file.

## Addendum 2026-11-08 — P3-B twin-state evidence root (implemented and verified)

The runtime architecture gained one additional, explicitly traceable evidence root; the published chain
`catalogue_state → lifetime → reentry → decision_priority` is unchanged (dependency tuples asserted by
`tests/test_p3b_twin_state.py::test_catalogue_chain_graph_and_outputs_are_unchanged_by_the_new_root`; a full
run reproduces the seven tables byte-for-byte, `tests/test_p3b_chain_unchanged.py`).

* **Shared reader** `cosmos/ai/twin/reader.py`: explicit source selection (`prefer_reemitted` default with a
  labelled fallback to the archived `twin_state/1.0`; `reemitted_only`; `archived_only`), candidate verdicts
  with reasons (missing / present-but-empty / digest MISMATCH / unsupported schema / record-count mismatch /
  malformed first record), streaming record validation (schema, identity uniqueness, malformed lines, invalid
  values) and value equivalence with the catalogue chain. One code path serves the console and the orchestrator.
* **Orchestrator** (`cosmos/ai/twin/modules.py`, registered in `adapters.default_modules()`): `twin_state`
  (root, no dependencies) and `twin_equivalence` (depends on `twin_state`, `catalogue_state`, `lifetime`,
  `reentry`; writes `twin_equivalence.csv`). A missing or invalid archive fails `twin_state` explicitly and blocks
  only `twin_equivalence`; the catalogue chain completes.
* **Console**: `GET /api/twin-state`, page `/twin-state`, `policy` parameter on `/api/objects/{norad}/twin`,
  selection and per-object equivalence on the object page, readiness reports the selected source, the
  "versioned twin state" capability row reads `implemented` only for runs whose manifest carries a successful
  `twin_state` module and `archived_only` otherwise.
* **Verified result on the real archives (2026-11-08):** re-emitted archive selected as primary, digest
  verified, 31,396 valid records, 0 malformed, 0 duplicates; equivalence with run `run_20261108T083402Z`:
  31,396 records compared, 31,396 equal, 0 different, 452,690 shared values equal; the archived 1.0 archive
  compares identically. Classification of the twin state moves from "archived-only, not read by the runtime"
  to **implemented as an additional root (archived evidence; nothing regenerated; model version unavailable)**.
  Health, collision and debris remain independent, benchmark-only roots (no identity linkage).
