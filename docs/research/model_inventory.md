# COSMOS-AI model and artifact inventory

Inventory snapshot: HEAD `78ee339`, 2026-11-03. Registry labels below are metadata, not
independent verification of scientific validity. “Validated-real” means the card points to
real-data benchmark evidence; it does not mean external independent validation.

## Registry summary

`outputs/registry/model_cards.json` contains 20 model cards:

| Registry status | Count | Interpretation |
|---|---:|---|
| `validated-real` | 16 | Card labels a real-data benchmark/evidence file. Strength and limitations differ by model. |
| `validated-synthetic` | 2 | Evidence is synthetic; not real-world validation. |
| `not-recommended` | 1 | Card marks a model as not recommended for its task. |
| `baseline` | 1 | Reference/baseline card. |

## Families represented

| Family | Models/cards | Evidence and caveats |
|---|---|---|
| ESA-ADB health | AR(8), PatchTST and persistence, each with threshold and conformal-BH variants (10 cards). | Results in `outputs/benchmarks/telemetry_esa_adb/results.csv`; some results use one seed. Mission-specific performance and calibration limitations are recorded in cards. |
| OPSSAT health | Hybrid, FCNN, CNN and XGBoost (4 cards). | Benchmark evidence points to `outputs/benchmarks/telemetry_opssat/summary_official.csv`. Three cards contain absolute checkpoint paths outside this workspace; those paths do not exist here. |
| Vision | SpotGEO heatmap U-Net; COSMOS synthetic heatmap | SpotGEO benchmark is real benchmark evidence, not independent observing validation. The synthetic card cannot support real-world claims. |
| Re-entry | XGBoost, hazard MLP, physics baseline, propagator surrogate | XGBoost card references real catalogue benchmark results; hazard MLP is marked not recommended; physics is a baseline; surrogate is synthetic validation only. |
| Other model candidates | Conjunction experts and lifetime learners are represented in study code/results and experiment records; inventory card status should not be mistaken for a portable trained checkpoint. | See `cosmos/ai/conjunction/`, `cosmos/ai/lifetime/`, `outputs/benchmarks/` and the experiment directories. |

The 20-card registry is not a complete list of every candidate configuration or seed run.
Some benchmark studies compare multiple model families without persisting one model card
per individual fitted model.

## Checkpoint and reproducibility findings

- Three OPSSAT checkpoint fields point to
  `/data/anupa/COSMOS_work/Final_Project/.../checkpoints/best.pt`; these paths were checked
  and do not resolve in the current environment.
- No `.pt`, `.pth`, `.ckpt`, or `.safetensors` weights were found under the repository's
  `outputs/` or `data/` trees at audit time.
- Many other cards correctly have `checkpoint: null`. This is consistent with benchmark
  results/prediction caches being retained without portable model weights.
- A read-only audit of all 20 cards found 10 missing evidence paths, 3 missing checkpoint
  paths, and 17 checkpoints not recorded. These counts describe the current registry only;
  no card or artifact was edited by the audit.
- A missing checkpoint does not invalidate a saved metric, but it does limit inference
  portability and exact retraining. The manuscript should distinguish those claims.
- Historical docs describe checkpoints or external environment paths; these should be
  reconciled before public release.

## Model selection and evaluation cautions

- Lifetime study: candidate pool restricted to 2022–2026 models after the first full run;
  the earlier run is retained and the deviation is documented. Tests were scored multiple
  times during development.
- Reliability-gated fusion does not beat the best single expert consistently; do not frame
  gating itself as established superiority.
- Collision model predicts final-CDM log collision probability on anonymised benchmark
  events. It does not model linked object vulnerability or operational response.
- Conformal/calibration labels are method-specific. Serial dependence, temporal shift,
  small calibration samples and distribution drift weaken nominal guarantees.

## Source locations

- Registry: `outputs/registry/model_cards.json`
- Study implementations: `cosmos/ai/telemetry/`, `cosmos/ai/vision/`,
  `cosmos/ai/conjunction/`, `cosmos/ai/lifetime/`, `cosmos/ai/twin/`
- Results: `outputs/benchmarks/`, `outputs/experiments/`
- [Model selection](../SOTA_MODEL_SELECTION.md)
- [Results and analysis](../RESULTS_AND_ANALYSIS.md)
- [Review and fixes](../REVIEW_AND_FIXES.md)
