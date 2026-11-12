"""Reproducible console benchmark: latency, payload size and peak RSS on the real archive (read-only).

    python scripts/benchmark_console.py --label before   # writes outputs/audit/console_benchmark_<label>_<UTC>.json

Same probes, same order, fresh process each time, so two runs are comparable. GET requests only.
"""
from __future__ import annotations

import argparse, json, resource, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--label", default="run"); a = ap.parse_args(argv)
    from fastapi.testclient import TestClient
    from cosmos.product.api import create_app
    from cosmos.product.store import ArtifactStore, TWIN_STATE_REEMITTED
    out: dict = {"label": a.label, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rss_mb_start": rss_mb(), "probes": []}
    app = create_app(ROOT); client = TestClient(app)

    def probe(label, path, params=None, repeat=1):
        for i in range(repeat):
            t0 = time.perf_counter(); r = client.get(path, params=params); dt = (time.perf_counter() - t0) * 1000
            out["probes"].append({"probe": f"{label}{' (warm)' if i else ''}", "path": path, "status": r.status_code,
                                  "ms": round(dt, 1), "kb": round(len(r.content) / 1024, 1), "rss_mb": round(rss_mb(), 0)})
    probe("overview api", "/api/overview", repeat=2)
    probe("overview page", "/", repeat=2)
    probe("datasets api", "/api/datasets")
    probe("search", "/api/objects/search", {"q": "ARIANE", "limit": 60})
    probe("object api 37607", "/api/objects/37607", repeat=2)
    probe("object page 37607", "/objects/37607")
    probe("twin api 23806 (index build)", "/api/objects/23806/twin")
    probe("twin api 25544", "/api/objects/25544/twin")
    probe("runs list api", "/api/runs", repeat=2)
    rid = next(r["run_id"] for r in client.get("/api/runs").json()["runs"] if r["complete"])
    probe("run manifest api", f"/api/runs/{rid}", repeat=2)
    probe("run page", f"/runs/{rid}")
    probe("ranking 25", f"/api/runs/{rid}/ranking", {"limit": 25})
    probe("report json 37607", "/api/reports/object/37607")
    probe("report html 37607", "/reports/object/37607")
    st = ArtifactStore(ROOT)
    t0 = time.perf_counter(); st.list_runs(); out["list_runs_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st.list_runs(); out["list_runs_ms_warm"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st.run_manifest(rid); out["run_manifest_parse_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st.run_manifest(rid); out["run_manifest_parse_ms_warm"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st.repository_provenance(); out["repository_provenance_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st.repository_provenance(); out["repository_provenance_ms_warm"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st.missions(); out["missions_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    t0 = time.perf_counter(); st._twin_line(TWIN_STATE_REEMITTED.format(as_of="2026-10-27"), "37607"); out["twin_lookup_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    out["latest_run"] = rid; out["latest_manifest_bytes"] = (ROOT / "outputs/pipeline" / rid / "run_manifest.json").stat().st_size
    out["rss_mb_peak"] = round(rss_mb(), 0)
    path = ROOT / f"outputs/audit/console_benchmark_{a.label}_{out['at'].replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    for p in out["probes"]:
        print(f"{p['probe']:34s} {p['status']} {p['ms']:8.1f} ms {p['kb']:9.1f} kB  RSS {p['rss_mb']:.0f} MB")
    print({k: v for k, v in out.items() if k.endswith("_ms") or k.endswith("_warm") or k in ("twin_lookup_ms", "latest_manifest_bytes", "rss_mb_peak")})
    print("written", path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
