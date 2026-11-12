"""Twin-state archive reader shared by the console and the orchestrator (P3-B, 2026-11-08).

One code path for: explicit source selection between the re-emitted ``twin_state/1.1`` archive and the
historical ``twin_state/1.0`` archive; provenance and integrity of the selected archive; streaming record
validation (schema, identity uniqueness, malformed lines, invalid values); and value equivalence of twin
records with the catalogue chain (``catalogue_state → lifetime → reentry``).

Everything here reads archives. Nothing regenerates a prediction, repairs a record or substitutes one
source for another without saying so. A missing archive is never reported as an empty one.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterator

from ..provenance import sha256_file
from ..schema import ACCEPTED, SchemaError, validate_twin_record

POLICIES = ("prefer_reemitted", "reemitted_only", "archived_only")
DEFAULT_POLICY = "prefer_reemitted"

#: The two archives a twin state can be read from. ``kind`` is the honest description of the data.
CANDIDATES: dict[str, dict[str, Any]] = {
    "reemitted": {
        "artifact": "outputs/twin/as_of_{as_of}_reemitted_v1/twins.jsonl",
        "digest": "outputs/twin/as_of_{as_of}_reemitted_v1/TWINS_SHA256.txt",
        "manifest": "outputs/twin/as_of_{as_of}_reemitted_v1/REEMISSION_MANIFEST.json",
        "expected_schema": "twin_state/1.1",
        "kind": "reemitted",
        "description": "versioned re-emission of the archived forecast table with per-output provenance; no model executed",
    },
    "archived": {
        "artifact": "outputs/twin/as_of_{as_of}/twins.jsonl",
        "digest": "outputs/twin/as_of_{as_of}/FORECAST_SHA256.txt",
        "manifest": None,
        "expected_schema": "twin_state/1.0",
        "kind": "original_archive",
        "description": "historical archived twin state; no per-output provenance",
    },
}
_LINE_ID = re.compile(rb'^\{"object_id": "(\d+)"')
HORIZON_KEYS = (("30d", 30.0, "p_30d"), ("90d", 90.0, "p_90d"), ("1yr", 365.25, "p_365d"))
_REL = 1e-9
_ABS = 1e-9


class TwinSourceError(RuntimeError):
    """No twin-state source could be selected under the policy; the message carries every reason."""


# ------------------------------------------------------------------------- candidates and selection
def _first_token(path: Path) -> str | None:
    try:
        parts = path.read_text(encoding="utf-8").split()
    except OSError:
        return None
    return parts[0] if parts and re.fullmatch(r"[0-9a-f]{64}", parts[0]) else None


def count_lines(path: Path) -> int:
    n = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            n += chunk.count(b"\n")
        if path.stat().st_size and not _ends_with_newline(path):
            n += 1
    return n


def _ends_with_newline(path: Path) -> bool:
    with path.open("rb") as fh:
        fh.seek(-1, 2)
        return fh.read(1) == b"\n"


def _peek_first_record(path: Path) -> tuple[dict | None, str | None]:
    with path.open("rb") as fh:
        line = fh.readline()
    if not line.strip():
        return None, "archive is present but holds no records (first line empty)"
    try:
        rec = json.loads(line)
    except ValueError as exc:
        return None, f"first line is not valid JSON: {exc}"
    return rec, None


def evaluate_candidate(root: Path, name: str, as_of: str,
                       digest_fn: Callable[[Path], str] | None = None) -> dict[str, Any]:
    """Everything that can be said about one candidate archive without reading every record."""
    spec = CANDIDATES[name]
    rel = spec["artifact"].format(as_of=as_of)
    path = Path(root) / rel
    out: dict[str, Any] = {
        "source": name, "kind": spec["kind"], "description": spec["description"], "artifact": rel,
        "expected_schema": spec["expected_schema"], "present": path.is_file(), "size_bytes": None,
        "recorded_sha256": None, "computed_sha256": None, "digest_state": "absent", "schema_version": None,
        "schema_supported": None, "record_count": None, "recorded_record_count": None, "record_count_state": "unknown",
        "provenance_complete": False, "artifact_provenance_complete": False, "provenance_on_outputs": False,
        "transformation_digest_sha256": None, "method": None, "code_revision": None,
        "predictions_regenerated": None, "model_executed": None,
        "model_version": {"status": "unavailable", "digest": None, "reason": "no fitted model is persisted; none is inferred"},
        "status": "missing", "reasons": [], "warnings": [],
    }
    if not out["present"]:
        out["reasons"].append(f"{rel} is not present in this checkout")
        return out
    out["size_bytes"] = path.stat().st_size
    digest_path = Path(root) / spec["digest"].format(as_of=as_of)
    out["recorded_sha256"] = _first_token(digest_path) if digest_path.is_file() else None
    out["computed_sha256"] = (digest_fn or sha256_file)(path)
    if out["recorded_sha256"] is None:
        out["digest_state"] = "unrecorded"
        out["warnings"].append(f"no recorded SHA-256 for {rel} ({spec['digest'].format(as_of=as_of)} absent or malformed)")
    elif out["recorded_sha256"] == out["computed_sha256"]:
        out["digest_state"] = "verified"
    else:
        out["digest_state"] = "MISMATCH"
        out["reasons"].append(f"SHA-256 of {rel} ({out['computed_sha256'][:12]}…) differs from the recorded digest "
                              f"({out['recorded_sha256'][:12]}…)")
    if out["size_bytes"] == 0:
        out["reasons"].append(f"{rel} is present but empty (0 bytes): an empty archive is not a missing one, and not a valid one")
        out["record_count"] = 0
    else:
        out["record_count"] = count_lines(path)
        rec, err = _peek_first_record(path)
        if err:
            out["reasons"].append(err)
        elif isinstance(rec, dict):
            version = rec.get("schema_version") or "twin_state/1.0"
            out["schema_version"] = version
            short = version.split("/", 1)[1] if version.startswith("twin_state/") else None
            out["schema_supported"] = short in ACCEPTED["twin_state"]
            if not out["schema_supported"]:
                out["reasons"].append(f"schema {version!r} is not supported (accepted: "
                                      f"{', '.join('twin_state/' + v for v in ACCEPTED['twin_state'])})")
            elif version != spec["expected_schema"]:
                out["warnings"].append(f"first record is {version}, expected {spec['expected_schema']} for this archive")
            try:
                validate_twin_record(rec)
            except SchemaError as exc:
                out["reasons"].append(f"first record fails twin_state validation: {exc}")
        else:
            out["reasons"].append("first line is not a JSON object")
    man_rel = spec["manifest"].format(as_of=as_of) if spec["manifest"] else None
    manifest = None
    if man_rel and (Path(root) / man_rel).is_file():
        try:
            manifest = json.loads((Path(root) / man_rel).read_text(encoding="utf-8"))
        except ValueError as exc:
            out["warnings"].append(f"{man_rel} is not valid JSON: {exc}")
    if isinstance(manifest, dict):
        out["transformation_digest_sha256"] = manifest.get("transformation_digest_sha256")
        out["method"] = manifest.get("method")
        out["code_revision"] = manifest.get("code_revision")
        out["predictions_regenerated"] = manifest.get("predictions_regenerated")
        out["model_executed"] = manifest.get("model_executed")
        mv = manifest.get("model_version")
        if isinstance(mv, dict) and mv.get("status") == "recorded" and mv.get("digest"):
            out["model_version"] = {"status": "recorded", "digest": mv["digest"], "reason": None}
        out["recorded_record_count"] = (manifest.get("output") or {}).get("records")
        recorded_out = (manifest.get("output") or {}).get("twins_jsonl_sha256")
        if recorded_out and out["computed_sha256"] and recorded_out != out["computed_sha256"]:
            out["reasons"].append(f"re-emission manifest records twins.jsonl SHA-256 {recorded_out[:12]}…, file hashes to "
                                  f"{out['computed_sha256'][:12]}…")
        if manifest.get("predictions_regenerated") is True or manifest.get("model_executed") is True:
            out["warnings"].append("re-emission manifest claims regeneration or model execution; this reader does not accept "
                                   "that claim as evidence of a model version")
    elif name == "reemitted":
        out["warnings"].append(f"{man_rel} absent: transformation digest, method and code revision are unavailable")
    if out["recorded_record_count"] is not None and out["record_count"] is not None:
        out["record_count_state"] = "matches" if out["recorded_record_count"] == out["record_count"] else "MISMATCH"
        if out["record_count_state"] == "MISMATCH":
            out["reasons"].append(f"{out['record_count']} records in file, {out['recorded_record_count']} recorded in the manifest")
    # artifact-level provenance: digest verified, schema known, and (for a re-emission) transformation digest,
    # method and code revision recorded. Output-level provenance exists only in twin_state/1.1 records.
    out["artifact_provenance_complete"] = bool(
        out["digest_state"] == "verified" and out["schema_version"] and
        (name == "archived" or (out["transformation_digest_sha256"] and out["code_revision"] and out["method"])))
    out["provenance_on_outputs"] = name == "reemitted" and out["schema_version"] == "twin_state/1.1"
    out["provenance_complete"] = bool(out["artifact_provenance_complete"] and out["provenance_on_outputs"])
    if name == "archived" and not out["reasons"]:
        out["warnings"].append("twin_state/1.0 records carry no per-output provenance; lineage is by value only")
    out["status"] = "invalid" if out["reasons"] else "valid"
    return out


def select_source(root: Path, as_of: str, policy: str = DEFAULT_POLICY,
                  digest_fn: Callable[[Path], str] | None = None, evaluate_all: bool = False) -> dict[str, Any]:
    """Choose the archive to read under an explicit policy; record every candidate's verdict and the reason.

    ``status``: ``primary`` (re-emitted 1.1 selected), ``fallback`` (archived 1.0 selected because the
    re-emitted archive was missing or invalid and the policy permits it), ``explicit_archived`` (policy
    asked for 1.0), ``unavailable`` (nothing selectable; reasons listed). Fallback and explicit archived
    reads are never presented as a primary read.
    """
    if policy not in POLICIES:
        raise ValueError(f"unknown twin-source policy {policy!r}; known: {POLICIES}")
    root = Path(root)
    candidates: dict[str, dict[str, Any]] = {}
    sel: dict[str, Any] = {"policy": policy, "selected": None, "status": "unavailable", "fallback_used": False,
                           "fallback_permitted": policy == "prefer_reemitted", "reason": None, "candidates": candidates}
    order = ("archived",) if policy == "archived_only" else ("reemitted", "archived")
    for name in order:
        cand = evaluate_candidate(root, name, as_of, digest_fn)
        candidates[name] = cand
        if cand["status"] == "valid":
            sel["selected"] = name
            if policy == "archived_only":
                sel["status"] = "explicit_archived"
                sel["reason"] = "policy archived_only selects the historical twin_state/1.0 archive explicitly (not a fallback)"
            elif name == "reemitted":
                sel["status"] = "primary"
                sel["reason"] = "re-emitted twin_state/1.1 archive present and valid (preferred source)"
            else:
                sel["status"] = "fallback"; sel["fallback_used"] = True
                why = "; ".join(candidates["reemitted"]["reasons"]) or "re-emitted archive not selectable"
                sel["reason"] = f"re-emitted twin state unavailable ({why}); archived twin_state/1.0 selected as a fallback under policy prefer_reemitted"
            break
        if name == "reemitted" and policy == "reemitted_only":
            sel["reason"] = ("re-emitted archive not selectable (" + "; ".join(cand["reasons"]) +
                             "); fallback to the archived twin_state/1.0 is not permitted by policy reemitted_only")
            candidates["archived"] = {"source": "archived", "status": "not_evaluated",
                                      "reasons": ["fallback not permitted by policy reemitted_only"]}
            break
    if sel["selected"] is None and sel["reason"] is None:
        parts = [f"{n}: {'; '.join(c['reasons']) or c['status']}" for n, c in candidates.items()]
        sel["reason"] = "no twin-state source is selectable — " + " | ".join(parts)
    if evaluate_all:
        for name in CANDIDATES:
            if name not in candidates or candidates[name].get("status") == "not_evaluated":
                candidates[name] = evaluate_candidate(root, name, as_of, digest_fn)
                if policy == "reemitted_only" and name == "archived":
                    candidates[name]["warnings"].append("evaluated for display only; policy reemitted_only never selects it")
    return sel


# ------------------------------------------------------------------------- records
def iter_lines(path: Path) -> Iterator[tuple[int, int, bytes]]:
    """(line number from 1, byte offset, raw line) for every line of a JSONL file."""
    offset = 0
    with path.open("rb") as fh:
        for n, line in enumerate(fh, start=1):
            yield n, offset, line
            offset += len(line)


def _bad_number(v: Any) -> bool:
    return v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))


def record_value_problems(rec: dict[str, Any]) -> list[str]:
    """Values a non-abstaining output must carry but does not (None/NaN/inf): reported, never filled."""
    problems = []
    for i, out in enumerate(rec.get("outputs") or []):
        if out.get("abstain"):
            continue
        vals = out.get("values") or {}
        for key in ("p_reentry_30d", "p_reentry_90d", "p_reentry_1yr"):
            if key not in vals or _bad_number(vals[key]):
                problems.append(f"outputs[{i}].values.{key}")
        for key, v in vals.items():
            if key.startswith("p_") and isinstance(v, (int, float)) and not _bad_number(v) and not 0.0 <= v <= 1.0:
                problems.append(f"outputs[{i}].values.{key} out of [0, 1]")
    return problems


def validate_archive(path: Path, max_examples: int = 5,
                     on_record: Callable[[dict[str, Any], int, int, int], None] | None = None) -> dict[str, Any]:
    """Stream every record once: schema, identity uniqueness, malformed lines, value problems.

    ``on_record(record, line_no, offset, length)`` is called for each syntactically valid record so a caller
    can build an index or compare values in the same pass without holding the archive in memory.
    """
    seen: dict[str, int] = {}
    out: dict[str, Any] = {"records_total": 0, "records_valid": 0, "records_malformed_json": 0, "records_schema_invalid": 0,
                           "records_with_value_problems": 0, "duplicate_identities": 0, "unique_identities": 0,
                           "schema_versions": {}, "examples": {"malformed": [], "schema_invalid": [], "duplicates": [], "value_problems": []},
                           "status": "ok"}
    for n, offset, line in iter_lines(path):
        if not line.strip():
            continue
        out["records_total"] += 1
        try:
            rec = json.loads(line)
        except ValueError as exc:
            out["records_malformed_json"] += 1
            if len(out["examples"]["malformed"]) < max_examples:
                out["examples"]["malformed"].append({"line": n, "error": str(exc)[:160]})
            continue
        version = (rec.get("schema_version") if isinstance(rec, dict) else None) or "twin_state/1.0"
        out["schema_versions"][version] = out["schema_versions"].get(version, 0) + 1
        try:
            validate_twin_record(rec)
        except SchemaError as exc:
            out["records_schema_invalid"] += 1
            if len(out["examples"]["schema_invalid"]) < max_examples:
                out["examples"]["schema_invalid"].append({"line": n, "object_id": rec.get("object_id") if isinstance(rec, dict) else None,
                                                          "error": str(exc)[:160]})
            continue
        oid = rec["object_id"]
        if oid in seen:
            out["duplicate_identities"] += 1
            if len(out["examples"]["duplicates"]) < max_examples:
                out["examples"]["duplicates"].append({"object_id": oid, "first_line": seen[oid], "line": n})
        else:
            seen[oid] = n
        problems = record_value_problems(rec)
        if problems:
            out["records_with_value_problems"] += 1
            if len(out["examples"]["value_problems"]) < max_examples:
                out["examples"]["value_problems"].append({"object_id": oid, "fields": problems[:6]})
        out["records_valid"] += 1
        if on_record is not None:
            on_record(rec, n, offset, len(line))
    out["unique_identities"] = len(seen)
    issues = out["records_malformed_json"] or out["records_schema_invalid"] or out["duplicate_identities"] or out["records_with_value_problems"]
    out["status"] = "issues" if issues else ("empty" if out["records_total"] == 0 else "ok")
    return out


# ------------------------------------------------------------------------- equivalence with the catalogue chain
def _norm(v: Any) -> Any:
    """NaN and None both encode 'unavailable' (the chain converts NaN to None, the twin keeps NaN)."""
    return None if isinstance(v, float) and math.isnan(v) else v


def _close(a: Any, b: Any) -> bool:
    a, b = _norm(a), _norm(b)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=_REL, abs_tol=_ABS)
    return a == b


def _monotone_ok(values: list[float | None]) -> bool:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return len(vals) == len(values) and all(x <= y for x, y in zip(vals, vals[1:]))


def _twin_output(rec: dict[str, Any], module: str) -> dict[str, Any] | None:
    for out in rec.get("outputs") or []:
        if out.get("module") == module:
            return out
    return None


def compare_record(rec: dict[str, Any], chain: dict[str, Any] | None) -> dict[str, Any]:
    """Compare one twin record with the catalogue chain's view of the same object.

    ``chain`` is the dictionary produced by ``chain_view_from_outputs`` / ``chain_view_from_tables``; None
    means the object is not in the chain. Fields whose semantics differ are reported as not comparable
    with the reason — never forced equal, never forced different.
    """
    oid = str(rec.get("object_id"))
    res: dict[str, Any] = {"object_id": oid, "status": None, "fields_compared": 0, "fields_equal": 0,
                           "fields_different": [], "not_comparable": {}, "differences": {}}
    if chain is None:
        res["status"] = "missing_in_chain"
        res["not_comparable"]["*"] = "object not present in the catalogue chain of this run"
        return res

    def cmp(field: str, a: Any, b: Any) -> None:
        res["fields_compared"] += 1
        if _close(a, b):
            res["fields_equal"] += 1
        else:
            res["fields_different"].append(field)
            if len(res["differences"]) < 8:
                res["differences"][field] = {"twin": a, "chain": b}

    cmp("name", rec.get("name"), chain.get("name"))
    cmp("regime", rec.get("regime"), chain.get("regime"))
    cmp("object_class", rec.get("object_class"), chain.get("object_class"))
    orbit = rec.get("orbit") or {}
    cmp("orbit.perigee_km", orbit.get("perigee_km"), chain.get("perigee_km"))
    cmp("orbit.apogee_km", orbit.get("apogee_km"), chain.get("apogee_km"))
    cmp("orbit.inc_deg", orbit.get("inc_deg"), chain.get("inc_deg"))
    cmp("physical.mass_kg", (rec.get("physical") or {}).get("mass_kg"), chain.get("mass_kg"))

    # re-entry: twin output "reentry" vs the chain's reentry module
    tw = _twin_output(rec, "reentry")
    ch = chain.get("reentry")
    if tw is None:
        res["not_comparable"]["reentry"] = "twin record has no reentry output"
    elif ch is None:
        res["not_comparable"]["reentry"] = "chain has no reentry record and no recorded abstention for this object"
    else:
        twin_abstains, chain_abstains = bool(tw.get("abstain")), bool(ch.get("abstained"))
        controlled_c3 = twin_abstains and not chain_abstains and rec.get("regime") == "operator_controlled"
        if controlled_c3:
            # Known representation difference, not a value difference: the twin state marks operator-controlled
            # payloads as abstaining (C3) and attaches the payload base-rate probabilities; the chain's reentry
            # module records those same forecast-table probabilities as a prediction with the regime as an
            # assumption. The flag is therefore not comparable; the probabilities are, and are compared below.
            res["not_comparable"]["reentry.abstained"] = ("twin marks operator-controlled objects as abstaining (C3) with base-rate "
                                                          "values attached; the chain records a prediction with the regime as an "
                                                          "assumption — representations differ, values are compared")
        else:
            cmp("reentry.abstained", twin_abstains, chain_abstains)
        if chain_abstains or (twin_abstains and not controlled_c3):
            res["not_comparable"]["reentry.values"] = ("chain abstained: " + str(ch.get("reason")) if chain_abstains
                                                      else "twin abstained (" + str(tw.get("reason"))[:80] + "); the chain holds a prediction")
        else:
            vals, p = tw.get("values") or {}, ch.get("p") or {}
            for key, _days, _col in HORIZON_KEYS:
                cmp(f"reentry.p_{key}", vals.get(f"p_reentry_{key}"), p.get(key))
            lo_hi = (tw.get("uncertainty") or {}).get("interval90_days")
            raw = [lo_hi[0] if lo_hi else None, vals.get("median_days"), lo_hi[1] if lo_hi else None]
            if ch.get("quantiles") is None:
                res["not_comparable"]["reentry.time_quantiles"] = str(ch.get("quantiles_reason") or "chain has no time quantiles for this object")
            elif not _monotone_ok(raw):
                res["not_comparable"]["reentry.time_quantiles"] = ("twin holds the raw quantiles, which are not monotone; the chain "
                                                                  "applies monotone ordering — semantics differ")
            else:
                q = ch["quantiles"]
                cmp("reentry.days_q05", raw[0], q[0]); cmp("reentry.days_q50", raw[1], q[1]); cmp("reentry.days_q95", raw[2], q[2])

    # lifetime: twin output "reentry-comparison" (D/R/C uncontrolled objects only) vs the chain's lifetime module
    tl = _twin_output(rec, "reentry-comparison")
    cl = chain.get("lifetime")
    if tl is None and (cl is None or cl.get("abstained")):
        pass                                             # no lifetime value on either side: nothing to compare
    elif tl is None:
        res["not_comparable"]["lifetime"] = ("twin_state/1.x emits the lifetime comparison output only for uncontrolled "
                                             "D/R/C objects; the chain's lifetime estimate for this object has no twin counterpart")
    elif cl is None:
        res["not_comparable"]["lifetime"] = "chain has no lifetime record and no recorded abstention for this object"
    elif cl.get("abstained"):
        res["not_comparable"]["lifetime"] = "chain lifetime abstained: " + str(cl.get("reason"))
    else:
        vals, p = tl.get("values") or {}, cl.get("p") or {}
        for key, _days, _col in HORIZON_KEYS:
            cmp(f"lifetime.p_{key}", vals.get(f"p_reentry_{key}"), p.get(key))
        lo_hi = (tl.get("uncertainty") or {}).get("interval90_days")
        raw = [lo_hi[0] if lo_hi else None, vals.get("median_days"), lo_hi[1] if lo_hi else None]
        if cl.get("quantiles") is None:
            res["not_comparable"]["lifetime.quantiles"] = str(cl.get("quantiles_reason") or "chain has no lifetime quantiles")
        elif not _monotone_ok(raw):
            res["not_comparable"]["lifetime.quantiles"] = ("twin holds the raw quantiles, which are not monotone; the chain applies "
                                                          "monotone ordering — semantics differ")
        else:
            q = cl["quantiles"]
            cmp("lifetime.days_q05", raw[0], q[0]); cmp("lifetime.days_q50", raw[1], q[1]); cmp("lifetime.days_q95", raw[2], q[2])

    if res["fields_different"]:
        res["status"] = "different"
    elif res["fields_compared"]:
        res["status"] = "equal"
    else:
        res["status"] = "not_comparable"
    return res


class EquivalenceAccumulator:
    """Running summary of compare_record results; keeps counts and a few examples, never the records."""

    def __init__(self, chain_ids: set[str], max_examples: int = 5):
        self.chain_ids = set(chain_ids)
        self.seen: set[str] = set()
        self.max_examples = max_examples
        self.counts = {"twin_records": 0, "records_compared": 0, "records_equal": 0, "records_different": 0,
                       "records_not_comparable": 0, "records_missing_in_chain": 0, "records_missing_in_twin": 0,
                       "fields_compared": 0, "fields_equal": 0, "fields_different": 0}
        self.not_comparable_reasons: dict[str, int] = {}
        self.different_fields: dict[str, int] = {}
        self.examples: dict[str, list] = {"different": [], "not_comparable": [], "missing_in_chain": []}

    def add(self, result: dict[str, Any]) -> None:
        c = self.counts
        c["twin_records"] += 1
        self.seen.add(result["object_id"])
        c["fields_compared"] += result["fields_compared"]; c["fields_equal"] += result["fields_equal"]
        c["fields_different"] += len(result["fields_different"])
        for f in result["fields_different"]:
            self.different_fields[f] = self.different_fields.get(f, 0) + 1
        for f, why in result["not_comparable"].items():
            key = f"{f}: {why}"
            self.not_comparable_reasons[key] = self.not_comparable_reasons.get(key, 0) + 1
        st = result["status"]
        if st == "missing_in_chain":
            c["records_missing_in_chain"] += 1
            if len(self.examples["missing_in_chain"]) < self.max_examples:
                self.examples["missing_in_chain"].append(result["object_id"])
            return
        if st == "not_comparable":
            c["records_not_comparable"] += 1
            if len(self.examples["not_comparable"]) < self.max_examples:
                self.examples["not_comparable"].append({"object_id": result["object_id"], "reasons": result["not_comparable"]})
            return
        c["records_compared"] += 1
        if st == "equal":
            c["records_equal"] += 1
        else:
            c["records_different"] += 1
            if len(self.examples["different"]) < self.max_examples:
                self.examples["different"].append({"object_id": result["object_id"], "fields": result["fields_different"],
                                                   "differences": result["differences"]})

    def summary(self) -> dict[str, Any]:
        missing_in_twin = sorted(self.chain_ids - self.seen, key=lambda s: (len(s), s))
        self.counts["records_missing_in_twin"] = len(missing_in_twin)
        return {**self.counts, "equivalent": self.counts["records_different"] == 0 and self.counts["records_compared"] > 0,
                "different_fields": dict(sorted(self.different_fields.items(), key=lambda kv: -kv[1])),
                "not_comparable_reasons": dict(sorted(self.not_comparable_reasons.items(), key=lambda kv: -kv[1])),
                "examples": {**self.examples, "missing_in_twin": missing_in_twin[: self.max_examples]},
                "note": ("value equivalence of twin records with the catalogue chain of one run; fields with differing "
                         "semantics are listed as not comparable, not forced equal")}


# ------------------------------------------------------------------------- chain views
def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def chain_view_from_outputs(outputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-object chain view from orchestrator module outputs (catalogue_state, lifetime, reentry)."""
    cat = outputs.get("catalogue_state") or {}
    life = outputs.get("lifetime") or {}
    re_ = outputs.get("reentry") or {}
    view: dict[str, dict[str, Any]] = {}
    for object_id, el in (cat.get("elements") or {}).items():
        oid = object_id.split("-", 1)[1] if object_id.startswith("NORAD-") else object_id
        ch = cat.get("characteristics", {}).get(object_id)
        view[oid] = {"name": cat.get("name", {}).get(object_id), "regime": cat.get("regime", {}).get(object_id),
                     "object_class": cat.get("object_class", {}).get(object_id),
                     "perigee_km": el.perigee_altitude_km, "apogee_km": el.apogee_altitude_km, "inc_deg": el.inclination_deg,
                     "mass_kg": ch.mass_kg if ch is not None else None, "reentry": None, "lifetime": None}
        pred = (re_.get("reentry") or {}).get(object_id)
        if pred is not None:
            q = tuple(v for _, v in pred.time_quantiles_days)
            view[oid]["reentry"] = {"abstained": False, "p": {k: pred.probability_by_horizon.get(d) for k, d, _ in HORIZON_KEYS},
                                    "quantiles": q if len(q) == 3 else None,
                                    "quantiles_reason": None if len(q) == 3 else "chain has no time quantiles for this object (bounds missing or non-positive)"}
        elif object_id in (re_.get("abstained") or {}):
            view[oid]["reentry"] = {"abstained": True, "reason": re_["abstained"][object_id]}
        est = (life.get("lifetime") or {}).get(object_id)
        if est is not None:
            q = tuple(v for _, v in est.quantiles_days)
            view[oid]["lifetime"] = {"abstained": False, "p": {k: est.horizon_probabilities.get(d) for k, d, _ in HORIZON_KEYS},
                                     "quantiles": q if len(q) == 3 else None, "quantiles_reason": None}
        elif object_id in (life.get("abstained") or {}):
            view[oid]["lifetime"] = {"abstained": True, "reason": life["abstained"][object_id]}
    return view


L17_REASON = ("saved per-horizon calibrated probabilities are not monotone across horizons (independent isotonic "
              "calibration per horizon); no coherent CDF available — limitation L17, listed in lifetime_noncoherent_horizons.csv")


def _chain_entry(cat: dict[str, Any], re_row: dict[str, Any] | None, li_row: dict[str, Any] | None,
                 reentry_table_present: bool, lifetime_table_present: bool, noncoherent: bool = False) -> dict[str, Any]:
    """One object's chain view from a catalogue row and its (optional) reentry / lifetime table rows.

    ``noncoherent`` marks an object listed in the run's ``lifetime_noncoherent_horizons.csv``: its lifetime
    abstention then carries the L17 reason instead of the generic "reason not tabulated".
    """
    v = {"name": str(cat["Name"]), "regime": str(cat["regime"]), "object_class": str(cat["type1"]),
         "perigee_km": _f(cat["perigee"]), "apogee_km": _f(cat["apogee"]), "inc_deg": _f(cat["inc"]), "mass_kg": _f(cat["mass"]),
         "reentry": None, "lifetime": None}
    if reentry_table_present:
        if re_row is not None:
            q = (_f(re_row["days_q05"]), _f(re_row["days_q50"]), _f(re_row["days_q95"]))
            has_q = str(re_row.get("uncertainty_kind")) == "quantiles" and None not in q
            v["reentry"] = {"abstained": False, "p": {k: _f(re_row[col]) for k, _d, col in HORIZON_KEYS},
                            "quantiles": q if has_q else None,
                            "quantiles_reason": None if has_q else "chain has no time quantiles for this object (bounds missing or non-positive)"}
        else:
            v["reentry"] = {"abstained": True, "reason": "no row in reentry_predictions.csv (abstained in the run; the per-object reason is not tabulated)"}
    if lifetime_table_present:
        if li_row is not None:
            q = (_f(li_row["days_q05"]), _f(li_row["days_q50"]), _f(li_row["days_q95"]))
            v["lifetime"] = {"abstained": False, "p": {k: _f(li_row[col]) for k, _d, col in HORIZON_KEYS},
                             "quantiles": q if None not in q else None,
                             "quantiles_reason": None if None not in q else "lifetime quantiles missing in the table"}
        elif noncoherent:
            v["lifetime"] = {"abstained": True, "reason": L17_REASON}
        else:
            v["lifetime"] = {"abstained": True, "reason": "no row in lifetime_estimates.csv (abstained in the run; the per-object reason is not tabulated)"}
    return v


def chain_view_from_tables(catalogue, ranking, reentry, lifetime, noncoherent=None) -> dict[str, dict[str, Any]]:
    """Per-object chain view from a run's tables plus the catalogue frame (the chain's own input).

    ``ranking`` defines the run's object universe (decision_ranking.csv); ``reentry`` / ``lifetime`` are the
    run's reentry_predictions.csv / lifetime_estimates.csv frames (None when the run did not write them).
    Abstentions are not tabulated per object by the pipeline, so an object absent from a table is recorded as
    abstained with that stated reason.
    """
    universe = set(ranking["object_id"].astype(str)) if ranking is not None else None
    re_rows = {str(r["object_id"]): r for r in reentry.to_dict(orient="records")} if reentry is not None else None
    li_rows = {str(r["object_id"]): r for r in lifetime.to_dict(orient="records")} if lifetime is not None else None
    nc_ids = set(noncoherent["object_id"].astype(str)) if noncoherent is not None else set()
    cols = ["norad", "Name", "regime", "type1", "perigee", "apogee", "inc", "mass"]
    view: dict[str, dict[str, Any]] = {}
    for row in catalogue[cols].to_dict(orient="records"):
        norad = int(row["norad"])
        object_id = f"NORAD-{norad}"
        if universe is not None and object_id not in universe:
            continue
        view[str(norad)] = _chain_entry(row, re_rows.get(object_id) if re_rows is not None else None,
                                        li_rows.get(object_id) if li_rows is not None else None,
                                        re_rows is not None, li_rows is not None, object_id in nc_ids)
    return view


def chain_view_for_object(cat_row: dict[str, Any] | None, in_universe: bool, re_row: dict[str, Any] | None,
                          li_row: dict[str, Any] | None, reentry_table_present: bool, lifetime_table_present: bool,
                          noncoherent: bool = False) -> dict[str, Any] | None:
    """Single-object form of ``chain_view_from_tables`` built from scalar row lookups (same entry builder)."""
    if cat_row is None or not in_universe:
        return None
    return _chain_entry(cat_row, re_row, li_row, reentry_table_present, lifetime_table_present, noncoherent)
