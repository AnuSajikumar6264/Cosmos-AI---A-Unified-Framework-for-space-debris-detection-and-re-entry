"""Versioned re-emission of the twin state from the archived forecast table (P1.2, 2026-11-08).

    python -m cosmos.ai.twin.reemit --as-of 2026-10-27            # writes outputs/twin/as_of_<date>_reemitted_v1/

What this is. The archived ``twins.jsonl`` was written by an earlier engine revision and carries no
per-output provenance. This module rebuilds the same records — the same identity, orbit, physical,
family and space-weather fields, the same module outputs with the same values, uncertainty,
validation labels and abstentions — from the archived ``forecast_table.csv.gz`` **without running any
model**, and attaches to every output a provenance record naming the source artifact and its SHA-256,
the code revision and a digest of this transformation. Each record states that it was re-emitted from
archived data; nothing is regenerated and no model version is claimed.

The mapping mirrors ``engine.run`` (the state builder) line for line. Equivalence with the archived
state is checked by value (``compare_with_archive``), and the output is byte-deterministic (no
timestamps inside records; the generation time lives in REEMISSION_MANIFEST.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ...common import output_dir
from ..provenance import ROOT, git_revision, sha256_file
from ..schema import stamp, validate_twin_record
from .state import ModuleOutput, ObjectTwin, OutputProvenance

HORIZONS = {"30d": 30.0, "90d": 90.0, "1yr": 365.25}
CAP_DAYS = 1826.25
METHOD = "cosmos.ai.twin.reemit.emit_records v1 (row-wise mapping of forecast_table.csv.gz; no model executed)"
SOURCES = (
    "CelesTrak SATCAT snapshot {as_of}",
    "GCAT catalogue snapshot",
    "CelesTrak SW-All observed values",
    "GCAT/CelesTrak lifetime training and calibration data",
)
# Labels identical to the engine's (imported lazily to avoid pulling the learner stack at import time).


def _labels():
    from . import engine as E
    return E.VALIDATION, E.VALIDATION_T1, E.VARIANT_LABEL


def _opt_str(v):
    return None if (v is None or (isinstance(v, float) and np.isnan(v))) else str(v)


def _empty_if_nan(v):
    return "" if (isinstance(v, float) and np.isnan(v)) else v


def _date_str(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and not v.strip()):
        return None
    return str(pd.Timestamp(v).date())


def transformation_digest(as_of: str) -> str:
    """SHA-256 of the canonical description of the mapping (constants, labels, method, schema)."""
    validation, validation_t1, variant_label = _labels()
    spec = {"method": METHOD, "schema_version": stamp("twin_state"), "horizons": HORIZONS, "cap_days": CAP_DAYS,
            "csv_round_trip_normalisation": {"family.breakup_parent": "NaN -> '' (engine held empty strings)"},
            "sources": [s.format(as_of=as_of) for s in SOURCES], "validation": validation,
            "validation_t1": validation_t1, "variant_label": variant_label}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def emit_records(table: pd.DataFrame, as_of: str, source_relative: str, source_sha256: str,
                 code_revision: str | None, digest: str):
    """Yield one versioned twin record per forecast-table row, in table order."""
    validation, validation_t1, variant_label = _labels()
    sources = tuple(s.format(as_of=as_of) for s in SOURCES)
    hashes = {source_relative: source_sha256}
    for i, row in enumerate(table.itertuples(index=False)):
        r = row._asdict()
        tw = ObjectTwin(object_id=str(int(r["norad"])), name=str(r["Name"]), object_class=r["type1"], as_of=as_of,
                        orbit={"perigee_km": r["perigee"], "apogee_km": r["apogee"], "inc_deg": r["inc"],
                               "canonical_epoch": _date_str(r["t0_canonical"])},
                        physical={"mass_kg": r["mass"], "area_to_mass_source": r["am_source"], "rcs_m2": r["rcs_m2"]},
                        operational_status=_opt_str(r["ops_status"]),
                        # CSV round-trip normalisation: the engine held an empty string for "no breakup parent";
                        # the archived CSV reads that back as NaN. Restored to "" so values match the archive.
                        family={"launch": r["launch_family"], "breakup_parent": _empty_if_nan(r["breakup_family"]),
                                "breakup_siblings_decayed": float(r["breakup_family_n_decayed"])},
                        space_weather={"f107_last81": r["f107_last81"], "ap_last81": r["ap_last81"]})
        reg, unc_i = r["regime"], r["type1"] in ("D", "R", "C")
        prov = OutputProvenance(as_of=as_of, input_sources=sources, input_hashes=hashes,
                                code_revision=code_revision, config_digest=digest)
        vals = {f"p_reentry_{k}": float(r[f"p_{k}"]) for k in HORIZONS}
        if reg == "operator_controlled":
            vals.update({f"drag_only_p_reentry_{k}": float(r[f"p_physics_prior_{k}"]) for k in HORIZONS})
            base_prov = OutputProvenance(as_of=as_of, input_sources=sources + ("previous-window CelesTrak SATCAT snapshots",),
                                         input_hashes=hashes, code_revision=code_revision, config_digest=digest)
            tw.attach(ModuleOutput("reentry", "previous-window payload base rate", validation["payload_controlled"], vals, {},
                                   abstain=True,
                                   reason="operational payload: operator-controlled regime, drag physics does not determine re-entry (C3)",
                                   provenance=base_prov))
        else:
            vals.update({"median_days": float(r["median_days"]), "capped_at_days": CAP_DAYS})
            unc_d = {"interval80_days": [float(r["lo80_days"]), float(r["hi80_days"])],
                     "interval90_days": [float(r["lo90_days"]), float(r["hi90_days"])],
                     "interval_kind": "physics Monte-Carlo quantiles (not conformalised)"}
            if unc_i:
                unc_d.update({"history_kind": r["history_kind"], "history_ess": float(r["history_ess"])})
                tw.attach(ModuleOutput("reentry", variant_label["physics_history"], validation_t1, vals, unc_d, provenance=prov))
                tw.attach(ModuleOutput("reentry-comparison", variant_label["lifetime"], validation["uncontrolled"],
                                       {f"p_reentry_{k}": float(r[f"p_lifetime_{k}"]) for k in HORIZONS} |
                                       {"median_days": float(r["median_days_lifetime"])},
                                       {"interval90_days": [float(r["lifetime_lo90_days"]), float(r["lifetime_hi90_days"])],
                                        "interval_kind": "Mondrian CQR"}, provenance=prov))
            else:
                tw.attach(ModuleOutput("reentry", variant_label["physics_prior"],
                                       validation["payload_natural" if reg == "natural_decay" else "payload_unknown"],
                                       vals, unc_d, provenance=prov))
        rec = tw.to_dict()
        rec["schema_version"] = stamp("twin_state")
        rec["source_record"] = {"artifact": source_relative, "sha256": source_sha256, "row_index": i, "norad": int(r["norad"])}
        rec["reemitted_from_archive"] = True
        rec["reemission_method"] = METHOD
        yield rec


_STRIP = ("schema_version", "source_record", "reemitted_from_archive", "reemission_method")


def canonical(record: dict, drop_provenance: bool = False) -> str:
    rec = {k: v for k, v in record.items() if k not in _STRIP}
    if drop_provenance:
        rec = {**rec, "outputs": [{**o, "provenance": None} for o in rec["outputs"]]}
    return json.dumps(rec, sort_keys=True, default=float)


def compare_with_archive(new_path: Path, archive_path: Path) -> dict:
    """Value equivalence of the re-emitted state with the archived one (provenance excluded)."""
    n = equal = 0
    first_diff = None
    with new_path.open() as fn, archive_path.open() as fa:
        for line_n, line_a in zip(fn, fa):
            n += 1
            a, b = canonical(json.loads(line_a), drop_provenance=True), canonical(json.loads(line_n), drop_provenance=True)
            if a == b:
                equal += 1
            elif first_diff is None:
                first_diff = {"line": n, "archived": a[:300], "reemitted": b[:300]}
        extra_new = sum(1 for _ in fn)
        extra_arch = sum(1 for _ in fa)
    return {"records_compared": n, "records_equal": equal, "records_differing": n - equal,
            "extra_in_reemitted": extra_new, "extra_in_archive": extra_arch, "first_difference": first_diff,
            "equivalent": (n - equal == 0 and extra_new == 0 and extra_arch == 0)}


def run(as_of: str = "2026-10-27", version: str = "v1", out: str | None = None) -> dict:
    src_dir = Path(output_dir("twin", f"as_of_{as_of}"))
    src = src_dir / "forecast_table.csv.gz"
    relative = str(src.relative_to(ROOT))
    sha = sha256_file(src)
    archive = src_dir / "twins.jsonl"
    archive_sha_before = sha256_file(archive) if archive.is_file() else None
    od = Path(out) if out else Path(output_dir("twin", f"as_of_{as_of}_reemitted_{version}"))
    od.mkdir(parents=True, exist_ok=True)
    if od.resolve() == src_dir.resolve():
        raise SystemExit("refusing to write into the archived twin directory")
    table = pd.read_csv(src, low_memory=False)
    git = git_revision(ROOT)["git_commit"]
    digest = transformation_digest(as_of)
    out_path = od / "twins.jsonl"
    n = 0
    with out_path.open("w") as f:
        for rec in emit_records(table, as_of, relative, sha, git, digest):
            validate_twin_record(rec)
            f.write(json.dumps(rec, default=float) + "\n")
            n += 1
    out_sha = sha256_file(out_path)
    (od / "TWINS_SHA256.txt").write_text(f"{out_sha}  twins.jsonl\n")
    equivalence = compare_with_archive(out_path, archive) if archive.is_file() else {"equivalent": None, "note": "archive absent"}
    manifest = {
        "artifact": "re-emitted twin state", "schema_version": stamp("twin_state"), "reemitted_from_archive": True,
        "predictions_regenerated": False, "model_executed": False,
        "model_version": {"status": "unavailable", "digest": None,
                          "reason": "no fitted model is persisted; the values are the archived forecast's, re-emitted"},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": METHOD, "transformation_digest_sha256": digest, "code_revision": git,
        "source": {"artifact": relative, "sha256": sha, "rows": int(len(table))},
        "archived_state": {"artifact": str(archive.relative_to(ROOT)), "sha256_before": archive_sha_before,
                           "sha256_after": sha256_file(archive) if archive.is_file() else None,
                           "digest_file": (src_dir / "FORECAST_SHA256.txt").read_text().split()[0] if (src_dir / "FORECAST_SHA256.txt").is_file() else None},
        "output": {"directory": str(od.relative_to(ROOT)) if od.is_relative_to(ROOT) else str(od), "twins_jsonl_sha256": out_sha, "records": n},
        "equivalence_with_archive": equivalence,
        "distinguishing_fields": list(_STRIP) + ["outputs[].provenance (non-null)"],
    }
    (od / "REEMISSION_MANIFEST.json").write_text(json.dumps(manifest, indent=1, default=str) + "\n")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of", default="2026-10-27")
    ap.add_argument("--version", default="v1")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    m = run(a.as_of, a.version, a.out)
    print(json.dumps({k: m[k] for k in ("output", "equivalence_with_archive", "archived_state")}, indent=1, default=str))
    return 0 if m["equivalence_with_archive"].get("equivalent") in (True, None) else 1


if __name__ == "__main__":
    sys.exit(main())
