"""Phase 6 — repeated execution of the twin pipeline is byte-deterministic (2026-11-06).

Two runs over the same saved artifacts into two fresh directories must produce byte-identical
tables; only timestamps and durations in the manifest may differ. Measured on the full 31,396-object
snapshot on 2026-11-06 (7 tables identical); this test repeats it on a bounded run so it stays cheap.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"
pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="snapshot absent")

TIMING_KEYS = {"started_at", "duration_s", "utc"}


def _strip_timing(obj):
    if isinstance(obj, dict):
        return {k: _strip_timing(v) for k, v in obj.items() if k not in TIMING_KEYS}
    if isinstance(obj, list):
        return [_strip_timing(v) for v in obj]
    return obj


def test_two_runs_write_identical_tables_and_manifests_up_to_timing(tmp_path):
    from scripts.run_pipeline import main as run_pipeline_main

    outs = []
    for i in range(2):
        out = tmp_path / f"run{i}"
        rc = run_pipeline_main(["--as-of", "2026-10-27", "--limit", "300", "--collision-limit", "50",
                                "--debris-sequence-limit", "3", "--health-calibrator", "conformal_bh", "--out", str(out)])
        assert rc == 0
        outs.append(out)
    tables = sorted(p.name for p in outs[0].iterdir() if p.suffix == ".csv")
    assert tables, "no tables written"
    assert tables == sorted(p.name for p in outs[1].iterdir() if p.suffix == ".csv")
    for name in tables:
        a, b = (hashlib.sha256((o / name).read_bytes()).hexdigest() for o in outs)
        assert a == b, name
    m0, m1 = (json.loads((o / "run_manifest.json").read_text()) for o in outs)
    assert _strip_timing(m0) == _strip_timing(m1)
    assert m0["config_sha256"] == m1["config_sha256"]
