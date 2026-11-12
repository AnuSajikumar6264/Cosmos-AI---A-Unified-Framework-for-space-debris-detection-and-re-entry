"""Generate G5 figures from the executed experiment outputs.

Every figure is drawn from a results JSON written by an experiment script, so no figure can
show a number that was not computed. Missing inputs produce a skip message, never a synthetic
panel.

    python scripts/g5_figures.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from cosmos.ai.provenance import ROOT  # noqa: E402

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "legend.frameon": False,
})

INK = "#1b3d5c"
ACCENT = "#1d6fa5"
WARN = "#c9622f"
MUTED = "#8192a4"


def _load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def figure_rank_by_slice(rolling: dict, out: Path) -> str | None:
    usable = [s for s in rolling["slices"] if s["status"] == "evaluated"]
    if not usable:
        return None
    labels = [f"o{s['origin']}\n{s['launch_year']}" for s in usable]
    show = ["robust_median_blend", "tabicl", "cosmos_gated", "physics_only", "equal_average"]
    colours = {"robust_median_blend": ACCENT, "cosmos_gated": WARN,
               "physics_only": "#5a7d5a", "tabicl": INK, "equal_average": MUTED}

    fig, ax = plt.subplots(figsize=(8.4, 3.2))
    for model in show:
        ranks = [s["ranks"].get(model) for s in usable]
        if all(r is None for r in ranks):
            continue
        ax.plot(range(len(usable)), ranks, marker="o", ms=4, lw=1.4,
                color=colours.get(model, MUTED),
                label=model.replace("_", " "))
    ax.set_xticks(range(len(usable)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_ylabel("rank (1 = best)")
    ax.set_xlabel("evaluation slice (forecast origin / launch year)", labelpad=2)
    ax.set_title("Model rank is not stable across launch-epoch slices", loc="left")
    ax.legend(ncol=2, fontsize=7.5, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    path = out / "fig_g5_rank_by_slice.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def figure_cap_mass(causal: dict, out: Path) -> str | None:
    origins = [o for o in ("2011", "2016") if causal["results"].get(o, {}).get("status") == "evaluated"]
    if not origins:
        return None
    splits = ("train", "tuneA", "tuneB", "test")
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    width = 0.35
    for index, origin in enumerate(origins):
        census = causal["results"][origin]["census"]
        values = [census[s]["at_cap_fraction"] for s in splits]
        ax.bar(np.arange(len(splits)) + index * width, values, width,
               label=f"origin {origin}", color=[ACCENT, WARN][index], alpha=0.85)
    ax.set_xticks(np.arange(len(splits)) + width / 2)
    ax.set_xticklabels(splits)
    ax.set_ylabel("fraction at the 5-year cap")
    ax.set_title("Target point mass differs between selection and test,\nand reverses direction",
                 loc="left")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = out / "fig_g5_cap_mass.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def figure_coverage_by_slice(rolling: dict, out: Path) -> str | None:
    usable = [s for s in rolling["slices"] if s["status"] == "evaluated"]
    if not usable:
        return None
    labels = [f"{s['origin'][-2:]}/{s['launch_year']}" for s in usable]
    models = ("cosmos_gated", "robust_mean_blend", "robust_median_blend")
    colours = {"cosmos_gated": WARN, "robust_mean_blend": ACCENT,
               "robust_median_blend": MUTED}

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.2), sharey=True)
    for ax, level, nominal in zip(axes, ("cov80", "cov90"), (0.80, 0.90)):
        for model in models:
            values = [s["coverage"].get(model, {}).get(level, {}).get("empirical_coverage")
                      for s in usable]
            if all(v is None for v in values):
                continue
            ax.plot(range(len(usable)), values, marker="o", ms=4, lw=1.4,
                    color=colours[model], label=model.replace("_", " "))
        ax.axhline(nominal, color="k", lw=1.0, ls="--", label=f"nominal {nominal:.2f}")
        ax.set_xticks(range(len(usable)))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_title(f"{int(nominal * 100)} % interval", loc="left")
    axes[0].set_ylabel("empirical coverage")
    axes[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Empirical coverage across evaluation slices", x=0.02, ha="left")
    fig.tight_layout()
    path = out / "fig_g5_coverage_by_slice.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def figure_selection_transfer(causal: dict, out: Path) -> str | None:
    rows = []
    for origin in ("2011", "2016"):
        entry = causal["results"].get(origin, {})
        if entry.get("status") != "evaluated":
            continue
        frame = entry["per_model"]
        tuned = [(r["tuneA_pinball"], r["test_pinball"], r["model"])
                 for r in frame if r.get("tuneA_pinball") is not None]
        if tuned:
            rows.append((origin, tuned))
    if not rows:
        return None

    fig, axes = plt.subplots(1, len(rows), figsize=(3.6 * len(rows), 3.2))
    axes = np.atleast_1d(axes)
    for ax, (origin, tuned) in zip(axes, rows):
        x = [t[0] for t in tuned]
        y = [t[1] for t in tuned]
        ax.scatter(x, y, s=28, color=ACCENT, zorder=3)
        for xi, yi, name in tuned:
            ax.annotate(name, (xi, yi), fontsize=6, xytext=(3, 3),
                        textcoords="offset points", color=MUTED)
        rho = causal["results"][origin]["rank_correlations"].get(
            "spearman_tuneA_vs_test_overall")
        ax.set_title(f"origin {origin}  (Spearman {rho:+.3f})", loc="left")
        ax.set_xlabel("tune-A pinball (selection)")
        ax.set_ylabel("test pinball (evaluation)")
    fig.suptitle("Selection score carries no rank information about forward performance",
                 x=0.02, ha="left")
    fig.tight_layout()
    path = out / "fig_g5_selection_transfer.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def figure_promotion(rolling: dict, out: Path) -> str | None:
    promotion = rolling.get("promotion") or {}
    if not promotion:
        return None
    candidates = list(promotion)
    fig, axes = plt.subplots(len(candidates), 1, figsize=(7.0, 2.2 * len(candidates)),
                             sharex=True)
    axes = np.atleast_1d(axes)
    for ax, candidate in zip(axes, candidates):
        per_slice = promotion[candidate]["per_slice"]
        labels = [e["slice"].split("/")[1] for e in per_slice]
        deltas = [e["delta"] for e in per_slice]
        los = [e["ci95_lo"] for e in per_slice]
        his = [e["ci95_hi"] for e in per_slice]
        colours = [ACCENT if e["significant"] and e["delta"] < 0
                   else WARN if e["significant"] else MUTED for e in per_slice]
        positions = np.arange(len(per_slice))
        ax.errorbar(positions, deltas,
                    yerr=[np.array(deltas) - np.array(los),
                          np.array(his) - np.array(deltas)],
                    fmt="none", ecolor=MUTED, lw=1.0, capsize=2)
        ax.scatter(positions, deltas, c=colours, s=30, zorder=3)
        ax.axhline(0, color="k", lw=1.0)
        ax.set_ylabel("Δ pinball\nvs deployed")
        ax.set_title(f"{candidate.replace('_', ' ')} — {promotion[candidate]['verdict']}",
                     loc="left", fontsize=9)
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    axes[-1].set_xlabel("evaluation slice (origin / launch year); below zero = candidate better")
    fig.tight_layout()
    path = out / "fig_g5_promotion.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path.name


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/g5_figures")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    rolling = _load(root / "outputs" / "g5_rolling" / "g5_rolling_results.json")
    causal = _load(root / "outputs" / "g5_censoring" / "g5_causal_results.json")

    written = []
    if rolling:
        for builder in (figure_rank_by_slice, figure_coverage_by_slice, figure_promotion):
            name = builder(rolling, out_dir)
            if name:
                written.append(name)
    else:
        print("  skip: g5_rolling results absent")
    if causal:
        for builder in (figure_cap_mass, figure_selection_transfer):
            name = builder(causal, out_dir)
            if name:
                written.append(name)
    else:
        print("  skip: g5_censoring results absent")

    for name in written:
        print(f"  wrote {name}")
    print(f"\n{len(written)} figure(s) in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
