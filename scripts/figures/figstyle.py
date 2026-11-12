"""Shared visual identity, palette and save helpers for every COSMOS-AI publication figure.

One module so that all figures share typography, palette, grid weight and export settings. Nothing
here reads experiment data; the figure scripts do that and pass values in.

Palette
-------
`CAT` is the categorical sequence, assigned in **fixed slot order and never cycled**. It was not
chosen by eye: it is the output of a constrained search over OKLCH space, and it is checked by
`palette_check.py` (a Python port of the reference JavaScript validator, same thresholds and same
Machado-Oliveira-Fernandes severity-1.0 colour-vision transforms). On a white surface, all pairs:

    Lightness band       PASS   all 6 inside L 0.43-0.77
    Chroma floor         PASS   all 6 >= 0.1
    CVD separation       PASS   worst all-pairs dE 11.6 (deutan), target 8.0
    Normal-vision floor  PASS   worst all-pairs dE 15.0, floor 15.0
    Contrast vs surface  PASS   all 6 >= 3.0:1

Regenerate that report with:

    python scripts/figures/palette_check.py \
        "#224bb2,#c26201,#15957b,#9c256e,#4a7ae4,#834105" \
        --mode light --surface "#ffffff" --pairs all

Because `CAT` clears the all-pairs gate (not merely the adjacent one), the same slots are safe in
scatter and forest figures where every series is visible against every other. Every figure
additionally carries a distinct marker or a direct label, so identity is never colour alone.

`SEQ` is a single-hue light-to-dark ramp for magnitude. `STATUS` is reserved for implementation and
validation state in the architecture diagrams and is never reused as a data series.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# ------------------------------------------------------------------ palette (fixed slot order)
CAT = ("#224bb2", "#c26201", "#15957b", "#9c256e", "#4a7ae4", "#834105")
C1, C2, C3, C4, C5, C6 = CAT

# single hue, light -> dark, for magnitude
SEQ = ("#c3d3f5", "#8fabe8", "#5b82db", "#3059c4", "#1d3a80")

# reserved: implementation / validation state. Never a data series.
STATUS = {
    "implemented":   "#15957b",   # green
    "partial":       "#c26201",   # amber
    "proposed":      "#6b6b68",   # grey
    "blocked":       "#9c256e",   # magenta
    "validated":     "#224bb2",   # blue
}

INK = "#1d1d1b"        # primary text
INK2 = "#55554f"        # secondary text
MUTED = "#8c8b85"       # axes, grid, rules
SURFACE = "#ffffff"

rcparams = {
    "figure.dpi": 150,
    "savefig.dpi": 400,
    "font.size": 9,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "axes.linewidth": 0.8,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "grid.color": MUTED,
    "grid.linewidth": 0.6,
    "grid.alpha": 0.30,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "lines.linewidth": 2.0,
    "lines.markersize": 8,
    "pdf.fonttype": 42,     # embed as TrueType so reviewers can select text
    "ps.fonttype": 42,
    "svg.fonttype": "none",
}


def apply() -> None:
    plt.rcParams.update(rcparams)


def grid(ax, axis: str = "y") -> None:
    """Recessive grid, always behind the marks."""
    ax.grid(axis=axis, alpha=0.30, linewidth=0.6, color=MUTED)
    ax.set_axisbelow(True)


def panel_title(ax, text: str) -> None:
    ax.set_title(text, loc="left", fontsize=10, color=INK, pad=8)


def footnote(fig, text: str, y: float = -0.01) -> None:
    fig.text(0.005, y, text, fontsize=7.0, color=INK2, ha="left", va="top", wrap=True)


# ------------------------------------------------------------------ export
def save(fig, out_dir: Path, stem: str, formats=("png", "pdf", "svg")) -> list[Path]:
    """Write one figure in several formats. PNG at 400 dpi for review, PDF/SVG as vector source."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in formats:
        path = out_dir / f"{stem}.{ext}"
        fig.savefig(path, bbox_inches="tight", format=ext)
        written.append(path)
    plt.close(fig)
    return written


def save_source(frame, data_dir: Path, stem: str) -> Path:
    """Persist the exact numbers a figure plots, so the image is independently checkable."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{stem}.csv"
    frame.to_csv(path, index=False)
    return path


def save_source_json(obj, data_dir: Path, stem: str) -> Path:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{stem}.json"
    path.write_text(json.dumps(obj, indent=1, default=str))
    return path


# ------------------------------------------------------------------ diagram primitives
def box(ax, x, y, w, h, label, *, face="#ffffff", edge=MUTED, lw=1.0, fontsize=7.6,
        weight="normal", textcolor=None, ls="-", radius=0.012, zorder=3, va="center"):
    """Rounded node for the architecture diagrams. Coordinates are axis fractions."""
    from matplotlib.patches import FancyBboxPatch
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad=0,rounding_size={radius}",
                           linewidth=lw, edgecolor=edge, facecolor=face,
                           linestyle=ls, zorder=zorder)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va=va,
            fontsize=fontsize, color=textcolor or INK, fontweight=weight,
            zorder=zorder + 1, linespacing=1.35)
    return patch


def arrow(ax, start, end, *, color=MUTED, lw=1.1, ls="-", rad=0.0, zorder=2,
          style="-|>", shrink=0.0):
    from matplotlib.patches import FancyArrowPatch
    patch = FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=11,
                            linewidth=lw, color=color, linestyle=ls,
                            connectionstyle=f"arc3,rad={rad}", zorder=zorder,
                            shrinkA=shrink, shrinkB=shrink)
    ax.add_patch(patch)
    return patch


def blank_axes(fig, rect=(0, 0, 1, 1)):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return ax
