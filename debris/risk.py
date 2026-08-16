"""
Ground risk: from an impact footprint to an expected-casualty number.

The quantity that regulators actually gate on is the **expected casualty count**, E_c:

    E_c = sum over fragments of  P(fragment lands at x) * rho_pop(x) * A_c(fragment)

with the *debris casualty area* (FAA AC 431.35-2A, and the same convention in ESA and
IADC re-entry safety work)

    A_c = (sqrt(A_debris) + sqrt(A_person))^2,     A_person ~ 0.36 m^2

A fragment only counts if it arrives with at least ~15 J of kinetic energy - the classic
range-safety threshold below which an impact is not casualty-causing.  Both rules are
applied here, and the 1-in-10 000 (E_c <= 1e-4) threshold used by NASA/ESA for a
controlled re-entry is reported against.

Population data - read this before quoting a number
---------------------------------------------------
There is no population raster in this repository, and a wrong one would be worse than an
honest approximation.  :class:`SyntheticPopulationModel` therefore builds density from:

* a hand-authored 10-degree land-fraction grid (ocean vs land - the single most important
  distinction, since ~71 % of impacts are into water and carry no risk at all);
* a table of ~50 real metropolitan areas with published coordinates and populations,
  each as a decaying urban core;
* a regional rural background multiplier (South Asia dense, Sahara and Siberia sparse).

That is good to roughly an order of magnitude at 100 km scales, which is enough to tell
"ocean", "empty desert" and "over Dhaka" apart - and *not* enough to support an
operational safety case.  :meth:`PopulationModel.from_grid` accepts a real raster
(GPWv4, LandScan, WorldPop) and should be used for anything that matters.  Every reported
figure carries the model's ``provenance`` string so the caveat travels with the number.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .constants import CASUALTY_KE_THRESHOLD, PERSON_AREA
from .geodesy import great_circle_distance, wrap_longitude
from .monte_carlo import ConformalZone, Footprint

# ------------------------------------------------------------------- land fraction grid
# 18 rows of 36 hex-ish digits: rows run 80..90N down to 90..80S, columns -180..-170 east
# to 170..180.  Each digit is land fraction in tenths.  Hand-authored from world geography
# at 10-degree resolution; coarse but unbiased about where the oceans are.
_LAND_ROWS = (
    "000000012222100000011001000110000000",  # 80-90 N
    "002334565555468610021013345654332101",  # 70-80 N
    "015778888887656411367788888888875432",  # 60-70 N
    "122347888888730001368888888888886421",  # 50-60 N
    "100002888885100004788888888888887310",  # 40-50 N
    "000003888861000015566788888888863100",  # 30-40 N
    "000000577410000038888886467578310000",  # 20-30 N
    "000000035422100004888888852356531000",  # 10-20 N
    "000000001256651027888862001255310100",  # 0-10 N
    "000000000058886100158866100003443210",  # 10 S-0
    "000000000038885000038852000002787200",  # 20-10 S
    "000000000028884000038831000002888200",  # 30-20 S
    "000000000276100000016400000001675012",  # 40-30 S
    "000000000015300000000000000000002021",  # 50-40 S
    "000000000011001000000000000000000000",  # 60-50 S
    "222222222223211111112222222222222222",  # 70-60 S
    "777777777733456777888888888888888545",  # 80-70 S
    "999999999999999999999999999999999999",  # 90-80 S
)
_LAND = np.array([[int(ch) / 9.0 for ch in row] for row in _LAND_ROWS])

#: Real metropolitan areas: (name, lat, lon, population in millions, core radius km).
#: Coordinates and populations are public figures for the wider urban agglomeration.
_METROS = [
    ("Tokyo", 35.68, 139.69, 37.0, 45), ("Delhi", 28.61, 77.21, 33.0, 40),
    ("Shanghai", 31.23, 121.47, 29.0, 40), ("Dhaka", 23.81, 90.41, 23.2, 25),
    ("Sao Paulo", -23.55, -46.63, 22.6, 35), ("Cairo", 30.04, 31.24, 22.2, 30),
    ("Mexico City", 19.43, -99.13, 22.0, 35), ("Beijing", 39.90, 116.41, 21.8, 40),
    ("Mumbai", 19.08, 72.88, 21.3, 25), ("Osaka", 34.69, 135.50, 19.0, 30),
    ("Karachi", 24.86, 67.01, 17.2, 25), ("Chongqing", 29.56, 106.55, 17.0, 40),
    ("Istanbul", 41.01, 28.98, 15.8, 30), ("Buenos Aires", -34.60, -58.38, 15.4, 35),
    ("Kolkata", 22.57, 88.36, 15.3, 25), ("Kinshasa", -4.44, 15.27, 15.0, 25),
    ("Lagos", 6.52, 3.38, 15.0, 30), ("Manila", 14.60, 120.98, 14.7, 25),
    ("Rio de Janeiro", -22.91, -43.17, 13.5, 30), ("Guangzhou", 23.13, 113.26, 13.3, 35),
    ("Lahore", 31.55, 74.34, 13.1, 25), ("Bangalore", 12.97, 77.59, 13.0, 25),
    ("Moscow", 55.76, 37.62, 12.6, 35), ("Shenzhen", 22.54, 114.06, 12.6, 30),
    ("Chennai", 13.08, 80.27, 11.5, 25), ("Bogota", 4.71, -74.07, 11.3, 25),
    ("Jakarta", -6.21, 106.85, 11.2, 30), ("Paris", 48.86, 2.35, 11.2, 30),
    ("Tehran", 35.69, 51.39, 9.6, 25), ("Seoul", 37.57, 126.98, 10.0, 30),
    ("London", 51.51, -0.13, 9.6, 30), ("New York", 40.71, -74.01, 8.8, 35),
    ("Lima", -12.05, -77.04, 11.0, 25), ("Bangkok", 13.76, 100.50, 11.0, 30),
    ("Hyderabad", 17.39, 78.49, 10.5, 25), ("Chicago", 41.88, -87.63, 8.9, 35),
    ("Ho Chi Minh City", 10.82, 106.63, 9.3, 25), ("Ahmedabad", 23.02, 72.57, 8.6, 20),
    ("Kuala Lumpur", 3.14, 101.69, 8.4, 25), ("Riyadh", 24.71, 46.68, 7.7, 25),
    ("Santiago", -33.45, -70.67, 6.9, 25), ("Johannesburg", -26.20, 28.05, 6.2, 30),
    ("Nairobi", -1.29, 36.82, 5.5, 20), ("Sydney", -33.87, 151.21, 5.4, 30),
    ("Melbourne", -37.81, 144.96, 5.2, 30), ("Toronto", 43.65, -79.38, 6.4, 30),
    ("Los Angeles", 34.05, -118.24, 12.5, 40), ("Madrid", 40.42, -3.70, 6.7, 25),
    ("Berlin", 52.52, 13.40, 4.5, 25), ("Rome", 41.90, 12.50, 4.3, 25),
    ("Chennai-Sriharikota", 13.72, 80.23, 0.05, 10),  # SDSC SHAR neighbourhood
]

#: Rural background density [people/km^2] by broad region, as (lat0, lat1, lon0, lon1, d).
_RURAL_REGIONS = [
    (5.0, 35.0, 60.0, 92.0, 420.0),     # South Asia
    (18.0, 45.0, 100.0, 125.0, 260.0),  # eastern China
    (30.0, 40.0, 126.0, 142.0, 300.0),  # Japan / Korea
    (35.0, 60.0, -10.0, 40.0, 110.0),   # Europe
    (-5.0, 15.0, 95.0, 130.0, 150.0),   # SE Asia
    (-35.0, 15.0, -20.0, 52.0, 40.0),   # sub-Saharan Africa
    (15.0, 32.0, -18.0, 40.0, 6.0),     # Sahara
    (25.0, 50.0, -125.0, -70.0, 30.0),  # USA / Mexico
    (-40.0, 10.0, -82.0, -35.0, 25.0),  # South America
    (50.0, 72.0, 40.0, 180.0, 2.0),     # Siberia
    (45.0, 72.0, -140.0, -60.0, 2.0),   # northern Canada
    (-45.0, -10.0, 112.0, 155.0, 3.0),  # Australia
    (-90.0, -60.0, -180.0, 180.0, 0.0),  # Antarctica
]
_DEFAULT_RURAL = 18.0  # global land average outside the named regions


# =============================================================================== models
@dataclass
class PopulationModel:
    """
    Base interface: population density in people per km^2 at geodetic points.

    Subclass or use :meth:`from_grid` to plug in real data.
    """

    provenance: str = "abstract"

    def density(self, lat, lon):  # pragma: no cover - interface
        raise NotImplementedError

    def land_fraction(self, lat, lon):
        """Fraction of the cell that is land, in [0, 1]."""
        raise NotImplementedError

    @staticmethod
    def from_grid(density_grid, lat_edges, lon_edges, provenance: str = "user raster"):
        """
        Wrap a real population raster.

        ``density_grid[i, j]`` is people/km^2 for latitudes ``lat_edges[i:i+2]`` and
        longitudes ``lon_edges[j:j+2]``.  Use this with GPWv4 / LandScan / WorldPop for any
        result that has to stand up to scrutiny.
        """
        return _GriddedPopulation(np.asarray(density_grid, dtype=float),
                                  np.asarray(lat_edges, dtype=float),
                                  np.asarray(lon_edges, dtype=float), provenance)


@dataclass
class _GriddedPopulation(PopulationModel):
    grid: np.ndarray = field(default_factory=lambda: np.zeros((1, 1)))
    lat_edges: np.ndarray = field(default_factory=lambda: np.array([-90.0, 90.0]))
    lon_edges: np.ndarray = field(default_factory=lambda: np.array([-180.0, 180.0]))
    provenance: str = "user raster"

    def density(self, lat, lon):
        lat = np.asarray(lat, dtype=float)
        lon = wrap_longitude(lon)
        i = np.clip(np.searchsorted(self.lat_edges, lat) - 1, 0, self.grid.shape[0] - 1)
        j = np.clip(np.searchsorted(self.lon_edges, lon) - 1, 0, self.grid.shape[1] - 1)
        return self.grid[i, j]

    def land_fraction(self, lat, lon):
        return (self.density(lat, lon) > 0).astype(float)


@dataclass
class SyntheticPopulationModel(PopulationModel):
    """
    Coarse global population density assembled from a land mask, metro table and regional
    rural background.  See the module docstring for exactly what this is and is not good
    for.
    """

    urban_scale: float = 1.0
    rural_scale: float = 1.0
    provenance: str = (
        "SYNTHETIC: 10-deg land mask + 51 metro areas + regional rural background. "
        "Order-of-magnitude only; not valid for an operational safety case."
    )

    def land_fraction(self, lat, lon):
        lat = np.asarray(lat, dtype=float)
        lon = wrap_longitude(lon)
        row = np.clip(((90.0 - lat) // 10.0).astype(int), 0, 17)
        col = np.clip(((lon + 180.0) // 10.0).astype(int), 0, 35)
        return _LAND[row, col]

    def _rural(self, lat, lon):
        lat = np.asarray(lat, dtype=float)
        lon = wrap_longitude(lon)
        out = np.full(np.shape(lat), _DEFAULT_RURAL, dtype=float)
        for la0, la1, lo0, lo1, dens in _RURAL_REGIONS:
            m = (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
            out = np.where(m, dens, out)
        return out * self.rural_scale

    def density(self, lat, lon):
        """People per km^2. Vectorised over ``lat``/``lon``."""
        lat = np.atleast_1d(np.asarray(lat, dtype=float))
        lon = wrap_longitude(np.atleast_1d(np.asarray(lon, dtype=float)))
        land = self.land_fraction(lat, lon)
        dens = self._rural(lat, lon) * land

        # Urban cores: Gaussian in great-circle distance, peak set so the integral over the
        # core recovers the stated population.
        for _name, mlat, mlon, pop_m, r_km in _METROS:
            d = great_circle_distance(lat, lon, mlat, mlon) / 1000.0
            near = d < 4.0 * r_km
            if not np.any(near):
                continue
            peak = pop_m * 1e6 / (2.0 * math.pi * r_km**2)
            dens = dens + self.urban_scale * peak * np.exp(-0.5 * (d / r_km) ** 2)
        return dens

    def nearest_metro(self, lat: float, lon: float):
        """``(name, distance_km, population_millions)`` of the closest listed metro."""
        best = None
        for name, mlat, mlon, pop_m, _r in _METROS:
            d = float(great_circle_distance(lat, lon, mlat, mlon)) / 1000.0
            if best is None or d < best[1]:
                best = (name, d, pop_m)
        return best


# ============================================================================ assessment
@dataclass
class RiskAssessment:
    """Ground-risk result for one footprint."""

    expected_casualties: float
    casualty_area_total: float          # [m^2]
    n_casualty_capable: int
    n_impacts: int
    land_impact_probability: float
    ocean_impact_probability: float
    mean_population_density: float      # [people/km^2] over impact points
    max_population_density: float
    worst_case_lat: float
    worst_case_lon: float
    nearest_city: str
    nearest_city_km: float
    per_impact_casualties: np.ndarray = field(default_factory=lambda: np.zeros(0))
    provenance: str = ""
    threshold: float = 1e-4

    @property
    def passes_threshold(self) -> bool:
        """True if E_c is within the 1-in-10 000 limit used for controlled re-entry."""
        return self.expected_casualties <= self.threshold

    @property
    def risk_band(self) -> str:
        ec = self.expected_casualties
        if ec <= 1e-6:
            return "NEGLIGIBLE"
        if ec <= 1e-4:
            return "ACCEPTABLE"
        if ec <= 1e-2:
            return "ELEVATED"
        if ec <= 1.0:
            return "HIGH"
        return "SEVERE"

    def summary(self) -> dict:
        return {
            "expected_casualties": self.expected_casualties,
            "risk_band": self.risk_band,
            "passes_1e-4_threshold": self.passes_threshold,
            "n_impacts": self.n_impacts,
            "n_casualty_capable": self.n_casualty_capable,
            "casualty_area_m2": self.casualty_area_total,
            "land_impact_probability": self.land_impact_probability,
            "ocean_impact_probability": self.ocean_impact_probability,
            "mean_pop_density_km2": self.mean_population_density,
            "max_pop_density_km2": self.max_population_density,
            "worst_case_lat": self.worst_case_lat,
            "worst_case_lon": self.worst_case_lon,
            "nearest_city": self.nearest_city,
            "nearest_city_km": self.nearest_city_km,
            "population_provenance": self.provenance,
        }


def casualty_area(debris_area_m2) -> np.ndarray:
    """
    Debris casualty area [m^2]:  ``(sqrt(A_debris) + sqrt(A_person))^2``.

    A fragment is dangerous over a bigger patch than its own footprint, because a person
    standing anywhere within roughly their own body radius of the impact is at risk.
    """
    a = np.maximum(np.asarray(debris_area_m2, dtype=float), 0.0)
    return (np.sqrt(a) + math.sqrt(PERSON_AREA)) ** 2


def assess_footprint(
    footprint: Footprint,
    population: PopulationModel | None = None,
    *,
    ke_threshold: float = CASUALTY_KE_THRESHOLD,
    threshold: float = 1e-4,
    fragment_areas=None,
    weight_per_sample: float | None = None,
) -> RiskAssessment:
    """
    Expected casualties from a Monte Carlo footprint.

    Each impact sample is one equally-likely realisation, so it carries probability
    ``1 / n_requested`` - note the denominator: fragments that *demised* correctly
    contribute zero rather than being renormalised away, which would inflate the risk of a
    re-entry that mostly burns up.

    Parameters
    ----------
    fragment_areas:
        Physical cross-sections [m^2] per impact, for the casualty-area term.  Defaults to
        an area inferred from each sample's impact mass and ballistic coefficient.
    weight_per_sample:
        Override the per-sample probability weight.  Use when samples are not equally
        likely (importance sampling).
    """
    pop = population or SyntheticPopulationModel()
    n_imp = footprint.n_impacted
    if n_imp == 0:
        return RiskAssessment(0.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, float("nan"),
                              float("nan"), "n/a", float("nan"),
                              provenance=pop.provenance, threshold=threshold)

    lat, lon = footprint.latitude, footprint.longitude
    dens = np.asarray(pop.density(lat, lon), dtype=float)
    land = np.asarray(pop.land_fraction(lat, lon), dtype=float)

    if fragment_areas is None:
        # A = m / (B * Cd); Cd is folded into B, so A ~ m / B with Cd ~ 1 as the estimator.
        bc = np.maximum(footprint.ballistic_coefficient, 1e-6)
        areas = np.maximum(footprint.impact_mass, 0.0) / bc
    else:
        areas = np.broadcast_to(np.asarray(fragment_areas, dtype=float), lat.shape)

    a_c = casualty_area(areas)
    lethal = footprint.impact_energy >= ke_threshold

    w = (1.0 / max(footprint.n_requested, 1)) if weight_per_sample is None else weight_per_sample
    # people/km^2 * m^2 * (1e-6 km^2/m^2) -> expected people struck
    per_impact = np.where(lethal, w * dens * a_c * 1e-6, 0.0)

    worst = int(np.argmax(dens))
    city, city_km, _pop = (
        pop.nearest_metro(float(lat[worst]), float(lon[worst]))
        if isinstance(pop, SyntheticPopulationModel) else ("n/a", float("nan"), 0.0)
    )

    return RiskAssessment(
        expected_casualties=float(per_impact.sum()),
        casualty_area_total=float(a_c[lethal].sum()),
        n_casualty_capable=int(lethal.sum()),
        n_impacts=n_imp,
        land_impact_probability=float(np.mean(land)),
        ocean_impact_probability=float(np.mean(1.0 - land)),
        mean_population_density=float(np.mean(dens)),
        max_population_density=float(np.max(dens)),
        worst_case_lat=float(lat[worst]),
        worst_case_lon=float(lon[worst]),
        nearest_city=city,
        nearest_city_km=city_km,
        per_impact_casualties=per_impact,
        provenance=pop.provenance,
        threshold=threshold,
    )


def zone_population(zone: ConformalZone, footprint: Footprint,
                    population: PopulationModel | None = None,
                    grid_points: int = 90) -> dict:
    """
    Population exposed inside a conformal prediction zone.

    Integrates density over the zone by sampling its bounding box in the local
    downrange/crossrange frame and keeping the cells the zone actually contains - which is
    why :meth:`ConformalZone.contains` exists as a score test rather than a polygon.

    This is the number to brief: "the 95 % zone covers 41 000 km^2 containing 2.3 million
    people" is a far more useful statement than a bare ellipse area.
    """
    pop = population or SyntheticPopulationModel()
    if not np.isfinite(zone.threshold) or footprint.n_impacted == 0:
        return {"area_km2": float("nan"), "population": float("nan"),
                "mean_density": float("nan"), "provenance": pop.provenance}

    d, c = footprint.downrange, footprint.crossrange
    pad = 0.35
    dspan = max(d.max() - d.min(), 1e3) * (1 + pad)
    cspan = max(c.max() - c.min(), 1e3) * (1 + pad)
    dg = np.linspace(d.mean() - dspan, d.mean() + dspan, grid_points)
    cg = np.linspace(c.mean() - cspan, c.mean() + cspan, grid_points)
    DD, CC = np.meshgrid(dg, cg, indexing="ij")
    inside = zone.contains(DD.ravel(), CC.ravel())
    if not np.any(inside):
        return {"area_km2": 0.0, "population": 0.0, "mean_density": 0.0,
                "provenance": pop.provenance}

    lat, lon = footprint.local_to_geodetic(DD.ravel()[inside], CC.ravel()[inside])
    dens = np.asarray(pop.density(lat, lon), dtype=float)
    cell_km2 = abs((dg[1] - dg[0]) * (cg[1] - cg[0])) / 1e6
    return {
        "area_km2": float(inside.sum() * cell_km2),
        "population": float(dens.sum() * cell_km2),
        "mean_density": float(dens.mean()),
        "max_density": float(dens.max()),
        "n_cells": int(inside.sum()),
        "provenance": pop.provenance,
    }
