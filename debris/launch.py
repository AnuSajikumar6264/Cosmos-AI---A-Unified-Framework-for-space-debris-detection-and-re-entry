"""
Launch-vehicle staging: where the hardware a rocket sheds on the way up comes down.

Most falling launch debris is not a failure at all - it is scheduled.  Every orbital
launch drops strap-on boosters, a first stage, a payload fairing and usually an
interstage, each on its own suborbital arc into a pre-cleared drop zone.  This module
produces the separation states those objects start from; :mod:`debris.propagator` and
:mod:`debris.monte_carlo` then say where they land and with how much spread.

Ascent model
------------
The ascent here is **kinematic, not dynamic**.  Rather than integrating thrust, mass flow
and a pitch program, it monotonically interpolates altitude, speed and flight-path angle
through the vehicle's published separation conditions, and carries the ground track along
a constant-azimuth great circle.  That is a deliberate choice:

* the separation states are the only ascent output that matters downstream, and those are
  pinned to published values rather than inferred;
* a real trajectory simulation would need vendor propulsion data that is not public;
* it cannot silently drift away from reality, because it is constrained to pass through
  every quoted separation point.

What it does *not* model: dog-leg azimuth changes, throttle-down through max-Q, or
in-plane yaw steering.  For drop-zone prediction those shift the answer by far less than
the ballistic-coefficient and atmospheric-density uncertainty already do.

All vehicle numbers below are **representative public-domain estimates assembled for
demonstration**, not vendor data.  Dry masses and tumbling cross-sections in particular
are order-of-magnitude figures.  Every one is a plain field you can override.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .drag import DragModel
from .geodesy import destination_point
from .propagator import DebrisObject, StateVector

# ============================================================================== sites


@dataclass(frozen=True)
class LaunchSite:
    """A launch complex, with the azimuth band its range safety actually permits."""

    name: str
    latitude: float
    longitude: float
    elevation: float = 0.0
    azimuth_range: tuple[float, float] = (0.0, 360.0)
    default_azimuth: float = 90.0
    country: str = ""


LAUNCH_SITES: dict[str, LaunchSite] = {
    "sdsc_shar": LaunchSite(
        "Satish Dhawan Space Centre (SDSC SHAR)", 13.7199, 80.2304, 10.0,
        (100.0, 200.0), 140.0, "India",
    ),
    "cape_canaveral": LaunchSite(
        "Cape Canaveral SFS / KSC", 28.5623, -80.5774, 5.0,
        (35.0, 120.0), 90.0, "USA",
    ),
    "vandenberg": LaunchSite(
        "Vandenberg SFB", 34.7420, -120.5724, 100.0,
        (150.0, 220.0), 180.0, "USA",
    ),
    "kourou": LaunchSite(
        "Guiana Space Centre (Kourou)", 5.2360, -52.7750, 10.0,
        (350.0, 110.0), 90.0, "France/ESA",
    ),
    "baikonur": LaunchSite(
        "Baikonur Cosmodrome", 45.9650, 63.3050, 90.0,
        (35.0, 90.0), 65.0, "Kazakhstan",
    ),
    "wenchang": LaunchSite(
        "Wenchang Space Launch Site", 19.6144, 110.9510, 10.0,
        (90.0, 175.0), 110.0, "China",
    ),
    "tanegashima": LaunchSite(
        "Tanegashima Space Centre", 30.4000, 130.9700, 20.0,
        (80.0, 190.0), 100.0, "Japan",
    ),
}


# ============================================================================ vehicles


@dataclass(frozen=True)
class StageEvent:
    """
    One separation event: what comes off, when, and in what flight condition.

    Parameters
    ----------
    time:
        Seconds after lift-off.
    altitude, speed, flight_path_angle:
        Conditions at separation - geometric altitude [m], Earth-relative speed [m/s],
        and flight-path angle above the local horizon [deg].
    dry_mass, area:
        Per-item mass [kg] and *average tumbling cross-section* [m^2].  For a spent
        cylindrical stage the tumbling average is one quarter of the total surface area.
    count:
        Number of identical items released (4 strap-ons, 2 fairing halves, ...).
    reaches_orbit:
        Upper stages that do not come straight back down.  Excluded from drop-zone
        prediction; flagged so the dashboard can say so rather than silently omit them.
    """

    name: str
    time: float
    altitude: float
    speed: float
    flight_path_angle: float
    dry_mass: float
    area: float
    shape: str = "cylinder"
    material: str = "aluminium_oxidised"
    count: int = 1
    reaches_orbit: bool = False

    def objects(self) -> list[DebrisObject]:
        """One :class:`DebrisObject` per released item."""
        ref_len = float(np.sqrt(max(self.area, 1e-6)))
        suffix = [""] if self.count == 1 else [f" #{i + 1}" for i in range(self.count)]
        return [
            DebrisObject(
                name=f"{self.name}{s}",
                mass=self.dry_mass,
                area=self.area,
                drag=DragModel(self.shape, reference_length=ref_len),
                material=self.material,
                origin="stage",
            )
            for s in suffix
        ]


@dataclass(frozen=True)
class LaunchVehicle:
    """A vehicle as a sequence of separation events, ordered by time."""

    name: str
    events: tuple[StageEvent, ...]
    operator: str = ""
    notes: str = ""

    @property
    def falling_events(self) -> tuple[StageEvent, ...]:
        """Events that produce re-entering debris (everything not going to orbit)."""
        return tuple(e for e in self.events if not e.reaches_orbit)

    @property
    def total_falling_mass(self) -> float:
        return sum(e.dry_mass * e.count for e in self.falling_events)

    @property
    def total_falling_items(self) -> int:
        return sum(e.count for e in self.falling_events)


LAUNCH_VEHICLES: dict[str, LaunchVehicle] = {
    "lvm3": LaunchVehicle(
        "LVM3 (GSLV Mk III)",
        (
            StageEvent("S200 solid booster", 130.0, 62_000.0, 1_900.0, 32.0,
                       31_000.0, 50.0, "cylinder", "stainless_steel", count=2),
            StageEvent("Payload fairing half", 208.0, 115_000.0, 3_400.0, 18.0,
                       1_200.0, 12.0, "flat_plate", "cfrp", count=2),
            StageEvent("L110 core stage", 325.0, 128_000.0, 4_400.0, 12.0,
                       10_000.0, 25.0, "cylinder", "aluminium_oxidised"),
            StageEvent("C25 cryogenic upper stage", 970.0, 190_000.0, 7_700.0, 0.5,
                       5_000.0, 20.0, "cylinder", "aluminium_oxidised",
                       reaches_orbit=True),
        ),
        "ISRO",
        "Three-stage heavy lifter; S200 boosters fall in the Bay of Bengal.",
    ),
    "pslv_xl": LaunchVehicle(
        "PSLV-XL",
        (
            StageEvent("PSOM-XL strap-on", 70.0, 24_000.0, 1_100.0, 45.0,
                       2_900.0, 9.0, "cylinder", "stainless_steel", count=6),
            StageEvent("PS1 first stage", 110.0, 63_000.0, 2_400.0, 30.0,
                       30_200.0, 42.0, "cylinder", "stainless_steel"),
            StageEvent("Heat shield half", 200.0, 118_000.0, 4_100.0, 15.0,
                       550.0, 8.0, "flat_plate", "cfrp", count=2),
            StageEvent("PS2 second stage", 263.0, 130_000.0, 4_600.0, 9.0,
                       5_300.0, 16.0, "cylinder", "aluminium_oxidised"),
            StageEvent("PS3 third stage", 500.0, 200_000.0, 6_500.0, 2.0,
                       1_120.0, 7.0, "cylinder", "cfrp"),
            StageEvent("PS4 fourth stage", 1_100.0, 640_000.0, 7_500.0, 0.0,
                       920.0, 6.0, "cylinder", "aluminium_oxidised",
                       reaches_orbit=True),
        ),
        "ISRO",
        "Workhorse SSO launcher; six strap-ons drop early and close to shore.",
    ),
    "falcon9": LaunchVehicle(
        "Falcon 9 (expendable profile)",
        (
            StageEvent("First stage", 150.0, 67_000.0, 2_300.0, 25.0,
                       25_600.0, 60.0, "cylinder", "aluminium_oxidised"),
            StageEvent("Fairing half", 200.0, 110_000.0, 3_000.0, 16.0,
                       950.0, 14.0, "flat_plate", "cfrp", count=2),
            StageEvent("Second stage", 540.0, 200_000.0, 7_600.0, 0.2,
                       4_000.0, 18.0, "cylinder", "aluminium_oxidised",
                       reaches_orbit=True),
        ),
        "SpaceX",
        "Modelled without booster recovery, i.e. the ballistic drop-zone case.",
    ),
    "ariane5": LaunchVehicle(
        "Ariane 5 ECA",
        (
            StageEvent("EAP solid booster", 140.0, 68_000.0, 2_000.0, 30.0,
                       38_200.0, 55.0, "cylinder", "stainless_steel", count=2),
            StageEvent("Fairing half", 200.0, 108_000.0, 2_900.0, 17.0,
                       1_100.0, 15.0, "flat_plate", "cfrp", count=2),
            StageEvent("EPC core stage", 540.0, 175_000.0, 7_000.0, 1.0,
                       14_700.0, 40.0, "cylinder", "aluminium_oxidised"),
            StageEvent("ESC-A upper stage", 1_500.0, 250_000.0, 9_400.0, 0.0,
                       4_540.0, 16.0, "cylinder", "aluminium_oxidised",
                       reaches_orbit=True),
        ),
        "Arianespace/ESA",
        "EPC core re-enters on a controlled arc into the Pacific.",
    ),
    "generic_two_stage": LaunchVehicle(
        "Generic two-stage medium lifter",
        (
            StageEvent("Booster", 120.0, 60_000.0, 2_000.0, 30.0,
                       20_000.0, 40.0, "cylinder", "aluminium_oxidised"),
            StageEvent("Fairing half", 200.0, 110_000.0, 3_000.0, 16.0,
                       800.0, 12.0, "flat_plate", "cfrp", count=2),
            StageEvent("Interstage", 205.0, 112_000.0, 3_050.0, 15.5,
                       450.0, 9.0, "cylinder", "aluminium_oxidised"),
            StageEvent("Upper stage", 540.0, 180_000.0, 7_200.0, 0.5,
                       3_000.0, 14.0, "cylinder", "aluminium_oxidised",
                       reaches_orbit=True),
        ),
        "-",
        "Neutral baseline for parameter studies.",
    ),
}


# ========================================================================= ascent model
def _monotone_cubic(x, y, xq):
    """
    Fritsch-Carlson monotone cubic interpolation.

    Plain cubic splines overshoot, which here would mean an ascent profile that dips below
    a separation altitude it has already passed, or briefly exceeds a speed it only
    reaches later.  Monotone Hermite interpolation cannot do that.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xq = np.atleast_1d(np.asarray(xq, dtype=float))
    n = len(x)
    if n < 2:
        return np.full_like(xq, y[0] if n else 0.0)

    h = np.diff(x)
    delta = np.diff(y) / h

    # Initial slopes: three-point difference, endpoints one-sided.
    m = np.empty(n)
    m[1:-1] = 0.5 * (delta[:-1] + delta[1:])
    m[0], m[-1] = delta[0], delta[-1]
    # Fritsch-Carlson limiter: kill slopes at extrema, clamp elsewhere.
    for i in range(n - 1):
        if delta[i] == 0.0:
            m[i] = m[i + 1] = 0.0
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] <= 0.0:
            m[i] = 0.0
    for i in range(n - 1):
        if delta[i] != 0.0:
            a, b = m[i] / delta[i], m[i + 1] / delta[i]
            s = a * a + b * b
            if s > 9.0:
                tau = 3.0 / np.sqrt(s)
                m[i], m[i + 1] = tau * a * delta[i], tau * b * delta[i]

    idx = np.clip(np.searchsorted(x, xq) - 1, 0, n - 2)
    dx = xq - x[idx]
    hh = h[idx]
    t = dx / hh
    t2, t3 = t * t, t * t * t
    h00 = 2 * t3 - 3 * t2 + 1
    h10 = t3 - 2 * t2 + t
    h01 = -2 * t3 + 3 * t2
    h11 = t3 - t2
    return h00 * y[idx] + h10 * hh * m[idx] + h01 * y[idx + 1] + h11 * hh * m[idx + 1]


@dataclass
class AscentProfile:
    """Sampled ascent: arrays over time plus the ground track."""

    time: np.ndarray
    altitude: np.ndarray
    speed: np.ndarray
    flight_path_angle: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    downrange: np.ndarray
    site: LaunchSite
    azimuth: float
    vehicle: LaunchVehicle


def ascent_profile(
    vehicle: LaunchVehicle,
    site: LaunchSite,
    azimuth: float | None = None,
    n_samples: int = 400,
) -> AscentProfile:
    """
    Kinematic ascent through the vehicle's separation conditions.

    Altitude, speed and flight-path angle are monotone-cubic interpolants of the quoted
    separation values; downrange comes from integrating the horizontal speed component,
    and the ground track follows a constant-azimuth great circle from the pad.
    """
    az = site.default_azimuth if azimuth is None else float(azimuth)
    events = sorted(vehicle.events, key=lambda e: e.time)

    # Lift-off anchor plus a short vertical-rise point so the initial pitch-over is not
    # interpolated as an instantaneous kink.
    t_k = [0.0, 8.0] + [e.time for e in events]
    alt_k = [site.elevation, site.elevation + 300.0] + [e.altitude for e in events]
    spd_k = [0.0, 60.0] + [e.speed for e in events]
    fpa_k = [90.0, 89.0] + [e.flight_path_angle for e in events]

    t = np.linspace(0.0, t_k[-1], int(n_samples))
    alt = _monotone_cubic(t_k, alt_k, t)
    spd = _monotone_cubic(t_k, spd_k, t)
    fpa = np.clip(_monotone_cubic(t_k, fpa_k, t), -90.0, 90.0)

    v_horiz = spd * np.cos(np.radians(fpa))
    downrange = np.concatenate([[0.0], np.cumsum(0.5 * (v_horiz[1:] + v_horiz[:-1]) * np.diff(t))])
    lat, lon = destination_point(site.latitude, site.longitude, az, downrange)

    return AscentProfile(
        time=t, altitude=alt, speed=spd, flight_path_angle=fpa,
        latitude=np.asarray(lat), longitude=np.asarray(lon), downrange=downrange,
        site=site, azimuth=az, vehicle=vehicle,
    )


def separation_states(
    vehicle: LaunchVehicle,
    site: LaunchSite,
    azimuth: float | None = None,
    include_orbital: bool = False,
) -> list[tuple[StageEvent, StateVector, list[DebrisObject]]]:
    """
    Separation state for every event, in the order they occur.

    Returns ``(event, state, objects)`` triples.  ``state`` is a full ECEF
    :class:`~debris.propagator.StateVector` ready for propagation; ``objects`` is one
    :class:`~debris.propagator.DebrisObject` per released item.
    """
    az = site.default_azimuth if azimuth is None else float(azimuth)
    profile = ascent_profile(vehicle, site, az)
    events = sorted(vehicle.events, key=lambda e: e.time)

    out = []
    for ev in events:
        if ev.reaches_orbit and not include_orbital:
            continue
        # Downrange at separation, from the same interpolant the profile plot uses.
        dr = float(np.interp(ev.time, profile.time, profile.downrange))
        lat, lon = destination_point(site.latitude, site.longitude, az, dr)
        state = StateVector.from_geodetic(
            float(lat), float(lon), ev.altitude, ev.speed,
            ev.flight_path_angle, az, t=ev.time,
        )
        out.append((ev, state, ev.objects()))
    return out


def with_scaled_performance(vehicle: LaunchVehicle, speed_factor: float = 1.0,
                            altitude_factor: float = 1.0) -> LaunchVehicle:
    """
    Copy of ``vehicle`` with all separation speeds/altitudes scaled.

    Useful for asking "what if the first stage underperformed by 5 %?" - an
    underperformance is one of the classic ways scheduled debris ends up outside its
    cleared drop zone.
    """
    events = tuple(
        replace(e, speed=e.speed * speed_factor, altitude=e.altitude * altitude_factor)
        for e in vehicle.events
    )
    return replace(vehicle, events=events, notes=f"{vehicle.notes} [scaled]")
