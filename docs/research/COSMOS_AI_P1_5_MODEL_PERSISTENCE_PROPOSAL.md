# P1.5 — Model persistence: investigation and implementation proposal (not implemented)

Date 2026-11-08. Investigation only: no model was trained, loaded or saved; no benchmark score was
regenerated. This document describes how fitted models *could* be persisted in future study runs so
that the twin's model version stops being "unavailable", and what that would cost.

## 1. What the study runs do today

| Study | Where models are fitted | What is persisted | Can the fit be reproduced here? |
|---|---|---|---|
| Lifetime benchmark (`cosmos/ai/lifetime/run.py`) | in-process: `MO.LEARNERS[name](seed).fit(...)` for xgboost / lightgbm / catboost / mlp / tabm / tabicl / kumo; gate `FU.Gate.fit`; `FU.MondrianCQR.fit`; isotonic per horizon (`sklearn.IsotonicRegression`) | predictions only (`test_predictions.npz`, `tuneB_predictions.npz`), `learner_cache/*.npz` (cached predictions, ~11 MB per origin), `summary.json::fits` (hyper-parameters) | xgboost, mlp, physics_only, gate, CQR, isotonic: **yes**; lightgbm, catboost, tabm, tabicl, kumo: **no** (backends absent) |
| Dated twin (`cosmos/ai/twin/engine.py::fit_as_of`) | returns an in-memory dict `M = {prior, shapes, cols, models[5 seeds], gate, cqr, iso, learner}` and discards it after `forecast()` | `forecast_table.csv.gz`, `twins.jsonl`, `summary.json` | selected learner is `tabm` → **no** |
| Conjunction (`cosmos/ai/conjunction/run.py`) | in-process; learners + gate + Mondrian CQR | `test_predictions.npz`, `candidates.npz`, `summary.json` | persistence / xgboost / mlp: yes; tabm / tabicl / kumo: no |
| ESA-ADB AR(8) (`forecasting._ar_forecast`, `oof.ar8_oof`) | closed-form ridge per channel, refit deterministically on demand | residual scores (regenerated 2026-11-08, see SCORE_CACHE_MANIFEST.json); **no weights** | **yes** — deterministic (seed 0 permutation), ~6 min for the OOF scores |
| OPS-SAT (`telemetry/opssat.py` via `experiment.Run.save_checkpoint`) | torch models per seed | **already persisted**: `outputs/experiments/*/checkpoints/best.pt` (`torch.save({"state_dict", "config", ...})`, 85 files); the registry hashes `best.pt` as the card's `version` | yes (cnn not seed-reproducible; fcnn/transformer exact) |

Conclusion: three of the four real-data pipelines keep no model object; the only existing precedent
is the OPS-SAT checkpoint (`experiment.Run.save_checkpoint`) and the registry's SHA-256 of it.

## 2. Which fitted models can be persisted

| Component | Serialisable form | Format | Loadable without pickle? | Backend needed to load |
|---|---|---|---|---|
| `XGBQuantile` (xgboost) | `Booster.save_model(path.json)` per quantile head (or one multi-output model, as implemented) | xgboost JSON | yes | xgboost |
| `MLPQuantile` (torch) | `state_dict` + the exact constructor arguments (`params`) | `torch.save(..., )` read with `weights_only=True` | yes (tensors only) | torch |
| `TabMQuantile`, `TabICLQuantile`, `KumoQuantile` | state_dict / vendor format | vendor | — | **absent here**; cannot be exercised |
| Physics prior (`PH.class_prior_from`) | sorted pools per class (`lc`, `am`) | `npz` | yes | numpy |
| `FU.Gate` | `theta`, `mu`, `sd`, `mode`, `l2` | JSON/npz | yes | numpy |
| `FU.MondrianCQR` | `corr[level][(col, key)]` tables, `levels`, `bounds` | JSON | yes | numpy |
| Isotonic per horizon (`sklearn.IsotonicRegression`) | breakpoints `X_thresholds_`, `y_thresholds_` | npz (not joblib) | yes | numpy (reconstruct by interpolation) |
| Design-matrix contract | `cols`, `shapes` (one-hot vocabularies) | JSON | yes | — |
| AR(8) per channel | weights `(order+1, C)` and `sigma (C,)` | npz | yes | numpy |
| Conjunction learners / gate / CQR | as above | as above | yes for xgboost/mlp/persistence | — |

Rule: no pickle/joblib of arbitrary objects. Every artifact is either a vendor model format with
its own loader, raw arrays, or JSON; this is what makes "can saved models be loaded safely" answerable
with yes.

## 3. Where to store, and how to name

```text
outputs/models/<study>/<run_id>/
  MODEL_MANIFEST.json      # see §4; the only file a consumer needs to read first
  physics_prior.npz        gate.json        cqr.json        isotonic.npz        design.json
  learner_<name>_seed<k>.<ext> ...          # one per seed; ext = .json (xgboost) | .pt (torch state_dict)
```

`<study>` ∈ {lifetime_origin2011, lifetime_origin2016, lifetime_origin2006, twin_as_of_<date>,
conjunction_kelvins_cac, esa_adb_ar8}. `<run_id>` is the study's existing run identifier. Nothing is
written under an ignored pattern: a `.gitignore` exception for `outputs/models/**` plus a size guard
(abort if a single file exceeds 200 MB) prevents a repeat of the lost-cache episode; large vendor
files are listed in the manifest with digests even if a repository policy later excludes them.

## 4. Digests and association

`model_digest` := SHA-256 over the concatenation, in manifest order, of the SHA-256 of every file
listed in `MODEL_MANIFEST.json` **plus** the canonical JSON of the hyper-parameters (`params`) and the
learner name. One digest therefore identifies the whole fitted ensemble (five seeds, gate, CQR,
isotonic, prior). The manifest records the four version notions already used by the twin's lineage:

```json
{"schema_version": "model_manifest/1.0",
 "study": "...", "run_id": "...",
 "code_version": {"git_commit": "..."},
 "configuration_version": {"params_sha256": "...", "config_sha256": "..."},
 "data_version": {"cohort_sha256": "...", "split": {"origin": "2016", "population": "uncontrolled"}},
 "model_version": {"digest": "...", "files": [{"path": "...", "sha256": "...", "bytes": 0}], "backend_versions": {"xgboost": "3.4.1", "torch": "2.14.0"}},
 "predictions_sha256": {"test_predictions.npz": "..."},
 "trained_at": "...", "seconds": 0}
```

Association is explicit and verifiable: a run manifest's `lineage.model_version.digest` must equal
a `MODEL_MANIFEST.json::model_version.digest` on disk, and the model manifest's `predictions_sha256`
must equal the hash of the prediction artifact the adapter read. Only then may the console show a
model version; the registry card (if any) is linked by name **and** digest, never by name alone —
which is why `VERIFIED_MODEL_CARD_ASSOCIATIONS` stays empty until such manifests exist.

## 5. Safe loading

* xgboost JSON via `Booster.load_model`; torch via `torch.load(path, weights_only=True)` into a
  freshly constructed network whose architecture comes from the manifest's `params`; arrays via
  `np.load(allow_pickle=False)`; JSON for tables. No arbitrary code is executed on load.
* A loader must refuse a model whose `backend_versions` major differs from the installed one, and
  must verify every file's SHA-256 against the manifest before use.
* A round-trip test is mandatory: `predict(load(save(model)))` must reproduce the archived
  `test_predictions.npz` of the same run to 1e-6 (xgboost, physics, gate, CQR: exactly; torch: to
  float32 tolerance).

## 6. How future inference integration would work (not now)

The adapters keep their archive-reading mode as the default. A second, explicit mode
(`config["mode"] = "inference"`) would: (1) load the model manifest for the declared study run,
verify digests, (2) build the design matrix with the persisted `design.json` contract, (3) predict,
fuse (gate), conformalise (CQR tables) and read horizon probabilities (isotonic), (4) set
`Provenance.model_digest` and `lineage.model_version.status = "recorded"`. Any difference between
inference-mode output and the archived table for the same as-of date is a reproducibility finding to
report, not to hide. The console would label inference-mode runs distinctly; nothing about this makes
the system "live" — the inputs are still a dated snapshot.

## 7. Tests required

Save/load round trip per component; digest determinism; manifest validation (schema family
`model_manifest/1.0`); refusal on digest mismatch and on backend-major mismatch; adapter inference
mode reproduces the archived forecast table for the available learner (`xgboost`/`mlp`) or records the
deviation; no write into any archived directory; `.gitignore` guard test.

## 8. Storage and compute costs (estimates from the existing artifacts)

| Item | Size | Notes |
|---|---|---|
| xgboost quantile model, 5 seeds | ~5–40 MB | depends on tree count; JSON |
| MLP quantile, 5 seeds | < 5 MB | state_dict |
| physics prior pools, gate, CQR, isotonic, design contract | < 2 MB | |
| AR(8) weights + sigma (M1 target, 58 channels) | < 100 kB | replaces a 3.4 GB score cache for selection studies |
| OPS-SAT checkpoints (already stored) | 85 files, existing | |
| Compute to produce them | the study's own fitting time (minutes for xgboost/mlp; `summary.json::seconds_total`); **tabm/kumo/tabicl cannot be fitted here** | no new benchmark scores need be published |

## 9. Blockers and what remains honest

Persisting the *selected* learners (`kumo` 2011, `tabm` 2016, the twin's `tabm`) requires installing
backends that are not present — an environment change that needs approval and a new environment lock.
Until then, persistence can cover physics, gate, CQR, isotonic, xgboost, mlp and AR(8); the twin's
own forecast would still read "model version unavailable", truthfully, because the model that
produced it cannot be rebuilt in this environment.
