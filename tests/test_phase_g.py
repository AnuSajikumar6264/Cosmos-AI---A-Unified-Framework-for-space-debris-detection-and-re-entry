"""Tests for the Phase G+ lifetime-optimization candidates.

The blend construction and the promotion rule are tested against hand-built cases, so a
candidate cannot be promoted by accident and the combiners cannot silently change.

Passing these tests says the candidate machinery is correct. It says nothing about whether any
candidate is scientifically better — Phase G+ promoted none on accuracy.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from cosmos.ai.provenance import ROOT
from scripts.phase_g_lifetime_optimization import build_blend, build_blend_bounds

G_RESULTS = ROOT / "outputs" / "phase_g_lifetime" / "phase_g_lifetime_results.json"
MH_RESULTS = ROOT / "outputs" / "phase_g_multihorizon" / "multihorizon_results.json"


def _data(**members) -> dict:
    return {f"{name}__q": np.asarray(value, dtype=float) for name, value in members.items()}


def test_median_blend_is_the_row_wise_median_and_monotone() -> None:
    data = _data(a=[[1.0, 2.0, 3.0]], b=[[2.0, 3.0, 4.0]], c=[[9.0, 9.0, 9.0]])
    blend = build_blend(data, ("a", "b", "c"), "median")
    # Median of {1,2,9}=2, {2,3,9}=3, {3,4,9}=4.
    assert blend.tolist() == [[2.0, 3.0, 4.0]]
    assert np.all(np.diff(blend, axis=1) >= 0)


def test_mean_blend_is_the_row_wise_mean() -> None:
    data = _data(a=[[1.0, 2.0, 3.0]], b=[[3.0, 4.0, 5.0]])
    assert build_blend(data, ("a", "b"), "mean").tolist() == [[2.0, 3.0, 4.0]]


def test_median_is_robust_to_one_collapsed_member() -> None:
    """The observed failure mode: one member scores far worse than the others."""
    good_a = [[1.0, 2.0, 3.0]]
    good_b = [[1.1, 2.1, 3.1]]
    collapsed = [[100.0, 100.0, 100.0]]
    data = _data(a=good_a, b=good_b, c=collapsed)

    median = build_blend(data, ("a", "b", "c"), "median")
    mean = build_blend(data, ("a", "b", "c"), "mean")

    # The median tracks the healthy members; the mean is dragged toward the outlier.
    assert median[0, 0] == pytest.approx(1.1)
    assert mean[0, 0] > 30.0


def test_blend_enforces_monotonicity_when_members_cross() -> None:
    data = _data(a=[[3.0, 1.0, 2.0]], b=[[3.0, 1.0, 2.0]])
    blend = build_blend(data, ("a", "b"), "mean")
    assert blend.tolist() == [[1.0, 2.0, 3.0]]


def test_blend_requires_at_least_two_members() -> None:
    assert build_blend(_data(a=[[1.0, 2.0]]), ("a",), "median") is None
    assert build_blend(_data(a=[[1.0, 2.0]]), ("a", "absent"), "median") is None


def test_blend_bounds_are_ordered_low_then_high() -> None:
    data = {"a__lo90": np.array([5.0]), "a__hi90": np.array([1.0]),
            "b__lo90": np.array([4.0]), "b__hi90": np.array([2.0])}
    low, high = build_blend_bounds(data, ("a", "b"), "mean", "90")
    # Inputs are deliberately inverted; the result must still be (low, high).
    assert low[0] <= high[0]


@pytest.mark.skipif(not G_RESULTS.is_file(), reason=f"missing {G_RESULTS}")
def test_promotion_requires_improvement_at_every_origin() -> None:
    record = json.loads(G_RESULTS.read_text())
    origins = set(record["results"])

    for row in record["promotion"]:
        improved = {o for o, d in row["per_origin"].items() if d["beats_significantly"]}
        degraded = {o for o, d in row["per_origin"].items() if d["loses_significantly"]}
        expected = bool(improved == origins and not degraded)
        assert row["promote"] is expected, row["candidate"]

    # Phase G+ promoted nothing on accuracy; a change here must be deliberate.
    assert not any(row["promote"] for row in record["promotion"])


@pytest.mark.skipif(not G_RESULTS.is_file(), reason=f"missing {G_RESULTS}")
def test_phase_g_results_are_internally_consistent() -> None:
    record = json.loads(G_RESULTS.read_text())
    assert record["exploratory"] is True
    assert "exploratory" in record["exploratory_note"]
    assert record["blend_specification"]["parameters"] == "none"

    for origin, entry in record["results"].items():
        if entry.get("status") != "evaluated":
            continue
        for contrast in entry["contrasts"]:
            assert contrast["ci95_lo"] <= contrast["mean"] <= contrast["ci95_hi"], origin
            assert contrast["p_adjusted_bh"] >= contrast["p_value"] - 1e-12
            if contrast["ci95_hi"] < 0:
                assert contrast["verdict"] == "CANDIDATE BETTER"
            elif contrast["ci95_lo"] > 0:
                assert contrast["verdict"] == "INCUMBENT BETTER"
            else:
                assert contrast["verdict"] == "INCONCLUSIVE"


@pytest.mark.skipif(not G_RESULTS.is_file(), reason=f"missing {G_RESULTS}")
def test_selection_transfer_diagnosis_is_recorded() -> None:
    """The root-cause finding must be preserved in the artifact."""
    record = json.loads(G_RESULTS.read_text())
    for origin, entry in record["selection_transfer_diagnosis"].items():
        if entry.get("status") != "evaluated":
            continue
        assert -1.0 <= entry["spearman_tuneA_vs_test"] <= 1.0
        assert entry["selected_model_test_pinball"] >= entry["best_possible_test_pinball"]


@pytest.mark.skipif(not MH_RESULTS.is_file(), reason=f"missing {MH_RESULTS}")
def test_coherent_reading_has_no_cross_horizon_violations() -> None:
    record = json.loads(MH_RESULTS.read_text())
    assert record["coherence"]["coherent_raw"]["violations"] == 0
    assert record["coherence"]["isotonic"]["violations"] > 0
    # L17 must be left alone by this analysis.
    assert "stands" in record["l17_note"]
    assert record["exploratory"] is True


@pytest.mark.skipif(not MH_RESULTS.is_file(), reason=f"missing {MH_RESULTS}")
def test_multihorizon_reports_the_overforecasting_caveat() -> None:
    """Neither reading may be presented as calibrated; both over-forecast heavily."""
    record = json.loads(MH_RESULTS.read_text())
    for horizon, entry in record["per_horizon"].items():
        for reading, metrics in entry.items():
            assert metrics["expected_over_observed"] > 1.0, f"{horizon}/{reading}"
    assert any("event counts" in item or "non-blind" in item
               for item in record["not_established"])
