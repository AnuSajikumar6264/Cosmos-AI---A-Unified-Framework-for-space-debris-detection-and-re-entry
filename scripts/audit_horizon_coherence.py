"""Check whether the saved per-horizon re-entry probabilities form a coherent CDF.

P(decay within 30 d) <= P(within 90 d) <= P(within 1 yr) must hold for every object: the
three columns are evaluations of one cumulative distribution. This script measures each
family of columns in a saved forecast table and writes the result, so the figure quoted as
limitation L17 is traceable to an executed check rather than to prose.

    python scripts/audit_horizon_coherence.py
    python scripts/audit_horizon_coherence.py --as-of 2026-10-27 --out outputs/audit

Exit status is 0 when the measurement completes; a detected violation is a finding reported
in the output, not a crash. Nothing is modified.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

#: Column families to test, and what each represents.
FAMILIES = {
    "p": "twin's reported forecast (per-regime selection)",
    "p_lifetime": "learned lifetime expert, isotonic-calibrated per horizon",
    "p_lifetime_raw": "learned lifetime expert, uncalibrated",
    "p_physics_prior": "physics expert with class area-to-mass priors",
    "p_physics_history": "physics expert with history-conditioned area-to-mass",
}
SUFFIXES = ("30d", "90d", "1yr")


def audit(table: pd.DataFrame) -> dict:
    findings = {}
    for family, description in FAMILIES.items():
        columns = [f"{family}_{suffix}" for suffix in SUFFIXES]
        if not all(column in table.columns for column in columns):
            findings[family] = {"status": "absent", "description": description}
            continue
        present = table[columns].dropna()
        values = present.to_numpy(dtype=float)
        if len(values) == 0:
            findings[family] = {"status": "no_values", "description": description}
            continue
        # Largest decrease between consecutive horizons; positive means a CDF violation.
        drops = np.maximum(values[:, 0] - values[:, 1], values[:, 1] - values[:, 2])
        violating = drops > 0
        findings[family] = {
            "status": "violations_found" if violating.any() else "coherent",
            "description": description,
            "objects_with_values": int(len(values)),
            "violations": int(violating.sum()),
            "violation_fraction": float(violating.mean()),
            "max_drop": float(drops.max()),
            "worst_example": (
                {column: float(value) for column, value in
                 zip(columns, values[int(np.argmax(drops))])}
                if violating.any() else None
            ),
        }
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", default="2026-10-27")
    parser.add_argument("--out", default=None, help="directory for the JSON result")
    args = parser.parse_args(argv)

    relative = f"outputs/twin/as_of_{args.as_of}/forecast_table.csv.gz"
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"forecast table is not present: {relative}")

    table = pd.read_csv(path)
    record = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "as_of": args.as_of,
        "artifact": relative,
        "artifact_sha256": sha256_file(path),
        "rows": int(len(table)),
        "git": git_revision(ROOT),
        "requirement": "P(<=30d) <= P(<=90d) <= P(<=1yr) for every object",
        "families": audit(table),
        "note": ("A violation indicates incoherent per-horizon calibration, not a drag-model "
                 "error. This script measures and reports; it does not modify any artifact."),
    }

    out_dir = Path(args.out) if args.out else ROOT / "outputs" / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / f"horizon_coherence_{args.as_of}.json"
    with open(destination, "w") as stream:
        json.dump(record, stream, indent=2)

    print(f"{relative}  ({record['rows']} rows)")
    for family, finding in record["families"].items():
        if finding["status"] in {"absent", "no_values"}:
            print(f"  {family:20s} {finding['status']}")
            continue
        print(f"  {family:20s} {finding['status']:17s} "
              f"n={finding['objects_with_values']:6d} "
              f"violations={finding['violations']:5d} "
              f"({100 * finding['violation_fraction']:5.2f}%) "
              f"max_drop={finding['max_drop']:.4f}")
    print(f"written: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
