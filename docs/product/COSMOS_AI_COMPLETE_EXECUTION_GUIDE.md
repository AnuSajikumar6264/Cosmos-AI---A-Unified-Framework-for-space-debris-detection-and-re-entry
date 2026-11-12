# COSMOS-AI — Complete execution guide

Written for: anyone who must set up, run, demonstrate, test and explain COSMOS-AI from the repository without further help.
Every path, command, option and expected output below was taken from the code or executed on 2026-11-08 at release commit B
(`633ad862`) on the project machine. Where a command was **not** executed in this release pass (the research drivers that retrain
or rescore), the guide says so. Short version: [`COSMOS_AI_QUICKSTART.md`](COSMOS_AI_QUICKSTART.md). Examiner's walk-through:
[`EVALUATOR_GUIDE.md`](EVALUATOR_GUIDE.md). Release status: `docs/research/COSMOS_AI_RELEASE_PROPOSAL.md` §8.

Contents: 1 Overview · 2 Repository structure · 3 Prerequisites · 4 Environment setup · 5 Datasets · 6 Models and weights ·
7 Modules independently · 8 Run the application · 9 Demonstration · 10 API · 11 Outputs · 12 Testing · 13 Troubleshooting ·
14 Shutdown and reproducibility · 15 Limitations and future work.

---

## 1. Project overview

**What COSMOS-AI does.** COSMOS-AI is an M.Tech research platform for an *evidence-aware satellite digital twin*. For every
object of a dated catalogue snapshot (2026-10-27, 31,396 objects with perigee below 2,000 km) it holds a versioned twin state
with orbital elements, an orbital-lifetime estimate with a conformal interval, a re-entry forecast with Monte-Carlo quantiles,
a decision priority computed by a recorded rule, and provenance for every value. Three independent research benchmarks sit
beside the catalogue chain and are never attributed to a catalogued object, because their public datasets are anonymised:
telemetry anomaly detection (ESA-ADB), conjunction collision risk (ESA Kelvins CAC) and optical debris detection (SpotGEO).
The Mission Intelligence Console is a read-only web application that serves all of this with its uncertainty, abstentions and
limitations visible on every screen.

**Objectives (as stated in the thesis).** (1) build the digital twin and its runtime chain; (2) evaluate each capability on real
public data with pre-registered or archived protocols; (3) make uncertainty, abstention and provenance first-class;
(4) demonstrate the result through a reproducible console. The scientific findings are summarised in
[`EVALUATOR_GUIDE.md`](EVALUATOR_GUIDE.md) §4 and in the two manuscripts under `paper/`.

**Main modules.**

| Module (package) | Role | How it is used |
|---|---|---|
| `cosmos.ai.orchestration` + `cosmos.ai.adapters` | nine-module pipeline under typed contracts (`cosmos.ai.contracts`), versioned run manifests (`cosmos.ai.schema`, `run_manifest/1.2`) | `scripts/run_pipeline.py`; `POST /api/scenario` |
| `cosmos.ai.twin` | twin state (`twin_state/1.1` re-emission, archive reader with explicit source policies, streaming integrity, equivalence with the chain); the forecast engine that built the 2026-10-27 snapshot | reader and modules at run time; engine is a research driver |
| `cosmos.product` | Mission Intelligence Console: FastAPI `api.py`, read-only `store.py`, server-side SVG `charts.py`, redacted reports `reports.py`, 17 Jinja templates | `scripts/serve_console.py` |
| `cosmos.ai.lifetime` | K7 orbital-lifetime benchmark: physics expert (King-Hele + NRLMSIS 2.1 table), quantile learners, gate + Mondrian conformal intervals | research driver; its archived predictions feed the twin |
| `cosmos.ai.conjunction` | Kelvins CAC collision-risk benchmark (persistence, learners, gated fusion) | research driver; archived `test_predictions.npz` is the `collision` root |
| `cosmos.ai.telemetry` | ESA-ADB official-protocol study (K6), OPSSAT-AD classifiers, learned monitor, SMAP/MSL | research driver; archived `results.csv` and prepared missions feed the `health` root and the telemetry screens |
| `cosmos.ai.vision` | SpotGEO classical front end and heat-map detectors; COSMOS synthetic frames | research driver; the saved classical detections are the `debris` root |
| `cosmos.ai.data`, `cosmos.datasets` | checksum-verified download, validation, preprocessing | `python -m cosmos.ai.data.{download,validate,preprocess_telemetry}` |
| `cosmos.health`, `cosmos.debris`, `cosmos.reentry`, `cosmos.pipeline` | the original (legacy) physics and simulator chain: telemetry simulator, break-up model, propagator, casualty risk | `notebooks/COSMOS_Demo.ipynb`; `cosmos.health.realdata` prepares the ESA-ADB missions the console reads |
| `cosmos.ai.survival`, `cosmos.ai.surrogate`, `cosmos.ai.fusion`, `cosmos.ai.registry/report/dashboard` | landmark survival study, propagator surrogate, evidence fusion (`decide`), model cards, benchmark reports, static dashboard | independently executable research code; not in the console's decision path |

**Architecture in one paragraph.** `scripts/run_pipeline.py` resolves a configuration, runs the nine modules in dependency order
(`catalogue_state → lifetime → reentry → decision_priority`; independent roots `collision`, `health`, `debris`; `twin_state`
with `twin_equivalence`) and writes one `outputs/pipeline/run_<UTC>/` directory containing `run_manifest.json` and the tables
that succeeded. Every adapter *reads archived outputs*; none trains, re-fits or rescores. The console (`cosmos.product.store.ArtifactStore`)
reads the forecast table, the twin-state archives, the run directories and the benchmark artifacts, and serves 17 page routes and 23
JSON operations. At request time no model runs; the only execution the console triggers is the same pipeline in a child process when
a user submits a scenario.

**Integrated versus independently executable.**

| Status | Modules |
|---|---|
| Fully integrated and operational | console (`cosmos.product`); orchestrator and the nine adapters; twin-state reader, modules and re-emission (`cosmos.ai.twin.reader/modules/reemit`); pipeline runner |
| Integrated with limitations | `collision` root (anonymised Kelvins events, never attributed, C4 abstains); `health` root (anonymised ESA-ADB arms and prepared missions, no object has telemetry); `debris` root (classical detections only, no confidence or time); lifetime and re-entry values (archived predictions of the 2026-10-27 engine run; L17 abstentions; interval kinds labelled) |
| Independently executable | research drivers `cosmos.ai.lifetime.run`, `cosmos.ai.twin.engine`, `cosmos.ai.conjunction.run`, `cosmos.ai.telemetry.*`, `cosmos.ai.vision.*`, `cosmos.ai.survival.landmark`, `cosmos.ai.data.*`, `cosmos.ai.dashboard/report`, legacy `cosmos.pipeline` and the notebook |
| Research / benchmark-only evidence | K6, K7, K8, X-series and T1 results under `outputs/benchmarks/`, `outputs/e3_e5/`, `outputs/am_design_stage1/`, `outputs/t1_ranking_utility/` … |
| Archived evidence only | OPSSAT-AD, SMAP/MSL and learned-monitor results (not reached by the console); the 85 OPSSAT checkpoints |
| Blocked | prospective (blind) validation (needs a snapshot dated ≥ 2026-11-26); propagator surrogate (checkpoints absent, needs training); full refit of the lifetime learners and X6 Stage 2 (backends `kumo`, `tabm`, `tabicl`, `lightgbm`, `catboost` not installed); thesis DOCX/PDF (toolchain absent) |
| Not implemented (deliberately) | live data ingestion, on-demand inference, per-object health verdicts, collision warnings for named objects, debris-to-object association, impact map, 3-D orbit view |

---

## 2. Repository structure

```
/data2/anupa/Final_Year_Project
├── README.md                      project front page (datasets, LFS, console section)
├── requirements.txt               core: numpy, pandas, matplotlib (+ optional torch, scikit-learn, pillow, jupyter)
├── requirements-ai.txt            research stack: torch, scikit-learn, xgboost, numba, pyyaml, pyarrow, requests, portion, jsonschema, chronos, ultralytics, torchvision …
├── requirements-product.txt       console: fastapi, uvicorn, jinja2, pydantic, python-multipart, pillow, httpx (tests)
├── .venv/                         the Python 3.12.16 virtual environment used for every result (ignored by git)
├── .gitattributes                 Git LFS patterns (data/**/raw, processed, *.npz, *.gz, outputs/**/*.npz|*.npy|*.gz, *.pt, outputs/twin/*_reemitted_*/twins.jsonl)
├── configs/                       YAML files: telemetry/{esa_adb,opssat,opssat_regen_20261106}.yaml, vision/{spotgeo,cosmos_synthetic}.yaml, reentry/{landmark,surrogate}.yaml
│                                  (only configs/telemetry/opssat*.yaml is read at run time; the others document code defaults and are checked by tests/test_ai.py)
├── cosmos/                        the Python package (112 files)
│   ├── common.py, datasets.py, pipeline.py, plots.py      legacy root modules (path helpers, dataset registry, simulator chain, figures)
│   ├── health/  debris/  reentry/                           legacy feature packages (simulator, catalogue/detection/lifetime, propagator/risk)
│   ├── ai/                                                 research and runtime layer
│   │   ├── orchestration.py  adapters.py  contracts.py  schema.py  provenance.py   runtime chain and contracts
│   │   ├── twin/  (state, engine, couplings, prospective, reemit, reader, modules)  twin state and its archives
│   │   ├── lifetime/  conjunction/  telemetry/ (+esa_metrics vendored)  vision/  survival/  data/   research drivers
│   │   ├── registry.py  report.py  dashboard.py  experiment.py  evaluation.py  fusion.py  uncertainty.py  explain.py  surrogate.py
│   └── product/                                            Mission Intelligence Console
│       ├── api.py  store.py  charts.py  reports.py  logging_setup.py
│       ├── templates/  (17 Jinja2 pages: base, overview, demo, objects, object, twin_state, telemetry, channel, debris, sequence, risk, runs, run, compare, prospective, scenario, error)
│       └── static/console.css
├── scripts/                       62 command-line entry points (console, pipeline, verification, analyses; see §7 and §12)
├── tests/                         58 pytest files (508 tests pass, 3 skip on this machine)
├── data/                          datasets, one folder per feature (feature1_health, feature2_debris, feature3_reentry) + DATASET_MANIFEST.csv (62 hashed entries)
├── outputs/                       every archived result (see §11): twin/, pipeline/, benchmarks/, audit/, experiments/, product/ …
├── research_design/               pre-registrations and their freeze records (G5d, ESA-ADB)
├── paper/                         manuscripts: jint/ (JINT paper + checklist), k7_lifetime_benchmark/, figures/ (frozen figure release + manifests)
├── thesis/                        thesis sources (src/*.md), evidence map, tools (render.py, render_draft_md.py), build/ (Markdown draft; DOCX/PDF from an earlier toolchain)
├── docs/                          documentation: product/ (this guide, quick start, evaluator guide, launch guide, demo script, protocol, limitations), research/ (reports, audits, release proposal, trackers), architecture and dataset notes
└── notebooks/                     COSMOS_Demo.ipynb (legacy chain), COSMOS_AI_Experiments.ipynb
```

Important generated directories: `outputs/pipeline/run_<UTC>/` (one per pipeline or scenario run; 89 present; regenerable and
deliberately not committed), `outputs/audit/` (dated verification records), `outputs/product/{logs,reports,screens}` (console
scripts' output), `outputs/experiments/` (273 research run folders; 37 GiB locally, mostly not committed).

---

## 3. Prerequisites

| Item | Mandatory for the console and demonstration | Notes |
|---|---|---|
| Operating system | Linux (verified: Linux 6.17, Ubuntu-family) | the code is pure Python; macOS should work; Windows is untested |
| Python | **3.11 or newer** (verified 3.12.16) | `scripts/check_console_prerequisites.py` enforces ≥ 3.11 |
| Required packages | `fastapi`, `uvicorn`, `jinja2`, `pydantic`, `pandas`, `numpy` (plus `starlette`, pulled by FastAPI) | verified versions: fastapi 0.162.0, uvicorn 0.54.0, jinja2 3.1.6, pydantic 2.14.1, pandas 3.1.0, numpy 2.3.5 |
| Required artifacts | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` and `FORECAST_SHA256.txt` (Git LFS) | without them the console starts but shows no catalogue; `/api/ready` answers 503 |
| Git LFS | **yes** for a clone: 831 LFS files ≈ 0.9 GB, including the 78 MB re-emitted twin state | `git lfs install` before cloning; see §4 |
| Optional artifacts | ESA-ADB prepared missions (`data/feature1_health/external/esa_ad/prepared/mission{1,2,3}.npz`, 81 / 110 / 1.4 MB), SpotGEO test frames and saved detections, Kelvins test predictions, ESA-ADB arm table, X6 Stage 1 results, at least one `outputs/pipeline/run_*` | each missing item makes its screen say UNAVAILABLE with the reason; nothing is substituted |
| Optional backends | `torch`, `xgboost`, `scikit-learn`, `scipy`, `statsmodels`, `lightgbm`, `catboost`, `tabm`, `tabicl`, `kumo` (`structured-data-models`), `pymsis` | **never needed to serve the console**; needed only to re-run research drivers. Present here: torch 2.14.0+xpu, xgboost 3.4.1, scikit-learn 1.9.1, scipy 1.18.1. Absent here: statsmodels, lightgbm, catboost, tabm, tabicl, kumo, pymsis |
| GPU / accelerator | none required | the console and pipeline are CPU-only. Research training used an Intel XPU (`torch 2.13/2.14+xpu`); any CPU/CUDA/XPU PyTorch build works for the code paths that use torch (`COSMOS_DEVICE` selects the device) |
| Memory | console: peak RSS 273 MB measured (fresh process incl. twin-state streaming); telemetry channel view ≈ 243 MB; scenario child process ≈ 312 MB. Recommend ≥ 4 GB free. Research drivers: ESA-ADB Mission 1 array is 448 MB; learner fits need several GB | measurements in `outputs/audit/console_cold_profile_release_candidate_*.json` |
| Storage | complete git checkout 0.92 GiB + LFS 0.9 GB; the full local working tree with every dataset and experiment is ≈ 172 GiB (not required) | see README "Datasets and Git LFS" and `docs/DATA_HOSTING.md` |
| External tools | `git`, `git-lfs` (verified git 2.48.1, git-lfs 3.6.1); `curl` for the checks below. Thesis DOCX/PDF only: pandoc 3.11, pandoc-crossref, LibreOffice (absent on this machine) | — |
| Environment variables | none required. Optional: `COSMOS_DEVICE` (torch device for research code; default first free Intel XPU else `cpu`), `COSMOS_TORCH_THREADS` (16), `COSMOS_PHYSICS_JOBS` (16), `COSMOS_KUMO_CONTEXT` (16000), `COSMOS_CONSOLE_ROOT` (repository root for `serve_console.py --reload`), `DISCOS_TOKEN` (ESA DISCOSweb client only) | the console reads no environment variable |
| External services / API keys | none for anything in this guide. Not used: Space-Track (account required), ESA DISCOSweb (token), CORDS (blocked) — see `docs/DATASET_AUDIT.md` | — |

---

## 4. Environment setup

### 4.1 On the project machine (environment already exists)

```bash
cd /data2/anupa/Final_Year_Project
source .venv/bin/activate
python -V                                   # Python 3.12.16
python scripts/check_console_prerequisites.py    # exit 0; prints required/optional status; add --json for a machine-readable report
```

### 4.2 On a fresh machine

```bash
git lfs install                             # once per machine (installs the LFS filter in ~/.gitconfig)
git clone --branch product/mission-intelligence-console https://github.com/AnuSajikumar6264/Cosmos-AI-.git cosmos-ai
cd cosmos-ai
git lfs pull                                # 831 LFS files ≈ 0.9 GB — see the note below about the remote
git lfs fsck                                # "Git LFS fsck OK"
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-ai.txt -r requirements-product.txt
python -m cosmos.ai.data.validate           # re-verifies every dataset checksum; REWRITES data/DATASET_REPORT.{json,md} (see the note below)
python scripts/check_console_prerequisites.py
```

Notes. (a) The release branch and its LFS objects reach GitHub only after the owner's push approval; until then the public remote
holds the 2026-11-06 state (`78ee339`) and the re-emitted twin-state object is absent, so a fresh clone *of GitHub* cannot yet
retrieve it (verified 2026-11-08 against a local clone instead; record
`outputs/audit/fresh_clone_lfs_verification_post_commit_a_20261108T153148+0000.json`). (b) `requirements-ai.txt` pins
`chronos-forecasting==2.3.2`, `ultralytics==8.4.185` (AGPL-3.0, baseline use only) and needs a PyTorch build for your hardware;
install `torch` first from the PyTorch index if the default wheel is not suitable. (c) The console alone needs only
`requirements.txt` (numpy, pandas) plus `requirements-product.txt`. (d) The exact frozen environment of the research runs is
`outputs/baseline/venv_freeze_2026-10-24.txt`. (e) Five learner backends used by archived studies are not in any requirements file
and were not installed here (`lightgbm`, `catboost`, `tabm`, `tabicl`, `structured-data-models`); `pymsis` and `statsmodels` likewise.
Do not install them silently on the project machine: record any environment change. (f) `cosmos.ai.data.validate` regenerates
`data/DATASET_REPORT.json` and `.md`; `DATASET_REPORT.json` is hashed in the frozen figure release manifest, and its `size_on_disk_mb`
fields depend on the filesystem, so on the project checkout run it only when you intend to, and restore the committed files afterwards
(`git checkout -- data/DATASET_REPORT.json data/DATASET_REPORT.md`) if only those size fields changed. The read-only alternative is
`python -m cosmos.ai.data.download status`.

### 4.3 Verify the installation

```bash
python -c "import fastapi, uvicorn, jinja2, pandas, numpy; print('console deps ok')"
python -m pytest tests/test_console_launch.py tests/test_approved_head.py -q      # fast smoke tests
python scripts/verify_protected_artifacts.py --label setup                        # all_protected_ok: True when the checkout is intact
```

---

## 5. Dataset setup

All datasets are listed with SHA-256 in `data/DATASET_MANIFEST.csv` (62 entries) and audited in `docs/DATASET_AUDIT.md`.
`python -m cosmos.ai.data.validate` recomputes and **rewrites** the report (`data/DATASET_REPORT.{json,md}`; see §4.2 note f);
`python -m cosmos.ai.data.download status` prints what is present without writing. Downloads verify checksums and resume; **nothing in this guide downloads automatically**.

| Dataset | Source | Local path | Download / setup command | Used by | Expected format |
|---|---|---|---|---|---|
| CelesTrak SATCAT, GP sets, `SW-All.csv` (snapshot 2026-10-27 and earlier) | celestrak.org (public, no credentials) | `data/feature2_debris/celestrak/` (34 MiB, in LFS) | `python -m cosmos.ai.data.download celestrak` | twin engine, lifetime cohort, catalogue chain | CSV |
| GCAT (J. McDowell, 1.8.8) | planet4589.org, CC BY 4.0 | `data/feature2_debris/gcat/raw/2026-10-27/` (42 MiB, in LFS) | `python -m cosmos.ai.data.download gcat` | twin engine, lifetime cohort | TSV |
| ESA Kelvins Collision Avoidance Challenge | Zenodo 4463683, CC BY 4.0 | `data/feature2_debris/kelvins_cac/raw/` (211 MiB zip, in LFS); extracted by `scripts/extract_lfs_archives.py` | `python -m cosmos.ai.data.download kelvins_cac`; `python scripts/extract_lfs_archives.py` | `cosmos.ai.conjunction`; archived predictions feed the `collision` root | CSV (CDMs) |
| ESA-ADB missions 1–3 (v1.0) | Zenodo 12528696; no licence stated on the record | `data/feature1_health/esa_adb/raw/ESA-Mission{1,2,3}.zip` (12.6 GiB, **not in LFS**: files above the 2 GB limit) | `python -m cosmos.ai.data.download esa_adb`; then `python -m cosmos.ai.data.preprocess_telemetry 1 2 3`; `python -m cosmos.datasets prepare esa_ad` writes the console's `data/feature1_health/external/esa_ad/prepared/mission{m}.npz` | `cosmos.ai.telemetry` (K6); console telemetry screens read the prepared `.npz` | zip → npy grids / npz |
| ESA OPSSAT-AD | Zenodo, CC BY 4.0 | `data/feature1_health/opssat_ad/raw/` (23 MiB, in LFS) | `python -m cosmos.ai.data.download opssat_ad` | `cosmos.ai.telemetry.opssat` (K8) | CSV |
| NASA SMAP / MSL telemetry (telemanom) | Caltech, BSD-style redistribution licence | `data/feature1_health/smap_msl/raw/` (342 MiB, in LFS) | `python -m cosmos.ai.data.download smap_msl` | `cosmos.ai.telemetry.smap_msl` (supporting study) | npy + csv |
| SpotGEO v2 | Kelvins, CC BY 4.0 | `data/feature2_debris/spotgeo/raw/extracted/SpotGEOv2/{train,test}` (45 GiB, **not in LFS**: 4.0 GiB archive above the limit) | `python -m cosmos.ai.data.download spotgeo`; `python -m cosmos.ai.vision.spotgeo preprocess` | `cosmos.ai.vision`; console `/debris` serves the test frames and the saved classical detections | PNG sequences + annotation JSON |
| Kelvins "Space Debris: the Origin" | Zenodo 4986292, CC BY 4.0 | `data/feature2_debris/kelvins_debris_origin/raw/` (12 MiB, in LFS) | `python -m cosmos.ai.data.download kelvins_debris_origin` | inspected only (simulated; not used in reported results) | CSV |
| Re-entry cohort, NRLMSIS 2.1 density table, derived lifetimes, recovered-debris records | derived from GCAT/CelesTrak; pymsis 0.13.0; ESA DISCOS public list | `data/feature3_reentry/{processed,derived,historical}/` (4.1 MiB, in LFS) | present in the checkout; cohort rebuilt by `python -m cosmos.ai.lifetime.catalogue`; density table rebuilt by `cosmos.ai.lifetime.physics` if absent (needs `pymsis`) | K7, twin engine | csv.gz, npz, csv |
| COSMOS synthetic telemetry and frames | generated by this code | `data/feature1_health/cosmos_synthetic/`, `data/feature2_debris/cosmos_synthetic/` | `python -m cosmos.ai.telemetry.learned_monitor generate`, `python -m cosmos.ai.vision.cosmos_synthetic generate` | learned monitor and synthetic vision studies only; **never served by the console** | npy / png |
| SpaceSense-Bench, SPARK | Hugging Face (CC BY-NC 4.0) / by request | not held or inspected only | — | not used in any reported result | — |

Not obtained, with the reason recorded in `docs/DATASET_AUDIT.md`: Space-Track TLE histories (account and user agreement),
ESA DISCOSweb (personal token), ESA re-entry predictions API (HTTP 401), CORDS (HTTP 403 to scripted access), REAT inventory
(not needed). A later catalogue snapshot (dated ≥ 2026-11-26) is required for prospective validation and needs explicit
download approval.

Expected layout check: `data/README.md` describes the feature folders; `du -sh data/*` on this machine gives 20 GB health, 8.8 GB
debris, 475 MB re-entry (compressed filesystem; true byte counts in the README).

---

## 6. Model and weight setup

No model inference happens at console or pipeline run time. The nine orchestrator modules and every console route read archived
predictions (CSV / NPZ / JSON / JSONL). The twin reader reports `model_version: unavailable` for every module because **no fitted
model is persisted** for the twin chain.

| Model / artifact | Purpose | Repository path | Weights | Config | Obtain / verify | Inference implemented? | Hardware |
|---|---|---|---|---|---|---|---|
| Twin forecast (lifetime + re-entry for 31,396 objects) | the values shown per object | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` (LFS, sha `b15644aa…`), `twins.jsonl` (sha `19a1fede…`) | none persisted; produced by `python -m cosmos.ai.twin.engine --as-of 2026-10-27`, which refits learners at run time | in code (`cosmos/ai/twin/engine.py`) | `sha256sum` against `FORECAST_SHA256.txt`; `scripts/verify_protected_artifacts.py` | no run-time inference; the table is read. **Regeneration is not authorised** (its learner set needs `tabm`, absent) | CPU; regeneration needs the learner backends |
| Re-emitted twin state `twin_state/1.1` | primary twin-state archive with per-output provenance | `outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl` (LFS, 78,616,187 B, sha `6bb4871f…`), `TWINS_SHA256.txt`, `REEMISSION_MANIFEST.json` | none (deterministic re-emission of the table, no model) | — | `python -m cosmos.ai.twin.reemit --as-of 2026-10-27` reproduces it byte-identically; `python scripts/twin_state_integrity.py` | n/a | CPU, < 1 min |
| K7 lifetime learners (xgboost, mlp, tabm, tabicl, kumo, physics expert, gates) | benchmark results in `paper/k7_lifetime_benchmark/` | `outputs/benchmarks/reentry_lifetime/origin{2011,2016}_uncontrolled/`, `outputs/g5d_origin2006/lifetime/` | **predictions only** (`learner_cache/*.npz`, `test_predictions.npz`); no weight files | hyper-parameters recorded in `summary.json["fits"]` | archived; prediction-level reproducibility 0.000e+00 (`docs/research/FINAL_REPRODUCIBILITY_AND_ARTIFACT_AUDIT.md`) | refit only via `python -m cosmos.ai.lifetime.run --origin 2016 --population uncontrolled` (2 of 7 learners refit here; others need absent backends) | CPU/XPU, hours |
| Kelvins CAC collision models (persistence, learners, `cosmos_gated`) | `/risk` and the `collision` root | `outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz` (538 kB), `test_results.csv`, `summary.json` | predictions only | — | archived; `tests/test_conjunction_benchmark.py` | no; `python -m cosmos.ai.conjunction.run` refits (not run in this pass) | CPU, minutes–hours |
| ESA-ADB arms (AR8, PatchTST, TCN, Chronos forecasters; alarm calibrators) | `/telemetry` arm table, `health` root, JINT manuscript | `outputs/benchmarks/telemetry_esa_adb/results.csv`, `oof_protocol/` (pre-registered freeze), `arms/*.json`, `posthoc_v2/` | no weights persisted (checkpoints of these runs are under the uncommitted `outputs/experiments/`) | `configs/telemetry/esa_adb.yaml` documents defaults | frozen hashes verified by `scripts/verify_protected_artifacts.py` | no; `python -m cosmos.ai.telemetry.esa_benchmark --mission 1 --encoder tcn --seed 0`, `python -m cosmos.ai.telemetry.oof_benchmark select|test --mission 1 --source ar8` retrain (not run in this pass; the pre-registered test half must not be re-scored casually) | XPU/CPU, hours |
| OPSSAT-AD classifiers (fcnn, cnn, hybrid, transformer) | K8 study, robustness analysis | `outputs/experiments/20261106-*_opssat_*/checkpoints/best.pt` — **85 files, ≈ 54 MB, the only persisted weights in the repository** (mostly uncommitted) | `.pt` state dicts | `configs/telemetry/opssat.yaml` (read at run time) | `cosmos/ai/registry.py` hashes the `*_f100_s0` checkpoints | yes, only in `cosmos.ai.telemetry.robustness` (loads them to score perturbed inputs); not used by the console | CPU |
| SpotGEO detectors (classical front end; heat-map U-Net / ResNet-U-Net) | `/debris` detections; vision benchmark table | `outputs/benchmarks/vision_spotgeo/classical_cosmos_frontend_test_submission.json`, `summary.csv`, `runs/*.json` | classical: no weights; learned: no weights persisted, scores only | `configs/vision/spotgeo.yaml` documents defaults | archived; `tests/test_vision_provenance.py` | classical front end re-runs with `python -m cosmos.ai.vision.spotgeo classical`; learned detectors retrain with `python -m cosmos.ai.vision.train_spotgeo --model unet --inputs both --seed 0` (ResNet encoder downloads torchvision ImageNet weights) — not run in this pass | CPU / XPU |
| Propagator surrogate (MLP ensemble) | research only | expected `data/feature3_reentry/simulated/propagator_surrogate_v1/checkpoints/member_*.pt` | **absent** (only `spread_threshold.json` exists) | `configs/reentry/surrogate.yaml` documents defaults | `python -m cosmos.ai.surrogate generate` then `train` would create them | not available; `tests/test_ai.py` skips | XPU/CPU |
| Learned telemetry monitor | research only | `outputs/benchmarks/telemetry_cosmos_synthetic/` | none trained | — | `python -m cosmos.ai.telemetry.learned_monitor generate` then `train` | not available; `tests/test_ai.py` skips | XPU/CPU |
| NASA telemanom LSTM models (`*.h5`, 82 files) | part of the upstream SMAP/MSL dataset archive | under `data/feature1_health/smap_msl/raw/extracted/` (the archive's own `models` folder) | third-party | — | dataset checksum | **not referenced by any COSMOS code** | — |

Integrity of everything above: `python scripts/verify_protected_artifacts.py --label check` (frozen research artifacts, figure
release manifest, twin digests, approved Git head) and `python -m cosmos.ai.data.validate` (dataset checksums).

---

## 7. Execute each module independently

Conventions: run from `/data2/anupa/Final_Year_Project` with `.venv` active. "Executed 2026-11-08" means the command was run in
this release pass with the shown result; "documented from code" means the entry point and options were read from the source but
the command was not run now, because it retrains, rescores or needs absent backends. Research drivers write **new** run folders
and never overwrite published artifacts, but running them is not required for the demonstration.

### 7.1 Pipeline runner (the runtime chain) — executed 2026-11-08

```bash
python scripts/run_pipeline.py --list                                              # module names and dependencies
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh   # full snapshot, all nine modules, ≈ 9 s
python scripts/run_pipeline.py --as-of 2026-10-27 --limit 500 --select catalogue_state lifetime reentry decision_priority   # fast subset ≈ 3 s
python scripts/run_pipeline.py --as-of 2026-10-27 --twin-source-policy archived_only
```

Inputs: `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz`, the twin-state archives, `outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz`,
`outputs/benchmarks/telemetry_esa_adb/results.csv`, `outputs/benchmarks/vision_spotgeo/classical_cosmos_frontend_test_submission.json`.
Output: `outputs/pipeline/run_<UTC>Z/` with `run_manifest.json` (`run_manifest/1.2`: per-module status, provenance, lineage,
config digest) and `decision_ranking.csv`, `reentry_predictions.csv`, `lifetime_estimates.csv`, `lifetime_noncoherent_horizons.csv`,
`collision_risk.csv`, `health_benchmark_arms.csv`, `debris_detections.csv`, `twin_equivalence.csv`. Success: exit code 0 and
`"module_counts": {"success": 9}` in the manifest; the directory appears in `/runs`. A non-zero exit means a module failed or was
blocked (the manifest names it). Common error: `ArtifactUnavailable` when an LFS artifact is still a pointer — run `git lfs pull`.

### 7.2 Twin state — executed 2026-11-08

```bash
python scripts/twin_state_integrity.py                       # selection, integrity, equivalence with the latest run → outputs/audit/twin_state_integration_check_*.json
python scripts/twin_state_integrity.py --policy archived_only
python -m cosmos.ai.twin.reemit --as-of 2026-10-27           # deterministic re-emission; refuses to overwrite; result sha 6bb4871f… (documented from code; the archive is already present)
```

Expected: `selected: reemitted`, `integrity: ok`, `equivalence: computed, 31396 compared, 31396 equal`. The forecast engine
`python -m cosmos.ai.twin.engine --as-of 2026-10-27` rebuilds a forecast from the catalogue snapshot by refitting learners — it is
documented from code, needs the absent `tabm` backend for the archived learner set, and **must not be run to "refresh" the
published forecast** (regeneration is not authorised; the archived table is a frozen research artifact).

### 7.3 Console scripts — executed 2026-11-08

| Command | What it does | Writes |
|---|---|---|
| `python scripts/check_console_prerequisites.py [--json]` | required/optional packages, artifacts, backends; exit 0 = launchable | stdout |
| `python scripts/serve_console.py [--host 127.0.0.1] [--port 8070] [--root PATH] [--log-level info] [--log-json] [--reload]` | the server (§8) | stdout logs |
| `python scripts/rehearse_demo.py --label <label>` | 13 demonstration stages from a fresh process (scenario on a temporary root) | `outputs/audit/demo_rehearsal_<label>_<UTC>.json`; 13/13 ok, ≈ 11 s |
| `python scripts/benchmark_console.py --label <label>` | benchmark-sequence timings and RSS | `outputs/audit/console_benchmark_<label>_<UTC>.json` |
| `python scripts/profile_console_cold.py --label <label> [--runs 5] [--trace]` | fresh-subprocess cold profile | `outputs/audit/console_cold_profile_<label>_<UTC>.json` |
| `python scripts/diagnose_console.py` | diagnostics bundle: prerequisites, readiness, five timed probes, cache statistics, and a protected-artifact verification (label `diagnose`) | `outputs/audit/console_diagnostics_<UTC>.json` (+ the verifier's own record) |
| `python scripts/capture_console_screens.py` | saves the rendered pages as self-contained HTML (no PNG: no headless browser) | `outputs/product/screens/` |

### 7.4 Verification scripts — executed 2026-11-08

```bash
python scripts/verify_protected_artifacts.py --label <label>     # → outputs/audit/protected_artifacts_<label>_<UTC>.json ; expect all_protected_ok: True
python scripts/audit_manuscript_claims.py [--json PATH] [--only FAIL]   # 147 checks; expect 0 FAIL
python -m cosmos.ai.data.validate                                 # dataset checksums → REWRITES data/DATASET_REPORT.{json,md} (§4.2 note f)
python scripts/t1_ranking_utility.py                              # exploratory T1 ranking-utility analysis (41 s) → outputs/t1_ranking_utility/
```

### 7.5 Data acquisition and preparation — documented from code (no downloads were run in this pass)

```bash
python -m cosmos.ai.data.download status                          # what is present
python -m cosmos.ai.data.download <name> [<name> …]               # names: celestrak gcat kelvins_cac opssat_ad esa_adb spotgeo smap_msl kelvins_debris_origin reentry_historical reentry_simulated cosmos_synthetic_telemetry cosmos_synthetic_vision spark spacesense_bench
python scripts/extract_lfs_archives.py                            # expands the Kelvins CAC archive (no network)
python -m cosmos.ai.data.preprocess_telemetry 1 2 3               # ESA-ADB official-protocol grids → data/feature1_health/esa_adb/processed/mission{m}/
python -m cosmos.datasets prepare esa_ad                          # console-ready mission{m}.npz → data/feature1_health/external/esa_ad/prepared/
```

### 7.6 Research drivers — documented from code (retrain or rescore; not run in this pass)

| Study | Command | Needs | Writes |
|---|---|---|---|
| K7 lifetime benchmark | `python -m cosmos.ai.lifetime.run --origin 2016 --population uncontrolled` (also `survival`, `diagnostics`, `gate_all`, `leak_check`, `cost`, `catalogue` sub-modules) | xgboost (present), torch (present), `tabm`, `tabicl`, `kumo`, `lightgbm`, `catboost` (absent → those arms fail), `pymsis` only if the density table is absent | `outputs/benchmarks/reentry_lifetime/origin<O>_<pop>/` |
| Kelvins CAC conjunction | `python -m cosmos.ai.conjunction.run` | learners as above | `outputs/benchmarks/conjunction_kelvins_cac/` |
| ESA-ADB official protocol (K6) | `python -m cosmos.ai.telemetry.esa_benchmark --mission 1 --encoder tcn --seed 0`; pre-registered selection/test: `python -m cosmos.ai.telemetry.oof_benchmark select --mission 1 --source ar8` / `test …` | torch, numba, portion; prepared grids (§7.5) | `outputs/benchmarks/telemetry_esa_adb/`, `outputs/experiments/<run>/` |
| OPSSAT-AD (K8) | `python -m cosmos.ai.telemetry.opssat --config configs/telemetry/opssat.yaml`; robustness: `python -m cosmos.ai.telemetry.robustness` | torch, xgboost | `outputs/benchmarks/telemetry_opssat*/`, checkpoints under `outputs/experiments/` |
| SMAP/MSL supporting study | `python -m cosmos.ai.telemetry.smap_msl` | scikit-learn, torch | `outputs/benchmarks/telemetry_smap_msl/` |
| SpotGEO | `python -m cosmos.ai.vision.spotgeo preprocess`, `… classical`; `python -m cosmos.ai.vision.train_spotgeo --model unet --inputs both --seed 0` | torch, torchvision (downloads ImageNet ResNet-18 weights), jsonschema, scipy | `outputs/benchmarks/vision_spotgeo/` |
| COSMOS synthetic vision | `python -m cosmos.ai.vision.cosmos_synthetic generate|tinyyolo|yolov8n|heatmap` | torch; ultralytics for yolov8n | `outputs/benchmarks/vision_cosmos_synthetic/` |
| Landmark survival | `python -m cosmos.ai.survival.landmark` | torch, xgboost | `outputs/benchmarks/reentry_landmark/` |
| Propagator surrogate | `python -m cosmos.ai.surrogate generate`, `train`, `evaluate` | torch | `data/feature3_reentry/simulated/propagator_surrogate_v1/`, `outputs/benchmarks/reentry_surrogate/` |
| Learned telemetry monitor | `python -m cosmos.ai.telemetry.learned_monitor generate|train|benchmark|heldout` | torch | `outputs/benchmarks/telemetry_cosmos_synthetic/` |
| Twin couplings and prospective window | `python -m cosmos.ai.twin.couplings c2|c3|c4`; `python -m cosmos.ai.twin.prospective` | scikit-learn | `outputs/benchmarks/twin_couplings/`, `outputs/benchmarks/twin_prospective_t1/` |
| Reports and dashboard | `python -m cosmos.ai.report`; `python -m cosmos.ai.dashboard --root . --output outputs/dashboard/index.html --overwrite` | matplotlib | `outputs/benchmarks/SUMMARY.md`, `outputs/dashboard/index.html` |
| Legacy simulator chain | `notebooks/COSMOS_Demo.ipynb` (`cosmos.pipeline.run_pipeline(faults=…)`) | numpy, pandas, matplotlib | an outputs/figures folder created when the notebook's plots run (absent until then) |

Running a research driver again produces a **new** run and will not match a published number unless the archived configuration,
seed and backend versions are reproduced; the published numbers are frozen and verified by `scripts/verify_protected_artifacts.py`.

---

## 8. Run the complete COSMOS-AI application

The application is **one process**: the FastAPI console served by uvicorn. There is no separate backend, API or frontend
process and no JavaScript build; pages are server-rendered and charts are inline SVG. A scenario spawns one short-lived child
process (`scripts/run_pipeline.py`).

```bash
cd /data2/anupa/Final_Year_Project
source .venv/bin/activate                                         # 1. environment
python scripts/check_console_prerequisites.py                     # 2. dependency, data and artifact checks (exit 0)
python scripts/verify_protected_artifacts.py --label launch       # 3. optional: frozen artifacts and twin digests intact
python scripts/serve_console.py                                   # 4. start: http://127.0.0.1:8070/  (API docs http://127.0.0.1:8070/docs)
```

Health and readiness (from another terminal):

```bash
curl -s http://127.0.0.1:8070/api/health                          # {"status":"ok","service":"cosmos-ai-console",...}  liveness only
curl -s http://127.0.0.1:8070/api/ready | python -m json.tool | head -30   # "ready": true; checks: forecast table present, digest verified, complete run present, twin source reemitted/primary
```

`/api/ready` returns 503 with the failing check named when the forecast table is missing or its digest does not verify.
Options: `--port 9000`, `--host 0.0.0.0` (trusted networks only: no authentication), `--log-json` (JSON-lines request log with
request ids), `--root /other/checkout`, `--reload` (development). Measured on 2026-11-08: ready ≈ 1.5 s after start; first
`/demo` 1.7 s; first `/twin-state` ≈ 1.2–1.5 s (streams the 78 MB archive once, then cached).

Stop: `Ctrl+C` in the server terminal, or `pkill -f "scripts/serve_console.py"` (uvicorn exits cleanly on SIGTERM).

---

## 9. Execute the demonstration

Open <http://127.0.0.1:8070/demo> first. The thirteen-stage presenter script is [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md); the
verified protocol with expected API responses is [`DEMONSTRATION_PROTOCOL.md`](DEMONSTRATION_PROTOCOL.md). The table below is
the step-by-step procedure with the results measured on 2026-11-08.

| Step | Open | Do | You should see | Say / limitation |
|---|---|---|---|---|
| 1 | `/demo` | read the capability map | implemented / benchmark-only / unavailable / blocked labels; 13 stages with live values | nothing is live; every value is read from the dated archive |
| 2 | `/` | look at System readiness and STALE | READY; forecast digest verified; latest run `run_20261108T121517Z`, nine modules; snapshot age computed on load | readiness is about files and digests, not spacecraft |
| 3 | `/objects` | search `37607` | one result: ARIANE 5 R/B, rocket body, natural decay | search by NORAD id or name |
| 4 | `/objects/37607` | Orbital lifetime assessment | median 27.5 d, conformal interval, relation *crosses* the 30-day horizon; subgroup cue (design-derived A/M under-covered 0.5625 vs 0.80 at origin 2016) | mean elements only (no state vector); the cue is a subgroup frequency |
| 5 | `/objects/23806` | Orbital lifetime assessment | `INCOHERENT` → abstention (L17, 123 records) | the console abstains instead of substituting a value |
| 6 | `/objects/37607` | Re-entry assessment | p(30 d) = 1.0; quantiles 10.0 d, labelled zero-width/degenerate; variants side by side | disagreement is shown, not averaged |
| 7 | `/objects/25544` | Re-entry assessment | operator-controlled: abstention with the payload base rate 0.0053, no quantiles; lifetime unavailable | drag physics does not decide for controlled objects |
| 8 | `/objects/12` | Re-entry assessment | quantiles at 1826.25 d, labelled *at the cap* | "not within 1826.25 days", not a lifetime |
| 9 | `/telemetry`, then a channel | expand Methodology; open `/telemetry/1/channel_1` | three anonymised ESA-ADB missions; arm table (conformal_bh); real samples with ground-truth intervals, stride shown | no catalogue object has telemetry; no per-sample score is drawn |
| 10 | `/risk` | read the panel | 2,167 held-out Kelvins events, `cosmos_gated`, gate weight near zero; C4 abstains | never an operational warning; anonymised |
| 11 | `/debris`, then `/debris/1` | frame 1 | classical front end's 26 detections over 5 frames (F1 0.084); learned U-Net scores in the table only | no confidence, no time, no object association |
| 12 | `/objects/37607` | Decision priority | rank 2 of 31,396; rule `p(30 d) × 2 if mass ≥ 500 kg` read from the run manifest; score 2.0 | an ordering, not a probability; point probability, not the interval; effectiveness measured only on the non-blind T1 window |
| 13 | `/twin-state`, then `?policy=archived_only` | compare | re-emitted state primary, digest verified, 31,396 valid, 31,396/31,396 equivalent; archived read is amber (explicit policy, no per-output provenance) | model version unavailable everywhere: no fitted model is persisted |
| 14 | `/scenario` | preset **Fast decision subset**, run | new run in ≈ 3–5 s; module statuses, configuration digest, assumptions | real pipeline in a child process over saved artifacts; nothing retrained |
| 15 | `/runs`, latest run, `/compare?a=<latest>&b=run_20261108T083402Z` | compare | lineage per module; byte-identical tables by digest | comparison never merges runs |
| 16 | `/reports/object/37607` → Download | export | redacted HTML attachment; hashes and run id preserved | — |
| 17 | `/demo` stage 13 | summary | established vs out-of-scope list | live data, inference on demand, health verdicts, warnings, association and prospective validation are out of scope |

Automated equivalents: `python scripts/rehearse_demo.py --label demo` (13/13 ok) and
`python -m pytest tests/test_demo_workflow.py tests/test_e2e_demo_journey.py -q` (29 passed, ≈ 14 s).

---

## 10. API documentation

Base URL `http://127.0.0.1:8070`. Every response carries `X-Request-ID`. API errors are JSON
(`{"error": "...", "message": "...", "detail": "..."}`) with 404 (`data_unavailable`), 400 (`invalid_selection`), 422
(validation) or 500 (generic, no traceback). Browser routes render `error.html`. The live OpenAPI document is at `/openapi.json`
(interactive at `/docs`). Identifiers: missions are `1`, `2`, `3`; run tables are addressed by file name (`decision_ranking.csv`);
`policy` ∈ {`prefer_reemitted`, `reemitted_only`, `archived_only`}; `as_of` defaults to `2026-10-27`.

| Method | Endpoint | Purpose | Required parameters (optional in italics) | Example request | Expected response (measured) |
|---|---|---|---|---|---|
| GET | `/api/health` | liveness | — | `curl -s localhost:8070/api/health` | `{"status":"ok","service":"cosmos-ai-console","version":"1.0.0",...}` |
| GET | `/api/ready` | readiness record (200 / 503) | — | `curl -s localhost:8070/api/ready` | `{"ready": true, "schema_version": "api/1.2", "checks": {"forecast_table_present": true, "dated_forecast_digest_state": "verified", "complete_run_present": true, "twin_state_source": {...}}, "latest_run": {...}, "schema_versions": {...}}` |
| GET | `/api/overview` | mission overview | — | `curl -s localhost:8070/api/overview` | latest run (nine modules, tables), abstention counts, datasets strip, freshness |
| GET | `/api/datasets` | evidence inventory and policy | — | `curl -s localhost:8070/api/datasets` | `datasets[]` with `evidence_class`, `available`, `records`, `identity`; `evidence_policy` |
| GET | `/api/objects/search` | search by NORAD id or name | *q* (≤ 64 chars), *limit* 50 (1–500), *as_of* | `curl -s "localhost:8070/api/objects/search?q=37607&limit=2"` | `{"results":[{"norad":37607,"name":"ARIANE 5 R/B","object_class":"R","regime":"natural_decay","perigee_km":122.0,"apogee_km":11622.0,"inclination_deg":2.46,"p_reentry_30d":1.0}]}` |
| GET | `/api/objects/{norad}` | full object record | `norad`; *policy* | `curl -s "localhost:8070/api/objects/37607?policy=prefer_reemitted"` | `object_record/1.1`: identity, elements, `lifetime`, `reentry`, `decision_priority` (rank 2, `ranked_objects` 31396), `twin_state`, `evidence` statuses |
| GET | `/api/objects/{norad}/twin` | twin-state record and equivalence for one object | `norad`; *as_of*, *policy* | `curl -s localhost:8070/api/objects/23806/twin` | `twin_state/1.1`: `selection`, `record`, `equivalence` (`status: equal`, `not_comparable` reasons such as L17) |
| GET | `/api/twin-state` | archive selection, integrity, equivalence | *as_of*, *policy*, *run_id* | `curl -s "localhost:8070/api/twin-state?policy=archived_only"` | `selection.selected`, `status`, candidates with `digest_state`, `record_count`; `integrity`; `equivalence` (31,396 compared / equal) |
| GET | `/api/telemetry/missions` | ESA-ADB missions | — | `curl -s localhost:8070/api/telemetry/missions` | 3 missions: channels 76/100/48, samples 1.47 M/0.92 M/0.93 M, `anonymised: true` |
| GET | `/api/telemetry/{mission}/channels` | channels of a mission | `mission` ∈ 1,2,3 | `curl -s localhost:8070/api/telemetry/1/channels` | `{"mission":"1","channels":[{"channel":"channel_1","subsystem":"subsystem_1","is_target":false,"labelled_intervals":0},...]}` |
| GET | `/api/telemetry/{mission}/{channel}` | strided series with labelled intervals | `mission`, `channel`; *max_points* 2000 (10–20000) | `curl -s "localhost:8070/api/telemetry/1/channel_1?max_points=50"` | `times[50]`, `values[50]`, `decimation_stride: 29457`, `total_samples: 1472832`, `labelled_intervals`, `anonymised: true` |
| GET | `/api/debris/sequences` | SpotGEO sequences with saved detections | *limit* 40 (1–500) | `curl -s "localhost:8070/api/debris/sequences?limit=1"` | `{"sequences":[{"sequence_id":1,"frames":5,"detections":26,"images_present":true}]}` |
| GET | `/api/debris/{sequence_id}` | one sequence | `sequence_id` | `curl -s localhost:8070/api/debris/1` | frames with detections, `detector`, `confidence_available: false`, `timestamp_available: false` |
| GET | `/api/debris/{sequence_id}/frame/{frame}.png` | the real frame image | `sequence_id`, `frame` 1–5 | `curl -s -o frame.png localhost:8070/api/debris/1/frame/1.png` | `image/png`, 131,763 bytes for sequence 1 frame 1 |
| GET | `/api/risk/collision` | Kelvins CAC events with archived predictions | *limit* 200 (1–3000), *model* (`cosmos_gated` default; also catboost, kumo, lightgbm, mlp, persistence, stack_constant, tabicl, tabm, xgboost) | `curl -s "localhost:8070/api/risk/collision?limit=2&model=cosmos_gated"` | `events_total: 2167`, events with `collision_probability`, `interval_lower/upper` (level 0.9), `true_final_log10_risk`; `identity_linkable: false`; `escalation_available: false` |
| GET | `/api/runs` | run list | — | `curl -s localhost:8070/api/runs` | `{"runs":[{"run_id":"run_20261108T121517Z","successful":true,"module_counts":{"success":9},"tables":[...]}, ...]}` |
| GET | `/api/runs/{run_id}` | run manifest with lineage | `run_id` | `curl -s localhost:8070/api/runs/run_20261108T121517Z` | `run_manifest/1.2`: per-module `status`, `provenance` (input hashes, code revision, config digest), `lineage` |
| GET | `/api/runs/{run_id}/ranking` | decision ranking rows | `run_id`; *limit* 25 (1–1000) | `curl -s "localhost:8070/api/runs/run_20261108T121517Z/ranking?limit=2"` | rows with `rank`, `object_id`, `p_reentry_30d`, `mass_kg`, `priority_score`, `horizon_relation` |
| GET | `/api/runs/{run_id}/tables/{name}` | any run table as JSON | `run_id`, `name` (file name, e.g. `lifetime_estimates.csv`); *limit* 200 (1–20000) | `curl -s "localhost:8070/api/runs/run_20261108T121517Z/tables/decision_ranking.csv?limit=1"` | `{"table":"decision_ranking.csv","rows":1,"columns":[...],"records":[...]}`; a name without `.csv` → 400 `invalid_selection` |
| GET | `/api/compare` | value-level comparison of two runs | `a`, `b` | `curl -s "localhost:8070/api/compare?a=run_20261108T121517Z&b=run_20261108T083402Z"` | per table `status: identical` (byte-identical by SHA-256) or joined differences by key column |
| GET | `/api/prospective` | prospective-mode status | — | `curl -s localhost:8070/api/prospective` | `{"mode":"prospective","enabled":false,"status":"BLOCKED","assessment":{...digest_verification..., outcome coverage ends 2026-10-26}}` |
| GET | `/api/reports/object/{norad}` | assessment report as JSON | `norad`; *run_id*, *redact* (false) | `curl -s "localhost:8070/api/reports/object/37607?redact=true"` | sections `subject`, `inputs`, `provenance`, `orbital_elements`, `physical`, `lifetime`, `reentry`, `horizon_relation`, `twin_state`, `decision_priority` |
| POST | `/api/scenario` | run the pipeline into a new run directory (child process, timeout 900 s) | JSON body `ScenarioRequest`: *as_of* "2026-10-27", *limit* 500 (1–40000), *collision_limit* 200, *debris_sequence_limit* 5, *health_calibrator* "conformal_bh", *collision_model* "cosmos_gated", *twin_source_policy* "prefer_reemitted", *modules* (list or null = all) | `curl -s -X POST -H 'Content-Type: application/json' -d '{"limit":500,"modules":["catalogue_state","lifetime","reentry","decision_priority"]}' localhost:8070/api/scenario` | measured 2.9 s: `{"mode":"scenario","run_id":"run_20261108T184949354706Z","exit_code":0,"successful":true,"partial":false,"run_url":"/runs/…","manifest":{...},"config_sha256":"b61de62f…","assumptions":[7 strings],"process":{"isolated":true,"exit_code":0}}`; invalid body → 422 |

Page routes (HTML): `/`, `/demo`, `/objects[?q=]`, `/objects/{norad}[?policy=]`, `/twin-state[?policy=&run_id=]`, `/telemetry`,
`/telemetry/{mission}/{channel}[?points=]`, `/debris`, `/debris/{sequence_id}[?frame=]`, `/risk[?limit=]`, `/runs`, `/runs/{run_id}`,
`/compare?a=&b=`, `/prospective`, `/scenario`, `/reports/object/{norad}[?run_id=]`, `/reports/object/{norad}/download` (HTML attachment,
redacted); static files under `/static/`.

---

## 11. Outputs and results

| What | Where | How to read it |
|---|---|---|
| Per-object predictions (lifetime, re-entry, priority) as served | `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` (columns incl. `median_days_lifetime`, `lifetime_lo90/hi90`, `p_lifetime_30d/90d/1yr`, `p_30d/p_90d/p_1yr`, `lo90/median/hi90_days`) and the twin-state archives (`twins.jsonl`, one JSON record per object) | one row/record per NORAD id; the console's object page and `/api/objects/{norad}` are the readable form |
| Pipeline / scenario runs | `outputs/pipeline/run_<UTC>Z/` — `run_manifest.json` + eight tables | `run_manifest.json`: `modules.<name>.status/provenance/lineage`, `config_sha256`; `decision_ranking.csv` sorted by `priority_score`; `lifetime_noncoherent_horizons.csv` lists the L17 abstentions; `twin_equivalence.csv` per-object verdicts |
| Reports | `/reports/object/{norad}` (HTML), `/reports/object/{norad}/download` (redacted HTML attachment `cosmos_assessment_NORAD<n>_<ts>.html`), `/api/reports/object/{norad}` (JSON); earlier saved copies under `outputs/product/reports/` | the `provenance` section lists run id, code revision and input hashes; `freshness` says STALE with the snapshot age |
| Research results | `outputs/benchmarks/<study>/` (`results.csv`, `summary.json`, `*_test.csv`, `test_predictions.npz`), `outputs/e3_e5/`, `outputs/am_design_stage1/`, `outputs/t1_ranking_utility/`, `outputs/g5d_origin2006/`, `outputs/phase_*` | each study's docs/research report names the file; numbers in the manuscripts cite these paths |
| Figures | `paper/figures/` (frozen release: 18 figures, 107 hashed files, `RELEASE_MANIFEST.{json,md}`), `outputs/g5_figures/`, `thesis/figures/` | `paper/figures/RELEASE_MANIFEST.md` lists every figure, its source data and generating script |
| Logs | server: stdout (JSON lines with `--log-json`: `ts`, `level`, `request_id`, `method`, `path`, `status`, `duration_ms`); a captured example `outputs/audit/serve_console_fresh_process_20261108.log`; test logs `outputs/audit/pytest_full_*.log` | request ids match the `X-Request-ID` header |
| Evaluation and verification records | `outputs/audit/` — `protected_artifacts_<label>_<UTC>.json`, `twin_state_integration_<label>_<UTC>.json`, `demo_rehearsal_<label>_<UTC>.json`, `console_benchmark_*.json`, `console_cold_profile_*.json`, `manuscript_claim_audit_*.json`, `fresh_clone_lfs_verification_*.json` | each is dated and self-describing (`label`, `evaluated_at`/`at`) |
| Provenance manifests | `run_manifest.json` per run; `outputs/twin/as_of_2026-10-27_reemitted_v1/REEMISSION_MANIFEST.json`; `data/DATASET_MANIFEST.csv`; `paper/figures/RELEASE_MANIFEST.json`; `research_design/preregistration/freeze*.json`; `outputs/g5d_origin2006/prereg_freeze.json` | all SHA-256 based; `scripts/verify_protected_artifacts.py` checks them |

Interpretation rules (from the console's own labels): STALE = snapshot age, not an error; UNAVAILABLE / UNSUPPORTED = evidence does
not exist or cannot be attributed, never a bug; `interval_quality` kinds `degenerate`, `spread`, `at_cap`, `unavailable` qualify
every interval; a `priority_score` is an ordering, not a probability; a benchmark F0.5 is a detection-performance figure of an arm,
not a spacecraft health score.

---

## 12. Testing and validation

Run from the repository root with `.venv` active. No `pytest.ini`/`pyproject.toml`: pytest discovers `tests/`. Results below
are from the final run at Commit B on 2026-11-08 (`outputs/audit/pytest_full_20261108_post_commit_b.log`).

| Purpose | Command | Result 2026-11-08 |
|---|---|---|
| All tests | `python -m pytest tests/ -q -rs -p no:cacheprovider` | **508 passed, 3 skipped, 0 failed** in 129 s |
| Skips (optional artifacts) | shown by `-rs` | `tests/test_ai.py:51` ×3 — baseline code snapshot missing; learned telemetry backend not trained; surrogate footprint not trained |
| Console and demonstration | `python -m pytest tests/test_product.py tests/test_phase_b_console.py tests/test_demo_workflow.py tests/test_e2e_demo_journey.py -q` | demo files alone: 29 passed in 13.8 s |
| API behaviour | `python -m pytest tests/test_phase_b_console.py tests/test_p3a_observability.py tests/test_p3a_manifest.py -q` | in suite |
| Twin state and chain | `python -m pytest tests/test_p3b_twin_state.py tests/test_twin_state_consistency.py tests/test_p3b_chain_unchanged.py tests/test_p1_reemission.py -q` | in suite |
| Figure release and approved head | `python -m pytest tests/test_figures.py tests/test_approved_head.py -q` | 52 passed |
| Manuscript | `python -m pytest tests/test_jint_manuscript.py -q`; `python scripts/audit_manuscript_claims.py` | 16 passed; 147 checks, 139 PASS, 8 NOT_EVALUABLE, 0 FAIL |
| Protected artifacts | `python scripts/verify_protected_artifacts.py --label check` | `all_protected_ok: True` |
| Dataset checksums | `python -m cosmos.ai.data.validate` | rewrites `data/DATASET_REPORT.{json,md}` (restore afterwards on the project checkout, §4.2 note f) |
| Twin integrity and equivalence | `python scripts/twin_state_integrity.py` | `primary_verified`, 31,396 / 31,396 equal |
| Fresh-process demonstration | `python scripts/rehearse_demo.py --label check` | 13/13 ok, ≈ 11 s |
| Performance (both definitions) | `python scripts/benchmark_console.py --label check && python scripts/profile_console_cold.py --label check` | overview 180 ms cold / 37 ms warm, peak 225 MB; fresh process import 534 ms, store + first overview ≈ 553 ms, peak 273 MB |
| Reproducibility of a pipeline run | `python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh` then `GET /api/compare?a=<new>&b=run_20261108T121517Z` | tables byte-identical by digest (same snapshot, same code) |

---

## 13. Troubleshooting

| Error / symptom | Likely cause | Exact solution | Verification |
|---|---|---|---|
| `ModuleNotFoundError: No module named 'cosmos'` | wrong working directory or interpreter | `cd /data2/anupa/Final_Year_Project && source .venv/bin/activate`; run scripts as `python scripts/...` from the root (scripts insert the root on `sys.path`) | `python -c "import cosmos; print(cosmos.__file__)"` prints a path under the repository |
| `ModuleNotFoundError: fastapi` (or uvicorn, jinja2) | console dependencies not installed in the active environment | `pip install -r requirements-product.txt` | `python scripts/check_console_prerequisites.py` → `launchable: true` |
| Prerequisite checker: forecast table **missing**; `/api/ready` 503 | LFS objects not fetched (file is a ≈130-byte pointer) | `git lfs install && git lfs pull` | `sha256sum outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` = `b15644aab581…`; `/api/ready` 200 |
| Clone stops with `fatal: the remote end hung up unexpectedly`, most files missing | the LFS filter in `~/.gitconfig` points at a `git-lfs` binary that no longer exists | `git lfs install` (or `git lfs install --local` inside the clone), then `git checkout -f HEAD -- . && git lfs pull` | `git lfs ls-files` shows `*` (present) for every entry; `git lfs fsck` OK |
| Twin-state screens say "fallback" to the archived 1.0 record | re-emitted `twins.jsonl` is a pointer or absent | `git lfs pull`, or regenerate deterministically: `python -m cosmos.ai.twin.reemit --as-of 2026-10-27` | `python scripts/twin_state_integrity.py` → `selected: reemitted`, `integrity: ok` |
| Object priorities and `/runs` empty; readiness warns "no complete pipeline run" | fresh clone has no `outputs/pipeline/run_*` (regenerable, not committed) | `python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh` | `/api/ready` shows `complete_run_present: true` |
| `OSError: [Errno 98] Address already in use` at start | port 8070 taken | `python scripts/serve_console.py --port 9000`, or stop the other server: `pkill -f "scripts/serve_console.py"` | `ss -ltn | grep 8070` empty |
| Telemetry screen UNAVAILABLE | `data/feature1_health/external/esa_ad/prepared/mission{m}.npz` absent (ESA-ADB not carried in LFS) | download ESA-ADB (§5) then `python -m cosmos.datasets prepare esa_ad`; or accept the labelled UNAVAILABLE state | `/api/telemetry/missions` lists the missions |
| Debris screen UNAVAILABLE | SpotGEO frames not downloaded (45 GiB, not in LFS) | `python -m cosmos.ai.data.download spotgeo` (large; needs disk and time) | `/api/debris/sequences?limit=1` returns a sequence with `images_present: true` |
| Scenario returns `exit_code != 0` / `partial: true` | a requested module's artifact is missing (pointer or absent) | check the manifest's module `reason`; fetch the artifact (`git lfs pull`) | re-run the scenario; `successful: true` |
| First `/twin-state` or first telemetry channel takes 1–2 s | one-off streaming of the 78 MB archive / 448 MB mission array | expected; cached afterwards (KNOWN_LIMITATIONS P17) | second load ≈ 20–40 ms |
| High memory | telemetry mission arrays or a very large scenario `--limit` | one mission is cached at a time; keep scenario limits default; use the CLI for bulk runs | RSS in `/api/ready` → `cache` block and the benchmark script |
| `ImportError` for `tabm`, `tabicl`, `sdm` (Kumo), `lightgbm`, `catboost`, `pymsis`, `statsmodels` when running a research driver | optional backends not installed (deliberately; record any environment change) | run only the arms whose backends exist, or install with approval into the environment and record it against `outputs/baseline/venv_freeze_2026-10-24.txt` | the driver's `summary.json["fits"]` lists the arms that ran |
| `tests/test_figures.py::test_manifest_git_state_is_consistent_with_git` fails with "nothing may be staged" | files are staged in the index | commit or unstage, then re-run | 39 figure tests pass with a clean index |
| `verify_protected_artifacts.py` → `head_ok: False` | HEAD is not an approved checkpoint or a descendant of one (unrelated branch / detached commit) | check out the release branch | `all_protected_ok: True` |
| Thesis `render.py` fails: pandoc not found | DOCX/PDF toolchain absent | install pandoc 3.11 + pandoc-crossref + LibreOffice (see `thesis/README.md`) or use the Markdown draft `thesis/build/COSMOS_Thesis_2026-11-08_draft.md` (`python thesis/tools/render_draft_md.py`) | draft renders with 1,072 keys and 0 unresolved placeholders |

---

## 14. Clean shutdown and reproducibility

- **Stop everything:** `Ctrl+C` in the server terminal, or `pkill -f "scripts/serve_console.py"`. A running scenario's child process
  (`scripts/run_pipeline.py`) finishes within seconds; a partially written run directory is reported by the manifest, never
  overwritten, and can be deleted by hand if unwanted.
- **Restart from a clean terminal:** `cd /data2/anupa/Final_Year_Project && source .venv/bin/activate && python scripts/check_console_prerequisites.py && python scripts/serve_console.py`.
- **Reproduce the demonstration:** `python scripts/rehearse_demo.py --label repro` (fresh process, 13 stages) and the e2e tests
  (`tests/test_e2e_demo_journey.py`) assert the same values the presenter quotes.
- **Verify the same outputs:** a new pipeline run on the same snapshot and code produces tables byte-identical to
  `run_20261108T121517Z` (`/api/compare` reports `identical` by SHA-256); `python -m cosmos.ai.twin.reemit` reproduces the
  re-emitted twin state with sha `6bb4871f…`; `python scripts/verify_protected_artifacts.py` confirms every frozen hash.
- **Archived versus newly generated:** archived = everything under `outputs/twin/`, `outputs/benchmarks/`, `paper/figures/` and the
  committed audit records (frozen, hash-verified); newly generated = any `outputs/pipeline/run_<UTC>/` you create (a scenario or
  `run_pipeline.py`), new `outputs/audit/*_<label>_<UTC>.json` records, and any research-driver run under `outputs/experiments/`.
  The console labels a run's lineage with its code revision; a dirty working tree is shown as `MODIFIED` (P14).

---

## 15. Known limitations and future work

**Completed.** Nine-module runtime chain with versioned manifests; versioned twin state with explicit source policies, streaming
integrity and 31,396/31,396 equivalence; the console with readiness, policies, error handling, run comparison, scenario execution,
reports and the thirteen-stage guided demonstration; the pre-registered ESA-ADB study (K6), the K7 lifetime benchmark with its
selection-regret and subgroup-coverage findings, the K8 withdrawal, the K1 integration finding, the exploratory T1 ranking-utility
analysis; JINT and K7 manuscripts with a zero-failure claim audit; thesis sources with an evidence-driven Markdown draft; the
release documentation.

**Partially completed.** Scenario execution is synchronous; run comparison compares tables above 12 MB by digest only; fresh-process
performance targets (400 ms / 250 MB) not met (≈ 553 ms / 273 MB); thesis DOCX/PDF await an external toolchain; author-only
manuscript fields, licence and data DOI are the author's.

**Research-only capabilities (never in the console's decision path).** ESA-ADB, Kelvins CAC and SpotGEO benchmarks (anonymised or
uncalibrated, never attributed to an object); OPSSAT-AD and SMAP/MSL studies; `fusion.decide`; the propagator surrogate; the
legacy simulator chain.

**Blocked.** Prospective (blind) validation (needs a catalogue snapshot dated ≥ 2026-11-26 and download approval); full
training-level reproducibility and X6 Stage 2 (learner backends not installed); remote fresh-clone retrieval (needs the push).

**Scientific limitations preserved (not software bugs).** No identity-linked public dataset spans telemetry, conjunctions and
re-entry (L1); space-weather features are constant within the snapshot; cross-satellite generalisation and health-to-conjunction
fusion are not established (C4 abstains); re-entry variants disagree up to 10.6×; 123 L17 lifetime records are incoherent and
abstained; isotonic probabilities disagree with quantile outputs for some objects (coherent reading reported separately);
design-derived area-to-mass objects are under-covered (0.5625 vs 0.80); archived evaluations are not prospective validation; the
priority uses the point probability; no model weights exist for the twin chain, so no run-time inference is possible or claimed.
Full register: [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) and `docs/research/limitations_register.md`.

**Future research.** Blind evaluation on the next snapshot; stratifying the conformal calibration by area-to-mass provenance;
refitting the archived learners once their backends are available; an interval-aware priority rule; a linked dataset that would
make C4 testable.
