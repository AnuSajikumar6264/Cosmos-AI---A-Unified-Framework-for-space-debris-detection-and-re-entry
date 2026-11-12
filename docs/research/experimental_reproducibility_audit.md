# Experimental reproducibility audit

Audit snapshot: HEAD `78ee339`, 2026-11-03. This is an inventory of reproducibility evidence
and limitations, not a claim that every reported experiment was rerun during this audit.

## What is present

- Typed contracts, a partial-run orchestrator, twin provenance checks, C2/C3 contract tests,
  a read-only model artifact audit and an evidence dashboard were added after the initial
  audit. They verify software structure, not scientific validity or complete lineage.
- Six experiment configuration files under `configs/` cover ESA-ADB, OPSSAT, SpotGEO,
  synthetic vision, landmark re-entry and surrogate re-entry.
- Experiment directories under `outputs/experiments/` commonly contain `config.yaml`,
  `metrics.json`, `env.json`, and, for training jobs, epoch logs.
- Benchmark outputs and registries are retained under `outputs/benchmarks/` and
  `outputs/registry/`.
- Dataset manifests record checksums and retrieval metadata; a combined dataset manifest
  can be built with `scripts/build_dataset_manifest.py`.
- Manuscript result values are generated from named result files by
  `paper/journal_v3_twin/tools/build_numbers.py`; that tool aborts when a referenced value
  is missing.
- Split, leakage, uncertainty, preprocessing and legacy physics tests exist in the three
  test modules.
- Prior restoration validation recorded: `test_ai.py` 44 passed, 0 failed, 3 expected skips;
  `test_datasets.py` 22 passed; `test_verify.py` 20 passed. These are prior results, not
  tests rerun for this documentation change.
- The provenance-stage regression command
  `./.venv/bin/python -m pytest -q tests/test_ai.py tests/test_datasets.py tests/test_verify.py tests/test_twin.py`
  completed with **47 passed** at that stage. Later architecture tests are recorded in the
  final task report. Pytest emitted an existing `pytest-asyncio` configuration
  deprecation warning; there were no test failures.
- Final focused architecture/artifact tests: **32 passed**. Repository-owned discovery
  (`./.venv/bin/python -m pytest -q tests/`) completed with **64 passed, 1 failed**. The
  remaining failure is the existing preregistration guard: it detects that
  `cosmos/ai/experiment.py` no longer matches the frozen digest. The code change adds run
  metadata only, but the guarded digest was deliberately not refreshed during this task.
- Unrestricted `pytest -q` also traverses vendored upstream tests under the ESA-ADB snapshot;
  collection fails because those suites require their own dependencies (including
  `msanomalydetector`) and import layout. It is not a valid repository test command.

## Experimental design and disclosures

| Area | Reproducibility evidence | Threat / disclosure |
|---|---|---|
| ESA-ADB | Protocol/config, official metric implementation, preprocessing verification and saved results. | Some registry rows have one seed. Small calibration subset, mission heterogeneity, temporal dependence/drift; do not describe realized false-alarm rates as guaranteed conformal control. |
| OPSSAT / SMAP-MSL | Experiment configs, metrics/environment records; SMAP labels merged by channel and OOF calibration with purged contiguous blocks. | Three OPSSAT checkpoint references are stale external absolute paths. SMAP/MSL anomaly labels are concentrated late; test min/max scaling is inherited from the source benchmark. |
| SpotGEO | Benchmark outputs and configuration exist. | Limited seeds/conditions; no independent observing dataset. Recheck exact threshold boundary behavior. |
| Lifetime | Two forward origins, launch-family splits, multiple seeds for many candidates, cache fingerprints, per-object RNG and saved prediction/result artifacts. | Test sets were scored repeatedly during development; learner set changed after first run; several diagnostic analyses are post hoc. Two temporal periods do not establish general temporal robustness. |
| C2/C3/T1 | Dated snapshots, saved outputs, and cluster bootstrap analyses are documented. | C3/T1 data/window had prior analysis/exposure; T1 is not blind. The 2026-10-27 dated forecast awaits later-snapshot verification. |
| Legacy re-entry simulator | Physics checks in `tests/test_verify.py`. | Code/analytic tests do not validate historical impact locations, casualty estimates or real fragmentation. |

## Artifact portability

- The model registry has 20 cards: 16 `validated-real`, 2 `validated-synthetic`, 1
  `not-recommended`, and 1 `baseline` by registry label.
- Three OPSSAT cards point to checkpoint files under an external absolute path that does not
  exist in the current environment.
- No model-weight files were found in repository `outputs/` or `data/` at audit time.
- The read-only audit found, across the 20 current cards, 10 missing evidence paths, 3
  missing checkpoint paths, and 17 checkpoints not recorded.
- Some studies rely on saved test predictions/results rather than portable trained models.
  This supports result inspection but does not guarantee independent inference/retraining
  without all dependencies, data, model weights, hardware and exact environment.

## Environment and determinism

The implementation documents environment variables and hardware requirements for models
using GPU/XPU or large in-context model inference. Lifetime physics uses per-object random
streams and cache fingerprints; this reduces batch-order dependence. At least one TabM run
uses GPU training noted as not bit-reproducible, and a repeated configuration produced a
slightly different aggregate. Hardware determinism should not be assumed from a fixed seed.

## Test exposure and scientific status

The project documentation discloses:

- Lifetime test sets were scored before and after the learner-pool change and during smoke
  testing.
- The first learner set and updated 2022–2026 candidate set are retained separately.
- C3/T1 follow-up period was used by an earlier landmark benchmark; the aggregate count was
  seen during diagnosis before the history-conditioned variant was designed.
- Post-hoc analyses are labelled as such; they are not untouched confirmatory evidence.

Any future result intended as confirmatory should freeze the protocol, metrics, model
selection and test snapshot before outcomes are examined.

## Reproduction gaps / next actions

1. Resolve stale checkpoint references only after confirming artifact ownership and intended
   storage; do not silently substitute weights.
2. Supply exact model/checkpoint digests in new runs and retain dependency/hardware/RNG detail.
3. Use the new read-only model artifact audit; do not mutate old registry entries based only
   on path failures.
4. Add direct integration tests for dataset-backed twin engine/couplings/T1.
5. Reserve later snapshots for prospective evaluation and report all prior test exposure.
6. Keep software test results, benchmark results, and independent scientific validation in
   separate report sections.

## Evidence references

- [Results and analysis](../RESULTS_AND_ANALYSIS.md)
- [Review and fixes](../REVIEW_AND_FIXES.md)
- [Final implementation report](../FINAL_IMPLEMENTATION_REPORT.md)
- [Submission checklist](../../paper/journal_v3_twin/SUBMISSION_CHECKLIST.md)
- [Dataset audit](../DATASET_AUDIT.md)
