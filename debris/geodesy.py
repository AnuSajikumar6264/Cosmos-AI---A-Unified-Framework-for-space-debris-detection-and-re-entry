"""
WGS-84 geodesy: frame conversions and spherical-Earth range/bearing helpers.

The re-entry propagator integrates in **ECEF** (Earth-Centred Earth-Fixed).  That is
deliberate: the atmosphere co-rotates with the Earth, so in ECEF the aerodynamic
relative velocity is simply the state velocity, and the Coriolis/centrifugal terms
that visibly rotate a debris footprint eastward are carried explicitly by the
equations of motion rather than bolted on afterwards.
"""

from __future__ import annotations

import math

import numpy as np

from .constants import WGS84_A, WGS84_B, WGS84_E2, WGS84_EP2

MEAN_EARTH_RADIUS = 6371008.8  # IUGG mean radius [m], for great-circle work


def geodetic_to_ecef(lat_deg, lon_deg, alt_m):
    """Geodetic (deg, deg, m above ellipsoid) -> ECEF xyz [m]. Vectorised."""
    lat = np.radians(np.asarray(lat_deg, dtype=float))
    lon = np.radians(np.asarray(lon_deg, dtype=float))
    alt = np.asarray(alt_m, dtype=float)
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    n = WGS84_A / np.sqrt(1.0 - WGS84_E2 * sin_lat**2)  # prime vertical radius
    x = (n + alt) * cos_lat * np.cos(lon)
    y = (n + alt) * cos_lat * np.sin(lon)
    z = (n * (1.0 - WGS84_E2) + alt) * sin_lat
    return np.stack(np.broadcast_arrays(x, y, z), axis=-1)


def ecef_to_geodetic(r_ecef):
    """
    ECEF xyz [m] -> (lat_deg, lon_deg, alt_m) via Ferrari's closed-form solution
    (Zhu 1994).  Exact to floating-point precision, no iteration, and stable from
    the geocentre out to deep space.  Accepts (3,) or (..., 3).
    """
    r = np.asarray(r_ecef, dtype=float)
    x, y, z = r[..., 0], r[..., 1], r[..., 2]

    lon = np.arctan2(y, x)
    p = np.hypot(x, y)

    # Degenerate case: on the polar axis.
    polar = p < 1e-9
    p_safe = np.where(polar, 1.0, p)

    f = 54.0 * WGS84_B**2 * z**2
    g = p_safe**2 + (1.0 - WGS84_E2) * z**2 - WGS84_E2 * (WGS84_A**2 - WGS84_B**2)
    g = np.where(np.abs(g) < 1e-30, 1e-30, g)
    c = WGS84_E2**2 * f * p_safe**2 / g**3
    s = np.cbrt(1.0 + c + np.sqrt(np.maximum(c**2 + 2.0 * c, 0.0)))
    pp = f / (3.0 * (s + 1.0 / s + 1.0) ** 2 * g**2)
    q = np.sqrt(np.maximum(1.0 + 2.0 * WGS84_E2**2 * pp, 0.0))
    r0 = -pp * WGS84_E2 * p_safe / (1.0 + q) + np.sqrt(
        np.maximum(
            0.5 * WGS84_A**2 * (1.0 + 1.0 / q)
            - pp * (1.0 - WGS84_E2) * z**2 / (q * (1.0 + q))
            - 0.5 * pp * p_safe**2,
            0.0,
        )
    )
    u = np.sqrt((p_safe - WGS84_E2 * r0) ** 2 + z**2)
    v = np.sqrt((p_safe - WGS84_E2 * r0) ** 2 + (1.0 - WGS84_E2) * z**2)
    v = np.where(v < 1e-30, 1e-30, v)
    z0 = WGS84_B**2 * z / (WGS84_A * v)

    alt = u * (1.0 - WGS84_B**2 / (WGS84_A * v))
    lat = np.arctan2(z + WGS84_EP2 * z0, p_safe)

    # Polar axis: latitude is +/-90 deg, altitude is |z| - b.
    lat = np.where(polar, np.sign(np.where(z == 0.0, 1.0, z)) * (np.pi / 2.0), lat)
    alt = np.where(polar, np.abs(z) - WGS84_B, alt)

    return np.degrees(lat), np.degrees(lon), alt


def geodetic_altitude(r_ecef):
    """Altitude above the WGS-84 ellipsoid [m] only (convenience for the integrator)."""
    return ecef_to_geodetic(r_ecef)[2]


def ecef_to_geodetic_scalar(x: float, y: float, z: float) -> tuple[float, float, float]:
    """
    Scalar, pure-``math`` ECEF -> (lat_deg, lon_deg, alt_m).

    Same answer as :func:`ecef_to_geodetic` to well under a millimetre, but roughly an
    order of magnitude faster for one point at a time because it avoids numpy array
    overhead.  The propagator calls this on every derivative evaluation, so the
    speed-up is worth having a second implementation - :func:`ecef_to_geodetic` stays
    as the vectorised reference the fast path is validated against.
    """
    p = math.hypot(x, y)
    lon = math.atan2(y, x)

    if p < 1e-9:  # polar axis
        return (90.0 if z >= 0.0 else -90.0), math.degrees(lon), abs(z) - WGS84_B

    lat = math.atan2(z, p)
    alt = 0.0
    for _ in range(4):
        sin_lat = math.sin(lat)
        n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        # Pick the numerically better of the two altitude expressions: dividing by
        # cos(lat) blows up near the poles, dividing by sin(lat) blows up at the equator.
        if abs(lat) < math.pi / 4.0:
            alt = p / math.cos(lat) - n
        else:
            alt = z / sin_lat - n * (1.0 - WGS84_E2)
        lat = math.atan2(z, p * (1.0 - WGS84_E2 * n / (n + alt)))
    return math.degrees(lat), math.degrees(lon), alt


def altitude_scalar(r_ecef) -> float:
    """Ellipsoidal altitude [m] of a single ECEF point, via the fast scalar path."""
    return ecef_to_geodetic_scalar(float(r_ecef[0]), float(r_ecef[1]), float(r_ecef[2]))[2]


def enu_basis(lat_deg, lon_deg):
    """
    East/North/Up unit vectors at a geodetic point, expressed in ECEF.

    Returns a (3, 3) matrix whose *rows* are (east, north, up), i.e. the rotation
    that takes an ECEF vector into the local ENU frame.
    """
    lat = np.radians(float(lat_deg))
    lon = np.radians(float(lon_deg))
    sl, cl = np.sin(lat), np.cos(lat)
    so, co = np.sin(lon), np.cos(lon)
    east = np.array([-so, co, 0.0])
    north = np.array([-sl * co, -sl * so, cl])
    up = np.array([cl * co, cl * so, sl])
    return np.stack([east, north, up])


def ecef_to_enu(vec_ecef, lat_deg, lon_deg):
    """Rotate an ECEF *vector* (not position) into local ENU components."""
    return enu_basis(lat_deg, lon_deg) @ np.asarray(vec_ecef, dtype=float)


def enu_to_ecef(vec_enu, lat_deg, lon_deg):
    """Rotate a local ENU *vector* into ECEF components."""
    return enu_basis(lat_deg, lon_deg).T @ np.asarray(vec_enu, dtype=float)


def great_circle_distance(lat1, lon1, lat2, lon2, radius=MEAN_EARTH_RADIUS):
    """Haversine surface distance [m] between geodetic points. Vectorised."""
    p1, p2 = np.radians(np.asarray(lat1, float)), np.radians(np.asarray(lat2, float))
    dphi = p2 - p1
    dlam = np.radians(np.asarray(lon2, float) - np.asarray(lon1, float))
    a = np.sin(dphi / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlam / 2.0) ** 2
    return 2.0 * radius * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def initial_bearing(lat1, lon1, lat2, lon2):
    """Forward azimuth [deg, 0 = north, clockwise] from point 1 to point 2."""
    p1, p2 = np.radians(np.asarray(lat1, float)), np.radians(np.asarray(lat2, float))
    dlam = np.radians(np.asarray(lon2, float) - np.asarray(lon1, float))
    y = np.sin(dlam) * np.cos(p2)
    x = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dlam)
    return np.degrees(np.arctan2(y, x)) % 360.0


def destination_point(lat_deg, lon_deg, bearing_deg, distance_m,
                      radius=MEAN_EARTH_RADIUS):
    """Great-circle propagation of a point along a bearing. Vectorised."""
    p1 = np.radians(np.asarray(lat_deg, float))
    l1 = np.radians(np.asarray(lon_deg, float))
    th = np.radians(np.asarray(bearing_deg, float))
    d = np.asarray(distance_m, float) / radius
    p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(th))
    l2 = l1 + np.arctan2(
        np.sin(th) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2)
    )
    return np.degrees(p2), wrap_longitude(np.degrees(l2))


def wrap_longitude(lon_deg):
    """Wrap longitude into [-180, 180)."""
    return (np.asarray(lon_deg, dtype=float) + 180.0) % 360.0 - 180.0


def velocity_from_launch_frame(lat_deg, lon_deg, speed, flight_path_deg, azimuth_deg,
                              earth_fixed=True):
    """
    Build an ECEF velocity vector from the range-safety convention operators use:
    speed, flight-path angle above the local horizon, and azimuth clockwise from
    north.  ``earth_fixed=True`` treats the inputs as Earth-relative (what a
    tracking radar reports), which is what the ECEF propagator wants.
    """
    fpa = np.radians(float(flight_path_deg))
    az = np.radians(float(azimuth_deg))
    v = float(speed)
    enu = np.array(
        [v * np.cos(fpa) * np.sin(az), v * np.cos(fpa) * np.cos(az), v * np.sin(fpa)]
    )
    v_ecef = enu_to_ecef(enu, lat_deg, lon_deg)
    if not earth_fixed:
        # Inputs were inertial: subtract the co-rotation velocity to get Earth-fixed.
        from .constants import EARTH_OMEGA

        r = geodetic_to_ecef(lat_deg, lon_deg, 0.0)
        v_ecef = v_ecef - np.cross([0.0, 0.0, EARTH_OMEGA], r)
    return v_ecef
