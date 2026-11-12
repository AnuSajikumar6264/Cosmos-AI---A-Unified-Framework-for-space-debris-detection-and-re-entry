"""Schema versions of COSMOS-AI records (P1.3, 2026-11-08).

Policy — see docs/architecture/SCHEMA_VERSIONING.md:
* every record family has a dotted version string; MAJOR changes break readers, MINOR adds fields;
* archived records never carry a version and are read as the family's legacy version ("1.0");
* readers accept every listed version; writers stamp the current one; archives are never rewritten;
* validation names the offending field and raises :class:`SchemaError`; nothing is repaired silently.
"""
from __future__ import annotations

from typing import Any

CURRENT = {
    "forecast_table": "1.0",     # the archived dated forecast (column set below); no version column exists
    "twin_state": "1.1",         # 1.0 = archived twins.jsonl (no provenance); 1.1 = re-emitted with provenance
    "run_manifest": "1.2",       # 1.0 = no `lineage`; 1.1 = lineage + schema_version; 1.2 = outputs serialised under the allow-list
    "object_record": "1.1",      # console object record / API
    "report": "1.1",             # object assessment report (1.0 lacked model version, subgroup cue, freshness)
    "api": "1.2",                # 1.1 evidence classes/lineage views; 1.2 (P3-A/P3-B, additive): /api/ready, redaction block, /api/twin-state, selection + equivalence on twin records
    "freshness": "1.0",
}
ACCEPTED = {"twin_state": ("1.0", "1.1"), "run_manifest": ("1.0", "1.1", "1.2"), "report": ("1.0", "1.1")}

#: Module-output dictionaries a run manifest may carry verbatim (metadata needed to explain an output from
#: the manifest alone). Every other dict-valued output is recorded as ``{"count": n}`` — per-object maps
#: such as names, regimes or abstention reasons never belong in the manifest (P3-A1, 2026-11-08).
MANIFEST_VERBATIM_OUTPUTS = frozenset({"priority_rule"})
#: The only dictionary shapes a non-allow-listed output may take in a 1.2 manifest: a collection count, a
#: table summary (rows + column names) or a module-evidence record (module, status, reason).
_MANIFEST_SUMMARY_FORMS = ({"count"}, {"rows", "columns"}, {"module", "status", "reason"})

#: Columns every reader of the dated forecast table requires (shared with adapters._load_snapshot).
REQUIRED_FORECAST_COLUMNS = frozenset({
    "norad", "Name", "type1", "regime", "perigee", "apogee", "inc", "mass",
    "median_days", "lo90_days", "hi90_days", "lo80_days", "hi80_days",
    "p_30d", "p_90d", "p_1yr", "median_days_lifetime",
    "lifetime_lo90_days", "lifetime_hi90_days",
    "p_lifetime_30d", "p_lifetime_90d", "p_lifetime_1yr"})

TWIN_RECORD_KEYS = ("object_id", "name", "object_class", "as_of", "orbit", "physical", "operational_status",
                    "family", "space_weather", "outputs", "regime")
TWIN_OUTPUT_KEYS = ("module", "model", "validation", "values", "uncertainty", "abstain", "reason")
# archived (1.0) outputs may lack the provenance key entirely; 1.1 outputs must carry a filled one


class SchemaError(ValueError):
    """A record does not match any accepted version of its family; the message names the field."""


def stamp(family: str) -> str:
    return f"{family}/{CURRENT[family]}"


def _version_of(record: dict[str, Any], family: str) -> str:
    raw = record.get("schema_version")
    if raw is None:
        return "1.0"                                   # archived, pre-versioning record
    if not isinstance(raw, str) or "/" not in raw or raw.split("/", 1)[0] != family:
        raise SchemaError(f"schema_version {raw!r} is not a {family} version")
    version = raw.split("/", 1)[1]
    if version not in ACCEPTED.get(family, (CURRENT[family],)):
        raise SchemaError(f"{family} version {version!r} is not accepted (accepted: {ACCEPTED.get(family)})")
    return version


def validate_twin_record(record: dict[str, Any]) -> str:
    """Return the record's version ("1.0" archived, "1.1" re-emitted) or raise SchemaError."""
    if not isinstance(record, dict):
        raise SchemaError("twin record must be an object")
    version = _version_of(record, "twin_state")
    for key in TWIN_RECORD_KEYS:
        if key not in record:
            raise SchemaError(f"twin record missing key {key!r}")
    if not isinstance(record["object_id"], str) or not record["object_id"].strip():
        raise SchemaError("twin record object_id must be a non-empty string")
    if record["object_class"] not in {"P", "R", "C", "D"}:
        raise SchemaError(f"twin record object_class {record['object_class']!r} unsupported")
    if not isinstance(record["outputs"], list):
        raise SchemaError("twin record outputs must be a list")
    for i, out in enumerate(record["outputs"]):
        for key in TWIN_OUTPUT_KEYS:
            if key not in out:
                raise SchemaError(f"twin output {i} missing key {key!r}")
        if not isinstance(out["abstain"], bool):
            raise SchemaError(f"twin output {i} abstain must be boolean")
        if out["abstain"] and not str(out.get("reason", "")).strip():
            raise SchemaError(f"twin output {i} abstains without a reason")
        if version == "1.1":
            prov = out.get("provenance")
            if not isinstance(prov, dict) or not prov.get("as_of") or not prov.get("input_hashes"):
                raise SchemaError(f"twin output {i} (v1.1) must carry provenance with as_of and input_hashes")
    if version == "1.1":
        src = record.get("source_record")
        if not isinstance(src, dict) or not {"artifact", "sha256", "row_index", "norad"} <= set(src):
            raise SchemaError("twin record (v1.1) must carry source_record {artifact, sha256, row_index, norad}")
        if record.get("reemitted_from_archive") is not True:
            raise SchemaError("twin record (v1.1) must state reemitted_from_archive: true")
    return version


def validate_run_manifest(manifest: dict[str, Any]) -> str:
    """Return the manifest version or raise SchemaError. 1.0 = no lineage; 1.1 = lineage per success module."""
    if not isinstance(manifest, dict):
        raise SchemaError("run manifest must be an object")
    version = _version_of(manifest, "run_manifest")
    for key in ("as_of", "started_at", "modules"):
        if key not in manifest:
            raise SchemaError(f"run manifest missing key {key!r}")
    if not isinstance(manifest["modules"], dict):
        raise SchemaError("run manifest modules must be an object")
    for name, rec in manifest["modules"].items():
        if not isinstance(rec, dict) or "status" not in rec:
            raise SchemaError(f"module record {name!r} must carry a status")
        if version in ("1.1", "1.2") and rec.get("status") == "success" and "lineage" not in rec:
            raise SchemaError(f"module record {name!r} (v{version}) must carry lineage")
        if version == "1.2":
            for key, value in (rec.get("outputs") or {}).items():
                if isinstance(value, dict) and key not in MANIFEST_VERBATIM_OUTPUTS \
                        and set(value) not in _MANIFEST_SUMMARY_FORMS:
                    raise SchemaError(f"module {name!r} output {key!r} (v1.2) must be a count, table summary or "
                                      f"evidence record, not a verbatim dictionary")
    return version


def validate_forecast_columns(columns) -> None:
    missing = REQUIRED_FORECAST_COLUMNS - set(columns)
    if missing:
        raise SchemaError(f"forecast table is missing columns: {sorted(missing)}")
