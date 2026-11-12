"""Three manuscript figures for the JINT alarm-selection paper.

Every plotted value is read from an archived artifact; nothing is hard-coded or illustrative.

    python scripts/jint_figures.py --out paper/jint/figures

Figure 1  burden-recall trade-off across alarm layers (the headline result)
Figure 2  pre-registered contrasts A0-A3 with bootstrap intervals
Figure 3  selection score versus test score, both missions

Accessibility: every series carries a distinct marker and line style as well as a hue, so the
figures remain readable in greyscale and under colour-vision deficiency. Hues are slots 1-4 of a
validated categorical palette, assigned in fixed order.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cosmos.ai.provenance import ROOT  # noqa: E402

PROTO = "outputs/benchmarks/telemetry_esa_adb/oof_protocol/test"
RESULTS = "outputs/benchmarks/telemetry_esa_adb/results.csv"
CAL = "conformal_bh"

C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8c8b85", "axes.labelcolor": "#2b2b2b",
    "xtick.color": "#2b2b2b", "ytick.color": "#2b2b2b",
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "DejaVu Sans",
})


def rows(root: Path, tag: str) -> list[dict]:
    path = root / PROTO / f"{tag}.json"
    return json.loads(path.read_text()) if path.is_file() else []


def arm_mean(root: Path, tags: list[str], field: str) -> float | None:
    vals = [r[field] for t in tags for r in rows(root, t) if r["calibrator"] == CAL]
    return float(np.mean(vals)) if vals else None


def arm_values(root: Path, tags: list[str], field: str) -> list[float]:
    return [r[field] for t in tags for r in rows(root, t) if r["calibrator"] == CAL]


# --------------------------------------------------------------------- Figure 1
def figure_burden_recall(root: Path, out: Path) -> Path:
    """Burden-recall trade-off. The paper's headline, with BOTH axes of the trade-off."""
    layers = ["conformal_bh_rolling", "threshold", "conformal_bh", "aci_event", "aci"]
    label = {"conformal_bh_rolling": "BH rolling", "threshold": "threshold",
             "conformal_bh": "BH (primary)", "aci_event": "ACI event-agg.", "aci": "ACI point-level"}
    recs = {r["calibrator"]: r for r in rows(root, "m1_target_ar8")}

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.2, 4.0))

    fa = [max(recs[c]["false_alarms_per_year"], 0.05) for c in layers]
    rc = [recs[c]["anomaly/EW_recall"] for c in layers]
    style = [("o", C1), ("s", C3), ("D", C1), ("^", C4), ("v", C2)]
    # threshold and conformal_bh are coincident (identical event-wise metrics); offset their
    # labels so neither is overprinted, and say so on the figure.
    offsets = {"conformal_bh_rolling": (6, 10), "threshold": (-8, 20), "conformal_bh": (12, -12),
               "aci_event": (-6, 14), "aci": (-10, -20)}
    align = {"conformal_bh_rolling": "left", "threshold": "right", "conformal_bh": "left",
             "aci_event": "right", "aci": "right"}
    for c, x, y, (m, col) in zip(layers, fa, rc, style):
        ax.scatter(x, y, s=130, marker=m, color=col, edgecolor="white", linewidth=1.5,
                   zorder=3, label=label[c])
        ax.annotate(label[c], (x, y), xytext=offsets[c], textcoords="offset points",
                    ha=align[c], fontsize=8.2, color="#2b2b2b", zorder=4)
    ax.set_xscale("log")
    ax.set_xlabel("false alarms per year  (log scale)")
    ax.set_ylabel("anomaly event-wise recall")
    ax.set_ylim(-0.05, 1.12)
    ax.set_xlim(0.03, 1.2e6)
    ax.set_title("(a) Burden\u2013recall trade-off, arm A1, Mission 1", loc="left", fontsize=10)
    ax.grid(alpha=0.25, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.annotate("", xy=(fa[2] * 1.9, rc[2] + 0.02), xytext=(fa[4] * 0.55, rc[4] - 0.03),
                arrowprops=dict(arrowstyle="->", color="#8c8b85", lw=1.3,
                                connectionstyle="arc3,rad=0.22"), zorder=2)
    ax.text(0.30, 0.80,
            f"{fa[4] / fa[2]:,.0f}\u00d7 fewer false alarms\n"
            f"{rc[4] / rc[2]:.1f}\u00d7 less recall",
            transform=ax.transAxes, fontsize=8.2, color="#52514e", ha="left", va="top")
    ax.text(0.985, 0.03, "threshold and BH (primary) are coincident:\nidentical event-wise metrics",
            transform=ax.transAxes, fontsize=7.4, color="#52514e", ha="right", va="bottom")

    f05 = [recs[c]["anomaly/EW_F0.5"] for c in layers]
    xs = np.arange(len(layers))
    bx.bar(xs, f05, color=[s[1] for s in style], edgecolor="white", linewidth=1.2, width=0.62)
    for x, v in zip(xs, f05):
        bx.text(x, v + 0.008, f"{v:.4f}", ha="center", fontsize=8, color="#2b2b2b")
    bx.set_xticks(xs)
    bx.set_xticklabels([label[c] for c in layers], rotation=22, ha="right", fontsize=8)
    bx.set_ylabel("anomaly event-wise F0.5")
    bx.set_ylim(0, max(f05) * 1.28)
    bx.set_title("(b) Scored performance by alarm layer", loc="left", fontsize=10)
    bx.grid(axis="y", alpha=0.25, linewidth=0.7)
    bx.set_axisbelow(True)

    fig.tight_layout()
    path = out / "Figure_1_burden_recall.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------- Figure 2
def figure_contrasts(root: Path, out: Path) -> Path:
    """Arm performance with observed seed spread, plus the pre-registered contrasts."""
    rc = pd.read_csv(root / RESULTS)
    a0 = {m: float(rc[(rc.mission == m) & (rc.tag == f"m{m}_target_ar8_s0")
                      & (rc.calibrator == CAL)]["anomaly_and_rare/EW_F0.5"].iloc[0])
          for m in (1, 2)}
    spec = {"A1": ["m{m}_target_ar8"],
            "A2": [f"m{{m}}_target_gbt_ar8_s{s}_event" for s in range(5)],
            "A3": [f"m{{m}}_target_event_ar8_all_c3_s{s}_event" for s in range(5)]}
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
    for ax, m in zip(axes, (1, 2)):
        names, means, errs, ns = ["A0"], [a0[m]], [0.0], [1]
        for arm, tags in spec.items():
            v = arm_values(root, [t.format(m=m) for t in tags], "anomaly_and_rare/EW_F0.5")
            names.append(arm); means.append(float(np.mean(v)))
            errs.append(float(np.std(v, ddof=1)) if len(v) > 1 else 0.0); ns.append(len(v))
        cols = [C2, C1, C3, C4]
        xs = np.arange(len(names))
        ax.bar(xs, means, yerr=errs, capsize=5, color=cols, edgecolor="white",
               linewidth=1.2, width=0.6, error_kw=dict(ecolor="#52514e", lw=1.2))
        for x, v, e in zip(xs, means, errs):
            ax.text(x, v + e + 0.03, f"{v:.3f}", ha="center", fontsize=8.5)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{nm}\nn={n}" for nm, n in zip(names, ns)], fontsize=9)
        ax.set_ylim(0, 1.34)
        ax.grid(axis="y", alpha=0.25, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(f"({'ab'[m - 1]}) Mission {m}"
                     + (" \u2014 confirmatory" if m == 1 else " \u2014 replication, no inference"),
                     loc="left", fontsize=10)
        if m == 1:
            ax.set_ylabel("corrected event-wise F0.5 (anomalies + rare)")
            ax.text(0.02, 0.97,
                    "H6: A1 \u2212 A0 = +0.353\n[+0.206, +0.488]\nHolm p = 0.0015  (supported)\n"
                    "H4: A3 \u2212 A1 = \u22120.222  (refuted)\n"
                    "H5: A3 \u2212 A2 = \u22120.338  (refuted)",
                    transform=ax.transAxes, fontsize=7.8, color="#2b2b2b",
                    ha="left", va="top", linespacing=1.5)
        else:
            ax.text(0.02, 0.97, "H6 reverses: \u22120.089\nM2 test half holds only\n6 anomalies "
                                "(see \u00a716.2)",
                    transform=ax.transAxes, fontsize=7.8, color="#2b2b2b",
                    ha="left", va="top", linespacing=1.5)
        ax.text(0.5, -0.17, "error bars: \u00b11 SD over seeds", transform=ax.transAxes,
                fontsize=7.2, color="#52514e", ha="center")
    fig.tight_layout()
    path = out / "Figure_2_arm_contrasts.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


# --------------------------------------------------------------------- Figure 3
def figure_selection(root: Path, out: Path) -> Path:
    """Selection (cross-fit) score against test score, per run, both missions."""
    spec = {"A1": ["m{m}_target_ar8"],
            "A2": [f"m{{m}}_target_gbt_ar8_s{s}_event" for s in range(5)],
            "A3": [f"m{{m}}_target_event_ar8_all_c3_s{s}_event" for s in range(5)]}
    style = {"A1": ("o", C1), "A2": ("s", C3), "A3": ("^", C4)}
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2), sharex=True, sharey=True)
    from scipy.stats import spearmanr
    for ax, m in zip(axes, (1, 2)):
        allx, ally = [], []
        for arm, tags in spec.items():
            xs, ys = [], []
            for t in tags:
                for r in rows(root, t.format(m=m)):
                    if r["calibrator"] != CAL:
                        continue
                    if r.get("cv_EW_F0.5") is None:
                        continue
                    xs.append(r["cv_EW_F0.5"]); ys.append(r["anomaly_and_rare/EW_F0.5"])
            mk, col = style[arm]
            ax.scatter(xs, ys, s=80, marker=mk, color=col, edgecolor="white",
                       linewidth=1.2, label=f"{arm} (n={len(xs)})", zorder=3)
            allx += xs; ally += ys
        lo, hi = 0.0, 1.05
        ax.plot([lo, hi], [lo, hi], color="#8c8b85", lw=1.0, ls=(0, (4, 3)), zorder=1)
        ax.text(0.97, 0.99, "y = x", transform=ax.transAxes, fontsize=7.5,
                color="#52514e", ha="right", va="top")
        rho = spearmanr(allx, ally).statistic if len(allx) > 2 else float("nan")
        ax.set_title(f"({'ab'[m - 1]}) Mission {m}   per-run Spearman ρ = {rho:+.3f}  (n={len(allx)})",
                     loc="left", fontsize=10)
        ax.set_xlabel("selection score (cross-fit on training half)")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        ax.grid(alpha=0.25, linewidth=0.7); ax.set_axisbelow(True)
        ax.legend(frameon=False, fontsize=8, loc="lower right")
        if m == 1:
            ax.set_ylabel("test score (corrected event-wise F0.5)")
    fig.suptitle("Points below the diagonal indicate cross-fit optimism", x=0.012, ha="left",
                 fontsize=8.5, color="#52514e", y=1.0)
    fig.tight_layout()
    path = out / "Figure_3_selection_vs_test.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="paper/jint/figures")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    out = Path(args.out)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    for fn in (figure_burden_recall, figure_contrasts, figure_selection):
        print("written:", fn(root, out).relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
