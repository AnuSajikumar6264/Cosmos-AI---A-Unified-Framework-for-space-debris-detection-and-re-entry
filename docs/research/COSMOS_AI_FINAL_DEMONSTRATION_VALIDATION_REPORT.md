# COSMOS-AI — Final demonstration validation report (2026-11-08)

Written for: the project owner and the M.Tech examiners. Every number below was measured on 2026-11-08 on the project machine
(`/data2/anupa/Final_Year_Project`, Python 3.12.16 in `.venv`, Linux 6.17, 512 CPUs, no CUDA device; Intel XPU present but not
used by the console) and is backed by a record under `outputs/audit/` or by a command that is reproduced in
`docs/product/COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md`. Nothing here is inferred from an earlier report.

## 1. Repository HEAD and release state

| Item | State at the time of this report |
|---|---|
| Branch | `product/mission-intelligence-console` (no upstream configured) |
| HEAD | `66f0bc54da30094d5750bd93e877726aab2142f5` — release commit C (2026-11-09), parent `633ad862bf5d7fe2612bb01038aee309bd350a07` (commit B), then `aeefac2bd93244f98f7acb20fb88427bbbe34da8` (commit A), `938d514` (approved checkpoint) and `78ee339` (public `main`) |
| Author / committer of every release commit | Anupa Sajikumar <anupa.sajikumar@intel.com>; no AI co-author trailer |
| Release commits | A, B and C created and verified (owner identity, no trailer, post-commit verifier green); D (acceptance report, release status, this report, audit records) staged and awaiting the owner's approval |
| Tag `v1.0-demonstration-2026-11-08` | not created (needs approval after the four commits) |
| Remote `origin` | `main` and `q1-reentry-rebuild` at `78ee339`; nothing pushed; the re-emitted twin-state LFS object `6bb4871f…` is absent from the remote |
| Working tree | after Commit C: only the tracker modified; untracked: 89 regenerable pipeline runs, `outputs/run_20261103T155605Z/`, 14 Phase 3 CSV copies, the Commit D documents and audit records |

Authoritative release status: `docs/research/COSMOS_AI_RELEASE_PROPOSAL.md` §8.

## 2. System architecture (as implemented)

A read-only, archive-backed evidence twin. The orchestrator (`cosmos/ai/orchestration.py`, adapters in `cosmos/ai/adapters.py`)
runs nine modules under typed contracts: the catalogue chain `catalogue_state → lifetime → reentry → decision_priority`,
identity-linked by NORAD id within one dated snapshot (2026-10-27, 31,396 objects); three independent benchmark roots
`collision` (Kelvins CAC), `health` (ESA-ADB) and `debris` (SpotGEO) that are never attributed to a catalogued object; and the
twin-state root `twin_state` with its `twin_equivalence` check against the chain. A run writes one
`outputs/pipeline/run_<UTC>/` directory with a `run_manifest/1.2` manifest (code, configuration, data and model lineage) and
the tables that succeeded. The Mission Intelligence Console (`cosmos/product/`: FastAPI `api.py`, read-only `store.py`, 17
Jinja templates, server-side SVG, no JavaScript build) serves 17 page routes and 23 JSON API operations (`api/1.2`) over those artifacts;
it executes nothing at request time except, on explicit request, the same pipeline in a child process into a new run directory.
No model weights are loaded by the runtime: lifetime, re-entry, collision and health values are archived predictions re-expressed
through the contracts.

## 3. Module integration matrix

Inventory basis: every package under `cosmos/` was read for its entry points, inputs, outputs, tests and console reach on
2026-11-08 (file references in `docs/product/COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md` §1, §6, §7). Statuses: **fully integrated and
operational** · **integrated with limitations** · **independently executable** · **research/benchmark-only** · **archived evidence
only** · **not implemented** · **blocked**.

| Module | Source | Entry point(s) | Inputs | Outputs | Console reach | Tests | Status | Evidence for the status |
|---|---|---|---|---|---|---|---|---|
| Mission Intelligence Console | `cosmos/product/` (api, store, charts, reports, 17 templates) | `scripts/serve_console.py`, `check_console_prerequisites.py`, `rehearse_demo.py`, `benchmark_console.py`, `profile_console_cold.py` | forecast table, twin archives, run dirs, benchmark artifacts, prepared missions, SpotGEO frames | HTTP pages/JSON; scenario child process → new run dir | 17 pages, 23 API operations | ≈ 20 test files (product, demo, journey, P0–P3) | **fully integrated and operational** | real-server sweep 32 routes 200; rehearsal 13/13; 508-test suite; no model loaded (`VERIFIED_MODEL_CARD_ASSOCIATIONS = {}`) |
| Orchestrator and the nine adapters | `cosmos/ai/orchestration.py`, `adapters.py`, `contracts.py`, `schema.py`, `provenance.py` | `scripts/run_pipeline.py`; `POST /api/scenario` | archived artifacts only (`adapters.py:56-60`) | `outputs/pipeline/run_<UTC>/` manifest + 8 tables | `/runs`, `/compare`, `/scenario`, object priorities | `test_orchestration`, `test_contracts`, `test_integration`, `test_end_to_end`, `test_pipeline_determinism`, `test_p3a_manifest` … | **fully integrated and operational** | run `run_20261108T121517Z` nine modules success; scenario via API 2.9 s; "adapters do not retrain, re-fit, resample or rescore" |
| Twin state: reader, modules, re-emission | `cosmos/ai/twin/{reader,modules,reemit,state}.py` | `scripts/twin_state_integrity.py`; `python -m cosmos.ai.twin.reemit` | `outputs/twin/as_of_2026-10-27{,_reemitted_v1}/` | `twin_equivalence.csv`; integrity records | `/twin-state`, `/api/twin-state`, `/api/objects/{n}/twin`, object pages | `test_p3b_twin_state`, `test_twin_state_consistency`, `test_p1_reemission`, `test_demo_workflow` | **fully integrated and operational** | selected reemitted/primary/verified; 31,396 valid; 31,396/31,396 equivalent; sha identical in a fresh clone |
| Twin forecast engine | `cosmos/ai/twin/engine.py` (+ `couplings.py`, `prospective.py`) | `python -m cosmos.ai.twin.engine --as-of …`; `couplings c2|c3|c4`; `prospective` | CelesTrak snapshot, GCAT, SW-All, lifetime cohort, origin-2016 learner parameters | `outputs/twin/as_of_<date>/…`, `outputs/benchmarks/twin_couplings/`, `twin_prospective_t1/` | indirectly: its 2026-10-27 output is what the console serves | `test_twin`, `test_couplings_regression` | **independently executable** (regeneration not authorised; needs `tabm`) | refits learners at run time; no persisted model; archived forecast frozen (`FORECAST_SHA256.txt`) |
| Lifetime and re-entry values (catalogue chain) | `adapters.lifetime_estimates`, `adapters.reentry_predictions` over the forecast table | `run_pipeline.py` | `forecast_table.csv.gz` columns | `lifetime_estimates.csv`, `lifetime_noncoherent_horizons.csv`, `reentry_predictions.csv` | object pages, reports | journey tests (37607, 23806, 25544, 12) | **integrated with limitations** | archived predictions, no inference; 123 L17 abstentions; interval kinds labelled; variants disagree up to 10.6× |
| Decision priority | `adapters.decision_priority` (`PRIORITY_RULE`) | `run_pipeline.py` | lifetime + re-entry outputs, GCAT mass | `decision_ranking.csv` | object page, `/api/runs/{id}/ranking` | journey stage 9; `test_product` | **integrated with limitations** | rule read from the manifest; point probability, not the interval; effectiveness only on the non-blind T1 window (exploratory) |
| Collision root (Kelvins CAC) | `cosmos/ai/conjunction/` (research) + `adapters.collision_risk` | `python -m cosmos.ai.conjunction.run` (research); `run_pipeline.py` | `outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz` | `collision_risk.csv` | `/risk`, `/api/risk/collision` | `test_conjunction_benchmark` (archive) | **integrated with limitations** | 2,167 anonymised events, `identity_linkable: false`, C4 abstains; no tests import the research module |
| Health root (ESA-ADB) | `cosmos/ai/telemetry/` (research) + `adapters.health_estimates`; `cosmos/health/realdata.py` prepares missions | `python -m cosmos.ai.telemetry.{esa_benchmark,oof_benchmark,…}` (research); `python -m cosmos.datasets prepare esa_ad` | `outputs/benchmarks/telemetry_esa_adb/results.csv`; `data/feature1_health/external/esa_ad/prepared/mission{1,2,3}.npz` | `health_benchmark_arms.csv`; telemetry screens | `/telemetry`, `/api/telemetry/*` | `test_ai` (modules), `test_jint_manuscript`, `test_telemetry_provenance` (archive) | **integrated with limitations** | anonymised missions: no object has telemetry; arm table is a benchmark result; pre-registered freeze verified |
| Debris root (SpotGEO) | `cosmos/ai/vision/` (research) + `adapters.debris_detections` | `python -m cosmos.ai.vision.spotgeo classical`, `train_spotgeo` (research) | saved classical submission JSON; test frames | `debris_detections.csv`; frame PNGs served | `/debris`, `/api/debris/*` | `test_ai` (vision), `test_vision_provenance` | **integrated with limitations** | only the classical front end's hard detections are served (no confidence, no time); learned detectors' scores archived only |
| K7 lifetime benchmark drivers | `cosmos/ai/lifetime/` | `python -m cosmos.ai.lifetime.{run,survival,diagnostics,gate_all,leak_check,cost,catalogue}` | catalogue cohort, density table | `outputs/benchmarks/reentry_lifetime/…`, `outputs/g5d_origin2006/` | none at run time (archived predictions only) | `test_physics_expert`, `test_phase_e`; archive tests `test_g5`, `test_phase_g`, `test_am_design_stage1` | **research/benchmark-only**; full refit **blocked** (5 of 7 backends absent) | predictions cached, no weights; prediction-level reproducibility 0.000e+00; K7 manuscript |
| OPSSAT-AD, SMAP/MSL, learned monitor | `cosmos/ai/telemetry/{opssat,smap_msl,learned_monitor,robustness}.py` | `python -m cosmos.ai.telemetry.opssat --config configs/telemetry/opssat.yaml`, `smap_msl`, `learned_monitor …`, `robustness` | OPSSAT CSV, SMAP/MSL arrays, synthetic telemetry | `outputs/benchmarks/telemetry_opssat*/`, `telemetry_smap_msl/`; 85 OPSSAT checkpoints (`outputs/experiments/…/best.pt`) | none | `test_ai`, `test_e6_branch`, `test_score_cache_preservation` | **archived evidence only** (learned monitor **blocked**: untrained) | K8 withdrawal (X10); `robustness.py` is the only loader of persisted weights; `test_ai` skips the untrained monitor |
| Landmark survival study | `cosmos/ai/survival/landmark.py` | `python -m cosmos.ai.survival.landmark` | `data/feature3_reentry/derived/landmark_*.csv` | `outputs/benchmarks/reentry_landmark/` | none | none found | **independently executable** (archived evidence) | no tests, no weights persisted, not in the console |
| Propagator surrogate | `cosmos/ai/surrogate.py` | `python -m cosmos.ai.surrogate generate|train|evaluate` | simulated propagator data | checkpoints `member_*.pt` (absent) | none | `test_ai` (skipped) | **blocked** (needs training) | checkpoint directory absent; only `spread_threshold.json` present |
| Evidence fusion `decide` | `cosmos/ai/fusion.py` | library | contracts | decision | none (not the deployed path) | `test_fusion_properties`, `test_ai` | **independently executable**; **not** the deployed decision path | KNOWN_LIMITATIONS item 11 |
| Data acquisition, validation, preprocessing | `cosmos/ai/data/`, `cosmos/datasets.py` | `python -m cosmos.ai.data.{download,validate,preprocess_telemetry}`, `python -m cosmos.datasets status|fetch|prepare` | manifests, upstream archives | `data/…`, `data/DATASET_REPORT.{json,md}` | none | `test_ai`, `test_datasets` | **independently executable** | validate run read-only 2026-11-08; downloads checksum-verified and resumable |
| Model cards, benchmark report, dashboard | `cosmos/ai/{registry,report,dashboard}.py` | `python -m cosmos.ai.report`, `python -m cosmos.ai.dashboard --root . --output outputs/dashboard/index.html` | `outputs/benchmarks/*` | `outputs/registry/model_cards.json`, `outputs/benchmarks/SUMMARY.md`, `outputs/dashboard/index.html` | none | `test_dashboard`, `test_p0_wording` | **independently executable** | static artifacts; registry only hashes checkpoints |
| Legacy simulator chain | `cosmos/{health,debris,reentry,pipeline,plots}` | `notebooks/COSMOS_Demo.ipynb` (`cosmos.pipeline.run_pipeline`) | simulated telemetry, SATCAT, GHS-POP grid | an outputs/figures folder created on demand, YOLO datasets | none (synthetic data never mixed with real evidence; `/api/datasets` says so) | `test_verify` (20 physics checks), `test_datasets` | **independently executable** | physics/statistics only; TinyYOLO trains in-process; no weights |
| Prospective (blind) validation | `cosmos/ai/twin/prospective.py`, `scripts/check_t1_later_snapshot.py` | `/prospective`, `/api/prospective` | a catalogue snapshot dated ≥ 2026-11-26 | assessment record | `/prospective` shows BLOCKED | `test_product` (BLOCKED path), `test_console_staleness` | **blocked** (missing data; download needs approval) | outcome coverage ends 2026-10-26, one day before the forecast's as-of date |
| Live ingestion, on-demand inference, per-object health verdicts, collision warnings for named objects, debris-to-object association, impact map, 3-D orbit view | — | — | — | — | the console states each as out of scope | — | **not implemented** (deliberately) | `KNOWN_LIMITATIONS.md` "Deliberately not built"; the data cannot support them honestly |

For every unresolved limitation the table in §13 states what is missing, why it matters, whether it blocks the software
demonstration (none does) or a scientific claim, and the next action.

## 4. Demonstration stages (mandated 16-stage workflow mapped onto the console)

Measured from a fresh process on 2026-11-08: real server (`python scripts/serve_console.py --port 8070 --log-json`, ready after
≈ 1.5 s, every route probed over HTTP, server stopped cleanly on SIGTERM), the in-process rehearsal
(`outputs/audit/demo_rehearsal_release_candidate_20261108T163743+0000.json`, 13/13 ok, 10.7 s) and the API probes recorded in
`docs/product/COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md` §10.

| # | Stage | Page / endpoint | Input | Expected | Actual (measured) | Pass | Limitation shown |
|---|---|---|---|---|---|---|---|
| 1 | Landing page | `/demo` | — | capability map and 13 stages with live values | 200 `text/html`, 19 kB, 1.7 s first load | PASS | capability map labels benchmark-only / unavailable / blocked |
| 2 | Architecture and methodology | `/` readiness panel; `/api/datasets`; methodology blocks on `/telemetry`, `/risk`, `/debris`; `docs/product/PRODUCT_ARCHITECTURE.md` | — | evidence policy, module list, dataset classes | `/api/datasets` 200: catalogue (31,396, NORAD-keyed) and three anonymised benchmark roots; nine modules in the latest run | PASS | architecture diagrams live in the documentation, not in the console |
| 3 | Satellite catalogue | `/objects` | — | catalogue table and search box | 200, 24 kB | PASS | perigee < 2000 km selection of the snapshot |
| 4 | Object selection | `/objects?q=37607`, `/api/objects/search?q=37607` | `37607` | ARIANE 5 R/B | one result: ARIANE 5 R/B, class R, natural decay, perigee 122 km, apogee 11,622 km, incl. 2.46°, p30 1.0 | PASS | — |
| 5 | Orbital state | `/objects/37607` | — | identity and mean elements | 200, 30 kB; elements shown, no state vector | PASS | P5: mean elements only, no position/velocity |
| 6 | Lifetime estimation | `/objects/37607`, `/objects/23806` | — | 37607 coherent interval crossing 30 d; 23806 abstention | 37607 median 27.5 d, coherent, relation `crosses`; 23806 `incoherent` → abstained (L17) | PASS | 123 L17 records abstain |
| 7 | Re-entry forecasting | `/objects/37607`, `/objects/25544`, `/objects/12` | — | p30 1.0 at 10 d; operator abstention; capped quantiles | 37607 p30 = 1.0, quantiles 10.0 d (zero-width, `degenerate`); 25544 `operator_controlled`, p30 0.00528 base rate, no quantiles; 12 quantiles 1826.25 d (`at_cap`), p30 0.0 | PASS | variants shown side by side, not averaged |
| 8 | Uncertainty and intervals | same pages, `interval_quality` | — | labelled interval kinds | 23806: 5–95 % Monte-Carlo spread 1.1–202.5 d (`spread`); labels `zero-width`, `at the cap`, `unavailable` where applicable | PASS | P11: Monte-Carlo spread is not a conformal interval |
| 9 | Conjunction / collision | `/risk`, `/api/risk/collision?limit=2` | — | Kelvins benchmark, never attributed | 2,167 events, model `cosmos_gated`, `identity_linkable: false`, escalation abstains (C4) | PASS | benchmark-only, anonymised |
| 10 | Health / telemetry | `/telemetry`, `/api/telemetry/missions`, `/api/telemetry/1/channel_1?max_points=50` | mission 1, channel_1 | three anonymised missions, real samples, ground-truth intervals | missions 1/2/3 (76/100/48 channels, 1.47 M / 0.92 M / 0.93 M samples, `anonymised: true`); channel returned 50 of 1,472,832 samples, stride 29,457 | PASS | P2: no catalogue object has telemetry; no per-sample score |
| 11 | Debris / imagery | `/debris`, `/debris/1`, `/api/debris/1/frame/1.png` | sequence 1 | classical detections drawn, learned scores only | sequence 1: 5 frames, 26 detections, `confidence_available: false`; frame PNG 200 `image/png` 131,763 B | PASS | P7: no confidence, no absolute time, no object association |
| 12 | Provenance and data sources | `/twin-state`, `/runs/run_20261108T121517Z`, `/api/ready` | — | digests, lineage, source policy | twin state `reemitted / primary / verified` (sha `6bb4871f…`), 31,396 records, equivalence 31,396/31,396; run manifest lists code revision, config digest `ff03cc1b…`, input hashes per module | PASS | P14: dirty worktree flagged `MODIFIED` |
| 13 | Decision support | `/objects/37607` Decision priority; `/api/runs/run_20261108T121517Z/ranking?limit=2` | — | rank from the recorded rule | 37607 rank 2 of 31,396; rule `p_reentry_30d × 2 if mass ≥ 500 kg` read from the manifest; top row NORAD-32730 score 2.0 | PASS | L12-style caveat: point probability, not the interval; effectiveness only on the non-blind T1 window |
| 14 | Scenario and policy comparisons | `POST /api/scenario` (fast preset), `/compare?a=…&b=run_20261108T083402Z`, `/objects/25544?policy=archived_only` | fast preset: limit 500, chain modules | new run, status, assumptions; identical tables by digest; explicit archived read | run `run_20261108T184949354706Z` successful in 2.9 s, child process exit 0, seven assumptions listed; compare: all tables byte-identical; archived_only → `explicit_archived` (amber) | PASS | P18: synchronous; scenario re-expresses saved artifacts only |
| 15 | Readiness and limitations | `/api/ready`, `/prospective`, `docs/product/KNOWN_LIMITATIONS.md` | — | ready record; prospective BLOCKED | `ready: true`, forecast digest verified, complete run present, twin source reemitted/primary; prospective `BLOCKED` (outcome coverage ends 2026-10-26) | PASS | P6/L3b: prospective validation blocked |
| 16 | Final integrated summary | `/demo` stage 13 | — | established vs out-of-scope list | rendered; rehearsal stage 13 ok (103 ms) | PASS | states live data, inference, health verdicts, warnings, association and prospective validation as out of scope |

Error handling, same server: `/objects/99999999` → 404 `text/html`; `/api/objects/99999999` → 404 `application/json`
(`data_unavailable`); `/nonexistent` → 404 HTML; `POST /api/scenario` with `{"limit": "abc"}` → 422 JSON detail, no run
executed; `/objects/abc` → 422 HTML; every response carries `X-Request-ID`. No unhandled exception appeared in the server log
(85 JSON lines).

## 5. Test commands and results (final, at Commit B; no code changed in Commit C)

| Suite / check | Command (cwd `/data2/anupa/Final_Year_Project`, `.venv` Python 3.12.16) | Result | Record |
|---|---|---|---|
| Full suite | `python -m pytest tests/ -q -rs -p no:cacheprovider` | **508 passed, 3 skipped, 0 failed** in 129 s | `outputs/audit/pytest_full_20261108_post_commit_b.log` |
| Skips (all optional artifacts, pre-existing) | — | `tests/test_ai.py:51` ×3: baseline code snapshot missing; learned telemetry backend not trained (`python -m cosmos.ai.telemetry.learned_monitor train`); surrogate footprint not trained (`python -m cosmos.ai.surrogate train`) | same log |
| New tests introduced in this release | `python -m pytest tests/test_approved_head.py -q` | 13 passed (approved-head predicate: checkpoint, descendants, ancestor rejected, orphan rejected, malformed refs rejected, hash checks unchanged) | in suite |
| Figure release + approved head | `python -m pytest tests/test_figures.py tests/test_approved_head.py -q` | 52 passed | — |
| Demonstration protocol + journey | `python -m pytest tests/test_demo_workflow.py tests/test_e2e_demo_journey.py -q` | 29 passed in 13.8 s | — |
| JINT manuscript tests | `python -m pytest tests/test_jint_manuscript.py -q` | 16 passed | — |
| Manuscript claim audit | `python scripts/audit_manuscript_claims.py --json outputs/audit/manuscript_claim_audit_release_candidate.json` | 147 checks: 139 PASS, 8 NOT_EVALUABLE, 0 FAIL | `outputs/audit/manuscript_claim_audit_release_candidate.json` |
| Protected artifacts | `python scripts/verify_protected_artifacts.py --label post_commit_b_manifest` | `all_protected_ok: True` (figure manifest 107/107, both twin digests, OPS-SAT 10/10, ESA-ADB freeze 28/28, G5d, `head_ok` with approved ancestor `78ee339`) | `outputs/audit/protected_artifacts_post_commit_b_manifest_20261108T184316+0000.json` |
| Twin-state integrity and equivalence | `python scripts/twin_state_integrity.py` | `primary_verified`; integrity ok; equivalence computed 31,396 / 31,396 equal | `outputs/audit/twin_state_integration_check_20261108T152934+0000.json` |
| Rehearsal (fresh process) | `python scripts/rehearse_demo.py --label release_candidate` | 13/13 ok, 10.7 s, RSS end 332 MB | `outputs/audit/demo_rehearsal_release_candidate_20261108T163743+0000.json` |
| Real server, fresh process | `python scripts/serve_console.py --port 8070 --log-json` + `curl` sweep | ready in ≈ 1.5 s; 32 routes 200 with correct content types; 404/422 paths correct; stopped cleanly | `outputs/audit/serve_console_fresh_process_20261108.log` |
| Fresh clone + LFS (local remote) | see release proposal §7 | 831/831 LFS files, `git lfs fsck` OK, twin state sha `6bb4871f…` identical, console reads it as primary/verified | `outputs/audit/fresh_clone_lfs_verification_post_commit_a_20261108T153148+0000.json` |

No failure is pre-existing or introduced: the only failing test of the release candidate (the exact-match approved-head
predicate) was corrected with the owner's approval in Commit B and is covered by regression tests. No assertion was weakened,
no expected value changed, no test skipped to obtain the result.

## 6. API and frontend verification

Real-server sweep (HTTP, fresh process): 18 page requests 200 `text/html`, 12 API requests 200 `application/json`, `/docs` and
`/openapi.json` 200, `/static/console.css` 200 `text/css`; browser 404s render `error.html`, API 404s return JSON; validation
errors are 422 (HTML for browsers, JSON for `/api/*`); `X-Request-ID` on every response. The OpenAPI document lists 23 API
operations and 17 page routes (table in the execution guide §10). Route conventions verified: run tables are addressed with
their file name (`/api/runs/{run_id}/tables/decision_ranking.csv`), telemetry missions by number (`/api/telemetry/1/channels`).

## 7. Demonstration object verification (fresh process, 2026-11-08)

| NORAD | Name | Regime / class | Re-entry | Lifetime | Priority | Twin vs chain |
|---|---|---|---|---|---|---|
| 37607 | ARIANE 5 R/B | natural decay, rocket body | p30 1.0; quantiles 10.0 d, zero-width (`degenerate`), relation `entirely_before` | median 27.5 d, coherent, `crosses` | rank 2 of 31,396 | equal on 20 of 20 fields |
| 23806 | TITAN 34B DEB | natural decay, fragment | p30 0.71875; median 20 d, 5–95 % spread 1.1–202.5 d | `incoherent` → abstained (L17) | rank 21 | equal on 14 of 14; lifetime not comparable (L17) |
| 25544 | ISS (ZARYA) | operator controlled, payload | abstention; base rate 0.00528; no quantiles (`unavailable`) | unavailable | rank 55 | equal on 10 of 10; abstention represented differently (C3), values compared |
| 12 | VANGUARD R/B | natural decay, rocket body | p30 0.0; quantiles 1826.25 d (`at_cap`, `censored_at_cap`) | median 1,708 d, `entirely_after` | rank 13,903 | equal on 20 of 20 |

## 8. Dataset and model availability

Prerequisite checker (`python scripts/check_console_prerequisites.py --json`, exit 0): required packages present (fastapi
0.162.0, uvicorn 0.54.0, jinja2 3.1.6, pandas 3.1.0, numpy 2.3.5); required artifacts present (forecast table and digest);
optional artifacts present (ESA-ADB prepared missions, SpotGEO test frames and saved detections, Kelvins test predictions,
ESA-ADB results, X6 Stage 1 results, 89 pipeline runs). Optional backends absent and never needed to serve the console:
`statsmodels`, `lightgbm`, `catboost`, `tabm`, `tabicl`, `kumo`, `pymsis`. No persisted model weights are loaded by the runtime
(the twin reader reports `model_version: unavailable` everywhere); the registry's checkpoint references point outside this
workspace (limitations register L13). Datasets carried in Git LFS and those that must be fetched locally are listed in the
execution guide §5 with their manifest (`data/DATASET_MANIFEST.csv`, 62 entries with SHA-256).

## 9. Performance (both definitions, final code)

| Definition | Measurement | Target | Met |
|---|---|---|---|
| Benchmark sequence, overview page cold / warm (`scripts/benchmark_console.py`) | 180 ms / 37 ms | 400 ms | yes |
| Benchmark sequence, peak RSS | 225 MB | 250 MB | yes |
| Fresh process, import of `cosmos.product.api` | 534 ms (median of 5) | — | — |
| Fresh process, store steps + first overview page (import excluded) | ≈ 553 ms (provenance 52, run list 52, prospective assessment 186, catalogue 59, twin selection 98, page 76) | 400 ms | **no** |
| Fresh process, first `/api/twin-state` (stream 78 MB archive + compare) | 1,492 ms, then cached | — | — |
| Fresh process, peak RSS incl. twin-state streaming and object page | 273 MB | 250 MB | **no** |

Records: `outputs/audit/console_benchmark_release_candidate_20261108T164637+0000.json`,
`outputs/audit/console_cold_profile_release_candidate_20261108T164707+0000.json`. The fresh-process gap is unchanged from
Phase F and is reported, not re-targeted.

## 10. Protected-artifact and manifest verification

Figure release manifest `paper/figures/RELEASE_MANIFEST.json`: re-issued on 2026-11-08 (final generation 18:43 from a clean
index at Commit B) with 105 of 107 entries identical to the 2026-11-06 freeze, which is preserved as
`RELEASE_MANIFEST_2026-11-06.json`; the two changed documents are the manuscript and `tests/test_figures.py`; the supersession
chain of the same-day intermediate re-issues is recorded in the manifest's `reissue` block. Verifier at Commit B:
`all_protected_ok: True`. Twin digests: archived `twins.jsonl` `19a1fede…` and re-emitted `twins.jsonl` `6bb4871f…` unchanged.

## 11. Fresh-process validation

Server start to `GET /api/ready` 200 in ≈ 1.5 s; rehearsal 13/13 from a new interpreter; cold profile from five fresh
subprocesses; the four demonstration objects and the full route sweep were read from a new process; the local fresh clone
retrieved all LFS objects and read the twin state as primary. Remote fresh-clone retrieval is **not possible yet** because
nothing has been pushed (the twin-state LFS object is absent from GitHub).

## 12. Known limitations (preserved; none resolved by this release)

Scientific: ESA-ADB and Kelvins CAC are anonymised, so no NORAD identity mapping exists (L1); health, collision and debris
evidence is never attributed to a catalogued object; space-weather features are constant across the 31,396-object snapshot;
cross-satellite generalisation and health-to-conjunction fusion are not established (C4 abstains); re-entry variants disagree
(up to 10.6× in expected 30-day counts); 123 L17 lifetime records are incoherent and abstained; isotonic probabilities disagree
with quantile outputs for some objects (coherent reading reported separately); design-derived area-to-mass objects are
under-covered (0.5625 vs 0.80 at origin 2016); archived evaluations are not prospective validation (prospective mode BLOCKED
until a snapshot dated ≥ 2026-11-26); the deployed priority uses the point probability, not the interval; `fusion.decide` is
not the deployed decision path. Engineering: no live ingestion, no on-demand inference, no model weights, several learner
backends unavailable (training-level reproducibility 2 of 7 learners), no authentication, single process, synchronous scenario,
no PNG screenshots (headless browser not installed), fresh-process performance targets not met.

## 13. Outstanding blockers

| Blocker | Type | Blocks the software demonstration? | Blocks a scientific claim? | Next action |
|---|---|---|---|---|
| Commits C and D, then the tag | owner approval | no | no | approve each staged set as presented |
| Push of branch, tag and LFS objects | owner approval | no (local demo complete) | no | separate approval; then re-run the fresh-clone retrieval from GitHub |
| Author-only manuscript fields, licence, data DOI, venue | author | no | no (submission readiness only) | fill §23 of the JINT manuscript and the K7 Statements; choose a licence |
| Thesis DOCX/PDF rebuild | external toolchain (pandoc 3.11, pandoc-crossref, LibreOffice absent) | no | no | install the toolchain per `thesis/README.md` and run `thesis/tools/render.py` |
| Prospective (blind) validation | data (snapshot ≥ 2026-11-26) + download approval | no (mode shows BLOCKED) | yes, for any prospective claim | download the later snapshot when it exists, then run the prospective mode |
| Learner backends (`kumo`, `tabm`, `tabicl`, `lightgbm`, `catboost`) | dependencies | no | yes, for training-level reproducibility and X6 Stage 2 | install with approval and refit from the recorded configurations |

## 14. Final acceptance decision

**PASS WITH LIMITATIONS.**

The application starts from a fresh process with the documented commands, every page and API route works with the correct
status and content type, the sixteen demonstration stages pass against the archived evidence, the four demonstration objects
show the documented values, the full suite passes (508 / 3 skipped / 0 failed) without any weakened test, the manuscript
claim audit has zero failures, the protected artifacts and the figure manifest verify, and the twin state is byte-identical in
a fresh clone. The limitations are the ones the project has always stated: the fresh-process performance targets are not met,
prospective validation is blocked by data, the thesis binary formats need an external toolchain, the author-only fields remain
the author's, and the GitHub release (push, remote LFS retrieval) awaits the owner's separate approval. None of these hides a
failure; each is labelled where it appears.
