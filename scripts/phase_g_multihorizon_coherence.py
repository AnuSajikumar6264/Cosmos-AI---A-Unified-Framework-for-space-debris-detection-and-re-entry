"""Phase G+: is a coherent multi-horizon reading as well calibrated as the incoherent one?

Limitation L17 records that the saved per-horizon **isotonic-calibrated** probabilities
(`p_lifetime_{30d,90d,1yr}`) are not a coherent CDF, because each horizon is calibrated by an
independent isotonic regressor. The decision not to recalibrate stands (decision 2 in the
master log), and this script does not change it.

It asks a different, answerable question: the study **already** computes a second reading,
`p_lifetime_raw_*`, by reading probabilities off the monotone quantile function. That reading
is coherent across horizons **by construction**. Is it also as well calibrated?

If it is, the practical recommendation is simply to report the coherent reading, requiring no
recalibration and no change to any published artifact.

Outcomes come from the T1 window (as-of 2026-08-16, follow-up 2026-10-27), which is **not
blind** -- so this is exploratory evidence, and the event counts are small (29 at 30 days, 64
at 72 days). Both facts bound the conclusion and are reported.

    python scripts/phase_g_multihorizon_coherence.py --n-boot 4000

No published artifact is modified.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402
from scripts.phase_e_coupling_ablations import paired_cluster_bootstrap  # noqa: E402

T1 = "outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz"
HORIZONS = ("30d", "72d")
SEED = 20261027


def _metrics(y: np.ndarray, p: np.ndarray) -> dict:
    """Brier, calibration-in-the-large and discrimination.

    At an event rate near 0.002 the Brier score is dominated by the true negatives, so
    calibration-in-the-large (expected vs observed event count) is the more informative
    calibration summary and is reported alongside it.
    """
    from cosmos.ai.evaluation import brier_score, expected_calibration_error
    record = {
        "n": int(len(y)),
        "events": int(y.sum()),
        "event_rate": float(y.mean()),
        "mean_p": float(p.mean()),
        "expected_events": float(p.sum()),
        "expected_over_observed": (float(p.sum() / y.sum()) if y.sum() else None),
        "brier": float(brier_score(y, p)),
        "ece": float(expected_calibration_error(y, p)),
    }
    if 0 < y.sum() < len(y) and np.ptp(p) > 0:
        from sklearn.metrics import average_precision_score, roc_auc_score
        record["auc_roc"] = float(roc_auc_score(y, p))
        record["auc_pr"] = float(average_precision_score(y, p))
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/phase_g_multihorizon")
    parser.add_argument("--n-boot", type=int, default=4000)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    path = root / T1
    if not path.is_file():
        raise SystemExit(f"T1 outcomes are not present: {T1}")
    table = pd.read_csv(path)

    needed = [f"p_lifetime_{h}" for h in HORIZONS] + \
             [f"p_lifetime_raw_{h}" for h in HORIZONS] + \
             [f"y_{h}" for h in HORIZONS] + ["launch"]
    frame = table[needed].dropna().reset_index(drop=True)
    clusters = frame["launch"].astype(str).to_numpy()

    print("Phase G+ -- multi-horizon coherence vs calibration (T1 outcomes, exploratory)")
    print(f"  objects with lifetime predictions: {len(frame)}")

    # ---- coherence: how often does each reading violate P(<=30d) <= P(<=72d)?
    coherence = {}
    for reading, prefix in (("isotonic", "p_lifetime"), ("coherent_raw", "p_lifetime_raw")):
        a = frame[f"{prefix}_30d"].to_numpy()
        b = frame[f"{prefix}_72d"].to_numpy()
        violations = int((a > b).sum())
        coherence[reading] = {
            "violations": violations,
            "violation_fraction": float(violations / len(frame)),
            "max_drop": float(np.max(a - b)) if violations else 0.0,
        }
        print(f"  {reading:14s} cross-horizon violations: {violations} "
              f"({100 * violations / len(frame):.2f}%), max drop "
              f"{coherence[reading]['max_drop']:.4f}")

    # ---- calibration and discrimination per horizon
    per_horizon, contrasts, rows = {}, [], []
    for horizon in HORIZONS:
        y = frame[f"y_{horizon}"].to_numpy().astype(float)
        iso = frame[f"p_lifetime_{horizon}"].to_numpy()
        raw = frame[f"p_lifetime_raw_{horizon}"].to_numpy()
        per_horizon[horizon] = {"isotonic": _metrics(y, iso), "coherent_raw": _metrics(y, raw)}

        # Paired Brier difference, resampled by launch. Negative = the coherent reading is better.
        difference = (raw - y) ** 2 - (iso - y) ** 2
        record = paired_cluster_bootstrap(difference, clusters, args.n_boot, seed=SEED)
        record.update({
            "horizon": horizon,
            "contrast": "coherent_raw minus isotonic (Brier)",
            "verdict": ("COHERENT READING BETTER" if record["ci95_hi"] < 0
                        else "ISOTONIC BETTER" if record["ci95_lo"] > 0
                        else "INCONCLUSIVE"),
        })
        contrasts.append(record)

        print(f"\n  horizon {horizon}: {int(y.sum())} events of {len(y)} "
              f"(rate {y.mean():.5f})")
        for name in ("isotonic", "coherent_raw"):
            m = per_horizon[horizon][name]
            print(f"    {name:14s} brier={m['brier']:.3e} ece={m['ece']:.5f} "
                  f"mean_p={m['mean_p']:.5f} exp/obs={m['expected_over_observed']:.2f} "
                  f"auc_roc={m.get('auc_roc', float('nan')):.4f}")
            rows.append({"horizon": horizon, "reading": name, **m})
        print(f"    paired Brier delta {record['mean']:+.3e} "
              f"CI [{record['ci95_lo']:+.3e}, {record['ci95_hi']:+.3e}] "
              f"p={record['p_value']:.4f} -> {record['verdict']}")

    # ---- recommendation
    any_worse = any(c["verdict"] == "ISOTONIC BETTER" for c in contrasts)
    recommendation = (
        "REPORT THE COHERENT READING" if not any_worse else
        "KEEP THE ISOTONIC READING (the coherent reading is significantly worse somewhere)")
    print(f"\n  RECOMMENDATION: {recommendation}")

    record = {
        "phase": "G+ multi-horizon coherence",
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "artifact": T1,
        "artifact_sha256": sha256_file(path),
        "n_boot": args.n_boot,
        "seed": SEED,
        "exploratory": True,
        "exploratory_note": ("T1 is not a blind window and the event counts are small "
                             "(29 at 30 d, 64 at 72 d); this is exploratory evidence"),
        "n_objects": int(len(frame)),
        "n_launches": int(pd.unique(clusters).size),
        "coherence": coherence,
        "per_horizon": per_horizon,
        "contrasts": contrasts,
        "recommendation": recommendation,
        "l17_note": ("the L17 decision not to recalibrate stands; this analysis changes no "
                     "published probability and only compares two readings the study already "
                     "computes"),
        "not_established": [
            "low event counts limit the power of the Brier comparison",
            "T1 is non-blind, so this cannot confirm the recommendation",
            "the 1-year horizon has no outcome in this window and is not evaluated",
        ],
    }
    with open(out_dir / "multihorizon_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)
    pd.DataFrame(rows).to_csv(out_dir / "multihorizon_metrics.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
