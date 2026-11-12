"""Why the three re-entry variants disagree by ~10x, and which is closest to what was observed.

    python scripts/reentry_variant_decomposition.py --n-boot 4000

The twin computes three readings of P(re-entry within h) for every uncontrolled object (classes
D, R, C) and reports one of them. On the 2026-10-27 snapshot their expected 30-day counts are
21.6 (physics_history), 76.3 (physics_prior) and 229.1 (lifetime, isotonic-calibrated) -- a 10.6x
spread. This script does three things, read-only on every input:

  A. **Decompose** the disagreement on the 2026-10-27 snapshot (no outcomes exist yet): which
     objects carry the lifetime variant's excess over physics_history -- by catalogue-history
     kind, by time already survived, by area-to-mass source, by class and by perigee band.
     Also adds the fourth reading the summary omits: the coherent ``p_lifetime_raw_*``.
  B. **Compare to observation** on the T1 window (as-of 2026-08-16, follow-up to 2026-10-27),
     where outcomes ``y_30d``/``y_72d`` exist: expected vs observed events per variant, with a
     cluster-bootstrap interval on the ratio (resampling launches), Brier per variant, and the
     same decomposition against observed events per bin. T1 is **not blind** and has 29 / 64
     events, so this is exploratory evidence, stated as such.
  C. **Record the assumptions** that differ between the variants, from the engine's own
     documentation, so a reader can see which modelling choice each number rests on.

Modelled expected counts and observed events are never mixed in one column.
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
from cosmos.ai.provenance import git_revision, sha256_file  # noqa: E402

SNAPSHOT = ROOT / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"
T1 = ROOT / "outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz"
OUT = ROOT / "outputs/reentry_variant_decomposition"
UNCONTROLLED = ("D", "R", "C")
VARIANTS = {"physics_history": "p_physics_history_{h}", "physics_prior": "p_physics_prior_{h}",
            "lifetime_isotonic": "p_lifetime_{h}", "lifetime_coherent_raw": "p_lifetime_raw_{h}"}

ASSUMPTIONS = {
    "physics_prior": ("NRLMSIS 2.1 density table (globally averaged, as a function of altitude, "
                      "F10.7, Ap); area-to-mass drawn from class priors fitted on the training "
                      "split; F10.7 and Ap held at the trailing-81-day value at the as-of date, "
                      "identical for every object; Monte-Carlo over 32 A/m draws"),
    "physics_history": ("as physics_prior, but the area-to-mass distribution is the posterior "
                        "conditioned on the object's own catalogue decay history (it has survived "
                        "since its canonical orbit); the twin's pre-fixed choice for uncontrolled "
                        "objects"),
    "lifetime_isotonic": ("gated learned quantile model (tabm) fitted at canonical-orbit epochs on "
                          "the forward-in-time cohort; horizon probabilities read off the quantile "
                          "function, then re-mapped by an independent isotonic calibrator per "
                          "horizon (L17: not a coherent CDF; 123 violations); does not condition "
                          "on survival to the as-of date"),
    "lifetime_coherent_raw": ("the same learned quantile function read directly, without the "
                              "per-horizon isotonic step; coherent across horizons by construction"),
}


def bins_history_days(x: pd.Series) -> pd.Series:
    edges = [-np.inf, 0, 365, 1826.25, 3652.5, 7305, np.inf]
    labels = ["none", "<1 yr", "1-5 yr", "5-10 yr", "10-20 yr", ">20 yr"]
    return pd.cut(x.fillna(0), bins=edges, labels=labels, right=True)


def bins_perigee(x: pd.Series) -> pd.Series:
    return pd.cut(x, bins=[0, 300, 400, 500, 600, 800, 2000], right=False,
                  labels=["<300", "300-400", "400-500", "500-600", "600-800", "800-2000"])


def decompose(df: pd.DataFrame, h: str, observed: str | None) -> pd.DataFrame:
    """Per-bin expected counts for every variant (and observed events where available)."""
    d = df.copy()
    d["history_days_bin"] = bins_history_days(d["history_days"])
    d["perigee_band"] = bins_perigee(d["perigee"])
    rows = []
    for key in ("history_kind", "history_days_bin", "am_source", "type1", "perigee_band"):
        for level, g in d.groupby(key, observed=True):
            row = {"horizon": h, "stratum": key, "level": str(level), "n": int(len(g))}
            for v, col in VARIANTS.items():
                row[f"expected_{v}"] = float(np.nansum(g[col.format(h=h)]))
            row["excess_isotonic_minus_history"] = row["expected_lifetime_isotonic"] - row["expected_physics_history"]
            if observed:
                row["observed_events"] = int(g[observed].sum())
            rows.append(row)
    out = pd.DataFrame(rows)
    tot = out.groupby(["horizon", "stratum"])["excess_isotonic_minus_history"].transform("sum")
    out["share_of_excess"] = out["excess_isotonic_minus_history"] / tot
    return out


def ratio_bootstrap(p: np.ndarray, y: np.ndarray, clusters: np.ndarray, n_boot: int, seed: int):
    codes, inv = np.unique(clusters, return_inverse=True)
    sp = np.bincount(inv, weights=np.nan_to_num(p), minlength=len(codes))
    sy = np.bincount(inv, weights=y, minlength=len(codes))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(codes), size=(n_boot, len(codes)))
    ratios = np.empty(n_boot)
    for b in range(n_boot):
        m = np.bincount(draws[b], minlength=len(codes))
        obs = (sy * m).sum()
        ratios[b] = (sp * m).sum() / obs if obs > 0 else np.nan
    ratios = ratios[np.isfinite(ratios)]
    return float(np.nanpercentile(ratios, 2.5)), float(np.nanpercentile(ratios, 97.5))


def part_a(n_boot: int, seed: int) -> dict:
    t = pd.read_csv(SNAPSHOT, low_memory=False)
    unc = t[t["type1"].isin(UNCONTROLLED) & t["p_lifetime_30d"].notna()].copy()
    res = {"n_uncontrolled_with_lifetime_reading": int(len(unc)), "expected_counts": {}}
    for h in ("30d", "90d", "1yr"):
        res["expected_counts"][h] = {v: float(np.nansum(unc[col.format(h=h)])) for v, col in VARIANTS.items()}
    e30 = res["expected_counts"]["30d"]
    res["ratio_isotonic_to_history_30d"] = e30["lifetime_isotonic"] / e30["physics_history"]
    res["ratio_coherent_to_history_30d"] = e30["lifetime_coherent_raw"] / e30["physics_history"]
    dec = pd.concat([decompose(unc, h, None) for h in ("30d", "90d", "1yr")])
    dec.to_csv(OUT / "snapshot_2026-10-27_decomposition.csv", index=False)
    top = (dec[dec.horizon == "30d"].sort_values("excess_isotonic_minus_history", ascending=False)
           .groupby("stratum").head(2))
    res["largest_contributors_to_excess_30d"] = top[["stratum", "level", "n", "expected_physics_history",
                                                     "expected_lifetime_isotonic", "share_of_excess"]].to_dict(orient="records")
    # how much of the isotonic-vs-history gap is the isotonic step itself?
    res["isotonic_step_share_of_gap_30d"] = float(
        (e30["lifetime_isotonic"] - e30["lifetime_coherent_raw"]) / (e30["lifetime_isotonic"] - e30["physics_history"]))
    return res


def part_b(n_boot: int, seed: int) -> dict:
    t = pd.read_csv(T1, low_memory=False)
    unc = t[t["type1"].isin(UNCONTROLLED) & t["p_lifetime_30d"].notna()].copy()
    res = {"as_of": "2026-08-16", "follow_up": "2026-10-27", "n_uncontrolled": int(len(unc)),
           "exploratory": True,
           "why_exploratory": "T1 outcomes were analysed before (not blind); 29 and 64 events only",
           "by_horizon": {}}
    rows = []
    for h, ycol in (("30d", "y_30d"), ("72d", "y_72d")):
        d = unc[unc[ycol].notna()].copy()
        y = d[ycol].to_numpy(float)
        obs = int(y.sum())
        per = {}
        for v, col in VARIANTS.items():
            p = d[col.format(h=h)].to_numpy(float)
            exp = float(np.nansum(p))
            lo, hi = ratio_bootstrap(p, y, d["launch"].astype(str).to_numpy(), n_boot, seed)
            brier = float(np.nanmean((np.nan_to_num(p) - y) ** 2))
            per[v] = {"expected": exp, "observed": obs, "ratio_expected_over_observed": exp / obs,
                      "ratio_ci95": [lo, hi], "brier": brier, "n": int(len(d))}
            rows.append({"horizon": h, "variant": v, **per[v]})
        res["by_horizon"][h] = per
        dec = decompose(d, h, ycol)
        dec.to_csv(OUT / f"t1_decomposition_{h}.csv", index=False)
    pd.DataFrame(rows).to_csv(OUT / "t1_observed_vs_expected.csv", index=False)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-boot", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20261027)
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    a = part_a(args.n_boot, args.seed)
    b = part_b(args.n_boot, args.seed)
    report = {"analysed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "git": git_revision(), "n_boot": args.n_boot, "seed": args.seed,
              "inputs": {str(SNAPSHOT.relative_to(ROOT)): sha256_file(SNAPSHOT),
                         str(T1.relative_to(ROOT)): sha256_file(T1)},
              "frozen_artifacts_modified": False, "refitting_performed": False,
              "A_snapshot_2026-10-27": a, "B_t1_observed_vs_expected": b, "C_assumptions": ASSUMPTIONS}
    (OUT / "results.json").write_text(json.dumps(report, indent=1, default=str) + "\n")

    e = a["expected_counts"]["30d"]
    print("A. snapshot 2026-10-27, uncontrolled with lifetime reading:", a["n_uncontrolled_with_lifetime_reading"])
    print("   expected 30-day re-entries: " + ", ".join(f"{k}={v:.1f}" for k, v in e.items()))
    print(f"   isotonic/history = {a['ratio_isotonic_to_history_30d']:.1f}x   coherent/history = "
          f"{a['ratio_coherent_to_history_30d']:.1f}x   isotonic step share of gap = {a['isotonic_step_share_of_gap_30d']:.2f}")
    print("   largest contributors to the isotonic-vs-history excess (30 d):")
    for r in a["largest_contributors_to_excess_30d"][:8]:
        print(f"     {r['stratum']:17s} {r['level']:16s} n={r['n']:6d}  history={r['expected_physics_history']:6.1f}  "
              f"isotonic={r['expected_lifetime_isotonic']:6.1f}  share={r['share_of_excess']:.2f}")
    print("\nB. T1 window (exploratory): expected vs OBSERVED")
    for h, per in b["by_horizon"].items():
        for v, r in per.items():
            print(f"   {h} {v:22s} expected {r['expected']:6.1f}  observed {r['observed']:3d}  "
                  f"ratio {r['ratio_expected_over_observed']:5.2f} [{r['ratio_ci95'][0]:.2f}, {r['ratio_ci95'][1]:.2f}]  brier {r['brier']:.5f}")
    print(f"\nwritten {OUT.relative_to(ROOT)}/results.json and 5 CSVs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
