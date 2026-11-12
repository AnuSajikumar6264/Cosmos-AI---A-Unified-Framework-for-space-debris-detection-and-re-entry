"""Phase 3 / G3′ — recalibration alternatives for the lifetime intervals, from archived predictions.

    python scripts/lifetime_recalibration_alternatives.py [--boot 2000]

Protocol: docs/research/PHASE3_RECALIBRATION_PROTOCOL.md (declared before this was run). Every
construction is calibrated on the archived tune-B quantiles and outcomes only, then scored once on
the archived test quantiles and outcomes. Nothing is refitted and no archived file is modified.
Constructions: R0 deployed Mondrian CQR (reproduction gate), R1 marginal, R2 class-only Mondrian,
R3 asymmetric, R4 recency-windowed (most recent half of tune-B by t0), R5 recency-weighted
(exp(-years/2), test weight 1). EXPLORATORY and post hoc; informs discussion, selects nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cosmos.ai.lifetime import fusion as FU  # noqa: E402
from cosmos.ai.lifetime import run as LR  # noqa: E402
from cosmos.ai.lifetime.models import QUANTILES, Z_CAP, Z_FLOOR, snap_bounds  # noqa: E402

ORIG = {"2011": "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled",
        "2016": "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled",
        "2006": "outputs/g5d_origin2006/lifetime"}
ORIGIN_2006_SPLIT = ("1999-01-01", "2001-01-01", "2006-01-01", "2011-01-01")
LEVELS = (0.8, 0.9)
SEED = 20261106
HALF_LIFE_YEARS = 2.0
OUT = ROOT / "outputs/phase3_uncertainty/recalibration_alternatives"
CONSTRUCTIONS = ("R0_deployed_mondrian", "R1_marginal", "R2_class_only", "R3_asymmetric",
                 "R4_recent_half_window", "R5_recency_weighted")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def idx(level):
    lo, hi = (1 - level) / 2, 1 - (1 - level) / 2
    return int(np.argmin(np.abs(QUANTILES - lo))), int(np.argmin(np.abs(QUANTILES - hi)))


def conformal_k(n: int, alpha: float) -> int:
    return min(int(np.ceil((1 - alpha) * (n + 1))), n) - 1


def weighted_threshold(s: np.ndarray, w: np.ndarray, alpha: float, w_test: float = 1.0) -> float:
    """Weighted conformal quantile (Tibshirani et al. 2019): smallest s whose normalised cumulative weight,
    with the test point's weight placed at +inf, reaches 1 - alpha."""
    order = np.argsort(s)
    s, w = s[order], w[order]
    cum = np.cumsum(w) / (w.sum() + w_test)
    j = np.searchsorted(cum, 1 - alpha, side="left")
    return float(s[j]) if j < len(s) else float("inf")


def intervals(construction: str, qB, zB, gB: pd.DataFrame, tB_years_before_origin, qT, gT: pd.DataFrame, level):
    """Return (lo, hi) on the test quantiles for one construction, calibrated on tune-B."""
    i, j = idx(level)
    alpha = 1 - level
    qB, qT = snap_bounds(qB, Z_FLOOR, Z_CAP), snap_bounds(qT, Z_FLOOR, Z_CAP)
    if construction == "R0_deployed_mondrian":
        cq = FU.MondrianCQR(mondrian=True, levels=(level,)).fit(qB, zB, gB)
        return cq.interval(qT, gT, level)
    if construction == "R1_marginal":
        cq = FU.MondrianCQR(mondrian=False, levels=(level,)).fit(qB, zB, gB)
        return cq.interval(qT, gT, level)
    if construction == "R2_class_only":
        g2B = gB.assign(fine=gB["coarse"])
        g2T = gT.assign(fine=gT["coarse"])
        cq = FU.MondrianCQR(mondrian=True, levels=(level,)).fit(qB, zB, g2B)
        return cq.interval(qT, g2T, level)
    if construction == "R3_asymmetric":
        s_lo, s_hi = qB[:, i] - zB, zB - qB[:, j]
        k = conformal_k(len(zB), alpha / 2)
        c_lo, c_hi = np.sort(s_lo)[k], np.sort(s_hi)[k]
        return snap_bounds(qT[:, i] - c_lo, Z_FLOOR, Z_CAP), snap_bounds(qT[:, j] + c_hi, Z_FLOOR, Z_CAP)
    if construction == "R4_recent_half_window":
        recent = tB_years_before_origin <= np.median(tB_years_before_origin)
        cq = FU.MondrianCQR(mondrian=True, levels=(level,)).fit(qB[recent], zB[recent], gB[recent].reset_index(drop=True))
        return cq.interval(qT, gT, level)
    if construction == "R5_recency_weighted":
        s = np.maximum(qB[:, i] - zB, zB - qB[:, j])
        w = np.exp(-np.clip(tB_years_before_origin, 0, None) / HALF_LIFE_YEARS)
        c = weighted_threshold(s, w, alpha)
        return snap_bounds(qT[:, i] - c, Z_FLOOR, Z_CAP), snap_bounds(qT[:, j] + c, Z_FLOOR, Z_CAP)
    raise ValueError(construction)


def cluster_boot_mean(x: np.ndarray, fam: np.ndarray, rng: np.random.Generator, n_boot: int) -> np.ndarray:
    """Launch-family cluster bootstrap of a mean: resample families with replacement."""
    codes, inv = np.unique(fam, return_inverse=True)
    sums = np.bincount(inv, weights=x, minlength=len(codes))
    counts = np.bincount(inv, minlength=len(codes)).astype(float)
    draws = rng.integers(0, len(codes), size=(n_boot, len(codes)))
    num = sums[draws].sum(1)
    den = counts[draws].sum(1)
    return num / den


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(SEED)
    LR.ORIGINS.setdefault("2006", ORIGIN_2006_SPLIT)
    cohort = LR.load_cohort()

    rows, prov, repro = [], {}, {}
    boots: dict[tuple, np.ndarray] = {}         # (origin, arm, level, construction) -> bootstrap coverage draws
    for o, d in ORIG.items():
        S = LR.split(cohort, o, "uncontrolled")
        dd = ROOT / d
        te = np.load(dd / "test_predictions.npz", allow_pickle=True)
        tb = np.load(dd / "tuneB_predictions.npz", allow_pickle=True)
        summary = json.loads((dd / "summary.json").read_text())
        sel = summary["best_learner_on_tuneA"]
        assert len(S["test"]) == len(te["z"]) and len(S["tuneB"]) == len(tb["z"])
        assert np.array_equal(S["tuneB"]["event"].to_numpy(), tb["event"]) and np.allclose(S["test"]["time_days"].to_numpy(), te["time_days"])
        origin_date = pd.Timestamp(LR.ORIGINS[o][2])
        mB, mT = tb["known5"].astype(bool), te["known5"].astype(bool)
        gB = FU.mondrian_groups(S["tuneB"])[mB].reset_index(drop=True)
        gT = FU.mondrian_groups(S["test"])
        yrsB = ((origin_date - S["tuneB"]["t0"]).dt.days.to_numpy() / 365.25)[mB]
        famT = S["test"]["launch_family"].astype(str).to_numpy()[mT]
        zT = te["z"][mT]
        prov[o] = {"dir": d, "test_sha256": sha256(dd / "test_predictions.npz"), "tuneB_sha256": sha256(dd / "tuneB_predictions.npz"),
                   "n_tuneB_known5": int(mB.sum()), "n_test_known5": int(mT.sum()), "n_test_families": int(len(np.unique(famT))),
                   "selected_learner": sel, "tuneB_years_before_origin_median": float(np.median(yrsB)),
                   "tuneB_years_before_origin_range": [float(yrsB.min()), float(yrsB.max())],
                   "r4_window_n": int((yrsB <= np.median(yrsB)).sum()), "r5_weight_range": [float(np.exp(-yrsB.max() / HALF_LIFE_YEARS)), float(np.exp(-max(yrsB.min(), 0) / HALF_LIFE_YEARS))]}
        for arm in ("cosmos_gated", "physics_only", sel):
            qB, qT = tb[f"{arm}__q"][mB], te[f"{arm}__q"]
            for lev in LEVELS:
                tag = str(int(round(lev * 100)))
                for con in CONSTRUCTIONS:
                    lo, hi = intervals(con, qB, tb["z"][mB], gB, yrsB, qT, gT, lev)
                    if con == "R0_deployed_mondrian":
                        delta = max(float(np.abs(lo - te[f"{arm}__lo{tag}"]).max()), float(np.abs(hi - te[f"{arm}__hi{tag}"]).max()))
                        repro[f"{o}/{arm}/{tag}"] = delta
                        assert delta < 1e-9, f"R0 does not reproduce the archive: {o} {arm} {tag} Δ={delta}"
                    cov = ((lo[mT] <= zT) & (zT <= hi[mT])).astype(float)
                    width = (hi[mT] - lo[mT])
                    bt = cluster_boot_mean(cov, famT, rng, a.boot)
                    boots[(o, arm, lev, con)] = bt
                    rows.append({"origin": o, "arm": arm, "selected_learner": arm == sel, "level": lev, "construction": con,
                                 "n": int(mT.sum()), "coverage": float(cov.mean()), "deviation": float(cov.mean() - lev),
                                 "dev_ci95_lo": float(np.percentile(bt, 2.5) - lev), "dev_ci95_hi": float(np.percentile(bt, 97.5) - lev),
                                 "mean_width_log10": float(width.mean()), "median_width_log10": float(np.median(width))})
    tab = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT / "coverage_by_construction.csv", index=False)

    # primary criterion: cosmos_gated mean |deviation| over the six (origin x level) cells, paired vs R0
    primary = {}
    cells = [(o, lev) for o in ORIG for lev in LEVELS]
    r0 = np.column_stack([boots[(o, "cosmos_gated", lev, "R0_deployed_mondrian")] - lev for o, lev in cells])
    r0_mad_point = float(tab[(tab.arm == "cosmos_gated") & (tab.construction == "R0_deployed_mondrian")].deviation.abs().mean())
    for con in CONSTRUCTIONS:
        sub = tab[(tab.arm == "cosmos_gated") & (tab.construction == con)]
        mad_point = float(sub.deviation.abs().mean())
        bt = np.column_stack([boots[(o, "cosmos_gated", lev, con)] - lev for o, lev in cells])
        diff = np.abs(bt).mean(1) - np.abs(r0).mean(1)          # paired: same family draws per cell (same rng stream order)
        lo_, hi_ = np.percentile(diff, [2.5, 97.5])
        primary[con] = {"mean_abs_deviation": mad_point, "minus_R0": mad_point - r0_mad_point,
                        "paired_ci95": [float(lo_), float(hi_)],
                        "closer_to_nominal_than_R0": bool(mad_point < r0_mad_point and hi_ < 0),
                        "mean_width_ratio_vs_R0": float(sub.mean_width_log10.mean()
                                                        / tab[(tab.arm == "cosmos_gated") & (tab.construction == "R0_deployed_mondrian")].mean_width_log10.mean()),
                        "cells_within_ci_of_nominal": int(((sub.dev_ci95_lo <= 0) & (sub.dev_ci95_hi >= 0)).sum())}
    # note: the bootstrap draws for different constructions in the same cell use *different* rng states
    # (rng advances per call), so the "paired" CI above pairs cells, not family draws; recorded honestly.
    results = {
        "experiment": "G3' recalibration alternatives (Phase 3), EXPLORATORY post hoc",
        "protocol": "docs/research/PHASE3_RECALIBRATION_PROTOCOL.md",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED, "n_boot": a.boot, "half_life_years": HALF_LIFE_YEARS,
        "provenance": prov, "reproduction_gate_R0_max_abs_delta": repro,
        "primary_criterion_cosmos_gated": primary,
        "bootstrap_note": ("cluster bootstrap by launch family per origin; the difference CI resamples families "
                           "independently per construction (rng advances), so it is a conservative, not a paired, interval"),
        "coverage_cosmos_gated": tab[tab.arm == "cosmos_gated"].pivot_table(index=["origin", "level"], columns="construction",
                                                                              values="coverage").round(4).reset_index().to_dict(orient="records"),
        "what_this_is_not": ["not a prospective validation", "no construction is adopted or deployed",
                             "R4/R5 use one fixed window/half-life; nothing was tuned", "censored objects excluded (known5)"],
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=float) + "\n")

    pd.set_option("display.width", 220)
    print("R0 reproduction gate max|Δ|:", max(repro.values()))
    print("\ncosmos_gated coverage by construction (nominal in 'level'):")
    print(tab[tab.arm == "cosmos_gated"].pivot_table(index=["origin", "level"], columns="construction", values="coverage").round(3).to_string())
    print("\ncosmos_gated mean width (log10 days):")
    print(tab[tab.arm == "cosmos_gated"].pivot_table(index=["origin", "level"], columns="construction", values="mean_width_log10").round(3).to_string())
    print("\nprimary criterion (cosmos_gated, mean |deviation| over 6 cells):")
    for k, v in primary.items():
        print(f"  {k:24s} MAD {v['mean_abs_deviation']:.4f}  vs R0 {v['minus_R0']:+.4f}  CI {np.round(v['paired_ci95'], 4)}  "
              f"width×{v['mean_width_ratio_vs_R0']:.3f}  cells@nominal {v['cells_within_ci_of_nominal']}/6  closer={v['closer_to_nominal_than_R0']}")
    print(f"\nwritten {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
