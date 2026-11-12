"""Digital-twin system outputs, read from one real versioned run.

    python scripts/figures/fig_system_outputs.py

Everything here comes from ``outputs/twin/as_of_2026-10-27/``, a single dated snapshot whose file
digests are recorded in ``FORECAST_SHA256.txt``. No satellite state, probability or interval is
invented, and no illustrative object is substituted for a real one.

Two things this figure set deliberately does *not* do. It does not present these forecasts as
validated: the 68-day follow-up window for the 2026-10-27 snapshot has not elapsed, so the console
marks prospective validation as blocked and so does this figure. And it does not hide the known
defect: 123 of the 13,238 objects carrying lifetime-model probabilities have cross-horizon
incoherent ``p_lifetime_*`` values, that record is preserved rather than repaired, and the panel
that would be affected by it says so.
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
from matplotlib.patches import Patch  # noqa: E402

TWIN = "outputs/twin/as_of_2026-10-27"
HORIZONS = ("30d", "90d", "1yr")


def fig_s1(root: Path, out: Path, data: Path):
    frame = pd.read_csv(root / f"{TWIN}/forecast_table.csv.gz", low_memory=False)
    summary = json.loads((root / f"{TWIN}/summary.json").read_text())
    top = pd.read_csv(root / f"{TWIN}/top50_reentry_30d.csv")

    # L17: the preserved cross-horizon incoherence, recomputed here rather than quoted
    lcols = [f"p_lifetime_{h}" for h in HORIZONS]
    lsub = frame[lcols].dropna()
    l17 = int(((lsub[lcols[0]] > lsub[lcols[1]] + 1e-12)
               | (lsub[lcols[1]] > lsub[lcols[2]] + 1e-12)).sum())
    fcols = [f"p_{h}" for h in HORIZONS]
    fsub = frame[fcols].dropna()
    final_bad = int(((fsub[fcols[0]] > fsub[fcols[1]] + 1e-12)
                     | (fsub[fcols[1]] > fsub[fcols[2]] + 1e-12)).sum())

    fig = plt.figure(figsize=(11.8, 8.0))
    gs = fig.add_gridspec(2, 3, height_ratios=(1.0, 1.15), hspace=0.52, wspace=0.38,
                          left=0.072, right=0.978, top=0.895, bottom=0.175)

    # ---- (a) population by decay regime and object class
    ax = fig.add_subplot(gs[0, 0])
    regimes = summary["regime_counts"]
    order = ["natural_decay", "operator_controlled", "unknown"]
    cols = [S.C1, S.C3, "#b9b9b3"]
    vals = [regimes[k] for k in order]
    ax.bar(range(len(order)), vals, color=cols, edgecolor="white", linewidth=1.2,
           width=0.62, zorder=3)
    for i, v in enumerate(vals):
        ax.text(i, v + max(vals) * 0.025, f"{v:,}", ha="center", fontsize=7.8, color=S.INK)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([k.replace("_", "\n") for k in order], fontsize=7.4)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_ylabel("catalogued objects")
    S.panel_title(ax, f"(a) Decay regime, {summary['objects']:,} objects")
    S.grid(ax, "y")
    ax.text(0.98, 0.96, "regime decides which\nmodel may speak",
            transform=ax.transAxes, fontsize=6.8, color=S.INK2, ha="right", va="top",
            linespacing=1.5)

    # ---- (b) where the re-entry probability mass sits
    bx = fig.add_subplot(gs[0, 1])
    nat = frame[frame.regime == "natural_decay"]
    for h, col, mk in zip(HORIZONS, (S.C1, S.C3, S.C4), ("o", "s", "^")):
        p = nat[f"p_{h}"].dropna()
        xs = np.sort(p.to_numpy())[::-1]
        bx.plot(np.arange(1, len(xs) + 1), xs, color=col, lw=1.9, label=f"P(re-entry ≤ {h})",
                zorder=3)
    bx.set_xscale("log")
    bx.set_xlabel("objects, ranked by probability (log scale)")
    bx.set_ylabel("predicted probability")
    bx.set_ylim(-0.03, 1.03)
    S.panel_title(bx, f"(b) Re-entry probability, natural-decay set")
    S.grid(bx, "both")
    bx.legend(fontsize=7.0, loc="upper right")
    above = int((nat.p_30d > 0.5).sum())
    bx.text(0.03, 0.12, f"{above} objects above 0.5 at 30 d",
            transform=bx.transAxes, fontsize=7.0, color=S.INK2)

    # ---- (c) expected re-entry counts: the three variants disagree
    cx = fig.add_subplot(gs[0, 2])
    variants = summary["expected_reentries_uncontrolled_by_variant"]
    names = ["physics_history", "physics_prior", "lifetime"]
    width = 0.26
    for i, n in enumerate(names):
        vals = [variants[n][h] for h in HORIZONS]
        cx.bar(np.arange(len(HORIZONS)) + (i - 1) * width, vals, width=width - 0.02,
               color=[S.C1, S.C3, S.C4][i], edgecolor="white", linewidth=0.9,
               label=n, zorder=3)
    cx.set_xticks(np.arange(len(HORIZONS)))
    cx.set_xticklabels(HORIZONS, fontsize=8.0)
    cx.set_ylabel("expected re-entries")
    S.panel_title(cx, "(c) Expected counts by model variant")
    S.grid(cx, "y")
    cx.legend(fontsize=6.8, loc="upper left")
    ratio = variants["lifetime"]["30d"] / variants["physics_history"]["30d"]
    cx.text(0.035, 0.66, f"the variants disagree\nby {ratio:.1f}× at 30 d",
            transform=cx.transAxes, fontsize=7.0, color=S.C4, ha="left", va="top",
            linespacing=1.5, fontweight="bold")

    # ---- (d) the highest-priority objects, with their intervals
    dx = fig.add_subplot(gs[1, :2])
    show = top.head(12).copy()
    key = "norad" if "norad" in show.columns else show.columns[0]
    y = np.arange(len(show))[::-1]
    # The published top-50 file carries the 90% interval, not the 80%. Resolve it from the columns
    # that are actually present and name the level on the axis, so the figure cannot claim one
    # level while drawing another.
    level = next((lv for lv in ("90", "80")
                  if {f"lo{lv}_days", f"hi{lv}_days"} <= set(show.columns)), None)
    if level is None or "median_days" not in show.columns:
        raise KeyError(f"no interval columns in top50_reentry_30d.csv: {list(show.columns)}")
    lo, hi = show[f"lo{level}_days"], show[f"hi{level}_days"]
    for yi, a, b, med in zip(y, lo, hi, show.median_days):
        dx.plot([a, b], [yi, yi], color=S.C1, lw=2.0, solid_capstyle="round", zorder=3)
        dx.scatter(med, yi, s=70, color=S.C1, edgecolor="white", linewidth=1.3, zorder=4)
    dx.set_xlabel(f"predicted days to re-entry  ({level}% interval, median marked)")
    dx.set_xscale("log")
    labels = []
    for r in show.itertuples():
        name = getattr(r, "Name", "") or ""
        labels.append(f"{getattr(r, key)}  {str(name)[:22]}")
    dx.set_yticks(y)
    dx.set_yticklabels(labels, fontsize=6.8)
    dx.set_ylim(-0.7, len(show) - 0.3)
    # The top of this list is saturated: repeating an identical probability on every row would be
    # noise, and worse, would imply a ranking among them that the numbers do not support.
    p_unique = show.p_30d.round(6).nunique()
    tie_note = (f"all {len(show)} at p₃₀ = {show.p_30d.iloc[0]:.3f} — the order among them is "
                f"not meaningful" if p_unique == 1 else
                f"{p_unique} distinct values of p₃₀ among these {len(show)}")
    S.panel_title(dx, "(d) Twelve highest-priority objects by P(re-entry ≤ 30 d)")
    dx.text(0.33, 0.03, tie_note, transform=dx.transAxes, fontsize=7.2, color=S.C4,
            ha="left", va="bottom", fontweight="bold")
    S.grid(dx, "x")
    dx.spines["left"].set_visible(False)
    dx.tick_params(axis="y", length=0)
    for yi, r in zip(y, show.itertuples()):
        dx.text(1.012, yi, f"{r.type1}   median {r.median_days:.2f} d",
                transform=dx.get_yaxis_transform(),
                va="center", ha="left", fontsize=6.6, color=S.INK2)

    # ---- (e) evidence state: what the system refuses to answer
    ex = fig.add_subplot(gs[1, 2])
    ex.set_xlim(0, 1)
    ex.set_ylim(0, 1)
    ex.axis("off")
    S.panel_title(ex, "(e) Evidence state and known defects")
    hist = summary["history_kinds"]
    lines = [
        ("provenance", f"snapshot as_of {summary['as_of']}, digests in FORECAST_SHA256.txt",
         S.STATUS["implemented"]),
        ("evidence depth", "  ·  ".join(f"{k}: {v:,}" for k, v in hist.items()),
         S.STATUS["implemented"]),
        ("area-to-mass", f"{int((frame.am_source != 'design').sum()):,} of "
                         f"{len(frame):,} objects use a class prior",
         S.STATUS["partial"]),
        ("L17 defect", f"{l17} of {len(lsub):,} objects have incoherent p_lifetime_* "
                       f"across horizons; preserved, not repaired",
         S.STATUS["blocked"]),
        ("ranking column", f"top-50 ranks on p_30d, which is coherent for all "
                           f"{len(fsub):,} objects ({final_bad} violations)",
         S.STATUS["implemented"]),
        ("prospective test", "blocked: the follow-up window for this snapshot has not elapsed",
         S.STATUS["blocked"]),
    ]
    import textwrap
    fig.canvas.draw()
    ax_h_in = ex.get_position().height * fig.get_figheight()

    def line(pt, ls=1.4):
        return pt * ls / 72.0 / ax_h_in

    # Pick the largest type size at which the six blocks still fit the panel, rather than trusting
    # a hand-chosen size: at a fixed size the last block printed past the bottom of the axes.
    GAP = 0.010
    for head_pt, body_pt, wrap_w in ((7.4, 6.3, 46), (7.0, 6.0, 49), (6.6, 5.7, 53),
                                     (6.2, 5.4, 57), (5.8, 5.1, 61)):
        wraps = ["\n".join(textwrap.wrap(b, wrap_w)) for _, b, _ in lines]
        heights = [line(head_pt) + line(body_pt) * (w.count("\n") + 1) + line(body_pt) * 0.55
                   for w in wraps]
        if sum(heights) + GAP * (len(lines) - 1) <= 1.0:
            break
    yy = 1.0
    for (title, _, col), wrapped, h in zip(lines, wraps, heights):
        ex.add_patch(plt.Rectangle((0.0, yy - h), 1.0, h, facecolor="#fafaf8",
                                   edgecolor=col, linewidth=1.2, zorder=2))
        ex.text(0.028, yy - line(body_pt) * 0.28, title, fontsize=head_pt, color=col,
                fontweight="bold", va="top", zorder=3)
        ex.text(0.028, yy - line(head_pt) - line(body_pt) * 0.18, wrapped, fontsize=body_pt,
                color=S.INK, va="top", linespacing=1.4, zorder=3)
        yy -= h + GAP

    src = pd.DataFrame([
        {"quantity": "objects in snapshot", "value": summary["objects"]},
        {"quantity": "natural_decay", "value": regimes["natural_decay"]},
        {"quantity": "operator_controlled", "value": regimes["operator_controlled"]},
        {"quantity": "unknown regime", "value": regimes["unknown"]},
        {"quantity": "objects with p_30d > 0.5 (natural decay)", "value": above},
        {"quantity": "expected re-entries 30d, physics_history",
         "value": variants["physics_history"]["30d"]},
        {"quantity": "expected re-entries 30d, physics_prior",
         "value": variants["physics_prior"]["30d"]},
        {"quantity": "expected re-entries 30d, lifetime", "value": variants["lifetime"]["30d"]},
        {"quantity": "L17 incoherent p_lifetime_* records", "value": l17},
        {"quantity": "objects with p_lifetime_* present", "value": len(lsub)},
        {"quantity": "incoherent p_* (ranking column) records", "value": final_bad},
        {"quantity": "objects with p_* present", "value": len(fsub)},
    ])

    fig.suptitle(f"COSMOS-AI digital-twin snapshot {summary['as_of']}: "
                 f"real outputs from one versioned run",
                 x=0.006, ha="left", fontsize=11.0, color=S.INK, y=0.975)
    S.footnote(fig,
               "Every number is read from the dated snapshot; nothing is simulated for display. "
               "Panel (c) is the most important caution in this set: the three re-entry variants "
               f"the system can run disagree by {ratio:.1f}× on the 30-day expected count, so a "
               "single headline count from this twin would be an artefact of the variant chosen, "
               "and the deployed configuration reports the physics-history variant. Panel (d) "
               "shows genuine per-object forecasts with the interval level the published file "
               "carries; they are predictions "
               "awaiting a follow-up snapshot, not verified outcomes, and the panel is not "
               "evidence that the system is accurate. Panel (e) records the evidence state "
               f"including the preserved L17 defect: {l17} objects carry cross-horizon incoherent "
               "lifetime probabilities. The top-50 ranking is unaffected because it ranks on the "
               f"gated p_30d column, which is coherent for all {len(fsub):,} objects — that was "
               "verified rather than assumed. Values are in "
               "paper/figures/data/twin_snapshot_summary.csv.", y=0.115)

    S.save_source(src, data, "twin_snapshot_summary")
    return S.save(fig, out, "Figure_S1_twin_snapshot"), src


FIGURES = [("S1", fig_s1)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="paper/figures/system_outputs")
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
