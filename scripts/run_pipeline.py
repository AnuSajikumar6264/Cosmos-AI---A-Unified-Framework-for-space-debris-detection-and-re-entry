"""Execute the COSMOS-AI adapter pipeline and write one versioned, auditable run directory.

The pipeline re-expresses saved scientific artifacts through the shared contracts (see
``cosmos/ai/adapters.py``). It does not train, re-fit or rescore anything, so running it
cannot change a published number.

    python scripts/run_pipeline.py --as-of 2026-10-27 --limit 500
    python scripts/run_pipeline.py --as-of 2026-10-27 --select decision_priority
    python scripts/run_pipeline.py --as-of 2026-10-27 --list

Each run writes ``outputs/pipeline/run_<UTC timestamp>/`` containing the resolved config, a
per-module status and provenance manifest, and the tables that succeeded. An existing run
directory is never overwritten. The process exits non-zero if any requested module failed or
was blocked, so a partial run is visible to a caller and to CI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai import adapters                                      # noqa: E402
from cosmos.ai.contracts import ModuleEvidence                      # noqa: E402
from cosmos.ai.experiment import environment                        # noqa: E402
from cosmos.ai.orchestration import Orchestrator, PipelineExecution  # noqa: E402
from cosmos.ai.provenance import ROOT, git_revision                 # noqa: E402


def _jsonable(value, key: str | None = None):
    """Manifest form of one module output.

    Dictionaries are kept verbatim ONLY when their output key is in ``schema.MANIFEST_VERBATIM_OUTPUTS`` (today:
    ``priority_rule``) and they hold scalars or lists of scalars; every other dict or sequence is recorded
    as a count. Per-object maps (names, regimes, abstention reasons) therefore never inflate a manifest —
    the 2026-11-08 demonstration run (5.2 MB) is the historical case this rule closes.
    """
    from cosmos.ai.schema import MANIFEST_VERBATIM_OUTPUTS
    if isinstance(value, ModuleEvidence):
        return {"module": value.module, "status": value.status, "reason": value.reason}
    if isinstance(value, pd.DataFrame):
        return {"rows": int(len(value)), "columns": list(value.columns)}
    if isinstance(value, dict):
        plain = all(isinstance(v, (str, int, float, bool, type(None))) or
                    (isinstance(v, (list, tuple)) and all(isinstance(x, (str, int, float, bool, type(None))) for x in v))
                    for v in value.values())
        if key in MANIFEST_VERBATIM_OUTPUTS and plain:
            return {k: (list(v) if isinstance(v, tuple) else v) for k, v in value.items()}
        return {"count": len(value)}
    if isinstance(value, (tuple, list)):
        return {"count": len(value)}
    return value


def _abstentions(outputs) -> dict:
    """Group per-object abstention reasons so the count for each reason is auditable.

    Reasons are grouped rather than listed per object: the list can be thousands of entries,
    while the distinct reasons are what a reader needs. Object identifiers stay in the CSVs.
    """
    abstained = outputs.get("abstained")
    if not isinstance(abstained, dict) or not abstained:
        return {}
    grouped: dict[str, int] = {}
    for reason in abstained.values():
        grouped[str(reason)] = grouped.get(str(reason), 0) + 1
    return dict(sorted(grouped.items(), key=lambda item: -item[1]))


def _module_manifest(execution: PipelineExecution) -> dict:
    manifest = {}
    for name, module in execution.modules.items():
        record = {
            "status": module.status,
            "reason": module.reason,
            "error": module.error,
            "started_at": module.started_at,
            "duration_s": module.duration_s,
            "outputs": {key: _jsonable(value, key) for key, value in module.outputs.items()},
        }
        abstentions = _abstentions(module.outputs)
        if abstentions:
            record["abstentions"] = abstentions
            record["abstained_total"] = sum(abstentions.values())
        evidence = module.outputs.get("health_escalation")
        if isinstance(evidence, ModuleEvidence):
            record["health_escalation"] = {
                "status": evidence.status, "reason": evidence.reason,
            }
        noncoherent = module.outputs.get("noncoherent_horizon_probabilities")
        if isinstance(noncoherent, dict):
            record["noncoherent_horizon_probabilities"] = len(noncoherent)
        if module.provenance is not None:
            record["provenance"] = {
                "as_of": module.provenance.as_of,
                "input_sources": list(module.provenance.input_sources),
                "input_hashes": dict(module.provenance.input_hashes),
                "code_revision": module.provenance.code_revision,
                "config_digest": module.provenance.config_digest,
                "upstream_outputs": list(module.provenance.upstream_outputs),
            }
            # Lineage keeps the four version notions apart. No twin module runs a fitted model, so
            # the model version is recorded as unavailable rather than borrowed from an artifact hash
            # or a registry card.
            record["lineage"] = {
                "code_version": {"git_commit": module.provenance.code_revision or "unavailable"},
                "configuration_version": {"config_sha256": module.provenance.config_digest or "unavailable"},
                "data_artifacts": dict(module.provenance.input_hashes) or (
                    {"derived_from_upstream_outputs": list(module.provenance.upstream_outputs)}
                    if module.provenance.upstream_outputs else {"unavailable": "no input hash recorded"}),
                "model_version": {
                    "status": "recorded" if module.provenance.model_digest else "unavailable",
                    "digest": module.provenance.model_digest,
                    "label": None,
                    "reason": (None if module.provenance.model_digest else
                               "no fitted model is persisted for this module; its values were read from the "
                               "archived prediction artifact(s) listed under data_artifacts"),
                    "registry_card": None,
                    "registry_note": ("no verified association between this output and a model registry "
                                      "card is recorded; none is inferred"),
                },
            }
        manifest[name] = record
    return manifest


def _write_tables(execution: PipelineExecution, run_dir: Path) -> list[str]:
    """Persist the tabular outputs that exist; never invent a table for a failed module."""
    written: list[str] = []

    decision = execution.modules["decision_priority"]
    if decision.status == "success":
        ranking = decision.outputs["ranking"]
        ranking.to_csv(run_dir / "decision_ranking.csv", index=False)
        written.append("decision_ranking.csv")

    reentry = execution.modules["reentry"]
    if reentry.status == "success":
        rows = []
        for object_id, prediction in reentry.outputs["reentry"].items():
            quantiles = dict(prediction.time_quantiles_days)
            rows.append({
                "object_id": object_id,
                "as_of": prediction.as_of,
                "model": prediction.model,
                **{f"p_{int(h)}d": p for h, p in prediction.probability_by_horizon.items()},
                "days_q05": quantiles.get(0.05),
                "days_q50": quantiles.get(0.50),
                "days_q95": quantiles.get(0.95),
                "uncertainty_kind": prediction.uncertainty.kind,
                "uncertainty_method": prediction.uncertainty.method,
            })
        pd.DataFrame(rows).to_csv(run_dir / "reentry_predictions.csv", index=False)
        written.append("reentry_predictions.csv")

    lifetime = execution.modules["lifetime"]
    if lifetime.status == "success":
        rows = []
        for object_id, estimate in lifetime.outputs["lifetime"].items():
            quantiles = dict(estimate.quantiles_days)
            rows.append({
                "object_id": object_id,
                "model": estimate.model,
                "days_q05": quantiles.get(0.05),
                "days_q50": quantiles.get(0.50),
                "days_q95": quantiles.get(0.95),
                **{f"p_{int(h)}d": p for h, p in estimate.horizon_probabilities.items()},
            })
        pd.DataFrame(rows).to_csv(run_dir / "lifetime_estimates.csv", index=False)
        written.append("lifetime_estimates.csv")
        flagged = lifetime.outputs["noncoherent_horizon_probabilities"]
        if flagged:
            pd.DataFrame(
                [{"object_id": key, **value} for key, value in flagged.items()]
            ).to_csv(run_dir / "lifetime_noncoherent_horizons.csv", index=False)
            written.append("lifetime_noncoherent_horizons.csv")

    collision = execution.modules["collision"]
    if collision.status == "success":
        rows = [{
            "event_id": event_id,
            "collision_probability": estimate.collision_probability,
            "interval_lower": estimate.uncertainty.lower,
            "interval_upper": estimate.uncertainty.upper,
            "interval_level": estimate.uncertainty.level,
            "priority_score": estimate.priority_score,
            "identity_linkable": False,
        } for event_id, estimate in collision.outputs["collision"].items()]
        pd.DataFrame(rows).to_csv(run_dir / "collision_risk.csv", index=False)
        written.append("collision_risk.csv")

    health = execution.modules["health"]
    if health.status == "success":
        rows = [{
            "arm_id": arm_id,
            "model": estimate.model,
            "event_wise_f05": estimate.anomaly_score,
            "score_semantics": estimate.score_semantics,
            "alarm": estimate.alarm,
            "identity_linkable": False,
        } for arm_id, estimate in health.outputs["health"].items()]
        pd.DataFrame(rows).to_csv(run_dir / "health_benchmark_arms.csv", index=False)
        written.append("health_benchmark_arms.csv")

    debris = execution.modules["debris"]
    if debris.status == "success":
        rows = [{
            "image_id": detection.image_id,
            "frame_index": detection.frame_index,
            "x_px": detection.x_px,
            "y_px": detection.y_px,
            "confidence": detection.confidence,
            "detector": detection.detector,
        } for detection in debris.outputs["detections"]]
        pd.DataFrame(rows).to_csv(run_dir / "debris_detections.csv", index=False)
        written.append("debris_detections.csv")

    twin_eq = execution.modules.get("twin_equivalence")
    if twin_eq is not None and twin_eq.status == "success":
        rows = list(twin_eq.outputs["comparison"].values())
        pd.DataFrame(rows, columns=["object_id", "status", "fields_compared", "fields_equal", "fields_different",
                                    "not_comparable_fields"]).to_csv(run_dir / "twin_equivalence.csv", index=False)
        written.append("twin_equivalence.csv")

    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", default="2026-10-27", help="snapshot date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=None,
                        help="keep the N highest 30-day re-entry probabilities")
    parser.add_argument("--collision-limit", type=int, default=None)
    parser.add_argument("--debris-sequence-limit", type=int, default=None)
    parser.add_argument("--health-calibrator", default=None,
                        help="restrict ESA-ADB rows to one calibrator, e.g. conformal_bh")
    parser.add_argument("--collision-model", default="cosmos_gated")
    parser.add_argument("--twin-source-policy", default="prefer_reemitted",
                        choices=["prefer_reemitted", "reemitted_only", "archived_only"],
                        help="twin-state archive selection (P3-B): prefer the re-emitted 1.1 with labelled 1.0 fallback, "
                             "1.1 only, or the historical 1.0 explicitly")
    parser.add_argument("--select", nargs="*", default=None,
                        help="modules to run (dependencies are added automatically)")
    parser.add_argument("--out", default=None, help="run directory (default: outputs/pipeline/run_<ts>)")
    parser.add_argument("--list", action="store_true", help="list modules and exit")
    args = parser.parse_args(argv)

    modules = adapters.default_modules()
    if args.list:
        for spec in modules:
            depends = ", ".join(spec.depends_on) or "-"
            print(f"{spec.name:20s} depends_on: {depends}")
        return 0

    config = {
        "as_of": args.as_of,
        "limit": args.limit,
        "collision_limit": args.collision_limit,
        "debris_sequence_limit": args.debris_sequence_limit,
        "health_calibrator": args.health_calibrator,
        "collision_model": args.collision_model,
        "twin_source_policy": args.twin_source_policy,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.out) if args.out else ROOT / "outputs" / "pipeline" / f"run_{stamp}"
    if run_dir.exists() and any(run_dir.iterdir()):
        raise SystemExit(f"{run_dir} already exists and is not empty; runs are never overwritten")
    run_dir.mkdir(parents=True, exist_ok=True)

    execution = Orchestrator(modules).run({}, selected=args.select, config=config)
    tables = _write_tables(execution, run_dir)

    from cosmos.ai.schema import stamp
    manifest = {
        "schema_version": stamp("run_manifest"),
        "as_of": args.as_of,
        "started_at": execution.started_at,
        "duration_s": round(execution.duration_s, 3),
        "requested": list(execution.requested),
        "config": config,
        "config_sha256": execution.config_sha256,
        "successful": execution.successful,
        "git": git_revision(ROOT),
        "environment": environment(),
        "tables_written": tables,
        "modules": _module_manifest(execution),
        "interpretation": {
            "scope": "interface and lineage execution over saved artifacts",
            "not_established": [
                "this run does not re-evaluate or revalidate any scientific result",
                "health (ESA-ADB) and conjunction (Kelvins CAC) records are anonymised and "
                "are not identity-linked to the catalogue or to each other",
                "the catalogue chain (elements, lifetime, re-entry) is identity-linked by "
                "NORAD number within one snapshot",
            ],
        },
    }
    with open(run_dir / "run_manifest.json", "w") as stream:
        json.dump(manifest, stream, indent=2, default=str)

    print(f"run directory: {run_dir}")
    for name, module in execution.modules.items():
        detail = module.error or module.reason
        print(f"  {name:20s} {module.status:14s} {detail}")
    print(f"tables written: {', '.join(tables) if tables else 'none'}")

    if not execution.successful:
        print("pipeline did not complete successfully", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
