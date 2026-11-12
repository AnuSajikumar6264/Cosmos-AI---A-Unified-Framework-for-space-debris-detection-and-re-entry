# COSMOS-AI integration audit

Audit snapshot: HEAD `78ee339`, 2026-11-03. This audit distinguishes implemented module
composition from joined-data validation.

## Orchestration surfaces

| Surface | Current behavior | Main gap |
|---|---|---|
| Legacy `cosmos/pipeline.py` | Linear demonstration: telemetry → health monitor → hazard → breakup cloud → footprint → risk; returns a `PipelineResult` with intermediate outputs. | No partial execution/checkpoint/recovery contract; provenance/validation metadata are not attached uniformly. Inputs and outputs are a simulated scenario, not a real joined dataset. |
| Dated twin `cosmos/ai/twin/engine.py` | Builds an as-of snapshot, assigns regimes, forecasts re-entry, attaches module outputs, and writes JSONL/table/summary records. | Focused on dated re-entry serving, not a general orchestrator for all health, vision, collision and re-entry modules. |
| Shared contracts `cosmos/ai/contracts.py` | Typed records validate timestamps, units/frame declarations, finite ranges, missing telemetry, monotone quantiles/horizon probabilities, uncertainty semantics and provenance structure. | Existing module-specific DataFrames/scripts have not all been adapted; declared coordinate frames are not transformed or scientifically checked. |
| Dependency runner `cosmos/ai/orchestration.py` | Supports dependency graphs, selected/partial runs, required-input checks, explicit failure/block statuses, and independent-module continuation. | **Adapters now exist** (`cosmos/ai/adapters.py`, 2026-11-04): the catalogue chain, collision, health and debris modules run through it on real saved artifacts. Orchestration plumbing still does not itself validate scientific outputs. |
| Adapter layer `cosmos/ai/adapters.py` | Re-expresses saved artifacts as typed contract records: identity-linked `catalogue_state → lifetime → reentry → decision_priority`, plus independent `collision`, `health`, `debris` roots. Reads only; never trains or rescores. Missing artifacts raise `ArtifactUnavailable`. | Covers the artifacts that exist today. Adapters for the ESA-ADB per-channel alarm series and for SpotGEO per-detection confidences are not possible from the current saved files. |
| Executable runner `scripts/run_pipeline.py` | Writes a versioned `outputs/pipeline/run_<ts>/` with run manifest, config digest, per-module provenance, Git revision, environment and per-module CSVs. Refuses to overwrite a run; exits non-zero on any failure or block. | Run artifacts are interface/lineage evidence, not scientific validation. |
| Twin records `cosmos/ai/twin/state.py` | `ObjectTwin`/`ModuleOutput` use typed provenance and validate as-of consistency; engine emits source names. | Exact input hashes/config/model digests/upstream IDs remain unset by the engine. |
| Experiment tracking `cosmos/ai/experiment.py` | New run records include seed/config digest, Git HEAD/dirty status, optional model version, and dataset-manifest SHA-256 if available. | Existing records are not backfilled; exact model/checkpoint digest is optional and must be supplied by each run. |
| Static evidence dashboard `cosmos/ai/dashboard.py` | Generates a local HTML view from registry, benchmark and dated twin artifacts that are present. | Not a live dashboard; missing timeline/trajectory views are explicitly unavailable. |
| Fusion `cosmos/ai/fusion.py` | Fuses compatible evidence with explicit in-domain/validation checks, abstention for insufficient/conflicting evidence, and a conditional-independence noisy-OR assumption. | Telemetry anomaly probability is a reporting score, not a calibrated posterior; assumptions must be retained downstream. |

## Couplings

| Coupling | Implementation | Evidence status |
|---|---|---|
| C1: family evidence → lifetime | Family features are restricted to information available before prediction; ablation is in lifetime study. | Quantitatively evaluated on two temporal origins; gains vary by model/origin. |
| C2: re-entry survival → debris-cloud population | Aggregates object survival probabilities and compares with observed catalogue counts by qualifying cloud. | Quantitatively evaluated on real catalogue data with cluster bootstrap; cannot confidently rank all variants/experts. |
| C3: catalogue status → re-entry regime | Operational payloads do not receive the same drag forecast as uncontrolled objects; a previous-window base rate is used. | One prospective as-of window, but previously analysed and not blind. Status is a proxy rather than telemetry-derived health. |
| T1: twin state → current-state re-entry | History-conditioned physics for uncontrolled objects and status-aware policy for payloads. | One 72-day follow-up window; aggregate outcome seen during diagnosis; not a blind test. |
| C4: health × conjunction → escalation | Demonstration applies escalation logic to separate/anonymised examples. | Not validated: no shared object identities or downstream outcome. Must not inflate physical collision probability. |

## Automated coverage

`tests/test_ai.py` covers uncertainty primitives, preprocessing, deterministic splits/leakage,
dataset/metric behavior, legacy pipeline compatibility, learned backend integration,
surrogate fallback and fusion abstention/noisy-OR behavior. `tests/test_datasets.py` covers
dataset discovery/status/validation, and `tests/test_verify.py` covers legacy physics checks.
The new `tests/test_twin.py` covers provenance serialization/consistency, C3 regime rules,
and bounded monotone C2 survival conversion.

The tests do not exercise dataset-backed `engine.run`/`forecast`, full C2/C3, or
`prospective.run`. Therefore code existence and saved result files do not establish
regression protection for those end-to-end paths. Existing coupling reports should be
reproduced only with their saved protocols and not treated as an automated pass.

Added 2026-11-04: `tests/test_integration.py` (13 checks) and `tests/test_end_to_end.py`
(10 checks) cover the adapter layer — identity linkage, uncertainty semantics, provenance
digests, partial execution, explicit failure and blocking, the priority/probability
separation, C4 abstention, output schemas, physical ranges, reproducibility and refusal to
overwrite a run. `tests/test_experiment.py` now also asserts the pre-registration freeze is
intact, so engineering work on a frozen file fails a test instead of silently closing the
held-out telemetry half. These are software checks; they are not scientific validation.

## Data contracts and failure behavior

- Inputs still use module-specific data frames/configs; shared typed contracts now exist,
  but they are not yet applied at every model boundary.
- Dataset manifest/validator utilities provide useful validation at ingestion, but the
  checks are not universally enforced at every module boundary.
- Missing health or imagery should not block unrelated analysis. The new adapter
  orchestrator supports independent partial runs; the legacy chain remains linear.
- Missing or incompatible evidence must result in an explicit abstention/failure, not a
  fabricated successful output. Existing fusion has abstention logic; this behavior is not a
  system-wide standard.
- Free-text validation labels are not a substitute for structured evidence provenance.

## Integration priorities

1. ~~Add deliberate adapters for current pipelines and populate provenance digests when exact
   inputs/artifacts are known~~ — **done 2026-11-04** in `cosmos/ai/adapters.py`; each result
   carries the SHA-256 of the artifact read, and digests are never inferred.
2. Add focused regression tests for full C2/C3 and T1 behavior using fixtures/small inputs.
   **C4 is now covered** by an abstention test; C2/C3/T1 remain uncovered.
3. ~~Preserve physical collision probability separately from operational priority~~ —
   **done**: `collision_risk` leaves `priority_score` unset and an integration test asserts
   that `decision_priority` reproduces upstream probabilities unchanged.
4. Do not claim full end-to-end empirical integration until a lawful, identity-linked
   dataset exists. **Still open and unchanged by the adapter work**: the executable pipeline
   demonstrates interface integration, not joined-data validation.
5. New: decide how to handle L17 (non-coherent per-horizon lifetime calibration). The adapter
   abstains and logs; a joint/isotonic-in-horizon recalibration would change methodology and
   needs approval.
