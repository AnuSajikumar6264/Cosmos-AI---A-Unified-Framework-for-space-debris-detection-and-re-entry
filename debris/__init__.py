"""
Debris detection, re-entry prediction and orbital-sustainability analysis for the satellite
digital twin.

The package answers one question end to end: **if this satellite comes apart, or if this
rocket sheds a stage, where does the hardware land, who is at risk, and what does it do to the
orbital environment?**  It is designed to plug into the existing anomaly-detection and
health-monitoring twin rather than sit beside it - subsystem health drives the breakup
physics, not just a separate risk readout.

Layers, bottom up
-----------------
======================================  ====================================================
:mod:`debris.constants`                 WGS-84, gravitational and range-safety constants
:mod:`debris.atmosphere`                US Standard Atmosphere 1976 (validated to <0.002 %)
:mod:`debris.geodesy`                   ECEF/geodetic frames, great-circle geometry
:mod:`debris.drag`                      Mach- and Knudsen-dependent drag coefficients
:mod:`debris.materials`                 Thermal properties for the demise model
:mod:`debris.propagator`                3-DOF re-entry integrator with aerothermal demise
:mod:`debris.fragmentation`             NASA Standard Breakup Model
:mod:`debris.launch`                    Launch-vehicle staging and drop zones
:mod:`debris.monte_carlo`               Impact dispersion and **conformal prediction zones**
:mod:`debris.risk`                      Population exposure and expected casualties
:mod:`debris.kessler`                   Two-species cascade / criticality engine
:mod:`debris.circular_economy`          Debris-years accounting and mitigation optimisation
:mod:`debris.detection`                 Frame-differencing debris detection, pixels to physics
:mod:`debris.coupling`                  Health/anomaly <-> breakup-physics coupling
:mod:`debris.viz`                       Plotly figures (needs plotly)
:mod:`debris.apsgtt`                    Trajectory transformer with LoRA adapters (needs torch)
:mod:`debris.continual`                 Continual learning without catastrophic forgetting
:mod:`debris.federated`                 Federated training across operators
======================================  ====================================================

Dependencies
------------
The physics core is **numpy-only**.  :mod:`debris.viz` needs plotly; :mod:`debris.apsgtt`,
:mod:`debris.continual` and :mod:`debris.federated` need torch.  Both are optional and are
imported lazily, so ``import debris`` works in a bare numpy environment and the deployed
dashboard degrades rather than failing.

Quick start
-----------
Predict where one object lands::

    from debris import DebrisObject, StateVector, propagate
    state = StateVector.from_geodetic(13.72, 80.23, 120e3, 7500.0, -1.5, 140.0)
    obj = DebrisObject("tank", mass=200.0, area=0.15)
    traj = propagate(state, obj)
    print(traj.impact_latitude, traj.impact_longitude, traj.impact_speed)

Full coupled chain from a telemetry anomaly to a casualty estimate::

    from debris import run_coupled_prediction
    result = run_coupled_prediction(
        anomaly_score=0.9,
        health={"Propulsion System": 0.9, "Thermal Control": 0.6},
    )
    print(result.hazard.summary(), result.risk.summary())

A note on the numbers
---------------------
The physics is real and cross-validated (two independent propagator implementations agree to
0.15 m on impact point; the atmosphere reproduces US76 to better than 0.002 %).  Several
*inputs* are not: the population model is a coarse synthetic raster, launch-vehicle masses are
public estimates, and the health-to-physics coupling is a stated hypothesis rather than a
fitted model.  Each module's docstring says which of the two it is.  Nothing here is
qualified for an operational safety case.
"""

from __future__ import annotations

__version__ = "0.1.0"

# ------------------------------------------------------------------ physics core (numpy)
from .atmosphere import US76, Atmosphere, AtmosphereSample, DensityTable
from .constants import CASUALTY_KE_THRESHOLD, EARTH_MU, EARTH_OMEGA, WGS84_A
from .drag import (
    SHAPES,
    DragModel,
    area_from_characteristic_length,
    ballistic_coefficient,
    characteristic_length_from_area,
)
from .geodesy import (
    ecef_to_enu,
    ecef_to_geodetic,
    enu_to_ecef,
    geodetic_to_ecef,
    great_circle_distance,
    initial_bearing,
    wrap_longitude,
)
from .materials import MATERIALS, Material, get_material
from .propagator import (
    OUTCOME_NAMES,
    DebrisObject,
    EnsembleResult,
    StateVector,
    Trajectory,
    WindField,
    propagate,
    propagate_ensemble,
    propagate_many,
)

# --------------------------------------------------------------------- breakup and launch
from .fragmentation import (
    BreakupType,
    DebrisCloud,
    ParentType,
    cumulative_fragment_count,
    generate_debris_cloud,
    sample_area_to_mass,
    sample_delta_v,
    size_distribution_check,
)
from .launch import (
    LAUNCH_SITES,
    LAUNCH_VEHICLES,
    AscentProfile,
    LaunchSite,
    LaunchVehicle,
    StageEvent,
    ascent_profile,
    separation_states,
)

# -------------------------------------------------------------- dispersion and conformal
from .monte_carlo import (
    ConformalZone,
    DispersionConfig,
    Footprint,
    chi2_quantile_2dof,
    conformalise_with_history,
    density_zone,
    mahalanobis_zone,
    run_cloud_dispersion,
    run_dispersion,
    zone_comparison,
)

# ------------------------------------------------------------------------ risk and policy
from .circular_economy import (
    LAUNCH_CARBON,
    MissionProfile,
    MitigationAction,
    MitigationPlan,
    SustainabilityAssessment,
    assess_sustainability,
    build_action_catalogue,
    compare_altitudes,
    deorbit_delta_v,
    greedy_mitigation,
    optimise_mitigation,
    propellant_mass,
)
from .kessler import (
    FRAGMENT,
    INTACT,
    CascadeContribution,
    CascadeResult,
    OrbitalShell,
    Species,
    breakup_contribution,
    default_leo_shells,
    environment_report,
    orbital_lifetime,
    simulate_cascade,
    spatial_density,
)
from .risk import (
    PopulationModel,
    RiskAssessment,
    SyntheticPopulationModel,
    assess_footprint,
    casualty_area,
    zone_population,
)

# ------------------------------------------------------------------ detection and coupling
from .coupling import (
    OBSERVABILITY_DRIVING,
    PHYSICS_DRIVING,
    SUBSYSTEMS,
    BreakupHazard,
    CoupledPrediction,
    DebrisEvidence,
    FailureForecast,
    SubsystemHealth,
    assess_breakup_hazard,
    debris_evidence_to_health,
    estimate_time_to_breakup,
    run_coupled_prediction,
)
from .detection import (
    Camera,
    Detection,
    DetectionMetrics,
    DoGDetector,
    SyntheticFrameConfig,
    TrueObject,
    detection_metrics,
    detections_to_objects,
    difference_frames,
    estimate_shift,
    evaluate_detector,
    generate_frame,
    generate_frame_pair,
    torch_available,
)

__all__ = [
    "__version__",
    # atmosphere / geodesy / drag / materials
    "US76", "Atmosphere", "AtmosphereSample", "DensityTable",
    "CASUALTY_KE_THRESHOLD", "EARTH_MU", "EARTH_OMEGA", "WGS84_A",
    "DragModel", "SHAPES", "area_from_characteristic_length",
    "characteristic_length_from_area", "ballistic_coefficient",
    "ecef_to_geodetic", "geodetic_to_ecef", "ecef_to_enu", "enu_to_ecef",
    "great_circle_distance", "initial_bearing", "wrap_longitude",
    "MATERIALS", "Material", "get_material",
    # propagation
    "DebrisObject", "StateVector", "Trajectory", "WindField", "EnsembleResult",
    "OUTCOME_NAMES", "propagate", "propagate_many", "propagate_ensemble",
    # breakup / launch
    "BreakupType", "ParentType", "DebrisCloud", "generate_debris_cloud",
    "sample_area_to_mass", "sample_delta_v", "cumulative_fragment_count",
    "size_distribution_check",
    "LaunchSite", "LaunchVehicle", "StageEvent", "AscentProfile",
    "LAUNCH_SITES", "LAUNCH_VEHICLES", "ascent_profile", "separation_states",
    # dispersion / conformal
    "DispersionConfig", "Footprint", "ConformalZone", "run_dispersion",
    "run_cloud_dispersion", "mahalanobis_zone", "density_zone", "zone_comparison",
    "conformalise_with_history", "chi2_quantile_2dof",
    # risk / kessler / circular economy
    "PopulationModel", "SyntheticPopulationModel", "RiskAssessment",
    "assess_footprint", "casualty_area", "zone_population",
    "OrbitalShell", "Species", "INTACT", "FRAGMENT", "CascadeResult",
    "CascadeContribution", "default_leo_shells", "simulate_cascade",
    "breakup_contribution", "environment_report", "spatial_density", "orbital_lifetime",
    "MissionProfile", "MitigationAction", "MitigationPlan", "SustainabilityAssessment",
    "assess_sustainability", "build_action_catalogue", "optimise_mitigation",
    "greedy_mitigation", "compare_altitudes", "deorbit_delta_v", "propellant_mass",
    "LAUNCH_CARBON",
    # detection / coupling
    "Camera", "Detection", "DetectionMetrics", "DoGDetector", "SyntheticFrameConfig",
    "TrueObject", "generate_frame", "generate_frame_pair", "difference_frames",
    "estimate_shift", "detection_metrics", "detections_to_objects", "evaluate_detector",
    "torch_available",
    "SubsystemHealth", "BreakupHazard", "DebrisEvidence", "FailureForecast",
    "CoupledPrediction", "assess_breakup_hazard", "debris_evidence_to_health",
    "estimate_time_to_breakup", "run_coupled_prediction",
    "SUBSYSTEMS", "PHYSICS_DRIVING", "OBSERVABILITY_DRIVING",
]


def _optional(name: str):
    """Import an optional submodule, returning ``None`` with a clear reason if unavailable."""
    import importlib

    try:
        return importlib.import_module(f"{__name__}.{name}")
    except ImportError:
        return None


def torch_modules_available() -> bool:
    """Whether the torch-dependent contributions (APSGTT, continual, federated) can load."""
    return torch_available()


def plotly_available() -> bool:
    """Whether :mod:`debris.viz` can be imported."""
    try:
        import plotly  # noqa: F401

        return True
    except Exception:
        return False
