"""
Kessler cascade risk engine.

A breakup has two consequences, and the dramatic one is not the ground risk.  Fragments
that *stay in orbit* raise the collision rate for everything sharing their altitude; if
each collision produces more debris than atmospheric drag removes, the population runs
away.  That is the Kessler syndrome, and whether a given altitude shell is on the stable
or unstable side of it is a computable question.

The model
---------
Particle-in-a-box (gas-kinetic) collision theory per altitude shell.  For a target of
cross-section ``A`` moving through a spatial density ``n`` of debris at mean relative
speed ``v_rel``, the collision rate is

    R = n * A * v_rel                                       [collisions / time]

and for the shell population as a whole, counting pairs,

    R_shell = 0.5 * N^2 * sigma_bar * v_rel / V              [collisions / time]

**Two species, not one.**  Each shell tracks intact objects (satellites and rocket
bodies, ~500 kg, ~4 m^2) separately from trackable fragments (~0.5 kg, ~0.01 m^2).  This is
the difference between a credible model and a useless one.  Collapsing them forces the ~900
fragments produced by a collision to inherit the mass and cross-section of the satellites
that made them, inflating their collision cross-section by two orders of magnitude and
their secondary yield by nearly three; run 200 years forward, that compounds into a
predicted population growth of several hundred times, against the factor of ~1.5-3 that
published multi-species studies find.  Fragments also have higher A/M, so drag clears them
faster - a stabilising effect a single-species model structurally cannot express.

Population evolution per shell, with ``R_xy`` the catastrophic collision rates and ``n_xy``
the NASA-breakup-model fragment yields (the same model :mod:`debris.fragmentation` uses, so
the two stay consistent)::

    dNi/dt = S  -  Ni/tau_i  -  (2*R_ii + R_if)
    dNf/dt =     -  Nf/tau_f  +  n_ii*R_ii + n_if*R_if + n_ff*R_ff  -  (R_if + 2*R_ff)

Whether a pairing counts as catastrophic is decided by the standard 40 J/g specific-energy
threshold rather than assumed.  At 10 km/s a 0.5 kg fragment carries 25 MJ, which destroys a
500 kg satellite outright - which is exactly why the *fragment* population drives a cascade.

The headline number is

    criticality = (collisional fragment production) / (drag removal)

At or above 1.0 a shell grows with no further launches.  This ratio is used in preference to
a single-species ``N / N_crit`` formula because it is well defined for a multi-species
population and because it states the question directly.

What this is not
----------------
This is an *aggregate* model.  It does not propagate individual orbits, screen
conjunctions, or resolve inclination bands - all of which matter for whether two specific
objects will actually meet.  Real conjunction assessment needs a TLE catalogue and a
covariance-based probability-of-collision calculation.  What an aggregate model is good
for is exactly the question asked here: does this breakup move this shell materially
toward instability, and by how much?  Spatial densities and lifetimes below are
representative published figures, not a live catalogue.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .constants import EARTH_MU, WGS84_A

# --------------------------------------------------------- LEO debris environment tables
# Spatial density of trackable (>10 cm) objects, per km^3, against altitude [km].
# Representative of published ORDEM/MASTER-class profiles: a strong peak near 800 km from
# decades of accumulated rocket bodies and breakups, a second bump near 1400 km.
_ALT_KM = np.array([200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300,
                    1400, 1500, 1700, 2000], dtype=float)
_SPATIAL_DENSITY = np.array([1.0e-10, 3.0e-10, 2.0e-9, 6.0e-9, 1.2e-8, 2.0e-8, 3.0e-8,
                             2.4e-8, 1.4e-8, 9.0e-9, 8.0e-9, 7.0e-9, 9.0e-9, 6.0e-9,
                             3.0e-9, 1.0e-9], dtype=float)

# Ballistic orbital lifetime [years] for a typical A/M ~ 0.01 m^2/kg object.  Spans nine
# orders of magnitude across LEO, which is the whole reason altitude matters so much.
_LIFETIME_YEARS = np.array([0.01, 0.1, 1.0, 10.0, 28.0, 100.0, 300.0, 1_000.0, 2_000.0,
                            5_000.0, 1.0e4, 2.0e4, 3.0e4, 5.0e4, 1.0e5, 2.0e5], dtype=float)

#: Mean relative speed of a random LEO encounter [m/s].  Roughly 10 km/s once inclination
#: and node distributions are averaged over; the classic value used in cascade studies.
MEAN_RELATIVE_SPEED = 10_000.0



def spatial_density(altitude_km):
    """Trackable-object spatial density [1/km^3] at an altitude [km]. Log-interpolated."""
    a = np.asarray(altitude_km, dtype=float)
    return np.exp(np.interp(a, _ALT_KM, np.log(_SPATIAL_DENSITY)))


def orbital_lifetime(altitude_km, area_to_mass: float = 0.01):
    """
    Ballistic orbital lifetime [years].

    Scaled inversely with A/M from the tabulated 0.01 m^2/kg reference, since drag decay
    is proportional to the area-to-mass ratio to first order.
    """
    a = np.asarray(altitude_km, dtype=float)
    base = np.exp(np.interp(a, _ALT_KM, np.log(_LIFETIME_YEARS)))
    return base * (0.01 / max(float(area_to_mass), 1e-6))


def shell_volume(alt_low_km: float, alt_high_km: float) -> float:
    """Volume of a spherical shell between two altitudes [km^3]."""
    r1 = (WGS84_A / 1000.0) + float(alt_low_km)
    r2 = (WGS84_A / 1000.0) + float(alt_high_km)
    return (4.0 / 3.0) * math.pi * (r2**3 - r1**3)


def orbital_period(altitude_km: float) -> float:
    """Circular orbital period [s]."""
    r = WGS84_A + float(altitude_km) * 1000.0
    return 2.0 * math.pi * math.sqrt(r**3 / EARTH_MU)


def fragments_per_collision(mass_kg: float, lc_min: float = 0.10) -> float:
    """
    Trackable fragments from one catastrophic collision, from the NASA breakup model:
    ``N(>Lc) = 0.1 * M^0.75 * Lc^-1.71``.

    Uses the *combined* mass of both objects, which is what the model is defined on.
    """
    return float(0.1 * max(mass_kg, 1e-9) ** 0.75 * max(lc_min, 1e-3) ** -1.71)

# =============================================================================== shells
@dataclass(frozen=True)
class Species:
    """
    One population class within a shell.

    Splitting intact objects from fragments is not cosmetic.  A single-species model has to
    give the ~900 fragments produced by a collision the same mass and cross-section as the
    satellites that produced them, which overstates their collision cross-section by two
    orders of magnitude and their secondary-fragment yield by nearly three.  Run forward
    200 years, that error compounds into a predicted population growth of several hundred
    times, against the factor of ~1.5-3 that published multi-species studies find.
    """

    name: str
    mass: float          # [kg]
    area: float          # cross-section [m^2]

    @property
    def radius(self) -> float:
        """Effective radius [m] of an equivalent circular cross-section."""
        return math.sqrt(max(self.area, 1e-12) / math.pi)

    @property
    def area_to_mass(self) -> float:
        return self.area / max(self.mass, 1e-12)


#: Intact satellites and rocket bodies.
INTACT = Species("intact", 500.0, 4.0)
#: Trackable fragments (>10 cm).  Higher A/M than an intact object, so drag clears them
#: appreciably faster - a stabilising effect a single-species model cannot represent.
FRAGMENT = Species("fragment", 0.5, 0.01)

#: Specific energy above which a collision is catastrophic (fully fragments the target).
#: The standard 40 J/g threshold.
CATASTROPHIC_SPECIFIC_ENERGY = 40_000.0  # [J/kg]


def is_catastrophic(projectile: Species, target: Species,
                    v_rel: float = MEAN_RELATIVE_SPEED) -> bool:
    """
    Whether ``projectile`` striking ``target`` at ``v_rel`` is catastrophic.

    ``0.5 * m_p * v^2 / m_t >= 40 kJ/kg``.  At 10 km/s a 0.5 kg fragment carries 25 MJ,
    enough to destroy a 500 kg satellite outright - which is precisely why the fragment
    population, not the intact population, drives a cascade.
    """
    return (0.5 * projectile.mass * v_rel**2) / max(target.mass, 1e-12) >= CATASTROPHIC_SPECIFIC_ENERGY


@dataclass
class OrbitalShell:
    """
    One altitude band with a two-species population.

    ``n_intact`` counts satellites and rocket bodies; ``n_fragment`` counts trackable
    debris.  Each species has its own drag lifetime, because lifetime scales with A/M.
    """

    alt_low: float                  # [km]
    alt_high: float                 # [km]
    n_intact: int = 0
    n_fragment: int = 0
    intact: Species = INTACT
    fragment: Species = FRAGMENT

    @classmethod
    def from_total(cls, alt_low: float, alt_high: float, n_total: int,
                   intact_fraction: float = 0.20, **kw) -> "OrbitalShell":
        """
        Split a catalogue count into species.

        ~20 % intact is representative of the tracked LEO catalogue: a few thousand
        satellites and spent stages against roughly four times as many fragments.
        """
        n_i = int(round(n_total * float(intact_fraction)))
        return cls(alt_low, alt_high, n_i, max(int(n_total) - n_i, 0), **kw)

    # -------------------------------------------------------------------- geometry
    @property
    def alt_mid(self) -> float:
        return 0.5 * (self.alt_low + self.alt_high)

    @property
    def volume(self) -> float:
        """[km^3]"""
        return shell_volume(self.alt_low, self.alt_high)

    @property
    def n_objects(self) -> int:
        return int(self.n_intact) + int(self.n_fragment)

    @property
    def total_mass(self) -> float:
        """Total mass in the shell [kg] - the conserved quantity that bounds a cascade."""
        return self.n_intact * self.intact.mass + self.n_fragment * self.fragment.mass

    @property
    def spatial_density_modelled(self) -> float:
        """Population-derived spatial density [1/km^3] (compare with the table)."""
        return self.n_objects / max(self.volume, 1e-9)

    def lifetime(self, species: Species | None = None) -> float:
        """Drag removal time constant [years] for a species (default: intact)."""
        sp = species or self.intact
        return float(orbital_lifetime(self.alt_mid, sp.area_to_mass))

    # ------------------------------------------------------------------ collisions
    def cross_section(self, a: Species, b: Species) -> float:
        """Pairwise collision cross-section [km^2]:  pi * (r_a + r_b)^2."""
        return math.pi * (a.radius + b.radius) ** 2 * 1e-6

    def _v_rel_km_per_year(self) -> float:
        return MEAN_RELATIVE_SPEED * 1e-3 * 3.15576e7

    def collision_rates(self) -> dict[str, float]:
        """
        Catastrophic collision rates per year for each species pairing.

        Pair counting: like-with-like carries the 1/2, cross terms do not.
        """
        v = self._v_rel_km_per_year()
        V = max(self.volume, 1e-30)
        ni, nf = float(self.n_intact), float(self.n_fragment)
        r = {
            "ii": 0.5 * ni * max(ni - 1.0, 0.0) * self.cross_section(self.intact, self.intact) * v / V,
            "if": ni * nf * self.cross_section(self.intact, self.fragment) * v / V,
            "ff": 0.5 * nf * max(nf - 1.0, 0.0) * self.cross_section(self.fragment, self.fragment) * v / V,
        }
        # Zero out any pairing that cannot reach the catastrophic energy threshold.
        if not is_catastrophic(self.intact, self.intact):
            r["ii"] = 0.0
        if not is_catastrophic(self.fragment, self.intact):
            r["if"] = 0.0
        if not is_catastrophic(self.fragment, self.fragment):
            r["ff"] = 0.0
        return r

    def collision_rate(self) -> float:
        """Total catastrophic collision rate in the shell [collisions/year]."""
        return sum(self.collision_rates().values())

    def fragment_yields(self, lc_min: float = 0.10) -> dict[str, float]:
        """Trackable fragments produced per collision, per pairing, from the NASA SBM."""
        mi, mf = self.intact.mass, self.fragment.mass
        return {
            "ii": fragments_per_collision(2.0 * mi, lc_min),
            "if": fragments_per_collision(mi + mf, lc_min),
            "ff": fragments_per_collision(2.0 * mf, lc_min),
        }

    def _rates_for(self, ni: float, nf: float) -> tuple[float, float, float]:
        """
        ``(collision_rate, fragment_production, removal)`` for arbitrary float populations.

        Factored out so :meth:`critical_scale_factor` can search over continuous
        populations; rounding to integers there made a scaled-down shell read as empty.
        """
        v = self._v_rel_km_per_year()
        V = max(self.volume, 1e-30)
        r_ii = (0.5 * ni * max(ni - 1.0, 0.0) * self.cross_section(self.intact, self.intact)
                * v / V) if is_catastrophic(self.intact, self.intact) else 0.0
        r_if = (ni * nf * self.cross_section(self.intact, self.fragment)
                * v / V) if is_catastrophic(self.fragment, self.intact) else 0.0
        r_ff = (0.5 * nf * max(nf - 1.0, 0.0) * self.cross_section(self.fragment, self.fragment)
                * v / V) if is_catastrophic(self.fragment, self.fragment) else 0.0
        y = self.fragment_yields()
        production = r_ii * y["ii"] + r_if * y["if"] + r_ff * y["ff"]
        removal = (ni / max(self.lifetime(self.intact), 1e-9)
                   + nf / max(self.lifetime(self.fragment), 1e-9))
        return r_ii + r_if + r_ff, production, removal

    def fragment_production_rate(self, lc_min: float = 0.10) -> float:
        """New trackable fragments per year from collisions [objects/year]."""
        r, y = self.collision_rates(), self.fragment_yields(lc_min)
        return sum(r[k] * y[k] for k in r)

    def removal_rate(self) -> float:
        """Objects removed per year by atmospheric drag [objects/year]."""
        return (self.n_intact / max(self.lifetime(self.intact), 1e-9)
                + self.n_fragment / max(self.lifetime(self.fragment), 1e-9))

    # ------------------------------------------------------------------- stability
    def criticality(self) -> float:
        """
        The Kessler criterion as a ratio: collisional production over drag removal.

        This is the definition used throughout, in preference to a single-species
        ``N / N_crit`` formula, because it is well defined for a multi-species population
        and because it is exactly the question that matters - is debris being created faster
        than it is being cleared?  At or above 1.0 the shell grows with no further launches.
        """
        prod, rem = self.fragment_production_rate(), self.removal_rate()
        if rem <= 0.0:
            # An empty (or fully decayed) shell produces nothing and removes nothing; that
            # is stable, not infinitely critical.
            return 0.0 if prod <= 0.0 else float("inf")
        return float(prod / rem)

    def critical_scale_factor(self, lo: float = 1e-4, hi: float = 1e4) -> float:
        """
        Factor by which this shell's population would have to be scaled to sit exactly at
        criticality 1.0.

        Below 1.0 means the shell is *already* past critical and would have to shrink.
        Found by bisection, since production is quadratic in population while removal is
        linear, so the ratio is monotone in the scale factor.
        """
        def crit(k):
            _c, prod, rem = self._rates_for(self.n_intact * k, self.n_fragment * k)
            if rem <= 0.0:
                return 0.0 if prod <= 0.0 else float("inf")
            return prod / rem

        if self.n_objects == 0:
            return float("inf")
        if crit(hi) < 1.0:
            return float("inf")
        if crit(lo) > 1.0:
            return float(lo)
        for _ in range(60):
            mid = math.sqrt(lo * hi)
            if crit(mid) < 1.0:
                lo = mid
            else:
                hi = mid
        return float(math.sqrt(lo * hi))

    def collisional_growth_time(self) -> float:
        """
        e-folding time of the population from collisions alone [years].

        The decision-relevant timescale.  The criticality ratio says *whether* a shell
        grows; this says how fast, and the two can rank shells differently because drag
        removal effectively vanishes at high altitude.
        """
        prod = self.fragment_production_rate()
        return float(self.n_objects / prod) if prod > 0 else float("inf")

    def net_growth_time(self) -> float:
        """e-folding time net of drag removal [years]; negative means shrinking."""
        net = self.fragment_production_rate() - self.removal_rate()
        return float(self.n_objects / net) if abs(net) > 1e-30 else float("inf")

    def stability(self) -> str:
        """Stability class, graded on criticality and then on growth timescale."""
        c = self.criticality()
        if c < 1.0:
            return "STABLE" if c < 0.25 else ("MARGINAL" if c < 0.75 else "NEAR-CRITICAL")
        tg = self.collisional_growth_time()
        if tg > 1_000.0:
            return "SUPERCRITICAL (slow)"
        if tg > 200.0:
            return "SUPERCRITICAL (centuries)"
        return "SUPERCRITICAL (decades)"

    def target_collision_rate(self, target_area_m2: float, use_table: bool = True) -> float:
        """
        Collision rate for *one specific* satellite in this shell [collisions/year].

        The number an operator cares about.  ``use_table=True`` uses the published
        spatial-density profile; ``False`` uses this shell's own modelled population, which
        is what you want after injecting a simulated breakup.
        """
        n = (float(spatial_density(self.alt_mid)) if use_table
             else self.spatial_density_modelled)
        return n * float(target_area_m2) * 1e-6 * self._v_rel_km_per_year()

    def summary(self) -> dict:
        return {
            "alt_low_km": self.alt_low,
            "alt_high_km": self.alt_high,
            "n_objects": self.n_objects,
            "n_intact": self.n_intact,
            "n_fragment": self.n_fragment,
            "volume_km3": self.volume,
            "lifetime_intact_years": self.lifetime(self.intact),
            "lifetime_fragment_years": self.lifetime(self.fragment),
            "spatial_density_modelled": self.spatial_density_modelled,
            "spatial_density_published": float(spatial_density(self.alt_mid)),
            "collision_rate_per_year": self.collision_rate(),
            "fragment_production_per_year": self.fragment_production_rate(),
            "removal_per_year": self.removal_rate(),
            "criticality": self.criticality(),
            "critical_scale_factor": self.critical_scale_factor(),
            "growth_time_years": self.collisional_growth_time(),
            "net_growth_time_years": self.net_growth_time(),
            "stability": self.stability(),
        }


def default_leo_shells(bin_width: float = 100.0, alt_min: float = 200.0,
                       alt_max: float = 1600.0,
                       intact_fraction: float = 0.20) -> list[OrbitalShell]:
    """
    LEO discretised into shells, populated to match the published spatial-density profile.

    Object counts are back-computed from the density table rather than invented, so the
    aggregate environment is consistent with the same source the collision rates use.
    """
    shells = []
    edges = np.arange(alt_min, alt_max + bin_width, bin_width)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mid = 0.5 * (lo + hi)
        n = int(round(float(spatial_density(mid)) * shell_volume(lo, hi)))
        shells.append(OrbitalShell.from_total(float(lo), float(hi), max(n, 0),
                                             intact_fraction))
    return shells


# ============================================================================== cascade
@dataclass
class CascadeResult:
    """Forward simulation of the two-species shell population ODEs."""

    time_years: np.ndarray
    n_intact: np.ndarray              # (n_steps+1, n_shells)
    n_fragment: np.ndarray            # (n_steps+1, n_shells)
    collision_events: np.ndarray      # cumulative catastrophic collisions per shell
    shells: list[OrbitalShell]
    criticality_initial: np.ndarray
    criticality_final: np.ndarray
    cascade_onset_year: float = float("nan")
    launch_rate: float = 0.0

    @property
    def population(self) -> np.ndarray:
        """Total objects per shell over time."""
        return self.n_intact + self.n_fragment

    @property
    def total_population(self) -> np.ndarray:
        return self.population.sum(axis=1)

    @property
    def growth_factor(self) -> float:
        p = self.total_population
        return float(p[-1] / max(p[0], 1e-9))

    @property
    def cascading(self) -> bool:
        return bool(np.isfinite(self.cascade_onset_year))

    def worst_shell(self) -> OrbitalShell:
        return self.shells[int(np.argmax(self.criticality_final))]

    def summary(self) -> dict:
        return {
            "horizon_years": float(self.time_years[-1]),
            "initial_population": int(self.total_population[0]),
            "final_population": int(self.total_population[-1]),
            "initial_intact": int(self.n_intact[0].sum()),
            "final_intact": int(self.n_intact[-1].sum()),
            "growth_factor": self.growth_factor,
            "total_collisions": float(self.collision_events[-1].sum()),
            "max_criticality_initial": float(np.max(self.criticality_initial)),
            "max_criticality_final": float(np.max(self.criticality_final)),
            "cascading": self.cascading,
            "cascade_onset_year": self.cascade_onset_year,
            "worst_shell_alt_km": self.worst_shell().alt_mid,
        }


def simulate_cascade(
    shells: list[OrbitalShell],
    years: float = 200.0,
    dt: float = 0.5,
    launch_rate: float = 0.0,
    lc_min: float = 0.10,
    onset_growth: float = 2.0,
) -> CascadeResult:
    """
    Integrate the two-species population ODEs forward.

    Per shell, with ``R_xy`` the catastrophic collision rates and ``n_xy`` the SBM fragment
    yields::

        dNi/dt = S  -  Ni/tau_i  -  (2*R_ii + R_if)
        dNf/dt =      -  Nf/tau_f  +  n_ii*R_ii + n_if*R_if + n_ff*R_ff  -  (R_if + 2*R_ff)

    Intact objects are consumed by collisions and never created except by launch; fragments
    are created by every catastrophic collision and consumed only by drag and by
    fragment-fragment collisions.

    Two numerical points, both load-bearing:

    * **Exponential-Euler on the linear decay.**  Drag lifetimes span 0.03 years at 200 km
      to 60 000 years at 1500 km.  Any explicit scheme with a step large enough to reach a
      200-year horizon is violently unstable on the low shells (``dt/tau`` of order 16).
      Solving the linear part exactly - ``N <- S*tau + (N - S*tau)*exp(-dt/tau)`` with the
      source frozen across the step - is unconditionally stable at any step size.
    * **Mass conservation bounds the fragment count.**  Collisions redistribute mass, they
      do not create it, so total shell mass can only fall (drag) or stay put.  Fragments are
      capped at the mass actually available.  Without this the quadratic source overflows,
      which is an artefact rather than a forecast.

    Fragments are deposited in the shell where the collision happened.  A real cloud spreads
    over neighbouring altitudes; keeping it local is conservative for judging that shell.
    """
    n_steps = max(int(round(float(years) / float(dt))), 1)
    t = np.arange(n_steps + 1) * float(dt)
    ns = len(shells)

    Ni = np.array([float(s.n_intact) for s in shells])
    Nf = np.array([float(s.n_fragment) for s in shells])
    vol = np.maximum(np.array([s.volume for s in shells]), 1e-30)
    tau_i = np.maximum(np.array([s.lifetime(s.intact) for s in shells]), 1e-9)
    tau_f = np.maximum(np.array([s.lifetime(s.fragment) for s in shells]), 1e-9)
    m_i = np.array([s.intact.mass for s in shells])
    m_f = np.array([s.fragment.mass for s in shells])
    v = MEAN_RELATIVE_SPEED * 1e-3 * 3.15576e7

    sig_ii = np.array([s.cross_section(s.intact, s.intact) for s in shells])
    sig_if = np.array([s.cross_section(s.intact, s.fragment) for s in shells])
    sig_ff = np.array([s.cross_section(s.fragment, s.fragment) for s in shells])
    y = {k: np.array([s.fragment_yields(lc_min)[k] for s in shells]) for k in ("ii", "if", "ff")}
    # Gates come straight from the energy criterion, so they do not depend on the current
    # population being non-zero.
    gate = {}
    gate["ii"] = np.array([1.0 if is_catastrophic(s.intact, s.intact) else 0.0 for s in shells])
    gate["if"] = np.array([1.0 if is_catastrophic(s.fragment, s.intact) else 0.0 for s in shells])
    gate["ff"] = np.array([1.0 if is_catastrophic(s.fragment, s.fragment) else 0.0 for s in shells])

    mass_budget = Ni * m_i + Nf * m_f
    per_shell_launch = float(launch_rate) / max(ns, 1)
    decay_i, decay_f = np.exp(-dt / tau_i), np.exp(-dt / tau_f)

    ni_hist = np.zeros((n_steps + 1, ns))
    nf_hist = np.zeros((n_steps + 1, ns))
    coll = np.zeros((n_steps + 1, ns))
    ni_hist[0], nf_hist[0] = Ni, Nf

    def rates(ni, nf):
        r_ii = gate["ii"] * 0.5 * ni * np.maximum(ni - 1.0, 0.0) * sig_ii * v / vol
        r_if = gate["if"] * ni * nf * sig_if * v / vol
        r_ff = gate["ff"] * 0.5 * nf * np.maximum(nf - 1.0, 0.0) * sig_ff * v / vol
        return r_ii, r_if, r_ff

    onset = float("nan")
    for k in range(n_steps):
        ni, nf = ni_hist[k], nf_hist[k]
        r_ii, r_if, r_ff = rates(ni, nf)
        # Half-step refresh of the quadratic source so it is not systematically low.
        prod0 = y["ii"] * r_ii + y["if"] * r_if + y["ff"] * r_ff
        r_ii, r_if, r_ff = rates(
            np.maximum(ni - 0.5 * dt * (2 * r_ii + r_if), 0.0),
            np.maximum(nf + 0.5 * dt * (prod0 - r_if - 2 * r_ff), 0.0),
        )
        prod = y["ii"] * r_ii + y["if"] * r_if + y["ff"] * r_ff

        src_i = per_shell_launch - (2.0 * r_ii + r_if)
        src_f = prod - (r_if + 2.0 * r_ff)

        eq_i, eq_f = src_i * tau_i, src_f * tau_f
        ni_new = np.maximum(eq_i + (ni - eq_i) * decay_i, 0.0)
        nf_new = np.maximum(eq_f + (nf - eq_f) * decay_f, 0.0)

        # Mass conservation: fragments cannot exceed the mass still present in the shell.
        mass_budget = mass_budget + per_shell_launch * dt * m_i
        avail = np.maximum(mass_budget - ni_new * m_i, 0.0)
        nf_new = np.minimum(nf_new, avail / np.maximum(m_f, 1e-12))
        mass_budget = np.minimum(mass_budget, ni_new * m_i + nf_new * m_f)

        ni_hist[k + 1], nf_hist[k + 1] = ni_new, nf_new
        coll[k + 1] = coll[k] + dt * (r_ii + r_if + r_ff)
        if not np.isfinite(onset) and launch_rate == 0.0:
            if (ni_new + nf_new).sum() > onset_growth * max((Ni + Nf).sum(), 1e-9):
                onset = float(t[k + 1])

    from dataclasses import replace as _replace

    crit0 = np.array([s.criticality() for s in shells])
    critf = np.array([
        _replace(shells[j], n_intact=int(ni_hist[-1, j]),
                 n_fragment=int(nf_hist[-1, j])).criticality() for j in range(ns)
    ])
    return CascadeResult(t, ni_hist, nf_hist, coll, shells, crit0, critf, onset,
                         float(launch_rate))


# ================================================================= breakup contribution
@dataclass
class CascadeContribution:
    """
    How much one breakup degrades an altitude shell.

    A note on which field to actually quote
    ---------------------------------------
    ``delta_criticality`` is reported for completeness but is a **poor** headline metric,
    and can even come out *negative*.  That is not a bug: criticality is a ratio of
    production to removal, and injected fragments have high A/M, so they raise drag removal
    proportionally faster than they raise production - the intact-intact collision term,
    which is over 40 % of production, does not change at all when you add fragments.

    The metric to quote is :attr:`added_collision_probability`: the probability that this
    one breakup destroys a given reference satellite at that altitude, integrated over the
    whole lifetime of the debris it created.  It is absolute rather than a ratio, strictly
    increasing in fragments added, and correctly weighted by altitude through the fragment
    drag lifetime - the same 400 fragments are about three orders of magnitude worse at
    850 km than at 350 km, and this number shows that while the ratio does not.
    """

    altitude_km: float
    fragments_added: int
    trackable_added: int
    population_before: int
    population_after: int
    criticality_before: float
    criticality_after: float
    delta_criticality: float
    production_before: float         # fragment production rate [objects/year]
    production_after: float
    collision_rate_before: float     # for a reference satellite, per year
    collision_rate_after: float
    rate_increase_pct: float
    added_collision_probability: float
    fragment_lifetime_years: float
    reference_area_m2: float
    debris_years: float              # fragment-years added before drag clears them
    stability_before: str
    stability_after: str

    def summary(self) -> dict:
        return {
            "altitude_km": self.altitude_km,
            "fragments_added": self.fragments_added,
            "trackable_added": self.trackable_added,
            "population_before": self.population_before,
            "population_after": self.population_after,
            "added_collision_probability": self.added_collision_probability,
            "fragment_lifetime_years": self.fragment_lifetime_years,
            "debris_years_added": self.debris_years,
            "production_before_per_year": self.production_before,
            "production_after_per_year": self.production_after,
            "collision_rate_before_per_year": self.collision_rate_before,
            "collision_rate_after_per_year": self.collision_rate_after,
            "rate_increase_pct": self.rate_increase_pct,
            "criticality_before": self.criticality_before,
            "criticality_after": self.criticality_after,
            "delta_criticality": self.delta_criticality,
            "stability_before": self.stability_before,
            "stability_after": self.stability_after,
        }


def breakup_contribution(
    altitude_km: float,
    n_fragments: int,
    *,
    trackable_fraction: float = 0.25,
    reference_area_m2: float = 10.0,
    shells: list[OrbitalShell] | None = None,
    fragment_area_to_mass: float = 0.05,
) -> CascadeContribution:
    """
    Effect of injecting ``n_fragments`` at ``altitude_km`` on that shell's stability.

    The headline outputs are the change in criticality and the percentage increase in
    collision rate for a reference operational satellite.  ``debris_years`` - fragments
    multiplied by their drag lifetime - is the sustainability metric: it is the quantity
    that :mod:`debris.circular_economy` charges an operator for, because it captures both
    how much debris was created and how long it will be in the way.

    Note the altitude sensitivity: the same breakup at 400 km clears in about a year, and
    at 900 km lasts a millennium.  A model that ignored lifetime would rate them equally.
    """
    shells = shells or default_leo_shells()
    idx = int(np.argmin([abs(s.alt_mid - float(altitude_km)) for s in shells]))
    shell = shells[idx]

    trackable = int(round(float(n_fragments) * float(trackable_fraction)))
    before = shell.n_objects
    after = before + trackable

    from dataclasses import replace as _replace

    # Injected debris joins the *fragment* species, not the intact one - which is the whole
    # point of separating them: fragments are small, numerous and shorter-lived.
    shell_after = _replace(shell, n_fragment=shell.n_fragment + trackable)
    rate_before = shell.target_collision_rate(reference_area_m2, use_table=False)
    rate_after = shell_after.target_collision_rate(reference_area_m2, use_table=False)

    life = float(orbital_lifetime(shell.alt_mid, fragment_area_to_mass))

    # Integrated added collision probability for one reference satellite.  The added
    # fragments decay exponentially with time constant ``life``, so the total extra
    # collision expectation is  (dn / V) * A * v_rel * life.
    v_km_yr = MEAN_RELATIVE_SPEED * 1e-3 * 3.15576e7
    added_p = (trackable / max(shell.volume, 1e-30)) * (float(reference_area_m2) * 1e-6) \
        * v_km_yr * life

    return CascadeContribution(
        altitude_km=shell.alt_mid,
        fragments_added=int(n_fragments),
        trackable_added=trackable,
        population_before=before,
        population_after=after,
        criticality_before=shell.criticality(),
        criticality_after=shell_after.criticality(),
        delta_criticality=shell_after.criticality() - shell.criticality(),
        production_before=shell.fragment_production_rate(),
        production_after=shell_after.fragment_production_rate(),
        collision_rate_before=rate_before,
        collision_rate_after=rate_after,
        rate_increase_pct=100.0 * (rate_after / max(rate_before, 1e-30) - 1.0),
        added_collision_probability=float(added_p),
        fragment_lifetime_years=life,
        reference_area_m2=float(reference_area_m2),
        debris_years=float(n_fragments) * life,
        stability_before=shell.stability(),
        stability_after=shell_after.stability(),
    )


def environment_report(shells: list[OrbitalShell] | None = None) -> list[dict]:
    """Per-shell stability table for the dashboard."""
    return [s.summary() for s in (shells or default_leo_shells())]
