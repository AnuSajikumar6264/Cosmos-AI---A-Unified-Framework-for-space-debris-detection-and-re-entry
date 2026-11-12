"""Hash every file created or modified for the three authorised Phase 8 analyses (2026-11-08).

    python scripts/phase8_approved_analyses_manifest.py

Writes outputs/audit/phase8_approved_analyses_manifest.json: path, bytes, sha256, mtime for each
declared file, plus the protected-artifact verification record written after execution.
"""
from __future__ import annotations

import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATED = [
    "scripts/verify_protected_artifacts.py", "scripts/e6_opssat_branch_analysis.py", "scripts/am_design_stage1.py", "scripts/cluster_logit.py",
    "scripts/track3b_stage2_cells.py", "scripts/phase8_approved_analyses_manifest.py",
    "tests/test_e6_branch.py", "tests/test_am_design_stage1.py", "tests/test_track3b_stage2.py",
    "docs/research/PHASE8_GATE_ADDENDUM_2026-11-08.md", "docs/research/PHASE8_APPROVED_ANALYSES_REPORT_2026-11-08.md",
]
MODIFIED = ["docs/research/MASTER_COMPLETION_TRACKER.md", "docs/research/PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md"]
OUTPUT_DIRS = ["outputs/e6_opssat_branch", "outputs/am_design_stage1", "outputs/benchmarks/telemetry_esa_adb/track3b_stage2"]
PROTECTED_UNCHANGED = ["outputs/audit/phase8_acceptance_gate.json", "docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md",
                       "outputs/benchmarks/telemetry_esa_adb/oof/m1_target_ar8/folds.json", "outputs/benchmarks/telemetry_esa_adb/posthoc_v2/p1_decompose/m1_target_conformal_bh.json",
                       "outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json", "paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md"]


def rec(p: Path) -> dict:
    if not p.is_file():
        return {"path": str(p.relative_to(ROOT)), "present": False}
    return {"path": str(p.relative_to(ROOT)), "present": True, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")}


def main() -> int:
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "created": [rec(ROOT / p) for p in CREATED], "modified_living_documents": [rec(ROOT / p) for p in MODIFIED],
           "outputs": {d: [rec(p) for p in sorted((ROOT / d).rglob("*")) if p.is_file() and p.suffix != ".npy"] for d in OUTPUT_DIRS},
           "large_regenerated_arrays_not_hashed_individually": {d: [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size} for p in sorted((ROOT / d).rglob("*.npy"))] for d in OUTPUT_DIRS},
           "protected_unchanged": [rec(ROOT / p) for p in PROTECTED_UNCHANGED],
           "after_verification_records": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "outputs/audit").glob("protected_artifacts_*x4_x6_x10_*.json"))}
    (ROOT / "outputs/audit/phase8_approved_analyses_manifest.json").write_text(json.dumps(out, indent=1) + "\n")
    n = sum(1 for c in out["created"] if c["present"]) + sum(len(v) for v in out["outputs"].values())
    print(f"manifest: {n} files hashed -> outputs/audit/phase8_approved_analyses_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
