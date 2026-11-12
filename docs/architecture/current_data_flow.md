# Current COSMOS-AI data flow

Audit snapshot: HEAD `78ee339`, 2026-11-03. This diagram separates the implemented
real-data workflows from the legacy simulated demonstration. Arrows denote implemented data
flow, not necessarily a validated causal relationship.

## Real-data benchmark and twin flows

```text
ESA-ADB / OPSSAT-AD / NASA SMAP-MSL
  -> format-specific loading and preprocessing
  -> per-channel forecasting or anomaly scoring
  -> calibration / conformal p-values / BH / alarm rules
  -> metrics and saved benchmark results
  -> health outputs (not linkable to catalogue objects)

SpotGEO images -> vision preprocessing -> detector -> image benchmark metrics
Generated images -> synthetic detector benchmark (separate from SpotGEO)

GCAT + CelesTrak SATCAT + observed SW-All
  -> cohort construction and as-of features
  -> forward temporal/launch-family split
  -> (A) orbit-averaged drag + A/m Monte Carlo
  -> (B) learned quantile experts + physics summaries
  -> training-OOF reliability gate + tune-B calibration
  -> canonical-epoch lifetime distributions / horizon probabilities
  -> saved predictions, metrics and experiment records

ESA Kelvins anonymised CDMs
  -> event filtering/feature aggregation
  -> persistence and learned experts
  -> nested event-fold selection, calibration and scoring
  -> final-CDM risk forecast (not linked to catalogue objects)

GCAT + dated CelesTrak snapshots + saved lifetime outputs
  -> twin state at as-of date
  -> history-conditioned physics for uncontrolled objects
  -> catalogue-status regime policy for payloads (C3)
  -> ObjectTwin/ModuleOutput records, tables, summaries and hashable dated forecast
  -> prospective follow-up scoring (T1) and cloud evaluation (C2)
```

The shared contract layer validates timestamp semantics, SI state-vector units and declared
coordinate frame, probabilities/quantiles, explicit telemetry missingness, and source
provenance. The dependency-injected orchestrator executes selected adapters, blocks failed
dependants and continues independent modules. Current benchmark scripts still require
module-specific adapters before they can be run through this common execution path.

## Couplings and evidence boundary

| Flow | Implemented operation | Available evidence |
|---|---|---|
| C1: debris family → lifetime | Causal sibling/decay summaries known before prediction enter the lifetime feature matrix. | Two temporal test folds and feature ablations. The gain is model/period-dependent. |
| C2: lifetime → debris cloud | Sum survival probabilities for fragments in qualifying breakup clouds; compare expected and observed catalogue counts. | Real catalogue counts and cloud-cluster bootstrap. Calibration variants are reported; rankings remain uncertain. |
| C3: status → re-entry policy | Operational payloads use a base-rate policy rather than an uncontrolled drag forecast; other regimes use physics policy. | One 72-day as-of window, previously seen during earlier analysis; not a blind confirmatory test. Status is only a catalogue proxy. |
| T1: twin state → current-state re-entry | History-conditioned area-to-mass posterior for uncontrolled objects, plus payload regime policies. | One as-of-date follow-up window; the aggregate outcome was seen during diagnosis and the window is not blind. |
| C4: health × conjunction → escalation | Demonstration combines anonymised, unpaired examples for prioritization. | No linked-object outcomes; not validated. Physical collision probability must remain separate from escalation priority. |

## Legacy simulated demonstration

```text
fault injection / simulated telemetry
  -> cosmos/health/monitor.py
  -> cosmos/health/hazard.py
  -> cosmos/reentry/breakup.py
  -> cosmos/reentry/propagator.py and montecarlo.py
  -> footprint / population exposure / risk
```

This sequence is runnable and has physics-oriented checks, but the input scenario and
downstream trajectory/impact outcomes are simulated. It does not join the real telemetry,
CAC, and orbital catalogue datasets. Its outputs are not historical validation.

## Provenance currently carried

- Dataset manifests carry file names, sizes, checksums and metadata; downloader records
  retrieval details.
- Validation recomputes dataset properties rather than relying solely on manifest summaries.
- Experiments generally have configuration, metrics, and environment records under
  `outputs/experiments/`.
- The twin records model/validation/uncertainty fields, attaches source-level typed
  provenance to re-entry outputs, and writes a dated forecast that can be hashed. The
  workflow does not yet populate input-file hashes, code/config/model digests, or upstream
  output identifiers.
- New experiment runs record Git HEAD/dirty state, seed, resolved config digest, optional
  model version, and a dataset-manifest digest when available.
- The read-only HTML dashboard displays saved artifacts; it explicitly marks unavailable
  views and does not synthesize telemetry traces or trajectory maps.
- The status checker verifies manifest-listed file presence and sizes; content hashes are
  not recomputed on each status check.

## Gaps in the end-to-end lineage

The typed provenance structure is now present and source names are emitted, but the workflow
does not yet populate exact input-file hashes, repository revision, full configuration,
model artifact digest, or upstream output IDs. There is also no universal time/unit/coordinate
contract. Exact cross-dataset synchronization is generally impossible because identities
and observation times are anonymised or absent. These are architectural gaps, not evidence
that the individual benchmark pipelines are invalid.

## Related documentation

- [Dataset audit](../DATASET_AUDIT.md)
- [Target definitions](../TARGET_DEFINITIONS.md)
- [Data flow and metrics](../DATAFLOW_AND_METRICS.md)
- [Twin implementation](../../cosmos/ai/twin/)
- [Legacy pipeline](../../cosmos/pipeline.py)
