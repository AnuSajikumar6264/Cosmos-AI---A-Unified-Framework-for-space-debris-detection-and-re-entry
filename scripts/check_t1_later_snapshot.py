"""Readiness check for the later-snapshot evaluation of the dated 2026-10-27 forecast.

The twin wrote an immutable forecast at ``as_of`` 2026-10-27 and recorded the SHA-256 of
``twins.jsonl``. Scoring it needs a CelesTrak SATCAT snapshot whose **data date is later
than the forecast's own as-of date** by at least the horizon being scored. This script
reports whether such a snapshot is present. It never downloads one and never fabricates one.

    python scripts/check_t1_later_snapshot.py
    python scripts/check_t1_later_snapshot.py --out outputs/run_phase_d

Exit status is 0 when the check completes. ``ready`` in the output says whether a horizon can
be scored; a horizon with no qualifying snapshot is reported BLOCKED with the data date that
would be required.

Distinction that must not be blurred: the existing **T1** study (``cosmos/ai/twin/prospective.py``)
forecasts from as-of 2026-08-16 and scores against the 2026-10-27 snapshot, and it is
explicitly **not blind**. The check here concerns a *different*, later evaluation of the
2026-10-27 forecast, which would be the first genuinely unseen-outcome test.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

FORECAST_AS_OF = "2026-10-27"
FORECAST_DIR = f"outputs/twin/as_of_{FORECAST_AS_OF}"
DIGEST_FILE = f"{FORECAST_DIR}/FORECAST_SHA256.txt"
FORECAST_TABLE = f"{FORECAST_DIR}/forecast_table.csv.gz"
SNAPSHOT_ROOT = "data/feature2_debris/celestrak/snapshots"
BASE_SNAPSHOT = "data/feature2_debris/celestrak/satcat.csv"

#: Horizons the dated forecast reports, in days (``cosmos.ai.twin.engine.HORIZONS``).
HORIZONS = {"30d": 30.0, "90d": 90.0, "1yr": 365.25}

DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def verify_digest(root: Path) -> dict:
    """Recompute the recorded digest of the immutable forecast."""
    digest_path = root / DIGEST_FILE
    if not digest_path.is_file():
        return {"state": "absent", "detail": f"{DIGEST_FILE} is not present"}
    entries = {}
    for line in digest_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            entries[parts[1]] = parts[0]
    results = {}
    for name, recorded in entries.items():
        target = root / FORECAST_DIR / name
        if not target.is_file():
            results[name] = {"state": "file_missing", "recorded_sha256": recorded}
            continue
        actual = sha256_file(target)
        results[name] = {
            "state": "verified" if actual == recorded else "MISMATCH",
            "recorded_sha256": recorded,
            "actual_sha256": actual,
        }
    overall = ("verified" if results and all(r["state"] == "verified" for r in results.values())
               else "not_verified")
    return {"state": overall, "files": results}


def available_snapshots(root: Path) -> list[dict]:
    """Snapshots on disk with their observed maximum decay date (their effective data date)."""
    found = []
    candidates = []
    base = root / BASE_SNAPSHOT
    if base.is_file():
        candidates.append(("catalogue root", base))
    snapshot_root = root / SNAPSHOT_ROOT
    if snapshot_root.is_dir():
        for child in sorted(snapshot_root.iterdir()):
            if child.is_dir() and DATE_DIR.match(child.name) and (child / "satcat.csv").is_file():
                candidates.append((child.name, child / "satcat.csv"))

    for label, path in candidates:
        frame = pd.read_csv(path, usecols=["NORAD_CAT_ID", "DECAY_DATE"])
        decay = pd.to_datetime(frame["DECAY_DATE"], errors="coerce")
        found.append({
            "label": label,
            "path": str(path.relative_to(root)),
            "rows": int(len(frame)),
            "decayed_rows": int(decay.notna().sum()),
            # The latest decay date present is the snapshot's effective outcome coverage.
            "max_decay_date": decay.max().date().isoformat() if decay.notna().any() else None,
        })
    return found


def assess(root: Path) -> dict:
    as_of = pd.Timestamp(FORECAST_AS_OF)
    snapshots = available_snapshots(root)
    coverage = [s for s in snapshots if s["max_decay_date"]]
    latest = max((s["max_decay_date"] for s in coverage), default=None)

    population = None
    table_path = root / FORECAST_TABLE
    if table_path.is_file():
        table = pd.read_csv(table_path, usecols=["norad", "type1", "regime", "p_30d"])
        population = {
            "objects": int(len(table)),
            "unique_norad": int(table["norad"].nunique()),
            "norad_is_unique": bool(table["norad"].is_unique),
            "by_regime": table["regime"].value_counts().to_dict(),
            "by_class": table["type1"].value_counts().to_dict(),
            "objects_with_p30d": int(table["p_30d"].notna().sum()),
        }

    horizons = {}
    for name, days in HORIZONS.items():
        required = (as_of + pd.Timedelta(days=days)).date().isoformat()
        qualifying = [s for s in coverage if s["max_decay_date"] >= required]
        horizons[name] = {
            "horizon_days": days,
            "outcome_window": [FORECAST_AS_OF, required],
            "required_snapshot_data_date_at_or_after": required,
            "qualifying_snapshots": [s["label"] for s in qualifying],
            "ready": bool(qualifying),
            "status": "READY" if qualifying else "BLOCKED",
        }

    days_available = None
    if latest is not None:
        days_available = (pd.Timestamp(latest) - as_of).days

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "forecast_as_of": FORECAST_AS_OF,
        "git": git_revision(root),
        "digest_verification": verify_digest(root),
        "forecast_population": population,
        "available_snapshots": snapshots,
        "latest_outcome_coverage": latest,
        "outcome_days_available_after_forecast": days_available,
        "horizons": horizons,
        "overall_status": ("READY" if any(h["ready"] for h in horizons.values()) else "BLOCKED"),
        "required_to_unblock": {
            "artifact": "CelesTrak SATCAT snapshot (satcat.csv) placed in "
                        f"{SNAPSHOT_ROOT}/<YYYY-MM-DD>/",
            "earliest_useful_data_date": horizons["30d"]["required_snapshot_data_date_at_or_after"],
            "fields": ["NORAD_CAT_ID", "DECAY_DATE"],
            "note": "acquisition is a network action and requires explicit authorisation; "
                    "this script does not download anything",
        },
        "protocol_requirements": [
            "score the hashed forecast exactly as written; re-verify the digest before scoring",
            "censor objects with no decay by the snapshot data date at that date, not at the "
            "horizon, when the snapshot is younger than the horizon",
            "match objects by NORAD_CAT_ID only; do not re-derive the population from the "
            "later snapshot, which would admit objects launched after the forecast",
            "treat a decay date at or before the forecast as-of date as a late report and "
            "exclude it, as T1 and C3 already do",
            "fix the metric set and the censoring rule before inspecting any outcome",
            "operator-controlled payloads carry a base-rate forecast, not a drag forecast; "
            "report them separately from uncontrolled objects",
        ],
        "not_established": [
            "this check does not score anything and is not evidence of forecast accuracy",
            "the existing T1 study (as-of 2026-08-16) is not blind and is a separate study",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default=None, help="directory for the JSON report")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = assess(root)

    print(f"forecast as-of           : {report['forecast_as_of']}")
    print(f"digest verification      : {report['digest_verification']['state']}")
    print(f"latest outcome coverage  : {report['latest_outcome_coverage']}")
    print(f"outcome days available   : {report['outcome_days_available_after_forecast']}")
    if report["forecast_population"]:
        print(f"forecast population      : {report['forecast_population']['objects']} objects")
    print("snapshots on disk:")
    for snapshot in report["available_snapshots"]:
        print(f"  {snapshot['label']:16s} max_decay={snapshot['max_decay_date']} "
              f"rows={snapshot['rows']}")
    print("horizons:")
    for name, record in report["horizons"].items():
        print(f"  {name:5s} {record['status']:8s} needs a snapshot dated >= "
              f"{record['required_snapshot_data_date_at_or_after']}")
    print(f"overall                  : {report['overall_status']}")

    if args.out:
        destination = Path(args.out)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / "t1_later_snapshot_readiness.json"
        with open(target, "w") as stream:
            json.dump(report, stream, indent=2, default=str)
        print(f"written: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
