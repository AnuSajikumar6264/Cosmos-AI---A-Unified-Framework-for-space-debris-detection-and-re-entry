"""P0.5 — regenerated AR(8) score caches: large arrays stay out of git, manifest + recipe preserve them."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from cosmos.ai.provenance import ROOT

BASE = ROOT / "outputs/benchmarks/telemetry_esa_adb/track3b_stage2"
MANIFEST = BASE / "SCORE_CACHE_MANIFEST.json"
pytestmark = pytest.mark.skipif(not MANIFEST.is_file(), reason="score cache manifest absent")


def _ignored(path: Path) -> bool:
    return subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", str(path.relative_to(ROOT))]).returncode == 0


def test_manifest_records_every_cache_file_and_verifies():
    from scripts.score_cache_manifest import verify
    ok, problems = verify()
    assert ok, problems
    rec = json.loads(MANIFEST.read_text())
    paths = {f["path"] for f in rec["files"]}
    assert "outputs/benchmarks/telemetry_esa_adb/track3b_stage2/oof_regen/m1_target_ar8/scores_train_oof.npy" in paths
    assert "outputs/benchmarks/telemetry_esa_adb/track3b_stage2/oof_regen/m1_target_ar8/scores_test.npy" in paths
    large = [f for f in rec["files"] if f["large"]]
    assert len(large) == 2 and all(not f["kept_in_git"] for f in large) and all(len(f["sha256"]) == 64 for f in rec["files"])
    assert rec["regeneration"]["archived_sha256_sample_reproduced"] is True and "track3b_stage2_cells.py" in rec["regeneration"]["command"]


def test_ignore_rules_are_narrow():
    assert _ignored(BASE / "oof_regen/m1_target_ar8/scores_test.npy"), "large regenerated cache must stay ignored"
    assert _ignored(BASE / "oof_regen/m1_target_ar8/scores_train_oof.npy")
    assert not _ignored(BASE / "alarms/m1_target_conformal_bh/c0_global.npy"), "small alarm bitmaps are kept"
    assert not _ignored(MANIFEST) and not _ignored(BASE / "m1_target_conformal_bh.json")
    # ordinary pipeline outputs and other generated arrays are untouched by the exception
    assert not _ignored(ROOT / "outputs/pipeline/run_20261106T055638946809Z/decision_ranking.csv")
    assert _ignored(ROOT / "outputs/experiments/x/scores_test.npy")
    assert sum(f.stat().st_size for f in (BASE / "alarms").rglob("*.npy")) < 50 * 1024 * 1024
