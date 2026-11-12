# COSMOS-AI target architecture

## Design constraint

COSMOS-AI has independently evaluated module pipelines but no identity-linked observations
across telemetry, conjunction messages and catalogues. The target therefore integrates
**execution and evidence records**, not data that cannot legitimately be joined. Every
cross-module edge is either an explicitly evaluated coupling or an adapter-level
dependency; no edge implies causal validity by itself.

## Component architecture

```text
                         COSMOS-AI evidence-oriented system
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Data layer                                                            │
 │ acquisition -> checksums/manifests -> schema/time/unit validation     │
 │ dataset identity, license, snapshot, split, processing lineage         │
 └────────────────────────────────────────────────────────────────────────┘
          │                          │                         │
          ▼                          ▼                         ▼
 ┌──────────────────┐   ┌────────────────────┐   ┌─────────────────────┐
 │ Health adapter   │   │ Orbital / lifetime │   │ Vision / debris     │
 │ telemetry scores │   │ state, survival    │   │ image detections    │
 │ alarms, evidence │   │ distributions      │   │ image-coordinate    │
 └──────────────────┘   └────────────────────┘   │ detections          │
          │                          │             └─────────────────────┘
          │                          │                         │
          └──────────────┬───────────┴─────────────────────────┘
                         ▼
          ┌──────────────────────────────┐       ┌───────────────────┐
          │ Evidence/uncertainty layer   │◄─────►│ Collision module │
          │ provenance, calibration,     │       │ physical P_coll  │
          │ domain, abstention, assumptions│      │ separate priority│
          └───────────────┬──────────────┘       └───────────────────┘
                          │
          ┌───────────────┴────────────────────────────────┐
          ▼                                                ▼
 ┌────────────────────┐                         ┌────────────────────┐
 │ Explicit couplings │                         │ Decision/reporting │
 │ C1/C2/C3 evaluated │                         │ abstain, rank,     │
 │ C4 demonstration   │                         │ explain, visualize │
 └────────────────────┘                         └────────────────────┘
                          ▲
                          │
              ┌───────────┴────────────┐
              │ Dependency-injected    │
              │ partial-run orchestrator│
              └────────────────────────┘
```

## Dependency and coupling graph

```text
Raw telemetry ──> Health ──> C3 status policy ──> Re-entry policy
                         └──> C4 priority demo ──┐
Anonymised CDMs ──> Collision probability ──────┴─> operational escalation only
GCAT family ──> C1 family-derived features ──> Lifetime distribution
Lifetime distribution ──> C2 expected cloud survival/counts
Current orbit + catalogue history ──> history-conditioned physics ──> T1 forecast
SpotGEO images ──> image detections (standalone until lawful identity/time linkage exists)
All outputs ──> typed uncertainty + provenance ──> evidence report/dashboard
```

C3 consumes catalogue operational status, not a joined telemetry alarm. C4 cannot be
validated with the current anonymised sources. Collision probability is a physical forecast;
health vulnerability and consequence affect a separate priority score only.

## Execution and failure model

`cosmos.ai.orchestration.Orchestrator` accepts registered module adapters and a dependency
graph. A caller may request a subset; its prerequisites are included. Missing required input
blocks only that module; a failed prerequisite blocks its dependants; independent modules
continue. Each run returns explicit `success`, `failed`, `blocked`, or `not_requested`
records. A caller that requires a fully successful run calls `raise_for_failures()`.
Successful adapters return named outputs together with typed source provenance. The run
hashes the canonical JSON configuration, attaches that digest to each output's provenance,
and records module start time and duration. Non-JSON or non-finite configuration values are
rejected rather than stringified into an unstable digest.

The orchestrator does not automatically invoke current research scripts: their inputs and
outputs are not yet uniform, so each needs a deliberate adapter. It does not silently create
data, join identities, or choose fallback predictions.

## Typed contracts

`cosmos.ai.contracts` defines structural contracts for telemetry batches, health estimates,
orbital state vectors, debris image detections, object characteristics, lifetime estimates,
collision-risk estimates, re-entry predictions, uncertainty, and provenance.

Key invariants:

- Timestamps are timezone-aware ISO-8601; prediction date and provenance date must agree.
- State vectors are SI (`position_m`, `velocity_m_s`) and declare a supported frame. The
  contract does not transform between frames.
- Orbit state vectors are not mixed with orbital elements unless an adapter explicitly
  performs and records that conversion.
- Probabilities are finite and in `[0, 1]`; cumulative horizon probabilities are
  nondecreasing. Collision probability and operational priority remain separate fields.
- Quantile levels and values are ordered; intervals have finite ordered bounds. The
  uncertainty method and assumptions remain explicit.
- Missing telemetry samples are represented as `None`; channels must share the same sample
  count and positive cadence.
- Object characteristics use positive SI quantities when present. Unknown values stay
  absent instead of being assigned a fabricated default.
- Provenance records source names and optionally SHA-256 hashes, code revision, config/model
  digests and upstream output IDs. Optional metadata is never inferred.

## Mathematical interface summary

| Interface | Contract | Meaning / boundary |
|---|---|---|
| Telemetry | `x_c(t_j)`, sample cadence, channel identity, missing-value mask, source/time provenance | Measurements, not anomaly probabilities. Time grids and resampling are module-specific. |
| Health | `a_c(t)`, alarm state, `score_semantics`, uncertainty and model evidence | Alarm score may not be a calibrated posterior; consumers must retain its semantics. |
| Orbit | `r(t), v(t)` in declared frame, SI units, epoch | Coordinate transformation and covariance propagation are not implied by the contract. |
| Image debris | `(image_id, time, x_px, y_px, score)` with detector/source | Pixels do not imply catalog-object identity, physical size or orbit. |
| Lifetime/re-entry | Quantile function `Q_T(u)` in days and `F_T(H)=P(T≤H)` | Nonnegative times; `F_T(H)` nondecreasing in `H`; censoring and cap semantics stay in model metadata. |
| Collision | `P_coll` plus a separately typed/labelled priority score | Health/context may affect priority, not the physical collision probability. |
| C2 | `E[N(t)] = Σ_i S_i(t-t0_i)` for eligible catalogued fragments | Independence is not required for the expectation, but variance/cluster dependence requires separate treatment. |
| C1 | `x_i(t) ← φ_family(i,t)` using only family events known before `t` | Causal availability must be tested at each split; model improvement is empirical, not assumed. |
| C3 | `π(status_i, class_i, orbit_i) → policy/regime` | Status is a proxy for operator control and does not change drag physics. Existing policy evidence is one exposed window. |
| C4 | `priority = f(P_coll, vulnerability, consequence, evidence)` | Demonstration only until paired, outcome-labelled data exist; never rewrite `P_coll`. |

## Deployment boundary

This architecture is a target, not a claim that the full system is already achieved.
Independent module runners and the typed orchestration layer are implemented; end-to-end
adapter coverage, operational dashboard, linked-data validation, and several scientific
experiments remain incomplete or blocked.
