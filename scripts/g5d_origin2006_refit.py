"""G5d: fit the published lifetime pipeline at the previously unexamined origin 2006.

This is the project's **first confirmatory experiment**. The test fold
``t0 in [2006-01-01, 2011-01-01)`` has never been constructed or scored in this repository, so
unlike every earlier result it is not post-hoc.

Protocol is fixed in ``research_design/G5D_PREREGISTRATION.md`` and this script refuses to run
if that file has changed since it was hashed into
``outputs/g5d_origin2006/prereg_freeze.json``.

    python scripts/g5d_origin2006_refit.py

``cosmos/ai/lifetime/run.py`` is **not edited**: the origin is injected into ``LR.ORIGINS`` at
runtime. Output goes to a new directory; no existing artifact is touched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

ORIGIN_KEY = "2006"
#: Exactly as pre-registered: (train_end, tune_end, origin, test_end).
ORIGIN_SPLIT = ("1999-01-01", "2001-01-01", "2006-01-01", "2011-01-01")
PREREG = "research_design/G5D_PREREGISTRATION.md"
FREEZE = "outputs/g5d_origin2006/prereg_freeze.json"

#: Pre-registered expected split sizes; a material deviation is reported.
EXPECTED = {"train": 18960, "tuneA": 211, "tuneB": 544, "test": 7281}


def check_preregistration(root: Path) -> dict:
    """Refuse to run if the pre-registration changed after it was hashed."""
    freeze_path = root / FREEZE
    if not freeze_path.is_file():
        raise SystemExit(f"no pre-registration freeze at {FREEZE}; refusing to run")
    record = json.loads(freeze_path.read_text())
    actual = sha256_file(root / PREREG)
    if actual != record["sha256"]:
        raise SystemExit(
            f"pre-registration has changed since it was frozen.\n"
            f"  frozen: {record['sha256']}\n  actual: {actual}\n"
            "Refusing to run: a confirmatory experiment cannot use an edited protocol.")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/g5d_origin2006/lifetime")
    parser.add_argument("--n-samples", type=int, default=32)
    parser.add_argument("--learners", default=None,
                        help="comma-separated learner subset; see G5D_DEVIATIONS.md. "
                             "Omit to use the pre-registered LEARNER_SET.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    record = check_preregistration(root)
    print(f"pre-registration verified: {record['sha256'][:16]}... (frozen {record['frozen_at']})")

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    from cosmos.ai.lifetime import run as LR

    # Inject the origin at runtime. run.py is never modified.
    if ORIGIN_KEY in LR.ORIGINS:
        raise SystemExit(f"origin {ORIGIN_KEY} already exists in run.py; aborting to avoid "
                         "silently changing a published protocol")
    LR.ORIGINS[ORIGIN_KEY] = ORIGIN_SPLIT
    print(f"injected origin {ORIGIN_KEY}: {ORIGIN_SPLIT}")

    # Verify the realised split against the pre-registered expectation.
    split = LR.split(LR.load_cohort(), ORIGIN_KEY, "uncontrolled")
    realised = {name: int(len(frame)) for name, frame in split.items()}
    deviations = {name: {"expected": EXPECTED[name], "realised": realised[name]}
                  for name in EXPECTED if realised.get(name) != EXPECTED[name]}
    print(f"split sizes realised: {realised}")
    if deviations:
        print(f"  DEVIATION from pre-registration: {deviations}")
    else:
        print("  matches the pre-registered sizes exactly")

    # Learner availability check. A learner whose backend is absent cannot be fitted, and
    # silently dropping it would be an undocumented protocol change.
    import importlib
    # Backends verified by reading each learner class body in models.py.
    backends = {"xgboost": "xgboost", "lightgbm": "lightgbm", "catboost": "catboost",
                "mlp": "torch", "tabm": "tabm", "tabicl": "tabicl", "kumo": "sdm"}
    available, missing = [], []
    for learner in LR.LEARNER_SET:
        try:
            importlib.import_module(backends[learner])
            available.append(learner)
        except Exception:
            missing.append(learner)
    print(f"learners available: {available}")
    if missing:
        print(f"learners MISSING (backend not installed): {missing}")

    if args.learners:
        learners = tuple(x.strip() for x in args.learners.split(",") if x.strip())
        unknown = [x for x in learners if x not in LR.LEARNER_SET]
        if unknown:
            raise SystemExit(f"unknown learners: {unknown}")
        unavailable = [x for x in learners if x in missing]
        if unavailable:
            raise SystemExit(f"requested learners are not installed: {unavailable}")
        print(f"DEVIATION: running a reduced learner set {learners} "
              "(see research_design/G5D_DEVIATIONS.md)")
    else:
        if missing:
            raise SystemExit(
                f"the pre-registered learner set cannot be fitted; missing backends for "
                f"{missing}. Either install them or pass --learners explicitly and log the "
                "deviation in research_design/G5D_DEVIATIONS.md.")
        learners = LR.LEARNER_SET

    started = time.time()
    print(f"\nfitting at origin {ORIGIN_KEY} with {len(learners)} learner(s)...", flush=True)
    LR.run(origin=ORIGIN_KEY, population="uncontrolled", n_samples=args.n_samples,
           learners=learners, ablations=True, out=str(out_dir))
    elapsed = time.time() - started

    manifest = {
        "experiment": "G5d",
        "origin": ORIGIN_KEY,
        "origin_split": list(ORIGIN_SPLIT),
        "population": "uncontrolled",
        "confirmatory": True,
        "confirmatory_basis": ("the test fold t0 in [2006-01-01, 2011-01-01) had never been "
                               "constructed or scored in this repository before this run"),
        "preregistration": PREREG,
        "preregistration_sha256": record["sha256"],
        "split_sizes_expected": EXPECTED,
        "split_sizes_realised": realised,
        "deviations": deviations,
        "n_samples": args.n_samples,
        "learners_requested": list(learners),
        "learners_available": available,
        "learners_missing_backends": missing,
        "preregistered_learner_set": list(LR.LEARNER_SET),
        "deviation_logged": "research_design/G5D_DEVIATIONS.md" if missing else None,
        "seeds": list(LR.SEEDS) if hasattr(LR, "SEEDS") else None,
        "elapsed_seconds": round(elapsed, 1),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "output_dir": str(out_dir.relative_to(root)),
        "run_py_edited": False,
        "note": ("origin injected into LR.ORIGINS at runtime; cosmos/ai/lifetime/run.py is "
                 "unmodified"),
    }
    with open(out_dir.parent / "g5d_run_manifest.json", "w") as stream:
        json.dump(manifest, stream, indent=2, default=str)

    print(f"\ncompleted in {elapsed / 60:.1f} min")
    print(f"written: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
