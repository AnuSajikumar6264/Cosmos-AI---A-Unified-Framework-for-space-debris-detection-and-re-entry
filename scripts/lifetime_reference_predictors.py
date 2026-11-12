"""Trivial reference predictors and per-arm cluster-bootstrap intervals for the lifetime leaderboard.

    python scripts/lifetime_reference_predictors.py --n-boot 4000

Re-derives, with archived artifacts, a result that `docs/publication/SECONDARY_A_…` §1 reports in
prose only ("computed from archived predictions and the cohort; no model fitted") and that has no
output file behind it. Nothing is fitted here either; the point is that the numbers now come from a
script whose inputs are hashed and whose outputs are written down.

Endpoint, as published: pinball loss averaged over the seven quantile levels in
``cosmos.ai.lifetime.models.QUANTILES`` of ``z = log10(min(time_days, 1826.25))``, on test objects
whose five-year outcome is known (``known5``). Per-object losses for every published arm come from
``test_predictions.npz`` through ``scripts.e3_e5_selection_analysis.load_origin``, so the arms are
scored by exactly the code the earlier analyses used.

Reference predictors (feature-free, scored on the same objects with the same function):
  * ``constant_at_cap``            every quantile at the cap -- "nothing decays in five years";
  * ``train_marginal_quantiles``   the training split's own marginal quantiles of z (honest);
  * ``test_marginal_quantiles``    the TEST split's marginal quantiles -- an ORACLE no predictor
                                   could know; the best any feature-free predictor could do.
Intervals: cluster bootstrap by launch family (``n_boot`` draws, seed 20261027), the unit used
throughout the lifetime study. Outputs go to ``outputs/lifetime_reference_predictors/``.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.e3_e5_selection_analysis import (ORIGIN_2006_SPLIT, ORIGINS, SEED,  # noqa: E402
                                              load_origin, pinball_per_object)
from cosmos.ai.lifetime import models as MO  # noqa: E402
from cosmos.ai.lifetime import run as LR  # noqa: E402
from cosmos.ai.provenance import git_revision  # noqa: E402

OUT = ROOT / "outputs/lifetime_reference_predictors"

# The prose claim under test (SECONDARY_A §1, 2026-11-05). Kept here as the thing being checked,
# not as an input to any computation.
DOCUMENTED = {
    "2011": {"constant_at_cap": 0.172892, "train_marginal_quantiles": 0.231209,
             "test_marginal_quantiles": 0.133180, "best": ("physics_only", 0.052676),
             "worst": ("mlp", 0.114661)},
    "2016": {"constant_at_cap": 0.232879, "train_marginal_quantiles": 0.200591,
             "test_marginal_quantiles": 0.146946, "best": ("tabicl", 0.049944),
             "worst": ("physics_only", 0.089249)},
}


def cluster_bootstrap_means(losses: dict[str, np.ndarray], families: np.ndarray,
                            n_boot: int, seed: int) -> dict[str, tuple[float, float, float]]:
    """Mean loss with a percentile 95 % interval, resampling launch families with replacement."""
    codes, inv = np.unique(families, return_inverse=True)
    n_fam = len(codes)
    counts = np.bincount(inv, minlength=n_fam).astype(float)
    sums = {k: np.bincount(inv, weights=v, minlength=n_fam) for k, v in losses.items()}
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_fam, size=(n_boot, n_fam))
    out = {}
    for k, s in sums.items():
        boot = np.empty(n_boot)
        for b in range(n_boot):
            mult = np.bincount(draws[b], minlength=n_fam)
            boot[b] = float((s * mult).sum() / (counts * mult).sum())
        lo, hi = np.percentile(boot, [2.5, 97.5])
        out[k] = (float(losses[k].mean()), float(lo), float(hi))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=4000)
    ap.add_argument("--origins", default="2011,2016,2006")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    cohort = LR.load_cohort()
    rows, checks = [], {}
    for origin in args.origins.split(","):
        arena = load_origin(ROOT, origin)
        if arena is None:
            print(f"origin {origin}: archive missing, skipped")
            continue
        if origin not in LR.ORIGINS:
            LR.ORIGINS[origin] = ORIGIN_2006_SPLIT
        train = LR.split(cohort, origin, "uncontrolled")["train"]
        z_train = train.loc[train["known5"], "z"].to_numpy(float)
        z = arena["z"]
        n = len(z)
        trivial = {
            "constant_at_cap": np.full((n, len(MO.QUANTILES)), np.log10(LR.CAP)),
            "train_marginal_quantiles": np.tile(np.quantile(z_train, MO.QUANTILES), (n, 1)),
            "test_marginal_quantiles": np.tile(np.quantile(z, MO.QUANTILES), (n, 1)),
        }
        losses = dict(arena["losses"])
        losses.update({k: pinball_per_object(z, q) for k, q in trivial.items()})
        stats = cluster_bootstrap_means(losses, arena["families"], args.n_boot, SEED)

        published = {k: v for k, v in stats.items() if k not in trivial}
        best = min(published, key=lambda k: published[k][0])
        worst = max(published, key=lambda k: published[k][0])
        oracle = stats["test_marginal_quantiles"][0]
        for arm, (m, lo, hi) in sorted(stats.items(), key=lambda kv: kv[1][0]):
            rows.append({"origin": origin, "arm": arm,
                         "kind": "trivial_reference" if arm in trivial else "published_arm",
                         "mean_pinball": m, "ci95_lo": lo, "ci95_hi": hi,
                         "beats_oracle": bool(m < oracle) if arm not in trivial else None,
                         "margin_over_oracle_pct": (1 - m / oracle) * 100 if arm not in trivial else None,
                         "n_objects": n, "n_families": arena["n_families"],
                         "n_train_known5": int(len(z_train)),
                         "artifact": arena["artifact"], "artifact_sha256": arena["sha256"]})
        doc = DOCUMENTED.get(origin)
        check = {"n_objects": n, "n_families": arena["n_families"],
                 "every_published_arm_beats_oracle": all(published[k][0] < oracle for k in published),
                 "worst_arm": worst, "worst_margin_over_oracle_pct": (1 - published[worst][0] / oracle) * 100,
                 "best_arm": best, "best_margin_over_oracle_pct": (1 - published[best][0] / oracle) * 100,
                 "trivial": {k: stats[k][0] for k in trivial}}
        if doc:
            check["documented_vs_rederived"] = {
                **{k: {"documented": doc[k], "rederived": stats[k][0],
                       "abs_diff": abs(doc[k] - stats[k][0])} for k in trivial},
                "best": {"documented": doc["best"], "rederived": (best, published[best][0])},
                "worst": {"documented": doc["worst"], "rederived": (worst, published[worst][0])},
            }
        checks[origin] = check
        print(f"\norigin {origin}: n={n} families={arena['n_families']} train_known5={len(z_train)}")
        for k in trivial:
            m, lo, hi = stats[k]
            tag = f"  (documented {doc[k]:.6f})" if doc else ""
            print(f"  {k:26s} {m:.6f} [{lo:.6f}, {hi:.6f}]{tag}")
        print(f"  best  {best:14s} {published[best][0]:.6f}   worst {worst:14s} {published[worst][0]:.6f}")
        print(f"  every published arm beats the oracle: {check['every_published_arm_beats_oracle']}  "
              f"(worst margin {check['worst_margin_over_oracle_pct']:.1f} %, best {check['best_margin_over_oracle_pct']:.1f} %)")

    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "leaderboard_with_intervals.csv", index=False)
    (OUT / "reference_predictor_results.json").write_text(json.dumps({
        "analysed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_revision(), "n_boot": args.n_boot, "seed": SEED,
        "endpoint": "mean pinball over MO.QUANTILES of z=log10(min(t,1826.25)), known5 test objects",
        "cluster_unit": "launch_family", "refitting_performed": False,
        "frozen_artifacts_modified": False, "origins": checks,
        "note": ("origin 2006 is the G5d confirmatory origin; its arms are the two refit learners "
                 "plus the stored baselines, so its leaderboard is not comparable in breadth"),
    }, indent=1, default=str) + "\n")
    print(f"\nwritten {OUT.relative_to(ROOT)}/leaderboard_with_intervals.csv ({len(frame)} rows), "
          f"reference_predictor_results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
