"""The decision layer must never let telemetry health change an object's priority.

Phase 2.2 of the completion directive asks whether anomaly evidence produces appropriate
health-state updates. In this repository the appropriate update is *none*: ESA-ADB missions are
anonymised and share no identifier with the catalogue, so `adapters.decision_priority` abstains
from health-driven escalation on every path. `tests/test_integration.py` already covers the
"health present but not linked" branch; these tests cover the other two branches and the
property that matters operationally -- the ranking is identical with and without health evidence.
"""
from __future__ import annotations

import pandas as pd
import pytest

from cosmos.ai import adapters
from cosmos.ai.contracts import ModuleEvidence
from cosmos.ai.orchestration import Orchestrator
from cosmos.ai.provenance import ROOT

AS_OF = "2026-10-27"
BASE = {"as_of": AS_OF, "limit": 60, "collision_limit": 5, "debris_sequence_limit": 1,
        "health_calibrator": "conformal_bh"}
SNAPSHOT = ROOT / adapters.TWIN_SNAPSHOT.format(as_of=AS_OF)
TELEMETRY = ROOT / adapters.TELEMETRY_RESULTS

pytestmark = pytest.mark.skipif(not (SNAPSHOT.is_file() and TELEMETRY.is_file()),
                                reason="twin snapshot or ESA-ADB results missing")


def _run(selected: tuple[str, ...], **overrides):
    # `selected` is closed over its dependencies by the orchestrator; `health` is an independent
    # root, so it participates only when named explicitly.
    runner = Orchestrator(adapters.default_modules())
    return runner.run({}, selected=selected, config={**BASE, **overrides})


def _escalation(execution) -> ModuleEvidence:
    module = execution.modules["decision_priority"]
    assert module.status == "success", module.reason
    escalation = module.outputs["health_escalation"]
    assert isinstance(escalation, ModuleEvidence)
    return escalation


def test_health_not_requested_abstains_and_says_so():
    escalation = _escalation(_run(("decision_priority",)))
    assert escalation.status == "abstain"
    assert escalation.payload is None
    assert "no health module output" in escalation.reason


def test_asserting_linkage_by_configuration_still_abstains():
    """A config flag cannot conjure a dataset that does not exist."""
    escalation = _escalation(_run(("decision_priority", "health"), health_identity_linked=True))
    assert escalation.status == "abstain"
    assert escalation.payload is None
    assert "asserted by configuration" in escalation.reason
    assert "no dataset" in escalation.reason


def test_priority_ranking_is_identical_with_and_without_health_evidence():
    with_health = _run(("decision_priority", "health"))
    without_health = _run(("decision_priority",))
    assert with_health.modules["health"].status == "success"
    assert "health" not in without_health.modules or \
        without_health.modules["health"].status == "not_requested"
    a = with_health.modules["decision_priority"].outputs["ranking"].reset_index(drop=True)
    b = without_health.modules["decision_priority"].outputs["ranking"].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    assert a["priority_score"].is_monotonic_decreasing
