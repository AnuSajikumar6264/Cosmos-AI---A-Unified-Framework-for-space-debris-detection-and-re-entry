# Mission Intelligence Console — reproducible launch path (P0.4, 2026-11-08)

The console is a **read-only evidence viewer** over archived COSMOS-AI artifacts and one dated
catalogue snapshot (2026-10-27). It runs no model at request time and connects to no live source.
Starting it never writes anything except when you explicitly run a scenario, which creates a new
directory under `outputs/pipeline/`.

Shorter and longer forms of this document: [`COSMOS_AI_QUICKSTART.md`](COSMOS_AI_QUICKSTART.md) (ten-minute start) and
[`COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md`](COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md) (setup, datasets, models, modules, API, outputs, tests, troubleshooting).

## 0. Release prerequisite: Git LFS

The repository stores dataset payloads, experiment arrays and the 78 MB re-emitted twin state
(`outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl`, sha `6bb4871f…`) in **Git LFS**. A fresh clone needs
`git lfs install` before cloning (or `git lfs pull` after it); without the LFS objects the forecast table
(`forecast_table.csv.gz`) and the re-emitted twin state are pointer files, the prerequisite check reports the forecast table
as missing, and the twin-state screens fall back to the archived `twin_state/1.0` record with a label. Verify after
retrieval with `python scripts/verify_protected_artifacts.py --label clone` and `python scripts/twin_state_integrity.py`.

Exact clone and retrieval commands (verified 2026-11-08 against a local clone of release commit A; the LFS objects reach
GitHub only when the owner approves the push — until then the public remote holds the 2026-11-06 state `78ee339` and does not
yet hold the re-emitted twin-state object):

```bash
git lfs install                                   # once per machine: installs the LFS filter in ~/.gitconfig
git clone --branch product/mission-intelligence-console https://github.com/AnuSajikumar6264/Cosmos-AI-.git cosmos-ai
cd cosmos-ai
git lfs pull                                      # 831 LFS files, ≈ 0.9 GB; the twin state alone is 78,616,187 bytes
git lfs fsck                                      # "Git LFS fsck OK"
sha256sum outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl   # 6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84
cat outputs/twin/as_of_2026-10-27_reemitted_v1/TWINS_SHA256.txt     # the same digest, recorded at re-emission
python scripts/twin_state_integrity.py            # selected: reemitted, integrity: ok (equivalence needs a pipeline run, see §3)
python scripts/verify_protected_artifacts.py --label clone
```

If a clone's checkout stops with `fatal: the remote end hung up unexpectedly` and leaves most files missing, the LFS
filter configured in `~/.gitconfig` points at a `git-lfs` binary that no longer exists; run `git lfs install` (or
`git lfs install --local` inside the clone) and then `git checkout -f HEAD -- .` followed by `git lfs pull`. A fresh clone
has no `outputs/pipeline/` run directories (they are regenerable and deliberately not committed): readiness reports
`complete_run_present: false` with a warning, the twin-state screens work, and one run restores the object priorities and
run explorer (§3, `python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh`, ≈ 9 s).

## 1. Check prerequisites (read-only)

```bash
cd /data2/anupa/Final_Year_Project
python scripts/check_console_prerequisites.py          # or --json
```

Exit code 0 means launchable. The checker separates:

| Class | Items | If missing |
|---|---|---|
| **Required** | Python ≥ 3.11; packages `fastapi`, `uvicorn`, `jinja2`, `pandas`, `numpy`; `outputs/twin/as_of_2026-10-27/forecast_table.csv.gz` and `FORECAST_SHA256.txt` | the console cannot start or shows no catalogue — restore the checkout; do not regenerate the forecast (its learner backend `tabm` is not installed and regeneration is not authorised) |
| **Optional artifacts** | `data/feature1_health/external/esa_ad/prepared/mission{1,2,3}.npz` (telemetry screens), SpotGEO test frames and saved detections (debris screens), `conjunction_kelvins_cac/test_predictions.npz` (risk screen), `telemetry_esa_adb/results.csv` (benchmark arms), `outputs/am_design_stage1/results.json` (subgroup-coverage cue), at least one run under `outputs/pipeline/` (run explorer, reports) | the corresponding screen reports **UNAVAILABLE** with the reason; nothing is substituted |
| **Optional backends** | `torch`, `xgboost`, `scikit-learn`, `scipy`, `statsmodels`, `lightgbm`, `catboost`, `tabm`, `tabicl`, `kumo`, `pymsis` | **never needed to serve the console**; they matter only for re-running study code. Absent today: `statsmodels`, `lightgbm`, `catboost`, `tabm`, `tabicl`, `kumo`, `pymsis`. Do not install them silently — record any environment change against `outputs/audit/environment_lock_20261106.txt` |

## 2. Launch

```bash
python scripts/serve_console.py                    # http://127.0.0.1:8070/   (API docs: /docs)
python scripts/serve_console.py --port 9000        # another port
python scripts/serve_console.py --host 0.0.0.0     # reachable from another machine — trusted networks only; no authentication
python scripts/serve_console.py --log-json         # structured JSON-lines logs: request id, method, path, status, duration (no payloads)
```

Readiness: `GET /api/ready` answers **200** when the forecast table is present and the dated-forecast
digest verifies, **503** otherwise (the body names the failing check). The Mission Overview shows the same record
in its **System readiness** panel (READY / NOT READY, the checks, the twin-state source and policy, the latest
run, schema versions, snapshot age and warnings); it describes the console's artifacts, not any spacecraft. `GET /api/health` stays a
liveness probe. Every response carries an `X-Request-ID` header (a client-supplied one is echoed);
unexpected errors return a generic 500 with that id and no traceback — the traceback is in the
server log under the same id.

Twin-state evidence root (P3-B): `GET /twin-state` (page) and `GET /api/twin-state` report which archive
was selected under the policy (`?policy=prefer_reemitted|reemitted_only|archived_only`), its provenance
(schema, SHA-256 recorded vs computed, transformation digest, record count), streaming record integrity and the
value equivalence with the latest run's catalogue chain. The first request streams the archive once (about
1.5 s); later requests are served from a cache that is invalidated when any candidate file or run table changes.
A fallback to the historical `twin_state/1.0` archive or an explicit archived read is always shown in amber,
never as a green primary. Offline: `python scripts/twin_state_integrity.py [--policy …]` writes the same record
under `outputs/audit/`. Pipeline runs select the archive with `--twin-source-policy` (default `prefer_reemitted`).

Diagnostics bundle (read-only; writes one JSON under `outputs/audit/`):

```bash
python scripts/diagnose_console.py                 # prerequisites, readiness, probes, cache statistics, protected-artifact check
```

Guided demonstration: `/demo` (nav "Guided Demonstration") walks through thirteen stages — launch, overview, the four
demonstration objects with their live ranks and abstentions, orbital intelligence, re-entry, telemetry, conjunction, debris,
decision support, twin state, scenario, pipeline evidence and the mission summary — each linking to the real screen and
stating what is shown, what it means and its limits. Every value on it is read from stored outputs.

Expected first screen: Mission Overview with the System readiness panel, the evidence-boundary note, the **STALE** finding
(the snapshot is dated 2026-10-27; its age is computed on every load), the latest run and its
findings.

## 3. Produce a run to explore (optional)

```bash
python scripts/run_pipeline.py --as-of 2026-10-27 --limit 500      # new directory outputs/pipeline/run_<UTC>/
```

The run reads archives only (about 7 s for all 31,396 objects); it never overwrites an existing
run directory.

## 4. Troubleshooting

| Symptom | Cause / action |
|---|---|
| `check_console_prerequisites.py` exits 1 | a required package or the forecast table is missing; the report names it |
| "No pipeline run is present" | run step 3 or a scenario from `/scenario` |
| Telemetry / debris / risk screen UNAVAILABLE | the optional artifact named on the screen is absent from this checkout |
| Object page shows **NO SUBGROUP EVIDENCE** | `outputs/am_design_stage1/results.json` absent; the interval is still shown, only the X6 cue is not |
| "model version UNAVAILABLE" everywhere | expected: no fitted model is persisted anywhere; see the run page's lineage table |
| `ModuleNotFoundError: tabm` (or kumo, tabicl, statsmodels…) when running *study* scripts | optional backend; the console does not need it; re-running those studies is a separate, approval-gated activity |
| Port in use | `--port 9000` |
| `/api/ready` returns 503 | the body's `checks` names the cause: forecast table absent, dated digest `MISMATCH`/`file_missing`, or no complete run; run `scripts/diagnose_console.py` |
| A page shows "Internal error" with a request id | look the id up in the server log (`--log-json`); the response deliberately carries no traceback |
| Twin State page shows FALLBACK or FINDINGS | the re-emitted archive is absent, fails its digest, is unsupported, or a record is malformed/duplicated; the page lists the reason per candidate. Nothing is repaired; re-run `scripts/twin_state_integrity.py` after restoring the artifact |
| Exported report says "Redacted export" | expected: downloads strip the repository path and hostname; `?redact=false` keeps them. Hashes, commit and run id are never removed |

## 5. What the launch does not do

It does not fetch data, train or run models, regenerate the forecast, or contact any network
service. All numbers shown are archived; their artifact SHA-256, run id, Git commit and
configuration digest are displayed; the model version is shown as unavailable because none is
recorded.
