"""Rehearse the thirteen-stage guided demonstration in a FRESH process and record per-stage latency (Phase C.3).

    python scripts/rehearse_demo.py [--label L]

Walks the stages of /demo through the application exactly as an evaluator would click them (the scenario stage is
executed on a temporary copy root so the repository gains no run directory), records status, latency and the key facts
seen, and writes outputs/audit/demo_rehearsal_<label>_<UTC>.json. Read-only against the repository.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rss_mb() -> float:
    with open("/proc/self/statm") as fh:
        return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--label", default="rehearsal"); a = ap.parse_args(argv)
    t_import = time.perf_counter()
    from fastapi.testclient import TestClient
    from cosmos.product.api import create_app
    import_ms = round((time.perf_counter() - t_import) * 1000, 1)
    c = TestClient(create_app(ROOT), raise_server_exceptions=False)
    stages: list[dict] = []

    def stage(n, title, calls):
        t0 = time.perf_counter(); facts = {}; ok = True
        for name, path in calls:
            r = c.get(path)
            ok &= r.status_code == 200
            facts[name] = {"status": r.status_code, "kb": round(len(r.content) / 1024, 1)}
        stages.append({"stage": n, "title": title, "ok": ok, "ms": round((time.perf_counter() - t0) * 1000, 1),
                       "rss_mb": round(rss_mb(), 1), "calls": facts})

    stage(1, "Launch and readiness", [("health", "/api/health"), ("ready", "/api/ready")])
    stage(2, "System overview", [("overview page", "/"), ("overview api", "/api/overview")])
    stage(3, "Satellite selection", [("search api", "/api/objects/search?q=37607"), ("search page", "/objects?q=37607"), ("demo page", "/demo")])
    stage(4, "Orbital intelligence", [(f"object {n}", f"/objects/{n}") for n in (37607, 23806, 12)])
    stage(5, "Re-entry prediction", [("object 25544", "/objects/25544"), ("object api 25544", "/api/objects/25544")])
    stage(6, "Telemetry and health semantics", [("telemetry", "/telemetry"), ("channel", "/telemetry/1/channel_1")])
    stage(7, "Collision and conjunction", [("risk", "/risk"), ("risk api", "/api/risk/collision")])
    stage(8, "Debris and imagery", [("debris", "/debris"), ("sequence", "/debris/1"), ("frame png", "/api/debris/1/frame/1.png")])
    stage(9, "Decision support", [("object 37607 api", "/api/objects/37607"), ("ranking", f"/api/runs/{c.get('/api/ready').json()['latest_run']}/ranking?limit=25")])
    stage(10, "Digital twin and provenance", [("twin-state", "/twin-state"), ("twin-state archived", "/twin-state?policy=archived_only"), ("object twin", "/api/objects/37607/twin")])
    # stage 11: scenario on a temporary copy root (the repository's run directory is never touched)
    tmp = Path(tempfile.mkdtemp(prefix="cosmos_rehearsal_"))
    try:
        (tmp / "outputs/twin").mkdir(parents=True)
        for rel in ("outputs/twin/as_of_2026-10-27", "outputs/twin/as_of_2026-10-27_reemitted_v1"):
            os.symlink(ROOT / rel, tmp / rel)
        (tmp / "outputs/pipeline").mkdir()
        fc = TestClient(create_app(tmp), raise_server_exceptions=False)
        t0 = time.perf_counter()
        r = fc.post("/api/scenario", json={"as_of": "2026-10-27", "limit": 500, "collision_limit": 200, "debris_sequence_limit": 5,
                                           "health_calibrator": "conformal_bh"})
        body = r.json() if r.status_code == 200 else {}
        stages.append({"stage": 11, "title": "Scenario analysis (fast preset, temporary root)", "ok": r.status_code == 200 and body.get("successful") is True,
                       "ms": round((time.perf_counter() - t0) * 1000, 1), "rss_mb": round(rss_mb(), 1),
                       "calls": {"scenario": {"status": r.status_code, "run_id": body.get("run_id"), "modules": {k: v.get("status") for k, v in ((body.get("manifest") or {}).get("modules") or {}).items()}}}})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rid = c.get("/api/ready").json()["latest_run"]
    stage(12, "Pipeline and research evidence", [("runs", "/runs"), ("run page", f"/runs/{rid}"), ("manifest api", f"/api/runs/{rid}"),
                                                  ("compare", f"/compare?a={rid}&b=run_20261108T083402Z"), ("report download", "/reports/object/37607/download")])
    stage(13, "Final mission summary", [("demo page", "/demo#stage-13")])
    out = {"label": a.label, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "import_ms": import_ms,
           "all_ok": all(s["ok"] for s in stages), "total_ms": round(sum(s["ms"] for s in stages), 1), "rss_mb_end": round(rss_mb(), 1), "stages": stages}
    path = ROOT / f"outputs/audit/demo_rehearsal_{a.label}_{out['at'].replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{'stage':6s} {'ok':3s} {'ms':>9s} {'RSS MB':>7s}  title")
    for s in stages:
        print(f"{s['stage']:6d} {'yes' if s['ok'] else 'NO ':3s} {s['ms']:9.1f} {s['rss_mb']:7.1f}  {s['title']}")
    print("import ms", import_ms, "| total ms", out["total_ms"], "| all ok", out["all_ok"], "| written", path.relative_to(ROOT))
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
