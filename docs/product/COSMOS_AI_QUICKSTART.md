# COSMOS-AI — Quick start (release candidate `v1.0-demonstration-2026-11-08`)

Written for: anyone who has to start COSMOS-AI and run its demonstration in ten minutes. Every command below was executed on
2026-11-08 against release commit B (`633ad862`). The complete manual is
[`COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md`](COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md); the examiner's walk-through is
[`EVALUATOR_GUIDE.md`](EVALUATOR_GUIDE.md).

The console is a **read-only evidence viewer** over archived research outputs and one dated catalogue snapshot (2026-10-27).
It runs no model at request time and connects to no live source. Nothing it shows is real-time.

## 1. Enter the project

```bash
cd /data2/anupa/Final_Year_Project
```

## 2. Activate the environment

```bash
source .venv/bin/activate          # Python 3.12.16; fastapi 0.162, uvicorn 0.54, jinja2 3.1.6, pandas 3.1, numpy 2.3
python -V                          # Python 3.12.16
```

Fresh machine instead of this one: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
-r requirements-ai.txt -r requirements-product.txt`, then `git lfs pull` (see the complete guide §4–§5).

## 3. Verify prerequisites (read-only, exit code 0 = launchable)

```bash
python scripts/check_console_prerequisites.py          # add --json for the machine-readable report
```

On a fresh clone also run **one** pipeline run so that object priorities and the run explorer have data (≈ 3–9 s; writes a new
directory under `outputs/pipeline/`, never touches an existing one):

```bash
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh
```

## 4. Start the application (one process)

```bash
python scripts/serve_console.py                        # http://127.0.0.1:8070/   (API docs: /docs)
```

The server answers `GET /api/ready` with HTTP 200 about two seconds after start. Other ports: `--port 9000`. The default
host is loopback; there is no authentication, so use `--host 0.0.0.0` only on a trusted network.

```bash
curl -s http://127.0.0.1:8070/api/ready | head -c 300      # {"ready": true, ...}
```

## 5. Open the demonstration

Open <http://127.0.0.1:8070/demo>. The page lists the capability map (implemented / benchmark-only / unavailable / blocked)
and the thirteen stages with live values read from the archive.

## 6. Run the main demonstration (13 stages, 15–20 minutes)

Follow [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) stage by stage. The four objects and what each shows:

| NORAD | Object | Shows |
|---|---|---|
| 37607 | ARIANE 5 R/B | p(30 d) = 1.0, re-entry quantiles at 10 days (zero-width, labelled), lifetime median 27.5 d crossing the horizon, priority rank 2 of 31,396 |
| 23806 | TITAN 34B DEB | lifetime abstention for a non-coherent record (L17, 123 such records), p(30 d) = 0.72 with a Monte-Carlo spread |
| 25544 | ISS (ZARYA) | operator-controlled: re-entry abstention with the payload base rate 0.0053, no quantiles, lifetime unavailable |
| 12 | VANGUARD R/B | quantiles censored at the 1826.25-day cap ("not within 1826.25 days"), lifetime entirely after the horizon |

Routes in order: `/` → `/objects?q=37607` → `/objects/37607` → `/objects/23806` → `/objects/25544` → `/objects/12` →
`/telemetry` → `/risk` → `/debris` → `/objects/37607` (Decision priority) → `/twin-state` and `/twin-state?policy=archived_only`
→ `/scenario` (preset "Fast decision subset", ≈ 3–5 s, creates a new run) → `/runs` → `/compare?a=<latest>&b=run_20261108T083402Z`
→ `/reports/object/37607` → `/demo` stage 13.

Automated equivalents, from a fresh process:

```bash
python scripts/rehearse_demo.py --label quickstart                    # all 13 stages, ≈ 11 s, record under outputs/audit/
python -m pytest tests/test_demo_workflow.py tests/test_e2e_demo_journey.py -q   # 29 passed in ≈ 14 s
```

## 7. Stop the application

Press `Ctrl+C` in the terminal running the server (uvicorn stops cleanly on SIGTERM/SIGINT), or from another terminal:

```bash
pkill -f "scripts/serve_console.py"
```

Nothing needs cleaning up: the server writes only JSON-lines logs to stdout (`--log-json`) and, when you run a scenario, one
new `outputs/pipeline/run_<UTC>/` directory.

## Where to go next

- Complete manual (setup, datasets, models, every module, API, outputs, tests, troubleshooting): [`COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md`](COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md)
- Examiner's guide to screens, objects, results and limitations: [`EVALUATOR_GUIDE.md`](EVALUATOR_GUIDE.md)
- Launch details, readiness, Git LFS prerequisite, troubleshooting: [`CONSOLE_LAUNCH.md`](CONSOLE_LAUNCH.md)
- Limitations register: [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md)
