"""Pins the re-entry variant decomposition (Phase 2.4 / X7, 2026-11-06).

What is pinned is the *structure* of the finding — the ordering of the variants, the sizes of the
disagreement, which objects carry it, and that every variant over-predicts the observed T1 events —
not a flattering number. If a later change makes the lifetime variant agree with observation, these
tests should fail so the change is noticed and re-examined, not silently absorbed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/reentry_variant_decomposition"

pytestmark = pytest.mark.skipif(not (OUT / "results.json").is_file(),
                                reason="variant decomposition not generated")


def _results() -> dict:
    return json.loads((OUT / "results.json").read_text())


def test_snapshot_expected_counts_and_ordering():
    a = _results()["A_snapshot_2026-10-27"]
    e = a["expected_counts"]["30d"]
    assert a["n_uncontrolled_with_lifetime_reading"] == 13238
    assert e["physics_history"] == pytest.approx(21.59, abs=0.05)
    assert e["lifetime_isotonic"] == pytest.approx(229.1, abs=0.1)   # the summary.json figure
    assert e["physics_history"] < e["physics_prior"] < e["lifetime_isotonic"] < e["lifetime_coherent_raw"]
    assert a["ratio_isotonic_to_history_30d"] == pytest.approx(10.6, abs=0.1)
    # the isotonic step moved the lifetime reading TOWARD physics_history, not away from it
    assert a["isotonic_step_share_of_gap_30d"] < 0


def test_excess_is_carried_by_class_prior_objects_that_already_survived():
    dec = pd.read_csv(OUT / "snapshot_2026-10-27_decomposition.csv")
    d30 = dec[dec.horizon == "30d"]
    am = d30[(d30.stratum == "am_source") & (d30.level == "class_prior_sbm")].iloc[0]
    assert am.share_of_excess > 0.8
    hist = d30[d30.stratum == "history_kind"].set_index("level")
    assert hist.loc["history", "share_of_excess"] > 0.6
    bins = d30[d30.stratum == "history_days_bin"].set_index("level")
    assert bins.loc["1-5 yr", "share_of_excess"] > 0.25 and bins.loc[">20 yr", "share_of_excess"] > 0.15


def test_every_variant_over_predicts_observed_t1_events_history_least():
    b = _results()["B_t1_observed_vs_expected"]
    assert b["exploratory"] is True
    for h, obs in (("30d", 29), ("72d", 64)):
        per = b["by_horizon"][h]
        assert all(v["observed"] == obs for v in per.values())
        ratios = {k: v["ratio_expected_over_observed"] for k, v in per.items()}
        assert all(r > 1.0 for r in ratios.values()), ratios
        assert min(ratios, key=ratios.get) == "physics_history"
        lo, hi = per["physics_history"]["ratio_ci95"]
        assert lo > 1.0, "physics_history's over-prediction interval must exclude 1 at this horizon"
        assert per["lifetime_isotonic"]["ratio_expected_over_observed"] > 9.0
        # Brier ranks differently from count calibration: the coherent reading beats isotonic on
        # Brier while over-predicting the 30-day count more. Both facts must stay visible.
        assert per["physics_history"]["brier"] < per["lifetime_coherent_raw"]["brier"] < per["lifetime_isotonic"]["brier"]
    assert b["by_horizon"]["30d"]["lifetime_coherent_raw"]["ratio_expected_over_observed"] > \
        b["by_horizon"]["30d"]["lifetime_isotonic"]["ratio_expected_over_observed"]


def test_assumptions_are_recorded_per_variant():
    c = _results()["C_assumptions"]
    assert set(c) == {"physics_history", "physics_prior", "lifetime_isotonic", "lifetime_coherent_raw"}
    assert "canonical-orbit" in c["lifetime_isotonic"] and "does not condition on survival" in c["lifetime_isotonic"]
    assert "posterior" in c["physics_history"]
