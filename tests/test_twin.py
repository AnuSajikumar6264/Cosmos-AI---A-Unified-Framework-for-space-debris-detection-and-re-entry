"""Dataset-free contracts and coupling tests for the digital-twin output path."""
from __future__ import annotations

import json

import numpy as np
import pytest

from cosmos.ai.twin.couplings import survival_from_quantiles
from cosmos.ai.twin.state import ModuleOutput, ObjectTwin, OutputProvenance, classify_regime


def test_output_provenance_and_twin_serialize() -> None:
    provenance = OutputProvenance(
        as_of="2026-10-27",
        input_sources=("GCAT", "CelesTrak SATCAT snapshot 2026-10-27"),
        input_hashes={"satcat.csv": "a" * 64},
    )
    output = ModuleOutput(
        module="reentry",
        model="physics prior",
        validation="benchmark only",
        values={"p_reentry_30d": 0.1},
        uncertainty={"interval90_days": [1.0, 20.0]},
        provenance=provenance,
    )
    twin = ObjectTwin(
        object_id="12345",
        name="example",
        object_class="D",
        as_of="2026-10-27",
        orbit={},
        physical={},
        operational_status=None,
        family={},
        space_weather={},
    )
    twin.attach(output)

    encoded = json.dumps(twin.to_dict())
    decoded = json.loads(encoded)
    assert decoded["outputs"][0]["provenance"]["input_sources"] == [
        "GCAT",
        "CelesTrak SATCAT snapshot 2026-10-27",
    ]
    assert decoded["outputs"][0]["provenance"]["input_hashes"]["satcat.csv"] == "a" * 64


@pytest.mark.parametrize(
    ("object_class", "status", "expected"),
    [
        ("P", "+", "operator_controlled"),
        ("P", "P", "operator_controlled"),
        ("P", "B", "operator_controlled"),
        ("P", "S", "operator_controlled"),
        ("P", "X", "operator_controlled"),
        ("P", "-", "natural_decay"),
        ("P", None, "unknown"),
        ("D", "+", "natural_decay"),
        ("R", None, "natural_decay"),
    ],
)
def test_c3_regime_rules(object_class: str, status: str | None, expected: str) -> None:
    assert classify_regime(object_class, status) == expected


def test_c3_rejects_unknown_object_class() -> None:
    with pytest.raises(ValueError, match="unsupported object class"):
        classify_regime("?", None)


def test_contracts_reject_invalid_dates_hashes_and_abstention() -> None:
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        OutputProvenance(as_of="27-10-2026", input_sources=("GCAT",))
    with pytest.raises(ValueError, match="SHA-256"):
        OutputProvenance(as_of="2026-10-27", input_sources=("GCAT",), input_hashes={"gcat": "abc"})
    with pytest.raises(ValueError, match="must include a reason"):
        ModuleOutput("reentry", "model", "unvalidated", {}, abstain=True)


def test_c2_survival_is_bounded_and_nonincreasing() -> None:
    quantiles = np.array([[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]])
    survival = survival_from_quantiles(quantiles, np.array([30.0, 180.0, 365.0, 730.0]))[0]

    assert np.all(np.isfinite(survival))
    assert np.all((survival >= 0.0) & (survival <= 1.0))
    assert np.all(np.diff(survival) <= 0.0)


def test_module_output_must_match_twin_as_of_date() -> None:
    twin = ObjectTwin(
        object_id="12345",
        name="example",
        object_class="D",
        as_of="2026-10-27",
        orbit={},
        physical={},
        operational_status=None,
        family={},
        space_weather={},
    )
    output = ModuleOutput(
        "reentry",
        "model",
        "benchmark only",
        {},
        provenance=OutputProvenance(as_of="2026-10-26", input_sources=("GCAT",)),
    )

    with pytest.raises(ValueError, match="must match"):
        twin.attach(output)
