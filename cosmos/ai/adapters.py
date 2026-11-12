"""Adapters that expose existing COSMOS-AI results through the shared contracts.

Each adapter reads an artifact that a scientific run already wrote and re-expresses it as
typed contract records for :mod:`cosmos.ai.orchestration`. Adapters do not retrain, re-fit,
resample or rescore anything, so running them cannot change a published number.

Three rules keep the layer honest:

* **No fabrication.** A missing artifact raises :class:`ArtifactUnavailable`; the
  orchestrator then records the module as failed and blocks its dependants. Nothing
  downstream receives an invented value.
* **No invented identity.** Telemetry (ESA-ADB) and conjunction (Kelvins CAC) records are
  anonymised and cannot be linked to catalogued objects or to each other. Adapters keep each
  source's own identifier namespace and never join across them.
* **Recorded lineage.** Every result carries the SHA-256 of the artifact it was read from,
  so a consumer can tell which file produced it.

The catalogue chain (elements → lifetime → re-entry) *is* identity-linked: all of its fields
come from one snapshot keyed by NORAD number, so it supports a genuine end-to-end run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .contracts import (
    CollisionRiskEstimate,
    DebrisDetection,
    HealthEstimate,
    LifetimeEstimate,
    ModuleEvidence,
    ObjectCharacteristics,
    OrbitalElements,
    Provenance,
    ReentryPrediction,
    Uncertainty,
)
from .orchestration import ModuleContext, ModuleResult, ModuleSpec
from .provenance import ROOT, git_revision, sha256_file

#: Quantile levels of the lifetime/conjunction quantile regressors
#: (``cosmos.ai.lifetime.models.QUANTILES``).
LIFETIME_QUANTILES = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)

#: Horizons, in days, reported by the dated twin (``cosmos.ai.twin.engine.HORIZONS``).
HORIZON_DAYS = {"30d": 30.0, "90d": 90.0, "1yr": 365.25}

#: ``cosmos.ai.conjunction.data.RISK_FLOOR``: log10 risk is clipped at this value, so a
#: prediction at the floor means "below the reported floor", not an exact probability.
CONJUNCTION_RISK_FLOOR = -30.0

TWIN_SNAPSHOT = "outputs/twin/as_of_{as_of}/forecast_table.csv.gz"
CONJUNCTION_PREDICTIONS = "outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz"
CONJUNCTION_SUMMARY = "outputs/benchmarks/conjunction_kelvins_cac/summary.json"
TELEMETRY_RESULTS = "outputs/benchmarks/telemetry_esa_adb/results.csv"
SPOTGEO_SUBMISSION = "outputs/benchmarks/vision_spotgeo/classical_cosmos_frontend_test_submission.json"


class ArtifactUnavailable(RuntimeError):
    """Raised when a required result artifact is absent, so no output is produced."""


def _artifact(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_file():
        raise ArtifactUnavailable(f"required artifact is not present: {relative}")
    return path


def _provenance(root: Path, relative: str, as_of: str, source: str,
                extra_sources: tuple[str, ...] = ()) -> Provenance:
    """Provenance naming the artifact actually read, with its content digest."""
    path = root / relative
    return Provenance(
        as_of=as_of,
        input_sources=(source,) + extra_sources,
        input_hashes={relative: sha256_file(path)},
        code_revision=git_revision(root)["git_commit"],
    )


def _as_of_timestamp(as_of: str) -> str:
    return f"{as_of}T00:00:00+00:00"


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return None if not np.isfinite(number) else number


def _monotone(values: list[float]) -> list[float]:
    """Enforce nondecreasing order caused by independent per-quantile regressors.

    The lifetime and conjunction experts fit each quantile separately, so a saved row can
    cross by a small amount. Taking a running maximum repairs the ordering without moving a
    quantile below its fitted value; it is a presentation fix, not a re-estimation.
    """
    out: list[float] = []
    current = -np.inf
    for value in values:
        current = max(current, value)
        out.append(current)
    return out


# --------------------------------------------------------------------- catalogue chain
def _load_snapshot(root: Path, as_of: str, limit: int | None) -> tuple[pd.DataFrame, str]:
    relative = TWIN_SNAPSHOT.format(as_of=as_of)
    path = _artifact(root, relative)
    table = pd.read_csv(path)
    from .schema import REQUIRED_FORECAST_COLUMNS   # one shared definition (forecast_table/1.0)
    missing = set(REQUIRED_FORECAST_COLUMNS) - set(table.columns)
    if missing:
        raise ArtifactUnavailable(f"{relative} is missing columns: {sorted(missing)}")
    if limit is not None:
        # Rank by 30-day re-entry probability so a bounded run keeps the decision-relevant
        # objects rather than an arbitrary slice of the catalogue.
        table = table.sort_values("p_30d", ascending=False, na_position="last").head(limit)
    return table.reset_index(drop=True), relative


def catalogue_state(context: ModuleContext) -> ModuleResult:
    """Catalogue elements and physical characteristics for the snapshot objects."""
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    table, relative = _load_snapshot(root, as_of, context.config.get("limit"))
    provenance = _provenance(root, relative, as_of, "CelesTrak SATCAT snapshot via COSMOS twin",
                             ("GCAT",))
    epoch = _as_of_timestamp(as_of)

    elements: dict[str, OrbitalElements] = {}
    characteristics: dict[str, ObjectCharacteristics] = {}
    for row in table.itertuples(index=False):
        object_id = f"NORAD-{int(row.norad)}"
        elements[object_id] = OrbitalElements(
            object_id=object_id,
            epoch=epoch,
            perigee_altitude_km=float(row.perigee),
            apogee_altitude_km=float(row.apogee),
            inclination_deg=float(row.inc),
            provenance=provenance,
        )
        characteristics[object_id] = ObjectCharacteristics(
            object_id=object_id,
            mass_kg=_float_or_none(row.mass),
            source="GCAT",
            provenance=provenance,
        )

    classes = {f"NORAD-{int(row.norad)}": str(row.type1) for row in table.itertuples(index=False)}
    regimes = {f"NORAD-{int(row.norad)}": str(row.regime) for row in table.itertuples(index=False)}
    names = {f"NORAD-{int(row.norad)}": str(row.Name) for row in table.itertuples(index=False)}
    return ModuleResult(
        outputs={
            "elements": elements,
            "characteristics": characteristics,
            "object_class": classes,
            "regime": regimes,
            "name": names,
        },
        provenance=provenance,
    )


def lifetime_estimates(context: ModuleContext) -> ModuleResult:
    """Orbital lifetime quantiles from the saved learned-expert columns."""
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    table, relative = _load_snapshot(root, as_of, context.config.get("limit"))
    provenance = _provenance(root, relative, as_of, "COSMOS lifetime expert (saved snapshot)")
    epoch = _as_of_timestamp(as_of)

    estimates: dict[str, LifetimeEstimate] = {}
    abstained: dict[str, str] = {}
    noncoherent: dict[str, dict[str, float]] = {}
    for row in table.itertuples(index=False):
        object_id = f"NORAD-{int(row.norad)}"
        lo90 = _float_or_none(row.lifetime_lo90_days)
        median = _float_or_none(row.median_days_lifetime)
        hi90 = _float_or_none(row.lifetime_hi90_days)
        horizons = {HORIZON_DAYS["30d"]: _float_or_none(row.p_lifetime_30d),
                    HORIZON_DAYS["90d"]: _float_or_none(row.p_lifetime_90d),
                    HORIZON_DAYS["1yr"]: _float_or_none(row.p_lifetime_1yr)}
        if None in (lo90, median, hi90) or any(p is None for p in horizons.values()):
            # The learned expert abstains for objects outside its fitted cohort; record the
            # abstention rather than substituting the physics forecast.
            abstained[object_id] = "saved lifetime expert produced no value for this object"
            continue
        ordered = [horizons[h] for h in sorted(horizons)]
        if any(a > b for a, b in zip(ordered, ordered[1:])):
            # The saved p_lifetime_* columns are calibrated by an independent isotonic
            # regressor per horizon, which does not constrain probabilities across horizons,
            # so a few objects are not a coherent CDF. Abstaining keeps the defect visible;
            # silently taking a running maximum here would overwrite a published number.
            abstained[object_id] = (
                "saved per-horizon calibrated probabilities are not monotone across horizons "
                "(independent isotonic calibration per horizon); no coherent CDF available"
            )
            noncoherent[object_id] = {str(h): horizons[h] for h in sorted(horizons)}
            continue
        quantiles = tuple(zip((0.05, 0.50, 0.95), _monotone([lo90, median, hi90])))
        estimates[object_id] = LifetimeEstimate(
            object_id=object_id,
            as_of=epoch,
            model="COSMOS lifetime expert (fused learned + physics), saved snapshot",
            quantiles_days=quantiles,
            horizon_probabilities={h: p for h, p in sorted(horizons.items())},
            uncertainty=Uncertainty(
                kind="quantiles",
                method="learned quantile regression with Monte Carlo drag prior",
                quantiles=quantiles,
                assumptions=(
                    "quantiles are capped at the study horizon; a value at the cap means "
                    "'at least this long', not an exact lifetime",
                    "calibrated on GCAT temporal origins; coverage under later space-weather "
                    "conditions is not guaranteed",
                ),
            ),
            provenance=provenance,
        )
    return ModuleResult(
        outputs={
            "lifetime": estimates,
            "abstained": abstained,
            "noncoherent_horizon_probabilities": noncoherent,
        },
        provenance=provenance,
    )


def reentry_predictions(context: ModuleContext) -> ModuleResult:
    """Re-entry horizon probabilities and time quantiles from the dated twin forecast."""
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    table, relative = _load_snapshot(root, as_of, context.config.get("limit"))
    provenance = _provenance(root, relative, as_of, "COSMOS dated twin forecast (saved snapshot)")
    epoch = _as_of_timestamp(as_of)

    predictions: dict[str, ReentryPrediction] = {}
    abstained: dict[str, str] = {}
    for row in table.itertuples(index=False):
        object_id = f"NORAD-{int(row.norad)}"
        regime = str(row.regime)
        horizons = {HORIZON_DAYS["30d"]: _float_or_none(row.p_30d),
                    HORIZON_DAYS["90d"]: _float_or_none(row.p_90d),
                    HORIZON_DAYS["1yr"]: _float_or_none(row.p_1yr)}
        if any(p is None for p in horizons.values()):
            abstained[object_id] = (
                "no drag forecast in the saved snapshot"
                + (" (operator-controlled object)" if regime == "operator_controlled" else "")
            )
            continue
        bounds = [_float_or_none(row.lo90_days), _float_or_none(row.median_days),
                  _float_or_none(row.hi90_days)]
        if any(value is None or value <= 0 for value in bounds):
            quantiles: tuple[tuple[float, float], ...] = ()
            uncertainty = Uncertainty(
                kind="score",
                method="physics Monte Carlo horizon probabilities without time quantiles",
                assumptions=("time quantiles unavailable for this object in the snapshot",),
            )
        else:
            quantiles = tuple(zip((0.05, 0.50, 0.95), _monotone(bounds)))
            uncertainty = Uncertainty(
                kind="quantiles",
                method="physics Monte Carlo over area-to-mass and space weather",
                quantiles=quantiles,
                assumptions=(
                    "Monte Carlo spread over drag and space-weather draws; not a conformal "
                    "interval and not a distribution-free coverage guarantee",
                    "quantiles are capped at the study horizon",
                    f"regime: {regime}",
                ),
            )
        predictions[object_id] = ReentryPrediction(
            object_id=object_id,
            as_of=epoch,
            model="COSMOS dated twin (physics prior + history posterior + lifetime fusion)",
            probability_by_horizon={h: p for h, p in sorted(horizons.items())},
            time_quantiles_days=quantiles,
            uncertainty=uncertainty,
            provenance=provenance,
        )
    return ModuleResult(
        outputs={"reentry": predictions, "abstained": abstained},
        provenance=provenance,
    )


# ------------------------------------------------------------- independent modules
def collision_risk(context: ModuleContext) -> ModuleResult:
    """Collision risk for anonymised Kelvins CAC conjunction events.

    The saved predictions are quantiles of log10 collision probability for the final CDM of
    each event. Event identifiers are positional: the dataset is anonymised, so an event
    cannot be attributed to a catalogued object.
    """
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    path = _artifact(root, CONJUNCTION_PREDICTIONS)
    model = context.config.get("collision_model", "cosmos_gated")
    with np.load(path, allow_pickle=True) as archive:
        key = f"{model}__q"
        if key not in archive:
            available = sorted(name[:-3] for name in archive.files if name.endswith("__q"))
            raise ArtifactUnavailable(
                f"conjunction model {model!r} is not in the saved predictions; available: {available}"
            )
        quantile_matrix = np.asarray(archive[key], dtype=float)
    if quantile_matrix.shape[1] != len(LIFETIME_QUANTILES):
        raise ArtifactUnavailable(
            f"expected {len(LIFETIME_QUANTILES)} quantiles, found {quantile_matrix.shape[1]}"
        )

    provenance = _provenance(root, CONJUNCTION_PREDICTIONS, as_of,
                             "ESA Kelvins Collision Avoidance Challenge (anonymised CDMs)")
    epoch = _as_of_timestamp(as_of)
    limit = context.config.get("collision_limit")
    rows = range(len(quantile_matrix) if limit is None else min(limit, len(quantile_matrix)))

    estimates: dict[str, CollisionRiskEstimate] = {}
    for index in rows:
        log_quantiles = _monotone([float(v) for v in quantile_matrix[index]])
        median_log = log_quantiles[LIFETIME_QUANTILES.index(0.50)]
        at_floor = median_log <= CONJUNCTION_RISK_FLOOR + 1e-9
        lower, upper = 10.0 ** log_quantiles[0], 10.0 ** log_quantiles[-1]
        estimates[f"CAC-EVENT-{index}"] = CollisionRiskEstimate(
            object_id=f"CAC-EVENT-{index}",
            as_of=epoch,
            model=f"COSMOS conjunction expert {model} (saved held-out predictions)",
            collision_probability=min(1.0, 10.0 ** median_log),
            uncertainty=Uncertainty(
                kind="interval",
                method="quantile regression on log10 collision probability (0.05-0.95)",
                level=0.90,
                lower=lower,
                upper=min(1.0, upper),
                assumptions=(
                    "physical collision probability of the final CDM; not an operational "
                    "response priority",
                    f"log10 risk is clipped at {CONJUNCTION_RISK_FLOOR}; a value at the floor "
                    "means 'below the reported floor'",
                    "events are anonymised and cannot be attributed to a catalogued object",
                )
                + (("this estimate sits at the reporting floor",) if at_floor else ()),
            ),
            provenance=provenance,
            # priority_score is deliberately left unset: priority is a decision-layer
            # quantity and must not be baked into a physical probability.
        )
    return ModuleResult(
        outputs={"collision": estimates, "identity_linkable": False},
        provenance=provenance,
    )


def health_estimates(context: ModuleContext) -> ModuleResult:
    """Health/anomaly evidence from the saved ESA-ADB benchmark rows.

    One record per benchmark arm, keyed by its mission and run tag. ESA-ADB missions are
    anonymised, so the identifier is a benchmark arm, not a spacecraft in any catalogue.
    The reported quantity is an event-wise F0.5 detection score for an arm, which is a
    *performance measurement*, not a per-object anomaly probability.
    """
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    path = _artifact(root, TELEMETRY_RESULTS)
    table = pd.read_csv(path)
    required = {"tag", "calibrator", "mission", "anomaly_and_rare/EW_F0.5",
                "anomaly_and_rare/EW_precision", "anomaly_and_rare/EW_recall",
                "false_alarm_runs", "alarm_runs"}
    missing = required - set(table.columns)
    if missing:
        raise ArtifactUnavailable(f"{TELEMETRY_RESULTS} is missing columns: {sorted(missing)}")

    calibrator = context.config.get("health_calibrator")
    if calibrator is not None:
        table = table[table["calibrator"].eq(calibrator)]
        if table.empty:
            raise ArtifactUnavailable(f"no ESA-ADB rows for calibrator {calibrator!r}")

    provenance = _provenance(root, TELEMETRY_RESULTS, as_of,
                             "ESA Anomaly Detection Benchmark (anonymised missions)")
    epoch = _as_of_timestamp(as_of)
    estimates: dict[str, HealthEstimate] = {}
    # Column names contain '/', which itertuples would rename, so rows are read as mappings.
    for values in table.to_dict(orient="records"):
        tag = f"ESA-ADB-M{int(values['mission'])}-{values['tag']}-{values['calibrator']}"
        score = _float_or_none(values["anomaly_and_rare/EW_F0.5"])
        alarm_runs = _float_or_none(values["alarm_runs"]) or 0.0
        false_alarm_runs = _float_or_none(values["false_alarm_runs"]) or 0.0
        estimates[tag] = HealthEstimate(
            spacecraft_id=tag,
            as_of=epoch,
            model=f"ESA-ADB arm {values['tag']} / {values['calibrator']} (saved benchmark row)",
            status="benchmark-arm-measurement",
            anomaly_score=score,
            score_semantics=("event-wise F0.5 of the arm on the ESA-ADB test half; a "
                             "detection-performance measurement, not a per-object anomaly "
                             "probability"),
            alarm=bool(alarm_runs > 0),
            uncertainty=Uncertainty(
                kind="score",
                method="event-wise F0.5 from the official ESA-ADB metric",
                assumptions=(
                    "anonymised missions; no link to a catalogued object",
                    f"{int(false_alarm_runs)} false-alarm runs of {int(alarm_runs)} alarm runs",
                    "some arms are single-seed; see the limitations register",
                ),
            ),
            provenance=provenance,
        )
    return ModuleResult(
        outputs={"health": estimates, "identity_linkable": False},
        provenance=provenance,
    )


def debris_detections(context: ModuleContext) -> ModuleResult:
    """Per-frame SpotGEO detections from the saved submission file.

    The classical front end emits hard detections, so no per-detection confidence exists and
    none is invented. SpotGEO sequences carry a frame index rather than an absolute UTC time.
    """
    root = Path(context.config.get("root", ROOT))
    as_of = context.config["as_of"]
    path = _artifact(root, SPOTGEO_SUBMISSION)
    records = json.loads(path.read_text(encoding="utf-8"))
    provenance = _provenance(root, SPOTGEO_SUBMISSION, as_of, "SpotGEO benchmark (ESA Kelvins)")

    limit = context.config.get("debris_sequence_limit")
    detections: list[DebrisDetection] = []
    sequences: set[int] = set()
    for record in records:
        sequence = int(record["sequence_id"])
        if limit is not None and sequence > limit:
            continue
        sequences.add(sequence)
        frame = int(record["frame"])
        for order, (x, y) in enumerate(record.get("object_coords") or ()):
            detections.append(DebrisDetection(
                image_id=f"spotgeo-seq{sequence}-frame{frame}-det{order}",
                observed_at=None,
                x_px=float(x),
                y_px=float(y),
                confidence=None,
                detector="classical COSMOS front end + DoG (saved test submission)",
                provenance=provenance,
                frame_index=frame,
            ))
    return ModuleResult(
        outputs={
            "detections": tuple(detections),
            "sequences": len(sequences),
            "astrometric_calibration": False,
        },
        provenance=provenance,
    )


# ------------------------------------------------------------------ decision layer
#: Mass above which a re-entering object is treated as a higher-consequence case. The
#: ESA/IADC re-entry casualty-risk screening convention is that objects of this order
#: require a re-entry assessment; it is a reporting threshold, not a validated casualty model.
CONSEQUENCE_MASS_KG = 500.0
#: Multiplier applied to the 30-day probability of a high-consequence object (mass >= CONSEQUENCE_MASS_KG).
CONSEQUENCE_MULTIPLIER = 2.0
#: The rule, recorded verbatim in every run manifest so that a consumer can explain a priority score
#: from the manifest alone instead of reconstructing it from code.
PRIORITY_RULE = {
    "formula": "priority_score = p_reentry_30d * (consequence_multiplier if mass_kg >= consequence_mass_kg else 1.0)",
    "inputs": ["p_reentry_30d (reported 30-day re-entry probability of the dated forecast)",
               "mass_kg (GCAT mass; None when unknown, in which case the multiplier is never applied)"],
    "consequence_mass_kg": CONSEQUENCE_MASS_KG,
    "consequence_multiplier": CONSEQUENCE_MULTIPLIER,
    "semantics": ("an operational ordering with no probabilistic interpretation; it never modifies a physical "
                  "probability, and health evidence never escalates it because no dataset links telemetry to a "
                  "catalogued object (C4)"),
    "interval_use": "none: the rule uses the point probability only; the 5-95 % interval is carried as a flag",
}


def decision_priority(context: ModuleContext) -> ModuleResult:
    """Rank objects for review, keeping physical probability separate from priority.

    Priority is an *operational ordering* built from the re-entry probability, the
    consequence proxy and the evidence state. It never modifies a physical probability, and
    it never escalates on health evidence unless the configuration asserts that the health
    and risk records refer to the same object -- which the public data do not support.
    """
    reentry: Mapping[str, ReentryPrediction] = context.outputs["reentry"]["reentry"]
    lifetime: Mapping[str, LifetimeEstimate] = context.outputs["lifetime"]["lifetime"]
    characteristics = context.outputs["catalogue_state"]["characteristics"]
    names = context.outputs["catalogue_state"]["name"]
    regimes = context.outputs["catalogue_state"]["regime"]
    as_of = context.config["as_of"]
    root = Path(context.config.get("root", ROOT))

    health_linked = bool(context.config.get("health_identity_linked", False))
    health_available = "health" in context.outputs
    horizon = HORIZON_DAYS["30d"]

    rows: list[dict[str, Any]] = []
    for object_id, prediction in reentry.items():
        probability = prediction.probability_by_horizon[horizon]
        mass = getattr(characteristics.get(object_id), "mass_kg", None)
        high_consequence = mass is not None and mass >= CONSEQUENCE_MASS_KG
        # Priority is a product of probability and a consequence multiplier; it is a ranking
        # score with no probabilistic interpretation.
        priority = probability * (CONSEQUENCE_MULTIPLIER if high_consequence else 1.0)
        rows.append({
            "object_id": object_id,
            "name": names.get(object_id, ""),
            "regime": regimes.get(object_id, "unknown"),
            "p_reentry_30d": probability,
            "mass_kg": mass,
            "mass_known": mass is not None,
            "high_consequence": high_consequence,
            "priority_score": priority,
            "lifetime_evidence": object_id in lifetime,
            "reentry_interval_available": prediction.uncertainty.kind == "quantiles",
        })
    ranking = pd.DataFrame(rows).sort_values(
        ["priority_score", "p_reentry_30d"], ascending=False
    ).reset_index(drop=True)

    if health_available and not health_linked:
        escalation = ModuleEvidence(
            module="decision_priority",
            status="abstain",
            payload=None,
            reason=("health evidence is present but not identity-linked to these objects: "
                    "ESA-ADB missions are anonymised and share no identifier with the "
                    "catalogue, so no health-driven escalation (C4) can be computed"),
        )
    elif not health_available:
        escalation = ModuleEvidence(
            module="decision_priority",
            status="abstain",
            payload=None,
            reason="no health module output was requested in this run",
        )
    else:
        escalation = ModuleEvidence(
            module="decision_priority",
            status="abstain",
            payload=None,
            reason=("health_identity_linked was asserted by configuration, but this "
                    "repository contains no dataset that links telemetry health to a "
                    "catalogued object; escalation stays unavailable"),
        )

    provenance = Provenance(
        as_of=as_of,
        input_sources=("COSMOS re-entry forecast", "COSMOS lifetime expert", "GCAT mass"),
        code_revision=git_revision(root)["git_commit"],
        upstream_outputs=("catalogue_state", "lifetime", "reentry"),
    )
    return ModuleResult(
        outputs={
            "ranking": ranking,
            "health_escalation": escalation,
            "consequence_mass_kg": CONSEQUENCE_MASS_KG,
            "priority_rule": dict(PRIORITY_RULE),
        },
        provenance=provenance,
    )


# ------------------------------------------------------------------------ assembly
def default_modules() -> tuple[ModuleSpec, ...]:
    """Module graph of the adapters.

    The catalogue chain is dependency-linked. Health, collision and debris are independent
    roots, so a missing imagery or telemetry artifact cannot block the catalogue chain.
    """
    from .twin.modules import twin_equivalence, twin_state_records   # P3-B: additional evidence root + its check
    return (
        ModuleSpec("catalogue_state", catalogue_state),
        ModuleSpec("lifetime", lifetime_estimates, depends_on=("catalogue_state",)),
        ModuleSpec("reentry", reentry_predictions, depends_on=("catalogue_state",)),
        ModuleSpec("collision", collision_risk),
        ModuleSpec("health", health_estimates),
        ModuleSpec("debris", debris_detections),
        ModuleSpec("twin_state", twin_state_records),
        ModuleSpec("twin_equivalence", twin_equivalence,
                   depends_on=("twin_state", "catalogue_state", "lifetime", "reentry")),
        ModuleSpec("decision_priority", decision_priority,
                   depends_on=("catalogue_state", "lifetime", "reentry")),
    )
