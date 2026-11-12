# JIRS reproducibility and data availability audit (Phase 6)

Date 2026-11-04 · revision `78ee339`

**Verdict: prediction-level reproducibility is strong and verified. Training-level reproducibility
is absent and cannot be restored. One critical blocker remains: there is no public artifact.**

---

## 1. Reproducibility classification of every published result

| Result | Training-level | Prediction-level | Classification |
|---|---|---|---|
| Orbital-lifetime leaderboards, both published origins | ✗ (5 of 7 backends unavailable; no environment recorded) | ✓ **exact, 0.000e+00 deviation** | **Prediction-level reproducible** |
| Selection-transfer ρ = 0.000, both origins | ✗ | ✓ | Prediction-level |
| Rolling-origin slice analysis, 23.64 % inversion, coverage | ✗ | ✓ | Prediction-level |
| Loss-composition ratios (4.13× / 6.60×) | ✗ | ✓ | Prediction-level |
| Coupling ablations C1–C3 | ✗ | ✓ | Prediction-level |
| E12 same-learner test | ✗ (reuses cached predictions by design) | ✓ (reconstruction verified against the published archive before use) | Prediction-level |
| G5d origin-2006 results | ✗ (only 2 of 7 learners fittable) | ✓ (archive present) | Prediction-level, **but see gap R4** |
| **OPS-SAT anomaly detection leaderboard** | **✓ — `torch` + `xgboost` only, both available** | **✗ — `test_scores_official.npz` absent** | **Partially reproducible (training yes, prediction archive missing)** |
| OPS-SAT paired significance comparison | ✓ (refittable) | **✗ — source archive absent** | **Partially reproducible** |
| ESA-ADB results | ✗ (`patchtst`, encoders not all declared) | ✓ (`results.csv` present) | Prediction-level |
| Conjunction / Kelvins CAC results | ✗ (`kumo`/`tabicl` unavailable) | ✓ (`test_predictions.npz` present) | Prediction-level |
| Debris / SpotGEO results | partial | ✓ | Prediction-level |
| T1 pseudo-prospective evaluation | ✗ | ✓ | Prediction-level |
| 2026-10-27 dated forecast | ✗ | ✓ digest-verified, **unscored** | Pending |

**Note the asymmetry.** The orbital-lifetime work is prediction-reproducible but not
training-reproducible. **The OPS-SAT work is the reverse** — it *is* training-reproducible (only
`torch` and `xgboost` are needed, and both are installed) but its score archive is missing. These
require opposite remedies, and the OPS-SAT one is trivially fixable by persisting the archive
during experiment E1.

## 2. The five undeclared backends and the uninvoked provenance module

You asked me to investigate these specifically.

### 2.1 What is actually wrong

| Backend | Learner | On PyPI now? | In `requirements-ai.txt`? | In the 2026-10-24 freeze? |
|---|---|---|---|---|
| `lightgbm` | lightgbm | ✓ 4.7.0 | ✗ | ✓ `4.7.0` |
| `catboost` | catboost | ✓ 1.2.10 | ✗ | ✗ |
| `tabm` | tabm | ✓ 0.0.3 | ✗ | ✗ |
| `tabicl` | tabicl | ✓ 2.2.0 | ✗ | ✗ |
| `sdm` | kumo | ✓ 1.6.0 — **commercial vendor library** (`sdm.models.KumoTabular`) | ✗ | ✗ |

**The cause is not package unavailability.** All five are currently published. The failures are:

1. **Declaration failure.** None of the five appears in any requirements file. The declared
   environment was never capable of refitting five of seven published arms.
2. **The one environment snapshot cannot be the fitting environment.** `venv_freeze_2026-10-24.txt`
   (303 packages) contains `lightgbm`, `torch==2.13.0+xpu` and `xgboost==3.4.1` but **not**
   `catboost`, `tabm`, `tabicl` or `sdm`. Four published arms were therefore fitted somewhere that
   snapshot does not describe.
3. **No per-run environment record exists.** Each origin's `summary.json` records splits,
   selection scores, tuned hyperparameters, gates and timings — and **no package versions, no
   Python version, no git revision.**
4. **Environment drift.** `lightgbm` was present at the freeze and is not importable now.
5. **By the project's own standard, `mlp` is also not reproducible**: the interpreter carries
   `torch 2.14.0+xpu` against the freeze's `2.13.0+xpu`. Strictly, **1 of 7** matches the recorded
   environment, not 2 of 7.
6. **`kumo` is irreproducible in principle** for any reader without a commercial vendor licence —
   a stronger limitation than a missing public package, and one the manuscript must disclose.

### 2.2 `provenance.py` — built, tested, never called

`cosmos/ai/provenance.py` provides `run_metadata()` and `tracked_run()`, which capture exactly the
git revision, Python version and package versions that are missing. A repository-wide search finds
**no call site** for either function outside the module itself. The capability was written and
never wired in.

**This is the proximate cause of the whole reproducibility failure, and it is a two-line fix for
future runs.** It cannot retroactively record an environment that was never captured.

### 2.3 What this cost the science

The gap is not merely bookkeeping. The pre-registered origin-2006 experiment was designed for
seven learners and could fit **two**. That is why hypothesis H1 is NOT_EVALUABLE and H3
UNDERPOWERED, and why the experiment's overall outcome is INCONCLUSIVE. **A reproducibility gap
destroyed the power of the project's only pre-registered experiment.** That is the most concrete
argument available for recording environments prospectively, and it belongs in the paper.

## 3. Artifact audit

| Item | Status |
|---|---|
| Dataset source and provenance | ✓ 15 manifests; GCAT, CelesTrak, ESA-ADB, OPS-SAT, Kelvins CAC, SpotGEO all recorded with source URLs |
| Licensing recorded | ✓ 12 of 15; 3 are locally generated (2 synthetic, 1 derived) and record generator + class |
| **Inherited terms for derived data** | ✗ `feature3_reentry/processed` names its three GCAT/CelesTrak inputs but states no inherited licence — **gap R1** |
| Preprocessing scripts | ✓ `cosmos.ai.lifetime.catalogue` and module pipelines, in-repo |
| Split definitions | ✓ in code and reproducible; sizes verified; origin-2006 splits match the pre-registration exactly |
| Model configurations | ✓ tuned hyperparameters recorded per learner in `summary.json` |
| Seeds | ✓ `SEEDS = (0,1,2,3,4)`, `seed=0` for tuning; 5 seeds for telemetry |
| **Environment snapshots** | ✗ one stale, incomplete snapshot; none per run — **gap R2** |
| **Dependency versions** | ✗ five backends undeclared — **gap R3** |
| Historical prediction artifacts | ✓ present for lifetime (both origins), G5d, conjunction, ESA-ADB, SpotGEO |
| **OPS-SAT score archive** | ✗ `test_scores_official.npz` referenced by `report.py:247` but absent — **gap R4** |
| Evaluation scripts | ✓ in-repo; plus audit harnesses that re-derive headline numbers |
| **Model checkpoints** | ✗ none released; and for `kumo` could not be released (vendor) — **gap R5** |
| Checksums | ✓ pre-registration freeze (28 files), dated forecast digest, 10 manuscript source artifacts. ✗ **not** for the origin-2006 prediction archive — **gap R6** |
| Documentation | ✓ extensive research documentation; architecture and dataflow docs present |
| Reproduction instructions | ⚠️ partial — audit harnesses are documented; no single top-level "reproduce the paper" entry point — **gap R7** |
| **Public availability** | ✗ **no DOI, no deposit, no release, no licence — CRITICAL blocker R8** |

## 4. Integrity verification (all intact)

| Item | State |
|---|---|
| Pre-registration freeze, 28 files | **INTACT** — 0 changed, 0 missing |
| G5d pre-registration hash | **INTACT** — `9ea4bf4171cad1b8…`, unchanged since sealed before any fit |
| Dated 2026-10-27 forecast digest | **INTACT** |
| Manuscript source artifacts | **10 / 10** present and digested |
| Audit harness | **27 / 28 checks PASS**, 0 critical |
| Test suite | **217 / 217 PASS** |

## 5. Reproducibility statement for a JIRS manuscript

> All reported quantitative results are reproducible at the **prediction level**: per-object and
> per-fragment model outputs are archived for the orbital-lifetime benchmark at every temporal
> origin, and every reported score, rank, bootstrap interval and coverage figure was recomputed
> from those archives to exact agreement (maximum absolute deviation 0.000e+00).
>
> Reproducibility at the **training level** differs by module. The spacecraft-telemetry
> anomaly-detection experiments depend only on `torch` and `xgboost` and are refittable from the
> declared environment. The orbital-lifetime benchmark is **not** refittable: five of seven learner
> backends are undeclared in the project's requirements files, one of them is a commercial vendor
> library, and no software environment was recorded for any published run, so the original fitting
> environment cannot be reconstructed. Tuned hyperparameters and random seeds **are** recorded per
> learner, so an independent party can refit under a documented configuration but not under the
> original software build.
>
> We report these levels separately and deliberately. They are different properties, they differ
> by module, and a single unqualified claim of reproducibility would misdescribe all of them.

**Prohibited wording:** "fully reproducible"; "the environment is captured in requirements-ai.txt";
any suggestion that installing current backend versions would reproduce the published models.

## 6. Gap register

| ID | Gap | Severity | Fix |
|---|---|---|---|
| **R8** | **No public artifact — no DOI, deposit, release or licence** | **CRITICAL — blocks submission** | `BENCHMARK_RELEASE_PLAN.md` |
| R2 | No environment recorded per run; `provenance.py` never called | Major | Wire it in (forward-only) |
| R3 | Five backends undeclared | Major | Declare with forward-pin comment |
| R4 | OPS-SAT score archive absent | Major | Persist during E1 |
| R5 | No checkpoints released; `kumo` cannot be | Major | Release what is permissible; disclose the vendor constraint |
| R6 | Origin-2006 prediction archive not checksummed | Moderate | Add to the digest manifest |
| R7 | No single reproduce-the-paper entry point | Moderate | Add a `REPRODUCE.md` and a driver script |
| R1 | Derived-dataset inherited terms unstated | Minor | One manifest field |

**Forward-only remediation changes no published artifact and no conclusion.** None of it can
retroactively record an environment that was never captured, and the manuscript must say so.
