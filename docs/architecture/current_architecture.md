# Current COSMOS-AI architecture

Audit snapshot: repository HEAD `78ee339` on `main`, 2026-11-03. This is an as-is
description; the repository already contains uncommitted dataset-restoration changes that
are not part of this audit.

## Architecture at a glance

```text
Public datasets and local snapshots
  ├─ telemetry: ESA-ADB, OPSSAT-AD, NASA SMAP/MSL
  ├─ imagery: SpotGEO; separate synthetic imagery
  ├─ orbital/catalogue: GCAT, CelesTrak, observed space weather
  └─ conjunction: ESA Kelvins CAC (anonymised CDMs)
          │
          ├─ cosmos/ai/data/       download, manifest, status, validation, preprocessing
          ├─ cosmos/ai/telemetry/  health/anomaly benchmarks and alarm studies
          ├─ cosmos/ai/vision/     real SpotGEO and synthetic image detection
          ├─ cosmos/ai/conjunction/ collision-risk forecast from CAC messages
          ├─ cosmos/ai/lifetime/   catalogue lifetime, drag physics, learners, calibration
          ├─ cosmos/ai/twin/       dated records, re-entry serving, C2/C3/C4 and T1
          ├─ cosmos/ai/uncertainty.py, fusion.py, registry.py
          └─ legacy cosmos/health, cosmos/debris, cosmos/reentry, cosmos/pipeline.py
```

The current system is a collection of task-specific pipelines plus a dated re-entry twin.
It is **not** a single, fully joined model or uniformly orchestrated execution graph. Public
data do not identify the same spacecraft across telemetry, conjunction, and catalogue
sources. The legacy simulator chain is a separate demonstration and must not be conflated
with the real-data-validated AI studies.

## Component status

Status terms follow the audit request. `QUANTITATIVELY_EVALUATED` means a reported
measurement exists, not that the result has independent scientific confirmation.
`INDEPENDENTLY_VALIDATED` is reserved for an independent dataset or authoritative
ground-truth validation beyond the development evaluation; none of the end-to-end twin
couplings meets that standard.

| Component | Evidence and status |
|---|---|
| Dataset download, manifests, status and validation | **IMPLEMENTED, EXECUTABLE, UNIT_TESTED**. Manifest/status checks and content validation are in `cosmos/ai/data/`; tests are in `tests/test_datasets.py`. Current status checks presence and size, not content hashes on every status query. |
| Telemetry health/anomaly studies | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** on ESA-ADB, OPSSAT-AD and SMAP/MSL. Preprocessing, metric, leakage and protocol tests exist in `tests/test_ai.py`. Some benchmark rows are single-seed; the separate ESA-ADB study is not uniformly a multi-seed confirmatory study. No independent operational deployment validation. |
| Real debris imagery (SpotGEO) | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** on the benchmark. Independent observing-condition/generalisation validation is absent. A scorer boundary-condition audit was flagged; do not treat synthetic imagery results as real-world evidence. |
| Synthetic imagery path | **PARTIALLY_IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** only on generated data. The current dataset validator reports the empty expected synthetic train/validation/test image splits as incomplete. This does not support real-imagery claims. |
| Orbital lifetime / re-entry at canonical epochs | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** on two forward temporal periods. Includes drag Monte Carlo, learned experts, censoring-aware baselines and calibration. Tests protect shared AI primitives, but automated tests do not cover the twin engine and coupling protocols as a complete workflow. **Defect found 2026-11-04 (L17):** the saved per-horizon *calibrated* columns `p_lifetime_{30d,90d,1yr}` are not a coherent CDF for 123/13,238 objects, because `engine.py` calibrates each horizon with an independent isotonic regressor. The final reported `p_*` columns are unaffected. |
| Conjunction risk from CAC CDMs | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** on the official held-out dataset. It estimates final-CDM log collision probability; operational prioritization is distinct and not independently established. |
| Dated twin/re-entry serving | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** through C3/T1 analyses. It writes dated per-object outputs and uncertainty/validation fields. The as-of window is not blind, and the 2026-10-27 forecast awaits later-snapshot scoring. |
| C1 family evidence → lifetime | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** by ablation across two temporal periods; effect is not consistent across periods/models. |
| C2 lifetime survival → breakup-cloud counts | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** against catalogue counts for qualifying clouds. Cluster uncertainty prevents confident ranking of the readings/experts. |
| C3 catalogue status → re-entry regime | **IMPLEMENTED, EXECUTABLE, QUANTITATIVELY_EVALUATED** on one previously analysed as-of window. Status is a proxy for operator control, not a telemetry health measurement; prospective policy results are distinguished from the in-window diagnostic. |
| C4 health/conjunction escalation | **PARTIALLY_IMPLEMENTED, EXECUTABLE** as a demonstration. It is not quantitatively or independently validated because health and conjunction examples cannot be linked to the same spacecraft. In the executable pipeline C4 **abstains with a recorded reason**, and an integration test asserts the abstention, so an unlinkable coupling cannot silently produce an escalation. |
| Legacy simulated health → hazard → breakup → footprint → risk chain | **IMPLEMENTED, EXECUTABLE, UNIT_TESTED** for physics/code behavior. It is a simulated scenario and is not validated against real breakup/impact outcomes. The README now distinguishes it from the real-data studies. |
| Shared contracts and dependency orchestration | **IMPLEMENTED, UNIT_TESTED, INTEGRATION_TESTED** in `cosmos/ai/contracts.py` and `cosmos/ai/orchestration.py`. As of 2026-11-04 real adapters (`cosmos/ai/adapters.py`) and an executable runner (`scripts/run_pipeline.py`) wire the catalogue chain plus independent collision/health/debris modules through the orchestrator on saved artifacts; see [pipeline execution](../architecture/pipeline_execution.md). Research scripts that write the artifacts still run under their own protocols, so round-trip adaptation of every training pipeline remains **PARTIALLY_IMPLEMENTED**. |
| Prediction provenance | **PARTIALLY_IMPLEMENTED**. Twin outputs carry typed source names and optional hash/digest fields. New experiment runs record code HEAD, dirty state, seed, config digest, model version and manifest hash via `cosmos/ai/provenance.py` — which lives outside the pre-registration freeze and attaches through `Run.extra`, so the frozen confirmatory code is not modified (L18). Adapter results carry the SHA-256 of the artifact read, verified against disk by an end-to-end test. Existing results are not retroactively changed, and twin exact input hashes/config/model digests remain unset. |
| Dashboard | **IMPLEMENTED** as a read-only HTML evidence dashboard generated from actual saved artifacts in `cosmos/ai/dashboard.py`. Missing/unsupported views are labeled unavailable; no individual trajectory or anomaly timeline is fabricated. It is not a live operational dashboard. |

No evidence found supports the labels `INDEPENDENTLY_VALIDATED` for a complete cross-domain
system. No `PROPOSED` item is treated as implemented merely because it appears in the
architecture prompt.

## Shared interfaces and uncertainty

Shared estimates now use `cosmos/ai/contracts.py`; the twin's `OutputProvenance` re-exports
the shared provenance contract. `cosmos/ai/orchestration.py` provides dependency-injected partial execution, required input
checks, explicit blocked/failed results, independent-module continuation, run-config hashes
and per-module typed source provenance. Adapters for existing research scripts remain
incomplete. Twin outputs attach source names, but exact input hashes/config/model
digests/upstream IDs are not yet populated.

Uncertainty methods include conformal p-values, BH/Simes procedures, split-conformal
quantiles, CQR intervals, calibration, Monte Carlo quantiles and risk-coverage utilities.
The guarantees are conditional on assumptions such as exchangeability; telemetry dependence,
drift, and the re-entry temporal shift limit literal coverage guarantees. Physics Monte Carlo
intervals in the twin are explicitly not labelled conformal.

## Important distinction

The former `cosmos/pipeline.py` implements the synthetic telemetry-to-risk demonstration.
The real-data studies in `cosmos/ai/` are separately validated on their own benchmarks. The
data do not support claiming an empirically validated causal chain from satellite health
through fragmentation to an observed re-entry footprint.

## Evidence references

- [Architecture and novelty](../ARCHITECTURE_AND_NOVELTY.md)
- [Data flow and metrics](../DATAFLOW_AND_METRICS.md)
- [Final implementation report](../FINAL_IMPLEMENTATION_REPORT.md)
- [Project audit](../PROJECT_AUDIT.md)
- [Results and analysis](../RESULTS_AND_ANALYSIS.md)
- [Review and fixes](../REVIEW_AND_FIXES.md)
