"""P3-B acceptance 13: a full pipeline run with the twin-state modules writes the seven catalogue-chain and
benchmark tables byte-identical to the approved demonstration run, plus the new twin_equivalence.csv."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from cosmos.ai.provenance import ROOT
from cosmos.ai.schema import validate_run_manifest

HIST = ROOT / "outputs/pipeline/run_20261108T083402Z"
TABLES = ("collision_risk.csv", "debris_detections.csv", "decision_ranking.csv", "health_benchmark_arms.csv",
          "lifetime_estimates.csv", "lifetime_noncoherent_horizons.csv", "reentry_predictions.csv")


@pytest.mark.skipif(not (HIST / "run_manifest.json").is_file(), reason="demonstration run absent")
def test_full_run_with_twin_modules_reproduces_the_seven_tables_byte_for_byte(tmp_path):
    out = tmp_path / "run"
    res = subprocess.run([sys.executable, "scripts/run_pipeline.py", "--as-of", "2026-10-27", "--health-calibrator", "conformal_bh",
                          "--out", str(out)], cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert res.returncode == 0, res.stderr[-2000:]
    for name in TABLES:
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == hashlib.sha256((HIST / name).read_bytes()).hexdigest(), name
    man = json.loads((out / "run_manifest.json").read_text())
    assert validate_run_manifest(man) == "1.2" and (out / "run_manifest.json").stat().st_size < 100_000
    assert {k: v["status"] for k, v in man["modules"].items()} == {m: "success" for m in man["modules"]}
    tw = man["modules"]["twin_state"]["outputs"]
    assert tw["source"] == "reemitted" and tw["digest_state"] == "verified" and tw["record_index"] == {"count": 31396}
    assert tw["artifact_sha256"] == "6bb4871f7dedfcf1fb2bef154d097aa382f11c852d0c226a20757638fcf09c84"
    eq = man["modules"]["twin_equivalence"]["outputs"]
    assert eq["records_compared"] == 31396 and eq["records_equal"] == 31396 and eq["records_different"] == 0 and eq["equivalent"] is True
    assert "twin_equivalence.csv" in man["tables_written"] and (out / "twin_equivalence.csv").is_file()
    hist = json.loads((HIST / "run_manifest.json").read_text())
    assert man["modules"]["decision_priority"]["outputs"]["priority_rule"] == hist["modules"]["decision_priority"]["outputs"]["priority_rule"]
