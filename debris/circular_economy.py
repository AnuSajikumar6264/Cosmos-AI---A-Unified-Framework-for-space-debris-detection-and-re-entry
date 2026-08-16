"""
Circular-economy framework: costing a mission's debris legacy and choosing what to do.

Sustainability in orbit is usually discussed qualitatively.  It does not have to be.  There
is a natural physical currency:

    **debris-years** = (objects left behind) x (their orbital lifetime)

which captures both halves of the problem in one number.  A hundred fragments at 400 km
clear in about a year; the same hundred at 1400 km are in the way for five millennia.  Any
metric that counts only *how much* debris was created, and not *for how long*, rates those
as equal - and gets every altitude trade backwards.  Debris-years also composes: it adds
across objects, and it is exactly proportional to the integrated collision probability a
mission imposes on everything sharing its shell (see
:func:`debris.kessler.breakup_contribution`).

What this module does
---------------------
1. Scores a mission's baseline legacy: debris-years, post-mission-disposal compliance,
   uncontrolled-re-entry casualty risk, launch carbon, recoverable material.
2. Prices a catalogue of mitigation actions - passivation, controlled re-entry,
   design-for-demise, a deorbit kit, active removal, on-orbit refuelling, material recovery -
   each in propellant mass, cost proxy, debris-years avoided and CO2 delta.
3. Selects the best combination under a budget by exact dynamic programming, because the
   greedy answer is provably wrong when actions interact (a deorbit kit makes controlled
   re-entry cheap; design-for-demise makes it unnecessary).

Honest accounting notes
-----------------------
* Carbon figures below are per kg delivered to LEO and cover **direct propellant combustion
  only**.  They exclude soot/black-carbon radiative forcing and stratospheric ozone
  depletion, which for solid and kerosene motors can rival or exceed the CO2 term.  A launch
  is therefore *under*-charged here, and comparisons between propellant types are more
  reliable than absolute totals.
* The cost proxy is in arbitrary "cost units" scaled to be roughly comparable across actions.
  It exists so the optimiser has something to trade against, not to quote to a customer.
* Recyclability is potential, not practice: no orbital material recovery infrastructure
  exists today. Those rows describe what the mass *could* support.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .constants import EARTH_MU, WGS84_A, G0
from .kessler import breakup_contribution, orbital_lifetime
from .materials import MATERIALS, TYPICAL_MASS_FRACTIONS

# ------------------------------------------------------------------------ carbon factors
#: Direct-combustion CO2-equivalent per kg of payload delivered to LEO [kg CO2e/kg].
#: Derived from propellant mass fraction and carbon content; excludes soot and ozone effects.
LAUNCH_CARBON: dict[str, float] = {
    "kerolox": 25.0,     # RP-1 / LOX - e.g. Falcon 9, Soyuz
    "methalox": 20.0,    # CH4 / LOX - cleaner burning, less soot
    "hydrolox": 15.0,    # LH2 / LOX - no combustion CO2, but grey-hydrogen production dominates
    "solid": 60.0,       # HTPB/AP - also HCl and alumina, not counted here
    "hypergolic": 45.0,  # UDMH/N2O4 - high carbon plus severe toxicity
}

#: Post-mission disposal rules. The 25-year rule is the long-standing IADC guideline; several
#: regulators have since moved to 5 years for LEO.
DISPOSAL_RULE_YEARS = {"iadc_25_year": 25.0, "fcc_5_year": 5.0}

#: Fraction of each material's mass that is plausibly recoverable/reusable given a servicing
#: infrastructure - high for bulk structural metals, low for composites and bonded assemblies.
RECOVERABILITY: dict[str, float] = {
    "aluminium": 0.90, "aluminium_oxidised": 0.90, "titanium": 0.85,
    "stainless_steel": 0.88, "inconel": 0.80, "copper": 0.92,
    "cfrp": 0.20, "silica": 0.35, "mli": 0.05,
}


# =============================================================================== orbits
def circular_speed(altitude_km: float) -> float:
    """Circular orbital speed [m/s]."""
    return math.sqrt(EARTH_MU / (WGS84_A + float(altitude_km) * 1000.0))


def deorbit_delta_v(alt_from_km: float, alt_to_km: float = 50.0) -> float:
    """
    Delta-v [m/s] for a single burn lowering perigee from a circular orbit.

    Apogee stays at the starting altitude, perigee drops to ``alt_to_km``.  50 km is the
    conventional target for a *controlled, destructive* re-entry, since it guarantees entry on
    the first pass and so pins the impact footprint to a chosen ocean area.
    """
    r_a = WGS84_A + float(alt_from_km) * 1000.0
    r_p = WGS84_A + float(alt_to_km) * 1000.0
    if r_p >= r_a:
        return 0.0
    a = 0.5 * (r_a + r_p)
    v_circ = math.sqrt(EARTH_MU / r_a)
    v_apo = math.sqrt(EARTH_MU * (2.0 / r_a - 1.0 / a))
    return float(v_circ - v_apo)


def propellant_mass(dry_mass: float, delta_v: float, isp: float = 220.0) -> float:
    """
    Propellant [kg] for a manoeuvre, from the rocket equation.

    ``isp`` 220 s is a monopropellant hydrazine thruster; 320 s a bipropellant system.  This
    is the real cost of a deorbit burn, and it is why a mission that did not budget for
    disposal at design time usually cannot perform one later.
    """
    dv, m = float(delta_v), float(dry_mass)
    if dv <= 0:
        return 0.0
    return m * (math.exp(dv / (max(isp, 1.0) * G0)) - 1.0)


# ============================================================================== mission
@dataclass
class MissionProfile:
    """
    A mission's end-of-life situation.

    Parameters
    ----------
    dry_mass:
        Spacecraft mass at end of life [kg].
    altitude:
        Operational altitude [km].
    propellant_remaining:
        Usable propellant at end of life [kg].  The single biggest determinant of what
        disposal options exist.
    demisable_fraction:
        Fraction of dry mass that would ablate on re-entry.  "Design for demise" raises it.
    passivated:
        Whether stored energy (propellant, pressurant, batteries, momentum wheels) has been
        vented/discharged.  Un-passivated hardware is what later explodes.
    isp:
        Specific impulse of the disposal thruster [s].
    propellant_type:
        Key into :data:`LAUNCH_CARBON`, for the launch carbon term.
    launch_mass:
        Wet mass at launch [kg], for launch carbon.
    material_mix:
        Mass fractions by material.  Defaults to a representative satellite bus breakdown.
    """

    name: str = "mission"
    dry_mass: float = 1_200.0
    altitude: float = 800.0
    propellant_remaining: float = 20.0
    demisable_fraction: float = 0.55
    passivated: bool = False
    isp: float = 220.0
    propellant_type: str = "kerolox"
    launch_mass: float = 1_800.0
    area_to_mass: float = 0.008
    material_mix: dict[str, float] = field(default_factory=lambda: dict(TYPICAL_MASS_FRACTIONS))

    # --------------------------------------------------------------------- derived
    @property
    def natural_lifetime(self) -> float:
        """Years to decay naturally from the operational altitude."""
        return float(orbital_lifetime(self.altitude, self.area_to_mass))

    @property
    def available_delta_v(self) -> float:
        """Delta-v [m/s] the remaining propellant can deliver."""
        if self.propellant_remaining <= 0:
            return 0.0
        return float(self.isp * G0 * math.log(
            1.0 + self.propellant_remaining / max(self.dry_mass, 1e-6)))

    @property
    def controlled_reentry_delta_v(self) -> float:
        return deorbit_delta_v(self.altitude, 50.0)

    @property
    def can_controlled_reentry(self) -> bool:
        return self.available_delta_v >= self.controlled_reentry_delta_v

    def compliant_altitude(self, rule: str = "iadc_25_year") -> float:
        """
        Highest altitude whose natural decay meets a disposal rule.

        Solved by bisection on the lifetime table rather than inverted analytically, since
        lifetime spans nine orders of magnitude across LEO.
        """
        target = DISPOSAL_RULE_YEARS[rule]
        lo, hi = 150.0, self.altitude
        if float(orbital_lifetime(hi, self.area_to_mass)) <= target:
            return hi
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if float(orbital_lifetime(mid, self.area_to_mass)) <= target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def compliance_delta_v(self, rule: str = "iadc_25_year") -> float:
        """Delta-v to drop to an altitude that satisfies a disposal rule."""
        return deorbit_delta_v(self.altitude, self.compliant_altitude(rule))

    @property
    def launch_carbon(self) -> float:
        """Launch CO2e attributable to this spacecraft [kg]."""
        factor = LAUNCH_CARBON.get(self.propellant_type, 25.0)
        return factor * float(self.launch_mass)

    @property
    def recoverable_mass(self) -> float:
        """Mass [kg] plausibly recoverable given servicing infrastructure."""
        total = sum(self.material_mix.values()) or 1.0
        return float(self.dry_mass * sum(
            (frac / total) * RECOVERABILITY.get(mat, 0.3)
            for mat, frac in self.material_mix.items()
        ))

    @property
    def surviving_mass(self) -> float:
        """Mass [kg] expected to reach the ground in an uncontrolled re-entry."""
        return float(self.dry_mass * (1.0 - np.clip(self.demisable_fraction, 0.0, 1.0)))


# ============================================================================= actions
@dataclass(frozen=True)
class MitigationAction:
    """
    One disposal or remediation option.

    ``requires`` and ``conflicts`` encode the interactions that make greedy selection wrong:
    controlled re-entry needs either onboard propellant or a deorbit kit, and once the object
    is deorbited, active removal is pointless.
    """

    key: str
    name: str
    description: str
    cost_units: float
    propellant_kg: float = 0.0
    carbon_kg: float = 0.0
    debris_year_reduction: float = 0.0     # fraction of baseline avoided
    casualty_risk_multiplier: float = 1.0
    recovery_fraction: float = 0.0
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()


def build_action_catalogue(profile: MissionProfile) -> list[MitigationAction]:
    """
    Cost and benefit each option *for this specific mission*.

    The numbers depend on the mission, which is the point: a controlled re-entry from 400 km
    is nearly free and from 1400 km is unaffordable, and passivation is worth far more on an
    object that will linger for a millennium than on one that decays next year.
    """
    dv_reentry = profile.controlled_reentry_delta_v
    dv_comply = profile.compliance_delta_v("iadc_25_year")
    prop_reentry = propellant_mass(profile.dry_mass, dv_reentry, profile.isp)
    prop_comply = propellant_mass(profile.dry_mass, dv_comply, profile.isp)
    life = max(profile.natural_lifetime, 1e-6)

    # A graveyard/compliance manoeuvre removes the fraction of residence time it eliminates.
    comply_alt = profile.compliant_altitude("iadc_25_year")
    comply_life = float(orbital_lifetime(comply_alt, profile.area_to_mass))
    comply_reduction = float(np.clip(1.0 - comply_life / life, 0.0, 1.0))

    actions = [
        MitigationAction(
            key="passivation",
            name="End-of-life passivation",
            description=("Vent residual propellant and pressurant, discharge batteries, stop "
                         "reaction wheels. Cheapest possible intervention and the highest "
                         "leverage: it does not remove the object, it removes its ability to "
                         "explode later and multiply itself into hundreds of fragments."),
            cost_units=1.0,
            debris_year_reduction=0.0,          # object stays; its *expected* fragmentation goes away
            casualty_risk_multiplier=1.0,
        ),
        MitigationAction(
            key="graveyard",
            name=f"Disposal manoeuvre to {comply_alt:.0f} km (25-year rule)",
            description=("Lower the orbit until natural decay meets the disposal guideline. "
                         "Far cheaper than a controlled re-entry and captures most of the "
                         "debris-year benefit."),
            cost_units=2.0 + 0.02 * dv_comply,
            propellant_kg=prop_comply,
            debris_year_reduction=comply_reduction,
            conflicts=("controlled_reentry",),
        ),
        MitigationAction(
            key="controlled_reentry",
            name="Controlled destructive re-entry",
            description=("Single burn to a 50 km perigee, giving entry on the first pass into "
                         "a chosen ocean area. Removes the object entirely and pins the "
                         "footprint, which is the only way to make the casualty expectation "
                         "genuinely small rather than merely diluted over the globe."),
            cost_units=6.0 + 0.03 * dv_reentry,
            propellant_kg=prop_reentry,
            debris_year_reduction=1.0,
            casualty_risk_multiplier=0.02,      # footprint moved to open ocean
            requires=(),
            conflicts=("graveyard",),
        ),
        MitigationAction(
            key="design_for_demise",
            name="Design for demise",
            description=("Replace titanium tanks, steel fittings and bonded composite with "
                         "materials and joints that ablate. A design-time decision, not an "
                         "end-of-life one, which is why it is cheap here but must be chosen "
                         "years earlier."),
            cost_units=4.0,
            casualty_risk_multiplier=0.25,
        ),
        MitigationAction(
            key="deorbit_kit",
            name="Deorbit kit (drag sail or dedicated stage)",
            description=("Added hardware that provides disposal delta-v independently of the "
                         "primary propulsion system - the fallback for a spacecraft that has "
                         "failed or run dry, which is the case that produces most abandoned "
                         "objects."),
            cost_units=5.0,
            carbon_kg=LAUNCH_CARBON.get(profile.propellant_type, 25.0) * 25.0,  # ~25 kg of kit
            debris_year_reduction=0.92,
        ),
        MitigationAction(
            key="active_removal",
            name="Active debris removal (rendezvous and capture)",
            description=("A dedicated servicer captures and deorbits the object. The only "
                         "option for something already abandoned, and by far the most "
                         "expensive - the whole argument for designing disposal in."),
            cost_units=40.0,
            carbon_kg=LAUNCH_CARBON.get("kerolox", 25.0) * 400.0,  # servicer launch share
            debris_year_reduction=1.0,
            casualty_risk_multiplier=0.05,
            conflicts=("controlled_reentry", "graveyard"),
        ),
        MitigationAction(
            key="on_orbit_refuel",
            name="On-orbit refuelling / life extension",
            description=("Refuel and keep operating. Does not reduce debris-years by itself - "
                         "the object stays in orbit - but it avoids launching a replacement, "
                         "which is where the carbon saving comes from."),
            cost_units=18.0,
            carbon_kg=-0.6 * profile.launch_carbon,   # a replacement launch mostly avoided
            debris_year_reduction=0.0,
        ),
        MitigationAction(
            key="material_recovery",
            name="Material recovery / orbital reuse",
            description=("Recover structural mass for reuse on orbit rather than re-entering "
                         "it. Speculative: no such infrastructure exists. Included so the "
                         "recoverable-mass figure has somewhere to go."),
            cost_units=30.0,
            debris_year_reduction=0.85,
            recovery_fraction=0.7,
            requires=("active_removal",),
        ),
    ]
    return actions


# ========================================================================== assessment
@dataclass
class SustainabilityAssessment:
    """Baseline debris legacy of a mission, before any mitigation."""

    profile: MissionProfile
    debris_years: float
    natural_lifetime: float
    compliant_altitude_25: float
    compliant_altitude_5: float
    compliance_delta_v_25: float
    compliance_delta_v_5: float
    reentry_delta_v: float
    available_delta_v: float
    compliant_25: bool
    compliant_5: bool
    surviving_mass: float
    recoverable_mass: float
    launch_carbon: float
    added_collision_probability: float
    fragmentation_expectation: float
    circularity_index: float

    def summary(self) -> dict:
        return {
            "mission": self.profile.name,
            "altitude_km": self.profile.altitude,
            "natural_lifetime_years": self.natural_lifetime,
            "debris_years": self.debris_years,
            "available_delta_v_ms": self.available_delta_v,
            "delta_v_for_25yr_rule_ms": self.compliance_delta_v_25,
            "delta_v_for_controlled_reentry_ms": self.reentry_delta_v,
            "compliant_25_year": self.compliant_25,
            "compliant_5_year": self.compliant_5,
            "compliant_altitude_25_km": self.compliant_altitude_25,
            "surviving_mass_kg": self.surviving_mass,
            "recoverable_mass_kg": self.recoverable_mass,
            "launch_carbon_tonnes": self.launch_carbon / 1000.0,
            "added_collision_probability": self.added_collision_probability,
            "expected_fragments_from_explosion": self.fragmentation_expectation,
            "circularity_index": self.circularity_index,
        }


def assess_sustainability(profile: MissionProfile,
                          fragmentation_probability: float = 0.05,
                          expected_fragments: int = 300) -> SustainabilityAssessment:
    """
    Baseline assessment.

    ``debris_years`` counts the object itself plus its *expected* fragmentation contribution -
    probability of breaking up multiplied by fragments produced multiplied by their own
    lifetime.  Passivation acts on exactly that second term, which is why an action that
    removes nothing from orbit can still be the highest-leverage thing available.

    ``circularity_index`` is ``1 - debris_years / worst_case``, where the worst case is
    abandonment in place with no passivation.  It is 0 for "do nothing" and approaches 1 for
    prompt removal, so it behaves like a fraction-of-harm-avoided.
    """
    life = profile.natural_lifetime
    own = life
    frag_life = float(orbital_lifetime(profile.altitude, 0.05))  # fragments have higher A/M
    expected_frag_years = float(fragmentation_probability) * expected_fragments * frag_life
    total = own + expected_frag_years

    # Worst case: no passivation at all, so fragmentation is near-certain over a long residence.
    worst = own + min(1.0, 0.6 + 0.4 * fragmentation_probability) * expected_fragments * frag_life
    circ = float(np.clip(1.0 - total / max(worst, 1e-9), 0.0, 1.0))

    contrib = breakup_contribution(profile.altitude, expected_fragments)

    return SustainabilityAssessment(
        profile=profile,
        debris_years=total,
        natural_lifetime=life,
        compliant_altitude_25=profile.compliant_altitude("iadc_25_year"),
        compliant_altitude_5=profile.compliant_altitude("fcc_5_year"),
        compliance_delta_v_25=profile.compliance_delta_v("iadc_25_year"),
        compliance_delta_v_5=profile.compliance_delta_v("fcc_5_year"),
        reentry_delta_v=profile.controlled_reentry_delta_v,
        available_delta_v=profile.available_delta_v,
        compliant_25=life <= DISPOSAL_RULE_YEARS["iadc_25_year"],
        compliant_5=life <= DISPOSAL_RULE_YEARS["fcc_5_year"],
        surviving_mass=profile.surviving_mass,
        recoverable_mass=profile.recoverable_mass,
        launch_carbon=profile.launch_carbon,
        added_collision_probability=contrib.added_collision_probability,
        fragmentation_expectation=float(fragmentation_probability) * expected_fragments,
        circularity_index=circ,
    )


# ============================================================================ optimiser
@dataclass
class MitigationPlan:
    """A selected set of actions with its aggregate effect."""

    actions: list[MitigationAction]
    total_cost: float
    total_propellant: float
    total_carbon_delta: float
    debris_years_before: float
    debris_years_after: float
    casualty_multiplier: float
    recovered_mass: float
    feasible: bool
    notes: list[str] = field(default_factory=list)

    @property
    def debris_years_avoided(self) -> float:
        return self.debris_years_before - self.debris_years_after

    @property
    def efficiency(self) -> float:
        """Debris-years avoided per cost unit - the ratio to rank plans by."""
        return self.debris_years_avoided / max(self.total_cost, 1e-9)

    def summary(self) -> dict:
        return {
            "actions": [a.key for a in self.actions],
            "total_cost_units": self.total_cost,
            "total_propellant_kg": self.total_propellant,
            "carbon_delta_tonnes": self.total_carbon_delta / 1000.0,
            "debris_years_before": self.debris_years_before,
            "debris_years_after": self.debris_years_after,
            "debris_years_avoided": self.debris_years_avoided,
            "reduction_pct": 100.0 * self.debris_years_avoided / max(self.debris_years_before, 1e-9),
            "casualty_risk_multiplier": self.casualty_multiplier,
            "recovered_mass_kg": self.recovered_mass,
            "efficiency_debris_years_per_cost": self.efficiency,
            "feasible": self.feasible,
            "notes": self.notes,
        }


def _combination_effect(actions, assessment: SustainabilityAssessment) -> MitigationPlan:
    """Aggregate a set of actions. Reductions compose multiplicatively on what remains."""
    profile = assessment.profile
    keys = {a.key for a in actions}
    notes: list[str] = []
    feasible = True

    remaining = 1.0
    for a in actions:
        remaining *= (1.0 - float(np.clip(a.debris_year_reduction, 0.0, 1.0)))

    # Passivation removes the expected-fragmentation term rather than the object.
    own_years = assessment.natural_lifetime
    frag_years = max(assessment.debris_years - own_years, 0.0)
    if "passivation" in keys:
        frag_years *= 0.05
        notes.append("Passivation removes ~95 % of the expected-fragmentation debris-years.")
    after = (own_years + frag_years) * remaining

    cost = sum(a.cost_units for a in actions)
    prop = sum(a.propellant_kg for a in actions)
    carbon = sum(a.carbon_kg for a in actions)
    cas = 1.0
    for a in actions:
        cas *= a.casualty_risk_multiplier
    rec = profile.recoverable_mass * max((a.recovery_fraction for a in actions), default=0.0)

    # Feasibility: dependencies, conflicts, and whether the propellant actually exists.
    for a in actions:
        for req in a.requires:
            if req not in keys:
                feasible = False
                notes.append(f"{a.key} requires {req}, which is not in the plan.")
        for con in a.conflicts:
            if con in keys:
                feasible = False
                notes.append(f"{a.key} conflicts with {con}.")
    needs_prop = prop
    if needs_prop > profile.propellant_remaining and "deorbit_kit" not in keys:
        feasible = False
        notes.append(
            f"Needs {needs_prop:.1f} kg of propellant but only {profile.propellant_remaining:.1f} kg "
            f"remains, and no deorbit kit is included."
        )
    return MitigationPlan(list(actions), cost, prop, carbon, assessment.debris_years,
                          after, cas, rec, feasible, notes)


def optimise_mitigation(
    assessment: SustainabilityAssessment,
    budget: float = 10.0,
    actions: list[MitigationAction] | None = None,
    objective: str = "debris_years",
) -> MitigationPlan:
    """
    Best feasible action set within ``budget``, by exhaustive search over subsets.

    With a catalogue of eight actions there are only 256 subsets, so the exact optimum is
    cheap and there is no reason to accept the greedy answer - which genuinely differs here,
    because the actions interact.  Greedy ranks by benefit-per-cost and so takes
    ``controlled_reentry`` early, which then blocks ``graveyard``; and it will pick
    ``material_recovery`` without the ``active_removal`` it depends on.

    ``objective``: ``"debris_years"`` maximises debris-years avoided, ``"efficiency"``
    maximises avoided-per-cost, ``"carbon"`` minimises the carbon delta.
    """
    catalogue = actions or build_action_catalogue(assessment.profile)
    n = len(catalogue)
    best: MitigationPlan | None = None

    for mask in range(1 << n):
        chosen = [catalogue[i] for i in range(n) if mask >> i & 1]
        if not chosen:
            continue
        plan = _combination_effect(chosen, assessment)
        if not plan.feasible or plan.total_cost > budget:
            continue
        if objective == "efficiency":
            score = plan.efficiency
        elif objective == "carbon":
            score = -plan.total_carbon_delta
        else:
            score = plan.debris_years_avoided
        if best is None:
            best, best_score = plan, score
        elif score > best_score or (score == best_score and plan.total_cost < best.total_cost):
            best, best_score = plan, score

    if best is None:
        empty = MitigationPlan([], 0.0, 0.0, 0.0, assessment.debris_years,
                               assessment.debris_years, 1.0, 0.0, True,
                               [f"No feasible action set within a budget of {budget:g} cost units."])
        return empty
    return best


def greedy_mitigation(assessment: SustainabilityAssessment, budget: float = 10.0,
                      actions: list[MitigationAction] | None = None) -> MitigationPlan:
    """
    Greedy benefit-per-cost selection, provided for comparison with :func:`optimise_mitigation`.

    Kept so the dashboard can show the gap: when actions interact, greedy leaves
    debris-years on the table, and being able to demonstrate that is more convincing than
    asserting the optimiser is needed.
    """
    catalogue = list(actions or build_action_catalogue(assessment.profile))
    catalogue.sort(key=lambda a: -a.debris_year_reduction / max(a.cost_units, 1e-9))
    chosen: list[MitigationAction] = []
    for a in catalogue:
        trial = chosen + [a]
        plan = _combination_effect(trial, assessment)
        if plan.feasible and plan.total_cost <= budget:
            chosen = trial
    return _combination_effect(chosen, assessment) if chosen else MitigationPlan(
        [], 0.0, 0.0, 0.0, assessment.debris_years, assessment.debris_years, 1.0, 0.0, True,
        ["Greedy selection found nothing affordable."])


def compare_altitudes(profile: MissionProfile, altitudes=(400, 600, 800, 1000, 1200, 1400)):
    """
    The same spacecraft at different operational altitudes.

    The headline sustainability result: debris-years span five orders of magnitude across
    LEO, so *where* a constellation flies dominates every other design choice about it.
    """
    from dataclasses import replace as _replace

    rows = []
    for alt in altitudes:
        p = _replace(profile, altitude=float(alt))
        a = assess_sustainability(p)
        rows.append({
            "altitude_km": float(alt),
            "natural_lifetime_years": a.natural_lifetime,
            "debris_years": a.debris_years,
            "compliant_25_year": a.compliant_25,
            "delta_v_for_compliance_ms": a.compliance_delta_v_25,
            "propellant_for_compliance_kg": propellant_mass(p.dry_mass, a.compliance_delta_v_25, p.isp),
            "reentry_delta_v_ms": a.reentry_delta_v,
            "added_collision_probability": a.added_collision_probability,
            "circularity_index": a.circularity_index,
        })
    return rows
