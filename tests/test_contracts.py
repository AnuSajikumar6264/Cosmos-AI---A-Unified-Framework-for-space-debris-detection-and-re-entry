"""Structural, timestamp, unit, and uncertainty contract checks."""
from __future__ import annotations

import pytest

from cosmos.ai.contracts import (
    CollisionRiskEstimate,
    DebrisDetection,
    HealthEstimate,
    LifetimeEstimate,
    ObjectCharacteristics,
    OrbitalElements,
    OrbitalState,
    Provenance,
    ReentryPrediction,
    TelemetryBatch,
    Uncertainty,
)


@pytest.fixture
def provenance() -> Provenance:
    return Provenance(
        as_of="2026-10-27",
        input_sources=("GCAT",),
        input_hashes={"gcat.tsv": "a" * 64},
    )


def test_telemetry_contract_allows_explicit_missing_values(provenance: Provenance) -> None:
    batch = TelemetryBatch(
        spacecraft_id="mission-channel-1",
        start="2026-10-27T00:00:00Z",
        sample_period_s=30.0,
        channels={"temperature": (1.0, None, 2.0), "voltage": (4.0, 4.1, 4.2)},
        provenance=provenance,
    )
    assert batch.channels["temperature"][1] is None


def test_telemetry_contract_rejects_misaligned_channels(provenance: Provenance) -> None:
    with pytest.raises(ValueError, match="same nonzero sample count"):
        TelemetryBatch(
            "mission-1", "2026-10-27T00:00:00Z", 30.0,
            {"a": (1.0, 2.0), "b": (3.0,)}, provenance,
        )


def test_prediction_contracts_validate_time_units_and_independent_priority(
    provenance: Provenance,
) -> None:
    health = HealthEstimate(
        "NORAD-123", "2026-10-27T01:00:00+00:00", "detector-v1", "monitoring",
        0.3, "uncalibrated anomaly score", False,
        Uncertainty("score", "conformal p-value"), provenance,
    )
    orbit = OrbitalState(
        "NORAD-123", "2026-10-27T01:00:00Z", "GCRF",
        (7_000_000.0, 0.0, 0.0), (0.0, 7_500.0, 0.0), provenance,
    )
    detection = DebrisDetection(
        "image-1", "2026-10-27T01:00:00Z", 150.0, 200.0, 0.8, "detector-v2", provenance,
    )
    characteristics = ObjectCharacteristics("NORAD-123", mass_kg=10.0, length_m=1.2,
                                               source="catalogue", provenance=provenance)
    lifetime = LifetimeEstimate(
        "NORAD-123", "2026-10-27T01:00:00Z", "lifetime-v1",
        ((0.1, 30.0), (0.5, 120.0), (0.9, 365.0)),
        {30.0: 0.1, 365.0: 0.9},
        Uncertainty("quantiles", "test quantile distribution",
                    quantiles=((0.1, 30.0), (0.5, 120.0), (0.9, 365.0))),
        provenance,
    )
    collision = CollisionRiskEstimate(
        "NORAD-123", "2026-10-27T01:00:00Z", "collision-v1", 1e-5,
        Uncertainty("interval", "calibrated interval", level=0.9, lower=1e-6, upper=2e-5),
        provenance, priority_score=7.0,
    )
    reentry = ReentryPrediction(
        "NORAD-123", "2026-10-27T01:00:00Z", "reentry-v1",
        {30.0: 0.1, 365.0: 0.9}, ((0.1, 30.0), (0.5, 120.0), (0.9, 365.0)),
        Uncertainty("quantiles", "Monte Carlo quantiles",
                    quantiles=((0.1, 30.0), (0.5, 120.0), (0.9, 365.0))),
        provenance,
    )

    assert health.anomaly_score == 0.3
    assert orbit.frame == "GCRF"
    assert detection.confidence == 0.8
    assert characteristics.mass_kg == 10.0
    assert lifetime.horizon_probabilities[365.0] == 0.9
    assert collision.collision_probability == 1e-5
    assert collision.priority_score == 7.0
    assert reentry.probability_by_horizon[365.0] == 0.9


def test_contracts_reject_naive_time_and_mismatched_provenance(provenance: Provenance) -> None:
    with pytest.raises(ValueError, match="timezone"):
        OrbitalState("x", "2026-10-27T01:00:00", "GCRF", (1.0, 2.0, 3.0), (4.0, 5.0, 6.0), provenance)
    wrong_day = Provenance(as_of="2026-10-26", input_sources=("GCAT",))
    with pytest.raises(ValueError, match="must match provenance.as_of"):
        DebrisDetection("image", "2026-10-27T00:00:00Z", 1.0, 2.0, 0.5, "detector", wrong_day)


def test_contracts_reject_invalid_frame_probability_and_nonmonotone_forecast(
    provenance: Provenance,
) -> None:
    with pytest.raises(ValueError, match="coordinate frame"):
        OrbitalState("x", "2026-10-27T00:00:00Z", "UNKNOWN", (1.0, 2.0, 3.0), (4.0, 5.0, 6.0), provenance)
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        DebrisDetection("image", "2026-10-27T00:00:00Z", 1.0, 2.0, 1.1, "detector", provenance)
    with pytest.raises(ValueError, match="nondecreasing"):
        ReentryPrediction(
            "x", "2026-10-27T00:00:00Z", "model", {30.0: 0.9, 365.0: 0.2}, (),
            Uncertainty("none", "not supplied"), provenance,
        )


def test_characteristics_require_positive_si_values(provenance: Provenance) -> None:
    with pytest.raises(ValueError, match="finite and positive"):
        ObjectCharacteristics("x", mass_kg=-1, provenance=provenance)


def test_health_scores_are_not_assumed_to_be_probabilities(provenance: Provenance) -> None:
    estimate = HealthEstimate(
        "NORAD-123", "2026-10-27T01:00:00Z", "detector", "monitoring",
        3.2, "uncalibrated reconstruction error", False,
        Uncertainty("score", "raw detector score"), provenance,
    )
    assert estimate.anomaly_score == 3.2
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        HealthEstimate(
            "NORAD-123", "2026-10-27T01:00:00Z", "detector", "monitoring",
            3.2, "calibrated anomaly probability", False,
            Uncertainty("score", "calibrated probability"), provenance,
            score_kind="probability",
        )


def test_uncertainty_requires_monotone_quantiles() -> None:
    with pytest.raises(ValueError, match="nondecreasing"):
        Uncertainty("quantiles", "quantile model", quantiles=((0.1, 5.0), (0.9, 4.0)))


def test_detection_records_absent_score_and_time_instead_of_inventing_them(
    provenance: Provenance,
) -> None:
    """A hard-thresholding detector has no confidence, and SpotGEO frames have no UTC time."""
    detection = DebrisDetection(
        "spotgeo-seq1-frame2", None, 493.1, 261.3, None, "classical front end",
        provenance, frame_index=2,
    )
    assert detection.confidence is None
    assert detection.observed_at is None
    assert detection.frame_index == 2


def test_detection_requires_some_time_reference(provenance: Provenance) -> None:
    with pytest.raises(ValueError, match="observed_at or frame_index"):
        DebrisDetection("image", None, 1.0, 2.0, None, "detector", provenance)


def test_orbital_elements_are_validated_without_becoming_state_vectors(
    provenance: Provenance,
) -> None:
    elements = OrbitalElements(
        "NORAD-37607", "2026-10-27T00:00:00Z", 180.0, 220.0, 51.6, provenance,
    )
    assert elements.element_set == "catalogue mean elements"
    assert elements.reference_radius_km == pytest.approx(6378.137)

    with pytest.raises(ValueError, match="must not be below perigee"):
        OrbitalElements("x", "2026-10-27T00:00:00Z", 400.0, 200.0, 10.0, provenance)
    with pytest.raises(ValueError, match=r"within \[0, 180\]"):
        OrbitalElements("x", "2026-10-27T00:00:00Z", 200.0, 400.0, 200.0, provenance)
    with pytest.raises(ValueError, match="above the body centre"):
        OrbitalElements("x", "2026-10-27T00:00:00Z", -7000.0, 400.0, 10.0, provenance)


def test_lifetime_rejects_a_noncoherent_horizon_cdf(provenance: Provenance) -> None:
    """The defect found in the saved p_lifetime_* columns must be rejected at the boundary."""
    quantiles = ((0.05, 30.0), (0.5, 120.0), (0.95, 365.0))
    with pytest.raises(ValueError, match="nondecreasing"):
        LifetimeEstimate(
            "NORAD-1", "2026-10-27T00:00:00Z", "lifetime-v1", quantiles,
            {30.0: 0.7797, 90.0: 0.60, 365.25: 0.8571},
            Uncertainty("quantiles", "quantile regression", quantiles=quantiles),
            provenance,
        )
