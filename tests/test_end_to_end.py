"""Level 3 end-to-end checks of the executable pipeline.

These run ``scripts/run_pipeline.py`` as a subprocess into a temporary directory and inspect
what it wrote: exit status, output schemas, finite values, physically admissible ranges,
timestamp consistency, provenance, reproducibility and refusal to overwrite a run.

They verify that the *software* executes and records itself correctly. They do not establish
that any prediction is scientifically accurate.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from cosmos.ai import adapters
from cosmos.ai.provenance import ROOT

AS_OF = "2026-10-27"
SCRIPT = ROOT / "scripts" / "run_pipeline.py"
SNAPSHOT = ROOT / adapters.TWIN_SNAPSHOT.format(as_of=AS_OF)

pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason=f"missing {SNAPSHOT}")


def _run(out: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--as-of", AS_OF, "--limit", "60",
         "--collision-limit", "25", "--debris-sequence-limit", "2",
         "--health-calibrator", "conformal_bh", "--out", str(out), *extra],
        cwd=str(ROOT), capture_output=True, text=True,
    )


@pytest.fixture(scope="module")
def completed(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("pipeline") / "run_a"
    result = _run(out)
    assert result.returncode == 0, f"pipeline failed:\n{result.stdout}\n{result.stderr}"
    return out


def test_pipeline_exits_zero_and_reports_every_module(completed: Path) -> None:
    manifest = json.loads((completed / "run_manifest.json").read_text())
    assert manifest["successful"] is True
    assert manifest["as_of"] == AS_OF
    assert len(manifest["config_sha256"]) == 64

    expected = {spec.name for spec in adapters.default_modules()}
    assert set(manifest["modules"]) == expected
    for name, record in manifest["modules"].items():
        assert record["status"] == "success", f"{name}: {record['error'] or record['reason']}"
        assert record["provenance"]["config_digest"] == manifest["config_sha256"]
        assert record["provenance"]["as_of"] == AS_OF


def test_outputs_have_the_expected_schemas(completed: Path) -> None:
    ranking = pd.read_csv(completed / "decision_ranking.csv")
    assert {"object_id", "name", "regime", "p_reentry_30d", "mass_kg", "high_consequence",
            "priority_score", "lifetime_evidence"} <= set(ranking.columns)

    reentry = pd.read_csv(completed / "reentry_predictions.csv")
    assert {"object_id", "as_of", "model", "uncertainty_kind", "uncertainty_method"} <= set(reentry.columns)

    collision = pd.read_csv(completed / "collision_risk.csv")
    assert {"event_id", "collision_probability", "interval_lower", "interval_upper"} <= set(collision.columns)


def test_values_are_finite_and_physically_admissible(completed: Path) -> None:
    ranking = pd.read_csv(completed / "decision_ranking.csv")
    assert ranking["p_reentry_30d"].between(0.0, 1.0).all()
    assert ranking["p_reentry_30d"].notna().all()
    assert (ranking["priority_score"] >= 0).all()
    mass = ranking["mass_kg"].dropna()
    assert (mass > 0).all(), "a catalogued mass must be positive"

    reentry = pd.read_csv(completed / "reentry_predictions.csv")
    probability_columns = [c for c in reentry.columns if c.startswith("p_") and c.endswith("d")]
    assert probability_columns
    for column in probability_columns:
        values = reentry[column].dropna()
        assert values.between(0.0, 1.0).all(), f"{column} outside [0, 1]"
    for column in ("days_q05", "days_q50", "days_q95"):
        values = reentry[column].dropna()
        assert (values > 0).all(), f"{column} must be a positive number of days"
    quantiles = reentry[["days_q05", "days_q50", "days_q95"]].dropna()
    assert (quantiles["days_q05"] <= quantiles["days_q50"]).all()
    assert (quantiles["days_q50"] <= quantiles["days_q95"]).all()

    collision = pd.read_csv(completed / "collision_risk.csv")
    assert collision["collision_probability"].between(0.0, 1.0).all()
    assert (collision["interval_lower"] <= collision["interval_upper"]).all()
    # Priority must stay absent from the physical-probability table.
    assert collision["priority_score"].isna().all()


def test_timestamps_are_consistent_with_the_requested_snapshot(completed: Path) -> None:
    reentry = pd.read_csv(completed / "reentry_predictions.csv")
    stamps = pd.to_datetime(reentry["as_of"], utc=True)
    assert (stamps.dt.strftime("%Y-%m-%d") == AS_OF).all()


def test_lifetime_estimates_are_coherent_cdfs(completed: Path) -> None:
    """Rows that survived into the output must be monotone across horizons."""
    lifetime = pd.read_csv(completed / "lifetime_estimates.csv")
    columns = sorted((c for c in lifetime.columns if c.startswith("p_") and c.endswith("d")),
                     key=lambda c: int(c[2:-1]))
    assert len(columns) >= 2
    values = lifetime[columns].to_numpy()
    for earlier, later in zip(range(len(columns) - 1), range(1, len(columns))):
        assert (values[:, earlier] <= values[:, later] + 1e-12).all(), \
            "a non-coherent CDF reached the output"


def test_provenance_digests_match_the_artifacts_on_disk(completed: Path) -> None:
    from cosmos.ai.provenance import sha256_file

    manifest = json.loads((completed / "run_manifest.json").read_text())
    checked = 0
    for record in manifest["modules"].values():
        for relative, digest in record["provenance"]["input_hashes"].items():
            assert sha256_file(ROOT / relative) == digest, f"{relative} digest does not match"
            checked += 1
    assert checked, "no artifact digests were recorded"


def test_repeated_run_reproduces_identical_tables(tmp_path: Path, completed: Path) -> None:
    second = tmp_path / "run_b"
    result = _run(second)
    assert result.returncode == 0, result.stderr

    for name in ("decision_ranking.csv", "reentry_predictions.csv", "lifetime_estimates.csv",
                 "collision_risk.csv", "debris_detections.csv"):
        first_table = pd.read_csv(completed / name)
        second_table = pd.read_csv(second / name)
        pd.testing.assert_frame_equal(first_table, second_table)

    first_manifest = json.loads((completed / "run_manifest.json").read_text())
    second_manifest = json.loads((second / "run_manifest.json").read_text())
    assert first_manifest["config_sha256"] == second_manifest["config_sha256"]


def test_existing_run_directory_is_never_overwritten(completed: Path) -> None:
    result = _run(completed)
    assert result.returncode != 0
    assert "never overwritten" in (result.stdout + result.stderr)


def test_partial_selection_runs_without_imagery_or_telemetry(tmp_path: Path) -> None:
    out = tmp_path / "run_partial"
    result = _run(out, "--select", "decision_priority")
    assert result.returncode == 0, result.stderr

    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["modules"]["decision_priority"]["status"] == "success"
    for name in ("debris", "health", "collision"):
        assert manifest["modules"][name]["status"] == "not_requested"
    assert not (out / "debris_detections.csv").exists()


def test_unavailable_snapshot_fails_without_writing_predictions(tmp_path: Path) -> None:
    out = tmp_path / "run_missing"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--as-of", "1999-01-01", "--out", str(out)],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    assert result.returncode == 1
    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["successful"] is False
    assert manifest["modules"]["catalogue_state"]["status"] == "failed"
    assert "ArtifactUnavailable" in manifest["modules"]["catalogue_state"]["error"]
    # Nothing downstream may invent a prediction from an absent snapshot.
    assert manifest["modules"]["decision_priority"]["status"] == "blocked"
    assert not (out / "reentry_predictions.csv").exists()
    assert not (out / "decision_ranking.csv").exists()
