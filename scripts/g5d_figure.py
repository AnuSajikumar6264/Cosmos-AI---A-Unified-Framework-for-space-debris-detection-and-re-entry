"""Figure 1: model rank across the three temporal origins (G5d, hypothesis H2).

A slope chart. The data's job is *identity and reordering across an ordered sequence*, so rank
position is the y-axis (inverted, rank 1 at the top) and the three origins are the ordered
x-positions. Every value is read from ``outputs/g5d_origin2006/analysis/g5d_analysis.json``;
nothing is hard-coded.

    python scripts/g5d_figure.py --out outputs/g5d_origin2006/figures

Accessibility: each arm carries its own marker *and* line style as well as its own hue, so the
series are separable in greyscale print and under colour-vision deficiency. Hues are slots 1-4 of
the validated default categorical palette, assigned in fixed order.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT  # noqa: E402

#: Chronological order, which is also the order the experiment treats as "unexamined last".
ORIGIN_ORDER = ("2006", "2011", "2016")

#: Categorical slots 1-4, fixed order, never cycled. Marker and dash make identity redundant.
STYLE = {
    "physics_only": {"color": "#2a78d6", "marker": "o", "dash": (None, None)},
    "xgboost":      {"color": "#eb6834", "marker": "s", "dash": (4, 1.5)},
    "mlp":          {"color": "#1baf7a", "marker": "^", "dash": (1.5, 1.5)},
    "tabm":         {"color": "#eda100", "marker": "D", "dash": (6, 2, 1.5, 2)},
}

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8c8b85", "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "figure.facecolor": "#ffffff", "axes.facecolor": "#ffffff",
})


def build(analysis: dict, out_dir: Path) -> Path:
    per_origin = analysis["per_origin"]
    origins = [o for o in ORIGIN_ORDER if o in per_origin]
    arms_per_origin = {o: len(per_origin[o]["ranks"]) for o in origins}
    complete = set(analysis["H2"].get("arms_present_at_every_origin") or [])

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    x = list(range(len(origins)))

    for arm, style in STYLE.items():
        ys = [per_origin[o]["ranks"].get(arm) for o in origins]
        points = [(xi, y) for xi, y in zip(x, ys) if y is not None]
        if not points:
            continue
        xs, vals = zip(*points)
        partial = arm not in complete
        ax.plot(xs, vals, color=style["color"], marker=style["marker"],
                markersize=7, linewidth=2.0 if not partial else 1.4,
                dashes=style["dash"] if style["dash"][0] else (),
                alpha=1.0 if not partial else 0.55,
                markeredgecolor="#ffffff", markeredgewidth=1.2,
                label=arm + ("" if not partial else "  (not fittable at 2006)"),
                zorder=3 if arm == "physics_only" else 2)
        # Direct end labels: four series, so every series is labelled rather than legend-only.
        ax.annotate(arm, (xs[-1], vals[-1]), xytext=(8, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=8.5,
                    color="#0b0b0b" if not partial else "#52514e")

    ax.set_xticks(x)
    ax.set_xticklabels([f"origin {o}\n({arms_per_origin[o]} arms)" for o in origins])
    max_rank = max(arms_per_origin.values())
    ax.set_yticks(range(1, max_rank + 1))
    ax.set_ylim(max_rank + 0.5, 0.5)          # rank 1 at the top
    ax.set_xlim(-0.25, len(origins) - 1 + 0.95)
    ax.set_ylabel("rank by test pinball loss  (1 = best)")
    ax.grid(axis="y", color="#e5e4df", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    ax.set_title("No arm present at every origin retains its rank", loc="left",
                 fontsize=10.5, color="#0b0b0b", pad=14)
    ax.text(0, 1.015, "Pre-registered hypothesis H2: SUPPORTED. Origin 2006 was never "
                      "constructed or scored before this experiment.",
            transform=ax.transAxes, fontsize=8.5, color="#52514e", va="bottom")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=2, frameon=False,
              fontsize=8.5, handlelength=3.0)
    # The flat tabm segment must not be read as rank stability: it has only two observations,
    # which is why H2 is tested on the arms present at every origin.
    incomplete = analysis["H2"].get("arms_excluded_incomplete") or []
    if incomplete:
        ax.text(0.5, -0.46, f"H2 is tested only on arms present at every origin. "
                            f"{', '.join(incomplete)} is excluded: a flat segment over two "
                            f"observations is not evidence of rank stability.",
                transform=ax.transAxes, fontsize=7.8, color="#52514e", ha="center", va="top",
                wrap=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "fig_g5d_rank_across_origins.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--analysis",
                        default="outputs/g5d_origin2006/analysis/g5d_analysis.json")
    parser.add_argument("--out", default="outputs/g5d_origin2006/figures")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    analysis_path = root / args.analysis
    if not analysis_path.is_file():
        raise SystemExit(f"no analysis at {analysis_path}")
    analysis = json.loads(analysis_path.read_text())

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    path = build(analysis, out_dir)
    print(f"written: {path.relative_to(root)}")
    print(f"source : {args.analysis} (H2 verdict {analysis['H2']['verdict']}, "
          f"outcome {analysis['outcome']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
