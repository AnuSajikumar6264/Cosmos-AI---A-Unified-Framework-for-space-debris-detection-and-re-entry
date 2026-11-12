"""Failure-analysis figures: where COSMOS-AI's models are miscalibrated, unstable or untestable.

    python scripts/figures/fig_diagnostics.py

This collection exists to make the limitations visible rather than to argue a case. Nothing here is
filtered to improve an appearance: every Phase H cell is drawn including the ones that fail, every
subgroup is drawn including the worst, and the coupling panel reports the verdicts the project's own
analyses recorded.

One methodological point governs the residual panels. The lifetime target is
``z = log10(min(time_days, 1826.25))``, so an object still in orbit at the five-year horizon sits
exactly at the cap and its true lifetime is unknown. Residuals are therefore computed only on
objects with an observed decay strictly inside the window, and the number excluded is reported on
the figure. Treating a censored object's cap value as if it were an observation would manufacture
accuracy.
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
from matplotlib.patches import Patch  # noqa: E402

LIFE = "outputs/benchmarks/reentry_lifetime"
PHASE_H = "outputs/phase_h/coverage_table.csv"
CAP_LOG10 = float(np.log10(1826.25))
QUANTILES = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)


# =============================================================== G1 calibration failure
def fig_g1(root: Path, out: Path, data: Path):
    cov = pd.read_csv(root / PHASE_H)
    sub = pd.read_csv(root / f"{LIFE}/origin2016_uncontrolled/subgroups_test.csv")
    temp = pd.read_csv(root / f"{LIFE}/origin2016_uncontrolled/temporal_coverage_test.csv")

    fig = plt.figure(figsize=(11.0, 7.8))
    gs = fig.add_gridspec(2, 2, height_ratios=(1.35, 1.0), width_ratios=(1.0, 1.0),
                          hspace=0.46, wspace=0.26,
                          left=0.095, right=0.975, top=0.900, bottom=0.165)

    # ---- (a) every Phase H cell: empirical coverage against nominal, with interval and verdict
    ax = fig.add_subplot(gs[0, :])
    cov = cov.sort_values(["level", "origin", "model"]).reset_index(drop=True)
    x = np.arange(len(cov))
    verdict_colour = {"CONSISTENT WITH NOMINAL": S.C3, "OVER-COVERS": S.C1,
                      "UNDER-COVERS": S.C4}
    for xi, r in zip(x, cov.itertuples()):
        lo, hi = r.level + r.ci95_lo, r.level + r.ci95_hi
        col = verdict_colour.get(r.verdict, S.MUTED)
        ax.plot([xi, xi], [lo, hi], color=col, lw=1.8, solid_capstyle="round", zorder=3)
        ax.scatter(xi, r.empirical_coverage, s=46, color=col, edgecolor="white",
                   linewidth=1.0, zorder=4)
    # The nominal levels go in the legend, not as inline text: at the right-hand edge the labels
    # printed over the spine, and there is no interior gap wide enough for them.
    for lvl, ls in ((0.8, (0, (5, 3))), (0.9, (0, (1, 2)))):
        ax.axhline(lvl, color=S.INK, lw=0.9, ls=ls, zorder=2)
    boundary = int((cov.level == 0.8).sum())
    ax.axvline(boundary - 0.5, color=S.MUTED, lw=1.0)
    ax.text(boundary / 2 - 0.5, 1.012, "80% intervals", ha="center", fontsize=8.0, color=S.INK2)
    ax.text(boundary + (len(cov) - boundary) / 2 - 0.5, 1.012, "90% intervals",
            ha="center", fontsize=8.0, color=S.INK2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.model}\n{r.origin}" for r in cov.itertuples()],
                       rotation=90, fontsize=6.2)
    ax.set_ylim(0.60, 1.045)
    ax.set_xlim(-0.8, len(cov) - 0.2)
    ax.set_ylabel("empirical coverage")
    S.panel_title(ax, "(a) Every Phase H uncertainty cell, with its recorded verdict")
    S.grid(ax, "y")
    n_bad = int((cov.verdict != "CONSISTENT WITH NOMINAL").sum())
    ax.text(0.004, 0.045, f"{n_bad} of {len(cov)} cells deviate significantly from nominal",
            transform=ax.transAxes, fontsize=8.0, color=S.C4, fontweight="bold")
    ax.legend(handles=[Line2D([], [], color=c, marker="o", lw=1.8, markeredgecolor="white",
                              label=v.lower()) for v, c in verdict_colour.items()]
                      + [Line2D([], [], color=S.INK, lw=0.9, ls=(0, (5, 3)),
                                label="nominal 0.80"),
                         Line2D([], [], color=S.INK, lw=0.9, ls=(0, (1, 2)),
                                label="nominal 0.90")],
              loc="lower right", fontsize=7.2, ncol=5, bbox_to_anchor=(1.0, -0.025),
              columnspacing=1.2, handlelength=1.8)

    # ---- (b) coverage by subgroup: the missingness pathway
    bx = fig.add_subplot(gs[1, 0])
    models = ["physics_only", "tabm", "cosmos_gated"]
    groups = ["am_source=class_prior_sbm", "am_source=design", "type=D", "type=R", "type=C"]
    width = 0.26
    for i, m in enumerate(models):
        vals, ns = [], []
        for g in groups:
            row = sub[(sub.model == m) & (sub.subgroup == g)]
            vals.append(float(row.cov80.iloc[0]) if len(row) else np.nan)
            ns.append(int(row.n.iloc[0]) if len(row) else 0)
        bx.bar(np.arange(len(groups)) + (i - 1) * width, vals, width=width - 0.02,
               color=[S.C1, S.C3, S.C4][i], edgecolor="white", linewidth=0.9,
               label=m, zorder=3)
    bx.axhline(0.80, color=S.INK, lw=1.0, ls=(0, (5, 3)), zorder=4)
    bx.text(0.015, 0.815, "nominal 0.80", transform=bx.get_yaxis_transform(),
            fontsize=7.0, color=S.INK, ha="left", va="bottom")
    labels = []
    for g in groups:
        n = sub[sub.subgroup == g].n.iloc[0] if (sub.subgroup == g).any() else 0
        labels.append(g.replace("am_source=", "A/m: ").replace("type=", "class ")
                      + f"\nn={int(n):,}")
    bx.set_xticks(np.arange(len(groups)))
    bx.set_xticklabels(labels, fontsize=6.8)
    bx.set_ylim(0, 1.0)
    bx.set_ylabel("empirical coverage of the 80% interval")
    S.panel_title(bx, "(b) Coverage by subgroup, origin 2016")
    S.grid(bx, "y")
    bx.legend(fontsize=7.0, loc="upper right", ncol=1)

    # ---- (c) coverage against test year
    cx = fig.add_subplot(gs[1, 1])
    style = {"physics_only": ("o", S.C1), "cosmos_gated": ("s", S.C3), "tabm": ("^", S.C4)}
    for m, (mk, col) in style.items():
        d = temp[temp.model == m].sort_values("year")
        if d.empty:
            continue
        cx.plot(d.year, d.cov90, marker=mk, color=col, lw=1.8, markeredgecolor="white",
                markeredgewidth=1.0, label=m, zorder=3)
    cx.axhline(0.90, color=S.INK, lw=1.0, ls=(0, (5, 3)), zorder=4)
    cx.text(0.015, 0.905, "nominal 0.90", transform=cx.get_yaxis_transform(),
            fontsize=7.0, color=S.INK, ha="left", va="bottom")
    cx.set_xticks(sorted(temp.year.unique()))
    cx.set_xticklabels([f"{int(y)}\nn={int(temp[temp.year == y].n.iloc[0]):,}"
                        for y in sorted(temp.year.unique())], fontsize=6.8)
    cx.set_ylim(0.65, 1.0)
    cx.set_ylabel("empirical coverage of the 90% interval")
    S.panel_title(cx, "(c) Coverage decays across the test window")
    S.grid(cx, "y")
    cx.legend(fontsize=7.0, loc="lower left")

    fig.suptitle("Uncertainty quantification: where the intervals do not hold",
                 x=0.006, ha="left", fontsize=11.0, color=S.INK, y=0.975)
    S.footnote(fig,
               "Panel (a) draws all 24 Phase H cells with the 95% interval on the coverage "
               "deviation and the verdict recorded by that analysis; cells that over-cover are as "
               "much a calibration failure as cells that under-cover, because an interval wider "
               "than it claims is uninformative rather than safe. Panel (b) is the missingness "
               "pathway the project flagged but has not closed: objects whose area-to-mass ratio "
               "is design-derived reach 0.56-0.59 against a nominal 0.80, and the worst subgroup of "
               "all is object class C at 0.54-0.56 — so the interval that holds on "
               "average does not hold for the subpopulations an operator would actually ask "
               "about. Panel (c) shows coverage falling as the "
               "test window moves away from the fitting period — the exchangeability that "
               "conformal methods require fails here by construction, which is why this project "
               "claims no distribution-free guarantee. Source tables are in "
               "paper/figures/data/.", y=0.105)

    S.save_source(cov, data, "diagnostics_phase_h_coverage")
    S.save_source(sub, data, "diagnostics_subgroup_coverage")
    S.save_source(temp, data, "diagnostics_temporal_coverage")
    return S.save(fig, out, "Figure_G1_calibration_failure"), cov


# =============================================================== G2 residuals and uncertainty
def fig_g2(root: Path, out: Path, data: Path):
    z = np.load(root / f"{LIFE}/origin2016_uncontrolled/test_predictions.npz", allow_pickle=True)
    known = z["known5"].astype(bool)
    truth = z["z"]
    event = z["event"].astype(int)

    # Residuals only where a decay was actually observed inside the window. An object sitting at
    # the cap is right-censored: its true lifetime is unknown and its "error" is not defined.
    uncensored = known & (event == 1) & (truth < CAP_LOG10 - 1e-9)
    n_excluded = int(known.sum() - uncensored.sum())

    arms = ["cosmos_gated", "tabicl", "physics_only"]
    recs = []
    for arm in arms:
        q = z[f"{arm}__q"]
        med = q[:, QUANTILES.index(0.50)]
        lo80, hi80 = z[f"{arm}__lo80"], z[f"{arm}__hi80"]
        resid = med[uncensored] - truth[uncensored]
        width = (hi80 - lo80)[uncensored]
        abserr = np.abs(resid)
        from scipy.stats import spearmanr
        recs.append({
            "arm": arm,
            "n_residual": int(uncensored.sum()),
            "n_excluded_censored_or_unknown": n_excluded,
            "median_residual_log10": float(np.median(resid)),
            "mae_log10": float(np.mean(abserr)),
            "mean_width80_log10": float(np.mean(width)),
            "spearman_width_vs_abs_error": float(spearmanr(width, abserr).statistic),
            "coverage80_uncensored": float(((truth[uncensored] >= lo80[uncensored])
                                            & (truth[uncensored] <= hi80[uncensored])).mean()),
            "coverage80_all_known5": float(((truth[known] >= lo80[known])
                                            & (truth[known] <= hi80[known])).mean()),
        })
    src = pd.DataFrame(recs)

    fig = plt.figure(figsize=(11.0, 5.4))
    gs = fig.add_gridspec(1, 3, wspace=0.30, left=0.070, right=0.980, top=0.860, bottom=0.300)
    style = {"cosmos_gated": S.C1, "tabicl": S.C3, "physics_only": S.C2}

    # ---- (a) signed residual distributions
    ax = fig.add_subplot(gs[0, 0])
    for arm in arms:
        q = z[f"{arm}__q"]
        resid = q[:, QUANTILES.index(0.50)][uncensored] - truth[uncensored]
        ax.hist(resid, bins=np.linspace(-2.2, 2.2, 56), histtype="step", linewidth=1.8,
                color=style[arm], label=arm, zorder=3)
    ax.axvline(0, color=S.INK, lw=1.0, zorder=4)
    ax.set_xlabel("median prediction − truth  (log₁₀ days)")
    ax.set_ylabel("objects")
    S.panel_title(ax, f"(a) Residuals: the {int(uncensored.sum()):,} observed decays "
                      f"of {int(known.sum()):,}")
    S.grid(ax, "y")
    ax.legend(fontsize=7.2, loc="upper left")

    # ---- (b) does the interval widen where the error is larger?
    bx = fig.add_subplot(gs[0, 1])
    for arm in arms:
        q = z[f"{arm}__q"]
        abserr = np.abs(q[:, QUANTILES.index(0.50)][uncensored] - truth[uncensored])
        width = (z[f"{arm}__hi80"] - z[f"{arm}__lo80"])[uncensored]
        edges = np.quantile(width, np.linspace(0, 1, 9))
        edges[-1] += 1e-9
        idx = np.digitize(width, edges[1:-1])
        xs = [float(np.median(width[idx == b])) for b in range(8) if (idx == b).sum() > 4]
        ys = [float(np.median(abserr[idx == b])) for b in range(8) if (idx == b).sum() > 4]
        rho = src.loc[src.arm == arm, "spearman_width_vs_abs_error"].iloc[0]
        bx.plot(xs, ys, marker="o", color=style[arm], lw=1.8, markeredgecolor="white",
                markeredgewidth=1.0, label=f"{arm}  ρ = {rho:+.3f}", zorder=3)
    bx.set_xlabel("interval width, 80%  (log₁₀ days, octile medians)")
    bx.set_ylabel("median |error|  (log₁₀ days)")
    S.panel_title(bx, "(b) Does the interval widen where the error is?")
    S.grid(bx, "both")
    bx.legend(fontsize=7.0, loc="lower right")

    # ---- (c) coverage against width across all arms: the honest trade-off
    cx = fig.add_subplot(gs[0, 2])
    reg = pd.read_csv(root / f"{LIFE}/origin2016_uncontrolled/regression_test.csv")
    cx.scatter(reg.width80_log10, reg.cov80, s=44, color="#b9b9b3", edgecolor="white",
               linewidth=0.8, zorder=3)
    for arm in arms:
        r = reg[reg.model == arm]
        if r.empty:
            continue
        cx.scatter(r.width80_log10, r.cov80, s=120, color=style[arm], edgecolor="white",
                   linewidth=1.5, zorder=5)
        # All three sit at the low-width end; labels go up-right and down-right so they clear
        # each other and, crucially, the y-axis label to their left.
        dx, dy, ha = {"physics_only": (12, 13, "left"),
                      "cosmos_gated": (12, -13, "left"),
                      "tabicl": (0, 14, "center")}.get(arm, (0, 13, "center"))
        cx.annotate(arm, (float(r.width80_log10.iloc[0]), float(r.cov80.iloc[0])),
                    xytext=(dx, dy), textcoords="offset points", fontsize=7.2,
                    color=style[arm], ha=ha, va="center", fontweight="bold", zorder=6,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.9))
    cx.axhline(0.80, color=S.INK, lw=1.0, ls=(0, (5, 3)), zorder=4)
    cx.text(0.98, 0.805, "nominal 0.80", transform=cx.get_yaxis_transform(),
            fontsize=7.0, color=S.INK, ha="right", va="bottom")
    cx.set_xlabel("mean interval width, 80%  (log₁₀ days)")
    cx.set_xlim(0.30, 0.85)
    cx.set_ylabel("empirical coverage, 80%")
    cx.set_ylim(0.62, 1.0)
    S.panel_title(cx, f"(c) Coverage against width, all {len(reg)} arms")
    S.grid(cx, "both")

    fig.suptitle("Orbital lifetime: prediction error and the uncertainty that should track it",
                 x=0.006, ha="left", fontsize=11.0, color=S.INK, y=0.975)
    S.footnote(fig,
               f"Origin 2016, {int(known.sum()):,} objects with a known five-year outcome. "
               f"Panels (a) and (b) use only the {int(uncensored.sum()):,} objects observed to "
               f"decay strictly inside the window; the other {n_excluded:,} sit at the "
               f"{10 ** CAP_LOG10:.2f}-day cap and are right-censored, so no error is defined for "
               "them and including them would manufacture accuracy. Panel (b) is the question an "
               "operator cares about — whether a wider interval really does signal a harder "
               "object — and the answer here is only weakly yes. Panel (c) shows the arms that "
               "reach nominal coverage do so largely by being wide, which is why coverage alone "
               "is never reported as a success criterion in this project. Values are in "
               "paper/figures/data/diagnostics_lifetime_residuals.csv.", y=0.205)

    S.save_source(src, data, "diagnostics_lifetime_residuals")
    return S.save(fig, out, "Figure_G2_residuals_uncertainty"), src


# =============================================================== G3 couplings
def fig_g3(root: Path, out: Path, data: Path):
    """What the four cross-module couplings actually showed, with intervals where they exist."""
    e12 = json.loads((root / "outputs/e12_same_learner/e12_results.json").read_text())
    phase_e = json.loads((root / "outputs/phase_e/phase_e_results.json").read_text())

    rows = []
    for cell, blk in e12["cells"].items():
        if blk.get("status") != "evaluated":
            continue
        for ab in blk.get("ablations", []):
            if ab.get("ablation") != "no_family" or ab.get("status") != "evaluated":
                continue
            rows.append({
                "coupling": "C1", "cell": cell, "learner": blk["learner"],
                "origin": blk["origin"],
                "effect": ab["effect_pinball_ablation_minus_full"],
                "ci95_lo": ab["ci95_lo"], "ci95_hi": ab["ci95_hi"],
                "p_value": ab["p_value"], "p_adjusted_bh": ab["p_adjusted_bh"],
                "significant": bool(ab["significant_after_correction"]),
                "n_launch_families": ab["n_launch_families"],
            })
    src = pd.DataFrame(rows)

    # The fair cross-origin test holds the learner fixed. `mlp` is the only learner run at both
    # origins; kumo and tabm are each the learner its own origin selected, so a result in those
    # cells cannot be separated from the choice of learner. Order the rows to make that visible.
    src["common_learner"] = src.learner == "mlp"
    src = src.sort_values(["common_learner", "origin"], ascending=[False, True])
    src = src.reset_index(drop=True)

    fig = plt.figure(figsize=(11.4, 6.8))
    gs = fig.add_gridspec(1, 2, width_ratios=(1.0, 1.05), wspace=0.08,
                          left=0.150, right=0.985, top=0.860, bottom=0.270)

    # ---- (a) C1, the only coupling with a per-cell interval
    ax = fig.add_subplot(gs[0, 0])
    y = np.arange(len(src))[::-1]
    ax.axvline(0, color=S.INK, lw=1.0, zorder=2)
    for yi, r in zip(y, src.itertuples()):
        col = S.C1 if r.significant else S.C2
        ax.plot([r.ci95_lo, r.ci95_hi], [yi, yi], color=col, lw=2.0,
                solid_capstyle="round", zorder=3)
        for e in (r.ci95_lo, r.ci95_hi):
            ax.plot([e, e], [yi - 0.1, yi + 0.1], color=col, lw=1.5, zorder=3)
        ax.scatter(r.effect, yi, s=84, color=col, edgecolor="white", linewidth=1.3, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(
        [f"{r.learner} @ {r.origin}\n{'common learner' if r.common_learner else 'origin-selected'}"
         f" · BH p = {r.p_adjusted_bh:.3f}" for r in src.itertuples()], fontsize=7.0)
    ax.set_xlabel("effect of removing the family features  (pinball ablated − full)\n"
                  "positive = the features helped")
    ax.set_ylim(-0.75, len(src) - 0.25)
    S.panel_title(ax, "(a) C1  family evidence → lifetime")
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.axhline(len(src) - 2.5, color=S.MUTED, lw=0.9, ls=(0, (3, 3)), zorder=1)
    ax.legend(handles=[
        Patch(facecolor=S.C1, label="significant after BH correction"),
        Patch(facecolor=S.C2, label="not significant"),
    ], loc="lower left", fontsize=7.0, bbox_to_anchor=(-0.005, 1.075), ncol=2)

    # ---- (b) the recorded verdict for each coupling
    bx = fig.add_subplot(gs[0, 1])
    bx.set_xlim(0, 1)
    bx.set_ylim(0, 1)
    bx.axis("off")
    S.panel_title(bx, "(b) Recorded verdicts, all four couplings")
    verdicts = []
    for key in ("C1", "C2", "C3", "C4"):
        blk = phase_e[key]
        verdicts.append((key, blk["hypothesis"], blk["verdict"],
                         blk.get("deployed_expert_caveat")
                         or blk.get("key_caveat") or blk.get("reason")
                         or blk.get("confound") or ""))
    colour = {"PARTIALLY SUPPORTED": S.STATUS["partial"], "INCONCLUSIVE": S.STATUS["partial"],
              "NOT EVALUABLE": S.STATUS["blocked"], "SUPPORTED": S.STATUS["implemented"]}
    # Box and cursor geometry are computed from real font metrics in this axes' own coordinate
    # space. Hand-tuned constants put the text through the bottom border, because one text line
    # is (points / 72) inches divided by the axes height in inches -- not a round number.
    fig.canvas.draw()
    ax_h_in = bx.get_position().height * fig.get_figheight()
    LS = 1.45

    def line(points: float) -> float:
        return points * LS / 72.0 / ax_h_in

    HEAD_PT, HYP_PT, CAV_PT = 8.2, 6.4, 6.0
    HYP_W, CAV_W, HYP_N, CAV_N = 86, 94, 2, 3
    PAD = line(HYP_PT) * 0.45

    blocks = [(k, _wrap(h, HYP_W, HYP_N), v, _wrap(c, CAV_W, CAV_N)) for k, h, v, c in verdicts]
    heights = [PAD * 2 + line(HEAD_PT) + line(HYP_PT) * (hb.count("\n") + 1)
               + (line(CAV_PT) * (cb.count("\n") + 1) + PAD * 0.5 if cb else 0)
               for _, hb, _, cb in blocks]
    gap = max((1.0 - sum(heights)) / max(len(blocks) - 1, 1), 0.0)
    yy = 1.0
    for (key, hyp, verdict, caveat), h in zip(blocks, heights):
        col = colour.get(verdict, S.MUTED)
        bx.add_patch(plt.Rectangle((0.01, yy - h), 0.98, h, facecolor="#fafaf8",
                                   edgecolor=col, linewidth=1.3, zorder=2))
        cursor = yy - PAD
        bx.text(0.028, cursor, f"{key}   {verdict}", fontsize=HEAD_PT, color=col,
                fontweight="bold", va="top", zorder=3)
        cursor -= line(HEAD_PT)
        bx.text(0.028, cursor, hyp, fontsize=HYP_PT, color=S.INK, va="top",
                linespacing=LS, zorder=3)
        if caveat:
            cursor -= line(HYP_PT) * (hyp.count("\n") + 1) + PAD * 0.5
            bx.text(0.028, cursor, caveat, fontsize=CAV_PT, color=S.INK2, va="top",
                    linespacing=LS, zorder=3)
        yy -= h + gap

    e12_note = e12["cells"]
    n_cells = sum(1 for c in e12_note.values() if c.get("status") == "evaluated")
    fig.suptitle("Cross-module integration: the four couplings, as tested",
                 x=0.006, ha="left", fontsize=11.0, color=S.INK, y=0.975)
    common = src[src.common_learner].sort_values("origin")
    picked = src[~src.common_learner].sort_values("origin")
    sig = src[src.significant]
    S.footnote(fig,
               f"Panel (a) re-analyses cached per-seed predictions from {n_cells} "
               "learner-by-origin cells without refitting anything. Read the two groups "
               "separately. Holding the learner fixed — mlp is the only one run at both origins — "
               f"the effect is {common.effect.iloc[0]:+.4f} at origin {common.origin.iloc[0]} and "
               f"{common.effect.iloc[1]:+.4f} at origin {common.origin.iloc[1]}: opposite in sign "
               "and significant at neither, so the family-feature coupling does not reproduce "
               "across origins when the learner is held constant. The one cell that does reach "
               f"significance after correction is {sig.learner.iloc[0]} at origin "
               f"{sig.origin.iloc[0]} ({sig.effect.iloc[0]:+.4f}, BH p = "
               f"{sig.p_adjusted_bh.iloc[0]:.3f}), but {picked.learner.iloc[0]} and "
               f"{picked.learner.iloc[1]} are each the learner their own origin selected, so a "
               "result there cannot be separated from the choice of learner. That is why C1 is "
               "recorded as partially supported rather than supported. Panel (b) quotes each "
               "coupling's verdict and leading caveat verbatim from "
               "outputs/phase_e/phase_e_results.json; an ellipsis marks where a caveat is cut. "
               "C4 carries no "
               "interval because it has no data: the telemetry corpora are anonymised, the "
               "conjunction data are anonymised by construction, and the two share zero object "
               "identities, so the coupling cannot be evaluated at all rather than having been "
               "evaluated and failed. Every result here is a post-hoc re-analysis of test sets "
               "scored by earlier studies, not a confirmatory test.", y=0.185)

    S.save_source(src, data, "diagnostics_c1_family_effect")
    S.save_source(pd.DataFrame([{"coupling": k, "hypothesis": h, "verdict": v, "caveat": c}
                                for k, h, v, c in verdicts]),
                  data, "diagnostics_coupling_verdicts")
    return S.save(fig, out, "Figure_G3_coupling_failure"), src


def _wrap(text: str, width: int, max_lines: int = 3) -> str:
    """Wrap to at most `max_lines`, marking the cut so a truncation is never mistaken for the end."""
    import textwrap
    lines = textwrap.wrap(text, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;") + " …"
    return "\n".join(lines)


FIGURES = [("G1", fig_g1), ("G2", fig_g2), ("G3", fig_g3)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="paper/figures/diagnostics")
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
