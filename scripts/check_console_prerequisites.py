"""Check what the Mission Intelligence Console needs before it is launched. Read-only.

    python scripts/check_console_prerequisites.py            # human-readable report, exit 0 if launchable
    python scripts/check_console_prerequisites.py --json     # machine-readable

Required  = without it the console cannot start or shows no catalogue: Python >= 3.11, the packages
            fastapi, uvicorn, jinja2, pandas, numpy, and the dated forecast table with its digest file.
Optional  = a screen degrades to an explicit "unavailable" state without it: prepared telemetry arrays,
            SpotGEO frames, conjunction predictions, ESA-ADB arm table, a completed pipeline run, the X6
            subgroup-coverage evidence.
Backends  = never needed to serve the console (it runs no model): listed for transparency only.
Nothing is installed or modified by this script.
"""
from __future__ import annotations

import argparse, importlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED_PACKAGES = ("fastapi", "uvicorn", "jinja2", "pandas", "numpy")
OPTIONAL_BACKENDS = ("torch", "xgboost", "sklearn", "scipy", "statsmodels", "lightgbm", "catboost", "tabm", "tabicl", "kumo", "pymsis")
LAUNCH = "python scripts/serve_console.py            # default http://127.0.0.1:8070/  (API docs at /docs)"


def _importable(name: str) -> dict:
    try:
        mod = importlib.import_module(name)
        return {"present": True, "version": getattr(mod, "__version__", None)}
    except Exception as exc:  # ModuleNotFoundError or a broken optional backend
        return {"present": False, "error": exc.__class__.__name__}


def collect(root: Path = ROOT) -> dict:
    from cosmos.product import store as S
    py = sys.version_info
    req_art = {
        "forecast table": root / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF),
        "forecast digest file": root / S.FORECAST_DIGEST,
    }
    opt_art = {
        "prepared telemetry (mission1.npz)": root / S.TELEMETRY_DIR / "mission1.npz",
        "SpotGEO test frames": root / S.SPOTGEO_IMAGES / "test",
        "SpotGEO saved detections": root / S.SPOTGEO_SUBMISSION,
        "conjunction predictions": root / S.CONJUNCTION_PREDICTIONS,
        "ESA-ADB arm table": root / S.TELEMETRY_RESULTS,
        "X6 subgroup-coverage evidence": root / S.AM_DESIGN_STAGE1,
        "at least one pipeline run": root / S.PIPELINE_RUNS,
    }
    def present(p: Path) -> bool:
        return p.is_dir() and any(p.iterdir()) if p.suffix == "" else p.is_file()
    report = {
        "python": {"version": f"{py.major}.{py.minor}.{py.micro}", "ok": (py.major, py.minor) >= (3, 11)},
        "required_packages": {n: _importable(n) for n in REQUIRED_PACKAGES},
        "required_artifacts": {k: {"path": str(p.relative_to(root)), "present": present(p)} for k, p in req_art.items()},
        "optional_artifacts": {k: {"path": str(p.relative_to(root)), "present": present(p),
                                   "if_missing": "the corresponding screen reports UNAVAILABLE with the reason"} for k, p in opt_art.items()},
        "optional_backends": {n: {**_importable(n), "needed_to_serve_console": False} for n in OPTIONAL_BACKENDS},
        "launch_command": LAUNCH,
        "expected_url": "http://127.0.0.1:8070/",
        "no_live_sources": "the console serves archived artifacts and a dated snapshot only; nothing is real-time",
    }
    report["launchable"] = (report["python"]["ok"] and all(v["present"] for v in report["required_packages"].values())
                            and all(v["present"] for v in report["required_artifacts"].values()))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = collect()
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"Python {r['python']['version']}: {'ok' if r['python']['ok'] else 'TOO OLD (need >= 3.11)'}")
        print("required packages: " + ", ".join(f"{k} {'ok' if v['present'] else 'MISSING'}" for k, v in r["required_packages"].items()))
        for k, v in r["required_artifacts"].items():
            print(f"required artifact  {'ok     ' if v['present'] else 'MISSING'} {k}: {v['path']}")
        for k, v in r["optional_artifacts"].items():
            print(f"optional artifact  {'ok     ' if v['present'] else 'absent '} {k}: {v['path']}")
        print("optional backends (not needed to serve): " + ", ".join(f"{k} {'ok' if v['present'] else 'absent'}" for k, v in r["optional_backends"].items()))
        print(f"\nlaunchable: {r['launchable']}\n  {r['launch_command']}\n  {r['no_live_sources']}")
    return 0 if r["launchable"] else 1


if __name__ == "__main__":
    sys.exit(main())
