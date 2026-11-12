# COSMOS-AI — P2 implementation plan: console integration and demonstration readiness

Date 2026-11-08 · HEAD `78ee339` · **plan only — no application code was modified for this document.**
Baseline re-verified before writing: protected artifacts all OK
(`outputs/audit/protected_artifacts_p2_plan_20261108T071706+0000.json`), 0 staged, suite 386 passed /
3 skipped (P1 log), archived twin state sha `19a1fede…` unchanged, re-emitted state sha `6bb4871f…`
(31,396 records). Nothing below changes scientific methodology, retrains, regenerates, or claims live
inference; the system stays a **read-only evidence twin**.

---

## 1. Updated architecture assessment (revalidated after P1)

What the 2026-11-08 audit said still holds, with these revisions:

| Audit statement | Status after P0/P1 | Evidence |
|---|---|---|
| Runtime chain = `catalogue_state → lifetime → reentry → decision_priority`, reading one archived table | **unchanged** | `scripts/run_pipeline.py --list`; adapters untouched except the shared column constant |
| No model runs at prediction time; no live source | **unchanged** | `MODULE_EVIDENCE_CLASS`; `/api/datasets.evidence_policy.live_sources = "none connected"` |
| Twin state `twins.jsonl` never read at runtime, no provenance | **partly superseded**: a versioned re-emission with per-output provenance now exists (`outputs/twin/as_of_2026-10-27_reemitted_v1/`, `twin_state/1.1`, value-equivalent) — but **no runtime component reads either state file** (grep: no consumer in `cosmos/product`, adapters or `run_pipeline`) | `cosmos/ai/twin/reemit.py`; P1 report §3 |
| Model version never set | **unchanged, now stated**: every output carries `model_version.status = "unavailable"`; `VERIFIED_MODEL_CARD_ASSOCIATIONS = {}` | P0.2 |
| Decision ranking uses the point probability only | **unchanged**; the interval-vs-horizon relation is now displayed next to it (display only) | P1.1 |
| Registry (20 cards) not linked to outputs | **unchanged** by design (no verified association exists) | P0.2 |
| Health module = benchmark-arm table | **unchanged**; labelled as such on run page, datasets and overview | P0.3 |
| Freshness = overview STALE only | **superseded**: object-level freshness (observation / archive / processing) in API, page, report | P1.4 |
| Schema: required-column sets, no versions | **superseded**: `cosmos/ai/schema.py`, seven families, legacy = 1.0 | P1.3 |

**Runtime components (execute on request):** `Orchestrator` + 7 adapters (archive readers), `ArtifactStore`
(forecast table, run tables, prepared telemetry arrays, SpotGEO frames, conjunction npz, X6 record),
FastAPI routes (34 GET + 1 POST), `reports.object_report`, `run_pipeline.main` (via `/api/scenario`).
**Archived-only components:** dated forecast and both twin-state files, all study outputs, couplings,
prospective T1, registry cards, dashboard/report scripts. **Disconnected benchmark roots:** ESA-ADB
telemetry (anonymised missions), Kelvins conjunction events (anonymised), SpotGEO detections (pixels,
no time) — none joinable to a NORAD object; each abstains explicitly.

## 2. Current console capabilities (verified by request on 2026-11-08)

| Journey step | Route(s) | Status | Backed by |
|---|---|---|---|
| Select an object | `/objects`, `/api/objects/search` | works | forecast table (31,396) |
| Identity + available evidence | `/objects/{norad}`, `/api/objects/{norad}` | works; telemetry and conjunction reported `available: false` with the identity reason | `store.object_record` |
| Source, observation time, freshness | same; `freshness` block | works (archive time honestly `missing`) | P1.4 |
| Versioned twin state | — | **not available**: no route reads `twins.jsonl` (archive or re-emitted) | gap G1 |
| Lifetime interval + 30-day relation | object page, report, `/api/runs/{id}/ranking`, run page | works | P1.1 |
| Subgroup reliability warning | object page, report | works for design / class-prior; unknown stated | P0.1 |
| Re-entry information | object page, report | works; operator-controlled objects show the abstention and base rate | store |
| Decision-priority calculation | run page ranking table, report `computed_outputs` | **partial**: the number is shown, the formula is not explained; the object page shows no priority at all | gap G2 |
| Output provenance / model version | object page, run page, report | works (artifact sha, run id, git, config; model version UNAVAILABLE) | P0.2 |

## 3. Remaining integration gaps

| # | Gap | Why it matters for the demonstration | P2 action |
|---|---|---|---|
| G1 | No twin-state view; the versioned record (identity, orbit, physical, family, space weather, two outputs with provenance) is invisible | the "twin" of the title cannot be shown | `store.twin_record(norad)` reading the **re-emitted** file through a one-time line-offset index; object-page panel "Twin state (twin_state/1.1, re-emitted from archive)" with source record pointer and equivalence note; `/api/objects/{norad}/twin` |
| G2 | Decision priority not explained; object page has no priority | step 9 of the journey fails | `store.priority_for_object(run_id, norad)` returning the run's row plus a **derived-from-run-constants** explanation (`consequence_mass_kg` is in the run manifest outputs; formula text from one place); object-page panel and report row; no recomputation of priority |
| G3 | Health labels: `telemetry.html` heading "Health model evidence", object section "Telemetry and health", nav "Satellite Intelligence" | semantic risk (Stage 3) | rename labels (see §4); no logic change |
| G4 | Object page reads the forecast table directly while reports merge the latest run — consistent today (same artifact) but unlabelled | API/UI consistency | show on the object page which run's outputs the report would cite (run id + as-of match flag), reusing `store.latest_run_id` |
| G5 | Unavailable-module handling is tested for the pipeline but not surfaced per object | step 13 of the acceptance list | object-page "evidence availability" strip derived from `object_record` flags (telemetry, conjunction, debris, health: all *not applicable* by identity) + run module statuses |
| G6 | Demonstration protocol document (`DEMO_SCRIPT.md`) predates P0/P1 (section "Satellite health assessment") | would mislead a presenter | rewrite as the Stage 5 protocol; retire the health-assessment section |

## 4. Health-screen semantic audit (Stage 3)

Classification of every health-related element found in `cosmos/product/`:

| Element | Current wording | Category | Verdict / P2 change |
|---|---|---|---|
| nav `Satellite Intelligence` → `/telemetry` | anonymised ESA-ADB missions | **B** (benchmark telemetry) | keep route; relabel nav to **"Telemetry Benchmarks"** and page title "Telemetry anomaly benchmarks (anonymised missions)" |
| `telemetry.html:48` "Health model evidence — saved ESA-ADB benchmark arms" | heading | **C** (independent model-evaluation outputs) | rename **"Anomaly-detection benchmark arms (ESA-ADB) — detection scores, not spacecraft health"**; body line 76 already says so |
| `channel.html:114` "not a health verdict for this channel" | correct | B | keep |
| `object.html:221` "Telemetry and health" + UNSUPPORTED reason | section | **D** (unavailable) | rename **"Spacecraft health — not determinable"**, state: *no telemetry is linkable to this object; no subsystem health exists for it; no score is synthesised* |
| run page module `health` | "archived benchmark-arm detection scores — not a spacecraft health state" | C | keep; add the same evidence-class text to the module-status table on the overview |
| `health_benchmark_arms.csv` (`event_wise_f05`, `score_semantics`, `alarm`) | run table | C | keep name (schema stability); P2 labels the table "benchmark arms" wherever listed |
| `/api/health` | app liveness, "unrelated to satellite health" | — | keep |
| `risk.html:92–94` "No health-driven escalation" (C4 abstains) | D | keep |
| Legacy simulator `cosmos/health` (subsystem faults, synthetic) | not served by the console | **A — synthetic only** | must stay out of the console; the overview already states synthetic data is never shown |
| Registry OPS-SAT cards | "benchmark arm … not a spacecraft health assessment" (P0.3) | C | keep |

Category **A (actual spacecraft subsystem health)** has **no real-data instance anywhere** in COSMOS-AI;
the console must say so per object (G3) and must never synthesise a score. No change to any evidence.

## 5. Proposed user journey (built only on existing evidence)

1. **Open** `/` — evidence boundary, read-only evidence twin, STALE finding (snapshot age), latest run.
2. **Select** — `/objects` search → `/objects/37607` (primary demo object: ARIANE 5 R/B, design-derived,
   natural decay, rank 1, p₃₀ = 1.0, re-entry interval 10/10/10 d, lifetime 6.9/27.5/95.3 d).
3. **Identity and evidence availability** — class, regime, elements (mean elements; state vector *not
   available*), evidence strip: catalogue ✓, lifetime ✓, re-entry ✓, telemetry ✗ (identity), conjunction ✗
   (identity), debris ✗ (no object identity), spacecraft health **not determinable** (G3/G5).
4. **Source, observation time, freshness** — snapshot 2026-10-27 (SATCAT data date), canonical epoch
   2011-05-23, archive time missing (stated), processing time of latest run, STALE.
5. **Versioned twin state** (G1) — the `twin_state/1.1` record: two outputs (physics-history re-entry,
   lifetime comparison), each with provenance (source sha, code revision, transformation digest,
   model version unavailable), source row pointer, "re-emitted from archive; equivalent to the archived
   record".
6. **Lifetime interval vs 30-day horizon** — CROSSES HORIZON (6.9–95.3 d), nominal wording.
7. **Subgroup reliability** — SUBGROUP UNDER-COVERAGE: design-derived; 2016 @80 % 0.5625 [0.512, 0.614]
   vs 0.80; 2011 0.792; descriptive, not individual, not extrapolated.
8. **Re-entry** — p₃₀/p₉₀/p₁yr = 1/1/1, quantiles 10 d, BEFORE HORIZON, Monte-Carlo spread note, variants.
9. **Decision priority** (G2) — rank 1 of 31,396; priority 2.0 = p₃₀ 1.0 × 2 (mass 5,000 kg ≥ 500 kg);
   health escalation ABSTAIN (C4); interval cue shown beside it.
10. **Provenance and model version** — artifact sha `b15644…`, run id, git `78ee339`, config digest,
    model version UNAVAILABLE with reason; report export `/reports/object/37607`.

Secondary objects for edge paths: **23806** TITAN 34B DEB (class-prior fragment; crossing interval
1.1–202.5 d; L17-incoherent lifetime record → lifetime ABSTAIN), **25544** ISS (operator-controlled →
re-entry abstention with previous-window base rate, no quantiles), **12** VANGUARD R/B (at-cap
censored interval). All four are real catalogue objects in the archived snapshot.

## 6. Demonstration acceptance criteria (Stage 4 — tests to add)

New file `tests/test_demo_workflow.py` (real archived evidence as principal source; synthetic roots only
for edge cases, never labelled as observations):

| # | Criterion | Assertion sketch |
|---|---|---|
| D1 | Object selection | search "ARIANE" / id 37607 → 200; unknown id → explicit absence (exists: `test_02b`) |
| D2 | Twin-state retrieval (G1) | `/api/objects/37607/twin` returns the `twin_state/1.1` record whose values equal the archived record (canonical compare), `reemitted_from_archive: true` |
| D3 | Versioned provenance display | page shows source sha, transformation digest prefix, "re-emitted", model version UNAVAILABLE |
| D4 | Lifetime interval + horizon | CROSSES HORIZON for 37607; BEFORE HORIZON re-entry; AT CAP for 12 |
| D5 | Subgroup under-coverage | 0.5625 / [0.512, 0.614] / nominal 0.80 on page and report (exists: P0 tests) |
| D6 | Unknown A/M source | `subgroup_coverage_cue(None, …)` → unknown, not inferred (exists) + a synthetic-root object record fixture with `am_source` blank renders "unknown" |
| D7 | Missing provenance | synthetic run without git/config → "unavailable" (exists: P0 lineage) |
| D8 | Missing / stale evidence | freshness stale on real snapshot; missing orbit epoch fixture; archive time missing (exists: P1.4) |
| D9 | Re-entry availability | 37607 quantiles present; 25544 abstention with reason and base rate; no substitution |
| D10 | Decision priority (G2) | object page shows rank, priority 2.0, formula text with `consequence_mass_kg` from the run manifest; value equals `decision_ranking.csv` row; C4 ABSTAIN |
| D11 | Archived vs synthetic labelling | overview text; `/api/datasets.evidence_policy`; no synthetic data served (exists: P0.3) |
| D12 | API/UI consistency | for 37607: every numeric field shown on the page (p₃₀, quantiles, priority, coverage figures) equals the API value; report `computed_outputs` equal run table rows |
| D13 | Unavailable modules | synthetic root with `lifetime` failed → object page shows priority "not computed: lifetime blocked"; run page shows blocked; nothing substituted (extends `test_06`) |
| D14 | Health semantics (Stage 3) | object page contains "not determinable" and never "health score"; telemetry page heading contains "not spacecraft health"; registry cards unchanged (P0.3) |

Pass condition: all D1–D14 green on the real archive; full suite green; protected artifacts unchanged.

## 7. Implementation phases and effort (P2 = essential; P3 = optional / external; Future inference)

### P2 — essential console integration

| # | Task | Files / functions | Depends on | Acceptance | Risk | Effort |
|---|---|---|---|---|---|---|
| P2.1 | Twin-state reader + panel + API (G1) | `store.py`: `TWIN_STATE_REEMITTED` path, `_twin_index()` (lru_cache: object_id → byte offset, built once, ~1 s), `twin_record(norad)`; `api.py`: `/api/objects/{norad}/twin`, pass to `page_object`; `object.html` panel; `reports.py` `twin_state` block | re-emitted artifact present (fallback: archived v1.0 record labelled "archived, no provenance") | D2, D3; record equals archive by value; no write | low; 78 MB file read lazily | 1 d |
| P2.2 | Decision-priority panel + explanation (G2) | `store.priority_for_object(run_id, norad)` (row from `decision_ranking.csv` + `consequence_mass_kg` from manifest outputs + formula text); `api.py` include in `/api/objects/{norad}` as `decision_priority` (latest run) ; `object.html`; `reports.py` row | latest complete run | D10, D12; priority never recomputed in UI | low | 0.5 d |
| P2.3 | Health-screen relabelling (G3) | `base.html` nav label, `telemetry.html` heading/title, `object.html` section, overview module-status text | — | D14; `test_p0_wording` extended | none | 0.25 d |
| P2.4 | Evidence-availability strip + unavailable-module surfacing (G5, G4) | `store.evidence_availability(record, run_manifest)`; `object.html`; `api.py` field `evidence_availability` | P2.2 | D13; blocked module → explicit text | low | 0.5 d |
| P2.5 | Demonstration tests `tests/test_demo_workflow.py` | new | P2.1–P2.4 | D1–D14 | — | 1 d |
| P2.6 | Demonstration protocol `docs/product/DEMONSTRATION_PROTOCOL.md` + retire `DEMO_SCRIPT.md` §3 | docs | P2.1–P2.5 | Stage 5 content; every expected output cross-checked by a test | none | 0.5 d |

Total P2 ≈ 3.75 engineer-days. No change to adapters, orchestrator, `decision_priority`, archives, or
scientific outputs.

### P3 — optional and external-data-dependent

| # | Task | Dependency | Effort |
|---|---|---|---|
| P3.1 | Runtime reader for the re-emitted twin state in the orchestrator (a `twin_state` module that *loads* records instead of rebuilding them from the table) | design choice; no scientific change | 1 d |
| P3.2 | Compare-runs view diffing table values (KNOWN_LIMITATIONS P21) | — | 1 d |
| P3.3 | Pagination / filtering in `/objects` and tables (P22) | — | 1 d |
| P3.4 | Ingest a later SATCAT snapshot (≥ 2026-11-26) → prospective evaluation screen becomes READY | external data; approval | 1 d after data |
| P3.5 | Rebuild the SpotGEO front-end cache (~1 h CPU) so debris screens can show a re-run at new operating points | compute approval | 0.5 d |
| P3.6 | Remaining 3b cells after the two protocol decisions; am_design Stage 2 with the substitute learner | user decisions / approval | hours |
| P3.7 | Visual regression of rendered screens | headless browser (blocked: install needs approval) | 0.5 d |

### Future inference (separately approved; see P1.5 proposal)

Model persistence for xgboost/mlp/physics/gate/CQR/isotonic/AR(8) in future study runs; backend
installation under a recorded environment (`statsmodels`, `tabm`, `kumo`, `tabicl`, `lightgbm`,
`catboost`); an explicit opt-in adapter inference mode with digest verification; only then may the
console show a recorded model version. Until then the system is, and is labelled, a read-only evidence
twin.

## 8. Test strategy

* Keep the three layers already in place: contract/unit (`test_contracts`, `test_fusion_properties`,
  `test_p1_schema`), integration on real artifacts (`test_integration`, `test_twin_state_consistency`,
  `test_p1_reemission`), console behaviour on a disposable root (`test_product`, P0/P1 tests).
* Add `tests/test_demo_workflow.py` implementing D1–D14 as one ordered journey on NORAD 37607 plus the
  three edge objects; every numeric assertion reads the expected value from the archive or run table,
  never from a literal copied into the test except the X6 figures already pinned.
* Synthetic fixtures (`synthetic_root`, `_write_run`) only for failure modes (blocked module, malformed
  manifest, missing epoch); each fixture labelled "fixture" in its manifest `interpretation`.
* Full suite after each P2 task; protected-artifact verification before and after the phase
  (`scripts/verify_protected_artifacts.py --label p2_{before,after}`); `outputs/pipeline/` count unchanged.

## 9. Dependencies and risks

| Risk | Mitigation |
|---|---|
| Twin-state file (78 MB) read per request | one-time offset index cached in the store; record fetched by seek; fallback to the archived v1.0 file labelled as such |
| Object page and report diverge (object page = snapshot; report = snapshot + latest run) | P2.2/P2.4 show the referenced run id and an as-of match flag on the object page from the same store call the report uses; D12 asserts equality |
| Relabelling breaks existing tests that assert old strings ("Telemetry and health", "Satellite Intelligence") | update those assertions in the same change; run the suite |
| Demonstration drifts from code | every "expected output" in the protocol is backed by a D-test; the protocol lists the test names |
| Temptation to synthesise a health score or a "live" badge | forbidden by Stage 3 and `test_p0_wording`; D14 adds the per-object "not determinable" assertion |
| Absent backends | not needed by any P2 task |

## 10. Changes requiring further approval (not part of P2)

1. Any **model execution at request time** (adapter inference mode) — needs the P1.5 persistence work,
   backend installation and a separate approval.
2. **Installing** `statsmodels`, `tabm`, `kumo`, `tabicl`, `lightgbm`, `catboost`, `pymsis`, or a
   headless browser.
3. **Ingesting new data** (later SATCAT snapshot; Space-Track element histories).
4. **Any re-run of studies**: remaining 3b cells (protocol decisions first), am_design Stage 2 substitute,
   X3, X13, vision front-end cache rebuild, full twin-state regeneration (blocked anyway by `tabm`).
5. **Changing the ranking formula, thresholds, Mondrian groups, or any calibration** — methodology; out of
   scope for engineering.
6. **Committing or pushing** anything.

Implementation of P2.1–P2.6 starts only on explicit approval of this plan.
