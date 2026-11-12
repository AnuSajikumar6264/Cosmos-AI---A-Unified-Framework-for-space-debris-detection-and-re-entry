# COSMOS-AI module dependencies and contracts

## Dependency map

```text
cosmos.ai.data
  ├─> cosmos.ai.telemetry ──> HealthEstimate ──┐
  ├─> cosmos.ai.vision ─────> DebrisDetection ├─> evidence/reporting
  ├─> cosmos.ai.lifetime ───> LifetimeEstimate ──> twin C1/C2/T1
  ├─> cosmos.ai.conjunction > CollisionRiskEstimate ──> priority (C4 demo)
  └─> cosmos.ai.twin ───────> ReentryPrediction / ObjectTwin

cosmos.ai.contracts: shared data shapes, units, timestamps, uncertainty, provenance
cosmos.ai.orchestration: adapter dependency graph and partial execution
cosmos.ai.uncertainty: numerical utilities; not a substitute for typed semantics
cosmos.ai.fusion: evidence decision utility; noisy-OR assumptions retained in output
```

The graph denotes data dependencies only where a supported adapter exists. A shared
contract does not imply shared observations. Identity joins must be explicit, provenance
preserving, and justified by source records.

## Contract ownership

| Contract | Producer | Consumer | Mandatory semantics |
|---|---|---|---|
| `TelemetryBatch` | data/preprocessing adapter | telemetry model | timezone, cadence, channel identity, missingness |
| `HealthEstimate` | telemetry adapter | evidence/decision layer | score meaning, alarm, uncertainty, model and provenance |
| `OrbitalState` | catalogue/orbit adapter | lifetime, conjunction, re-entry | epoch, supported frame, SI position/velocity |
| `DebrisDetection` | vision adapter | debris characterization (when available) | image ID/time and pixel coordinate system |
| `ObjectCharacteristics` | catalogue adapter | physics/lifetime | positive SI attributes or explicit missingness |
| `LifetimeEstimate` | lifetime adapter | C2/re-entry decision | quantiles, cumulative horizon probabilities, censoring/cap semantics |
| `CollisionRiskEstimate` | conjunction adapter | priority layer | physical probability distinct from priority |
| `ReentryPrediction` | lifetime/twin adapter | C2/reporting | quantiles, horizon probabilities, interval semantics |
| `Provenance` | every adapter | audit/reporting | source names; exact hashes and execution digests when available |
| `Uncertainty` | every predictor | downstream consumers | kind, method, level, values and assumptions preserved |

## Adapting current pipelines

Adapters should be added at module boundaries rather than rewriting the scientific modules.
Each adapter must:

1. Validate source schema, time zone, units and frame.
2. Reject invalid or ambiguous inputs with an explicit error.
3. Keep missingness explicit and avoid zero-filled scientific defaults unless the model
   protocol specifies and documents that transformation.
4. Return a typed estimate plus source provenance and model/validation status.
5. Abstain or fail if required data are absent; never generate plausible-looking outputs.
6. Preserve physical likelihood, operational vulnerability, consequence and decision
   priority as distinct quantities.

The initial `Orchestrator` deliberately accepts callables, so data-specific adapters can be
introduced incrementally without forcing all current scripts into one incompatible API.
