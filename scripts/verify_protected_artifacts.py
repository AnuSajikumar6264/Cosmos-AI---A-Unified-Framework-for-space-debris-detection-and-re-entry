"""Verify every protected artifact against its recorded hash and write a dated record.

    python scripts/verify_protected_artifacts.py --label before_x4_x6_x10

Reuses the Phase 8 gate's checks but never rewrites the accepted gate record
(outputs/audit/phase8_acceptance_gate.json, docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md).
Output: outputs/audit/protected_artifacts_<label>_<UTC>.json
"""
from __future__ import annotations

import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.phase8_acceptance_gate import sha, verify_hashes, FORECAST_TABLE_SHA, HEAD_AT_DIRECTIVE  # noqa: E402

#: Commits at which the protected artifacts were verified and the owner accepted the repository state:
#: the directive-C start (78ee339) and the owner-approved checkpoint of all P0–P3-B work (938d514, 2026-11-08).
APPROVED_HEADS = {HEAD_AT_DIRECTIVE, "938d514a9f91988e37b63d25475899632eb370d0"}


def head_is_approved(head: str, approved: set[str] | frozenset[str] = frozenset(APPROVED_HEADS),
                     repo: Path = ROOT) -> tuple[bool, str | None]:
    """HEAD is acceptable when it is an approved checkpoint or a descendant of one (owner-approved 2026-11-08).

    The release commits are approved one at a time and a commit can never carry its own hash, so exact
    membership would fail at every release commit. Descent is established with ``git merge-base --is-ancestor``;
    unrelated branches, orphan commits and unknown or malformed references are rejected (git exits non-zero).
    Artifact drift is caught by the content hashes, never by this predicate.
    Returns ``(ok, approved_commit)`` where ``approved_commit`` is the checkpoint HEAD equals or descends from."""
    if not head or not all(c in "0123456789abcdef" for c in head.lower()) or len(head) < 7:
        return False, None
    if head in approved:
        return True, head
    for base in sorted(approved):
        r = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", base, head],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return True, base
    return False, None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="check")
    a = ap.parse_args(argv)
    rec: dict = {"evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "label": a.label, "checks": {}}
    fz = json.loads((ROOT / "research_design/preregistration/freeze.json").read_text())
    n, bad = verify_hashes(list(fz["sha256"].items()))
    rec["checks"]["esa_adb_freeze_681cc7ddec86"] = {"n": n, "bad": bad}
    conf = json.loads((ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json").read_text())
    fz0 = json.loads((ROOT / f"research_design/preregistration/freeze_{conf['freeze_id']}.json").read_text())
    n0, bad0 = verify_hashes(list(fz0["sha256"].items()))
    rec["checks"]["esa_adb_freeze_original"] = {"freeze_id": conf["freeze_id"], "n": n0, "bad": bad0, "expected_bad": [fz0["document"]]}
    rec["checks"]["confirmatory_sha256"] = sha(ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json")
    g5 = json.loads((ROOT / "outputs/g5d_origin2006/prereg_freeze.json").read_text())
    rec["checks"]["g5d_prereg"] = {"ok": sha(ROOT / g5["preregistration"]) == g5["sha256"]}
    man = json.loads((ROOT / "paper/figures/RELEASE_MANIFEST.json").read_text())
    entries = [(f["formats"][k]["path"], f["formats"][k]["sha256"]) for f in man["figures"] for k in f["formats"]]
    entries += [(s["path"], s["sha256"]) for key in ("source_data", "scripts", "documents", "upstream_artifacts") for s in man[key] if s.get("present")]
    n, bad = verify_hashes(entries)
    rec["checks"]["figure_release_manifest"] = {"n": n, "bad": bad}
    opssat = ROOT / "outputs/benchmarks/telemetry_opssat"
    lines = [ln.split() for ln in (ROOT / "outputs/audit/opssat_historical_sha256.txt").read_text().splitlines() if ln.strip()]
    n, bad = verify_hashes([(str((opssat / name).relative_to(ROOT)), h) for h, name in lines])
    rec["checks"]["opssat_archive"] = {"n": n, "bad": bad}
    twin = ROOT / "outputs/twin/as_of_2026-10-27"
    rec["checks"]["twin"] = {"twins_ok": sha(twin / "twins.jsonl") == (twin / "FORECAST_SHA256.txt").read_text().split()[0],
                             "forecast_table_ok": sha(twin / "forecast_table.csv.gz") == FORECAST_TABLE_SHA}
    rec["checks"]["accepted_gate_record"] = {p: sha(ROOT / p) for p in ("outputs/audit/phase8_acceptance_gate.json", "docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md")}
    rec["checks"]["posthoc_p1_records"] = {p.name: sha(p) for p in sorted((ROOT / "outputs/benchmarks/telemetry_esa_adb/posthoc_v2/p1_decompose").glob("*.json"))}
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    staged = subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True).stdout.split()
    # HEAD may be the directive-era commit, an owner-approved checkpoint, or a commit descending from one of them
    # (the owner-approved release commits of 2026-11-08); anything else is reported.
    head_ok, approved_base = head_is_approved(head)
    rec["git"] = {"head": head, "head_ok": head_ok, "approved_ancestor": approved_base,
                  "approved_heads": sorted(APPROVED_HEADS), "staged": staged}
    ok = (not rec["checks"]["esa_adb_freeze_681cc7ddec86"]["bad"] and set(bad0) == {fz0["document"]} and rec["checks"]["g5d_prereg"]["ok"]
          and not rec["checks"]["figure_release_manifest"]["bad"] and not rec["checks"]["opssat_archive"]["bad"]
          and all(rec["checks"]["twin"].values()) and rec["git"]["head_ok"] and not staged)
    rec["all_protected_ok"] = bool(ok)
    out = ROOT / f"outputs/audit/protected_artifacts_{a.label}_{rec['evaluated_at'].replace(':', '').replace('-', '')}.json"
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rec["checks"].items() if k not in ("posthoc_p1_records", "accepted_gate_record")}, indent=None)[:900])
    print("accepted gate record:", {k: v[:16] for k, v in rec["checks"]["accepted_gate_record"].items()})
    print("all_protected_ok:", rec["all_protected_ok"], "->", out.relative_to(ROOT))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
