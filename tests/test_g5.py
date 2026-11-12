"""Tests for the G5 rolling-evaluation and censoring-causal analyses.

The promotion rule is the part most likely to be bent, so it is tested hardest: all three
pre-specified criteria must be enforced, and a candidate that degrades coverage must not be
promoted even when its accuracy criterion passes.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from cosmos.ai.provenance import ROOT

ROLLING = ROOT / "outputs" / "g5_rolling" / "g5_rolling_results.json"
CAUSAL = ROOT / "outputs" / "g5_censoring" / "g5_causal_results.json"
FIGURES = ROOT / "outputs" / "g5_figures"


# ------------------------------------------------------------------ promotion rule
@pytest.mark.skipif(not ROLLING.is_file(), reason=f"missing {ROLLING}")
def test_promotion_enforces_all_three_criteria() -> None:
    record = json.loads(ROLLING.read_text())
    for candidate, entry in record["promotion"].items():
        accuracy = entry["accuracy_criterion_met"]
        coverage = entry["coverage_criterion_met"]
        expected = bool(accuracy and coverage) if coverage is not None else bool(accuracy)
        assert entry["promote"] is expected, candidate
        assert entry["verdict"] == ("PROMOTE" if expected else "DO NOT PROMOTE")


@pytest.mark.skipif(not ROLLING.is_file(), reason=f"missing {ROLLING}")
def test_accuracy_criterion_requires_a_majority_and_no_degradation() -> None:
    record = json.loads(ROLLING.read_text())
    for candidate, entry in record["promotion"].items():
        better = len(entry["significantly_better_in"])
        worse = len(entry["significantly_worse_in"])
        expected = bool(better > entry["n_slices"] / 2 and worse == 0)
        assert entry["accuracy_criterion_met"] is expected, candidate


@pytest.mark.skipif(not ROLLING.is_file(), reason=f"missing {ROLLING}")
def test_coverage_criterion_compares_against_the_incumbent() -> None:
    """A candidate reaching nominal in fewer slices than the incumbent must fail."""
    record = json.loads(ROLLING.read_text())
    for candidate, entry in record["promotion"].items():
        comparisons = entry.get("coverage_comparison") or {}
        if not comparisons:
            continue
        expected = all(c["candidate_at_nominal"] >= c["incumbent_at_nominal"]
                       for c in comparisons.values())
        assert entry["coverage_criterion_met"] is expected, candidate
        for level, comparison in comparisons.items():
            assert comparison["not_degraded"] is (
                comparison["candidate_at_nominal"] >= comparison["incumbent_at_nominal"])


@pytest.mark.skipif(not ROLLING.is_file(), reason=f"missing {ROLLING}")
def test_no_candidate_was_promoted_in_g5() -> None:
    """G5 promoted nothing; a change here must be a deliberate, reviewed decision."""
    record = json.loads(ROLLING.read_text())
    assert not any(entry["promote"] for entry in record["promotion"].values())


@pytest.mark.skipif(not ROLLING.is_file(), reason=f"missing {ROLLING}")
def test_rolling_results_are_internally_consistent() -> None:
    record = json.loads(ROLLING.read_text())
    assert record["exploratory"] is True
    assert "not independent confirmation" in record["exploratory_note"]
    # The design must not be described as rolling-origin retraining.
    assert "NOT rolling-origin" in record["design"]

    usable = [s for s in record["slices"] if s["status"] == "evaluated"]
    assert usable
    for s in usable:
        assert s["n"] >= record["min_objects"]
        assert s["n_families"] >= record["min_families"]
        assert 0.0 <= s["at_cap_fraction"] <= 1.0
        # Ranks must be a permutation of 1..n over the scored models.
        ranks = sorted(s["ranks"].values())
        assert ranks == list(range(1, len(ranks) + 1)), s["launch_year"]
        # The best model must be the one ranked 1.
        assert s["ranks"][s["best_model"]] == 1

    for candidate, entry in record["promotion"].items():
        for slice_entry in entry["per_slice"]:
            assert slice_entry["ci95_lo"] <= slice_entry["delta"] <= slice_entry["ci95_hi"]
            assert slice_entry["p_adjusted_bh"] >= slice_entry["p_value"] - 1e-12


@pytest.mark.skipif(not ROLLING.is_file(), reason=f"missing {ROLLING}")
def test_rank_agreement_is_reported_and_bounded() -> None:
    record = json.loads(ROLLING.read_text())
    agreement = record["rank_agreement_between_slices"]
    assert agreement["n_pairs"] > 0
    for key in ("mean_spearman", "median_spearman", "min_spearman"):
        assert -1.0 <= agreement[key] <= 1.0
    assert 0.0 <= agreement["fraction_negative"] <= 1.0


# ------------------------------------------------------- censoring causal analysis
@pytest.mark.skipif(not CAUSAL.is_file(), reason=f"missing {CAUSAL}")
def test_causal_analysis_records_the_correction_to_phase_g_plus() -> None:
    """The corrected attribution must be preserved, not quietly dropped."""
    record = json.loads(CAUSAL.read_text())
    corrected = record["corrects_previous_finding"]
    assert "CORRECTED" in corrected
    assert "censoring relative to the cap is not the differentiator" in corrected
    assert "POINT MASS" in corrected


@pytest.mark.skipif(not CAUSAL.is_file(), reason=f"missing {CAUSAL}")
def test_known5_is_near_one_in_every_split() -> None:
    """The evidence that refutes the censoring explanation."""
    record = json.loads(CAUSAL.read_text())
    for origin, entry in record["results"].items():
        if entry.get("status") != "evaluated":
            continue
        for name, census in entry["census"].items():
            assert census["known5_fraction"] > 0.99, f"{origin}/{name}"


@pytest.mark.skipif(not CAUSAL.is_file(), reason=f"missing {CAUSAL}")
def test_cap_mass_shift_reverses_across_origins() -> None:
    record = json.loads(CAUSAL.read_text())
    shifts = record["cap_mass_shift_by_origin"]
    if len(shifts) < 2:
        pytest.skip("fewer than two origins evaluated")
    signs = {np.sign(value) for value in shifts.values()}
    assert len(signs) == 2, shifts
    assert record["shift_reverses_across_origins"] is True


@pytest.mark.skipif(not CAUSAL.is_file(), reason=f"missing {CAUSAL}")
def test_loss_concentrates_below_the_cap() -> None:
    """The robust structural finding: at-cap objects contribute little loss."""
    record = json.loads(CAUSAL.read_text())
    for origin, entry in record["results"].items():
        if entry.get("status") != "evaluated":
            continue
        deployed = entry.get("deployed_expert_decomposition") or {}
        if "at_cap_mean" not in deployed:
            continue
        assert deployed["below_cap_mean"] > 2 * deployed["at_cap_mean"], origin


@pytest.mark.skipif(not CAUSAL.is_file(), reason=f"missing {CAUSAL}")
def test_causal_analysis_does_not_claim_a_confirmed_mechanism() -> None:
    """The hypothesis was not confirmed; the artifact must say so."""
    record = json.loads(CAUSAL.read_text())
    joined = " ".join(record["not_established"]).lower()
    assert "observational" in joined
    assert record["exploratory"] is True

    # The cap-mass/loss correlation must disagree in sign across origins, which is why the
    # mechanism is not established. If a future run makes it consistent, this test should fail
    # so the conclusion is revisited deliberately.
    correlations = []
    for entry in record["results"].values():
        if entry.get("status") != "evaluated":
            continue
        value = entry["rank_correlations"].get(
            "spearman_abs_cap_mass_error_vs_test_pinball")
        if value is not None:
            correlations.append(value)
    if len(correlations) == 2:
        assert np.sign(correlations[0]) != np.sign(correlations[1]), correlations


# --------------------------------------------------------------------- figures
@pytest.mark.skipif(not FIGURES.is_dir(), reason=f"missing {FIGURES}")
def test_figures_were_generated_and_are_nonempty() -> None:
    expected = {
        "fig_g5_rank_by_slice.png", "fig_g5_coverage_by_slice.png",
        "fig_g5_promotion.png", "fig_g5_cap_mass.png",
        "fig_g5_selection_transfer.png",
    }
    present = {p.name for p in FIGURES.glob("*.png")}
    assert expected <= present, expected - present
    for name in expected:
        assert (FIGURES / name).stat().st_size > 10_000, name
