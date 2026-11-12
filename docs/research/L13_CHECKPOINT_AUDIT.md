# L13 — checkpoint and evidence path audit

Date: 2026-11-04. Read-only audit. No checkpoint was downloaded, no model weight was changed,
and `outputs/registry/model_cards.json` was **not** modified.

Reproduce with:

```bash
python scripts/audit_model_artifacts.py --quiet --out outputs/run_phase_d/l13_checkpoint_audit.json
```

## Headline result

L13 is **not a code defect and not a path bug**. `cosmos/ai/registry.py` already resolves
checkpoints workspace-relative:

```python
ck = sorted(glob.glob(os.path.join(output_dir("experiments"),
                                   f"*opssat_{model}_official_f100_s0", "checkpoints", "best.pt")))
```

The stale absolute paths exist only inside the **saved** `model_cards.json`, which was
generated in a different workspace rooted at `/data/anupa/COSMOS_work/Final_Project`. Two
separate facts were being conflated under one "missing" label, and the audit now separates
them.

| Summary field | Count |
|---|---|
| Cards | 20 |
| Checkpoint not recorded (correct for the model type) | 17 |
| Checkpoint recorded but under a foreign workspace | **3** |
| Checkpoint present in this workspace | 0 |
| Evidence paths that do not resolve as recorded | 10 |
| …of those, resolvable by repo-relative path | **10 (all)** |

## Checkpoint-by-checkpoint

| Model | Expected path (as recorded) | Actual | Exists | Local run dir (same run ID) | `checkpoints/` dir | Required by current pipeline? |
|---|---|---|---|---|---|---|
| `opssat_hybrid` | `/data/anupa/COSMOS_work/.../20261024-084444_opssat_hybrid_official_f100_s0/checkpoints/best.pt` | foreign workspace | **No** | `outputs/experiments/20261024-084444_opssat_hybrid_official_f100_s0` | **absent** | No |
| `opssat_fcnn` | `/data/anupa/COSMOS_work/.../20261024-084205_opssat_fcnn_official_f100_s0/checkpoints/best.pt` | foreign workspace | **No** | `outputs/experiments/20261024-084205_opssat_fcnn_official_f100_s0` | **absent** | No |
| `opssat_cnn` | `/data/anupa/COSMOS_work/.../20261024-084255_opssat_cnn_official_f100_s0/checkpoints/best.pt` | foreign workspace | **No** | `outputs/experiments/20261024-084255_opssat_cnn_official_f100_s0` | **absent** | No |
| 17 other cards | not recorded | — | — | — | — | No |

Model and checkpoint identity: the three cards record `version = _sha(ck[-1])`, the SHA-256 of
the checkpoint that existed when the card was generated. Because no weight file is present in
this workspace, **checkpoint identity cannot be verified here**, and no substitute may be
treated as the same model.

Configuration compatibility: each local run directory retains `config.yaml`, `env.json`,
`epochs.csv` and `metrics.json`. The configuration that produced the result is therefore
recoverable even though the weights are not. Compatibility of a *future* checkpoint with these
configs cannot be asserted without the weights.

## Why no weights exist anywhere

`.gitignore` excludes them deliberately:

```
outputs/experiments/*/checkpoints/
*.pt
*.pth
```

A repository-wide search found **zero** `.pt`, `.pth` or `.ckpt` files outside the virtual
environment. Their absence is therefore **expected and by design**, not a loss. The run
directories are present with everything except the large binaries.

## Evidence paths

All 10 non-resolving evidence paths have the same cause — a stale workspace root — and **all
10 resolve at the identical repo-relative suffix**:

| Cards | Recorded root | Repo-relative suffix | Exists locally |
|---|---|---|---|
| `opssat_hybrid`, `opssat_fcnn`, `opssat_cnn`, `opssat_xgboost` | `/data/anupa/COSMOS_work/Final_Project` | `outputs/benchmarks/telemetry_opssat/summary_official.csv` | **Yes** |
| `spotgeo_heatmap_unet` | same | `outputs/benchmarks/vision_spotgeo/runs` | **Yes** |
| `cosmos_synthetic_heatmap` | same | `outputs/benchmarks/vision_cosmos_synthetic/runs` | **Yes** |
| `reentry_xgboost`, `reentry_hazard_mlp`, `reentry_physics` | same | `outputs/benchmarks/reentry_landmark/results.json` | **Yes** |
| `reentry_propagator_surrogate` | same | `outputs/benchmarks/reentry_surrogate/results.json` | **Yes** |

The audit does not assert that a local file is byte-identical to the one the card was
generated from; it reports that the same repo-relative location is populated.

## Safe improvements made

1. `scripts/audit_model_artifacts.py` now classifies every recorded path as `not_recorded`,
   `present`, `foreign_workspace` or `missing_in_workspace`, instead of one "missing" flag.
2. For a foreign checkpoint it reports whether a run directory with the **same run ID** exists
   locally, whether it has a `checkpoints/` folder, and which records it does hold.
3. For a non-resolving path it reports the repo-relative suffix and whether that exists. The
   suffix search tries every anchor occurrence and prefers one that resolves — necessary
   because `/data/anupa/...` begins with `data`, which would otherwise be mistaken for the
   repository's own `data/` directory.
4. `--out` writes the JSON report; `--quiet` prints the summary plus unresolved entries.
5. The report shape stays backward compatible: `evidence_exists` and `checkpoint_exists` are
   retained.

Not done, deliberately: no substitute checkpoint was downloaded, no weights were altered, and
`model_cards.json` was not rewritten. Regenerating it would set these three checkpoints to
`None` and `version` to `"n/a"` — accurate for this workspace, but it would overwrite a saved
artifact and discard the recorded SHA-256 of weights that did once exist. That is a decision
for the author.

## Recommendation

Leave `model_cards.json` as published and treat it as a record of a run on another machine.
If registry regeneration is wanted later, the defensible sequence is: confirm the weights are
genuinely gone or re-locate them, log the decision in
[`METHODOLOGY_DECISIONS.md`](../../research_design/METHODOLOGY_DECISIONS.md), then regenerate —
accepting that the recorded checkpoint digests are lost.

## Status

| Item | Status |
|---|---|
| Checkpoint paths audited and classified | **PASS** |
| Registry code resolves workspace-relative | **PASS** — already correct, no change needed |
| Evidence artifacts locatable in this workspace | **PASS** — 10/10 via repo-relative suffix |
| OPSSAT checkpoint weights available | **BLOCKED** — absent by `.gitignore` design; not required by the current pipeline |
| Checkpoint identity verifiable here | **NOT VALIDATED** — no weight file to hash |
| Exact trained-weight reuse for the three OPSSAT models | **BLOCKED** — do not claim exact reproduction of these models |
| Metric traceability for those runs | **PASS** — `metrics.json`, `config.yaml`, `env.json` retained |

Checkpoint portability and result reproducibility are separate properties. The three OPSSAT
models cannot be re-loaded here; their reported metrics remain traceable to run records.
