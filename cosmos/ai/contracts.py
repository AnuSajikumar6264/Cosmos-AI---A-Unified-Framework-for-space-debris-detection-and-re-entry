"""Typed, validated data contracts shared by COSMOS-AI modules.

These contracts validate interface structure and declared units. They do not certify
measurement accuracy, coordinate transformations, calibration, or scientific validity.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Literal, Mapping

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_FRAMES = {"GCRF", "EME2000", "TEME", "ITRF", "ITRS"}


def _validate_date(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{name} must be YYYY-MM-DD")


def _validate_timestamp(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an ISO-8601 timestamp string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone")


def _validate_time_provenance(timestamp: str, provenance: Provenance, name: str) -> None:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    timestamp_date = parsed.astimezone(timezone.utc).date().isoformat()
    if timestamp_date != provenance.as_of:
        raise ValueError(f"{name} date must match provenance.as_of in UTC")


def _nonempty(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


def _probability(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be finite and in [0, 1]")


@dataclass(frozen=True)
class Provenance:
    """Source and execution lineage; optional digests are never guessed."""

    as_of: str
    input_sources: tuple[str, ...]
    input_hashes: Mapping[str, str] = field(default_factory=dict)
    code_revision: str | None = None
    config_digest: str | None = None
    model_digest: str | None = None
    upstream_outputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_date(self.as_of, "provenance.as_of")
        if not self.input_sources:
            raise ValueError("provenance.input_sources must not be empty")
        for source in self.input_sources:
            _nonempty(source, "provenance input source")
        for name, digest in self.input_hashes.items():
            _nonempty(name, "provenance input name")
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValueError(f"input hash for {name!r} must be a SHA-256 hex digest")
        for name in ("config_digest", "model_digest"):
            digest = getattr(self, name)
            if digest is not None and not _SHA256.fullmatch(digest):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
        if self.code_revision is not None:
            _nonempty(self.code_revision, "provenance.code_revision")


@dataclass(frozen=True)
class Uncertainty:
    """Uncertainty description that preserves its semantics rather than collapsing it."""

    kind: Literal["interval", "quantiles", "samples", "score", "none"]
    method: str
    level: float | None = None
    lower: float | None = None
    upper: float | None = None
    quantiles: tuple[tuple[float, float], ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in {"interval", "quantiles", "samples", "score", "none"}:
            raise ValueError(f"unsupported uncertainty kind: {self.kind!r}")
        _nonempty(self.method, "uncertainty.method")
        if self.level is not None:
            _probability(self.level, "uncertainty.level")
        if self.kind == "interval":
            if self.lower is None or self.upper is None:
                raise ValueError("interval uncertainty requires lower and upper")
            if not math.isfinite(self.lower) or not math.isfinite(self.upper) or self.lower > self.upper:
                raise ValueError("uncertainty interval bounds must be finite and ordered")
        if self.kind == "quantiles":
            if not self.quantiles:
                raise ValueError("quantile uncertainty requires at least one quantile")
            levels = [level for level, _ in self.quantiles]
            values = [value for _, value in self.quantiles]
            if any(not math.isfinite(level) or not 0 <= level <= 1 for level in levels):
                raise ValueError("quantile levels must be finite and in [0, 1]")
            if any(not math.isfinite(value) for value in values):
                raise ValueError("quantile values must be finite")
            if levels != sorted(levels) or values != sorted(values):
                raise ValueError("quantile levels and values must be nondecreasing")


@dataclass(frozen=True)
class TelemetryBatch:
    spacecraft_id: str
    start: str
    sample_period_s: float
    channels: Mapping[str, tuple[float | None, ...]]
    provenance: Provenance

    def __post_init__(self) -> None:
        _nonempty(self.spacecraft_id, "telemetry.spacecraft_id")
        _validate_timestamp(self.start, "telemetry.start")
        if not math.isfinite(self.sample_period_s) or self.sample_period_s <= 0:
            raise ValueError("telemetry.sample_period_s must be finite and positive")
        if not self.channels:
            raise ValueError("telemetry.channels must not be empty")
        lengths = set()
        for channel, values in self.channels.items():
            _nonempty(channel, "telemetry channel")
            lengths.add(len(values))
            for value in values:
                if value is not None and not math.isfinite(value):
                    raise ValueError(f"telemetry channel {channel!r} contains a non-finite value")
        if len(lengths) != 1 or 0 in lengths:
            raise ValueError("telemetry channels must have the same nonzero sample count")


@dataclass(frozen=True)
class HealthEstimate:
    spacecraft_id: str
    as_of: str
    model: str
    status: str
    anomaly_score: float | None
    score_semantics: str
    alarm: bool
    uncertainty: Uncertainty
    provenance: Provenance
    score_kind: Literal["score", "probability"] = "score"

    def __post_init__(self) -> None:
        _nonempty(self.spacecraft_id, "health.spacecraft_id")
        _validate_timestamp(self.as_of, "health.as_of")
        _validate_time_provenance(self.as_of, self.provenance, "health.as_of")
        _nonempty(self.model, "health.model")
        _nonempty(self.status, "health.status")
        _nonempty(self.score_semantics, "health.score_semantics")
        if self.anomaly_score is not None:
            if not math.isfinite(self.anomaly_score):
                raise ValueError("health.anomaly_score must be finite")
            if self.score_kind == "probability":
                _probability(self.anomaly_score, "health.anomaly_score")
        if self.score_kind not in {"score", "probability"}:
            raise ValueError(f"unsupported health score kind: {self.score_kind!r}")


@dataclass(frozen=True)
class OrbitalState:
    object_id: str
    epoch: str
    frame: str
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]
    provenance: Provenance

    def __post_init__(self) -> None:
        _nonempty(self.object_id, "orbit.object_id")
        _validate_timestamp(self.epoch, "orbit.epoch")
        _validate_time_provenance(self.epoch, self.provenance, "orbit.epoch")
        if self.frame not in _FRAMES:
            raise ValueError(f"unsupported coordinate frame: {self.frame!r}")
        for name, vector in (("position_m", self.position_m), ("velocity_m_s", self.velocity_m_s)):
            if len(vector) != 3 or any(not math.isfinite(v) for v in vector):
                raise ValueError(f"orbit.{name} must contain three finite SI values")


@dataclass(frozen=True)
class OrbitalElements:
    """Mean orbital elements as published by a catalogue.

    Catalogue snapshots (CelesTrak SATCAT, GCAT) publish perigee/apogee altitudes and
    inclination, not an instantaneous state vector. Converting them into a position and
    velocity would invent information that the source does not contain, so this contract
    carries the elements as given and records the altitude reference radius used.
    """

    object_id: str
    epoch: str
    perigee_altitude_km: float
    apogee_altitude_km: float
    inclination_deg: float
    provenance: Provenance
    reference_radius_km: float = 6378.137
    element_set: str = "catalogue mean elements"

    def __post_init__(self) -> None:
        _nonempty(self.object_id, "elements.object_id")
        _nonempty(self.element_set, "elements.element_set")
        _validate_timestamp(self.epoch, "elements.epoch")
        _validate_time_provenance(self.epoch, self.provenance, "elements.epoch")
        for name in ("perigee_altitude_km", "apogee_altitude_km", "inclination_deg",
                     "reference_radius_km"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"elements.{name} must be finite")
        if self.apogee_altitude_km < self.perigee_altitude_km:
            raise ValueError("elements.apogee_altitude_km must not be below perigee")
        if self.perigee_altitude_km <= -self.reference_radius_km:
            raise ValueError("elements.perigee_altitude_km must be above the body centre")
        if not 0.0 <= self.inclination_deg <= 180.0:
            raise ValueError("elements.inclination_deg must be within [0, 180]")
        if self.reference_radius_km <= 0:
            raise ValueError("elements.reference_radius_km must be positive")


@dataclass(frozen=True)
class DebrisDetection:
    """One image-plane detection.

    ``observed_at`` and ``confidence`` are optional because real benchmark detectors do not
    always supply them: the SpotGEO sequences carry a frame index rather than an absolute
    UTC time, and a hard-thresholding front end emits detections without a score. Leaving
    these ``None`` records the absence instead of inventing a timestamp or a confidence.
    At least one time reference (absolute or frame index) is required.
    """

    image_id: str
    observed_at: str | None
    x_px: float
    y_px: float
    confidence: float | None
    detector: str
    provenance: Provenance
    frame_index: int | None = None

    def __post_init__(self) -> None:
        _nonempty(self.image_id, "detection.image_id")
        _nonempty(self.detector, "detection.detector")
        if self.observed_at is None and self.frame_index is None:
            raise ValueError("detection requires observed_at or frame_index")
        if self.observed_at is not None:
            _validate_timestamp(self.observed_at, "detection.observed_at")
            _validate_time_provenance(self.observed_at, self.provenance, "detection.observed_at")
        if self.frame_index is not None:
            if isinstance(self.frame_index, bool) or not isinstance(self.frame_index, int):
                raise TypeError("detection.frame_index must be an integer")
            if self.frame_index < 0:
                raise ValueError("detection.frame_index must be nonnegative")
        if not math.isfinite(self.x_px) or not math.isfinite(self.y_px):
            raise ValueError("detection pixel coordinates must be finite")
        if self.confidence is not None:
            _probability(self.confidence, "detection.confidence")


@dataclass(frozen=True)
class ObjectCharacteristics:
    object_id: str
    mass_kg: float | None = None
    length_m: float | None = None
    diameter_m: float | None = None
    area_m2: float | None = None
    source: str = "unknown"
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        _nonempty(self.object_id, "characteristics.object_id")
        _nonempty(self.source, "characteristics.source")
        for name in ("mass_kg", "length_m", "diameter_m", "area_m2"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"characteristics.{name} must be finite and positive")


@dataclass(frozen=True)
class LifetimeEstimate:
    object_id: str
    as_of: str
    model: str
    quantiles_days: tuple[tuple[float, float], ...]
    horizon_probabilities: Mapping[float, float]
    uncertainty: Uncertainty
    provenance: Provenance

    def __post_init__(self) -> None:
        _nonempty(self.object_id, "lifetime.object_id")
        _validate_timestamp(self.as_of, "lifetime.as_of")
        _validate_time_provenance(self.as_of, self.provenance, "lifetime.as_of")
        _nonempty(self.model, "lifetime.model")
        if self.uncertainty.kind != "quantiles":
            raise ValueError("lifetime uncertainty must preserve quantile semantics")
        Uncertainty(kind="quantiles", method=self.uncertainty.method, quantiles=self.quantiles_days)
        if any(value <= 0 for _, value in self.quantiles_days):
            raise ValueError("lifetime quantiles must be positive days")
        horizons = sorted(self.horizon_probabilities)
        probabilities = [self.horizon_probabilities[h] for h in horizons]
        if any(a > b for a, b in zip(probabilities, probabilities[1:])):
            raise ValueError("lifetime horizon probabilities must be nondecreasing")
        for horizon, probability in self.horizon_probabilities.items():
            if not math.isfinite(horizon) or horizon <= 0:
                raise ValueError("lifetime horizons must be finite and positive days")
            _probability(probability, f"lifetime probability at {horizon} days")


@dataclass(frozen=True)
class CollisionRiskEstimate:
    object_id: str
    as_of: str
    model: str
    collision_probability: float
    uncertainty: Uncertainty
    provenance: Provenance
    priority_score: float | None = None

    def __post_init__(self) -> None:
        _nonempty(self.object_id, "collision.object_id")
        _validate_timestamp(self.as_of, "collision.as_of")
        _validate_time_provenance(self.as_of, self.provenance, "collision.as_of")
        _nonempty(self.model, "collision.model")
        _probability(self.collision_probability, "collision.collision_probability")
        if self.priority_score is not None and (
            not math.isfinite(self.priority_score) or self.priority_score < 0
        ):
            raise ValueError("collision.priority_score must be finite and nonnegative")


@dataclass(frozen=True)
class ReentryPrediction:
    object_id: str
    as_of: str
    model: str
    probability_by_horizon: Mapping[float, float]
    time_quantiles_days: tuple[tuple[float, float], ...]
    uncertainty: Uncertainty
    provenance: Provenance

    def __post_init__(self) -> None:
        _nonempty(self.object_id, "reentry.object_id")
        _validate_timestamp(self.as_of, "reentry.as_of")
        _validate_time_provenance(self.as_of, self.provenance, "reentry.as_of")
        _nonempty(self.model, "reentry.model")
        if self.time_quantiles_days and self.uncertainty.kind != "quantiles":
            raise ValueError("re-entry time uncertainty must preserve quantile semantics")
        for horizon, probability in self.probability_by_horizon.items():
            if not math.isfinite(horizon) or horizon <= 0:
                raise ValueError("re-entry horizons must be finite and positive days")
            _probability(probability, f"re-entry probability at {horizon} days")
        if self.time_quantiles_days:
            Uncertainty(kind="quantiles", method=self.uncertainty.method,
                        quantiles=self.time_quantiles_days)
            if any(value <= 0 for _, value in self.time_quantiles_days):
                raise ValueError("re-entry time quantiles must be positive days")
        horizons = sorted(self.probability_by_horizon)
        probabilities = [self.probability_by_horizon[h] for h in horizons]
        if any(a > b for a, b in zip(probabilities, probabilities[1:])):
            raise ValueError("re-entry horizon probabilities must be nondecreasing")


@dataclass(frozen=True)
class ModuleEvidence:
    """Validated module result envelope used by orchestration and decision layers."""

    module: str
    status: Literal["success", "abstain"]
    payload: Any
    reason: str = ""
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        _nonempty(self.module, "evidence.module")
        if self.status == "abstain":
            _nonempty(self.reason, "evidence.reason")
