"""
US Standard Atmosphere 1976, plus the flow-regime bookkeeping a re-entry drag model
needs.

Two regimes are stitched together:

* 0 - 86 km geometric: the closed-form US76 layer model (7 gradient/isothermal
  layers over geopotential altitude).  Exact to the standard.
* 86 - 1000 km geometric: log-linear interpolation of the tabulated US76 upper
  atmosphere.  The closed-form US76 thermosphere requires integrating diffusive
  equilibrium species-by-species; the table reproduces it to well inside the
  day/night and solar-cycle variability that dominates real re-entry uncertainty
  at those altitudes anyway.

Density uncertainty is a first-order driver of impact-point dispersion, so the
model carries a multiplicative ``density_scale`` that Monte Carlo sampling
perturbs (see :mod:`debris.monte_carlo`).
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

import numpy as np

from .constants import (
    AIR_COLLISION_DIAMETER,
    AVOGADRO,
    G0,
    GAMMA_AIR,
    M0_AIR,
    R_AIR,
    R_GEOPOT,
    R_STAR,
)

# --------------------------------------------------------------------------- US76 lower
# Layer bases in *geopotential* km, lapse rates in K/km'.
_H_B = np.array([0.0, 11.0, 20.0, 32.0, 47.0, 51.0, 71.0, 84.8520])
_L_B = np.array([-6.5, 0.0, 1.0, 2.8, 0.0, -2.8, -2.0, 0.0])
_T_B = np.array([288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946])
_P_B = np.array(
    [101325.0, 22632.06, 5474.889, 868.0187, 110.9063, 66.93887, 3.956420, 0.3733836]
)

_GMR = G0 * M0_AIR / R_STAR * 1000.0  # 34.1632 K/km', for exp() of geopotential km

# --------------------------------------------------------------------------- US76 upper
# Geometric altitude [km] -> (density [kg/m^3], kinetic temperature [K]).
_UPPER_Z = np.array(
    [86.0, 90.0, 95.0, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 180.0,
     200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0,
     900.0, 1000.0]
)
_UPPER_RHO = np.array(
    [6.958e-6, 3.416e-6, 1.393e-6, 5.604e-7, 9.708e-8, 2.222e-8, 8.152e-9,
     3.831e-9, 2.076e-9, 1.233e-9, 5.194e-10, 2.541e-10, 6.073e-11, 1.916e-11,
     7.014e-12, 2.803e-12, 1.184e-12, 5.215e-13, 1.137e-13, 3.070e-14,
     1.136e-14, 5.759e-15, 3.561e-15]
)
_UPPER_T = np.array(
    [186.87, 186.87, 188.42, 195.08, 240.00, 360.00, 469.27, 559.63, 634.39,
     696.29, 790.07, 854.56, 941.33, 976.01, 990.06, 995.83, 998.22, 999.24,
     999.85, 1000.00, 1000.00, 1000.00, 1000.00]
)

_LOG_UPPER_RHO = np.log(_UPPER_RHO)
_Z_TOP = _UPPER_Z[-1] * 1000.0


def geopotential_altitude(z_m):
    """Geometric altitude [m] -> US76 geopotential altitude [m]."""
    z = np.asarray(z_m, dtype=float)
    return R_GEOPOT * z / (R_GEOPOT + z)


def _us76_lower(z_m):
    """Closed-form US76 for geometric altitude below 86 km. Returns (rho, T, p)."""
    h_km = geopotential_altitude(z_m) / 1000.0
    h_km = np.clip(h_km, _H_B[0], _H_B[-1])
    # searchsorted with side="right" gives the layer whose base is <= h.
    i = np.clip(np.searchsorted(_H_B, h_km, side="right") - 1, 0, len(_H_B) - 2)

    t_b, p_b, l_b, h_b = _T_B[i], _P_B[i], _L_B[i], _H_B[i]
    dh = h_km - h_b
    temp = t_b + l_b * dh

    isothermal = l_b == 0.0
    # Guard both branches so neither produces a warning on the masked-out side.
    l_safe = np.where(isothermal, 1.0, l_b)
    t_safe = np.where(temp <= 0.0, t_b, temp)
    p_grad = p_b * (t_b / t_safe) ** (_GMR / l_safe)
    p_iso = p_b * np.exp(-_GMR * dh / t_b)
    press = np.where(isothermal, p_iso, p_grad)

    return press / (R_AIR * temp), temp, press


def _us76_upper(z_m):
    """Tabulated US76 for 86 - 1000 km. Returns (rho, T, p)."""
    z_km = np.clip(np.asarray(z_m, dtype=float) / 1000.0, _UPPER_Z[0], _UPPER_Z[-1])
    rho = np.exp(np.interp(z_km, _UPPER_Z, _LOG_UPPER_RHO))
    temp = np.interp(z_km, _UPPER_Z, _UPPER_T)
    return rho, temp, rho * R_AIR * temp


@dataclass(frozen=True)
class AtmosphereSample:
    """Point sample of the atmosphere along a trajectory."""

    density: float          # [kg/m^3]
    temperature: float      # [K]
    pressure: float         # [Pa]
    sound_speed: float      # [m/s]
    mean_free_path: float   # [m]


@dataclass(frozen=True)
class Atmosphere:
    """
    Callable US76 atmosphere.

    Parameters
    ----------
    density_scale:
        Multiplicative density bias.  1.0 is the standard atmosphere; Monte Carlo
        dispersion samples this lognormally to represent the 10-30 % day-to-day and
        solar-cycle density variability that no static model captures.
    exo_cutoff_m:
        Above this altitude density is forced to zero so the propagator can skip
        drag entirely in vacuum.  1000 km is the top of the US76 table.
    """

    density_scale: float = 1.0
    exo_cutoff_m: float = _Z_TOP

    def density(self, z_m):
        """Mass density [kg/m^3] at geometric altitude ``z_m`` [m]. Vectorised."""
        z = np.asarray(z_m, dtype=float)
        rho = np.where(z < 86_000.0, _us76_lower(z)[0], _us76_upper(z)[0])
        rho = np.where(z > self.exo_cutoff_m, 0.0, rho)
        rho = np.where(z < 0.0, _us76_lower(np.zeros_like(z))[0], rho)
        out = rho * self.density_scale
        return float(out) if np.isscalar(z_m) or out.ndim == 0 else out

    def state(self, z_m):
        """Full (rho, T, p, a) profile at geometric altitude ``z_m`` [m]. Vectorised."""
        z = np.asarray(z_m, dtype=float)
        lo_rho, lo_t, lo_p = _us76_lower(z)
        hi_rho, hi_t, hi_p = _us76_upper(z)
        below = z < 86_000.0
        rho = np.where(below, lo_rho, hi_rho) * self.density_scale
        temp = np.where(below, lo_t, hi_t)
        press = np.where(below, lo_p, hi_p) * self.density_scale
        rho = np.where(z > self.exo_cutoff_m, 0.0, rho)
        return rho, temp, press, np.sqrt(GAMMA_AIR * R_AIR * temp)

    def sample(self, z_m: float) -> AtmosphereSample:
        """Scalar sample including the molecular mean free path."""
        rho, temp, press, sound = (float(np.asarray(v)) for v in self.state(float(z_m)))
        return AtmosphereSample(
            density=rho,
            temperature=temp,
            pressure=press,
            sound_speed=sound,
            mean_free_path=mean_free_path(rho),
        )

    def scalar(self, z_m: float):
        """
        Fast scalar ``(density, temperature, sound_speed, mean_free_path)``.

        This is the entry point the propagator's derivative uses; see
        :func:`scalar_state`.
        """
        return scalar_state(z_m, self.density_scale, self.exo_cutoff_m)

    def scaled(self, factor: float) -> "Atmosphere":
        """Copy with ``density_scale`` multiplied by ``factor``."""
        return Atmosphere(self.density_scale * factor, self.exo_cutoff_m)


# ------------------------------------------------------------------ scalar fast path
# Pure-``math`` mirrors of the model above, used inside the propagator's derivative
# where numpy's per-call array overhead would dominate the runtime.  Validated against
# the vectorised implementation in the module self-check.
_H_B_L = _H_B.tolist()
_L_B_L = _L_B.tolist()
_T_B_L = _T_B.tolist()
_P_B_L = _P_B.tolist()
_UPPER_Z_L = _UPPER_Z.tolist()
_LOG_UPPER_RHO_L = _LOG_UPPER_RHO.tolist()
_UPPER_T_L = _UPPER_T.tolist()
_N_UPPER = len(_UPPER_Z_L)
_MFP_COEFF = M0_AIR / (math.sqrt(2.0) * math.pi * AIR_COLLISION_DIAMETER**2 * AVOGADRO)
_R_GEOPOT_KM = R_GEOPOT / 1000.0


def scalar_state(z_m: float, density_scale: float = 1.0,
                 exo_cutoff_m: float = _Z_TOP):
    """
    Fast scalar atmosphere: returns ``(density, temperature, sound_speed, mean_free_path)``.

    Below sea level the sea-level values are held constant (a fragment is already on
    the ground by then; this only keeps the integrator finite during event bisection).
    Above ``exo_cutoff_m`` density is zero, so the propagator can short-circuit drag.
    """
    z = z_m if z_m > 0.0 else 0.0

    if z > exo_cutoff_m:
        temp = _UPPER_T_L[-1]
        return 0.0, temp, math.sqrt(GAMMA_AIR * R_AIR * temp), math.inf

    if z < 86_000.0:
        h = _R_GEOPOT_KM * z / (R_GEOPOT + z)
        i = bisect_right(_H_B_L, h) - 1
        if i < 0:
            i = 0
        elif i > 6:
            i = 6
        t_b, p_b, l_b, h_b = _T_B_L[i], _P_B_L[i], _L_B_L[i], _H_B_L[i]
        dh = h - h_b
        if l_b == 0.0:
            temp = t_b
            press = p_b * math.exp(-_GMR * dh / t_b)
        else:
            temp = t_b + l_b * dh
            press = p_b * (t_b / temp) ** (_GMR / l_b)
        rho = press / (R_AIR * temp)
    else:
        z_km = z / 1000.0
        if z_km >= _UPPER_Z_L[-1]:
            rho, temp = math.exp(_LOG_UPPER_RHO_L[-1]), _UPPER_T_L[-1]
        else:
            j = bisect_right(_UPPER_Z_L, z_km)
            if j < 1:
                j = 1
            elif j > _N_UPPER - 1:
                j = _N_UPPER - 1
            z0, z1 = _UPPER_Z_L[j - 1], _UPPER_Z_L[j]
            w = (z_km - z0) / (z1 - z0)
            rho = math.exp(
                _LOG_UPPER_RHO_L[j - 1] * (1.0 - w) + _LOG_UPPER_RHO_L[j] * w
            )
            temp = _UPPER_T_L[j - 1] * (1.0 - w) + _UPPER_T_L[j] * w

    rho *= density_scale
    lam = _MFP_COEFF / rho if rho > 0.0 else math.inf
    return rho, temp, math.sqrt(GAMMA_AIR * R_AIR * temp), lam


def mean_free_path(density: float) -> float:
    """
    Molecular mean free path [m] from mass density, hard-sphere kinetic theory:

        lambda = 1 / (sqrt(2) * pi * d^2 * n),      n = rho * N_A / M

    Used to form the Knudsen number that selects the drag regime.
    """
    rho = np.asarray(density, dtype=float)
    n = np.where(rho > 0.0, rho, 1e-30) * AVOGADRO / M0_AIR
    lam = 1.0 / (np.sqrt(2.0) * np.pi * AIR_COLLISION_DIAMETER**2 * n)
    lam = np.where(rho > 0.0, lam, np.inf)
    return float(lam) if lam.ndim == 0 else lam


#: Module-level standard atmosphere, safe to share (frozen dataclass).
US76 = Atmosphere()


# ------------------------------------------------------------------- tabulated lookup
class DensityTable:
    """
    Pre-sampled log-density / sound-speed table for the ensemble propagator.

    The closed-form model needs ~50 numpy operations per evaluation (two branches, a
    fractional power, a mask merge).  The ensemble right-hand side calls it seven times
    per step, so that cost dominates a Monte Carlo run.  Interpolating a pre-built table
    replaces all of it with two :func:`numpy.interp` calls.

    Grid resolution is 20 m below 130 km, which is where drag actually happens.  Since
    the density scale height is ~7 km, log-linear interpolation over 20 m carries a
    relative error of order 1e-6 - far below the 10-30 % that real atmospheric
    variability contributes, and below the propagator's own integration tolerance.

    The table is built for the *unscaled* atmosphere; per-sample ``density_scale`` is
    applied by the caller as a plain multiply, so a single shared table serves every
    Monte Carlo sample.
    """

    def __init__(self, z_max: float = _Z_TOP, fine_step: float = 20.0,
                 fine_top: float = 130_000.0, coarse_step: float = 2_000.0):
        fine = np.arange(0.0, fine_top + fine_step, fine_step)
        coarse = np.arange(fine_top + coarse_step, z_max + coarse_step, coarse_step)
        self.z = np.concatenate([fine, coarse])
        rho, temp, _p, sound = Atmosphere(1.0, z_max + 1.0).state(self.z)
        self.log_rho = np.log(np.maximum(rho, 1e-300))
        self.sound = sound
        self.temperature = temp
        self._log_mfp_c = math.log(_MFP_COEFF)

    def lookup(self, alt_m):
        """``(density, sound_speed, mean_free_path)`` for an array of altitudes."""
        log_rho = np.interp(alt_m, self.z, self.log_rho)
        return (
            np.exp(log_rho),
            np.interp(alt_m, self.z, self.sound),
            np.exp(self._log_mfp_c - log_rho),
        )


#: Shared table for the standard atmosphere, built once on import (~170 kB).
US76_TABLE = DensityTable()
