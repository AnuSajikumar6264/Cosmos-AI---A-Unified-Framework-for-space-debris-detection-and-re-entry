"""
NASA Standard Breakup Model (SBM) - turning one failure into a fragment population.

This is the model NASA's EVOLVE/ORDEM debris-environment work is built on (Johnson,
Krisko, Liou & Anz-Meador, *NASA's New Breakup Model of EVOLVE 4.0*, 2001).  It is
empirical, calibrated against ground hypervelocity-impact tests and against radar
catalogues of real on-orbit explosions, and it is the standard reference for "given a
breakup, what fragments exist?".

Three sampled distributions define a cloud:

1. **Size.**  A power law in characteristic length L_c:

       explosion:  N(> L_c) = 6 * S * L_c^-1.6
       collision:  N(> L_c) = 0.1 * M^0.75 * L_c^-1.71

   S scales explosion intensity; M is the colliding mass in kg.

2. **Area-to-mass ratio.**  chi = log10(A/M) drawn from a lognormal mixture whose
   parameters slide with lambda = log10(L_c).  Above 11 cm the distribution is bimodal
   and differs between rocket bodies and spacecraft; below 8 cm it collapses to a single
   mode.  A/M is what really matters downstream, because it fixes the ballistic
   coefficient and therefore where the fragment lands.

3. **Ejection velocity.**  log10(dv) drawn normal about ``0.2*chi + 1.85`` (explosion) or
   ``0.9*chi + 2.9`` (collision), isotropic in direction.  High-A/M fragments get the
   biggest kicks, which is what smears a footprint out.

Beyond the standard model, two things are added here because they matter for *ground*
risk rather than orbital population:

* **Aerodynamic breakup.**  A satellite coming apart under air load at ~78 km is not an
  explosion: the delta-v is metres per second, not hundreds.  ``BreakupType.AERODYNAMIC``
  scales the velocity distribution down accordingly.
* **Mass bookkeeping.**  The raw SBM does not conserve mass.  With
  ``conserve_mass=True`` fragment generation stops once the parent mass is accounted
  for, and the shortfall/overshoot is reported rather than hidden.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .drag import DragModel, area_from_characteristic_length
from .materials import TYPICAL_MASS_FRACTIONS
from .propagator import DebrisObject, StateVector


class BreakupType(str, Enum):
    """Which physical process produced the fragments."""

    EXPLOSION = "explosion"      # residual propellant / battery / COPV rupture
    COLLISION = "collision"      # hypervelocity impact
    AERODYNAMIC = "aerodynamic"  # structural failure under re-entry air loads


class ParentType(str, Enum):
    """SBM area-to-mass branch: rocket bodies and spacecraft fragment differently."""

    ROCKET_BODY = "rocket_body"
    SPACECRAFT = "spacecraft"


# --------------------------------------------------------------------- SBM A/M profiles
def _ramp(lam, lo_x, lo_y, hi_x, hi_y):
    """Piecewise-linear ramp: constant ``lo_y`` below ``lo_x``, ``hi_y`` above ``hi_x``."""
    lam = np.asarray(lam, dtype=float)
    t = np.clip((lam - lo_x) / (hi_x - lo_x), 0.0, 1.0)
    return lo_y + t * (hi_y - lo_y)


def _am_params_large(lam, parent: ParentType):
    """Bimodal lognormal parameters (alpha, mu1, s1, mu2, s2) for L_c > 11 cm."""
    if parent is ParentType.ROCKET_BODY:
        alpha = _ramp(lam, -1.4, 1.0, 0.0, 0.5)
        mu1 = _ramp(lam, -0.5, -0.45, 0.0, -0.9)
        s1 = np.full_like(np.asarray(lam, dtype=float), 0.55)
        mu2 = np.full_like(np.asarray(lam, dtype=float), -0.9)
        s2 = _ramp(lam, -1.0, 0.28, 0.1, 0.1)
    else:
        alpha = _ramp(lam, -1.95, 0.0, 0.55, 1.0)
        mu1 = _ramp(lam, -1.1, -0.6, 0.0, -0.95)
        s1 = _ramp(lam, -1.3, 0.1, -0.3, 0.3)
        mu2 = _ramp(lam, -0.7, -1.2, -0.1, -2.0)
        s2 = _ramp(lam, -0.5, 0.5, -0.3, 0.3)
    return alpha, mu1, s1, mu2, s2


def _am_params_small(lam):
    """Single lognormal parameters (mu, sigma) for L_c < 8 cm ("small object class")."""
    mu = _ramp(lam, -1.75, -0.3, -1.25, -1.0)
    sigma = np.where(
        np.asarray(lam, dtype=float) <= -3.5, 0.2, 0.2 + 0.1333 * (np.asarray(lam, float) + 3.5)
    )
    return mu, np.maximum(sigma, 0.05)


def sample_area_to_mass(lc, parent: ParentType, rng: np.random.Generator):
    """
    Sample A/M [m^2/kg] for each characteristic length in ``lc``.

    Implements the SBM's three regimes with a random pick in the 8-11 cm overlap band,
    which is how the model is normally applied (the two branches are not defined to meet
    continuously there).
    """
    lc = np.atleast_1d(np.asarray(lc, dtype=float))
    lam = np.log10(np.maximum(lc, 1e-6))

    alpha, mu1, s1, mu2, s2 = _am_params_large(lam, parent)
    pick_second = rng.random(lc.shape) > alpha
    chi_large = np.where(
        pick_second, rng.normal(mu2, s2), rng.normal(mu1, s1)
    )

    mu_s, sig_s = _am_params_small(lam)
    chi_small = rng.normal(mu_s, sig_s)

    use_large = lc > 0.11
    use_small = lc < 0.08
    coin = rng.random(lc.shape) < 0.5  # overlap band: 50/50 between the two branches
    chi = np.where(use_large, chi_large, np.where(use_small, chi_small,
                                                 np.where(coin, chi_large, chi_small)))
    # Clip to a physically sensible band: denser than solid tungsten on one end, thinner
    # than a few microns of foil on the other, are both model artefacts.
    return np.clip(10.0**chi, 1e-4, 100.0)


def sample_delta_v(area_to_mass, breakup: BreakupType, rng: np.random.Generator,
                   scale: float = 1.0):
    """
    Sample ejection speed [m/s] for each fragment, per the SBM velocity distribution.

    ``scale`` multiplies the result; the aerodynamic case additionally uses a much lower
    intercept because breaking up under air load imparts far less energy than a rupture.
    """
    chi = np.log10(np.maximum(np.asarray(area_to_mass, dtype=float), 1e-9))
    if breakup is BreakupType.COLLISION:
        mu, sigma = 0.9 * chi + 2.9, 0.4
    elif breakup is BreakupType.AERODYNAMIC:
        # Empirically-tuned low-energy analogue: metres per second, not hundreds.
        mu, sigma = 0.2 * chi + 0.6, 0.35
    else:
        mu, sigma = 0.2 * chi + 1.85, 0.4
    return np.maximum(10.0 ** rng.normal(mu, sigma), 0.0) * float(scale)


def cumulative_fragment_count(lc, breakup: BreakupType, mass: float = 1000.0,
                              scaling: float = 1.0):
    """
    ``N(> lc)``: expected number of fragments larger than ``lc`` [m].

    This is the raw SBM power law, useful for plotting the size distribution against the
    sampled population as a validation check.
    """
    lc = np.asarray(lc, dtype=float)
    if breakup is BreakupType.COLLISION:
        return 0.1 * max(mass, 1e-9) ** 0.75 * lc**-1.71
    return 6.0 * scaling * lc**-1.6


# ------------------------------------------------------------------------ shape/material
def _assign_shape(area_to_mass, lc):
    """
    Pick a drag geometry from A/M.

    High A/M means thin: a sheet of solar-array substrate or insulation.  Low A/M means
    compact: a machined fitting or a tank stub.  The SBM gives no shape information, so
    this is a documented heuristic - but it is the right *kind* of correlation, and it
    only modulates C_D by a factor under two.
    """
    shapes = np.where(area_to_mass > 0.5, "flat_plate",
                      np.where(area_to_mass > 0.05, "tumbling", "cylinder"))
    return [DragModel(str(s), reference_length=float(max(l, 1e-3)))
            for s, l in zip(shapes, lc)]


def _assign_materials(n: int, rng: np.random.Generator):
    """Draw per-fragment materials from a representative bus/stage mass breakdown."""
    keys = list(TYPICAL_MASS_FRACTIONS)
    probs = np.array([TYPICAL_MASS_FRACTIONS[k] for k in keys], dtype=float)
    probs = probs / probs.sum()
    return [keys[i] for i in rng.choice(len(keys), size=n, p=probs)]


# ================================================================================= cloud
@dataclass
class DebrisCloud:
    """
    A generated fragment population, ready to hand to the propagator.

    ``delta_v`` is the per-fragment ejection velocity in ECEF components, already
    isotropically oriented, so ``state.v + delta_v[i]`` is fragment *i*'s initial
    velocity.
    """

    objects: list[DebrisObject]
    delta_v: np.ndarray                       # (N, 3) ECEF [m/s]
    breakup_state: StateVector
    breakup_type: BreakupType
    parent_type: ParentType
    parent_mass: float
    mass_accounted: float                     # total fragment mass generated [kg]
    truncated: bool = False                   # generation stopped on the mass budget
    metadata: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.objects)

    @property
    def characteristic_lengths(self) -> np.ndarray:
        return np.array([o.characteristic_length for o in self.objects])

    @property
    def masses(self) -> np.ndarray:
        return np.array([o.mass for o in self.objects])

    @property
    def areas(self) -> np.ndarray:
        return np.array([o.area for o in self.objects])

    @property
    def area_to_mass(self) -> np.ndarray:
        return np.array([o.area_to_mass for o in self.objects])

    @property
    def ballistic_coefficients(self) -> np.ndarray:
        return np.array([o.ballistic_coefficient() for o in self.objects])

    @property
    def delta_v_magnitude(self) -> np.ndarray:
        return np.linalg.norm(self.delta_v, axis=1)

    @property
    def mass_closure(self) -> float:
        """Generated mass as a fraction of the parent mass. 1.0 is perfect closure."""
        return self.mass_accounted / max(self.parent_mass, 1e-9)

    def initial_states(self) -> tuple[np.ndarray, np.ndarray]:
        """``(r0, v0)`` arrays of shape (N, 3) for :func:`~debris.propagator.propagate_ensemble`."""
        r0 = np.tile(self.breakup_state.r, (len(self), 1))
        v0 = self.breakup_state.v[None, :] + self.delta_v
        return r0, v0

    def summary(self) -> dict:
        lc = self.characteristic_lengths
        m = self.masses
        bc = self.ballistic_coefficients
        return {
            "n_fragments": len(self),
            "breakup_type": self.breakup_type.value,
            "parent_type": self.parent_type.value,
            "parent_mass_kg": self.parent_mass,
            "mass_accounted_kg": self.mass_accounted,
            "mass_closure": self.mass_closure,
            "truncated": self.truncated,
            "lc_min_cm": 100.0 * lc.min() if len(lc) else float("nan"),
            "lc_max_cm": 100.0 * lc.max() if len(lc) else float("nan"),
            "mass_median_kg": float(np.median(m)) if len(m) else float("nan"),
            "bc_min": float(bc.min()) if len(bc) else float("nan"),
            "bc_max": float(bc.max()) if len(bc) else float("nan"),
            "dv_median_ms": float(np.median(self.delta_v_magnitude)) if len(self) else float("nan"),
        }


def generate_debris_cloud(
    state: StateVector,
    parent_mass: float,
    *,
    breakup: BreakupType = BreakupType.AERODYNAMIC,
    parent: ParentType = ParentType.SPACECRAFT,
    lc_min: float = 0.05,
    lc_max: float = 2.0,
    scaling: float = 1.0,
    max_fragments: int = 400,
    delta_v_scale: float = 1.0,
    conserve_mass: bool = True,
    add_remnant: bool = True,
    n_remnants: int = 3,
    rng: np.random.Generator | int | None = None,
) -> DebrisCloud:
    """
    Sample a fragment population from a breakup at ``state``.

    Parameters
    ----------
    parent_mass:
        Mass of the object that broke up [kg].  Sets the collision size distribution and
        the mass budget when ``conserve_mass`` is on.
    lc_min, lc_max:
        Characteristic-length range to sample [m].  ``lc_min`` matters: the power law
        diverges as L_c -> 0, so the count is only meaningful relative to a stated
        smallest size.  5 cm is a sensible floor for ground-risk work because anything
        smaller carries too little energy to be casualty-causing.
    max_fragments:
        Hard cap, since ``N(>5 cm)`` for an energetic explosion runs into the thousands
        and each fragment costs a propagation.  When the cap bites, the *largest*
        fragments are kept - they are the ones that survive to the ground and dominate
        risk - and this is recorded in ``metadata``.
    conserve_mass:
        Stop generating once cumulative fragment mass reaches ``parent_mass``.
    add_remnant:
        Assign any unaccounted parent mass to a small number of large, compact
        **remnant** bodies.  This matters more than anything else in the function for
        ground risk: the SBM's size distribution, sampled over a metre-scale band,
        typically accounts for only 10-20 % of a satellite's mass, yet the missing mass in
        reality sits in a handful of big pieces - a propulsion module, a tank, an optical
        bench - and those are precisely the objects that survive re-entry and arrive with
        megajoules of energy.  Dropping them would make the risk numbers look far better
        than they are.
    """
    rng = np.random.default_rng(rng)
    lc_min = max(float(lc_min), 1e-4)
    lc_max = max(float(lc_max), lc_min * 1.001)

    # Expected count in the sampled band, from the SBM power law.
    n_expected = float(
        cumulative_fragment_count(lc_min, breakup, parent_mass, scaling)
        - cumulative_fragment_count(lc_max, breakup, parent_mass, scaling)
    )
    n_expected = max(n_expected, 1.0)
    n_draw = int(min(n_expected, max_fragments * 4))  # oversample, then cap by size/mass

    # Inverse-CDF sample of the truncated power law N(>Lc) ~ Lc^-b  =>  pdf ~ Lc^-(b+1).
    b = 1.71 if breakup is BreakupType.COLLISION else 1.6
    u = rng.random(n_draw)
    a_lo, a_hi = lc_min**-b, lc_max**-b
    lc = (a_lo + u * (a_hi - a_lo)) ** (-1.0 / b)

    am = sample_area_to_mass(lc, parent, rng)
    area = np.asarray(area_from_characteristic_length(lc), dtype=float)
    mass = area / am

    # Largest first: if anything has to be dropped, drop the pieces that would have
    # demised or been harmless anyway.
    order = np.argsort(-mass)
    lc, am, area, mass = lc[order], am[order], area[order], mass[order]

    truncated = False
    keep = len(lc)
    if conserve_mass:
        cum = np.cumsum(mass)
        over = np.flatnonzero(cum > parent_mass)
        if over.size:
            keep = int(over[0])  # last fragment that still fits the budget
            truncated = True
    keep = max(min(keep, max_fragments), 1)
    if keep < len(lc):
        truncated = True
    lc, am, area, mass = lc[:keep], am[:keep], area[:keep], mass[:keep]

    dv_mag = sample_delta_v(am, breakup, rng, delta_v_scale)
    # Isotropic directions via normalised Gaussians (uniform on the sphere).
    dirs = rng.normal(size=(keep, 3))
    dirs /= np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-12)
    delta_v = dirs * dv_mag[:, None]

    drags = _assign_shape(am, lc)
    materials = _assign_materials(keep, rng)
    objects = [
        DebrisObject(
            name=f"frag{i:03d}",
            mass=float(mass[i]),
            area=float(area[i]),
            drag=drags[i],
            material=materials[i],
            origin="fragment",
        )
        for i in range(keep)
    ]

    # ------------------------------------------------------------------ parent remnants
    n_rem = 0
    remnant_mass = max(float(parent_mass) - float(mass.sum()), 0.0)
    if add_remnant and remnant_mass > 0.01 * parent_mass and n_remnants > 0:
        n_rem = int(n_remnants)
        # Split the balance unevenly (Dirichlet), so there is one dominant survivor rather
        # than n identical ones - which is what post-flight debris recoveries look like.
        shares = rng.dirichlet(np.full(n_rem, 1.5))
        rem_mass = remnant_mass * shares
        # Compact bodies: A/M an order of magnitude below the fragment population, and
        # made of the alloys that actually survive.
        rem_am = 10.0 ** rng.uniform(-2.4, -1.6, n_rem)
        rem_area = rem_mass * rem_am
        rem_mat = list(rng.choice(
            ["titanium", "stainless_steel", "inconel", "cfrp"], size=n_rem,
            p=[0.35, 0.35, 0.15, 0.15],
        ))
        rem_dv = sample_delta_v(rem_am, breakup, rng, delta_v_scale * 0.4)
        rem_dirs = rng.normal(size=(n_rem, 3))
        rem_dirs /= np.maximum(np.linalg.norm(rem_dirs, axis=1, keepdims=True), 1e-12)

        for i in range(n_rem):
            objects.append(
                DebrisObject(
                    name=f"remnant{i:02d}",
                    mass=float(rem_mass[i]),
                    area=float(rem_area[i]),
                    drag=DragModel("box", reference_length=float(np.sqrt(rem_area[i]))),
                    material=str(rem_mat[i]),
                    origin="remnant",
                )
            )
        delta_v = np.vstack([delta_v, rem_dirs * rem_dv[:, None]])
        mass = np.concatenate([mass, rem_mass])

    return DebrisCloud(
        objects=objects,
        delta_v=delta_v,
        breakup_state=state,
        breakup_type=breakup,
        parent_type=parent,
        parent_mass=float(parent_mass),
        mass_accounted=float(mass.sum()),
        truncated=truncated,
        metadata={
            "n_expected_sbm": n_expected,
            "n_drawn": n_draw,
            "n_kept": keep,
            "n_remnants": n_rem,
            "remnant_mass_kg": remnant_mass if n_rem else 0.0,
            "lc_min_m": lc_min,
            "lc_max_m": lc_max,
            "scaling": scaling,
            "delta_v_scale": delta_v_scale,
        },
    )


def size_distribution_check(cloud: DebrisCloud, n_bins: int = 24):
    """
    Compare the sampled population against the analytic SBM power law.

    Returns ``(lc_edges, n_sampled_cumulative, n_analytic_cumulative)``.  A generated
    cloud should track the analytic curve in slope; the offset reflects the mass-budget
    truncation and the fragment cap, both of which are deliberate.
    """
    lc = cloud.characteristic_lengths
    if not len(lc):
        return np.zeros(0), np.zeros(0), np.zeros(0)
    edges = np.logspace(
        math.log10(cloud.metadata["lc_min_m"]), math.log10(cloud.metadata["lc_max_m"]), n_bins
    )
    sampled = np.array([np.count_nonzero(lc >= e) for e in edges], dtype=float)
    analytic = cumulative_fragment_count(
        edges, cloud.breakup_type, cloud.parent_mass, cloud.metadata["scaling"]
    ) - cumulative_fragment_count(
        cloud.metadata["lc_max_m"], cloud.breakup_type, cloud.parent_mass,
        cloud.metadata["scaling"],
    )
    return edges, sampled, analytic
