"""Pins the re-derived trivial reference predictors (Phase 2.3 / X5, 2026-11-06).

The Secondary-A analysis stated these numbers in prose with no artifact behind them. They are now
produced by `scripts/lifetime_reference_predictors.py` from hashed inputs; this test keeps the
conclusion and the values from drifting silently, and records the one small discrepancy found.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/lifetime_reference_predictors"

pytestmark = pytest.mark.skipif(not (OUT / "reference_predictor_results.json").is_file(),
                                reason="reference predictors not re-derived")


def test_every_published_arm_beats_the_feature_free_oracle_at_every_origin():
    r = json.loads((OUT / "reference_predictor_results.json").read_text())
    assert r["refitting_performed"] is False and r["frozen_artifacts_modified"] is False
    for origin in ("2011", "2016", "2006"):
        c = r["origins"][origin]
        assert c["every_published_arm_beats_oracle"] is True, origin
        assert c["worst_margin_over_oracle_pct"] > 5.0, (origin, c["worst_margin_over_oracle_pct"])


def test_values_match_the_documented_claim_where_it_was_exact():
    r = json.loads((OUT / "reference_predictor_results.json").read_text())
    expect = {"2011": (0.172892, 0.133180, "physics_only", 0.052676, "mlp", 0.114661),
              "2016": (0.232879, 0.146946, "tabicl", 0.049944, "physics_only", 0.089249)}
    for origin, (cap, oracle, best, best_v, worst, worst_v) in expect.items():
        d = r["origins"][origin]["documented_vs_rederived"]
        assert d["constant_at_cap"]["rederived"] == pytest.approx(cap, abs=1e-6)
        assert d["test_marginal_quantiles"]["rederived"] == pytest.approx(oracle, abs=1e-6)
        assert d["best"]["rederived"][0] == best and d["best"]["rederived"][1] == pytest.approx(best_v, abs=1e-6)
        assert d["worst"]["rederived"][0] == worst and d["worst"]["rederived"][1] == pytest.approx(worst_v, abs=1e-6)
        # the honest, feature-free predictor: re-derived within 3e-4 of the prose value; the prose
        # did not record its exact training population, so exactness cannot be demanded here
        assert d["train_marginal_quantiles"]["abs_diff"] < 3e-4, origin


def test_leaderboard_table_is_complete_and_intervals_bracket_means():
    t = pd.read_csv(OUT / "leaderboard_with_intervals.csv")
    assert set(t.origin.astype(str)) == {"2011", "2016", "2006"}
    assert ((t.ci95_lo <= t.mean_pinball) & (t.mean_pinball <= t.ci95_hi)).all()
    for origin, g in t.groupby("origin"):
        assert set(g[g.kind == "trivial_reference"].arm) == {
            "constant_at_cap", "train_marginal_quantiles", "test_marginal_quantiles"}
        oracle = float(g.loc[g.arm == "test_marginal_quantiles", "mean_pinball"].iloc[0])
        assert (g.loc[g.kind == "published_arm", "mean_pinball"] < oracle).all(), origin
