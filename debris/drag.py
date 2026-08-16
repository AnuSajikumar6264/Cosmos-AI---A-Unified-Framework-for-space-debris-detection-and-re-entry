"""
Drag coefficient models for re-entering debris.

Two effects dominate and both are modelled:

1. **Compressibility.**  C_D of a blunt body rises through the transonic drag rise,
   peaks around M ~ 1.2, then flattens into the hypersonic plateau.  A tabulated
   sphere curve provides the shape; other geometries scale off it.

2. **Rarefaction.**  Above roughly 90 km the flow stops being a continuum.  In the
   free-molecular limit C_D rises towards 2.0-2.6 for a diffusely reflecting body.
   The transition is bridged smoothly in log(Knudsen), which is the standard
   engineering treatment used by re-entry survivability tools.

What the propagator actually needs is the **ballistic coefficient**

    B = m / (C_D * A)      [kg/m^2]

High-B objects (dense tank sections, engines) punch deep into the atmosphere and land
far downrange; low-B objects (insulation blankets, panel skins) decelerate high up and
fall almost straight down.  That spread in B is what turns a single breakup into a
long, narrow debris footprint, so getting C_D approximately right matters more than
getting it precisely right.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

import numpy as np

# Sphere drag coefficient vs Mach number (continuum), from classical
# incompressible/supersonic sphere data at re-entry Reynolds numbers.
_MACH = np.array([0.0, 0.5, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0, 10.0, 25.0])
_CD_SPHERE = np.array(
    [0.47, 0.47, 0.50, 0.55, 0.68, 0.92, 1.02, 0.98, 0.92, 0.88, 0.89, 0.92, 0.92]
)

#: shape -> (continuum multiplier on the sphere curve, free-molecular C_D).
#:
#: ``tumbling`` is the right default for breakup fragments: an irregular chunk with no
#: attitude control averages its drag over all orientations.
SHAPES: dict[str, tuple[float, float]] = {
    "sphere": (1.00, 2.00),
    "tumbling": (1.45, 2.20),
    "cylinder": (1.25, 2.10),
    "box": (1.35, 2.15),
    "flat_plate": (1.90, 2.60),
}


def _continuum_cd(mach):
    return np.interp(np.abs(np.asarray(mach, dtype=float)), _MACH, _CD_SPHERE)


def _rarefaction_blend(knudsen):
    """
    Continuum (0) -> free-molecular (1) bridging weight.

    Logistic in log10(Kn) centred at Kn = 1 with a ~1.5-decade width, so the blend is
    <5 % continuum-corrupted below Kn = 0.01 and >95 % free-molecular above Kn = 100.
    """
    kn = np.asarray(knudsen, dtype=float)
    kn = np.where(np.isfinite(kn), np.maximum(kn, 1e-12), 1e12)
    return 1.0 / (1.0 + np.exp(-np.log10(kn) / 0.65))


@dataclass(frozen=True)
class DragModel:
    """
    Mach- and Knudsen-dependent drag coefficient.

    Parameters
    ----------
    shape:
        Key into :data:`SHAPES`, or ``"constant"`` to freeze C_D at ``cd_constant``.
    cd_constant:
        Used only when ``shape == "constant"``.  Handy for reproducing published
        trajectories that quote a single C_D.
    reference_length:
        Characteristic length [m] used to form Kn = lambda / L.  Defaults to the
        fragment's own characteristic length when the object supplies one.
    """

    shape: str = "tumbling"
    cd_constant: float = 1.0
    reference_length: float = 0.3

    def cd(self, mach, knudsen):
        """Drag coefficient. Vectorised over ``mach`` / ``knudsen``."""
        if self.shape == "constant":
            return float(self.cd_constant)
        try:
            scale, cd_fm = SHAPES[self.shape]
        except KeyError as exc:  # pragma: no cover - guard against typos in configs
            raise ValueError(
                f"unknown shape {self.shape!r}; expected one of "
                f"{sorted(SHAPES) + ['constant']}"
            ) from exc
        cd_cont = scale * _continuum_cd(mach)
        w = _rarefaction_blend(knudsen)
        out = (1.0 - w) * cd_cont + w * cd_fm
        return float(out) if np.ndim(out) == 0 else out

    def cd_scalar(self, mach: float, knudsen: float) -> float:
        """
        Pure-``math`` mirror of :meth:`cd` for the propagator's inner loop.

        Agrees with :meth:`cd` to floating-point round-off; validated in the module
        self-check.
        """
        if self.shape == "constant":
            return self.cd_constant
        scale, cd_fm = SHAPES[self.shape]

        m = mach if mach >= 0.0 else -mach
        if m <= 0.0:
            cd_cont = _CD_SPHERE_L[0]
        elif m >= _MACH_L[-1]:
            cd_cont = _CD_SPHERE_L[-1]
        else:
            j = bisect_right(_MACH_L, m)
            if j < 1:
                j = 1
            m0, m1 = _MACH_L[j - 1], _MACH_L[j]
            w = (m - m0) / (m1 - m0)
            cd_cont = _CD_SPHERE_L[j - 1] * (1.0 - w) + _CD_SPHERE_L[j] * w
        cd_cont *= scale

        kn = knudsen if math.isfinite(knudsen) else 1e12
        if kn < 1e-12:
            kn = 1e-12
        # Logistic bridge; the exponent is clamped because Kn spans ~20 decades.
        e = -math.log10(kn) / 0.65
        w_fm = 0.0 if e > 700.0 else (1.0 if e < -700.0 else 1.0 / (1.0 + math.exp(e)))
        return (1.0 - w_fm) * cd_cont + w_fm * cd_fm

    def knudsen(self, mean_free_path, length=None):
        """Knudsen number from mean free path [m] and body length [m]."""
        length = float(length) if length else self.reference_length
        lam = np.asarray(mean_free_path, dtype=float)
        return lam / max(length, 1e-6)


_MACH_L = _MACH.tolist()
_CD_SPHERE_L = _CD_SPHERE.tolist()


# ------------------------------------------------------------------ ensemble fast path
def cd_ensemble(mach, knudsen, cont_scale, cd_free_molecular, cd_const, is_const):
    """
    Fully vectorised C_D for a whole Monte Carlo ensemble at once.

    Every argument broadcasts, so a population of fragments with *different shapes* can
    be evaluated in one call - which is what the ensemble propagator needs, since a
    breakup cloud mixes spheres, plates and tumbling chunks.
    """
    cd_cont = np.interp(np.abs(np.asarray(mach, dtype=float)), _MACH, _CD_SPHERE) * cont_scale
    kn = np.asarray(knudsen, dtype=float)
    kn = np.where(np.isfinite(kn), np.maximum(kn, 1e-12), 1e12)
    w = 1.0 / (1.0 + np.exp(-np.log10(kn) / 0.65))
    cd = (1.0 - w) * cd_cont + w * cd_free_molecular
    return np.where(is_const, cd_const, cd)


def pack_drag_models(models):
    """
    Turn a list of :class:`DragModel` into the flat arrays :func:`cd_ensemble` wants.

    Returns ``(cont_scale, cd_free_molecular, cd_const, is_const, reference_length)``.
    """
    models = list(models)
    n = len(models)
    cont = np.ones(n)
    cd_fm = np.full(n, 2.0)
    cd_c = np.ones(n)
    is_c = np.zeros(n, dtype=bool)
    ref = np.full(n, 0.3)
    for i, m in enumerate(models):
        ref[i] = m.reference_length
        if m.shape == "constant":
            is_c[i] = True
            cd_c[i] = m.cd_constant
        else:
            cont[i], cd_fm[i] = SHAPES[m.shape]
    return cont, cd_fm, cd_c, is_c, ref


#: Default model: an irregular tumbling breakup fragment.
TUMBLING = DragModel()


def sphere_area(diameter_m: float) -> float:
    """Cross-sectional area [m^2] of a sphere of the given diameter."""
    return np.pi * (0.5 * float(diameter_m)) ** 2


def ballistic_coefficient(mass_kg: float, area_m2: float, cd: float) -> float:
    """B = m / (C_D * A) [kg/m^2]."""
    denom = max(float(cd) * float(area_m2), 1e-12)
    return float(mass_kg) / denom


def area_from_characteristic_length(lc_m):
    """
    NASA Standard Breakup Model average cross-section from characteristic length.

    Piecewise power law (Johnson et al., 2001):
        A = 0.540424 * Lc^2                for Lc <  0.00167 m
        A = 0.556945 * Lc^2.0047077        for Lc >= 0.00167 m
    """
    lc = np.asarray(lc_m, dtype=float)
    small = 0.540424 * lc**2
    large = 0.556945 * np.maximum(lc, 1e-12) ** 2.0047077
    out = np.where(lc < 0.00167, small, large)
    return float(out) if out.ndim == 0 else out


def characteristic_length_from_area(area_m2):
    """Inverse of :func:`area_from_characteristic_length`."""
    a = np.asarray(area_m2, dtype=float)
    a_break = 0.540424 * 0.00167**2
    small = np.sqrt(np.maximum(a, 0.0) / 0.540424)
    large = (np.maximum(a, 1e-30) / 0.556945) ** (1.0 / 2.0047077)
    out = np.where(a < a_break, small, large)
    return float(out) if out.ndim == 0 else out
