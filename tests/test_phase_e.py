"""Tests for the Phase E coupling-ablation statistics.

The statistical machinery is tested against hand-computed and analytically known cases, so a
reported effect, interval or corrected p-value cannot silently change. Expected values come
from outside the code under test.

Passing these tests says the statistics are computed correctly. It says nothing about whether
a coupling is scientifically valid.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from cosmos.ai.provenance import ROOT
from scripts.phase_e_coupling_ablations import (
    _pinball_per_object,
    analyse_c4,
    benjamini_hochberg,
    integration_value,
    paired_cluster_bootstrap,
)

RESULTS = ROOT / "outputs" / "phase_e" / "phase_e_results.json"


# ------------------------------------------------------- multiple-comparison correction
def test_benjamini_hochberg_matches_a_hand_computed_example() -> None:
    """Hand-worked BH on four p-values with n = 4."""
    p_values = [0.01, 0.02, 0.03, 0.40]
    result = benjamini_hochberg(p_values, alpha=0.05)

    # raw * n / rank = 0.04, 0.04, 0.04, 0.40 then enforced monotone from the largest down.
    assert result["adjusted"] == pytest.approx([0.04, 0.04, 0.04, 0.40])
    assert result["rejected"] == [True, True, True, False]


def test_benjamini_hochberg_enforces_monotonicity() -> None:
    """Adjusted p-values must be nondecreasing in the raw value."""
    raw = [0.001, 0.2, 0.3, 0.9]
    adjusted = benjamini_hochberg(raw)["adjusted"]
    assert all(a <= b + 1e-12 for a, b in zip(adjusted, adjusted[1:]))
    assert all(0.0 <= a <= 1.0 for a in adjusted)


def test_benjamini_hochberg_is_identity_for_a_single_test() -> None:
    assert benjamini_hochberg([0.03])["adjusted"] == pytest.approx([0.03])
    assert benjamini_hochberg([])["adjusted"] == []


def test_benjamini_hochberg_only_ever_increases_p_values() -> None:
    """Correction must never make a result look more significant."""
    raw = [0.001, 0.01, 0.04, 0.2, 0.6]
    adjusted = benjamini_hochberg(raw)["adjusted"]
    assert all(a >= r - 1e-12 for a, r in zip(adjusted, raw))


# ---------------------------------------------------------- paired cluster bootstrap
def test_paired_bootstrap_recovers_a_clear_constant_effect() -> None:
    """A constant negative difference must give a negative interval excluding zero."""
    difference = np.full(200, -0.5)
    clusters = np.repeat(np.arange(40), 5)
    result = paired_cluster_bootstrap(difference, clusters, n_boot=500, seed=1)

    assert result["mean"] == pytest.approx(-0.5)
    assert result["ci95_hi"] < 0
    assert result["n"] == 200
    assert result["n_clusters"] == 40
    assert result["p_value"] == pytest.approx(0.0)


def test_paired_bootstrap_reports_no_effect_as_inconclusive() -> None:
    rng = np.random.default_rng(0)
    difference = rng.normal(0.0, 1.0, 400)
    clusters = np.repeat(np.arange(80), 5)
    result = paired_cluster_bootstrap(difference, clusters, n_boot=800, seed=2)

    assert result["ci95_lo"] < 0 < result["ci95_hi"]
    assert result["p_value"] > 0.05


def test_paired_bootstrap_widens_when_observations_are_clustered() -> None:
    """Dependence within clusters must widen the interval; ignoring it would be too narrow."""
    rng = np.random.default_rng(3)
    # One shared offset per cluster: rows within a cluster are strongly dependent.
    offsets = rng.normal(0.0, 1.0, 20)
    difference = np.repeat(offsets, 20) + rng.normal(0.0, 0.01, 400)

    clustered = paired_cluster_bootstrap(difference, np.repeat(np.arange(20), 20),
                                         n_boot=800, seed=4)
    as_independent = paired_cluster_bootstrap(difference, np.arange(400),
                                              n_boot=800, seed=4)

    clustered_width = clustered["ci95_hi"] - clustered["ci95_lo"]
    independent_width = as_independent["ci95_hi"] - as_independent["ci95_lo"]
    assert clustered_width > 3 * independent_width


def test_paired_bootstrap_handles_empty_and_nonfinite_input() -> None:
    empty = paired_cluster_bootstrap(np.array([]), np.array([]), n_boot=10)
    assert empty["mean"] is None and empty["n"] == 0

    mixed = paired_cluster_bootstrap(np.array([1.0, np.nan, 1.0]),
                                     np.array([0, 0, 1]), n_boot=50, seed=5)
    # The non-finite row is dropped, not imputed.
    assert mixed["n"] == 2
    assert mixed["mean"] == pytest.approx(1.0)


def test_paired_bootstrap_is_reproducible_for_a_fixed_seed() -> None:
    rng = np.random.default_rng(6)
    difference = rng.normal(-0.2, 1.0, 300)
    clusters = np.repeat(np.arange(60), 5)
    first = paired_cluster_bootstrap(difference, clusters, n_boot=400, seed=7)
    second = paired_cluster_bootstrap(difference, clusters, n_boot=400, seed=7)
    assert first == second


# ------------------------------------------------------------------- pinball loss
def test_pinball_per_object_matches_the_study_definition() -> None:
    """Hand-computed pinball loss for a single object against the study's quantile levels."""
    from cosmos.ai.lifetime import models as MO

    taus = np.asarray(MO.QUANTILES)
    z = np.array([2.0])
    quantiles = np.full((1, len(taus)), 1.0)      # every prediction one decade too low
    difference = 1.0                              # z - q
    expected = float(np.mean(np.maximum(taus * difference, (taus - 1) * difference)))

    assert _pinball_per_object(z, quantiles)[0] == pytest.approx(expected)


def test_pinball_is_zero_for_a_perfect_point_prediction() -> None:
    from cosmos.ai.lifetime import models as MO

    z = np.array([1.5])
    quantiles = np.full((1, len(MO.QUANTILES)), 1.5)
    assert _pinball_per_object(z, quantiles)[0] == pytest.approx(0.0)


def test_pinball_penalises_both_directions() -> None:
    from cosmos.ai.lifetime import models as MO

    n = len(MO.QUANTILES)
    z = np.array([1.0, 1.0])
    quantiles = np.array([np.full(n, 0.0), np.full(n, 2.0)])
    losses = _pinball_per_object(z, quantiles)
    assert (losses > 0).all()


# ----------------------------------------------------------------------- C4
def test_c4_is_not_evaluable_and_says_why() -> None:
    """C4 must report an unavailable join, never a manufactured result."""
    result = analyse_c4(ROOT)

    assert result["verdict"] == "NOT EVALUABLE"
    assert result["joinable_pairs"] == 0
    assert "anonymised" in result["reason"]
    assert result["what_would_be_needed"]
    # No effect, interval or p-value may be reported for an unevaluable coupling.
    for key in ("mean", "ci95_lo", "ci95_hi", "p_value", "effect"):
        assert key not in result

    identifiable = [s for s in result["sources_examined"] if s["spacecraft_identifiable"]]
    for source in identifiable:
        # The only identifiable source must be the one with neither telemetry nor CDMs.
        assert "no telemetry" in source["detail"] or "neither" in source["detail"]


# --------------------------------------------------------------- integration verdict
def test_integration_verdict_is_not_demonstrated_without_reproducible_support() -> None:
    partial = {"verdict": "PARTIALLY SUPPORTED"}
    inconclusive = {"verdict": "INCONCLUSIVE"}
    unevaluable = {"verdict": "NOT EVALUABLE"}

    result = integration_value(partial, partial, inconclusive, unevaluable)
    assert result["answer"].startswith("NOT DEMONSTRATED")
    assert result["combined_chain_evaluated"] is False
    assert "NOT supported" in result["honest_summary"]
    # A single aggregate score must not be invented to declare success.
    assert "aggregation" in result["why_no_combined_chain"]


def test_integration_verdict_reports_partial_when_a_coupling_is_supported() -> None:
    supported = {"verdict": "SUPPORTED"}
    inconclusive = {"verdict": "INCONCLUSIVE"}
    result = integration_value(supported, inconclusive, inconclusive,
                               {"verdict": "NOT EVALUABLE"})
    assert result["answer"].startswith("PARTIAL")
    assert result["supported"] == ["C1"]


def test_integration_never_claims_a_validated_end_to_end_chain() -> None:
    result = integration_value({"verdict": "SUPPORTED"}, {"verdict": "SUPPORTED"},
                               {"verdict": "SUPPORTED"}, {"verdict": "SUPPORTED"})
    joined = " ".join(result["what_integration_does_not_provide"])
    assert "no validated end-to-end" in joined
    assert result["combined_chain_evaluated"] is False


# ------------------------------------------------- saved results, if the phase has run
@pytest.mark.skipif(not RESULTS.is_file(), reason=f"missing {RESULTS}")
def test_saved_phase_e_results_are_internally_consistent() -> None:
    record = json.loads(RESULTS.read_text())

    assert record["post_hoc_disclosure"]
    assert "no model was retrained" in record["method_note"]
    assert record["C4"]["verdict"] == "NOT EVALUABLE"

    # Every reported interval must bracket its own point estimate.
    for contrast in record["C2"]["contrasts"]:
        if contrast.get("mean") is None:
            continue
        assert contrast["ci95_lo"] <= contrast["mean"] <= contrast["ci95_hi"], contrast["name"]
        assert 0.0 <= contrast["p_value"] <= 1.0
        assert contrast["p_adjusted_bh"] >= contrast["p_value"] - 1e-12

    for origin, per in record["C1"]["per_origin"].items():
        for ablation in per.get("ablations", []) or []:
            assert ablation["ci95_lo"] <= ablation["effect_pinball_ablation_minus_full"] \
                <= ablation["ci95_hi"], f"{origin}/{ablation['ablation']}"
            assert ablation["p_adjusted_bh"] >= ablation["p_value"] - 1e-12

    # A verdict of SUPPORTED requires a corrected-significant effect in the right direction.
    for coupling in ("C1", "C2"):
        if record[coupling]["verdict"] == "SUPPORTED":
            assert record[coupling].get("origins_supporting") or \
                record[coupling].get("deployed_expert_helps")


@pytest.mark.skipif(not RESULTS.is_file(), reason=f"missing {RESULTS}")
def test_saved_c1_reproduces_the_original_study_interval() -> None:
    """The recomputed effect must match the study's stored ablation interval closely.

    This is a reproducibility check on the re-analysis: if the recomputation disagreed with
    the published interval, the re-analysis would be measuring something else.
    """
    import pandas as pd

    record = json.loads(RESULTS.read_text())
    for origin, per in record["C1"]["per_origin"].items():
        stored_path = (ROOT / "outputs" / "benchmarks" / "reentry_lifetime"
                       / f"origin{origin}_uncontrolled" / "ablation_effects_test.csv")
        if not stored_path.is_file() or not per.get("ablations"):
            continue
        stored = pd.read_csv(stored_path).set_index("ablation")
        for ablation in per["ablations"]:
            name = ablation["ablation"]
            if name not in stored.index:
                continue
            published = float(stored.loc[name, "pinball_ablation_minus_full"])
            assert ablation["effect_pinball_ablation_minus_full"] == pytest.approx(
                published, abs=1e-9), f"{origin}/{name} effect disagrees with the study"


# ================================================================ Phase H coverage
PHASE_H = ROOT / "outputs" / "phase_h" / "phase_h_results.json"


def test_coverage_record_detects_under_and_over_coverage() -> None:
    """Hand-built cases: clear under-coverage, clear over-coverage, and nominal."""
    from scripts.phase_h_uncertainty_audit import coverage_record

    clusters = np.repeat(np.arange(60), 5)
    # 60 % observed against a 90 % nominal level -> under-covers.
    under = np.zeros(300, dtype=bool)
    under[: int(0.60 * 300)] = True
    result = coverage_record(under, clusters, 0.90, n_boot=600)
    assert result["empirical_coverage"] == pytest.approx(0.60)
    assert result["verdict"] == "UNDER-COVERS"
    assert result["deviation_ci95_hi"] < 0

    # 99 % observed against 0.90 -> over-covers.
    over = np.ones(300, dtype=bool)
    over[:3] = False
    assert coverage_record(over, clusters, 0.90, n_boot=600)["verdict"] == "OVER-COVERS"


def test_coverage_record_is_conservative_under_clustering() -> None:
    """A deviation driven by whole-cluster behaviour must not be called significant."""
    from scripts.phase_h_uncertainty_audit import coverage_record

    rng = np.random.default_rng(11)
    # Each cluster is entirely covered or entirely not: strong dependence, mean near 0.85.
    per_cluster = rng.random(40) < 0.85
    indicator = np.repeat(per_cluster, 10)
    clusters = np.repeat(np.arange(40), 10)

    clustered = coverage_record(indicator, clusters, 0.90, n_boot=800)
    as_independent = coverage_record(indicator, np.arange(len(indicator)), 0.90, n_boot=800)

    width_clustered = clustered["deviation_ci95_hi"] - clustered["deviation_ci95_lo"]
    width_independent = (as_independent["deviation_ci95_hi"]
                         - as_independent["deviation_ci95_lo"])
    assert width_clustered > 2 * width_independent


@pytest.mark.skipif(not PHASE_H.is_file(), reason=f"missing {PHASE_H}")
def test_phase_h_results_are_internally_consistent() -> None:
    record = json.loads(PHASE_H.read_text())
    assert record["post_hoc"] is True

    checked = 0
    for origin, block in record["interval_coverage"].items():
        if block.get("status") != "evaluated":
            continue
        for model, entry in block["models"].items():
            for label, value in entry.items():
                if value.get("status") != "evaluated":
                    continue
                # Every interval must bracket its own deviation, and coverage is a proportion.
                assert value["deviation_ci95_lo"] <= value["deviation"] <= value["deviation_ci95_hi"]
                assert 0.0 <= value["empirical_coverage"] <= 1.0
                assert value["deviation"] == pytest.approx(
                    value["empirical_coverage"] - value["nominal"], abs=1e-9)
                # The verdict must follow from the interval, not be asserted independently.
                if value["deviation_ci95_hi"] < 0:
                    assert value["verdict"] == "UNDER-COVERS"
                elif value["deviation_ci95_lo"] > 0:
                    assert value["verdict"] == "OVER-COVERS"
                else:
                    assert value["verdict"] == "CONSISTENT WITH NOMINAL"
                checked += 1
    assert checked > 0


@pytest.mark.skipif(not PHASE_H.is_file(), reason=f"missing {PHASE_H}")
def test_phase_h_does_not_claim_validated_conformal_coverage() -> None:
    """The audit must not describe nominal coverage as an observed guarantee."""
    record = json.loads(PHASE_H.read_text())
    joined = " ".join(record["not_established"]).lower()
    assert "nominal" in joined and "not the same quantity" in joined

    for mechanism in record["mechanism_inventory"]:
        if mechanism["mechanism"].startswith("Mondrian"):
            # Must point at the measurement rather than assert a blanket verdict.
            assert "interval_coverage" in mechanism["status"]
            assert "measured_deployed_expert" in mechanism
