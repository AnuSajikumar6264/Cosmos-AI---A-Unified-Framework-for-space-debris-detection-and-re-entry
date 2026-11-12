#!/usr/bin/env python3
"""Report model-card evidence and checkpoint resolution without modifying the registry.

This script is read-only. It never rewrites `outputs/registry/model_cards.json`, never
downloads a substitute checkpoint and never alters model weights.

Limitation L13 is that three OPSSAT cards in the saved registry record absolute checkpoint
paths under a *different* workspace (`/data/anupa/COSMOS_work/...`). The audit therefore
separates cases that a single "missing" flag would conflate:

``not_recorded``
    The card records no checkpoint. For most cards this is correct: the model is a tree
    ensemble, a zero-shot model or an analytic baseline with no saved weights.
``present``
    The recorded path resolves to a file in this workspace.
``foreign_workspace``
    The path is absolute and points outside this repository. It cannot be checked here and
    says nothing about whether the result is reproducible.
``missing_in_workspace``
    The path is inside this repository but the file is absent.

For a foreign path the audit also reports whether a run directory with the **same run ID**
exists locally, and whether that directory has a `checkpoints/` folder. Weights are excluded
from the repository by `.gitignore` (`outputs/experiments/*/checkpoints/`, `*.pt`), so their
absence is expected and is a *checkpoint-portability* limitation, not evidence that the
recorded metrics are untraceable: `metrics.json`, `config.yaml` and `env.json` remain.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

#: An experiment run directory is named "<timestamp>_<name>_s<seed>".
RUN_ID = re.compile(r"\d{8}-\d{6}_[A-Za-z0-9_.\-]+")

#: Repository top-level directories that a recorded artifact path may start from. Used to
#: recover the repo-relative suffix of a path recorded under a different workspace root.
REPO_ANCHORS = ("outputs", "data", "configs", "paper", "thesis", "research_design")


def _relative_suffix(value: str, project: Path | None = None) -> str | None:
    """Repo-relative suffix of a path recorded under some other workspace root.

    ``/data/anupa/COSMOS_work/Final_Project/outputs/benchmarks/x.csv`` yields
    ``outputs/benchmarks/x.csv``. An anchor name can occur more than once -- the example above
    starts with ``/data`` -- so every candidate is tried and one that resolves inside
    ``project`` wins. Without a project, or when none resolves, the rightmost anchor is used,
    since the deepest anchor is the one nearest the repository-relative part of the path.
    """
    parts = Path(value).parts
    candidates = [str(Path(*parts[index:])) for index, part in enumerate(parts)
                  if part in REPO_ANCHORS]
    if not candidates:
        return None
    if project is not None:
        for candidate in candidates:
            if (project / candidate).exists():
                return candidate
    return candidates[-1]


def _relative_equivalent(project: Path, value: str | None) -> dict | None:
    """Whether the repo-relative suffix of a foreign path exists in this workspace.

    This is a diagnostic only. It does not rewrite the registry and does not assert that the
    local file is byte-identical to the one the card was generated from.
    """
    if not value:
        return None
    suffix = _relative_suffix(value, project)
    if suffix is None:
        return None
    candidate = project / suffix
    return {
        "relative_suffix": suffix,
        "exists_in_workspace": candidate.exists(),
        "note": ("same repo-relative location; identity with the originally recorded file is "
                 "not verified"),
    }


def _resolution(project: Path, value: str | None) -> dict:
    """Classify how a recorded artifact path resolves against this workspace."""
    if not value:
        return {"state": "not_recorded", "resolved_path": None, "exists": None,
                "inside_workspace": None}
    path = Path(value)
    if not path.is_absolute():
        resolved = (project / path).resolve()
        inside = True
    else:
        resolved = path
        try:
            resolved.relative_to(project)
            inside = True
        except ValueError:
            inside = False
    exists = resolved.exists()
    if not inside:
        state = "foreign_workspace"
    elif exists:
        state = "present"
    else:
        state = "missing_in_workspace"
    return {"state": state, "resolved_path": str(resolved), "exists": exists,
            "inside_workspace": inside}


def _local_equivalent(project: Path, checkpoint: str | None) -> dict | None:
    """Look for a local run directory with the same run ID as a foreign checkpoint path.

    Reports only what is on disk. It does not treat a local directory as a substitute for
    the recorded weights.
    """
    if not checkpoint:
        return None
    match = None
    for part in Path(checkpoint).parts:
        found = RUN_ID.fullmatch(part)
        if found:
            match = part
            break
    if match is None:
        return None
    candidate = project / "outputs" / "experiments" / match
    if not candidate.is_dir():
        return {"run_id": match, "local_run_dir": None, "has_checkpoint_dir": False,
                "records": []}
    checkpoints = candidate / "checkpoints"
    records = sorted(p.name for p in candidate.iterdir() if p.is_file())
    return {
        "run_id": match,
        "local_run_dir": str(candidate.relative_to(project)),
        "has_checkpoint_dir": checkpoints.is_dir(),
        "checkpoint_files": sorted(p.name for p in checkpoints.iterdir()) if checkpoints.is_dir() else [],
        "records": records,
    }


def audit_model_cards(root: str | Path) -> dict:
    project = Path(root).resolve()
    registry = project / "outputs/registry/model_cards.json"
    if not registry.is_file():
        raise FileNotFoundError(f"model registry not found: {registry}")
    cards = json.loads(registry.read_text(encoding="utf-8"))
    if not isinstance(cards, list):
        raise ValueError(f"model registry must contain a list: {registry}")

    results = []
    counts = {"cards": len(cards), "missing_evidence": 0, "missing_checkpoint": 0,
              "checkpoint_not_recorded": 0, "checkpoint_present": 0,
              "checkpoint_foreign_workspace": 0,
              "evidence_resolvable_by_relative_path": 0}
    for card in cards:
        if not isinstance(card, dict) or not isinstance(card.get("name"), str):
            raise ValueError("each model card must be an object with a name")
        evidence = card.get("evidence")
        checkpoint = card.get("checkpoint")
        evidence_resolution = _resolution(project, evidence)
        checkpoint_resolution = _resolution(project, checkpoint)

        evidence_relative = None
        if evidence and not evidence_resolution["exists"]:
            counts["missing_evidence"] += 1
            evidence_relative = _relative_equivalent(project, evidence)
            if evidence_relative and evidence_relative["exists_in_workspace"]:
                counts["evidence_resolvable_by_relative_path"] += 1
        state = checkpoint_resolution["state"]
        if state == "not_recorded":
            counts["checkpoint_not_recorded"] += 1
        elif state == "present":
            counts["checkpoint_present"] += 1
        elif state == "foreign_workspace":
            counts["checkpoint_foreign_workspace"] += 1
            counts["missing_checkpoint"] += 1
        else:
            counts["missing_checkpoint"] += 1

        record = {
            "name": card["name"],
            "feature": card.get("feature", "unspecified"),
            "status": card.get("status", "unspecified"),
            "version": card.get("version"),
            "evidence": evidence,
            # Retained for backward compatibility with the earlier report shape.
            "evidence_exists": evidence_resolution["exists"],
            "checkpoint": checkpoint,
            "checkpoint_exists": checkpoint_resolution["exists"],
            "checkpoint_state": state,
            "checkpoint_inside_workspace": checkpoint_resolution["inside_workspace"],
            "checkpoint_resolved_path": checkpoint_resolution["resolved_path"],
        }
        if evidence_relative is not None:
            record["evidence_relative_equivalent"] = evidence_relative
        if state == "foreign_workspace":
            record["local_equivalent"] = _local_equivalent(project, checkpoint)
        results.append(record)

    return {
        "registry": str(registry),
        "summary": counts,
        "models": results,
        "interpretation": {
            "read_only": "this audit never modifies the registry or any weight file",
            "checkpoint_absence": ("weights are excluded by .gitignore "
                                   "(outputs/experiments/*/checkpoints/, *.pt), so absence is "
                                   "expected in a clone"),
            "reproducibility": ("a missing checkpoint limits exact weight reuse; it does not "
                                "by itself make the recorded metrics untraceable, because "
                                "metrics.json, config.yaml and env.json remain"),
            "not_established": ("registry status strings are not claims of independent "
                                "validation"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--out", default=None, help="write the JSON report to this path")
    parser.add_argument("--quiet", action="store_true", help="print only the summary table")
    args = parser.parse_args(argv)

    report = audit_model_cards(args.root)
    if args.quiet:
        print(json.dumps(report["summary"], indent=2))
        for model in report["models"]:
            if model["checkpoint_state"] in {"foreign_workspace", "missing_in_workspace"}:
                local = model.get("local_equivalent") or {}
                print(f"  {model['name']:22s} {model['checkpoint_state']:22s} "
                      f"local_run_dir={local.get('local_run_dir')} "
                      f"has_checkpoint_dir={local.get('has_checkpoint_dir')}")
    else:
        print(json.dumps(report, indent=2))

    if args.out:
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w") as stream:
            json.dump(report, stream, indent=2)
        print(f"written: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
