"""Compare a regenerated OPS-SAT study against the archived 2026-10-24 study. Read-only.

    python scripts/opssat_compare_regen.py \
        --regen outputs/benchmarks/telemetry_opssat_regen_20261106

Three things are checked, in this order, because each is a different kind of claim:

  1. The archived study is untouched -- every file's SHA-256 still equals the pin taken before the
     regeneration started (``outputs/audit/opssat_historical_sha256.txt``).
  2. The regenerated per-run table covers the same (protocol, model, train_frac, seed) cells, and
     the per-cell metric differences are reported per model, not hidden in an average. Deterministic
     models (xgboost, logreg, iforest, adaboost, random_forest, cosmos_robust_z) should reproduce to
     numerical precision; deep models ran on a different torch build and device and are expected to
     differ, so for them the question is whether the *ranking* and the *summary* survive.
  3. The per-seed score archive now exists, with the keys ``report.py`` expects.

Nothing is written except the comparison report under ``--regen``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "outputs/benchmarks/telemetry_opssat"
PIN = ROOT / "outputs/audit/opssat_historical_sha256.txt"
KEYS = ["protocol", "model", "train_frac", "seed"]
METRICS = ["f1", "auc_pr", "auc_roc", "mcc", "precision", "recall", "accuracy",
           "false_alarm_rate", "brier", "ece"]
DETERMINISTIC = {"xgboost", "logreg", "iforest", "adaboost", "random_forest", "cosmos_robust_z"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_archive_untouched() -> list[dict]:
    rows = []
    for line in PIN.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        p = ARCHIVE / name.strip()
        rows.append({"file": name.strip(), "pinned": digest[:16],
                     "now": sha256(p)[:16] if p.is_file() else "MISSING",
                     "untouched": p.is_file() and sha256(p) == digest})
    return rows


def compare_runs(regen: Path, tag: str) -> tuple[pd.DataFrame | None, dict]:
    a_path, b_path = ARCHIVE / f"per_run_{tag}.csv", regen / f"per_run_{tag}.csv"
    if not b_path.is_file():
        return None, {"tag": tag, "status": "regen table missing"}
    a, b = pd.read_csv(a_path), pd.read_csv(b_path)
    m = a.merge(b, on=KEYS, suffixes=("_arch", "_regen"), how="outer", indicator=True)
    cover = m["_merge"].value_counts().to_dict()
    both = m[m["_merge"] == "both"].copy()
    out = []
    for model, g in both.groupby("model"):
        rec = {"tag": tag, "model": model, "cells": len(g),
               "deterministic": model in DETERMINISTIC}
        for met in METRICS:
            if f"{met}_arch" in g and f"{met}_regen" in g:
                d = (g[f"{met}_regen"] - g[f"{met}_arch"]).abs()
                rec[f"{met}_maxabs"] = float(d.max())
        out.append(rec)
    return pd.DataFrame(out), {"tag": tag, "coverage": {str(k): int(v) for k, v in cover.items()}}


def rank_agreement(regen: Path, tag: str) -> dict:
    a, b = ARCHIVE / f"summary_{tag}.csv", regen / f"summary_{tag}.csv"
    if not (a.is_file() and b.is_file()):
        return {"tag": tag, "status": "summary missing"}
    sa, sb = pd.read_csv(a), pd.read_csv(b)
    key = ["protocol", "train_frac", "model"]
    m = sa.merge(sb, on=key, suffixes=("_arch", "_regen"))
    full = m[m.train_frac == 1.0]
    from scipy.stats import spearmanr
    res = {"tag": tag, "n_models_full_frac": int(len(full))}
    for met in ("f1_mean", "auc_pr_mean", "mcc_mean"):
        if f"{met}_arch" in full:
            rho = spearmanr(full[f"{met}_arch"], full[f"{met}_regen"]).statistic
            res[f"spearman_{met}"] = None if np.isnan(rho) else round(float(rho), 4)
            res[f"top_model_{met}_arch"] = str(full.loc[full[f"{met}_arch"].idxmax(), "model"])
            res[f"top_model_{met}_regen"] = str(full.loc[full[f"{met}_regen"].idxmax(), "model"])
    return res


def check_scores(regen: Path, tag: str) -> dict:
    p = regen / f"test_scores_{tag}.npz"
    if not p.is_file():
        return {"tag": tag, "present": False}
    z = np.load(p)
    keys = list(z.files)
    y = z[f"{tag}|y"] if f"{tag}|y" in z else None
    return {"tag": tag, "present": True, "bytes": p.stat().st_size, "n_keys": len(keys),
            "has_y": y is not None, "n_test": int(len(y)) if y is not None else None,
            "n_positive": int(y.sum()) if y is not None else None,
            "score_keys_full_frac": sum(1 for k in keys if k.startswith(f"{tag}|1.0|"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regen", required=True)
    args = ap.parse_args(argv)
    regen = (ROOT / args.regen).resolve()

    report: dict = {"archive": str(ARCHIVE.relative_to(ROOT)), "regen": str(regen.relative_to(ROOT))}
    untouched = check_archive_untouched()
    report["archive_untouched"] = untouched
    ok_arch = all(r["untouched"] for r in untouched)
    print(f"1. archive untouched: {'YES' if ok_arch else 'NO'}  ({sum(r['untouched'] for r in untouched)}/{len(untouched)} files)")

    pd.set_option("display.width", 220)
    for tag in ("official", "time_blocked"):
        df, cov = compare_runs(regen, tag)
        report[f"coverage_{tag}"] = cov
        print(f"\n2. per-run comparison [{tag}]: {cov}")
        if df is not None and len(df):
            show = ["model", "cells", "deterministic"] + [c for c in df.columns if c.endswith("_maxabs")][:6]
            print(df[show].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
            report[f"per_model_{tag}"] = df.to_dict(orient="records")
        ra = rank_agreement(regen, tag)
        report[f"rank_agreement_{tag}"] = ra
        print(f"   rank agreement: {ra}")
        sc = check_scores(regen, tag)
        report[f"scores_{tag}"] = sc
        print(f"3. score archive [{tag}]: {sc}")

    out = regen / "comparison_vs_archive.json"
    out.write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(f"\nwritten {out.relative_to(ROOT)}")
    return 0 if ok_arch else 1


if __name__ == "__main__":
    sys.exit(main())
