"""Level 2 integration checks for the adapter layer.

These tests exercise module-to-module behaviour: dependency handling, partial execution,
uncertainty semantics, provenance preservation and the separation of physical probability
from operational priority. They assert *interface* behaviour on real saved artifacts; they
do not re-evaluate any scientific result, and passing them is not scientific validation.

Tests that need a saved artifact skip when it is absent, so a fresh clone without the large
outputs reports SKIP rather than a false PASS.
"""
from __future__ import annotations

import pytest

from cosmos.ai import adapters
from cosmos.ai.contracts import (
    CollisionRiskEstimate,
    HealthEstimate,
    LifetimeEstimate,
    ModuleEvidence,
    OrbitalElements,
    Provenance,
    ReentryPrediction,
)
from cosmos.ai.orchestration import ModuleSpec, Orchestrator
from cosmos.ai.provenance import ROOT

AS_OF = "2026-10-27"
CONFIG = {
    "as_of": AS_OF,
    "limit": 150,
    "collision_limit": 40,
    "debris_sequence_limit": 2,
    "health_calibrator": "conformal_bh",
}

SNAPSHOT = ROOT / adapters.TWIN_SNAPSHOT.format(as_of=AS_OF)
CONJUNCTION = ROOT / adapters.CONJUNCTION_PREDICTIONS
TELEMETRY = ROOT / adapters.TELEMETRY_RESULTS
SPOTGEO = ROOT / adapters.SPOTGEO_SUBMISSION

needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason=f"missing {SNAPSHOT}")
needs_conjunction = pytest.mark.skipif(not CONJUNCTION.is_file(), reason=f"missing {CONJUNCTION}")
needs_telemetry = pytest.mark.skipif(not TELEMETRY.is_file(), reason=f"missing {TELEMETRY}")
needs_spotgeo = pytest.mark.skipif(not SPOTGEO.is_file(), reason=f"missing {SPOTGEO}")


@pytest.fixture(scope="module")
def execution():
    runner = Orchestrator(adapters.default_modules())
    return runner.run({}, config=CONFIG)


# ------------------------------------------------------------------ catalogue chain
@needs_snapshot
def test_catalogue_chain_is_identity_linked(execution) -> None:
    """Elements, lifetime and re-entry must describe the *same* objects."""
    state = execution.modules["catalogue_state"]
    lifetime = execution.modules["lifetime"]
    reentry = execution.modules["reentry"]
    assert state.status == "success"
    assert lifetime.status == reentry.status == "success"

    objects = set(state.outputs["elements"])
    assert objects, "snapshot produced no objects"
    assert set(reentry.outputs["reentry"]) <= objects
    assert set(lifetime.outputs["lifetime"]) <= objects
    # Every snapshot object is either estimated or explicitly abstained for -- never dropped.
    assert objects == set(reentry.outputs["reentry"]) | set(reentry.outputs["abstained"])
    assert objects == set(lifetime.outputs["lifetime"]) | set(lifetime.outputs["abstained"])


@needs_snapshot
def test_uncertainty_semantics_are_preserved_per_module(execution) -> None:
    """Each module keeps its own uncertainty representation; none collapses to a score."""
    lifetime = execution.modules["lifetime"].outputs["lifetime"]
    reentry = execution.modules["reentry"].outputs["reentry"]

    for estimate in lifetime.values():
        assert isinstance(estimate, LifetimeEstimate)
        assert estimate.uncertainty.kind == "quantiles"
        assert len(estimate.uncertainty.quantiles) >= 2
        assert estimate.uncertainty.assumptions, "quantile assumptions must travel with it"

    kinds = {prediction.uncertainty.kind for prediction in reentry.values()}
    assert kinds <= {"quantiles", "score"}
    for prediction in reentry.values():
        assert isinstance(prediction, ReentryPrediction)
        if prediction.uncertainty.kind == "quantiles":
            # Monte Carlo spread must not be advertised as a conformal guarantee.
            joined = " ".join(prediction.uncertainty.assumptions).lower()
            assert "not a conformal" in joined


@needs_snapshot
def test_noncoherent_calibrated_probabilities_abstain_rather_than_being_repaired(execution) -> None:
    """A non-monotone saved CDF is reported, not silently overwritten."""
    outputs = execution.modules["lifetime"].outputs
    flagged = outputs["noncoherent_horizon_probabilities"]
    for object_id, probabilities in flagged.items():
        ordered = [probabilities[key] for key in sorted(probabilities, key=float)]
        assert any(a > b for a, b in zip(ordered, ordered[1:])), "flagged row is actually monotone"
        assert object_id not in outputs["lifetime"]
        assert "monotone" in outputs["abstained"][object_id]


@needs_snapshot
def test_provenance_records_the_artifact_digest_and_code_revision(execution) -> None:
    for name in ("catalogue_state", "lifetime", "reentry"):
        module = execution.modules[name]
        provenance = module.provenance
        assert isinstance(provenance, Provenance)
        assert provenance.as_of == AS_OF
        assert provenance.input_sources
        assert provenance.input_hashes, f"{name} recorded no artifact digest"
        assert provenance.config_digest == execution.config_sha256
        for digest in provenance.input_hashes.values():
            assert len(digest) == 64


@needs_snapshot
def test_elements_are_elements_not_invented_state_vectors(execution) -> None:
    """Catalogue mean elements must not be presented as an instantaneous state vector."""
    for element in execution.modules["catalogue_state"].outputs["elements"].values():
        assert isinstance(element, OrbitalElements)
        assert element.apogee_altitude_km >= element.perigee_altitude_km
        assert 0.0 <= element.inclination_deg <= 180.0
        assert element.element_set == "catalogue mean elements"


# --------------------------------------------------------- physical risk vs. priority
@needs_conjunction
def test_collision_module_reports_physical_probability_without_priority(execution) -> None:
    estimates = execution.modules["collision"].outputs["collision"]
    assert estimates
    for estimate in estimates.values():
        assert isinstance(estimate, CollisionRiskEstimate)
        assert 0.0 <= estimate.collision_probability <= 1.0
        # Priority must not be fused into the physical probability.
        assert estimate.priority_score is None
        assert estimate.uncertainty.kind == "interval"
        joined = " ".join(estimate.uncertainty.assumptions).lower()
        assert "not an operational" in joined
    assert execution.modules["collision"].outputs["identity_linkable"] is False


@needs_snapshot
@needs_telemetry
def test_health_evidence_does_not_escalate_without_identity_linkage(execution) -> None:
    """C4 must abstain: ESA-ADB missions share no identifier with the catalogue."""
    escalation = execution.modules["decision_priority"].outputs["health_escalation"]
    assert isinstance(escalation, ModuleEvidence)
    assert escalation.status == "abstain"
    assert escalation.payload is None
    assert "identity-linked" in escalation.reason or "links telemetry" in escalation.reason

    for estimate in execution.modules["health"].outputs["health"].values():
        assert isinstance(estimate, HealthEstimate)
        # An F0.5 benchmark score must not be read as a per-object anomaly probability.
        assert estimate.score_kind == "score"
        assert "not a per-object anomaly" in estimate.score_semantics


@needs_snapshot
def test_priority_is_ordering_only_and_leaves_probabilities_untouched(execution) -> None:
    ranking = execution.modules["decision_priority"].outputs["ranking"]
    reentry = execution.modules["reentry"].outputs["reentry"]
    assert not ranking.empty
    assert ranking["priority_score"].is_monotonic_decreasing

    for row in ranking.itertuples(index=False):
        source = reentry[row.object_id].probability_by_horizon[adapters.HORIZON_DAYS["30d"]]
        # The decision layer may reorder objects; it may not alter the physical forecast.
        assert row.p_reentry_30d == source
        assert 0.0 <= row.p_reentry_30d <= 1.0
        if row.mass_known:
            assert row.high_consequence == (row.mass_kg >= adapters.CONSEQUENCE_MASS_KG)
        else:
            # Unknown mass must not be silently treated as low consequence.
            assert row.high_consequence is False


@needs_spotgeo
def test_debris_detections_record_absent_scores_and_times(execution) -> None:
    detections = execution.modules["debris"].outputs["detections"]
    assert detections
    for detection in detections:
        assert detection.confidence is None     # hard-thresholding front end has no score
        assert detection.observed_at is None    # SpotGEO frames carry no absolute UTC time
        assert detection.frame_index is not None
    assert execution.modules["debris"].outputs["astrometric_calibration"] is False


# ------------------------------------------------------------- partial execution
@needs_snapshot
def test_missing_imagery_does_not_block_independent_analysis() -> None:
    """Selecting the catalogue chain alone must not require imagery or telemetry."""
    runner = Orchestrator(adapters.default_modules())
    result = runner.run({}, selected=("decision_priority",), config=CONFIG)

    assert result.successful
    for name in ("catalogue_state", "lifetime", "reentry", "decision_priority"):
        assert result.modules[name].status == "success"
    for name in ("debris", "health", "collision"):
        assert result.modules[name].status == "not_requested"


@needs_snapshot
def test_unavailable_artifact_fails_explicitly_and_blocks_only_dependants() -> None:
    """A missing artifact must produce no output and must not be worked around."""
    modules = list(adapters.default_modules())

    def unavailable(_context):
        raise adapters.ArtifactUnavailable("required artifact is not present: fixture")

    patched = tuple(
        ModuleSpec("lifetime", unavailable, depends_on=("catalogue_state",))
        if spec.name == "lifetime" else spec
        for spec in modules
    )
    result = Orchestrator(patched).run({}, config=CONFIG)

    assert not result.successful
    assert result.modules["lifetime"].status == "failed"
    assert "ArtifactUnavailable" in result.modules["lifetime"].error
    assert result.modules["lifetime"].outputs == {}
    # Only the dependant is blocked; independent work still completes.
    assert result.modules["decision_priority"].status == "blocked"
    assert "lifetime" in result.modules["decision_priority"].reason
    assert result.modules["reentry"].status == "success"
    assert result.modules["catalogue_state"].status == "success"


@needs_snapshot
def test_missing_required_input_is_reported_as_blocked() -> None:
    runner = Orchestrator((
        ModuleSpec("catalogue_state", adapters.catalogue_state),
        ModuleSpec("needs_imagery", adapters.debris_detections, required_inputs=("images",)),
    ))
    result = runner.run({}, config=CONFIG)

    assert result.modules["needs_imagery"].status == "blocked"
    assert "images" in result.modules["needs_imagery"].reason
    assert result.modules["catalogue_state"].status == "success"


@needs_snapshot
def test_unknown_conjunction_model_is_refused_not_substituted() -> None:
    runner = Orchestrator((ModuleSpec("collision", adapters.collision_risk),))
    result = runner.run({}, config={**CONFIG, "collision_model": "no_such_model"})

    assert result.modules["collision"].status == "failed"
    assert "no_such_model" in result.modules["collision"].error
