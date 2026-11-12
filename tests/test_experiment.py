"""Reproducibility metadata recorded for each newly created experiment run.

The metadata is attached by ``cosmos/ai/provenance.py`` rather than by the experiment
module, because ``cosmos/ai/experiment.py`` is pre-registration-frozen (see
``research_design/preregistration/freeze.json``).  The freeze itself is asserted here so a
future edit to a frozen file fails in this test instead of silently locking the held-out
telemetry half out of scoring.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cosmos.ai.provenance import ROOT, sha256_file, tracked_run

FREEZE = ROOT / "research_design" / "preregistration" / "freeze.json"


def test_tracked_run_records_revision_seed_config_model_and_dataset_digest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("dataset,version\nfixture,1\n", encoding="utf-8")
    experiment_root = tmp_path / "experiments"

    with tracked_run(
        "metadata_contract",
        {"split": "forward"},
        seed=17,
        root=str(experiment_root),
        dataset_manifest=str(manifest),
        model_version="fixture-model-v1",
    ) as run:
        run.finish({"score": 1.0})

    run_directory = next(path for path in experiment_root.iterdir() if path.is_dir())
    metadata = json.loads((run_directory / "run_metadata.json").read_text())
    metrics = json.loads((run_directory / "metrics.json").read_text())
    expected_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()

    assert metadata["seed"] == 17
    assert metadata["model_version"] == "fixture-model-v1"
    assert metadata["dataset_manifest_sha256"] == expected_hash
    assert metrics["provenance"] == metadata
    assert metadata["git_commit"] or metadata["git_error"]


def test_missing_dataset_manifest_is_reported_not_guessed(tmp_path: Path) -> None:
    experiment_root = tmp_path / "experiments"
    absent = tmp_path / "absent.csv"

    with tracked_run("no_manifest", {"a": 1}, seed=0, root=str(experiment_root),
                     dataset_manifest=str(absent)):
        pass

    run_directory = next(path for path in experiment_root.iterdir() if path.is_dir())
    metadata = json.loads((run_directory / "run_metadata.json").read_text())

    assert metadata["dataset_manifest_sha256"] is None
    assert "not found" in metadata["dataset_manifest"]


def test_preregistration_freeze_is_intact() -> None:
    """Guard the confirmatory gate: a changed frozen file closes the test half."""
    record = json.loads(FREEZE.read_text())
    changed = [path for path, digest in record["sha256"].items()
               if sha256_file(ROOT / path) != digest]
    assert not changed, f"frozen files changed since the freeze: {changed}"
