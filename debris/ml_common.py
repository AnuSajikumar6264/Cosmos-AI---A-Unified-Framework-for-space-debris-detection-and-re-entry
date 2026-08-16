"""
Shared machinery for the learning modules: dataset generation, regimes and a numpy fallback.

The single most useful thing about pairing a learned model with a validated physics engine is
that **labels are free and unlimited**.  :func:`build_trajectory_dataset` runs the propagator
from :mod:`debris.propagator` to produce as many labelled re-entry trajectories as wanted, with
exactly known impact points, so the learning modules never need a real dataset and there is
nothing to overfit to - every epoch can see fresh samples.

What the learned models are *for*, given the physics already works: the propagator takes
milliseconds per object but seconds per Monte Carlo ensemble, and a surrogate that maps a short
observation window straight to an impact point runs in microseconds.  That is what makes
continuous re-prediction against a live radar feed, or a very large fragment population,
tractable.  A surrogate is also differentiable, which the propagator is not.

Every module here degrades gracefully without torch: :class:`RidgeSurrogate` is a real
closed-form baseline that the neural models are measured against, not a stub.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .atmosphere import US76
from .drag import DragModel
from .geodesy import great_circle_distance, initial_bearing
from .propagator import DebrisObject, StateVector, propagate

# ------------------------------------------------------------------------ feature layout
#: Input channel names, in order.  Kept explicit because the graph adjacency below is defined
#: over these indices and a silent reordering would scramble it.
FEATURES = (
    "altitude",        # 0  normalised by 120 km
    "speed",           # 1  normalised by 8 km/s
    "sin_fpa",         # 2  flight-path angle, as a unit vector to avoid the wrap at +/-90
    "cos_fpa",         # 3
    "log_bc",          # 4  log10 ballistic coefficient / 4
    "downrange",       # 5  travelled so far, normalised by 3000 km
    "crossrange",      # 6  normalised by 300 km
    "log_density",     # 7  log10 of local density, offset and scaled
    "mach",            # 8  normalised by 25
)
N_FEATURES = len(FEATURES)

#: Target names, in order.
TARGETS = ("time_to_impact", "impact_downrange", "impact_crossrange")
N_TARGETS = len(TARGETS)

# Normalisation constants. Fixed rather than fitted so a model trained in one session can be
# applied in another without carrying a scaler object around.
_ALT_SCALE = 120_000.0
_SPEED_SCALE = 8_000.0
_DOWNRANGE_SCALE = 3_000_000.0
_CROSSRANGE_SCALE = 300_000.0
_TIME_SCALE = 3_000.0
_BC_SCALE = 4.0


def physics_adjacency() -> np.ndarray:
    """
    Channel-coupling graph, read off the equations of motion rather than learned.

    An edge means one channel appears directly in another's derivative:

    * altitude determines density, which scales drag, which decelerates speed;
    * speed and flight-path angle determine the rate of change of altitude and of downrange;
    * ballistic coefficient scales every drag term, so it couples to all the dynamic channels;
    * Mach follows from speed and the local temperature, hence from altitude.

    Supplying this instead of letting attention discover it from scratch is the "physics
    structured" part of the model: with a few thousand training trajectories there is not
    nearly enough signal to recover the coupling structure reliably, and getting it for free is
    strictly better than hoping.
    """
    a = np.eye(N_FEATURES)
    idx = {n: i for i, n in enumerate(FEATURES)}

    def link(x, y):
        a[idx[x], idx[y]] = 1.0
        a[idx[y], idx[x]] = 1.0

    link("altitude", "log_density")
    link("log_density", "speed")
    link("speed", "sin_fpa")
    link("speed", "cos_fpa")
    link("altitude", "sin_fpa")
    link("downrange", "speed")
    link("downrange", "cos_fpa")
    link("crossrange", "downrange")
    link("mach", "speed")
    link("mach", "altitude")
    for ch in ("altitude", "speed", "sin_fpa", "cos_fpa", "log_density", "mach"):
        link("log_bc", ch)
    # Row-normalise so the mixer averages neighbours rather than summing them, which would make
    # a channel's scale depend on how many neighbours it happens to have.
    return a / a.sum(axis=1, keepdims=True)


# ================================================================================ regimes
@dataclass(frozen=True)
class Regime:
    """
    A slice of the re-entry parameter space.

    Regimes are what make the continual-learning and federated experiments meaningful: they
    are genuinely different data distributions, not random splits of one distribution, so a
    model that does well on all of them has actually generalised rather than memorised.
    """

    name: str
    mass_range: tuple[float, float] = (5.0, 500.0)
    area_range: tuple[float, float] = (0.02, 2.0)
    altitude_range: tuple[float, float] = (95_000.0, 125_000.0)
    speed_range: tuple[float, float] = (6_800.0, 7_800.0)
    fpa_range: tuple[float, float] = (-4.0, -0.6)
    lat_range: tuple[float, float] = (-45.0, 45.0)
    azimuth_range: tuple[float, float] = (0.0, 360.0)
    shapes: tuple[str, ...] = ("tumbling", "cylinder", "box")
    materials: tuple[str, ...] = ("aluminium_oxidised", "stainless_steel", "titanium")
    wind_sigma: float = 12.0
    description: str = ""


#: Physically distinct regimes, used as continual-learning tasks and federated clients.
REGIMES: dict[str, Regime] = {
    "shallow_decay": Regime(
        "Shallow orbital decay", fpa_range=(-2.0, -0.8), speed_range=(7_300.0, 7_750.0),
        altitude_range=(105_000.0, 125_000.0),
        description="Natural decay from LEO: shallow entry, long footprints."),
    "steep_deorbit": Regime(
        "Steep controlled de-orbit", fpa_range=(-8.0, -3.0), speed_range=(7_000.0, 7_600.0),
        altitude_range=(95_000.0, 120_000.0),
        description="Deliberate perigee-lowering burn: steep, short, tightly bunched."),
    "suborbital_stage": Regime(
        "Suborbital launch stage", fpa_range=(-40.0, -12.0), speed_range=(1_500.0, 4_500.0),
        altitude_range=(60_000.0, 130_000.0), mass_range=(300.0, 30_000.0),
        area_range=(4.0, 60.0), shapes=("cylinder", "flat_plate"),
        description="Spent booster on a ballistic arc: low speed, steep, very large."),
    "light_fragments": Regime(
        "Light high-drag fragments", mass_range=(0.2, 15.0), area_range=(0.3, 6.0),
        shapes=("flat_plate", "tumbling"), materials=("cfrp", "mli", "aluminium_oxidised"),
        wind_sigma=25.0,
        description="Insulation and panel debris: tiny B, hour-long falls, wind dominated."),
    "dense_survivors": Regime(
        "Dense ground survivors", mass_range=(80.0, 900.0), area_range=(0.02, 0.4),
        shapes=("sphere", "box"), materials=("titanium", "stainless_steel", "inconel"),
        description="Tanks and engine parts: very high B, deep penetration, far downrange."),
}


# =============================================================================== dataset
@dataclass
class TrajectoryDataset:
    """
    Windowed observations with impact targets.

    ``x`` is ``(N, window, N_FEATURES)`` - what a tracker would have seen over a short arc.
    ``y`` is ``(N, N_TARGETS)`` - normalised time-to-impact and impact offset in the local
    range-safety frame.  ``meta`` keeps the un-normalised quantities for reporting.
    """

    x: np.ndarray
    y: np.ndarray
    meta: dict = field(default_factory=dict)
    regime: str = ""

    def __len__(self) -> int:
        return int(self.x.shape[0])

    def split(self, train_fraction: float = 0.8, seed: int = 0):
        """Deterministic shuffle-then-split into train and test halves."""
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(self))
        cut = int(round(train_fraction * len(self)))
        return self.subset(idx[:cut]), self.subset(idx[cut:])

    def subset(self, idx) -> "TrajectoryDataset":
        idx = np.asarray(idx, dtype=int)
        meta = {k: (v[idx] if isinstance(v, np.ndarray) and v.shape[:1] == (len(self),) else v)
                for k, v in self.meta.items()}
        return TrajectoryDataset(self.x[idx], self.y[idx], meta, self.regime)

    @staticmethod
    def concatenate(datasets) -> "TrajectoryDataset":
        datasets = [d for d in datasets if len(d)]
        if not datasets:
            raise ValueError("nothing to concatenate")
        return TrajectoryDataset(
            np.concatenate([d.x for d in datasets]),
            np.concatenate([d.y for d in datasets]),
            {"regimes": np.concatenate([np.full(len(d), d.regime, dtype=object)
                                        for d in datasets])},
            regime="mixed",
        )

    def denormalise_targets(self, y=None):
        """Targets back in seconds and metres."""
        y = self.y if y is None else np.asarray(y, dtype=float)
        return np.stack([y[:, 0] * _TIME_SCALE,
                         y[:, 1] * _DOWNRANGE_SCALE,
                         y[:, 2] * _CROSSRANGE_SCALE], axis=1)


def _window_features(traj, obj, window: int, observe_fraction: float):
    """
    Resample the first ``observe_fraction`` of a trajectory onto a fixed-length window.

    Resampling on a uniform *time* grid rather than taking the first ``window`` integrator steps
    matters: the integrator's step size varies by three orders of magnitude over a re-entry, so
    the first N steps would cover wildly different physical durations for different objects and
    the model would be given an inconsistent observation.
    """
    if traj.t.size < 4 or not traj.impacted:
        return None
    t0, t_end = float(traj.t[0]), float(traj.impact_time)
    t_obs = t0 + observe_fraction * (t_end - t0)
    grid = np.linspace(t0, t_obs, int(window))

    alt = np.interp(grid, traj.t, traj.altitude)
    spd = np.interp(grid, traj.t, traj.speed)
    mach = np.interp(grid, traj.t, traj.mach)
    lat = np.interp(grid, traj.t, traj.latitude)
    lon = np.interp(grid, traj.t, traj.longitude)

    # Flight-path angle from the vertical rate over the horizontal rate, on the same grid.
    d_alt = np.gradient(alt, grid, edge_order=1)
    horiz = np.sqrt(np.maximum(spd**2 - d_alt**2, 1.0))
    fpa = np.arctan2(d_alt, horiz)

    dist = great_circle_distance(lat[0], lon[0], lat, lon)
    brg = initial_bearing(lat[0], lon[0], lat, lon)
    ref_az = float(brg[min(3, len(brg) - 1)])
    rel = np.radians(brg - ref_az)
    down, cross = dist * np.cos(rel), dist * np.sin(rel)

    rho = np.maximum(US76.density(alt), 1e-30)
    log_bc = math.log10(max(obj.ballistic_coefficient(), 1e-3))

    feats = np.stack([
        alt / _ALT_SCALE,
        spd / _SPEED_SCALE,
        np.sin(fpa),
        np.cos(fpa),
        np.full(len(grid), log_bc / _BC_SCALE),
        down / _DOWNRANGE_SCALE,
        cross / _CROSSRANGE_SCALE,
        (np.log10(rho) + 12.0) / 14.0,
        mach / 25.0,
    ], axis=1)
    return feats, (lat[0], lon[0], ref_az, t_obs)


def build_trajectory_dataset(
    n_samples: int = 600,
    regime: Regime | str = "shallow_decay",
    *,
    window: int = 24,
    observe_fraction: float = 0.25,
    seed: int = 0,
    wind: bool = True,
    max_downrange: float = 8_000_000.0,
    max_fall_time: float = 12_000.0,
    progress=None,
) -> TrajectoryDataset:
    """
    Generate labelled trajectories by running the physics propagator.

    The model observes the first ``observe_fraction`` of the fall - by default the first
    quarter, which for an orbital entry is roughly the hypersonic arc a tracking radar would
    actually see - and predicts where and when it lands.

    ``max_downrange`` / ``max_fall_time`` exist to keep the *target* well posed, not to make the
    numbers look better.  The shallowest entries skip off the atmosphere and travel most of the
    way around the Earth; a great-circle downrange saturates at the antipode and cannot
    represent more than half a revolution, so those samples have an ambiguous label and would
    teach the model nothing except to fit noise.  Anything excluded is reported in
    ``meta["rejected"]`` rather than silently dropped - a filter that is invisible in the output
    is indistinguishable from a bug.

    Costs roughly 15 ms per sample, so a few thousand samples take under a minute.  Cache the
    result; do not rebuild it per epoch.
    """
    reg = REGIMES[regime] if isinstance(regime, str) else regime
    rng = np.random.default_rng(seed)
    from .propagator import WindField

    xs, ys, bcs, masses, fall_times, downranges = [], [], [], [], [], []
    attempts = 0
    rejected = {"no_impact": 0, "too_far": 0, "too_slow": 0}
    max_attempts = int(n_samples * 6)
    while len(xs) < n_samples and attempts < max_attempts:
        attempts += 1
        mass = float(10 ** rng.uniform(*np.log10(reg.mass_range)))
        area = float(10 ** rng.uniform(*np.log10(reg.area_range)))
        shape = str(rng.choice(reg.shapes))
        material = str(rng.choice(reg.materials))
        obj = DebrisObject(
            "sample", mass=mass, area=area, material=material,
            drag=DragModel(shape, reference_length=float(np.sqrt(area))))
        state = StateVector.from_geodetic(
            float(rng.uniform(*reg.lat_range)), float(rng.uniform(-180.0, 180.0)),
            float(rng.uniform(*reg.altitude_range)), float(rng.uniform(*reg.speed_range)),
            float(rng.uniform(*reg.fpa_range)), float(rng.uniform(*reg.azimuth_range)))
        wf = WindField(float(rng.normal(0, reg.wind_sigma)),
                       float(rng.normal(0, reg.wind_sigma))) if wind else None

        traj = propagate(state, obj, wind=wf, store_trajectory=True, rtol=1e-6)
        packed = _window_features(traj, obj, window, observe_fraction)
        if packed is None:
            rejected["no_impact"] += 1
            continue
        feats, (lat0, lon0, ref_az, t_obs) = packed

        dist = float(great_circle_distance(lat0, lon0, traj.impact_latitude,
                                          traj.impact_longitude))
        if dist > max_downrange:
            rejected["too_far"] += 1
            continue
        if traj.flight_time > max_fall_time:
            rejected["too_slow"] += 1
            continue
        brg = float(initial_bearing(lat0, lon0, traj.impact_latitude, traj.impact_longitude))
        rel = math.radians(brg - ref_az)
        xs.append(feats)
        ys.append([(traj.impact_time - t_obs) / _TIME_SCALE,
                   dist * math.cos(rel) / _DOWNRANGE_SCALE,
                   dist * math.sin(rel) / _CROSSRANGE_SCALE])
        bcs.append(obj.ballistic_coefficient())
        masses.append(mass)
        fall_times.append(traj.flight_time)
        downranges.append(dist)
        if progress is not None and len(xs) % 50 == 0:
            progress(len(xs) / n_samples)

    if not xs:
        raise RuntimeError(f"no usable trajectories for regime {reg.name!r}")
    return TrajectoryDataset(
        np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32),
        meta={"ballistic_coefficient": np.asarray(bcs), "mass": np.asarray(masses),
              "fall_time": np.asarray(fall_times), "downrange": np.asarray(downranges),
              "window": window, "observe_fraction": observe_fraction,
              "yield_rate": len(xs) / max(attempts, 1), "rejected": dict(rejected),
              "attempts": attempts},
        regime=reg.name,
    )


# ============================================================================== metrics
def surrogate_metrics(y_true, y_pred) -> dict:
    """
    Errors in physical units, which is the only form worth reporting.

    A normalised MSE of 0.01 means nothing to anyone; "median impact-point error 38 km" is
    immediately comparable against the Monte Carlo dispersion the surrogate is meant to
    replace.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    dt = (yp[:, 0] - yt[:, 0]) * _TIME_SCALE
    dd = (yp[:, 1] - yt[:, 1]) * _DOWNRANGE_SCALE
    dc = (yp[:, 2] - yt[:, 2]) * _CROSSRANGE_SCALE
    radial = np.hypot(dd, dc)
    true_dr = yt[:, 1] * _DOWNRANGE_SCALE
    return {
        "n": int(len(yt)),
        "time_mae_s": float(np.mean(np.abs(dt))),
        "time_rmse_s": float(np.sqrt(np.mean(dt**2))),
        "downrange_mae_km": float(np.mean(np.abs(dd))) / 1e3,
        "crossrange_mae_km": float(np.mean(np.abs(dc))) / 1e3,
        "impact_median_error_km": float(np.median(radial)) / 1e3,
        "impact_p90_error_km": float(np.quantile(radial, 0.90)) / 1e3,
        "downrange_relative_error": float(np.mean(np.abs(dd) / np.maximum(np.abs(true_dr), 1e3))),
        "r2_downrange": _r2(yt[:, 1], yp[:, 1]),
        "r2_time": _r2(yt[:, 0], yp[:, 0]),
    }


def _r2(t, p) -> float:
    t, p = np.asarray(t, dtype=float), np.asarray(p, dtype=float)
    ss_res = float(np.sum((t - p) ** 2))
    ss_tot = float(np.sum((t - t.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


# ============================================================================== fallback
@dataclass
class RidgeSurrogate:
    """
    Closed-form ridge regression on flattened window features - the numpy fallback and baseline.

    This is a genuine model, not a placeholder: with a window of 24 x 9 features it has a few
    hundred parameters, trains in milliseconds by solving the normal equations, and is a fair
    linear baseline.  Reporting the transformer's numbers without it would leave the obvious
    question - "does the architecture actually buy anything?" - unanswered.

    Includes squared terms, because the underlying map is strongly nonlinear (downrange goes
    roughly as log B) and a purely linear baseline would be a straw man.
    """

    alpha: float = 1.0
    quadratic: bool = True
    coef_: np.ndarray | None = None
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None

    def _design(self, x):
        flat = np.asarray(x, dtype=float).reshape(len(x), -1)
        if self.quadratic:
            flat = np.concatenate([flat, flat**2], axis=1)
        return flat

    def fit(self, dataset: TrajectoryDataset) -> "RidgeSurrogate":
        a = self._design(dataset.x)
        self.mean_ = a.mean(axis=0)
        self.scale_ = np.maximum(a.std(axis=0), 1e-8)
        z = (a - self.mean_) / self.scale_
        z = np.concatenate([z, np.ones((len(z), 1))], axis=1)
        n_feat = z.shape[1]
        reg = self.alpha * np.eye(n_feat)
        reg[-1, -1] = 0.0  # never penalise the intercept
        self.coef_ = np.linalg.solve(z.T @ z + reg, z.T @ np.asarray(dataset.y, dtype=float))
        return self

    def predict(self, x) -> np.ndarray:
        if self.coef_ is None:
            raise RuntimeError("call fit() first")
        a = self._design(x)
        z = (a - self.mean_) / self.scale_
        z = np.concatenate([z, np.ones((len(z), 1))], axis=1)
        return z @ self.coef_

    def evaluate(self, dataset: TrajectoryDataset) -> dict:
        return surrogate_metrics(dataset.y, self.predict(dataset.x))

    @property
    def n_parameters(self) -> int:
        return int(self.coef_.size) if self.coef_ is not None else 0

    @classmethod
    def tune(cls, train: TrajectoryDataset, alphas=(0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0),
             val_fraction: float = 0.25, seed: int = 0, quadratic: bool = True):
        """
        Fit with the ridge penalty chosen on a held-out split, scored on the **90th-percentile**
        impact error.

        Selecting on the median instead picks a badly overfitted model here and looks fine while
        doing it.  With a 24 x 9 window plus squared terms there are more features than training
        samples, so a small penalty leaves the system underdetermined: the median error improves
        while a handful of test points blow up, driving R^2 to around -1e10.  A tail statistic
        sees that; a median does not.
        """
        tr, val = train.split(1.0 - val_fraction, seed=seed)
        best, best_score = None, float("inf")
        for a in alphas:
            m = cls(alpha=float(a), quadratic=quadratic).fit(tr)
            score = m.evaluate(val)["impact_p90_error_km"]
            if np.isfinite(score) and score < best_score:
                best, best_score = float(a), score
        # Refit the winner on all the training data.
        return cls(alpha=best if best is not None else 1.0, quadratic=quadratic).fit(train)


def torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:
        return False
