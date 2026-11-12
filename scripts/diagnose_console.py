"""Diagnostics bundle for the Mission Intelligence Console (P3-A3). Read-only; writes one JSON file.

    python scripts/diagnose_console.py            # -> outputs/audit/console_diagnostics_<UTC>.json

Bundles: prerequisite check, readiness, protected-artifact verification summary, cache statistics, and a
handful of timed probes. Contains no payload values, no credentials; the hostname is recorded as a hash.
"""
from __future__ import annotations

import hashlib, json, socket, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from fastapi.testclient import TestClient
    from scripts.check_console_prerequisites import collect
    from cosmos.product.api import create_app
    out: dict = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "host_sha256_prefix": hashlib.sha256(socket.gethostname().encode()).hexdigest()[:12],
                 "prerequisites": collect(ROOT)}
    app = create_app(ROOT); client = TestClient(app, raise_server_exceptions=False)
    probes = {}
    for path in ("/api/ready", "/api/health", "/api/overview", "/api/objects/37607", "/api/runs"):
        t0 = time.perf_counter(); r = client.get(path)
        probes[path] = {"status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000, 1), "kb": round(len(r.content) / 1024, 1)}
    out["probes"] = probes
    out["ready"] = client.get("/api/ready").json()
    out["cache_stats"] = app.state.store.cache_stats()
    try:
        from scripts.verify_protected_artifacts import main as verify_main   # writes its own record
        out["protected_artifacts_exit_code"] = verify_main(["--label", "diagnose"])
    except SystemExit as exc:
        out["protected_artifacts_exit_code"] = int(exc.code or 0)
    path = ROOT / f"outputs/audit/console_diagnostics_{out['at'].replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({"ready": out["ready"]["ready"], "probes": probes, "protected_exit": out["protected_artifacts_exit_code"]}, indent=None))
    print("written", path.relative_to(ROOT))
    return 0 if out["ready"]["ready"] and out["protected_artifacts_exit_code"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
