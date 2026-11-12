# Executable adapter pipeline

Added 2026-11-04. This document describes the pipeline that actually runs, and the limits of
what running it establishes.

## What it is

`cosmos/ai/adapters.py` re-expresses artifacts that scientific runs already wrote as typed
contract records, and `scripts/run_pipeline.py` executes them through
`cosmos/ai/orchestration.py`. The layer **reads** results; it does not train, re-fit,
resample or rescore, so executing it cannot change a published number.

Before this, the orchestrator was exercised only by synthetic lambdas in
`tests/test_orchestration.py`; no scientific module was wired through it. That was the top
integration priority in `../research/integration_audit.md`.

## Module graph

```text
catalogue_state ──┬──> lifetime ──┐
                  │               ├──> decision_priority
                  └──> reentry ───┘

collision      (independent root)
health         (independent root)
debris         (independent root)
```

`catalogue_state`, `lifetime`, `reentry` and `decision_priority` form an **identity-linked**
chain: every field comes from one CelesTrak/GCAT snapshot keyed by NORAD number, so the chain
describes the same objects throughout.

`collision`, `health` and `debris` are **independent roots**. They are not identity-linked to
the catalogue chain or to each other, because the ESA-ADB missions and the Kelvins CAC
conjunction events are anonymised. They are roots rather than dependencies precisely so that
a missing imagery or telemetry artifact cannot block the catalogue chain.

## Running it

```bash
python scripts/run_pipeline.py --list
python scripts/run_pipeline.py --as-of 2026-10-27 --limit 500
python scripts/run_pipeline.py --as-of 2026-10-27 --select decision_priority
```

`--limit N` keeps the N highest 30-day re-entry probabilities, so a bounded run retains the
decision-relevant objects instead of an arbitrary slice.

Each run creates `outputs/pipeline/run_<UTC timestamp>/` holding `run_manifest.json` (resolved
config, config digest, per-module status, provenance, Git revision, environment) and one CSV
per successful module. **An existing run directory is never overwritten**, and the process
exits non-zero if any requested module failed or was blocked.

## Behaviour under missing or defective inputs

| Situation | Behaviour |
|---|---|
| Artifact absent | Adapter raises `ArtifactUnavailable`; module is `failed`; dependants are `blocked`; independent modules still run; no prediction file is written. |
| Module not selected | `not_requested`; its dependencies are added automatically. |
| Required input absent | `blocked`, naming the missing input. |
| Unknown conjunction model requested | `failed`, listing the models actually present — no substitution. |
| Learned expert has no value for an object | Recorded in `abstained`, never backfilled with the physics forecast. |
| Saved calibrated CDF non-monotone | Object is abstained and logged to `lifetime_noncoherent_horizons.csv` (see L17). |

## Uncertainty is kept, not collapsed

Each module keeps its own representation rather than reducing everything to one confidence
number:

- **Lifetime** — `quantiles` (0.05/0.50/0.95 days) with the cap and calibration-origin
  assumptions attached.
- **Re-entry** — `quantiles` from the physics Monte Carlo, carrying the explicit assumption
  that the spread is **not** a conformal interval and **not** a distribution-free coverage
  guarantee; `score` where the snapshot has horizon probabilities but no time quantiles.
- **Collision** — `interval` on the 0.05–0.95 quantiles of log10 collision probability, with
  the reporting floor at log10 = −30 recorded, so a floored value is not read as an exact
  probability.
- **Health** — `score`, stated as an event-wise F0.5 *performance measurement of a benchmark
  arm*, explicitly not a per-object anomaly probability.

## Physical probability versus operational priority

`collision_risk` leaves `priority_score` unset: priority is a decision-layer quantity and is
not baked into a physical probability. `decision_priority` ranks objects by re-entry
probability and a mass-based consequence proxy, and the integration tests assert that it
reproduces the upstream probability unchanged.

Coupling **C4** abstains. Health evidence is present but shares no identifier with the
catalogue, so no health-driven escalation is computed, and the abstention carries that reason.
Asserting `health_identity_linked` in the config does **not** unlock it — no dataset in this
repository links telemetry health to a catalogued object, so the module reports that instead.

## What running this does not establish

Executing this pipeline is **interface and lineage verification**. It does not revalidate any
scientific result, and a green run is not evidence of predictive accuracy. Every statement in
`../research/limitations_register.md` still applies — in particular the absence of any
identity-linked dataset spanning telemetry, conjunctions and catalogue outcomes (L1), and the
non-coherent saved calibration columns (L17).

## Tests

- `tests/test_integration.py` — 13 Level 2 checks: identity linkage, uncertainty semantics,
  provenance digests, partial execution, explicit failure/blocking, priority-versus-probability
  separation, C4 abstention.
- `tests/test_end_to_end.py` — 10 Level 3 checks on a real subprocess run: exit status, output
  schemas, finite and physically admissible values, timestamp consistency, digest agreement
  with files on disk, run-to-run reproducibility, refusal to overwrite, and failure without
  written predictions when the snapshot is absent.

Both skip rather than pass when the large saved artifacts are not in the checkout.
