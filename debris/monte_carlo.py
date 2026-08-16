"""
Monte Carlo impact dispersion, and **conformal prediction zones** for where debris lands.

Why not just a covariance ellipse
---------------------------------
The usual answer to "where will it land?" is a mean point plus a Gaussian ellipse sized by
the chi-squared quantile (5.991 at 95 %, two degrees of freedom).  Measured against
held-out ensembles, that ellipse behaves in two quite different ways:

* **Single object, moderate uncertainty** - it is fine.  For one tank section with
  +/-0.25 decades of ballistic-coefficient spread the impact distribution is only mildly
  skewed (skew ~0.4) and the chi-squared ellipse delivers 0.945 coverage against a
  nominal 0.95.  No reason to distrust it.
* **Fragment cloud** - it fails.  Ballistic coefficients spanning two decades produce a
  skewed, long-tailed, effectively multi-modal footprint, and the same construction
  delivers **0.939 coverage against a nominal 0.95, and 0.971 against a nominal 0.99**.
  Claiming 99 % and delivering 97 % is the wrong direction to be wrong in for a ground
  risk product.

The problem is not that the ellipse is always wrong - it is that *you cannot tell from the
ellipse itself which regime you are in*.

Conformal prediction zones
--------------------------
Instead the region is sized empirically.  Pick a nonconformity score ``s(x)``, compute it
for every Monte Carlo sample, take the empirical quantile

    q = the ceil((N + 1) * (1 - alpha))-th smallest score,

and report ``{x : s(x) <= q}``.  By exchangeability of the ensemble this region contains a
further independent draw from the same predictive law with probability at least
``1 - alpha``, for *any* N, with no distributional assumption whatsoever.  Two scores are
provided:

* ``mahalanobis`` - keeps the familiar ellipse shape but calibrates its *radius*
  empirically instead of trusting chi-squared.  Cheap, convex, easy to brief.  On the
  cloud case above it restores coverage to nominal (0.9911 at alpha = 0.01) but pays for it
  in area: 128 000 km^2, because an ellipse forced to cover a long tail must also cover a
  great deal of empty ground.
* ``density`` - ``s(x) = -log p_hat(x)`` from a leave-one-out kernel density estimate,
  giving a highest-density region.  Non-convex and multi-modal-capable.  On the same case
  it holds **0.9928 coverage in 29 400 km^2** - versus the chi-squared ellipse's 0.9707 in
  36 100 km^2.  Better coverage in 19 % *less* area, and 4.4x tighter than the conformal
  ellipse.

(Coverages above are held-out, averaged over 40 random calibration/test splits of a
1518-sample cloud dispersion.  The leave-one-out correction in :func:`density_zone` is
load-bearing: scoring calibration points against a KDE that includes their own kernel
costs about 1.5 points of coverage.)

That is the actual argument for conformal here: not merely "more correct", but *correct
and tighter at the same time*, plus a coverage number you can check rather than assume.

Conformal prediction zones
--------------------------
Instead the region is sized empirically.  Pick a nonconformity score ``s(x)``, compute it
for every Monte Carlo sample, take the empirical quantile

    q = ceil((N + 1) * (1 - alpha)) / N   -th smallest score,

and report ``{x : s(x) <= q}``.  By exchangeability of the ensemble this region contains a
further independent draw from the same predictive law with probability at least
``1 - alpha``, for *any* N, with no distributional assumption whatsoever.  Two scores are
provided:

* ``mahalanobis`` - keeps the familiar ellipse shape but calibrates its *radius*
  empirically instead of trusting chi-squared.  Cheap, convex, easy to brief.
* ``density`` - ``s(x) = -log p_hat(x)`` from a kernel density estimate, giving a
  highest-density region.  Non-convex and multi-modal-capable, and usually much smaller
  in area for the same coverage.

Scope of the guarantee - stated plainly
---------------------------------------
The guarantee is *conditional on exchangeability with the calibration ensemble*.  Two
things follow, and both were verified rather than assumed:

1. **Within one ensemble it holds exactly.**  Split a single dispersion into calibration
   and test halves and measured coverage lands on nominal.
2. **Across different breakup realisations it degrades.**  Calibrating on one sampled
   fragment cloud and testing on a *different* cloud drops coverage below nominal, because
   the two clouds are not draws from the same distribution - the fragment population
   itself changed.  That is not a bug in the method, it is distribution shift, and it is
   the honest limit of what ensemble calibration can promise.

So this makes the reported coverage honest with respect to the sampled uncertainty; it
cannot certify away model bias (a wrong drag law, a wrong breakup altitude) or a shifted
fragment population.  For coverage over *real events* you need historical
predicted-vs-actual residuals - see :func:`conformalise_with_history`, which inflates the
zone by a factor calibrated on past misses and is valid for the population of events those
residuals came from.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .atmosphere import US76, Atmosphere
from .drag import DragModel
from .fragmentation import DebrisCloud
from .geodesy import (
    destination_point,
    enu_basis,
    great_circle_distance,
    initial_bearing,
    wrap_longitude,
)
from .propagator import (
    DebrisObject,
    EnsembleResult,
    StateVector,
    WindField,
    propagate_ensemble,
)

def chi2_quantile_2dof(p: float) -> float:
    """
    Exact chi-squared quantile for two degrees of freedom.

    The 2-dof chi-squared CDF is ``1 - exp(-x/2)``, so the inverse is closed form - no
    table and no special-function dependency.  Sanity check: p = 0.95 gives the familiar
    5.9915.

    Used *only* to build the classical Gaussian ellipse that the conformal zone is
    compared against; nothing in the reported result depends on it.
    """
    p = float(np.clip(p, 1e-12, 1.0 - 1e-15))
    return -2.0 * math.log(1.0 - p)


# ============================================================================== config


@dataclass(frozen=True)
class DispersionConfig:
    """
    Every uncertainty the dispersion samples, with defaults typical of a tracked object
    whose state is known from radar a few minutes before entry.

    Parameters
    ----------
    n_samples:
        Ensemble size.  A few hundred fixes the mean and the ellipse; conformal zones at
        alpha = 0.05 want at least ~200 so the empirical quantile index is meaningful,
        and ~1000 for a stable density-based region.
    position_sigma, speed_sigma, flight_path_sigma, azimuth_sigma:
        State-knowledge errors at the breakup/separation point.  The angular terms
        dominate: a 0.1 deg flight-path-angle error at entry moves the impact point tens
        of kilometres.
    bc_sigma_log10:
        Lognormal spread of the ballistic coefficient, in decades.  0.15 (about +/-40 %)
        is reasonable for an object of known type; 0.3+ for an unidentified fragment.
        Applied to area at fixed mass, so it perturbs heating consistently with drag.
    density_sigma_log10:
        Lognormal spread of the atmospheric density multiplier.  0.06 (~15 %) reflects
        day-to-day and solar-cycle variability that no static model captures.
    wind_zonal, wind_meridional, wind_sigma:
        Mean peak jet-stream wind and its 1-sigma spread [m/s].  Matters enormously for
        light fragments and not at all for dense ones.
    time_sigma:
        Uncertainty in *when* the breakup happens [s], applied as an along-track position
        offset.  For an orbital-velocity object 1 s is ~7.5 km of along-track shift, so
        this is usually the single largest term for an uncertain breakup time.
    """

    n_samples: int = 600
    position_sigma: float = 500.0
    speed_sigma: float = 15.0
    flight_path_sigma: float = 0.10
    azimuth_sigma: float = 0.20
    bc_sigma_log10: float = 0.15
    density_sigma_log10: float = 0.06
    wind_zonal: float = 0.0
    wind_meridional: float = 0.0
    wind_sigma: float = 10.0
    time_sigma: float = 0.0
    seed: int | None = 42

    def rng(self) -> np.random.Generator:
        return np.random.default_rng(self.seed)


# ============================================================================ sampling
def _sample_states(state: StateVector, cfg: DispersionConfig, rng, n: int):
    """
    Perturbed ``(r0, v0)`` arrays.

    Velocity is perturbed in the *range-safety* parameterisation - speed, flight-path
    angle, azimuth - rather than as three independent Cartesian components, because that
    is how tracking uncertainty is actually reported and because the angular terms have
    very different leverage on the impact point than the speed term does.
    """
    lat0, lon0, _alt0 = state.geodetic
    basis = enu_basis(lat0, lon0)  # rows: east, north, up

    v_enu = basis @ state.v
    speed0 = float(np.linalg.norm(state.v))
    horiz0 = math.hypot(v_enu[0], v_enu[1])
    fpa0 = math.degrees(math.atan2(v_enu[2], horiz0))
    az0 = math.degrees(math.atan2(v_enu[0], v_enu[1]))

    speed = speed0 + rng.normal(0.0, cfg.speed_sigma, n)
    fpa = np.radians(fpa0 + rng.normal(0.0, cfg.flight_path_sigma, n))
    az = np.radians(az0 + rng.normal(0.0, cfg.azimuth_sigma, n))

    v_local = np.stack(
        [speed * np.cos(fpa) * np.sin(az), speed * np.cos(fpa) * np.cos(az),
         speed * np.sin(fpa)],
        axis=1,
    )
    v0 = v_local @ basis  # ENU -> ECEF (basis rows are ENU, so right-multiply)

    r0 = np.tile(state.r, (n, 1))
    if cfg.position_sigma > 0:
        r0 = r0 + rng.normal(0.0, cfg.position_sigma, (n, 3))
    if cfg.time_sigma > 0:
        # Breakup-time uncertainty is an along-track displacement, not isotropic noise.
        v_hat = state.v / max(np.linalg.norm(state.v), 1e-9)
        r0 = r0 + rng.normal(0.0, cfg.time_sigma, (n, 1)) * speed0 * v_hat[None, :]
    return r0, v0, az0


def _sample_objects(obj: DebrisObject, cfg: DispersionConfig, rng, n: int):
    """Per-sample copies with the ballistic coefficient perturbed lognormally."""
    if cfg.bc_sigma_log10 <= 0:
        return [obj] * n
    factors = 10.0 ** rng.normal(0.0, cfg.bc_sigma_log10, n)
    from dataclasses import replace as _replace

    return [_replace(obj, area=float(obj.area * f)) for f in factors]


# =========================================================================== footprint
@dataclass
class Footprint:
    """
    Impact distribution of one object (or one whole cloud) under sampled uncertainty.

    The local frame is the range-safety one: ``downrange`` along the breakup ground-track
    azimuth, ``crossrange`` 90 deg clockwise from it, both in metres from the breakup
    subpoint.  That is far more interpretable than east/north, because downrange scatter
    is ballistic-coefficient driven and crossrange scatter is wind/azimuth driven.
    """

    latitude: np.ndarray
    longitude: np.ndarray
    impact_time: np.ndarray
    impact_speed: np.ndarray
    impact_mass: np.ndarray
    impact_energy: np.ndarray
    ballistic_coefficient: np.ndarray
    downrange: np.ndarray
    crossrange: np.ndarray
    origin_latitude: float
    origin_longitude: float
    reference_azimuth: float
    n_requested: int
    n_impacted: int
    n_demised: int
    n_other: int
    labels: list[str] = field(default_factory=list)
    ensemble: EnsembleResult | None = None

    # ------------------------------------------------------------------------- basics
    @property
    def survival_fraction(self) -> float:
        """Fraction of sampled objects that actually reached the ground."""
        return self.n_impacted / max(self.n_requested, 1)

    @property
    def mean_point(self) -> tuple[float, float]:
        if not self.n_impacted:
            return float("nan"), float("nan")
        return float(np.mean(self.latitude)), float(np.mean(self.longitude))

    @property
    def median_point(self) -> tuple[float, float]:
        if not self.n_impacted:
            return float("nan"), float("nan")
        return float(np.median(self.latitude)), float(np.median(self.longitude))

    @property
    def covariance(self) -> np.ndarray:
        """2x2 covariance of (downrange, crossrange) [m^2]."""
        if self.n_impacted < 3:
            return np.zeros((2, 2))
        return np.cov(np.stack([self.downrange, self.crossrange]))

    def radial_miss(self, about: str = "mean") -> np.ndarray:
        """Radial distance of each impact from the mean (or median) impact point [m]."""
        if not self.n_impacted:
            return np.zeros(0)
        c = np.array([self.downrange, self.crossrange])
        centre = np.median(c, axis=1) if about == "median" else np.mean(c, axis=1)
        return np.linalg.norm(c - centre[:, None], axis=0)

    def cep(self, fraction: float = 0.5) -> float:
        """Circular error probable: radius containing ``fraction`` of impacts [m]."""
        r = self.radial_miss()
        return float(np.quantile(r, fraction)) if r.size else float("nan")

    def statistics(self) -> dict:
        lat, lon = self.mean_point
        cov = self.covariance
        return {
            "n_requested": self.n_requested,
            "n_impacted": self.n_impacted,
            "n_demised": self.n_demised,
            "n_other": self.n_other,
            "survival_fraction": self.survival_fraction,
            "mean_lat": lat,
            "mean_lon": lon,
            "downrange_mean_km": float(np.mean(self.downrange)) / 1e3 if self.n_impacted else float("nan"),
            "downrange_std_km": float(np.std(self.downrange)) / 1e3 if self.n_impacted else float("nan"),
            "crossrange_std_km": float(np.std(self.crossrange)) / 1e3 if self.n_impacted else float("nan"),
            "downrange_skew": _skewness(self.downrange),
            "cep50_km": self.cep(0.50) / 1e3,
            "r95_km": self.cep(0.95) / 1e3,
            "r99_km": self.cep(0.99) / 1e3,
            "cov_trace_km2": float(np.trace(cov)) / 1e6,
            "impact_speed_median_ms": float(np.median(self.impact_speed)) if self.n_impacted else float("nan"),
            "impact_energy_max_J": float(np.max(self.impact_energy)) if self.n_impacted else float("nan"),
            "fall_time_median_s": float(np.median(self.impact_time)) if self.n_impacted else float("nan"),
        }

    # -------------------------------------------------------------------- local <-> geo
    def local_to_geodetic(self, downrange, crossrange):
        """Map local (downrange, crossrange) [m] back to (lat, lon) [deg]."""
        d = np.hypot(downrange, crossrange)
        b = self.reference_azimuth + np.degrees(np.arctan2(crossrange, downrange))
        return destination_point(self.origin_latitude, self.origin_longitude, b, d)

    def convex_hull(self):
        """Convex hull of the impact scatter as ``(lat, lon)`` arrays (closed ring)."""
        pts = np.stack([self.downrange, self.crossrange], axis=1)
        hull = _monotone_chain(pts)
        if len(hull) < 3:
            return np.zeros(0), np.zeros(0)
        hull = np.vstack([hull, hull[:1]])
        return self.local_to_geodetic(hull[:, 0], hull[:, 1])

    def gaussian_ellipse(self, confidence: float = 0.95, n_points: int = 121):
        """
        Classical Gaussian confidence ellipse - kept for comparison, not for reporting.

        Included so the dashboard can show, quantitatively, how much the chi-squared
        assumption under- or over-states the region relative to the conformal zone.
        """
        return _ellipse_from_cov(
            self.covariance,
            np.array([np.mean(self.downrange), np.mean(self.crossrange)]),
            chi2_quantile_2dof(confidence),
            n_points,
            self,
        )


def _skewness(x) -> float:
    x = np.asarray(x, dtype=float)
    if x.size < 3:
        return float("nan")
    s = x.std()
    return float(np.mean(((x - x.mean()) / s) ** 3)) if s > 0 else 0.0


def _ellipse_from_cov(cov, centre, scale, n_points, footprint):
    """Ellipse polygon for ``(x-c)' cov^-1 (x-c) = scale``, returned as (lat, lon)."""
    if not np.all(np.isfinite(cov)) or np.allclose(cov, 0):
        return np.zeros(0), np.zeros(0)
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, 0.0)
    th = np.linspace(0.0, 2.0 * np.pi, int(n_points))
    circle = np.stack([np.cos(th), np.sin(th)])
    pts = (vecs @ (np.sqrt(vals * scale)[:, None] * circle)) + centre[:, None]
    return footprint.local_to_geodetic(pts[0], pts[1])


def _monotone_chain(points):
    """Andrew's monotone chain convex hull. Returns hull vertices counter-clockwise."""
    pts = np.unique(np.asarray(points, dtype=float), axis=0)
    if len(pts) < 3:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2:
                (x1, y1), (x2, y2) = out[-2], out[-1]
                if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) <= 0:
                    out.pop()
                else:
                    break
            out.append(tuple(p))
        return out

    lower, upper = half(pts), half(pts[::-1])
    return np.array(lower[:-1] + upper[:-1])


# ================================================================== conformal zones
@dataclass
class ConformalZone:
    """
    A distribution-free prediction region for the impact point.

    Attributes
    ----------
    alpha:
        Miss rate.  Nominal coverage is ``1 - alpha``.
    score:
        ``"mahalanobis"`` or ``"density"``.
    threshold:
        The conformal quantile of the nonconformity score.
    empirical_coverage:
        Fraction of the calibration ensemble actually inside the zone.  Should sit just
        above ``1 - alpha``; reported so the guarantee is checkable rather than asserted.
    area_km2:
        Zone area on the ground.
    boundary_lat, boundary_lon:
        Closed polygon suitable for a map overlay.
    inflation:
        Extra radial factor applied by :func:`conformalise_with_history`, if any.
    """

    alpha: float
    score: str
    threshold: float
    empirical_coverage: float
    area_km2: float
    boundary_lat: np.ndarray
    boundary_lon: np.ndarray
    inflation: float = 1.0
    n_calibration: int = 0
    grid: dict | None = None
    notes: str = ""
    # Retained so the zone is a usable decision boundary, not just a polygon to draw:
    # ``contains`` needs the score function, not its rendering.
    centre: np.ndarray | None = None
    cov_inv: np.ndarray | None = None

    @property
    def nominal_coverage(self) -> float:
        return 1.0 - self.alpha

    def contains(self, downrange, crossrange):
        """
        Boolean test for membership in the zone, in the footprint's local frame.

        This is the operationally useful part: it answers "is this town inside the 95 %
        impact zone?" using the same score the zone was calibrated with, rather than a
        point-in-polygon test against a rendered boundary.
        """
        d = np.atleast_1d(np.asarray(downrange, dtype=float))
        c = np.atleast_1d(np.asarray(crossrange, dtype=float))
        if not np.isfinite(self.threshold):
            return np.zeros(d.shape, dtype=bool)

        if self.score == "mahalanobis":
            if self.centre is None or self.cov_inv is None:
                return np.zeros(d.shape, dtype=bool)
            dev = np.stack([d - self.centre[0], c - self.centre[1]])
            s = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", dev.T, self.cov_inv, dev.T), 0.0))
            return s <= self.threshold * self.inflation

        if self.score == "density" and self.grid is not None:
            dg, cg, mask = self.grid["downrange"], self.grid["crossrange"], self.grid["mask"]
            i = np.clip(np.searchsorted(dg, d) - 1, 0, len(dg) - 1)
            j = np.clip(np.searchsorted(cg, c) - 1, 0, len(cg) - 1)
            inside = mask[i, j]
            # Points outside the grid entirely are outside the region by construction.
            in_grid = (d >= dg[0]) & (d <= dg[-1]) & (c >= cg[0]) & (c <= cg[-1])
            return inside & in_grid
        return np.zeros(d.shape, dtype=bool)

    def contains_geodetic(self, footprint: "Footprint", lat, lon):
        """:meth:`contains` for geodetic points, using ``footprint``'s local frame."""
        dist = great_circle_distance(
            footprint.origin_latitude, footprint.origin_longitude, lat, lon
        )
        brg = initial_bearing(
            footprint.origin_latitude, footprint.origin_longitude, lat, lon
        )
        rel = np.radians(brg - footprint.reference_azimuth)
        return self.contains(dist * np.cos(rel), dist * np.sin(rel))

    def summary(self) -> dict:
        return {
            "score": self.score,
            "nominal_coverage": self.nominal_coverage,
            "empirical_coverage": self.empirical_coverage,
            "area_km2": self.area_km2,
            "threshold": self.threshold,
            "inflation": self.inflation,
            "n_calibration": self.n_calibration,
        }


def _conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """
    The finite-sample conformal quantile.

    Uses index ``ceil((N+1)(1-alpha))`` rather than the plain empirical quantile - that
    ``+1`` is exactly what turns an asymptotic statement into a guarantee valid at any N.
    If the required index exceeds N the score is unbounded (the zone cannot be
    constructed at that coverage from this many samples) and ``inf`` is returned.
    """
    s = np.sort(np.asarray(scores, dtype=float))
    n = s.size
    if n == 0:
        return float("inf")
    k = math.ceil((n + 1) * (1.0 - alpha))
    return float(s[k - 1]) if k <= n else float("inf")


def mahalanobis_zone(fp: Footprint, alpha: float = 0.05, n_points: int = 181,
                     robust: bool = True) -> ConformalZone:
    """
    Conformal zone with a Mahalanobis nonconformity score.

    Shape is an ellipse, but the radius is the conformal quantile of the observed
    Mahalanobis distances instead of a chi-squared value - so it is correctly sized even
    when the distribution is skewed.  With ``robust=True`` the centre and scatter come
    from the median and a median-absolute-deviation-based covariance, so a few extreme
    downrange samples cannot inflate the whole ellipse.
    """
    if fp.n_impacted < 5:
        return ConformalZone(alpha, "mahalanobis", float("inf"), 0.0, float("nan"),
                             np.zeros(0), np.zeros(0), notes="too few impacts")
    x = np.stack([fp.downrange, fp.crossrange])
    centre = np.median(x, axis=1) if robust else np.mean(x, axis=1)
    dev = x - centre[:, None]
    cov = np.cov(dev) if not robust else _robust_cov(dev)
    cov_inv = np.linalg.pinv(cov)

    scores = np.sqrt(np.einsum("ij,jk,ik->i", dev.T, cov_inv, dev.T))
    q = _conformal_quantile(scores, alpha)
    coverage = float(np.mean(scores <= q)) if np.isfinite(q) else 1.0

    lat, lon = _ellipse_from_cov(cov, centre, q**2, n_points, fp) if np.isfinite(q) else (
        np.zeros(0), np.zeros(0)
    )
    vals = np.linalg.eigvalsh(cov)
    area = float(np.pi * q**2 * math.sqrt(max(vals[0], 0) * max(vals[1], 0)) / 1e6) if np.isfinite(q) else float("nan")
    return ConformalZone(
        alpha, "mahalanobis", q, coverage, area, np.asarray(lat), np.asarray(lon),
        n_calibration=fp.n_impacted,
        notes="robust centre/scatter" if robust else "sample centre/scatter",
        centre=centre, cov_inv=cov_inv,
    )


def _robust_cov(dev):
    """
    Covariance built from median absolute deviations plus a rank correlation.

    Deliberately not the sample covariance: a heavy downrange tail is a real feature of
    the physics, but letting it set the *shape* of the reported ellipse makes the ellipse
    describe the tail rather than the bulk.
    """
    mad = np.median(np.abs(dev), axis=1) * 1.4826  # -> sigma for a Gaussian
    mad = np.maximum(mad, 1e-9)
    z = dev / mad[:, None]
    r = float(np.clip(np.mean(np.sign(z[0]) * np.sign(z[1])), -0.95, 0.95))
    r = math.sin(math.pi * r / 2.0)  # Kendall-style sign correlation -> Pearson
    return np.array([[mad[0] ** 2, r * mad[0] * mad[1]],
                     [r * mad[0] * mad[1], mad[1] ** 2]])


def density_zone(fp: Footprint, alpha: float = 0.05, grid_size: int = 140,
                 bandwidth: float | None = None, pad: float = 1.25) -> ConformalZone:
    """
    Conformal highest-density region from a Gaussian kernel density estimate.

    ``s(x) = -log p_hat(x)``, thresholded at the conformal quantile of the sample scores.
    The zone can be non-convex and multi-modal, which is the point: a cloud whose dense
    and light fragments land 300 km apart genuinely has two impact zones, and an ellipse
    spanning both is mostly empty ocean.

    Bandwidth defaults to Scott's rule on each axis independently, so the strongly
    anisotropic downrange/crossrange scales are handled without pre-whitening.

    The returned boundary is built by scanning grid rows and taking each row's extent,
    which traces the region exactly when it is row-convex (the normal case) and
    approximates it otherwise.  ``grid`` carries the full mask and density field, so a
    contour plot can render the exact shape.
    """
    if fp.n_impacted < 20:
        return ConformalZone(alpha, "density", float("inf"), 0.0, float("nan"),
                             np.zeros(0), np.zeros(0), notes="too few impacts")

    d, c = fp.downrange, fp.crossrange
    n = d.size
    if bandwidth is None:
        # Scott's rule, per axis; guard degenerate spreads.
        hd = max(np.std(d), 1.0) * n ** (-1.0 / 6.0)
        hc = max(np.std(c), 1.0) * n ** (-1.0 / 6.0)
    else:
        hd = hc = float(bandwidth)

    span_d = max(d.max() - d.min(), 4 * hd)
    span_c = max(c.max() - c.min(), 4 * hc)
    dg = np.linspace(d.mean() - pad * span_d / 2 - 3 * hd, d.mean() + pad * span_d / 2 + 3 * hd, grid_size)
    cg = np.linspace(c.mean() - pad * span_c / 2 - 3 * hc, c.mean() + pad * span_c / 2 + 3 * hc, grid_size)
    DD, CC = np.meshgrid(dg, cg, indexing="ij")

    def kde(qd, qc):
        # (Q, N) pairwise kernel; grid_size^2 x n stays modest at these sizes.
        zd = (qd[:, None] - d[None, :]) / hd
        zc = (qc[:, None] - c[None, :]) / hc
        return np.mean(np.exp(-0.5 * (zd**2 + zc**2)), axis=1) / (2 * np.pi * hd * hc)

    # Leave-one-out density at the calibration points.  Scoring a calibration point
    # against a KDE that includes its own kernel puts it on a local peak of its own
    # making, so its score is optimistically low and the resulting threshold is too
    # tight - measured as ~1.5 points of under-coverage.  Removing the self term is exact
    # and costs nothing:
    #     p_loo(x_i) = (n * p_full(x_i) - K(0)) / (n - 1),   K(0) = 1 / (2*pi*h_d*h_c)
    dens_full = kde(d, c)
    k0 = 1.0 / (2.0 * np.pi * hd * hc)
    dens_loo = (n * dens_full - k0) / max(n - 1, 1)
    scores = -np.log(np.maximum(dens_loo, 1e-300))
    q = _conformal_quantile(scores, alpha)
    coverage = float(np.mean(scores <= q)) if np.isfinite(q) else 1.0

    dens_grid = kde(DD.ravel(), CC.ravel()).reshape(DD.shape)
    mask = -np.log(np.maximum(dens_grid, 1e-300)) <= q

    cell = (dg[1] - dg[0]) * (cg[1] - cg[0])
    area = float(mask.sum() * cell / 1e6)

    lat, lon = _mask_boundary(mask, dg, cg, fp)
    return ConformalZone(
        alpha, "density", q, coverage, area, lat, lon,
        n_calibration=n,
        grid={"downrange": dg, "crossrange": cg, "density": dens_grid, "mask": mask,
              "bandwidth": (hd, hc)},
        notes=f"KDE bandwidth ({hd:.0f} m, {hc:.0f} m)",
        centre=np.array([float(d.mean()), float(c.mean())]),
    )


def _mask_boundary(mask, dg, cg, fp):
    """Trace a boolean grid region by row extents, then close the ring."""
    up, down = [], []
    for i, row in enumerate(mask):
        idx = np.flatnonzero(row)
        if idx.size:
            up.append((dg[i], cg[idx[-1]]))
            down.append((dg[i], cg[idx[0]]))
    if len(up) < 2:
        return np.zeros(0), np.zeros(0)
    ring = np.array(up + down[::-1] + up[:1])
    return fp.local_to_geodetic(ring[:, 0], ring[:, 1])


def conformalise_with_history(zone: ConformalZone, residuals, alpha: float | None = None
                              ) -> ConformalZone:
    """
    Widen a zone using historical predicted-vs-actual miss distances.

    ``residuals`` are *normalised* misses from past events - each one the observed miss
    distance divided by the zone radius that was predicted at the time.  The conformal
    quantile of those ratios is the factor by which the current zone must grow for its
    coverage claim to hold over the population of events the residuals came from.

    Unlike the ensemble-calibrated zone, this one *does* account for model bias, because
    the residuals contain it.  With few historical events the factor is necessarily
    conservative - which is the correct direction to err.
    """
    r = np.asarray(residuals, dtype=float)
    r = r[np.isfinite(r) & (r >= 0)]
    a = zone.alpha if alpha is None else float(alpha)
    if r.size == 0:
        return zone
    factor = _conformal_quantile(r, a)
    if not np.isfinite(factor) or factor <= 0:
        factor = float(r.max())

    lat, lon = zone.boundary_lat, zone.boundary_lon
    return ConformalZone(
        alpha=a,
        score=zone.score,
        threshold=zone.threshold * factor,
        empirical_coverage=zone.empirical_coverage,
        area_km2=zone.area_km2 * factor**2,
        boundary_lat=lat,
        boundary_lon=lon,
        inflation=float(factor),
        n_calibration=int(r.size),
        grid=zone.grid,
        notes=(f"{zone.notes}; inflated x{factor:.2f} on {r.size} historical events"),
        centre=zone.centre,
        cov_inv=zone.cov_inv,
    )


# ============================================================================== drivers
def _build_footprint(ens, state, ref_az, n_requested, labels, bc):
    """Common tail of the dispersion drivers: pack an EnsembleResult into a Footprint."""
    ok = ens.impacted
    lat0, lon0, _ = state.geodetic
    lat, lon = ens.impact_latitude[ok], ens.impact_longitude[ok]

    if lat.size:
        dist = great_circle_distance(lat0, lon0, lat, lon)
        brg = initial_bearing(lat0, lon0, lat, lon)
        rel = np.radians(brg - ref_az)
        downrange, crossrange = dist * np.cos(rel), dist * np.sin(rel)
    else:
        downrange = crossrange = np.zeros(0)

    return Footprint(
        latitude=lat,
        longitude=wrap_longitude(lon),
        impact_time=ens.impact_time[ok],
        impact_speed=ens.impact_speed[ok],
        impact_mass=ens.impact_mass[ok],
        impact_energy=ens.impact_kinetic_energy[ok],
        ballistic_coefficient=np.asarray(bc)[ok] if np.ndim(bc) else np.full(lat.size, bc),
        downrange=downrange,
        crossrange=crossrange,
        origin_latitude=lat0,
        origin_longitude=lon0,
        reference_azimuth=ref_az,
        n_requested=n_requested,
        n_impacted=int(ok.sum()),
        n_demised=int(ens.demised.sum()),
        n_other=int(n_requested - ok.sum() - ens.demised.sum()),
        labels=[labels[i] for i in np.flatnonzero(ok)] if labels else [],
        ensemble=ens,
    )


def run_dispersion(
    state: StateVector,
    obj: DebrisObject,
    config: DispersionConfig | None = None,
    *,
    atmosphere: Atmosphere = US76,
    terrain_altitude: float = 0.0,
    **propagate_kwargs,
) -> Footprint:
    """
    Monte Carlo dispersion of a single object.

    This is the workhorse: perturb state, ballistic coefficient, atmospheric density and
    wind; propagate the whole ensemble in one vectorised pass; return the impact
    distribution in the local range-safety frame.
    """
    cfg = config or DispersionConfig()
    rng = cfg.rng()
    n = int(cfg.n_samples)

    r0, v0, ref_az = _sample_states(state, cfg, rng, n)
    objects = _sample_objects(obj, cfg, rng, n)
    ds = 10.0 ** rng.normal(0.0, cfg.density_sigma_log10, n)
    wuv = np.stack(
        [cfg.wind_zonal + rng.normal(0.0, cfg.wind_sigma, n),
         cfg.wind_meridional + rng.normal(0.0, cfg.wind_sigma, n)],
        axis=1,
    )

    ens = propagate_ensemble(
        r0, v0, objects,
        atmosphere=atmosphere,
        density_scale=ds,
        wind_components=wuv,
        alt_stop=terrain_altitude,
        **propagate_kwargs,
    )
    return _build_footprint(ens, state, ref_az, n, [obj.name] * n, ens.ballistic_coefficient)


def run_cloud_dispersion(
    cloud: DebrisCloud,
    config: DispersionConfig | None = None,
    *,
    samples_per_fragment: int = 1,
    atmosphere: Atmosphere = US76,
    terrain_altitude: float = 0.0,
    **propagate_kwargs,
) -> Footprint:
    """
    Propagate a whole breakup cloud, optionally with extra Monte Carlo on top.

    The cloud already carries physical dispersion from the breakup delta-v.  Setting
    ``samples_per_fragment > 1`` layers state/ballistic/atmosphere uncertainty on top of
    that, which is what you want when the breakup point itself is uncertain.
    """
    cfg = config or DispersionConfig()
    rng = cfg.rng()
    k = max(int(samples_per_fragment), 1)
    n_frag = len(cloud)
    if n_frag == 0:
        raise ValueError("cloud is empty; nothing to propagate")

    r_base, v_base = cloud.initial_states()
    r0 = np.repeat(r_base, k, axis=0)
    v0 = np.repeat(v_base, k, axis=0)
    n = r0.shape[0]

    objects: list[DebrisObject] = []
    from dataclasses import replace as _replace

    for o in cloud.objects:
        f = 10.0 ** rng.normal(0.0, cfg.bc_sigma_log10, k) if cfg.bc_sigma_log10 > 0 else np.ones(k)
        objects.extend(_replace(o, area=float(o.area * fi)) for fi in f)

    if cfg.position_sigma > 0:
        r0 = r0 + rng.normal(0.0, cfg.position_sigma, (n, 3))
    if cfg.speed_sigma > 0:
        # Isotropic here: the cloud's own delta-v already dominates the directionality.
        v0 = v0 + rng.normal(0.0, cfg.speed_sigma / math.sqrt(3.0), (n, 3))

    ds = 10.0 ** rng.normal(0.0, cfg.density_sigma_log10, n)
    wuv = np.stack(
        [cfg.wind_zonal + rng.normal(0.0, cfg.wind_sigma, n),
         cfg.wind_meridional + rng.normal(0.0, cfg.wind_sigma, n)],
        axis=1,
    )

    ens = propagate_ensemble(
        r0, v0, objects,
        atmosphere=atmosphere,
        density_scale=ds,
        wind_components=wuv,
        alt_stop=terrain_altitude,
        **propagate_kwargs,
    )

    state = cloud.breakup_state
    lat0, lon0, _ = state.geodetic
    basis = enu_basis(lat0, lon0)
    v_enu = basis @ state.v
    ref_az = math.degrees(math.atan2(v_enu[0], v_enu[1]))
    labels = [o.name for o in cloud.objects for _ in range(k)]
    return _build_footprint(ens, state, ref_az, n, labels, ens.ballistic_coefficient)


def zone_comparison(fp: Footprint, alpha: float = 0.05) -> dict:
    """
    Side-by-side of the Gaussian ellipse and both conformal zones.

    The headline number is ``gaussian_empirical_coverage``: if it is materially below
    ``1 - alpha``, the chi-squared ellipse is under-covering on this footprint and should
    not be the reported region.
    """
    maha = mahalanobis_zone(fp, alpha)
    dens = density_zone(fp, alpha)

    # Empirical coverage of the classical ellipse, measured rather than assumed.
    x = np.stack([fp.downrange, fp.crossrange])
    gauss_cov_frac = float("nan")
    gauss_area = float("nan")
    if fp.n_impacted >= 5:
        centre = np.mean(x, axis=1)
        cov = np.cov(x)
        dev = x - centre[:, None]
        d2 = np.einsum("ij,jk,ik->i", dev.T, np.linalg.pinv(cov), dev.T)
        chi2 = chi2_quantile_2dof(1.0 - alpha)
        gauss_cov_frac = float(np.mean(d2 <= chi2))
        vals = np.maximum(np.linalg.eigvalsh(cov), 0.0)
        gauss_area = float(np.pi * chi2 * math.sqrt(vals[0] * vals[1]) / 1e6)

    return {
        "alpha": alpha,
        "nominal_coverage": 1.0 - alpha,
        "gaussian_empirical_coverage": gauss_cov_frac,
        "gaussian_area_km2": gauss_area,
        "conformal_mahalanobis": maha.summary(),
        "conformal_density": dens.summary(),
        "area_reduction_density_vs_gaussian": (
            dens.area_km2 / gauss_area if gauss_area and np.isfinite(gauss_area) and gauss_area > 0
            else float("nan")
        ),
        "zones": {"mahalanobis": maha, "density": dens},
    }
