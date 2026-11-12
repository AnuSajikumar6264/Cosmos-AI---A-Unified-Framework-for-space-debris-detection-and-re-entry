"""Schematic orbit geometry for the console's three-dimensional globe.

**What is evidence here, and what is not.** The dated catalogue snapshot
(``outputs/twin/as_of_<date>/forecast_table.csv.gz``) publishes three geometric quantities per
object: perigee altitude, apogee altitude and inclination. From those three the semi-major axis,
the eccentricity and the Keplerian period follow in closed form, so the **size, shape and tilt**
of every orbit this module returns are archive-derived.

The snapshot publishes **no** right ascension of the ascending node, **no** argument of perigee,
**no** epoch and **no** anomaly (limitation P5: mean elements only, no state vector). Without
them an object's position in inertial space is undetermined, and so is any ground track. This
module therefore never invents them. It assigns a *layout* angle per object — a deterministic
golden-angle sequence keyed by the NORAD id — for the single purpose of separating orbits on
screen, and marks every such quantity ``not_physical``. The payload carries a
``geometry_basis`` block that states this in the response itself, so a client cannot present the
result as a propagated trajectory without contradicting its own data.

Consequences that the caller must respect:

* the drawn ellipse is the object's real orbit *shape* in an arbitrary orientation about the pole;
* the marker is a position *on that ellipse*, not the object's position at any time;
* no ground track, sub-satellite point, latitude, longitude or velocity is produced, because the
  archive cannot support one;
* nothing here is animated as a function of time: a moving marker would assert propagation.

Everything is pure, deterministic and unit-tested (``tests/test_visual_console.py``).
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

from ..common import MU_EARTH, R_EARTH

SCHEMA_VERSION = "globe/1.0"

#: Earth equatorial radius in kilometres (WGS-84, from :mod:`cosmos.common`).
R_EARTH_KM = R_EARTH / 1000.0
#: Geocentric gravitational constant in km^3/s^2 (from :mod:`cosmos.common`).
MU_EARTH_KM3_S2 = MU_EARTH / 1e9

#: Points per drawn ellipse. Sampled in eccentric anomaly, so points are evenly spaced along the
#: curve rather than bunched at apogee.
ORBIT_SAMPLES = 64
#: Points for the one selected object, drawn at higher resolution.
ORBIT_SAMPLES_DETAIL = 192

#: Golden angle and two further irrational multipliers. Keyed by NORAD id, they spread the layout
#: angles evenly and reproducibly: the same object always lands in the same place, so nothing on
#: screen can look like motion between page loads.
_GOLDEN_DEG = 137.50776405003785
_ARGP_DEG = 99.61904761904762
_PHASE_DEG = 222.49223594996215

#: Altitude bands, by perigee altitude in km, as plain descriptive labels.
_BANDS = ((2000.0, "LEO"), (35_000.0, "MEO"), (float("inf"), "GEO/high"))


def _finite(value: Any) -> float | None:
    """A float if the value is finite, else None. Accepts NaN, None and strings."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def orbit_shape(perigee_km: Any, apogee_km: Any, inclination_deg: Any) -> dict[str, Any] | None:
    """Two-body orbit shape from the three archived quantities, or None when they are unusable.

    ``perigee_km`` and ``apogee_km`` are altitudes above the WGS-84 equatorial radius, as the
    catalogue publishes them. Returns radii and the period as well, all archive-derived.
    """
    hp, ha, inc = _finite(perigee_km), _finite(apogee_km), _finite(inclination_deg)
    if hp is None or ha is None or inc is None:
        return None
    if ha < hp:                                  # never silently reorder a bad row
        return None
    if hp <= -R_EARTH_KM or not (0.0 <= inc <= 180.0):
        return None
    r_p, r_a = R_EARTH_KM + hp, R_EARTH_KM + ha
    if r_p <= 0.0:
        return None
    a = 0.5 * (r_p + r_a)
    e = (r_a - r_p) / (r_a + r_p)
    period_min = 2.0 * math.pi * math.sqrt(a ** 3 / MU_EARTH_KM3_S2) / 60.0
    band = next(label for limit, label in _BANDS if hp < limit)
    return {
        "perigee_km": hp, "apogee_km": ha, "inclination_deg": inc,
        "periapsis_radius_km": r_p, "apoapsis_radius_km": r_a,
        "semi_major_axis_km": a, "eccentricity": e,
        "period_min": period_min, "altitude_band": band,
        "periapsis_earth_radii": r_p / R_EARTH_KM, "apoapsis_earth_radii": r_a / R_EARTH_KM,
    }


def layout_angles(norad: int) -> dict[str, Any]:
    """Deterministic on-screen layout angles. **Not** orbital elements: see the module docstring."""
    n = int(norad)
    return {
        "node_deg": (n * _GOLDEN_DEG) % 360.0,
        "perigee_argument_deg": (n * _ARGP_DEG) % 360.0,
        "phase_deg": (n * _PHASE_DEG) % 360.0,
        "not_physical": True,
        "reason": ("the archive publishes no node, perigee argument, epoch or anomaly; these angles "
                   "only separate orbits on screen and are keyed to the NORAD id so they never change"),
    }


def _point(shape: Mapping[str, Any], node_deg: float, argp_deg: float,
           eccentric_anomaly_rad: float) -> tuple[float, float, float]:
    """One point of the ellipse in Earth radii, in a frame whose z axis is the Earth's rotation axis.

    Standard two-body transformation from the perifocal frame: radius and true anomaly from the
    eccentric anomaly, then the rotations R3(-node) R1(-inclination) R3(-perigee argument).
    """
    a = float(shape["semi_major_axis_km"])
    e = float(shape["eccentricity"])
    inc = math.radians(float(shape["inclination_deg"]))
    node = math.radians(node_deg)
    argp = math.radians(argp_deg)
    big_e = eccentric_anomaly_rad
    r = a * (1.0 - e * math.cos(big_e))
    nu = math.atan2(math.sqrt(max(0.0, 1.0 - e * e)) * math.sin(big_e), math.cos(big_e) - e)
    u = argp + nu
    cu, su, ci, si = math.cos(u), math.sin(u), math.cos(inc), math.sin(inc)
    cn, sn = math.cos(node), math.sin(node)
    x = r * (cn * cu - sn * su * ci)
    y = r * (sn * cu + cn * su * ci)
    z = r * (su * si)
    k = 1.0 / R_EARTH_KM
    return (x * k, y * k, z * k)


def orbit_polyline(shape: Mapping[str, Any], angles: Mapping[str, Any],
                   samples: int = ORBIT_SAMPLES, places: int = 4) -> list[float]:
    """The closed ellipse as a flat ``[x, y, z, x, y, z, ...]`` list in Earth radii.

    Flat and rounded because this travels to the browser for every drawn object; the first point
    is repeated at the end so the renderer can draw one line strip without closing logic.
    """
    node = float(angles["node_deg"])
    argp = float(angles["perigee_argument_deg"])
    out: list[float] = []
    for i in range(samples + 1):
        big_e = 2.0 * math.pi * (i % samples) / samples
        for v in _point(shape, node, argp, big_e):
            out.append(round(v, places))
    return out


def marker_point(shape: Mapping[str, Any], angles: Mapping[str, Any], places: int = 4) -> list[float]:
    """A point **on** the drawn ellipse, at the layout phase. Not a position at any time."""
    return [round(v, places) for v in _point(shape, float(angles["node_deg"]),
                                             float(angles["perigee_argument_deg"]),
                                             math.radians(float(angles["phase_deg"])))]


def object_geometry(row: Mapping[str, Any], *, detail: bool = False) -> dict[str, Any] | None:
    """Geometry for one catalogue row, or None when its three quantities cannot support an orbit.

    ``row`` uses the keys of :meth:`cosmos.product.store.ArtifactStore.search_objects`.
    """
    shape = orbit_shape(row.get("perigee_km"), row.get("apogee_km"), row.get("inclination_deg"))
    if shape is None:
        return None
    norad = int(row["norad"])
    angles = layout_angles(norad)
    samples = ORBIT_SAMPLES_DETAIL if detail else ORBIT_SAMPLES
    return {
        "norad": norad,
        "name": row.get("name"),
        "object_class": row.get("object_class"),
        "regime": row.get("regime"),
        "p_reentry_30d": _finite(row.get("p_reentry_30d")),
        "archived_elements": {k: shape[k] for k in
                              ("perigee_km", "apogee_km", "inclination_deg")},
        "derived_elements": {k: shape[k] for k in
                             ("semi_major_axis_km", "eccentricity", "period_min", "altitude_band",
                              "periapsis_earth_radii", "apoapsis_earth_radii")},
        "layout": angles,
        "marker_earth_radii": marker_point(shape, angles),
        "orbit_earth_radii": orbit_polyline(shape, angles, samples=samples),
        "orbit_points": samples + 1,
    }


def geometry_basis() -> dict[str, Any]:
    """The statement of what the geometry is, carried inside every payload."""
    return {
        "frame": ("geocentric, z along the Earth's rotation axis, in Earth radii "
                  f"(1 = {R_EARTH_KM:.3f} km, WGS-84 equatorial)"),
        "from_archive": ["perigee altitude", "apogee altitude", "inclination"],
        "derived_from_archive": ["semi-major axis", "eccentricity", "Keplerian period",
                                 "orbit shape and tilt"],
        "not_available_and_not_invented": ["right ascension of the ascending node",
                                           "argument of perigee", "epoch", "mean or true anomaly",
                                           "position at any time", "velocity",
                                           "sub-satellite point", "ground track"],
        "layout_angles": ("node, perigee argument and phase are a deterministic golden-angle layout "
                          "keyed to the NORAD id, used only to separate orbits on screen"),
        "reading": ("each ellipse is that object's real orbit size, shape and tilt in an arbitrary "
                    "orientation about the pole; each marker is a point on that ellipse, not the "
                    "object's position; nothing is propagated and nothing is animated in time"),
        "limitation": "P5 (mean elements only, no state vector); see docs/product/KNOWN_LIMITATIONS.md",
        "earth_texture": ("land mask derived from the archived population grid "
                          "data/feature3_reentry/external/population_grid_0p25deg.npz "
                          "(GHS-POP E2020 R2023A, JRC, CC BY 4.0; Natural Earth 1:50m land, public domain)"),
    }


def globe_payload(rows: Sequence[Mapping[str, Any]], *, as_of: str,
                  detail_norad: int | None = None,
                  include: Iterable[int] = (),
                  catalogue_objects: int | None = None) -> dict[str, Any]:
    """The whole scene: drawable objects, what was excluded and why, and the geometry basis."""
    wanted = [int(n) for n in include]
    ordered = sorted(rows, key=lambda r: (0, wanted.index(int(r["norad"])))
                     if int(r["norad"]) in wanted else (1, 0))
    objects: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in ordered:
        norad = int(row["norad"])
        geom = object_geometry(row, detail=(detail_norad is not None and norad == detail_norad))
        if geom is None:
            missing = [name for name, key in (("perigee", "perigee_km"), ("apogee", "apogee_km"),
                                              ("inclination", "inclination_deg"))
                       if _finite(row.get(key)) is None]
            excluded.append({"norad": norad, "name": row.get("name"),
                             "reason": ("the snapshot has no usable "
                                        + ", ".join(missing or ["orbit geometry"])
                                        + " for this object, so no orbit is drawn")})
            continue
        objects.append(geom)
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": as_of,
        "live": False,
        "note": ("archived snapshot geometry; the console connects to no live source and propagates "
                 "nothing at request time"),
        "earth_radius_km": R_EARTH_KM,
        "objects": objects,
        "object_count": len(objects),
        "catalogue_objects": catalogue_objects,
        "excluded": excluded,
        "excluded_count": len(excluded),
        "geometry_basis": geometry_basis(),
    }
