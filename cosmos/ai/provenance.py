"""Reproducibility metadata for experiment runs, recorded outside the frozen code.

``cosmos/ai/experiment.py`` is listed in
``research_design/preregistration/freeze.json``: ``oof_benchmark.test`` refuses to score the
held-out telemetry half if any frozen file changes.  Provenance capture therefore lives here
and attaches itself to an existing :class:`cosmos.ai.experiment.Run` through that class's
public ``extra`` mapping, so the pre-registration hash of the confirmatory analysis code
stays intact.

What this module records is lineage, not scientific validity: a Git revision, a seed, a
config digest and a dataset-manifest digest say which inputs produced a result, not that the
result is correct.  Digests are never guessed; a value that cannot be determined is written
as ``None`` with the reason alongside it.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .experiment import Run, config_hash

#: Repository root (this file is ``<root>/cosmos/ai/provenance.py``).
ROOT = Path(__file__).resolve().parents[2]

#: Default dataset manifest consulted when a run does not name one.
DEFAULT_MANIFEST = ROOT / "data" / "DATASET_MANIFEST.csv"

METADATA_FILENAME = "run_metadata.json"


def sha256_file(path: str | os.PathLike[str]) -> str:
    """SHA-256 of a file, read in blocks so large archives do not load into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision(repository: Path = ROOT) -> dict[str, Any]:
    """Current commit and whether tracked files differ from it.

    ``tracked_worktree_dirty`` deliberately ignores untracked files: an untracked scratch
    file does not change the code that produced a result, but an edited tracked file does.
    A failure is reported in ``git_error`` rather than silently dropped.
    """
    record: dict[str, Any] = {"git_commit": None, "tracked_worktree_dirty": None,
                              "git_error": None}
    try:
        record["git_commit"] = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=no"],
            check=True, capture_output=True, text=True,
        ).stdout
        record["tracked_worktree_dirty"] = bool(status.strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        record["git_error"] = f"{type(exc).__name__}: {exc}"
    return record


def run_metadata(seed: int, config: dict, *, dataset_manifest: str | os.PathLike[str] | None = None,
                 model_version: str | None = None,
                 repository: Path = ROOT) -> dict[str, Any]:
    """Lineage record for one run: seed, config digest, code revision, dataset digest."""
    metadata: dict[str, Any] = {
        "seed": seed,
        "config_sha256": config_hash(config),
        "model_version": model_version,
        "repository": str(repository),
        "dataset_manifest": None,
        "dataset_manifest_sha256": None,
    }
    metadata.update(git_revision(repository))

    manifest = Path(dataset_manifest) if dataset_manifest else DEFAULT_MANIFEST
    if not manifest.is_absolute():
        manifest = repository / manifest
    if manifest.is_file():
        metadata["dataset_manifest"] = str(manifest.resolve())
        metadata["dataset_manifest_sha256"] = sha256_file(manifest)
    else:
        # Recorded as a stated absence, so a reader cannot mistake it for a verified input.
        metadata["dataset_manifest"] = f"not found: {manifest}"
    return metadata


@contextmanager
def tracked_run(name: str, config: dict, *, seed: int = 0, device: str | None = None,
                group: str | None = None, root: str | None = None,
                dataset_manifest: str | os.PathLike[str] | None = None,
                model_version: str | None = None) -> Iterator[Run]:
    """Open an experiment :class:`Run` and record its lineage next to its results.

    Writes ``run_metadata.json`` into the run directory and mirrors the same record into
    ``metrics.json`` under ``provenance`` via ``Run.extra``, without modifying the frozen
    experiment module.  Existing run directories are never rewritten.
    """
    run = Run(name, config, seed=seed, device=device, group=group, root=root)
    with run:
        metadata = run_metadata(seed, run.config, dataset_manifest=dataset_manifest,
                                model_version=model_version)
        with open(os.path.join(run.dir, METADATA_FILENAME), "w") as stream:
            json.dump(metadata, stream, indent=2)
        run.extra["provenance"] = metadata
        yield run
