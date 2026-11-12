"""Cold-start profile of the Mission Intelligence Console (P3-B performance investigation, 2026-11-08).

    python scripts/profile_console_cold.py [--runs 5] [--label L]

Each run is a FRESH Python process (``--child``) so that nothing is warm: it times, in the order the overview
page needs them, the import of the application, app construction, the git subprocess
(``repository_provenance``), the run listing with manifest fingerprinting (``list_runs``), the first
prospective-status assessment, the catalogue load, the latest-manifest parse, the telemetry metadata
(``missions``), the P3-B twin-state selection, then the first and second GET / and GET /api/overview, and
records RSS after every step plus the top allocation sites (tracemalloc) retained after rendering. The parent
aggregates the runs (median / min / max) into ``outputs/audit/console_cold_profile_<label>_<UTC>.json``.

Repeatable by construction: same machine, same checkout, fresh process per run, no warm cache. The numbers
are for this environment only; the report records the environment next to them.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rss_mb() -> float:
    with open("/proc/self/statm") as fh:
        return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576


def child(trace: bool = False) -> int:
    """One fresh-process measurement. ``trace`` adds tracemalloc for allocation attribution ONLY — it slows every
    step several-fold and inflates RSS, so traced runs are reported separately and never used for timings."""
    steps: list[dict] = []
    t_all = time.perf_counter()

    def step(name, fn):
        r0 = rss_mb(); t0 = time.perf_counter()
        value = fn()
        steps.append({"step": name, "ms": round((time.perf_counter() - t0) * 1000, 1), "rss_mb_after": round(rss_mb(), 1),
                      "rss_delta_mb": round(rss_mb() - r0, 1)})
        return value

    if trace:
        tracemalloc.start(5)
    api = step("import cosmos.product.api (pandas, numpy, fastapi, jinja)", lambda: __import__("cosmos.product.api", fromlist=["create_app"]))
    app = step("create_app", lambda: api.create_app(ROOT))
    st = app.state.store
    step("repository_provenance (git subprocess + digest check)", st.repository_provenance)
    step("list_runs (fingerprint + parse every manifest)", st.list_runs)
    step("prospective_status (first assessment)", st.prospective_status)
    step("catalogue (forecast_table.csv.gz load)", st.catalogue)
    step("run_manifest(latest) parse", lambda: st.run_manifest(st.latest_run_id()))
    step("missions (telemetry metadata, header reads)", st.missions)
    step("twin_selection (P3-B: candidate digest + peek)", st.twin_selection)
    from fastapi.testclient import TestClient
    c = TestClient(app)
    step("GET / (overview page, remaining cold work)", lambda: c.get("/"))
    retained, traced_mb = None, None
    if trace:
        snap = tracemalloc.take_snapshot()
        top = snap.statistics("filename")[:8]
        retained = [{"file": str(s.traceback[0].filename).replace(str(ROOT) + "/", ""), "mb": round(s.size / 1048576, 1)} for s in top]
        traced_mb = round(tracemalloc.get_traced_memory()[0] / 1048576, 1)
        tracemalloc.stop()
    step("GET / (warm)", lambda: c.get("/"))
    step("GET /api/overview (warm)", lambda: c.get("/api/overview"))
    step("GET /api/twin-state (P3-B, first: stream archive + compare)", lambda: c.get("/api/twin-state"))
    step("GET /objects/37607 (first)", lambda: c.get("/objects/37607"))
    step("GET /objects/37607 (warm)", lambda: c.get("/objects/37607"))
    import resource
    print(json.dumps({"steps": steps, "total_ms": round((time.perf_counter() - t_all) * 1000, 1), "rss_mb_end": round(rss_mb(), 1),
                      "rss_mb_peak": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "traced": trace,
                      "python_traced_mb_after_overview": traced_mb, "top_allocations_after_overview": retained}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=5); ap.add_argument("--label", default="profile")
    ap.add_argument("--child", action="store_true"); ap.add_argument("--trace", action="store_true")
    a = ap.parse_args(argv)
    if a.child:
        return child(trace=a.trace)
    runs = []
    for i in range(a.runs):
        res = subprocess.run([sys.executable, __file__, "--child"], cwd=ROOT, capture_output=True, text=True, check=True)
        runs.append(json.loads([l for l in res.stdout.splitlines() if l.startswith("{")][-1]))
    traced = subprocess.run([sys.executable, __file__, "--child", "--trace"], cwd=ROOT, capture_output=True, text=True, check=True)
    traced_run = json.loads([l for l in traced.stdout.splitlines() if l.startswith("{")][-1])
    names = [s["step"] for s in runs[0]["steps"]]
    agg = []
    for k, name in enumerate(names):
        ms = [r["steps"][k]["ms"] for r in runs]; rss = [r["steps"][k]["rss_mb_after"] for r in runs]; d = [r["steps"][k]["rss_delta_mb"] for r in runs]
        agg.append({"step": name, "ms_median": round(statistics.median(ms), 1), "ms_min": min(ms), "ms_max": max(ms),
                    "rss_after_median_mb": round(statistics.median(rss), 1), "rss_delta_median_mb": round(statistics.median(d), 1)})
    out = {"label": a.label, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "runs": a.runs,
           "environment": {"python": platform.python_version(), "platform": platform.platform(), "cpu_count": os.cpu_count(),
                           "pandas": __import__("pandas").__version__, "numpy": __import__("numpy").__version__},
           "method": ("fresh subprocess per run, uninstrumented; perf_counter per step; RSS from /proc/self/statm; peak RSS from "
                      "getrusage; ONE separate tracemalloc-instrumented run gives allocation attribution only (its timings are not used)"),
           "steps": agg, "total_ms_median": round(statistics.median(r["total_ms"] for r in runs), 1),
           "rss_mb_end_median": round(statistics.median(r["rss_mb_end"] for r in runs), 1),
           "rss_mb_peak_median": round(statistics.median(r["rss_mb_peak"] for r in runs), 1),
           "traced_run": {"python_traced_mb_after_overview": traced_run["python_traced_mb_after_overview"],
                          "top_allocations_after_overview": traced_run["top_allocations_after_overview"],
                          "note": "instrumented run: slower and larger than the uninstrumented runs by construction"},
           "raw_runs": runs}
    path = ROOT / f"outputs/audit/console_cold_profile_{a.label}_{out['at'].replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{'step':68s} {'median ms':>10s} {'min':>8s} {'max':>8s} {'RSS MB':>8s} {'ΔRSS':>6s}")
    for s in agg:
        print(f"{s['step'][:68]:68s} {s['ms_median']:10.1f} {s['ms_min']:8.1f} {s['ms_max']:8.1f} {s['rss_after_median_mb']:8.1f} {s['rss_delta_median_mb']:6.1f}")
    print("total median ms", out["total_ms_median"], "| RSS end median MB", out["rss_mb_end_median"], "| RSS peak median MB", out["rss_mb_peak_median"])
    print("traced run (attribution only): python traced MB after overview", out["traced_run"]["python_traced_mb_after_overview"],
          "| top:", json.dumps(out["traced_run"]["top_allocations_after_overview"]))
    print("written", path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
