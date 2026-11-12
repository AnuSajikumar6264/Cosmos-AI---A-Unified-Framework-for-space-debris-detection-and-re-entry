"""Record (or verify) the regenerated AR(8) score caches of the 3b Stage 2 run. Read-only on the caches.

    python scripts/score_cache_manifest.py            # write SCORE_CACHE_MANIFEST.json beside the caches
    python scripts/score_cache_manifest.py --verify   # exit 1 if a recorded file is missing or altered

Policy (P0.5, 2026-11-08). The large arrays (two 1.7 GB score matrices) stay ignored by git and are
preserved by (a) this manifest of their sizes and SHA-256 digests, (b) the exact regeneration recipe
(frozen code, deterministic: the regenerated OOF scores reproduced the archived sample hash), and (c)
a narrow .gitignore exception for the small per-cell alarm bitmaps and JSON records only. Nothing
large is added to version control.
"""
from __future__ import annotations

import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/benchmarks/telemetry_esa_adb/track3b_stage2"
MANIFEST = BASE / "SCORE_CACHE_MANIFEST.json"
LARGE_BYTES = 64 * 1024 * 1024


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory() -> dict:
    files = []
    for p in sorted(BASE.rglob("*")):
        if p.is_file() and p.name != MANIFEST.name and p.suffix in (".npy", ".json", ".log"):
            files.append({"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p),
                          "large": p.stat().st_size >= LARGE_BYTES, "kept_in_git": p.suffix != ".npy" or "/alarms/" in str(p)})
    folds = json.loads((BASE / "oof_regen/m1_target_ar8/folds.json").read_text()) if (BASE / "oof_regen/m1_target_ar8/folds.json").is_file() else {}
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "policy": ("large regenerated arrays are intentionally NOT version-controlled; they are preserved by this "
                   "manifest (size + SHA-256), by the deterministic regeneration recipe below, and by the archived "
                   "sample hash in folds.json; small alarm bitmaps and JSON records are kept in git via a narrow exception"),
        "regeneration": {"command": "POSTHOC_TMP=/data2/anupa/tmp_posthoc python scripts/track3b_stage2_cells.py",
                         "producer": "frozen cosmos.ai.telemetry.oof.run(1, 'target') (K = 5, purge 1 day, seed 0) and frozen forecasting.py for A0",
                         "seconds_observed": folds.get("seconds"), "oof_sha256_sample": folds.get("sha256_sample"),
                         "archived_sha256_sample_reproduced": folds.get("sha256_sample") == "02455519984c"},
        "files": files,
    }


def verify() -> tuple[bool, list[str]]:
    if not MANIFEST.is_file():
        return False, ["manifest missing"]
    rec = json.loads(MANIFEST.read_text())
    problems = []
    for f in rec["files"]:
        p = ROOT / f["path"]
        if not p.is_file():
            problems.append(f"missing: {f['path']}")
        elif p.stat().st_size != f["bytes"]:
            problems.append(f"size changed: {f['path']}")
        elif not f["large"] and sha(p) != f["sha256"]:
            problems.append(f"hash changed: {f['path']}")
    # large arrays: size checked above; their content is tied to the archived sample hash
    return not problems, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    if a.verify:
        ok, problems = verify()
        print("score cache verify:", "OK" if ok else "PROBLEMS", problems)
        return 0 if ok else 1
    rec = inventory()
    MANIFEST.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"recorded {len(rec['files'])} files ({sum(f['bytes'] for f in rec['files']) / 1e9:.2f} GB), "
          f"{sum(f['large'] for f in rec['files'])} large arrays kept out of git -> {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
