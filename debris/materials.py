"""
Thermal/structural material properties for the demise model.

A re-entering fragment only shows up in a ground footprint if it survives.  Thin
aluminium skin, insulation blankets and solar-array substrate almost always ablate
away; titanium pressurant tanks, steel engine parts, CFRP overwrap and reaction
wheels routinely reach the ground intact.  The lumped-mass demise model in
:mod:`debris.propagator` uses these numbers to decide which fragments to keep.

``ablation_enthalpy`` is the effective energy per unit mass needed to remove
material - sensible heating from 300 K to the melt point plus the latent heat:

    h_eff = cp * (T_melt - 300) + L_fusion

Values are representative engineering figures for the alloys actually flown; they
are not a substitute for a validated material database.
"""

from __future__ import annotations

from dataclasses import dataclass

STEFAN_BOLTZMANN = 5.670374419e-8  # [W/(m^2 K^4)]


@dataclass(frozen=True)
class Material:
    """Properties needed for lumped-mass aerothermal heating and demise."""

    name: str
    density: float          # [kg/m^3]
    specific_heat: float    # cp [J/(kg K)]
    melt_temperature: float  # [K]
    latent_heat: float      # heat of fusion [J/kg]
    emissivity: float       # hemispherical total emissivity [-]

    @property
    def ablation_enthalpy(self) -> float:
        """Effective energy per kg to melt away material from 300 K [J/kg]."""
        return self.specific_heat * max(self.melt_temperature - 300.0, 1.0) + self.latent_heat


#: Common spacecraft / launch-vehicle materials.
MATERIALS: dict[str, Material] = {
    # Structure and skin - demises readily, which is why most breakup mass never lands.
    "aluminium": Material("Aluminium 2024-T3", 2780.0, 900.0, 830.0, 3.97e5, 0.14),
    "aluminium_oxidised": Material("Aluminium (oxidised)", 2780.0, 900.0, 830.0, 3.97e5, 0.30),
    # Tanks, thrust structures, fasteners - frequent ground survivors.
    "titanium": Material("Titanium Ti-6Al-4V", 4430.0, 560.0, 1900.0, 4.35e5, 0.60),
    "stainless_steel": Material("Stainless steel A316", 7900.0, 500.0, 1700.0, 2.86e5, 0.35),
    "inconel": Material("Inconel 718", 8440.0, 435.0, 1600.0, 2.90e5, 0.55),
    # Composite overwrap and payload adaptors - char rather than melt; the enthalpy
    # here stands in for pyrolysis.
    "cfrp": Material("CFRP (carbon/epoxy)", 1600.0, 1000.0, 900.0, 1.20e6, 0.85),
    # Optics, sensor windows.
    "silica": Material("Fused silica", 2200.0, 740.0, 1900.0, 1.42e5, 0.80),
    # Multi-layer insulation / blankets - very low B, always demises or flutters down.
    "mli": Material("Multi-layer insulation", 350.0, 1100.0, 600.0, 2.0e5, 0.80),
    # Battery packs, magnets, reaction wheels.
    "copper": Material("Copper", 8940.0, 385.0, 1358.0, 2.05e5, 0.40),
}

DEFAULT_MATERIAL = "aluminium_oxidised"


def get_material(name: str | Material | None) -> Material:
    """Resolve a material by key, pass a :class:`Material` through, or use the default."""
    if isinstance(name, Material):
        return name
    key = (name or DEFAULT_MATERIAL).strip().lower().replace(" ", "_")
    if key in MATERIALS:
        return MATERIALS[key]
    aliases = {"al": "aluminium", "ti": "titanium", "steel": "stainless_steel",
               "composite": "cfrp", "glass": "silica", "insulation": "mli"}
    if key in aliases:
        return MATERIALS[aliases[key]]
    raise ValueError(f"unknown material {name!r}; expected one of {sorted(MATERIALS)}")


#: Rough mass split of a spent upper stage / satellite bus by material, used when a
#: breakup model has to assign materials to fragments it only knows the size of.
TYPICAL_MASS_FRACTIONS: dict[str, float] = {
    "aluminium_oxidised": 0.52,
    "cfrp": 0.14,
    "stainless_steel": 0.12,
    "titanium": 0.09,
    "copper": 0.06,
    "inconel": 0.04,
    "silica": 0.02,
    "mli": 0.01,
}
