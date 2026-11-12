"""Registry artifact audit reports missing paths without changing model cards."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.audit_horizon_coherence import audit as audit_horizons
from scripts.audit_model_artifacts import audit_model_cards


def test_artifact_audit_reports_present_and_missing_files_read_only(tmp_path: Path) -> None:
    registry = tmp_path / "outputs/registry/model_cards.json"
    registry.parent.mkdir(parents=True)
    evidence = tmp_path / "outputs/benchmark.csv"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("metric\n1\n")
    card_data = [
        {"name": "present", "status": "baseline", "evidence": "outputs/benchmark.csv",
         "checkpoint": None},
        {"name": "missing", "status": "baseline", "evidence": "outputs/missing.csv",
         "checkpoint": "/outside/missing.pt"},
    ]
    registry.write_text(json.dumps(card_data))

    report = audit_model_cards(tmp_path)

    assert report["summary"]["cards"] == 2
    assert report["summary"]["missing_evidence"] == 1
    assert report["summary"]["missing_checkpoint"] == 1
    assert report["summary"]["checkpoint_not_recorded"] == 1
    assert report["models"][0]["evidence_exists"] is True
    assert report["models"][1]["checkpoint_exists"] is False
    # The audit must not rewrite the registry it reads.
    assert json.loads(registry.read_text()) == card_data


def test_audit_separates_foreign_workspace_paths_from_missing_files(tmp_path: Path) -> None:
    """L13: a path under another workspace is not the same finding as a missing local file."""
    registry = tmp_path / "outputs/registry/model_cards.json"
    registry.parent.mkdir(parents=True)
    # The local equivalents of a foreign-rooted evidence path and run directory.
    evidence = tmp_path / "outputs/benchmarks/telemetry_opssat/summary_official.csv"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("model,f1_mean\nhybrid,0.9\n")
    run_dir = tmp_path / "outputs/experiments/20261024-084444_opssat_hybrid_official_f100_s0"
    run_dir.mkdir(parents=True)
    (run_dir / "metrics.json").write_text("{}")

    foreign = "/data/anupa/COSMOS_work/Final_Project"
    registry.write_text(json.dumps([
        {"name": "opssat_hybrid", "status": "validated-real",
         "evidence": f"{foreign}/outputs/benchmarks/telemetry_opssat/summary_official.csv",
         "checkpoint": f"{foreign}/outputs/experiments/"
                       "20261024-084444_opssat_hybrid_official_f100_s0/checkpoints/best.pt"},
        {"name": "inside_but_absent", "status": "baseline",
         "evidence": "outputs/benchmarks/nope.csv",
         "checkpoint": "outputs/experiments/absent/checkpoints/best.pt"},
        {"name": "no_weights_by_design", "status": "baseline",
         "evidence": "outputs/benchmarks/telemetry_opssat/summary_official.csv",
         "checkpoint": None},
    ]))

    report = audit_model_cards(tmp_path)
    models = {model["name"]: model for model in report["models"]}

    foreign_card = models["opssat_hybrid"]
    assert foreign_card["checkpoint_state"] == "foreign_workspace"
    assert foreign_card["checkpoint_inside_workspace"] is False
    # The leading "/data" must not be mistaken for the repository's own data/ directory.
    relative = foreign_card["evidence_relative_equivalent"]
    assert relative["relative_suffix"] == "outputs/benchmarks/telemetry_opssat/summary_official.csv"
    assert relative["exists_in_workspace"] is True
    # The run exists locally, but the weights do not.
    local = foreign_card["local_equivalent"]
    assert local["local_run_dir"].endswith("20261024-084444_opssat_hybrid_official_f100_s0")
    assert local["has_checkpoint_dir"] is False
    assert "metrics.json" in local["records"]

    assert models["inside_but_absent"]["checkpoint_state"] == "missing_in_workspace"
    assert models["inside_but_absent"]["checkpoint_inside_workspace"] is True
    assert models["no_weights_by_design"]["checkpoint_state"] == "not_recorded"
    assert models["no_weights_by_design"]["evidence_exists"] is True

    summary = report["summary"]
    assert summary["checkpoint_foreign_workspace"] == 1
    assert summary["evidence_resolvable_by_relative_path"] == 1
    assert summary["checkpoint_not_recorded"] == 1
    assert report["interpretation"]["read_only"]


def test_horizon_audit_detects_a_hand_built_cdf_violation() -> None:
    """Expected values are computed by hand, not by the code under test."""
    table = pd.DataFrame({
        # Coherent: 0.1 <= 0.2 <= 0.3, and 0.4 <= 0.4 <= 0.9.
        "p_30d": [0.1, 0.4], "p_90d": [0.2, 0.4], "p_1yr": [0.3, 0.9],
        # One violation: 0.7797 > 0.600 is a drop of 0.1797; the second row is coherent.
        "p_lifetime_30d": [0.7797, 0.1],
        "p_lifetime_90d": [0.600, 0.2],
        "p_lifetime_1yr": [0.8571, 0.3],
        # Missing values must be dropped, leaving one coherent row.
        "p_lifetime_raw_30d": [0.1, None],
        "p_lifetime_raw_90d": [0.2, None],
        "p_lifetime_raw_1yr": [0.3, 0.5],
    })

    findings = audit_horizons(table)

    assert findings["p"]["status"] == "coherent"
    assert findings["p"]["violations"] == 0

    lifetime = findings["p_lifetime"]
    assert lifetime["status"] == "violations_found"
    assert lifetime["objects_with_values"] == 2
    assert lifetime["violations"] == 1
    assert lifetime["violation_fraction"] == 0.5
    assert lifetime["max_drop"] == pytest.approx(0.1797)
    assert lifetime["worst_example"]["p_lifetime_30d"] == pytest.approx(0.7797)

    raw = findings["p_lifetime_raw"]
    assert raw["status"] == "coherent"
    assert raw["objects_with_values"] == 1

    # A family whose columns are absent is reported as absent, not as coherent.
    assert audit_horizons(pd.DataFrame({"p_30d": [0.1]}))["p"]["status"] == "absent"
    assert audit_horizons(pd.DataFrame({"p_30d": [0.1]}))["p_lifetime"]["status"] == "absent"
