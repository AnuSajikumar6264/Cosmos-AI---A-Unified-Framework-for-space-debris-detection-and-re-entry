"""
Six-degree-of-freedom-free (3-DOF point mass) re-entry propagator with coupled
aerothermal demise.

Equations of motion, integrated in the **rotating ECEF frame** so that the
atmosphere is stationary in the integration frame:

    dr/dt = v
    dv/dt = g_J2(r) + a_drag(v_rel) - 2*omega x v - omega x (omega x r)

with ``v_rel = v - v_wind``.  Writing it this way means the Coriolis and centrifugal
terms - which are what rotate a debris footprint noticeably eastward over a 10-minute
fall - come out of the frame rather than being patched in.

Two extra states are carried so that survivability is part of the same integration
rather than a post-hoc filter:

    dT/dt  = (eta * q_stag * A - sigma * eps * 4A * (T^4 - T_amb^4)) / (m * cp)
    dm/dt  = -(net heat) / L_fusion             once T reaches the melt point

so an object can *demise* mid-flight and simply never produce an impact point.  This
is a lumped-mass, single-node simplification of what tools like ORSAT/SCARAB do; it
captures the first-order split between fragments that reach the ground and fragments
that do not, which is the split that matters for ground risk.

The integrator is Dormand-Prince 5(4) with adaptive step size and FSAL.  Step size is
error-controlled rather than heuristic, because a re-entry spans a near-vacuum coast
(where 60-second steps are fine) and a peak-deceleration pulse a few seconds long
(where they are catastrophically wrong).

Known characteristic: very low ballistic coefficients are *stiff*.  Terminal velocity is
an attracting equilibrium with time constant tau = 2B / (rho * v), which for an MLI
blanket (B ~ 0.6 kg/m^2) is under 0.1 s while the fall itself lasts an hour.  An explicit
method is then limited by stability rather than accuracy, so loosening the tolerance
barely reduces the step count.  Such fragments cost a few thousand steps each (~0.2 s of
wall clock); everything with B above ~10 kg/m^2 costs a couple of hundred.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .atmosphere import US76, US76_TABLE, Atmosphere, mean_free_path
from .constants import (
    CASUALTY_KE_THRESHOLD,
    EARTH_J2,
    EARTH_MU,
    EARTH_OMEGA,
    G0,
    SUTTON_GRAVES_K,
    WGS84_A,
)
from .drag import DragModel, area_from_characteristic_length, characteristic_length_from_area
from .geodesy import (
    ecef_to_enu,
    ecef_to_geodetic,
    ecef_to_geodetic_scalar,
    enu_basis,
    geodetic_to_ecef,
    great_circle_distance,
    velocity_from_launch_frame,
)
from .materials import STEFAN_BOLTZMANN, Material, get_material

# ============================================================================= objects


@dataclass(frozen=True)
class DebrisObject:
    """
    A single re-entering body: spent stage, fairing half, or breakup fragment.

    Parameters
    ----------
    mass, area:
        Mass [kg] and *average cross-sectional* area [m^2].  For a tumbling fragment
        the average projected area is one quarter of its total surface area (Cauchy's
        theorem), which is what the drag and heating models assume.
    drag:
        :class:`~debris.drag.DragModel`.  Defaults to a tumbling irregular fragment.
    material:
        Key into :data:`~debris.materials.MATERIALS`, or a :class:`Material`.
    origin:
        Free-form provenance tag: ``"stage"``, ``"fragment"``, ``"detected"``.  Carried
        through so the dashboard can colour a footprint by where the object came from.
    """

    name: str = "fragment"
    mass: float = 10.0
    area: float = 0.1
    drag: DragModel = field(default_factory=DragModel)
    material: str | Material = "aluminium_oxidised"
    origin: str = "fragment"
    nose_radius: float | None = None

    # ---------------------------------------------------------------- derived geometry
    @property
    def characteristic_length(self) -> float:
        """NASA-SBM characteristic length [m] implied by the average cross-section."""
        return float(characteristic_length_from_area(self.area))

    @property
    def effective_nose_radius(self) -> float:
        """Radius [m] used by Sutton-Graves; the equivalent-sphere radius by default."""
        if self.nose_radius:
            return float(self.nose_radius)
        return max(math.sqrt(max(self.area, 1e-12) / math.pi), 1e-3)

    @property
    def area_to_mass(self) -> float:
        """A/M [m^2/kg] - the quantity the NASA breakup model actually samples."""
        return self.area / max(self.mass, 1e-12)

    @property
    def material_props(self) -> Material:
        return get_material(self.material)

    def cd(self, mach: float = 20.0, knudsen: float = 0.0) -> float:
        """Drag coefficient at a given flight condition (hypersonic continuum default)."""
        return float(self.drag.cd(mach, knudsen))

    def ballistic_coefficient(self, mach: float = 20.0, knudsen: float = 0.0) -> float:
        """
        B = m / (C_D * A) [kg/m^2] at a given flight condition.

        This single number explains most of a footprint's shape: it sets how deep into
        the atmosphere the object gets before it decelerates, and therefore how far
        downrange it lands.
        """
        return self.mass / max(self.cd(mach, knudsen) * self.area, 1e-12)

    def with_mass(self, mass: float) -> "DebrisObject":
        """Copy with a different mass (area held fixed)."""
        return replace(self, mass=float(mass))

    @classmethod
    def from_characteristic_length(
        cls, lc: float, area_to_mass: float, name: str = "fragment", **kwargs
    ) -> "DebrisObject":
        """Build from the (Lc, A/M) pair produced by the NASA Standard Breakup Model."""
        area = float(area_from_characteristic_length(lc))
        return cls(name=name, mass=area / max(area_to_mass, 1e-9), area=area, **kwargs)

    @classmethod
    def sphere(cls, diameter: float, material: str = "titanium", **kwargs) -> "DebrisObject":
        """A solid sphere of the given material - the classic 'pressurant tank' case."""
        props = get_material(material)
        radius = 0.5 * float(diameter)
        area = math.pi * radius**2
        mass = props.density * (4.0 / 3.0) * math.pi * radius**3
        return cls(
            mass=mass,
            area=area,
            drag=DragModel(shape="sphere", reference_length=float(diameter)),
            material=material,
            **kwargs,
        )


@dataclass(frozen=True)
class StateVector:
    """Instantaneous ECEF state. ``t`` is seconds from the reference epoch."""

    t: float
    r: np.ndarray  # ECEF position [m], shape (3,)
    v: np.ndarray  # ECEF velocity [m/s], shape (3,)

    def __post_init__(self):
        object.__setattr__(self, "r", np.asarray(self.r, dtype=float).reshape(3))
        object.__setattr__(self, "v", np.asarray(self.v, dtype=float).reshape(3))

    @classmethod
    def from_geodetic(
        cls,
        lat_deg: float,
        lon_deg: float,
        alt_m: float,
        speed: float,
        flight_path_deg: float,
        azimuth_deg: float,
        t: float = 0.0,
        earth_fixed: bool = True,
    ) -> "StateVector":
        """
        Build from the range-safety convention: speed, flight-path angle above the local
        horizon (negative = descending) and azimuth clockwise from north.
        """
        r = geodetic_to_ecef(lat_deg, lon_deg, alt_m)
        v = velocity_from_launch_frame(
            lat_deg, lon_deg, speed, flight_path_deg, azimuth_deg, earth_fixed
        )
        return cls(t=float(t), r=r, v=v)

    # ------------------------------------------------------------------- geodetic view
    @property
    def geodetic(self) -> tuple[float, float, float]:
        return ecef_to_geodetic_scalar(*self.r)

    @property
    def latitude(self) -> float:
        return self.geodetic[0]

    @property
    def longitude(self) -> float:
        return self.geodetic[1]

    @property
    def altitude(self) -> float:
        return self.geodetic[2]

    @property
    def speed(self) -> float:
        """Earth-relative speed [m/s]."""
        return float(np.linalg.norm(self.v))

    @property
    def flight_path_angle(self) -> float:
        """Angle of the Earth-relative velocity above the local horizon [deg]."""
        lat, lon, _ = self.geodetic
        enu = ecef_to_enu(self.v, lat, lon)
        horiz = math.hypot(enu[0], enu[1])
        return math.degrees(math.atan2(enu[2], horiz)) if horiz + abs(enu[2]) > 0 else 0.0

    @property
    def azimuth(self) -> float:
        """Heading of the Earth-relative velocity, deg clockwise from north."""
        lat, lon, _ = self.geodetic
        enu = ecef_to_enu(self.v, lat, lon)
        return math.degrees(math.atan2(enu[0], enu[1])) % 360.0

    def perturbed(self, dr=None, dv=None) -> "StateVector":
        """Copy with additive ECEF position/velocity offsets (Monte Carlo helper)."""
        r = self.r if dr is None else self.r + np.asarray(dr, dtype=float)
        v = self.v if dv is None else self.v + np.asarray(dv, dtype=float)
        return StateVector(self.t, r, v)


@dataclass(frozen=True)
class WindField:
    """
    Horizontal wind, specified by its *peak* (jet-stream) components.

    The vertical profile is a jet-stream Gaussian centred at 11 km on a weak background,
    decaying exponentially above 25 km.  Winds are irrelevant to the hypersonic part of a
    re-entry, but they dominate the long subsonic descent of a low-ballistic-coefficient
    fragment: an MLI blanket takes over an hour to fall and simply goes wherever the air
    goes, which is where most of the footprint spread for light debris comes from.

    Direction convention: ``zonal`` is positive eastward, ``meridional`` positive
    northward, both in m/s.

    Note on frames
    --------------
    The wind is *always* applied in the local ENU frame at the object's current position,
    never as a fixed ECEF vector captured at entry.  A light fragment can drift well over
    1000 km, by which point a frozen ECEF wind vector has acquired a large component
    along the new local vertical - a spurious updraught/downdraught that changes the fall
    time rather than merely the drift direction.
    """

    zonal: float = 0.0
    meridional: float = 0.0

    _PEAK_NORM = 1.3  # value of the raw profile at its 11 km peak

    def profile(self, alt_m: float) -> float:
        """
        Dimensionless altitude weighting, 1.0 at the jet-stream peak.

        Continuous and finite everywhere: any jump here would be a discontinuity in the
        equations of motion, which an error-controlled integrator responds to by
        collapsing the step size.
        """
        f = 0.30 + math.exp(-(((alt_m - 11_000.0) / 9_000.0) ** 2))
        if alt_m > 25_000.0:
            f *= math.exp(-(alt_m - 25_000.0) / 12_000.0)
        return f / self._PEAK_NORM

    def profile_array(self, alt_m):
        """Vectorised :meth:`profile`, for the ensemble propagator."""
        alt = np.asarray(alt_m, dtype=float)
        f = 0.30 + np.exp(-(((alt - 11_000.0) / 9_000.0) ** 2))
        f = np.where(alt > 25_000.0, f * np.exp(-(alt - 25_000.0) / 12_000.0), f)
        return f / self._PEAK_NORM

    @property
    def speed(self) -> float:
        return math.hypot(self.zonal, self.meridional)

    @property
    def components(self) -> tuple[float, float]:
        """``(zonal, meridional)`` peak components [m/s]."""
        return float(self.zonal), float(self.meridional)

    def ecef_at(self, lat_deg: float, lon_deg: float, alt_m: float) -> np.ndarray:
        """Wind velocity as an ECEF vector at a specific geodetic point [m/s]."""
        basis = enu_basis(lat_deg, lon_deg)
        f = self.profile(alt_m)
        return f * (self.zonal * basis[0] + self.meridional * basis[1])


# ======================================================================== trajectory


@dataclass
class Trajectory:
    """
    Result of a single propagation.

    ``outcome`` is one of:
      ``"impact"``   - reached ``alt_stop``; impact fields are populated
      ``"demised"``  - ablated away in flight; no impact point
      ``"timeout"``  - still airborne when ``max_time`` expired
      ``"escaped"``  - left the atmosphere upward past the model ceiling
    """

    obj: DebrisObject
    outcome: str
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))
    r: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    v: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    latitude: np.ndarray = field(default_factory=lambda: np.zeros(0))
    longitude: np.ndarray = field(default_factory=lambda: np.zeros(0))
    altitude: np.ndarray = field(default_factory=lambda: np.zeros(0))
    speed: np.ndarray = field(default_factory=lambda: np.zeros(0))
    mach: np.ndarray = field(default_factory=lambda: np.zeros(0))
    density: np.ndarray = field(default_factory=lambda: np.zeros(0))
    dynamic_pressure: np.ndarray = field(default_factory=lambda: np.zeros(0))
    heat_flux: np.ndarray = field(default_factory=lambda: np.zeros(0))
    deceleration_g: np.ndarray = field(default_factory=lambda: np.zeros(0))
    temperature: np.ndarray = field(default_factory=lambda: np.zeros(0))
    mass: np.ndarray = field(default_factory=lambda: np.zeros(0))

    # scalar summary, always populated (even when the trajectory was not stored)
    start_latitude: float = 0.0
    start_longitude: float = 0.0
    start_altitude: float = 0.0
    impact_latitude: float = float("nan")
    impact_longitude: float = float("nan")
    impact_time: float = float("nan")
    impact_speed: float = float("nan")
    impact_mass: float = float("nan")
    peak_dynamic_pressure: float = 0.0
    peak_heat_flux: float = 0.0
    peak_deceleration_g: float = 0.0
    peak_heating_altitude: float = float("nan")
    total_heat_load: float = 0.0
    mass_fraction_remaining: float = 1.0
    steps: int = 0

    # ------------------------------------------------------------------- convenience
    @property
    def impacted(self) -> bool:
        return self.outcome == "impact"

    @property
    def demised(self) -> bool:
        return self.outcome == "demised"

    @property
    def impact_kinetic_energy(self) -> float:
        """Impact kinetic energy [J]; NaN if the object never reached the ground."""
        if not self.impacted:
            return float("nan")
        return 0.5 * self.impact_mass * self.impact_speed**2

    @property
    def is_casualty_capable(self) -> bool:
        """True if the impact energy exceeds the 15 J range-safety threshold."""
        ke = self.impact_kinetic_energy
        return bool(np.isfinite(ke) and ke >= CASUALTY_KE_THRESHOLD)

    @property
    def downrange(self) -> float:
        """Great-circle distance from start point to impact point [m]."""
        if not self.impacted:
            return float("nan")
        return float(
            great_circle_distance(
                self.start_latitude,
                self.start_longitude,
                self.impact_latitude,
                self.impact_longitude,
            )
        )

    @property
    def flight_time(self) -> float:
        return self.impact_time - (self.t[0] if self.t.size else 0.0)

    def summary(self) -> dict:
        """Flat dict of the headline numbers, for tables and logging."""
        return {
            "name": self.obj.name,
            "origin": self.obj.origin,
            "outcome": self.outcome,
            "mass_kg": self.obj.mass,
            "area_m2": self.obj.area,
            "ballistic_coeff_kg_m2": self.obj.ballistic_coefficient(),
            "impact_lat": self.impact_latitude,
            "impact_lon": self.impact_longitude,
            "impact_speed_ms": self.impact_speed,
            "impact_mass_kg": self.impact_mass,
            "impact_ke_J": self.impact_kinetic_energy,
            "downrange_km": self.downrange / 1000.0,
            "fall_time_s": self.flight_time,
            "peak_q_kPa": self.peak_dynamic_pressure / 1000.0,
            "peak_heat_flux_kW_m2": self.peak_heat_flux / 1000.0,
            "peak_decel_g": self.peak_deceleration_g,
            "mass_remaining_frac": self.mass_fraction_remaining,
            "casualty_capable": self.is_casualty_capable,
        }


# ========================================================================= integrator

# Dormand-Prince 5(4) coefficients (FSAL: stage 7 of step n is stage 1 of step n+1).
_DP_A = (
    (),
    (1 / 5,),
    (3 / 40, 9 / 40),
    (44 / 45, -56 / 15, 32 / 9),
    (19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729),
    (9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656),
    (35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84),
)
_DP_C = (0.0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1.0, 1.0)
_DP_B5 = (35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0.0)
_DP_B4 = (
    5179 / 57600, 0.0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40,
)
_DP_E = tuple(b5 - b4 for b5, b4 in zip(_DP_B5, _DP_B4))  # error weights

_AMBIENT_T = 288.15  # radiation sink temperature [K]


def _local_wind_ecef(lat_deg, lon_deg, alt_m, zonal, meridional, wind_field):
    """
    Wind as an ECEF triple at the *current* geodetic point, pure-``math``.

    Rebuilding the ENU basis every evaluation rather than freezing it at entry is what
    keeps a horizontal wind horizontal over a 1000 km drift.
    """
    f = wind_field.profile(alt_m)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sl, cl = math.sin(lat), math.cos(lat)
    so, co = math.sin(lon), math.cos(lon)
    ze, zm = f * zonal, f * meridional
    # east = (-so, co, 0);  north = (-sl*co, -sl*so, cl)
    return (
        -ze * so - zm * sl * co,
        ze * co - zm * sl * so,
        zm * cl,
    )


def _local_wind_ecef_vec(lat_deg, lon_deg, alt_m, wuv, wind_field):
    """
    Vectorised :func:`_local_wind_ecef`: ``(wx, wy, wz)`` ECEF wind components for a whole
    ensemble, each in its own local ENU frame.  ``wuv`` is ``(N, 2)`` of
    ``(zonal, meridional)``.
    """
    f = wind_field.profile_array(alt_m)
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    sl, cl = np.sin(lat), np.cos(lat)
    so, co = np.sin(lon), np.cos(lon)
    ze = f * wuv[:, 0]
    zm = f * wuv[:, 1]
    return (-ze * so - zm * sl * co, ze * co - zm * sl * so, zm * cl)


def _diagnostics(y, obj, atmosphere, wind_uv, wind_field):
    """
    Flight condition at an accepted state.

    Returns ``(lat, lon, alt, rho, speed_rel, mach, q, q_dot, decel_g)``.  Called once
    per accepted step, so it doubles as the ground-crossing event function and the
    peak-load tracker.
    """
    x, yy, z, vx, vy, vz, temp, mass = y
    lat, lon, alt = ecef_to_geodetic_scalar(x, yy, z)
    rho, t_air, a_snd, lam = atmosphere.scalar(alt)

    wx = wy = wz = 0.0
    if wind_uv is not None:
        wx, wy, wz = _local_wind_ecef(lat, lon, alt, wind_uv[0], wind_uv[1], wind_field)
    vrx, vry, vrz = vx - wx, vy - wy, vz - wz
    speed = math.sqrt(vrx * vrx + vry * vry + vrz * vrz)

    mach = speed / a_snd if a_snd > 0.0 else 0.0
    q = 0.5 * rho * speed * speed
    area = obj.area * (mass / obj.mass) ** (2.0 / 3.0) if mass > 0.0 else 0.0
    cd = obj.drag.cd_scalar(mach, lam / max(obj.characteristic_length, 1e-4))
    decel = q * cd * area / mass / G0 if mass > 0.0 else 0.0
    q_dot = (
        SUTTON_GRAVES_K * math.sqrt(rho / obj.effective_nose_radius) * speed**3
        if rho > 0.0
        else 0.0
    )
    return lat, lon, alt, rho, speed, mach, q, q_dot, decel


def propagate(
    state: StateVector,
    obj: DebrisObject,
    atmosphere: Atmosphere = US76,
    wind: WindField | None = None,
    *,
    alt_stop: float = 0.0,
    max_time: float = 30_000.0,
    thermal: bool = True,
    store_trajectory: bool = True,
    heat_transfer_efficiency: float = 0.3,
    rtol: float = 1e-7,
    atol_pos: float = 1e-2,
    atol_vel: float = 1e-5,
    atol_temp: float = 1.0,
    dt_init: float = 1.0,
    dt_max: float = 60.0,
    dt_min: float = 1e-7,
    max_steps: int = 500_000,
    demise_mass_fraction: float = 1e-3,
    ceiling: float = 1.0e6,
) -> Trajectory:
    """
    Propagate one object from ``state`` down to ``alt_stop`` (default: sea level).

    Parameters worth knowing about
    ------------------------------
    thermal:
        Integrate temperature and mass loss.  Turn it off to get a pure ballistic
        trajectory (useful when comparing against a published drag-only case).
    store_trajectory:
        Keep the full time history.  Monte Carlo runs set this ``False`` and get only
        the scalar summary, which roughly halves the runtime and the memory.
    heat_transfer_efficiency:
        Fraction of the Sutton-Graves stagnation-point flux applied to the whole
        reference area.  0.2-0.4 is the usual engineering range for a tumbling body;
        it is the single largest knob on whether marginal objects demise.
    alt_stop:
        Set to the local terrain elevation to land debris on ground rather than on the
        ellipsoid.
    """
    lat0, lon0, alt0 = state.geodetic
    wind_field = wind if wind is not None else WindField()
    wind_uv = wind_field.components if wind_field.speed > 0.0 else None

    # ------------------------------------------------------------------ closed-over rhs
    m0 = float(obj.mass)
    area0 = float(obj.area)
    lc = max(obj.characteristic_length, 1e-4)
    nose_r = obj.effective_nose_radius
    cd_scalar = obj.drag.cd_scalar
    atm_scalar = atmosphere.scalar
    props = obj.material_props
    cp, t_melt = props.specific_heat, props.melt_temperature
    latent = max(props.latent_heat, 1.0)
    rad_coeff = STEFAN_BOLTZMANN * props.emissivity * 4.0
    melt_band = 5.0  # K over which melting ramps in, to keep the rhs near-continuous
    amb4_const = _AMBIENT_T**4
    omega2 = EARTH_OMEGA * EARTH_OMEGA

    def rhs(_t, y):
        x, yy, z, vx, vy, vz, temp, mass = y

        # --- gravity: spherical + J2 ------------------------------------------------
        r2 = x * x + yy * yy + z * z
        r = math.sqrt(r2)
        inv_r3 = 1.0 / (r2 * r)
        zr2 = z * z / r2
        k = 1.5 * EARTH_J2 * (WGS84_A / r) ** 2
        gx = -EARTH_MU * x * inv_r3 * (1.0 + k * (1.0 - 5.0 * zr2))
        gy = -EARTH_MU * yy * inv_r3 * (1.0 + k * (1.0 - 5.0 * zr2))
        gz = -EARTH_MU * z * inv_r3 * (1.0 + k * (3.0 - 5.0 * zr2))

        # --- rotating-frame terms: -2 w x v  and  -w x (w x r), with w = (0, 0, W) ---
        ax = gx + 2.0 * EARTH_OMEGA * vy + omega2 * x
        ay = gy - 2.0 * EARTH_OMEGA * vx + omega2 * yy
        az = gz

        # --- aerodynamics + heating ------------------------------------------------
        dtemp = 0.0
        dmass = 0.0
        lat_r, lon_r, alt = ecef_to_geodetic_scalar(x, yy, z)
        rho, _t_air, a_snd, lam = atm_scalar(alt)
        if rho > 0.0 and mass > 0.0:
            wx = wy = wz = 0.0
            if wind_uv is not None:
                wx, wy, wz = _local_wind_ecef(
                    lat_r, lon_r, alt, wind_uv[0], wind_uv[1], wind_field
                )
            vrx, vry, vrz = vx - wx, vy - wy, vz - wz
            speed = math.sqrt(vrx * vrx + vry * vry + vrz * vrz)
            if speed > 0.0:
                cd = cd_scalar(speed / a_snd if a_snd > 0.0 else 0.0, lam / lc)
                # Self-similar shrinkage as mass ablates away.
                area = area0 * (mass / m0) ** (2.0 / 3.0)
                fdrag = -0.5 * rho * speed * cd * area / mass
                ax += fdrag * vrx
                ay += fdrag * vry
                az += fdrag * vrz

                if thermal:
                    q_dot = SUTTON_GRAVES_K * math.sqrt(rho / nose_r) * speed**3
                    q_in = heat_transfer_efficiency * q_dot * area
                    q_rad = rad_coeff * area * (temp**4 - amb4_const)
                    net = q_in - q_rad
                    if temp < t_melt - melt_band:
                        dtemp = net / (mass * cp)
                    elif temp > t_melt:
                        dmass = -max(net, 0.0) / latent
                    else:
                        w_melt = (temp - (t_melt - melt_band)) / melt_band
                        dtemp = (1.0 - w_melt) * net / (mass * cp)
                        dmass = -w_melt * max(net, 0.0) / latent

        return [vx, vy, vz, ax, ay, az, dtemp, dmass]

    # ------------------------------------------------------------------------ stepping
    y = [
        float(state.r[0]), float(state.r[1]), float(state.r[2]),
        float(state.v[0]), float(state.v[1]), float(state.v[2]),
        _AMBIENT_T, m0,
    ]
    t = float(state.t)
    t_end = t + float(max_time)
    atol = [atol_pos] * 3 + [atol_vel] * 3 + [atol_temp, m0 * 1e-6]

    if alt0 <= alt_stop:
        # Already at or below the stopping surface: nothing to integrate.
        traj = Trajectory(obj=obj, outcome="impact", t=np.array([t]))
        traj.start_latitude, traj.start_longitude, traj.start_altitude = lat0, lon0, alt0
        traj.impact_latitude, traj.impact_longitude = lat0, lon0
        traj.impact_time, traj.impact_mass = t, m0
        traj.impact_speed = state.speed
        return traj

    def dp_step(t0, y0, h, k1):
        """One DP5(4) step. Returns (y5, err_norm, k_last)."""
        ks = [k1]
        for i in range(1, 7):
            a_row = _DP_A[i]
            ystage = [
                y0[j] + h * sum(a_row[s] * ks[s][j] for s in range(len(a_row)))
                for j in range(8)
            ]
            ks.append(rhs(t0 + _DP_C[i] * h, ystage))
        y5 = [y0[j] + h * sum(_DP_B5[s] * ks[s][j] for s in range(7)) for j in range(8)]
        err = 0.0
        for j in range(8):
            e = abs(h * sum(_DP_E[s] * ks[s][j] for s in range(7)))
            scale = atol[j] + rtol * max(abs(y0[j]), abs(y5[j]))
            err = max(err, e / scale)
        return y5, err, ks[6]

    ts: list[float] = [t]
    ys: list[list[float]] = [list(y)]

    peak_q = peak_qdot = peak_decel = 0.0
    peak_qdot_alt = float("nan")
    heat_load = 0.0

    k1 = rhs(t, y)
    _, _, alt_prev, _, _, _, q_prev, qdot_prev, decel_prev = _diagnostics(
        y, obj, atmosphere, wind_uv, wind_field
    )
    peak_q, peak_qdot, peak_decel = q_prev, qdot_prev, decel_prev
    peak_qdot_alt = alt_prev

    h = min(float(dt_init), float(dt_max))
    outcome = "timeout"
    steps = 0
    iters = 0
    # Rejections do not advance ``steps``, so the loop is bounded on total iterations to
    # make a pathological shrink-forever case impossible rather than merely unlikely.
    iter_budget = 20 * max_steps

    while steps < max_steps and iters < iter_budget:
        iters += 1
        if t >= t_end:
            outcome = "timeout"
            break
        h = min(h, t_end - t)
        y_new, err, k_last = dp_step(t, y, h, k1)

        if err > 1.0 and h > dt_min:
            # Reject and shrink. Exponent 1/5 is the DP5(4) order-based control law.
            h = max(h * max(0.2, 0.9 * err ** -0.2), dt_min)
            continue

        t_prev, y_prev, alt_before = t, y, alt_prev
        t = t + h
        y = y_new
        k1 = k_last  # FSAL
        steps += 1

        lat, lon, alt, rho, speed, mach, q, qdot, decel = _diagnostics(
            y, obj, atmosphere, wind_uv, wind_field
        )
        heat_load += 0.5 * (qdot + qdot_prev) * h
        if q > peak_q:
            peak_q = q
        if qdot > peak_qdot:
            peak_qdot, peak_qdot_alt = qdot, alt
        if decel > peak_decel:
            peak_decel = decel
        qdot_prev = qdot

        if store_trajectory:
            ts.append(t)
            ys.append(list(y))

        # ---------------------------------------------------------------- termination
        if y[7] <= demise_mass_fraction * m0:
            outcome = "demised"
            break
        if alt <= alt_stop:
            # Ground crossing: bisect within the accepted step for the exact impact state.
            t, y = _refine_event(t_prev, y_prev, h, alt_stop, dp_step, rhs(t_prev, y_prev))
            if store_trajectory:
                ts[-1], ys[-1] = t, list(y)
            outcome = "impact"
            break
        if alt > ceiling and alt > alt_before:
            outcome = "escaped"
            break

        alt_prev = alt
        # Grow the step, capped so a single accepted step cannot overshoot the physics.
        h = min(dt_max, h * min(5.0, 0.9 * max(err, 1e-10) ** -0.2))

    return _finalise(
        obj=obj,
        outcome=outcome,
        ts=ts,
        ys=ys,
        atmosphere=atmosphere,
        wind_uv=wind_uv,
        wind_field=wind_field,
        store_trajectory=store_trajectory,
        start=(lat0, lon0, alt0),
        final_t=t,
        final_y=y,
        peaks=(peak_q, peak_qdot, peak_decel, peak_qdot_alt, heat_load),
        m0=m0,
        steps=steps,
    )


def _refine_event(t0, y0, h_full, alt_stop, dp_step, k1_start, iterations=60):
    """
    Bisect a single accepted step to land exactly on ``alt == alt_stop``.

    Each probe is a full DP5(4) step from the step start, so the refined state is
    fifth-order accurate rather than linearly interpolated - which matters because the
    last kilometre of a steep re-entry covers hundreds of metres per second.
    """
    lo, hi = 0.0, h_full
    y_best = None
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        y_mid, _, _ = dp_step(t0, y0, mid, k1_start)
        alt_mid = ecef_to_geodetic_scalar(y_mid[0], y_mid[1], y_mid[2])[2]
        if alt_mid > alt_stop:
            lo = mid
        else:
            hi, y_best = mid, y_mid
        if hi - lo < 1e-9:
            break
    if y_best is None:
        y_best, _, _ = dp_step(t0, y0, hi, k1_start)
    return t0 + hi, y_best


def _finalise(
    *, obj, outcome, ts, ys, atmosphere, wind_uv, wind_field,
    store_trajectory, start, final_t, final_y, peaks, m0, steps,
):
    """Assemble a :class:`Trajectory`, computing the derived arrays vectorised."""
    peak_q, peak_qdot, peak_decel, peak_qdot_alt, heat_load = peaks
    traj = Trajectory(obj=obj, outcome=outcome)
    traj.start_latitude, traj.start_longitude, traj.start_altitude = start
    traj.peak_dynamic_pressure = peak_q
    traj.peak_heat_flux = peak_qdot
    traj.peak_deceleration_g = peak_decel
    traj.peak_heating_altitude = peak_qdot_alt
    traj.total_heat_load = heat_load
    traj.mass_fraction_remaining = final_y[7] / m0 if m0 > 0 else 0.0
    traj.steps = steps

    if outcome == "impact":
        lat, lon, _ = ecef_to_geodetic_scalar(final_y[0], final_y[1], final_y[2])
        traj.impact_latitude = lat
        traj.impact_longitude = lon
        traj.impact_time = final_t
        traj.impact_mass = final_y[7]
        # Impact speed is Earth-relative, i.e. what a ground observer would measure.
        traj.impact_speed = math.sqrt(final_y[3] ** 2 + final_y[4] ** 2 + final_y[5] ** 2)

    if not store_trajectory or len(ts) < 2:
        traj.t = np.asarray(ts, dtype=float)
        return traj

    arr = np.asarray(ys, dtype=float)
    traj.t = np.asarray(ts, dtype=float)
    traj.r = arr[:, 0:3]
    traj.v = arr[:, 3:6]
    traj.temperature = arr[:, 6]
    traj.mass = arr[:, 7]

    lat, lon, alt = ecef_to_geodetic(traj.r)
    traj.latitude, traj.longitude, traj.altitude = lat, lon, alt

    rho, _t_air, _p, a_snd = atmosphere.state(alt)
    v_rel = traj.v.copy()
    if wind_uv is not None:
        # Local-frame wind at every stored point, same convention as the integrator.
        w = np.array(
            [wind_field.ecef_at(la, lo, a) for la, lo, a in zip(lat, lon, alt)]
        )
        v_rel = v_rel - w
    speed = np.linalg.norm(v_rel, axis=1)

    with np.errstate(divide="ignore", invalid="ignore"):
        mach = np.where(a_snd > 0, speed / a_snd, 0.0)
        lam = mean_free_path(np.where(rho > 0, rho, 1e-30))
        lam = np.where(rho > 0, lam, np.inf)
    cd = obj.drag.cd(mach, lam / max(obj.characteristic_length, 1e-4))
    area = obj.area * np.power(np.maximum(traj.mass, 0.0) / m0, 2.0 / 3.0)
    q = 0.5 * rho * speed**2

    traj.speed = speed
    traj.mach = np.asarray(mach, dtype=float)
    traj.density = rho
    traj.dynamic_pressure = q
    traj.heat_flux = np.where(
        rho > 0, SUTTON_GRAVES_K * np.sqrt(rho / obj.effective_nose_radius) * speed**3, 0.0
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        traj.deceleration_g = np.where(
            traj.mass > 0, q * cd * area / np.maximum(traj.mass, 1e-12) / G0, 0.0
        )
    return traj


def propagate_many(
    objects,
    state: StateVector | list[StateVector],
    atmosphere: Atmosphere = US76,
    wind: WindField | None = None,
    **kwargs,
) -> list[Trajectory]:
    """
    Propagate a list of objects, optionally each from its own state.

    Used for a deterministic debris field: one trajectory per fragment, all released at
    the same breakup point but with the breakup's individual delta-v already folded into
    each fragment's state.
    """
    objects = list(objects)
    states = state if isinstance(state, (list, tuple)) else [state] * len(objects)
    if len(states) != len(objects):
        raise ValueError(
            f"got {len(objects)} objects but {len(states)} states; they must match"
        )
    return [
        propagate(s, o, atmosphere, wind, **kwargs) for o, s in zip(objects, states)
    ]


# ================================================================= ensemble propagator

OUTCOME_IMPACT, OUTCOME_DEMISED, OUTCOME_TIMEOUT, OUTCOME_ESCAPED = 0, 1, 2, 3
OUTCOME_NAMES = ("impact", "demised", "timeout", "escaped")


@dataclass
class EnsembleResult:
    """
    Outcome of propagating N bodies simultaneously.

    Every field is a length-N array aligned with the input ordering.  This is the object
    a Monte Carlo dispersion or a whole breakup cloud is built from.
    """

    outcome: np.ndarray            # int codes, see OUTCOME_* above
    impact_latitude: np.ndarray
    impact_longitude: np.ndarray
    impact_time: np.ndarray
    impact_speed: np.ndarray
    impact_mass: np.ndarray
    start_latitude: np.ndarray
    start_longitude: np.ndarray
    start_altitude: np.ndarray
    mass_fraction_remaining: np.ndarray
    peak_dynamic_pressure: np.ndarray
    peak_heat_flux: np.ndarray
    peak_deceleration_g: np.ndarray
    initial_mass: np.ndarray
    ballistic_coefficient: np.ndarray
    steps: int = 0

    @property
    def n(self) -> int:
        return int(self.outcome.size)

    @property
    def impacted(self) -> np.ndarray:
        return self.outcome == OUTCOME_IMPACT

    @property
    def demised(self) -> np.ndarray:
        return self.outcome == OUTCOME_DEMISED

    @property
    def impact_kinetic_energy(self) -> np.ndarray:
        return 0.5 * self.impact_mass * self.impact_speed**2

    @property
    def casualty_capable(self) -> np.ndarray:
        ke = self.impact_kinetic_energy
        return self.impacted & np.isfinite(ke) & (ke >= CASUALTY_KE_THRESHOLD)

    def outcome_names(self) -> list[str]:
        return [OUTCOME_NAMES[int(c)] for c in self.outcome]

    def counts(self) -> dict[str, int]:
        return {
            name: int(np.count_nonzero(self.outcome == code))
            for code, name in enumerate(OUTCOME_NAMES)
        }


def propagate_ensemble(
    r0: np.ndarray,
    v0: np.ndarray,
    objects,
    *,
    t0=0.0,
    atmosphere: Atmosphere = US76,
    density_scale=None,
    wind_components=None,
    wind: WindField | None = None,
    alt_stop=0.0,
    max_time: float = 30_000.0,
    thermal: bool = True,
    heat_transfer_efficiency: float = 0.3,
    rtol: float = 1e-6,
    atol_pos: float = 1e-1,
    atol_vel: float = 1e-4,
    atol_temp: float = 1.0,
    dt_init: float = 1.0,
    dt_max: float = 60.0,
    dt_min: float = 1e-6,
    max_steps: int = 100_000,
    demise_mass_fraction: float = 1e-3,
    ceiling: float = 1.0e6,
    refine_iterations: int = 34,
) -> EnsembleResult:
    """
    Propagate N bodies at once with shared adaptive stepping.

    Same physics as :func:`propagate` - the two are cross-validated against each other
    in the package self-check - but written against numpy arrays instead of Python
    floats.  For N in the hundreds-to-thousands this is two orders of magnitude faster
    than looping :func:`propagate`, which is what makes a live Monte Carlo footprint
    practical in a dashboard.

    Design notes
    ------------
    * **Shared step size.**  One ``h`` for the whole active set, driven by the worst
      per-sample error estimate.  Conservative (easy samples take needlessly small
      steps) but it keeps the error control honest and the bookkeeping simple.
    * **Compaction.**  Finished samples are removed from the working arrays, so a
      long-lived low-B fragment does not drag 2000 dead samples along behind it.
    * **Deferred event refinement.**  Ground crossings are only *bracketed* during the
      main loop; all of them are then bisected in one batched pass at the end.  Doing it
      inline would mean dozens of tiny numpy calls whose fixed overhead dominates.

    Parameters
    ----------
    r0, v0:
        ``(N, 3)`` ECEF position [m] and velocity [m/s].
    objects:
        A single :class:`DebrisObject` broadcast to all N, or a length-N sequence.
    density_scale:
        Optional ``(N,)`` per-sample atmospheric density multiplier, on top of
        ``atmosphere.density_scale``.  This is where density uncertainty enters.
    wind_components:
        Optional ``(N, 2)`` array of per-sample ``(zonal, meridional)`` peak wind
        components [m/s].  Takes precedence over ``wind``; this is how wind uncertainty
        enters a Monte Carlo dispersion.
    """
    r0 = np.atleast_2d(np.asarray(r0, dtype=float))
    v0 = np.atleast_2d(np.asarray(v0, dtype=float))
    if r0.shape != v0.shape or r0.shape[1] != 3:
        raise ValueError(f"r0/v0 must both be (N, 3); got {r0.shape} and {v0.shape}")
    n = r0.shape[0]

    if isinstance(objects, DebrisObject):
        objects = [objects] * n
    objects = list(objects)
    if len(objects) != n:
        raise ValueError(f"got {n} states but {len(objects)} objects; they must match")

    # ------------------------------------------------------------------ pack properties
    from .drag import cd_ensemble, pack_drag_models

    m0 = np.array([o.mass for o in objects], dtype=float)
    area0 = np.array([o.area for o in objects], dtype=float)
    lc = np.array([max(o.characteristic_length, 1e-4) for o in objects], dtype=float)
    nose_r = np.array([o.effective_nose_radius for o in objects], dtype=float)
    cont_scale, cd_fm, cd_c, is_c, _ref = pack_drag_models([o.drag for o in objects])

    props = [o.material_props for o in objects]
    cp = np.array([p.specific_heat for p in props], dtype=float)
    t_melt = np.array([p.melt_temperature for p in props], dtype=float)
    latent = np.array([max(p.latent_heat, 1.0) for p in props], dtype=float)
    rad_coeff = np.array([STEFAN_BOLTZMANN * p.emissivity * 4.0 for p in props])

    ds = (
        np.full(n, 1.0) if density_scale is None
        else np.broadcast_to(np.asarray(density_scale, dtype=float), (n,)).astype(float)
    )
    # Density uncertainty enters purely as a multiplier, so a single table built for the
    # *unscaled* standard atmosphere serves every sample.
    ds = ds * atmosphere.density_scale
    table = US76_TABLE

    lat_start, lon_start, alt_start = ecef_to_geodetic(r0)
    if wind_components is not None:
        wuv = np.broadcast_to(np.asarray(wind_components, dtype=float), (n, 2)).astype(float)
        if not np.any(wuv):
            wuv = None
    elif wind is not None and wind.speed > 0.0:
        wuv = np.tile(np.array(wind.components, dtype=float), (n, 1))
    else:
        wuv = None
    wind_field = wind if wind is not None else WindField()

    alt_stop_arr = np.broadcast_to(np.asarray(alt_stop, dtype=float), (n,)).astype(float)
    t_start = np.broadcast_to(np.asarray(t0, dtype=float), (n,)).astype(float)
    amb4 = _AMBIENT_T**4
    omega2 = EARTH_OMEGA * EARTH_OMEGA
    melt_band = 5.0

    # --------------------------------------------------------------------- output slots
    outcome = np.full(n, OUTCOME_TIMEOUT, dtype=np.int8)
    imp_lat = np.full(n, np.nan)
    imp_lon = np.full(n, np.nan)
    imp_t = np.full(n, np.nan)
    imp_v = np.full(n, np.nan)
    imp_m = np.full(n, np.nan)
    mass_frac = np.ones(n)
    pk_q = np.zeros(n)
    pk_qdot = np.zeros(n)
    pk_g = np.zeros(n)
    # Bracketing state for the deferred ground-crossing refinement.
    cross_y = np.zeros((n, 8))
    cross_t = np.zeros(n)
    cross_h = np.zeros(n)
    crossed = np.zeros(n, dtype=bool)

    # ------------------------------------------------------------------- working arrays
    idx = np.arange(n)
    Y = np.empty((n, 8))
    Y[:, 0:3] = r0
    Y[:, 3:6] = v0
    Y[:, 6] = _AMBIENT_T
    Y[:, 7] = m0
    t_cur = t_start.copy()
    t_end = t_start + float(max_time)

    def rhs(Y_):
        """(K, 8) state -> (K, 8) derivative."""
        x, y_, z = Y_[:, 0], Y_[:, 1], Y_[:, 2]
        vx, vy, vz = Y_[:, 3], Y_[:, 4], Y_[:, 5]
        temp, mass = Y_[:, 6], Y_[:, 7]

        r2 = x * x + y_ * y_ + z * z
        r = np.sqrt(r2)
        inv_r3 = 1.0 / (r2 * r)
        zr2 = z * z / r2
        k = 1.5 * EARTH_J2 * (WGS84_A / r) ** 2
        common = 1.0 + k * (1.0 - 5.0 * zr2)
        ax = -EARTH_MU * x * inv_r3 * common + 2.0 * EARTH_OMEGA * vy + omega2 * x
        ay = -EARTH_MU * y_ * inv_r3 * common - 2.0 * EARTH_OMEGA * vx + omega2 * y_
        az = -EARTH_MU * z * inv_r3 * (1.0 + k * (3.0 - 5.0 * zr2))

        lat_d, lon_d, alt = ecef_to_geodetic(Y_[:, 0:3])
        rho, a_snd, lam = table.lookup(alt)
        rho = rho * ds_w
        lam = lam / ds_w

        mass_pos = np.maximum(mass, 1e-12)
        vrx, vry, vrz = vx, vy, vz
        if wuv_w is not None:
            wx, wy, wz = _local_wind_ecef_vec(lat_d, lon_d, alt, wuv_w, wind_field)
            vrx = vx - wx
            vry = vy - wy
            vrz = vz - wz
        speed = np.sqrt(vrx * vrx + vry * vry + vrz * vrz)

        flying = (rho > 0.0) & (mass > 0.0) & (speed > 0.0)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            mach = speed / a_snd
            cd = cd_ensemble(mach, lam / lc_w, cont_scale_w, cd_fm_w, cd_c_w, is_c_w)
            area = area0_w * np.power(np.maximum(mass, 0.0) / m0_w, 2.0 / 3.0)
            fd = np.where(flying, -0.5 * rho * speed * cd * area / mass_pos, 0.0)
        ax = ax + fd * vrx
        ay = ay + fd * vry
        az = az + fd * vrz

        dtemp = np.zeros_like(temp)
        dmass = np.zeros_like(mass)
        if thermal:
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                q_dot = np.where(
                    flying,
                    SUTTON_GRAVES_K * np.sqrt(np.maximum(rho, 0.0) / nose_r_w) * speed**3,
                    0.0,
                )
                net = heat_transfer_efficiency * q_dot * area - rad_coeff_w * area * (
                    temp**4 - amb4
                )
                net = np.where(flying, net, 0.0)
                w_melt = np.clip((temp - (t_melt_w - melt_band)) / melt_band, 0.0, 1.0)
                dtemp = (1.0 - w_melt) * net / (mass_pos * cp_w)
                dmass = -w_melt * np.maximum(net, 0.0) / latent_w

        out = np.empty_like(Y_)
        out[:, 0], out[:, 1], out[:, 2] = vx, vy, vz
        out[:, 3], out[:, 4], out[:, 5] = ax, ay, az
        out[:, 6], out[:, 7] = dtemp, dmass
        return out

    def dp_step(Y_, h_, k1_):
        """One DP5(4) step with a per-sample step size ``h_`` of shape (K,)."""
        hcol = h_[:, None]
        ks = [k1_]
        for i in range(1, 7):
            a_row = _DP_A[i]
            acc = a_row[0] * ks[0]
            for s in range(1, len(a_row)):
                if a_row[s]:
                    acc = acc + a_row[s] * ks[s]
            ks.append(rhs(Y_ + hcol * acc))
        acc5 = _DP_B5[0] * ks[0]
        acc_e = _DP_E[0] * ks[0]
        for s in range(1, 7):
            if _DP_B5[s]:
                acc5 = acc5 + _DP_B5[s] * ks[s]
            if _DP_E[s]:
                acc_e = acc_e + _DP_E[s] * ks[s]
        Y5 = Y_ + hcol * acc5
        err_abs = np.abs(hcol * acc_e)
        scale = atol_w + rtol * np.maximum(np.abs(Y_), np.abs(Y5))
        return Y5, np.max(err_abs / scale, axis=1), ks[6]

    def slice_props(mask_or_idx):
        """Refresh the closed-over per-sample property views after compaction."""
        nonlocal ds_w, wuv_w, lc_w, cont_scale_w, cd_fm_w, cd_c_w, is_c_w
        nonlocal area0_w, m0_w, nose_r_w, rad_coeff_w, t_melt_w, cp_w, latent_w, atol_w
        ds_w = ds[mask_or_idx]
        wuv_w = None if wuv is None else wuv[mask_or_idx]
        lc_w = lc[mask_or_idx]
        cont_scale_w = cont_scale[mask_or_idx]
        cd_fm_w = cd_fm[mask_or_idx]
        cd_c_w = cd_c[mask_or_idx]
        is_c_w = is_c[mask_or_idx]
        area0_w = area0[mask_or_idx]
        m0_w = m0[mask_or_idx]
        nose_r_w = nose_r[mask_or_idx]
        rad_coeff_w = rad_coeff[mask_or_idx]
        t_melt_w = t_melt[mask_or_idx]
        cp_w = cp[mask_or_idx]
        latent_w = latent[mask_or_idx]
        atol_w = np.stack(
            [np.full(len(m0_w), atol_pos)] * 3
            + [np.full(len(m0_w), atol_vel)] * 3
            + [np.full(len(m0_w), atol_temp), m0_w * 1e-6],
            axis=1,
        )

    ds_w = wuv_w = lc_w = cont_scale_w = cd_fm_w = cd_c_w = is_c_w = None
    area0_w = m0_w = nose_r_w = rad_coeff_w = t_melt_w = cp_w = latent_w = atol_w = None
    slice_props(idx)

    def diagnostics(Y_):
        """(alt, q, q_dot, decel_g) for the active set."""
        lat_d, lon_d, alt = ecef_to_geodetic(Y_[:, 0:3])
        rho, a_snd, lam = table.lookup(alt)
        rho = rho * ds_w
        lam = lam / ds_w
        V = Y_[:, 3:6]
        if wuv_w is not None:
            V = V - np.stack(_local_wind_ecef_vec(lat_d, lon_d, alt, wuv_w, wind_field), axis=1)
        speed = np.linalg.norm(V, axis=1)
        q = 0.5 * rho * speed**2
        mass = np.maximum(Y_[:, 7], 1e-12)
        area = area0_w * np.power(np.maximum(Y_[:, 7], 0.0) / m0_w, 2.0 / 3.0)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            cd = cd_ensemble(
                speed / a_snd, lam / lc_w, cont_scale_w, cd_fm_w, cd_c_w, is_c_w
            )
            qdot = np.where(
                rho > 0, SUTTON_GRAVES_K * np.sqrt(np.maximum(rho, 0) / nose_r_w) * speed**3, 0.0
            )
        return alt, q, qdot, q * cd * area / mass / G0

    # ---------------------------------------------------------------------- main loop
    def track_peaks(active, q_, qdot_, dg_):
        # ``active`` holds unique indices, so plain fancy indexing is correct here and
        # markedly faster than np.maximum.at.
        pk_q[active] = np.maximum(pk_q[active], q_)
        pk_qdot[active] = np.maximum(pk_qdot[active], qdot_)
        pk_g[active] = np.maximum(pk_g[active], dg_)

    k1 = rhs(Y)
    alt_prev, q, qdot, dg = diagnostics(Y)
    track_peaks(idx, q, qdot, dg)

    h = np.full(len(idx), min(float(dt_init), float(dt_max)))
    steps = 0
    iter_budget = 20 * max_steps

    # Per-sample step size with per-sample accept/reject.  This is only legitimate
    # because the right-hand side has no explicit time dependence, so samples sitting at
    # different times in the same array are perfectly independent.  It matters a lot for
    # a breakup cloud: an MLI blanket falls for an hour while a titanium sphere is down
    # in nine minutes, and a shared step size would force the sphere's tolerance onto the
    # blanket's entire flight.
    while steps < iter_budget and len(idx):
        steps += 1
        # Clamp so no sample steps past its own horizon.
        h_used = np.minimum(h, np.maximum(t_end[idx] - t_cur[idx], dt_min))
        Y_new, err, k_last = dp_step(Y, h_used, k1)

        # Force acceptance once a sample is already at the floor, so a stiff sample can
        # never stall the whole run.
        ok = (err <= 1.0) | (h_used <= dt_min)
        okc = ok[:, None]

        Y_prev = Y
        t_prev_arr = t_cur[idx].copy()
        alt_before = alt_prev
        Y = np.where(okc, Y_new, Y)
        k1 = np.where(okc, k_last, k1)
        t_cur[idx] = np.where(ok, t_prev_arr + h_used, t_prev_arr)

        alt, q, qdot, dg = diagnostics(Y)
        track_peaks(idx, q, qdot, dg)

        # Rejected samples have not moved, so none of these predicates can fire for them.
        hit = alt <= alt_stop_arr[idx]
        gone = Y[:, 7] <= demise_mass_fraction * m0_w
        out_up = (alt > ceiling) & (alt > alt_before)
        timed = t_cur[idx] >= t_end[idx]
        done = hit | gone | out_up | timed

        if done.any():
            gidx = idx[done]
            # Precedence: demise beats impact (it happened earlier within the step).
            g_gone = gone[done]
            g_hit = hit[done] & ~g_gone
            g_up = out_up[done] & ~g_gone & ~g_hit
            outcome[gidx[g_gone]] = OUTCOME_DEMISED
            outcome[gidx[g_up]] = OUTCOME_ESCAPED
            outcome[gidx[timed[done] & ~g_gone & ~g_hit & ~g_up]] = OUTCOME_TIMEOUT
            outcome[gidx[g_hit]] = OUTCOME_IMPACT
            mass_frac[gidx] = Y[done, 7] / m0_w[done]
            # Bracket the crossing; every bracket is refined together at the end.
            crossed[gidx[g_hit]] = True
            cross_y[gidx[g_hit]] = Y_prev[done][g_hit]
            cross_t[gidx[g_hit]] = t_prev_arr[done][g_hit]
            cross_h[gidx[g_hit]] = h_used[done][g_hit]

        # Per-sample step-size update (classical order-based control law).
        with np.errstate(divide="ignore", over="ignore"):
            fac = np.clip(0.9 * np.maximum(err, 1e-10) ** -0.2, 0.2, 5.0)
        h = np.minimum(dt_max, h_used * fac)

        if done.any():
            keep = ~done
            idx = idx[keep]
            Y = Y[keep]
            k1 = k1[keep]
            h = h[keep]
            alt = alt[keep]
            slice_props(idx)
            if not len(idx):
                break

        alt_prev = alt

    # Samples still airborne when the step budget ran out keep their current mass.
    if len(idx):
        mass_frac[idx] = Y[:, 7] / m0[idx]

    # ------------------------------------------------------- batched event refinement
    if crossed.any():
        sel = np.flatnonzero(crossed)
        slice_props(sel)
        Yc = cross_y[sel]
        hc = cross_h[sel]
        k1c = rhs(Yc)
        lo = np.zeros(len(sel))
        hi = hc.copy()
        stop = alt_stop_arr[sel]
        for _ in range(int(refine_iterations)):
            mid = 0.5 * (lo + hi)
            Ym, _e, _k = dp_step(Yc, mid, k1c)
            above = ecef_to_geodetic(Ym[:, 0:3])[2] > stop
            lo = np.where(above, mid, lo)
            hi = np.where(above, hi, mid)
        # ``hi`` always brackets from below the surface, so one final step at ``hi`` is
        # the impact state - no need to carry a running "best" through the bisection.
        best, _e, _k = dp_step(Yc, hi, k1c)
        lat_i, lon_i, _a = ecef_to_geodetic(best[:, 0:3])
        imp_lat[sel] = lat_i
        imp_lon[sel] = lon_i
        imp_t[sel] = cross_t[sel] + hi
        imp_v[sel] = np.linalg.norm(best[:, 3:6], axis=1)
        imp_m[sel] = best[:, 7]
        mass_frac[sel] = best[:, 7] / m0[sel]

    bc = np.array([o.ballistic_coefficient() for o in objects], dtype=float)
    return EnsembleResult(
        outcome=outcome,
        impact_latitude=imp_lat,
        impact_longitude=imp_lon,
        impact_time=imp_t,
        impact_speed=imp_v,
        impact_mass=imp_m,
        start_latitude=lat_start,
        start_longitude=lon_start,
        start_altitude=alt_start,
        mass_fraction_remaining=mass_frac,
        peak_dynamic_pressure=pk_q,
        peak_heat_flux=pk_qdot,
        peak_deceleration_g=pk_g,
        initial_mass=m0,
        ballistic_coefficient=bc,
        steps=steps,
    )

