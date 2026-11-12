"""Orchestrator modules for the twin-state evidence root (P3-B, 2026-11-08).

``twin_state`` is an additional ROOT module: it selects the twin-state archive under an explicit policy,
validates every record in one streaming pass and publishes a byte-offset index plus the archive's
provenance. ``twin_equivalence`` depends on it and on the catalogue chain and compares shared values record
by record. Neither module changes, feeds or replaces ``catalogue_state → lifetime → reentry →
decision_priority``; nothing is regenerated, repaired or substituted.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..contracts import Provenance
from ..orchestration import ModuleContext, ModuleResult
from ..provenance import ROOT, git_revision, sha256_file
from . import reader


class TwinStateUnavailable(RuntimeError):
    """No twin-state archive could be selected or the selected archive holds no valid record."""


def twin_state_records(context: ModuleContext) -> ModuleResult:
    """Select, verify and index the twin-state archive; publish its provenance as flat manifest fields."""
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    policy = context.config.get("twin_source_policy") or reader.DEFAULT_POLICY
    selection = reader.select_source(root, as_of, policy)
    if selection["selected"] is None:
        raise TwinStateUnavailable(selection["reason"])
    cand = selection["candidates"][selection["selected"]]
    path = root / cand["artifact"]
    index: dict[str, tuple[int, int]] = {}

    def on_record(rec: dict[str, Any], _line: int, offset: int, length: int) -> None:
        index.setdefault(str(rec["object_id"]), (offset, length))   # first occurrence; duplicates are counted below

    integrity = reader.validate_archive(path, on_record=on_record)
    if integrity["records_valid"] == 0:
        raise TwinStateUnavailable(
            f"{cand['artifact']} holds no valid twin record ({integrity['records_total']} lines: "
            f"{integrity['records_malformed_json']} malformed JSON, {integrity['records_schema_invalid']} schema-invalid)")
    model_digest = cand["model_version"]["digest"] if cand["model_version"]["status"] == "recorded" else None
    provenance = Provenance(
        as_of=as_of,
        input_sources=(f"COSMOS twin-state archive ({cand['kind']}, {cand['schema_version']})",)
        + (("re-emission manifest",) if cand.get("transformation_digest_sha256") else ()),
        input_hashes={cand["artifact"]: cand["computed_sha256"]},
        code_revision=git_revision(root)["git_commit"],
        model_digest=model_digest,
    )
    outputs: dict[str, Any] = {
        "record_index": index,
        "artifact": cand["artifact"], "source": selection["selected"], "selection_status": selection["status"],
        "policy": policy, "fallback_used": selection["fallback_used"], "selection_reason": selection["reason"],
        "schema_version": cand["schema_version"], "artifact_sha256": cand["computed_sha256"],
        "artifact_recorded_sha256": cand["recorded_sha256"], "digest_state": cand["digest_state"],
        "transformation_digest_sha256": cand["transformation_digest_sha256"], "reemission_method": cand["method"],
        "reemission_code_revision": cand["code_revision"], "original_or_reemitted": cand["kind"],
        "record_count": cand["record_count"], "recorded_record_count": cand["recorded_record_count"],
        "record_count_state": cand["record_count_state"], "provenance_on_outputs": cand["provenance_on_outputs"],
        "provenance_complete": cand["provenance_complete"], "model_version_status": cand["model_version"]["status"],
        "predictions_regenerated": cand["predictions_regenerated"], "model_executed": cand["model_executed"],
        "integrity_status": integrity["status"], "records_total": integrity["records_total"],
        "records_valid": integrity["records_valid"], "records_malformed_json": integrity["records_malformed_json"],
        "records_schema_invalid": integrity["records_schema_invalid"], "duplicate_identities": integrity["duplicate_identities"],
        "records_with_value_problems": integrity["records_with_value_problems"], "unique_identities": integrity["unique_identities"],
        "schema_versions_seen": "; ".join(f"{v}: {n}" for v, n in integrity["schema_versions"].items()),
        "integrity_examples": integrity["examples"],
    }
    return ModuleResult(outputs=outputs, provenance=provenance)


def twin_equivalence(context: ModuleContext) -> ModuleResult:
    """Compare every indexed twin record with the catalogue chain's outputs of this run."""
    from .. import adapters  # local import: adapters imports this module for default_modules()
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    tw = context.outputs["twin_state"]
    path = root / tw["artifact"]
    view = reader.chain_view_from_outputs(context.outputs)
    acc = reader.EquivalenceAccumulator(set(view))
    comparison: dict[str, dict[str, Any]] = {}
    with path.open("rb") as fh:
        for oid, (offset, length) in tw["record_index"].items():
            fh.seek(offset)
            rec = json.loads(fh.read(length))
            res = reader.compare_record(rec, view.get(oid))
            acc.add(res)
            comparison[f"NORAD-{oid}"] = {
                "object_id": f"NORAD-{oid}", "status": res["status"], "fields_compared": res["fields_compared"],
                "fields_equal": res["fields_equal"], "fields_different": ";".join(res["fields_different"]),
                "not_comparable_fields": ";".join(res["not_comparable"]),
            }
    summary = acc.summary()
    snapshot_rel = adapters.TWIN_SNAPSHOT.format(as_of=as_of)
    hashes = {tw["artifact"]: tw["artifact_sha256"]}
    if (root / snapshot_rel).is_file():
        hashes[snapshot_rel] = sha256_file(root / snapshot_rel)
    provenance = Provenance(
        as_of=as_of,
        input_sources=("twin_state module output", "catalogue chain outputs (catalogue_state, lifetime, reentry)"),
        input_hashes=hashes, code_revision=git_revision(root)["git_commit"],
        upstream_outputs=("twin_state", "catalogue_state", "lifetime", "reentry"),
    )
    outputs: dict[str, Any] = {
        "comparison": comparison,
        **{k: summary[k] for k in ("twin_records", "records_compared", "records_equal", "records_different", "records_not_comparable",
                                   "records_missing_in_chain", "records_missing_in_twin", "fields_compared", "fields_equal",
                                   "fields_different", "equivalent")},
        "different_fields_summary": "; ".join(f"{k}: {n}" for k, n in summary["different_fields"].items()) or "none",
        "not_comparable_reasons_summary": " | ".join(f"{k} ({n})" for k, n in summary["not_comparable_reasons"].items()) or "none",
        "chain_source": tw["source"], "run_universe": len(view),
        "note": summary["note"],
    }
    return ModuleResult(outputs=outputs, provenance=provenance)
