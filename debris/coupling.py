"""
The coupling layer: telemetry anomalies and subsystem health drive the debris physics.

This is what makes the system one thing rather than two dashboards side by side.  The
existing digital twin answers "is this satellite unwell, and how?".  The debris stack
answers "if it comes apart, where does it land and who is at risk?".  The link between them
is that *which subsystem is failing changes the physics of the breakup* - not just its
probability.

Forward direction: health -> breakup physics
--------------------------------------------
Each mapping below is a stated, inspectable hypothesis, not a fitted model - there is no
labelled corpus of satellite breakups to fit against, and pretending otherwise would be
worse than being explicit.  The reasoning:

* **Propulsion System** severity drives *explosive* rather than aerodynamic breakup.
  Residual hypergolic propellant and pressurised COPVs are the single most common cause of
  on-orbit fragmentation events in the historical record.  It therefore raises fragmentation
  probability, sets the breakup type, and scales the ejection delta-v - which widens the
  footprint by hundreds of kilometres.
* **Power System** severity contributes through battery thermal runaway, historically the
  second major fragmentation cause.  Raises probability and yield, but with less delta-v
  than a propellant rupture.
* **Thermal Control** severity is a proxy for structural margin.  A satellite that cannot
  reject heat loses structural strength and comes apart *higher* in the atmosphere, which
  means lower dynamic pressure at breakup, more fragments surviving, and a longer footprint.
* **Attitude Control** severity means tumbling.  A tumbling body presents a larger average
  cross-section, so it decelerates earlier and breaks up higher - and its ballistic
  coefficient becomes much less predictable, which widens the dispersion.
* **Communication / Data Storage / On-board Computer** severity does *not* change the
  physics.  It degrades the *observability* of the event: less telemetry means a worse state
  estimate, which enters as inflated state uncertainty rather than a different trajectory.
  Keeping this separate matters - it is the difference between "more dangerous" and "less
  well known".

Reverse direction: debris observation -> health
----------------------------------------------
:func:`debris_evidence_to_health` closes the loop.  If the imaging chain detects fragments
near the spacecraft, that is direct physical evidence of shedding, and it should raise the
anomaly score and degrade structural confidence regardless of what the telemetry says.  A
satellite can be shedding insulation while reporting nominal on every channel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .atmosphere import US76, Atmosphere
from .fragmentation import (
    BreakupType,
    DebrisCloud,
    ParentType,
    generate_debris_cloud,
)
from .monte_carlo import (
    ConformalZone,
    DispersionConfig,
    Footprint,
    density_zone,
    mahalanobis_zone,
    run_cloud_dispersion,
)
from .propagator import StateVector
from .risk import PopulationModel, RiskAssessment, assess_footprint

#: Canonical subsystem names, matching the digital twin's telemetry model.
SUBSYSTEMS = (
    "Attitude Control",
    "Power System",
    "Thermal Control",
    "Communication",
    "Payload Sensors",
    "On-board Computer",
    "Propulsion System",
    "Data Storage Unit",
)

#: Subsystems whose failure changes the breakup *physics*.
PHYSICS_DRIVING = ("Propulsion System", "Power System", "Thermal Control", "Attitude Control")

#: Subsystems whose failure changes only how well the event can be *observed*.
OBSERVABILITY_DRIVING = ("Communication", "Data Storage Unit", "On-board Computer")


@dataclass
class SubsystemHealth:
    """
    Subsystem severities in [0, 1], where 0 is nominal and 1 is failed.

    Accepts the shape the existing dashboard already produces - a mapping of subsystem name
    to either a bare severity or a ``(severity, status, colour)`` tuple - so the twin's
    health model can be handed straight over without reshaping.
    """

    severities: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dashboard(cls, health: dict) -> "SubsystemHealth":
        """Build from ``{name: (value, status, colour)}`` or ``{name: value}``."""
        out = {}
        for k, v in (health or {}).items():
            out[k] = float(v[0]) if isinstance(v, (tuple, list)) else float(v)
        return cls(out)

    @classmethod
    def nominal(cls) -> "SubsystemHealth":
        return cls({k: 0.05 for k in SUBSYSTEMS})

    def get(self, name: str, default: float = 0.0) -> float:
        return float(self.severities.get(name, default))

    @property
    def mean_severity(self) -> float:
        v = list(self.severities.values())
        return float(np.mean(v)) if v else 0.0

    @property
    def max_severity(self) -> float:
        v = list(self.severities.values())
        return float(np.max(v)) if v else 0.0

    @property
    def physics_severity(self) -> float:
        """Worst severity among the subsystems that change the breakup physics."""
        return max((self.get(k) for k in PHYSICS_DRIVING), default=0.0)

    @property
    def observability_severity(self) -> float:
        """Worst severity among the subsystems that only degrade state knowledge."""
        return max((self.get(k) for k in OBSERVABILITY_DRIVING), default=0.0)

    def critical_subsystems(self, threshold: float = 0.55) -> list[str]:
        return [k for k, v in self.severities.items() if v >= threshold]

    def with_penalty(self, name: str, amount: float) -> "SubsystemHealth":
        s = dict(self.severities)
        s[name] = float(np.clip(s.get(name, 0.0) + amount, 0.0, 1.0))
        return SubsystemHealth(s)


# ============================================================================== hazard
@dataclass
class BreakupHazard:
    """
    Breakup physics implied by the current anomaly score and subsystem health.

    Every field here is an input to :mod:`debris.fragmentation` or
    :mod:`debris.monte_carlo`, so the health assessment feeds the physics directly rather
    than being displayed alongside it.
    """

    fragmentation_probability: float
    breakup_altitude: float           # [m]
    breakup_type: BreakupType
    parent_type: ParentType
    delta_v_scale: float
    sbm_scaling: float
    expected_fragments: int
    bc_sigma_log10: float             # inflated by health degradation
    state_position_sigma: float       # inflated by observability degradation
    state_speed_sigma: float
    dominant_driver: str
    rationale: list[str] = field(default_factory=list)

    @property
    def hazard_band(self) -> str:
        p = self.fragmentation_probability
        if p < 0.05:
            return "LOW"
        if p < 0.25:
            return "MODERATE"
        if p < 0.60:
            return "HIGH"
        return "SEVERE"

    def dispersion_config(self, n_samples: int = 400, seed: int | None = 42,
                          wind_zonal: float = 0.0, wind_meridional: float = 0.0,
                          wind_sigma: float = 12.0) -> DispersionConfig:
        """A :class:`DispersionConfig` carrying this hazard's inflated uncertainties."""
        return DispersionConfig(
            n_samples=n_samples,
            position_sigma=self.state_position_sigma,
            speed_sigma=self.state_speed_sigma,
            bc_sigma_log10=self.bc_sigma_log10,
            wind_zonal=wind_zonal,
            wind_meridional=wind_meridional,
            wind_sigma=wind_sigma,
            seed=seed,
        )

    def summary(self) -> dict:
        return {
            "fragmentation_probability": self.fragmentation_probability,
            "hazard_band": self.hazard_band,
            "breakup_altitude_km": self.breakup_altitude / 1000.0,
            "breakup_type": self.breakup_type.value,
            "parent_type": self.parent_type.value,
            "delta_v_scale": self.delta_v_scale,
            "sbm_scaling": self.sbm_scaling,
            "expected_fragments": self.expected_fragments,
            "bc_sigma_log10": self.bc_sigma_log10,
            "state_position_sigma_m": self.state_position_sigma,
            "dominant_driver": self.dominant_driver,
        }


def assess_breakup_hazard(
    anomaly_score: float,
    health: SubsystemHealth | dict | None = None,
    *,
    parent_type: ParentType = ParentType.SPACECRAFT,
    base_altitude: float = 78_000.0,
    base_position_sigma: float = 400.0,
    base_speed_sigma: float = 12.0,
    base_bc_sigma: float = 0.15,
) -> BreakupHazard:
    """
    Map an anomaly score and subsystem health onto breakup physics.

    ``anomaly_score`` is the twin's detector output in [0, 1] (reconstruction error for the
    autoencoder, class probability for the CNN, forecast residual for the LSTM/GRU).

    The fragmentation probability is a logistic in the anomaly score and the three
    subsystems with a physical failure path to fragmentation.  Coefficients are chosen so
    that: a nominal satellite with a mild anomaly sits near a few percent; a satellite with a
    failed propulsion system and a strong anomaly approaches certainty; and no single
    subsystem alone can drive it past ~0.5, because historically fragmentation needs both an
    energy source and a trigger.
    """
    h = health if isinstance(health, SubsystemHealth) else SubsystemHealth.from_dashboard(health or {})
    a = float(np.clip(anomaly_score, 0.0, 1.0))

    prop = h.get("Propulsion System")
    power = h.get("Power System")
    therm = h.get("Thermal Control")
    att = h.get("Attitude Control")

    # ---- fragmentation probability -------------------------------------------------
    # Calibration targets, in order of importance:
    #   * a nominal satellite must read ~1 %, not 5 % - historically only a handful of
    #     fragmentation events occur per year across thousands of orbiting objects, so a
    #     healthy spacecraft's prior has to be small;
    #   * a failed *energetic* subsystem (propellant, battery) must reach 0.7-0.85, since
    #     those are the two dominant causes in the historical record;
    #   * a failed non-energetic subsystem alone must stay well below 0.5 - fragmentation
    #     needs an energy source as well as a trigger;
    #   * both together must approach certainty.
    z = -5.2 + 3.2 * a + 4.2 * prop + 3.4 * power + 1.8 * therm + 0.8 * att
    p_frag = 1.0 / (1.0 + math.exp(-z))

    # ---- breakup type and energetics ------------------------------------------------
    energetic = max(prop, power)
    if energetic >= 0.55:
        btype = BreakupType.EXPLOSION
        dv_scale = 0.6 + 1.8 * prop + 0.6 * power
    elif energetic >= 0.30:
        btype = BreakupType.EXPLOSION
        dv_scale = 0.3 + 0.9 * energetic
    else:
        btype = BreakupType.AERODYNAMIC
        dv_scale = 1.0 + 1.5 * energetic

    # ---- breakup altitude ------------------------------------------------------------
    # Tumbling raises it (earlier deceleration); intact thermal/structural margin lowers it
    # (the structure survives deeper into the atmosphere).
    altitude = base_altitude + 10_000.0 * att - 8_000.0 * (1.0 - therm)
    if btype is BreakupType.EXPLOSION:
        # An energetic rupture does not wait for air loads.
        altitude += 6_000.0 * energetic
    altitude = float(np.clip(altitude, 60_000.0, 110_000.0))

    # ---- yield and uncertainty inflation ---------------------------------------------
    sbm_scaling = 0.5 + 1.5 * energetic + 0.4 * a
    expected_fragments = int(round(60 + 340 * p_frag + 200 * energetic))

    # A degraded, tumbling satellite has a far less predictable ballistic coefficient.
    bc_sigma = base_bc_sigma * (1.0 + 0.9 * att + 0.5 * h.mean_severity)

    # Lost comms/storage/computer degrades the state estimate, not the trajectory.
    obs = h.observability_severity
    pos_sigma = base_position_sigma * (1.0 + 6.0 * obs)
    spd_sigma = base_speed_sigma * (1.0 + 3.0 * obs)

    drivers = {"Propulsion System": 4.2 * prop, "Power System": 3.4 * power,
               "Thermal Control": 1.8 * therm, "Attitude Control": 0.8 * att,
               "anomaly score": 3.2 * a}
    dominant = max(drivers, key=drivers.get)

    rationale = [
        f"P(fragmentation) = {p_frag:.3f} from logit {z:+.2f}; dominant term: {dominant}.",
        f"Breakup type {btype.value} (energetic severity {energetic:.2f}); "
        f"delta-v scale x{dv_scale:.2f}.",
        f"Breakup altitude {altitude / 1000:.1f} km: base {base_altitude / 1000:.0f} "
        f"{'+' if att else ''}{10 * att:.1f} km tumbling, "
        f"-{8 * (1 - therm):.1f} km structural margin.",
        f"Ballistic-coefficient sigma inflated {bc_sigma / base_bc_sigma:.2f}x by attitude "
        f"and overall degradation.",
        f"State uncertainty inflated {pos_sigma / base_position_sigma:.2f}x by "
        f"observability loss ({obs:.2f}).",
    ]

    return BreakupHazard(
        fragmentation_probability=float(p_frag),
        breakup_altitude=altitude,
        breakup_type=btype,
        parent_type=parent_type,
        delta_v_scale=float(dv_scale),
        sbm_scaling=float(sbm_scaling),
        expected_fragments=expected_fragments,
        bc_sigma_log10=float(bc_sigma),
        state_position_sigma=float(pos_sigma),
        state_speed_sigma=float(spd_sigma),
        dominant_driver=dominant,
        rationale=rationale,
    )


# ============================================================== reverse coupling
@dataclass
class DebrisEvidence:
    """What the imaging chain saw near the spacecraft, and what it implies."""

    n_detections: int
    mean_confidence: float
    largest_size_m: float
    anomaly_boost: float
    health_penalties: dict[str, float]
    interpretation: str

    def apply(self, health: SubsystemHealth) -> SubsystemHealth:
        out = health
        for name, amount in self.health_penalties.items():
            out = out.with_penalty(name, amount)
        return out


def debris_evidence_to_health(
    n_detections: int,
    mean_confidence: float = 0.8,
    largest_size_m: float = 0.1,
    *,
    frame_count: int = 1,
) -> DebrisEvidence:
    """
    Turn detections of debris near the spacecraft into an anomaly and health update.

    This is the loop-closing direction.  Telemetry can read nominal on every channel while
    a satellite quietly sheds insulation, and conversely a noisy sensor can look like a
    fault when nothing is wrong.  A visual detection of separated material is *physical*
    evidence and should move the assessment on its own.

    The penalty is attributed by fragment size, which is a crude but meaningful
    discriminator: centimetre-scale flecks read as insulation or paint loss (thermal
    control), while decimetre-scale pieces imply structural or appendage failure (attitude
    control and payload optics, which are what break off).
    """
    n = max(int(n_detections), 0)
    conf = float(np.clip(mean_confidence, 0.0, 1.0))
    rate = n / max(int(frame_count), 1)

    if n == 0:
        return DebrisEvidence(0, 0.0, 0.0, 0.0, {},
                              "No separated material detected; no evidence-based update.")

    # Saturating in detection rate: one fragment is a strong signal, twenty is not twenty
    # times stronger.
    boost = float(np.clip(conf * (1.0 - math.exp(-rate / 3.0)) * 0.75, 0.0, 0.75))

    penalties: dict[str, float] = {}
    if largest_size_m < 0.05:
        penalties["Thermal Control"] = 0.30 * boost
        penalties["Payload Sensors"] = 0.10 * boost
        interp = (f"{n} sub-5 cm fragments: consistent with MLI/paint shedding - thermal "
                  f"blanket degradation rather than structural failure.")
    elif largest_size_m < 0.25:
        penalties["Thermal Control"] = 0.35 * boost
        penalties["Attitude Control"] = 0.25 * boost
        penalties["Payload Sensors"] = 0.20 * boost
        interp = (f"{n} fragments up to {largest_size_m * 100:.0f} cm: blanket or appendage "
                  f"material separating; expect attitude disturbance from mass loss.")
    else:
        penalties["Attitude Control"] = 0.55 * boost
        penalties["Payload Sensors"] = 0.40 * boost
        penalties["Power System"] = 0.35 * boost
        interp = (f"{n} fragments, largest {largest_size_m * 100:.0f} cm: structural or "
                  f"solar-array failure. Treat as an in-progress breakup.")

    return DebrisEvidence(n, conf, float(largest_size_m), boost, penalties, interp)


# ================================================================ predictive fault link
@dataclass
class FailureForecast:
    """Extrapolation of a degradation trend to a failure threshold."""

    time_to_threshold: float          # in samples (or seconds if dt given)
    doubling_time: float
    growth_rate: float                # per sample, in log space
    r_squared: float
    current_level: float
    threshold: float
    confidence_low: float
    confidence_high: float
    trend: str

    @property
    def credible(self) -> bool:
        """Whether the fit is good enough to act on."""
        return self.r_squared >= 0.5 and self.growth_rate > 0

    def summary(self) -> dict:
        return {
            "trend": self.trend,
            "time_to_threshold": self.time_to_threshold,
            "confidence_interval": (self.confidence_low, self.confidence_high),
            "doubling_time": self.doubling_time,
            "growth_rate_per_sample": self.growth_rate,
            "r_squared": self.r_squared,
            "credible": self.credible,
            "current_level": self.current_level,
            "threshold": self.threshold,
        }


def estimate_time_to_breakup(
    error_series,
    threshold: float | None = None,
    *,
    dt: float = 1.0,
    threshold_multiple: float = 5.0,
) -> FailureForecast:
    """
    Extrapolate an anomaly-score or reconstruction-error trend to a failure threshold.

    This is the "predictive fault analysis" half of the twin's remit, and it deliberately
    fits in **log space**: degradation processes (crack growth, battery capacity fade,
    thermal runaway onset) are multiplicative, so a linear fit systematically under-predicts
    how soon a threshold is reached.

    Returns a forecast with a confidence interval derived from the regression's standard
    error, and a ``credible`` flag - an ill-fitting trend should not be presented as a
    countdown.  ``time_to_threshold`` is in the same units as ``dt``.
    """
    y = np.asarray(error_series, dtype=float)
    y = y[np.isfinite(y)]
    if y.size < 6:
        return FailureForecast(float("inf"), float("inf"), 0.0, 0.0,
                               float(y[-1]) if y.size else 0.0, 0.0, float("inf"),
                               float("inf"), "insufficient data")

    thr = float(threshold) if threshold is not None else float(np.median(y) * threshold_multiple)
    thr = max(thr, float(y[-1]) * 1.001)

    x = np.arange(y.size, dtype=float)
    ly = np.log(np.maximum(y, 1e-12))
    # Ordinary least squares on log(level); slope is the fractional growth rate per sample.
    n = y.size
    sx, sy = x.mean(), ly.mean()
    sxx = float(np.sum((x - sx) ** 2))
    if sxx <= 0:
        return FailureForecast(float("inf"), float("inf"), 0.0, 0.0, float(y[-1]), thr,
                               float("inf"), float("inf"), "degenerate")
    slope = float(np.sum((x - sx) * (ly - sy)) / sxx)
    intercept = sy - slope * sx
    pred = intercept + slope * x
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - sy) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    se_slope = math.sqrt(ss_res / max(n - 2, 1) / sxx) if sxx > 0 else float("inf")

    # A weak fit carries no directional information, whatever the sign of the slope: a flat
    # noisy series will always have some tiny non-zero slope, and labelling that "improving"
    # would be reading a trend out of noise.
    if r2 < 0.30 or abs(slope) < 2e-3:
        return FailureForecast(float("inf"), float("inf"), slope, r2, float(y[-1]), thr,
                               float("inf"), float("inf"), "no significant trend")
    if slope <= 0:
        return FailureForecast(float("inf"), float("inf"), slope, r2, float(y[-1]), thr,
                               float("inf"), float("inf"), "improving")

    def t_to(s):
        if s <= 0:
            return float("inf")
        return max((math.log(thr) - intercept) / s - x[-1], 0.0) * dt

    t_hat = t_to(slope)
    # 95% interval from the slope's standard error; a steeper slope arrives sooner.
    t_low = t_to(slope + 1.96 * se_slope)
    t_high = t_to(max(slope - 1.96 * se_slope, 1e-9))

    trend = "degrading fast" if slope > 0.02 else "degrading"
    return FailureForecast(
        time_to_threshold=t_hat,
        doubling_time=math.log(2.0) / slope * dt,
        growth_rate=slope,
        r_squared=r2,
        current_level=float(y[-1]),
        threshold=thr,
        confidence_low=t_low,
        confidence_high=t_high,
        trend=trend,
    )


# ================================================================== end-to-end pipeline
@dataclass
class CoupledPrediction:
    """Everything the coupled chain produces, from telemetry anomaly to ground risk."""

    hazard: BreakupHazard
    cloud: DebrisCloud
    footprint: Footprint
    risk: RiskAssessment
    zone_95: ConformalZone
    zone_99: ConformalZone
    anomaly_score: float
    health: SubsystemHealth
    forecast: FailureForecast | None = None

    @property
    def risk_weighted_casualties(self) -> float:
        """
        Expected casualties *weighted by the probability that a breakup happens at all*.

        This is the number to compare against the 1e-4 threshold when the breakup is a
        possibility rather than an observed fact - reporting the conditional figure alone
        overstates the risk of a satellite that is merely unwell.
        """
        return self.hazard.fragmentation_probability * self.risk.expected_casualties

    def summary(self) -> dict:
        return {
            "anomaly_score": self.anomaly_score,
            "health_mean_severity": self.health.mean_severity,
            "critical_subsystems": self.health.critical_subsystems(),
            **{f"hazard_{k}": v for k, v in self.hazard.summary().items()},
            **{f"cloud_{k}": v for k, v in self.cloud.summary().items()},
            **{f"footprint_{k}": v for k, v in self.footprint.statistics().items()},
            **{f"risk_{k}": v for k, v in self.risk.summary().items()},
            "risk_weighted_casualties": self.risk_weighted_casualties,
            "zone_95_area_km2": self.zone_95.area_km2,
            "zone_99_area_km2": self.zone_99.area_km2,
        }


def run_coupled_prediction(
    anomaly_score: float,
    health: SubsystemHealth | dict | None,
    *,
    latitude: float = 13.72,
    longitude: float = 80.23,
    entry_speed: float = 7_400.0,
    flight_path_angle: float = -1.5,
    azimuth: float = 140.0,
    parent_mass: float = 1_800.0,
    n_samples_per_fragment: int = 3,
    max_fragments: int = 150,
    wind_zonal: float = 0.0,
    wind_meridional: float = 0.0,
    population: PopulationModel | None = None,
    atmosphere: Atmosphere = US76,
    error_series=None,
    seed: int | None = 42,
) -> CoupledPrediction:
    """
    Full chain: anomaly score + health -> breakup physics -> fragment cloud -> dispersed
    footprint -> conformal zones -> ground risk.

    The whole point is that changing a *subsystem severity* changes the impact footprint and
    the casualty number, through physics rather than through a lookup table.
    """
    h = health if isinstance(health, SubsystemHealth) else SubsystemHealth.from_dashboard(health or {})
    hazard = assess_breakup_hazard(anomaly_score, h)

    state = StateVector.from_geodetic(
        latitude, longitude, hazard.breakup_altitude, entry_speed,
        flight_path_angle, azimuth,
    )
    cloud = generate_debris_cloud(
        state,
        parent_mass=parent_mass,
        breakup=hazard.breakup_type,
        parent=hazard.parent_type,
        scaling=hazard.sbm_scaling,
        delta_v_scale=hazard.delta_v_scale,
        max_fragments=max_fragments,
        rng=seed,
    )
    cfg = hazard.dispersion_config(
        seed=seed, wind_zonal=wind_zonal, wind_meridional=wind_meridional
    )
    footprint = run_cloud_dispersion(
        cloud, cfg, samples_per_fragment=n_samples_per_fragment, atmosphere=atmosphere
    )
    risk = assess_footprint(footprint, population)
    z95 = density_zone(footprint, 0.05)
    z99 = mahalanobis_zone(footprint, 0.01)

    forecast = estimate_time_to_breakup(error_series) if error_series is not None else None
    return CoupledPrediction(hazard, cloud, footprint, risk, z95, z99,
                             float(anomaly_score), h, forecast)
