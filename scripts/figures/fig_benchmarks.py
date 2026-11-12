"""Cross-task benchmarking figures: learned methods against parameter-free references.

    python scripts/figures/fig_benchmarks.py

The organising question is the one a reviewer asks first: does the learned component beat the
cheapest thing that could have been done instead? Each row below pairs the best learned arm in a
setting with the best parameter-free reference evaluated on the *same* split under the *same*
decision rule, and the rows are grouped so that no two metrics share an axis.

Three discipline rules are enforced in code, not left to the caption:

  * metrics are never mixed on one axis -- the bounded "higher is better" scores occupy one panel
    and the pinball loss, which is unbounded and lower-is-better, occupies its own;
  * the ESA-ADB rows all come from ``results.csv``, i.e. the arm-A0 selection protocol, and are
    not mixed with the cross-fitted A1-A3 numbers reported in the JINT figures;
  * on the conjunction task the native and threshold-tuned decision rules give opposite verdicts,
    so both are drawn rather than whichever flatters the project.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as S  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ESA = "outputs/benchmarks/telemetry_esa_adb/results.csv"
PARAM_FREE = ("out_of_limits", "out_of_limits_all", "global_std3", "global_std5")
LEARNED = ("ar8", "patchtst", "patchtst_tc", "tcn", "tcn_tc", "chronos-bolt-small")


def esa_rows(root: Path) -> list[dict]:
    """Best learned scorer-and-layer configuration against the best parameter-free reference.

    The alarm layer is averaged over **seeds only, never over calibrators**. Collapsing the
    calibrator would understate every learned arm here by a wide margin -- on Mission 1 at full
    channel scale the best configuration scores 0.318 and the scorer's calibrator-averaged value
    is 0.144 -- and this project has already been bitten once by averaging over a load-bearing
    calibrator. The winning layer is recorded in the output so the pairing stays auditable.
    """
    frame = pd.read_csv(root / ESA)
    frame["scale"] = np.where(frame.tag.str.contains("_target_"), "target (full)", "lightweight")
    frame["scorer"] = (frame.tag.str.replace(r"^m\d_(target|lightweight)_", "", regex=True)
                                .str.replace(r"_s\d+$", "", regex=True))
    agg = (frame.groupby(["mission", "scale", "scorer", "calibrator"])
                ["anomaly_and_rare/EW_F0.5"].agg(["mean", "count"]).reset_index()
                .rename(columns={"mean": "score", "count": "n_seeds"}))
    out = []
    for m in (1, 2):
        for sc in ("target (full)", "lightweight"):
            sub = agg[(agg.mission == m) & (agg.scale == sc)]
            ref = sub[sub.scorer.isin(PARAM_FREE)].sort_values("score", ascending=False)
            lrn = sub[sub.scorer.isin(LEARNED)].sort_values("score", ascending=False)
            if ref.empty or lrn.empty:
                continue
            rb, lb = ref.iloc[0], lrn.iloc[0]
            out.append({
                "setting": f"ESA-ADB M{m}\n{sc}",
                "metric": "corrected event-wise F0.5",
                "reference_name": f"{rb.scorer}",
                "reference": float(rb.score),
                "learned_name": f"{lb.scorer} + {lb.calibrator}",
                "learned": float(lb.score),
                "protocol": f"arm-A0 selection (9-month calibration period); "
                            f"learned arm averaged over {int(lb.n_seeds)} seed(s), "
                            f"best alarm layer retained per scorer",
                "source": "telemetry_esa_adb/results.csv",
            })
    return out


# =============================================================== B1 learned vs reference
def fig_b1(root: Path, out: Path, data: Path):
    rows = esa_rows(root)

    kel = pd.read_csv(root / "outputs/benchmarks/conjunction_kelvins_cac/test_results.csv")
    triv = kel[kel.model == "latest_risk_point"].iloc[0]
    learned_native = kel[kel.model != "latest_risk_point"].sort_values("F2", ascending=False).iloc[0]
    learned_tuned = kel[kel.model != "latest_risk_point"].sort_values(
        "F2_decision", ascending=False).iloc[0]
    rows += [
        {"setting": "conjunction — Kelvins CAC\nnative decision rule",
         "metric": "F2 (high-risk)", "reference_name": "latest_risk_point",
         "reference": float(triv.F2), "learned_name": str(learned_native.model),
         "learned": float(learned_native.F2),
         "protocol": "official test split, no threshold tuning",
         "source": "conjunction_kelvins_cac/test_results.csv column F2"},
        {"setting": "conjunction — Kelvins CAC\ntuned decision threshold",
         "metric": "F2 (high-risk)", "reference_name": "latest_risk_point",
         "reference": float(triv.F2_clip), "learned_name": str(learned_tuned.model),
         "learned": float(learned_tuned.F2_decision),
         "protocol": "learned arms use a tuned decision threshold; the reference has none to tune",
         "source": "conjunction_kelvins_cac/test_results.csv columns F2_clip, F2_decision"},
    ]

    spot = pd.read_csv(root / "outputs/benchmarks/vision_spotgeo/summary.csv")
    classical = spot[spot.model.str.contains("classical")].iloc[0]
    best_cnn = spot[~spot.model.str.contains("classical")].sort_values(
        "test_f1|mean", ascending=False).iloc[0]
    rows.append({"setting": "debris — SpotGEO\nofficial metric",
                 "metric": "test F1", "reference_name": "classical front end + DoG",
                 "reference": float(classical["test_f1|mean"]),
                 "learned_name": str(best_cnn.model),
                 "learned": float(best_cnn["test_f1|mean"]),
                 "protocol": "official test split",
                 "source": "vision_spotgeo/summary.csv test_f1|mean"})

    land = pd.read_csv(root / "outputs/benchmarks/reentry_landmark/results.csv")
    phys = land[land.model == "physics"].iloc[0]
    bestl = land[land.model != "physics"].sort_values("all/c_index", ascending=False).iloc[0]
    rows.append({"setting": "re-entry landmark\n68-day follow-up",
                 "metric": "concordance (c-index)", "reference_name": "physics expert",
                 "reference": float(phys["all/c_index"]),
                 "learned_name": str(bestl.model), "learned": float(bestl["all/c_index"]),
                 "protocol": "38 events among 6,371 objects at risk",
                 "source": "reentry_landmark/results.csv all/c_index"})

    src = pd.DataFrame(rows)
    src["margin_learned_minus_reference"] = src.learned - src.reference
    src["winner"] = np.where(src.learned > src.reference, "learned", "parameter-free reference")

    # ---- the unbounded, lower-is-better metric gets its own panel
    life = []
    for origin, folder in (("2011", "origin2011_uncontrolled"), ("2016", "origin2016_uncontrolled")):
        r = pd.read_csv(root / f"outputs/benchmarks/reentry_lifetime/{folder}/regression_test.csv")
        phys = float(r[r.model == "physics_only"].pinball.iloc[0])
        lrn = r[r.model != "physics_only"].sort_values("pinball").iloc[0]
        life.append({"setting": f"orbital lifetime\norigin {origin}", "metric": "pinball loss",
                     "reference_name": "physics_only", "reference": phys,
                     "learned_name": str(lrn.model), "learned": float(lrn.pinball),
                     "n_scored": int(r.n.iloc[0]),
                     "source": f"reentry_lifetime/{folder}/regression_test.csv pinball"})
    life = pd.DataFrame(life)
    life["margin_reference_minus_learned"] = life.reference - life.learned
    life["winner"] = np.where(life.learned < life.reference, "learned",
                              "parameter-free reference")

    fig = plt.figure(figsize=(10.6, 7.6))
    gs = fig.add_gridspec(2, 1, height_ratios=(len(src), 2.0), hspace=0.26,
                          left=0.255, right=0.905, top=0.880, bottom=0.150)

    # ---------------- panel (a): bounded, higher is better
    ax = fig.add_subplot(gs[0])
    y = np.arange(len(src))[::-1]
    for yi, r in zip(y, src.itertuples()):
        win = r.learned > r.reference
        ax.plot([r.reference, r.learned], [yi, yi],
                color=S.C1 if win else S.C2, lw=2.2, solid_capstyle="round", zorder=2)
        ax.scatter(r.reference, yi, s=92, marker="s", color="white",
                   edgecolor=S.C2, linewidth=1.8, zorder=4)
        ax.scatter(r.learned, yi, s=104, marker="o",
                   color=S.C1 if win else "white",
                   edgecolor=S.C1 if win else S.C2, linewidth=1.8, zorder=4)
        ax.text(1.012, yi, f"{r.margin_learned_minus_reference:+.3f}",
                transform=ax.get_yaxis_transform(), va="center", ha="left", fontsize=7.4,
                color=S.C1 if win else S.C2, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.setting}\n[{r.metric}]" for r in src.itertuples()], fontsize=7.2)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("score  (all metrics bounded in [0, 1]; higher is better)")
    S.panel_title(ax, "(a) Best learned arm against the best parameter-free reference, "
                      "same split")  # legend sits above this title
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.text(1.012, len(src) - 0.55, "margin", transform=ax.get_yaxis_transform(),
            va="center", ha="left", fontsize=7.2, color=S.INK2, fontweight="bold")

    # ---------------- panel (b): unbounded, lower is better
    bx = fig.add_subplot(gs[1])
    y2 = np.arange(len(life))[::-1]
    for yi, r in zip(y2, life.itertuples()):
        win = r.learned < r.reference
        bx.plot([r.reference, r.learned], [yi, yi],
                color=S.C1 if win else S.C2, lw=2.2, solid_capstyle="round", zorder=2)
        bx.scatter(r.reference, yi, s=92, marker="s", color="white",
                   edgecolor=S.C2, linewidth=1.8, zorder=4)
        bx.scatter(r.learned, yi, s=104, marker="o", color=S.C1 if win else "white",
                   edgecolor=S.C1 if win else S.C2, linewidth=1.8, zorder=4)
        margin = r.margin_reference_minus_learned
        label = "≈ 0 (tie)" if abs(margin) < 1e-4 else f"{margin:+.4f}"
        bx.text(1.012, yi, label,
                transform=bx.get_yaxis_transform(), va="center", ha="left", fontsize=7.4,
                color=S.C1 if win else S.C2, fontweight="bold")
        bx.annotate(r.learned_name, (r.learned, yi), xytext=(0, 13),
                    textcoords="offset points", fontsize=6.8, color=S.INK2, ha="center")
    bx.set_yticks(y2)
    bx.set_yticklabels([f"{r.setting}\n[{r.metric}]" for r in life.itertuples()], fontsize=7.2)
    bx.set_ylim(-0.75, len(life) - 0.25)
    bx.set_xlim(0.044, 0.096)
    bx.set_xlabel("pinball loss of log₁₀ capped lifetime  (lower is better)")
    S.panel_title(bx, "(b) Same comparison on an unbounded, lower-is-better metric")
    S.grid(bx, "x")
    bx.spines["left"].set_visible(False)
    bx.tick_params(axis="y", length=0)

    ax.legend(handles=[
        Line2D([], [], marker="s", color="none", markerfacecolor="white",
               markeredgecolor=S.C2, markeredgewidth=1.8, markersize=9,
               label="best parameter-free reference"),
        Line2D([], [], marker="o", color="none", markerfacecolor=S.C1,
               markeredgecolor=S.C1, markersize=9, label="best learned arm (learned wins)"),
        Line2D([], [], marker="o", color="none", markerfacecolor="white",
               markeredgecolor=S.C2, markeredgewidth=1.8, markersize=9,
               label="best learned arm (reference wins)"),
    ], loc="lower left", fontsize=7.4, bbox_to_anchor=(-0.005, 1.085), ncol=3,
        handletextpad=0.5, columnspacing=1.8)

    fig.suptitle("Does the learned component beat the cheapest alternative?",
                 x=0.006, ha="left", fontsize=11.0, color=S.INK, y=0.985)
    all_rows = len(src) + len(life)
    learned_wins = int((src.winner == "learned").sum() + (life.winner == "learned").sum())
    worst = src.loc[src.margin_learned_minus_reference.idxmin()]
    S.footnote(fig,
               "Parameter-free references are the out-of-limits and global-sigma rules for "
               "ESA-ADB, the last reported risk value for conjunctions, a classical "
               "difference-of-Gaussians front end for SpotGEO, and the physics expert for "
               f"re-entry and lifetime. Learning wins {learned_wins} of these {all_rows} rows and "
               f"loses {all_rows - learned_wins}, and the losses are not marginal: the widest is "
               f"{worst.setting.replace(chr(10), ', ')}, where the reference beats the best "
               f"learned arm by {abs(worst.margin_learned_minus_reference):.3f}. The two "
               "conjunction rows are drawn separately because they are not the same comparison — "
               "the learned arms gain a tuned decision threshold in the second row while the "
               "reference has none to tune, and that reverses the verdict; reporting either one "
               "alone would misrepresent the result. Each ESA-ADB learned arm keeps its best "
               "alarm layer and is averaged over seeds only, never over layers, because the layer "
               "is load-bearing; the layer chosen is named in the source-data file. Those rows "
               "use the arm-A0 selection protocol and are not comparable with the A1–A3 values in "
               "the JINT figures. Orbital lifetime reverses with the temporal origin: the physics "
               "expert ties for best at origin 2011 and is the worst of nineteen arms at origin "
               "2016.", y=0.085)

    S.save_source(src, data, "benchmark_learned_vs_reference")
    S.save_source(life, data, "benchmark_lifetime_vs_physics")
    return S.save(fig, out, "Figure_B1_learned_vs_reference"), src


# =============================================================== B2 rank instability
def fig_b2(root: Path, out: Path, data: Path):
    """The same nineteen-arm leaderboard at two temporal origins. Ranks do not survive."""
    frames = {}
    for origin, folder in (("2011", "origin2011_uncontrolled"), ("2016", "origin2016_uncontrolled")):
        r = pd.read_csv(root / f"outputs/benchmarks/reentry_lifetime/{folder}/regression_test.csv")
        r = r[["model", "pinball", "cov80", "cov90", "n"]].copy()
        r["rank"] = r.pinball.rank(method="min").astype(int)
        frames[origin] = r.set_index("model")

    common = sorted(set(frames["2011"].index) & set(frames["2016"].index))
    src = pd.DataFrame({
        "model": common,
        "pinball_2011": [frames["2011"].pinball[m] for m in common],
        "pinball_2016": [frames["2016"].pinball[m] for m in common],
        "rank_2011": [int(frames["2011"]["rank"][m]) for m in common],
        "rank_2016": [int(frames["2016"]["rank"][m]) for m in common],
        "cov80_2016": [frames["2016"].cov80[m] for m in common],
    })
    # re-rank within the comparable subset, so a rank of 1 means first among these arms
    src["rank_2011"] = src.pinball_2011.rank(method="min").astype(int)
    src["rank_2016"] = src.pinball_2016.rank(method="min").astype(int)
    src["rank_change"] = src.rank_2016 - src.rank_2011
    from scipy.stats import spearmanr, kendalltau
    rho = spearmanr(src.pinball_2011, src.pinball_2016).statistic
    tau = kendalltau(src.rank_2011, src.rank_2016).statistic

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.6, 6.6),
                                 gridspec_kw={"width_ratios": (1.25, 1.0), "wspace": 0.42})
    fig.subplots_adjust(left=0.105, right=0.975, top=0.865, bottom=0.235)

    # ---- (a) rank slope chart
    HILITE = {"physics_only": S.C2, "cosmos_gated": S.C1, "tabicl": S.C3, "equal_average": S.C4}
    for r in src.itertuples():
        col = HILITE.get(r.model, "#c9c9c3")
        lw = 2.2 if r.model in HILITE else 1.0
        z = 4 if r.model in HILITE else 2
        ax.plot([0, 1], [r.rank_2011, r.rank_2016], color=col, lw=lw, zorder=z,
                solid_capstyle="round")
        ax.scatter([0, 1], [r.rank_2011, r.rank_2016], s=42 if r.model in HILITE else 16,
                   color=col, edgecolor="white", linewidth=1.0, zorder=z + 1)
    for r in src.itertuples():
        if r.model in HILITE:
            ax.text(-0.045, r.rank_2011, r.model, ha="right", va="center", fontsize=7.4,
                    color=HILITE[r.model], fontweight="bold")
            ax.text(1.045, r.rank_2016, r.model, ha="left", va="center", fontsize=7.4,
                    color=HILITE[r.model], fontweight="bold")
    ax.set_xlim(-0.62, 1.62)
    ax.set_ylim(len(src) + 0.6, 0.4)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["origin 2011\n(test 2011–2016)", "origin 2016\n(test 2016–2021)"],
                       fontsize=8.0)
    ax.set_ylabel("rank by pinball loss  (1 = best)")
    ax.set_yticks(range(1, len(src) + 1))
    ax.tick_params(axis="y", labelsize=7.4)
    S.panel_title(ax, f"(a) Rank across temporal origins   Kendall τ = {tau:+.3f}")
    ax.grid(axis="y", alpha=0.22, linewidth=0.6, color=S.MUTED)
    ax.set_axisbelow(True)

    # ---- (b) loss against loss
    bx.plot([0.045, 0.12], [0.045, 0.12], color=S.MUTED, lw=1.0, ls=(0, (4, 3)), zorder=1)
    for r in src.itertuples():
        col = HILITE.get(r.model, "#9a9a94")
        bx.scatter(r.pinball_2011, r.pinball_2016,
                   s=96 if r.model in HILITE else 34, color=col,
                   edgecolor="white", linewidth=1.2,
                   zorder=4 if r.model in HILITE else 2)
    # All four highlighted arms sit at the low-loss end, so their labels go out to the right with
    # a white backing: to the left they printed over the y axis and its label.
    for name, dx, dy in (("physics_only", 15, 0), ("equal_average", 15, 0),
                         ("cosmos_gated", 15, 7), ("tabicl", 15, -8)):
        if name in set(src.model):
            r = src[src.model == name].iloc[0]
            bx.annotate(name, (r.pinball_2011, r.pinball_2016), xytext=(dx, dy),
                        textcoords="offset points", fontsize=7.2, color=HILITE[name],
                        ha="left", va="center", fontweight="bold", zorder=6,
                        bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.9))
    bx.set_xlabel("pinball loss, origin 2011")
    bx.set_ylabel("pinball loss, origin 2016")
    bx.set_xlim(0.045, 0.122)
    bx.set_ylim(0.045, 0.095)
    S.panel_title(bx, f"(b) Loss against loss   Spearman ρ = {rho:+.3f}")
    S.grid(bx, "both")
    bx.text(0.97, 0.05, "dashed line: equal loss", transform=bx.transAxes, fontsize=7.0,
            color=S.INK2, ha="right")

    fig.suptitle("Orbital lifetime: arm ranking does not transfer between temporal origins",
                 x=0.006, ha="left", fontsize=10.8, color=S.INK, y=0.975)

    S.footnote(fig,
               f"Restricted to the {len(src)} arms evaluated at both origins; each origin's "
               "learner-specific ablations are excluded because the selected learner differs "
               "between them, so those arms do not exist in both leaderboards. Ranks are "
               "recomputed within this comparable subset. The physics expert is first at origin "
               "2011 and last at origin 2016; equal_average goes second to eleventh; the deployed "
               "arm (cosmos_gated) goes third to seventh. Both rank statistics are negative, not "
               "merely weak, so on this evidence a leaderboard position measured at one origin is "
               "if anything mildly anti-informative about the next — though with thirteen arms "
               "neither coefficient is precisely estimated, and the honest reading is that "
               "ranking carries no dependable signal across origins rather than that it inverts. "
               "This is the main reason the lifetime result is reported as negative, and why no "
               "arm in this project is described as state of the art.", y=0.135)
    S.save_source(src, data, "lifetime_rank_instability")
    return S.save(fig, out, "Figure_B2_rank_instability"), src


FIGURES = [("B1", fig_b1), ("B2", fig_b2)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="paper/figures/benchmarks")
    ap.add_argument("--data", default="paper/figures/data")
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    out, data = root / args.out, root / args.data
    S.apply()
    want = set(args.only.split(",")) if args.only else None
    for fid, fn in FIGURES:
        if want and fid not in want:
            continue
        paths, src = fn(root, out, data)
        print(f"{fid}: {paths[0].relative_to(root)}  ({len(src)} source rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
