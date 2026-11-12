"""Phase M: clean-environment reproducibility audit.

Checks whether the published results could actually be regenerated from the declared
requirements in this environment, and which published conclusions depend on components that
cannot be reinstalled.

    python scripts/final_reproducibility_audit.py --out outputs/final_repro

Read-only: installs nothing, modifies nothing.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

REQUIREMENTS = ("requirements.txt", "requirements-ai.txt", "requirements-product.txt")

#: Learner -> python backend module it imports at fit time.
#: Learner -> the module its class body actually imports at fit time. Verified by reading
#: each class in cosmos/ai/lifetime/models.py: `tabm` imports a package named `tabm` (not just
#: torch), and `tabicl` imports both `tabicl` and `sdm.nn.attention`.
LEARNER_BACKENDS = {
    "xgboost": "xgboost", "lightgbm": "lightgbm", "catboost": "catboost",
    "mlp": "torch", "tabm": "tabm", "tabicl": "tabicl", "kumo": "sdm",
}

#: Which published conclusions depend on which learner.
LEARNER_ROLE = {
    "kumo": "SELECTED learner at origin 2011 (its gated fusion and all origin-2011 ablations)",
    "tabicl": "best test performer at origin 2016; member of the pre-specified RECENT pool "
              "and of the Phase G+ robust blends",
    "tabm": "SELECTED learner at origin 2016; member of RECENT and of the robust blends",
    "lightgbm": "reference baseline in both origins' leaderboards",
    "catboost": "reference baseline in both origins' leaderboards",
    "xgboost": "reference baseline in both origins' leaderboards",
    "mlp": "reference baseline; the common learner used by experiment E12",
}

#: Frozen / integrity-critical artifacts.
INTEGRITY = {
    "preregistration_freeze": "research_design/preregistration/freeze.json",
    "dated_forecast_digest": "outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt",
    "g5d_preregistration": "outputs/g5d_origin2006/prereg_freeze.json",
}


def declared_packages(root: Path) -> dict[str, list[str]]:
    out = {}
    for name in REQUIREMENTS:
        path = root / name
        if not path.is_file():
            continue
        packages = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            match = re.match(r"^([A-Za-z0-9_.\-]+)", line)
            if match:
                packages.append(match.group(1).lower())
        out[name] = packages
    return out


def audit_learners(root: Path) -> dict:
    declared = {pkg for packages in declared_packages(root).values() for pkg in packages}
    rows = []
    for learner, backend in LEARNER_BACKENDS.items():
        try:
            module = importlib.import_module(backend)
            importable = True
            version = getattr(module, "__version__", None)
        except Exception as exc:
            importable, version = False, None
            detail = f"{type(exc).__name__}"
        else:
            detail = None
        # A backend counts as declared if its import name or an obvious distribution name is
        # present in a requirements file.
        candidates = {backend, backend.replace("_", "-")}
        if backend == "sdm":
            candidates |= {"structured-data-models", "structured_data_models"}
        is_declared = bool(candidates & declared)
        rows.append({
            "learner": learner, "backend": backend,
            "importable": importable, "version": version,
            "declared_in_requirements": is_declared,
            "import_error": detail,
            "published_role": LEARNER_ROLE.get(learner),
            "reproducible": bool(importable and is_declared),
        })
    return {"learners": rows,
            "n_importable": sum(r["importable"] for r in rows),
            "n_declared": sum(r["declared_in_requirements"] for r in rows),
            "n_reproducible": sum(r["reproducible"] for r in rows),
            "total": len(rows)}


def audit_integrity(root: Path) -> dict:
    out = {}
    freeze = root / INTEGRITY["preregistration_freeze"]
    if freeze.is_file():
        record = json.loads(freeze.read_text())
        changed = [p for p, h in record["sha256"].items()
                   if (root / p).is_file() and sha256_file(root / p) != h]
        missing = [p for p in record["sha256"] if not (root / p).is_file()]
        out["preregistration_freeze"] = {
            "state": "INTACT" if not changed and not missing else "BROKEN",
            "files": len(record["sha256"]), "changed": changed, "missing": missing}
    digest = root / INTEGRITY["dated_forecast_digest"]
    if digest.is_file():
        results = {}
        for line in digest.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) != 2:
                continue
            recorded, name = parts
            target = digest.parent / name
            results[name] = ("verified" if target.is_file()
                             and sha256_file(target) == recorded else "MISMATCH_OR_MISSING")
        out["dated_forecast"] = {"state": ("INTACT" if all(v == "verified" for v in
                                                           results.values()) else "BROKEN"),
                                 "files": results}
    g5d = root / INTEGRITY["g5d_preregistration"]
    if g5d.is_file():
        record = json.loads(g5d.read_text())
        actual = sha256_file(root / record["preregistration"])
        out["g5d_preregistration"] = {
            "state": "INTACT" if actual == record["sha256"] else "BROKEN",
            "frozen_sha256": record["sha256"], "actual_sha256": actual}
    return out


def audit_artifacts(root: Path) -> dict:
    """Digest the artifacts that manuscript numbers are read from."""
    targets = [
        "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled/test_predictions.npz",
        "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled/test_predictions.npz",
        "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled/regression_test.csv",
        "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled/regression_test.csv",
        "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz",
        "outputs/benchmarks/twin_couplings/c2_cloud_survival.csv",
        "outputs/benchmarks/twin_couplings/c3_summary.json",
        "outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz",
        "outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz",
        "outputs/benchmarks/telemetry_esa_adb/results.csv",
    ]
    rows = []
    for relative in targets:
        path = root / relative
        rows.append({"artifact": relative, "present": path.is_file(),
                     "sha256": sha256_file(path) if path.is_file() else None,
                     "bytes": path.stat().st_size if path.is_file() else None})
    return {"artifacts": rows, "present": sum(r["present"] for r in rows),
            "total": len(rows)}


def audit_environment() -> dict:
    record = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }
    for name in ("numpy", "pandas", "scikit-learn", "torch", "xgboost", "matplotlib",
                 "fastapi", "pydantic"):
        module_name = {"scikit-learn": "sklearn"}.get(name, name)
        try:
            module = importlib.import_module(module_name)
            record[name] = getattr(module, "__version__", "unknown")
        except Exception:
            record[name] = None
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/final_repro")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Phase M -- clean-environment reproducibility audit\n")

    learners = audit_learners(root)
    print(f"=== learner backends: {learners['n_importable']}/{learners['total']} importable, "
          f"{learners['n_declared']}/{learners['total']} declared, "
          f"{learners['n_reproducible']}/{learners['total']} reproducible ===")
    print(f"  {'learner':10s} {'backend':10s} {'import':>7s} {'declared':>9s} {'version':>10s}")
    for row in learners["learners"]:
        print(f"  {row['learner']:10s} {row['backend']:10s} "
              f"{str(row['importable']):>7s} {str(row['declared_in_requirements']):>9s} "
              f"{str(row['version'] or '-'):>10s}")
    unreproducible = [r for r in learners["learners"] if not r["reproducible"]]
    if unreproducible:
        print("\n  NOT REPRODUCIBLE from the declared requirements:")
        for row in unreproducible:
            print(f"    {row['learner']:10s} -- {row['published_role']}")

    integrity = audit_integrity(root)
    print("\n=== integrity ===")
    for name, record in integrity.items():
        print(f"  {name:26s} {record['state']}")

    artifacts = audit_artifacts(root)
    print(f"\n=== manuscript source artifacts: {artifacts['present']}/{artifacts['total']} present ===")
    for row in artifacts["artifacts"]:
        mark = "ok " if row["present"] else "ABSENT"
        digest = (row["sha256"] or "")[:12]
        print(f"  {mark} {digest:12s} {row['artifact']}")

    environment = audit_environment()
    print(f"\n=== environment: python {environment['python']} on {environment['platform']} ===")

    verdict = {
        "all_integrity_intact": all(r["state"] == "INTACT" for r in integrity.values()),
        "all_artifacts_present": artifacts["present"] == artifacts["total"],
        "all_learners_reproducible": learners["n_reproducible"] == learners["total"],
    }
    verdict["overall"] = ("PASS" if all(verdict.values())
                          else "PARTIAL" if verdict["all_integrity_intact"]
                          and verdict["all_artifacts_present"] else "FAIL")
    print(f"\n=== verdict: {verdict['overall']} ===")
    for key, value in verdict.items():
        if key != "overall":
            print(f"  {key}: {value}")

    payload = {
        "phase": "M reproducibility audit",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "environment": environment,
        "declared_packages": declared_packages(root),
        "learner_backends": learners,
        "integrity": integrity,
        "artifacts": artifacts,
        "verdict": verdict,
        "interpretation": {
            "scope": "whether published results can be regenerated from declared requirements",
            "not_established": [
                "artifact digests confirm the files are unchanged, not that they are correct",
                "a reproducible environment does not make a scientific conclusion valid",
            ],
        },
    }
    with open(out_dir / "final_reproducibility.json", "w") as stream:
        json.dump(payload, stream, indent=2, default=str)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
