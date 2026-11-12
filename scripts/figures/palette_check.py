"""Computable categorical-palette checks, ported from the data-visualisation reference validator.

The reference implementation ships as JavaScript (`validate_palette.js`); no Node runtime is
available in this environment, so the measurable checks are reproduced here one-for-one. The
thresholds, the OKLab matrices and the Machado-Oliveira-Fernandes (2009) severity-1.0 colour-vision
transforms are copied verbatim from that file so the two agree numerically.

Checks implemented (the ones measurable from hex values alone):

    2.  lightness band        OKLCH L inside the mode's band
    3.  chroma floor          OKLCH C >= floor, below which a hue reads as grey
    4.  CVD separation        OKLab dE x100 between slots under simulated protan/deutan
    4b. normal-vision floor   worst OKLab dE x100 on the active pair list, unsimulated
    5.  contrast vs surface   WCAG ratio of each mark against the chart surface

Checks 1 (fixed hue order) and 6 (values come from the documented palette) are structural and are
enforced by `figstyle.py`, which assigns slots in a fixed order and never cycles them.

    python scripts/figures/palette_check.py "#2a78d6,#eb6834" --mode light
"""
from __future__ import annotations

import argparse
import math
import re
import sys

# ---------------------------------------------------------------------- thresholds (verbatim)
BAND = {"light": (0.43, 0.77), "dark": (0.48, 0.67)}   # OKLCH L
CHROMA_FLOOR = 0.10                                     # OKLCH C
CVD_TARGET, CVD_FLOOR = 8.0, 6.0                        # OKLab dE x100, min(protan, deutan)
NORMAL_FLOOR = 15.0                                     # OKLab dE x100, unsimulated, worst pair
CONTRAST_MIN = 3.0                                      # WCAG vs surface
DEFAULT_SURFACE = {"light": "#fcfcfb", "dark": "#1a1a19"}

MACHADO = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779),
               (-0.078411, 0.930809, 0.147602),
               (0.004733, 0.691367, 0.303900)),
}

# Input boundary. Kept in lockstep with the JavaScript twin: the shared whitespace set is the
# intersection of what JS trim() and Python str.strip() remove, which also covers the NBSP and
# em-space padding picked up when hex lists are copied out of a rendered page.
_WS = "[ \t\n\v\f\r   -     　]+"
_HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")


def _strip(value: str) -> str:
    return re.sub(f"^{_WS}|{_WS}$", "", value)


def split_colors(raw: str) -> list[str]:
    return [c for c in (_strip(p) for p in (raw or "").split(",")) if c]


def _check_hex(value: str, what: str) -> str:
    if not _HEX.match(value):
        raise ValueError(f"{what} is not a 6-digit hex colour: {value!r}")
    return value if value.startswith("#") else "#" + value


# ---------------------------------------------------------------------- colour conversions
def _srgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _s2lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin(h: str) -> tuple[float, float, float]:
    return tuple(_s2lin(c) for c in _srgb(h))


def _rel_lum(h: str) -> float:
    r, g, b = _lin(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_rel_lum(a), _rel_lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _oklab_from_lin(rgb) -> tuple[float, float, float]:
    r, g, b = rgb
    l = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklch(h: str) -> tuple[float, float]:
    L, a, b = _oklab_from_lin(_lin(h))
    return L, math.hypot(a, b)


def _simulate(h: str, kind: str) -> tuple[float, float, float]:
    r, g, b = _lin(h)
    M = MACHADO[kind]
    return tuple(min(1.0, max(0.0, M[i][0] * r + M[i][1] * g + M[i][2] * b)) for i in range(3))


def delta_e(h1: str, h2: str, kind: str | None = None) -> float:
    a = _oklab_from_lin(_simulate(h1, kind) if kind else _lin(h1))
    b = _oklab_from_lin(_simulate(h2, kind) if kind else _lin(h2))
    return 100 * math.dist(a, b)


# ---------------------------------------------------------------------- the checks
def validate(palette: list[str], mode: str = "light", surface: str | None = None,
             pairs: str = "adjacent") -> tuple[bool, list[tuple[str, object, str]]]:
    palette = [_check_hex(c, "palette entry") for c in palette]
    surface = _check_hex(surface or DEFAULT_SURFACE[mode], "surface")
    lo, hi = BAND[mode]
    report: list[tuple[str, object, str]] = []
    ok = True

    offband = [(c, round(oklch(c)[0], 3)) for c in palette if not lo <= oklch(c)[0] <= hi]
    ok &= not offband
    report.append(("Lightness band", not offband,
                   f"outside band: {offband}" if offband
                   else f"all {len(palette)} inside L {lo}-{hi}"))

    lowc = [(c, round(oklch(c)[1], 3)) for c in palette if oklch(c)[1] < CHROMA_FLOOR]
    ok &= not lowc
    report.append(("Chroma floor", not lowc,
                   f"below floor (reads grey): {lowc}" if lowc
                   else f"all {len(palette)} >= {CHROMA_FLOOR}"))

    n = len(palette)
    if pairs == "all":
        pairlist = [(i, j) for i in range(n) for j in range(i + 1, n)]
    else:
        pairlist = [(i, i + 1) for i in range(n - 1)]
    label = "all-pairs" if pairs == "all" else "adjacent"

    worst = None
    for kind in ("protan", "deutan"):
        for i, j in pairlist:
            d = delta_e(palette[i], palette[j], kind)
            if worst is None or d < worst[0]:
                worst = (d, kind, palette[i], palette[j])
    tri = min((delta_e(palette[i], palette[j], "tritan") for i, j in pairlist), default=99.0)
    wd = worst[0] if worst else 99.0
    state = "pass" if wd >= CVD_TARGET else ("floor" if wd >= CVD_FLOOR else "fail")
    ok &= state != "fail"
    report.append(("CVD separation", state,
                   f"worst {label} {worst[3]}<->{worst[2]} dE {wd:.1f} ({worst[1]})"
                   f" | tritan {tri:.1f}" if worst else "n/a"))

    nworst = min(((delta_e(palette[i], palette[j]), palette[i], palette[j])
                  for i, j in pairlist), default=(99.0, "", ""))
    npass = nworst[0] >= NORMAL_FLOOR
    ok &= npass
    report.append(("Normal-vision floor", npass,
                   f"worst {label} {nworst[1]}<->{nworst[2]} dE {nworst[0]:.1f}"
                   f" (floor {NORMAL_FLOOR})"))

    weak = [(c, round(contrast(c, surface), 2)) for c in palette
            if contrast(c, surface) < CONTRAST_MIN]
    report.append(("Contrast vs surface", "warn" if weak else True,
                   f"below {CONTRAST_MIN}:1 on {surface} -> needs labels/texture: {weak}" if weak
                   else f"all {len(palette)} >= {CONTRAST_MIN}:1 on {surface}"))
    return ok, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("palette", help="comma-separated hex colours")
    ap.add_argument("--mode", default="light", choices=["light", "dark"])
    ap.add_argument("--surface", default=None)
    ap.add_argument("--pairs", default="adjacent", choices=["adjacent", "all"])
    args = ap.parse_args(argv)
    ok, report = validate(split_colors(args.palette), args.mode, args.surface, args.pairs)
    width = max(len(r[0]) for r in report)
    for name, state, detail in report:
        mark = {True: "PASS", False: "FAIL", "pass": "PASS",
                "floor": "WARN", "fail": "FAIL", "warn": "WARN"}[state]
        print(f"  {mark:4s}  {name:<{width}s}  {detail}")
    print(f"\n  overall: {'PASS' if ok else 'FAIL'}  (mode={args.mode}, pairs={args.pairs})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
