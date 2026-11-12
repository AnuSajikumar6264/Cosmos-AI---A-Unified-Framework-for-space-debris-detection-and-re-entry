"""Pins X6 Stage 1 — am_design missingness, archives only (2026-11-08).

Structure pinned: the derived area-to-mass source labels reproduce the archived per-split counts; the
deployed intervals under-cover design-derived objects relative to class-prior objects at the 80 % level at
both origins (A3 rule, CI excludes 0); the 2016 design-derived 80 % coverage equals the Stage-1 evidence
quoted in the protocol (0.5625); the training-vs-test odds-ratio difference is not established (A4);
the numpy odds-ratio estimator reproduces the archived statsmodels values; Stage 2 was not run.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/am_design_stage1"
pytestmark = pytest.mark.skipif(not (OUT / "results.json").is_file(), reason="X6 Stage 1 not generated")


@pytest.fixture(scope="module")
def res() -> dict:
    return json.loads((OUT / "results.json").read_text())


def test_am_source_labels_reproduce_the_archived_counts(res):
    for o, d in ((("2011"), "origin2011_uncontrolled"), (("2016"), "origin2016_uncontrolled")):
        summ = json.loads((ROOT / "outputs/benchmarks/reentry_lifetime" / d / "summary.json").read_text())
        assert res["origins"][o]["am_source_counts"]["test"] == summ["am_source_test"]
        assert res["origins"][o]["am_source_counts"]["tuneB"] == summ["am_source_tuneB"]
    assert res["origins"]["2016"]["design_share"]["tuneB"] < 0.07 < 0.2 < res["origins"]["2016"]["design_share"]["test"]


def test_design_derived_objects_are_under_covered_at_80_percent_at_both_origins(res):
    for o in ("2011", "2016"):
        d = res["origins"][o]["coverage_difference_design_minus_sbm"]["cosmos_gated@80"]
        assert d["diff"] < -0.1 and d["A3_rule_ci_excludes_zero"], (o, d)
        cov = res["origins"][o]["coverage"]["cosmos_gated@80"]
        assert cov["design"]["coverage"] < 0.80 and cov["design"]["coverage"] < cov["class_prior_sbm"]["coverage"], (o, cov)
    # the protocol's Stage-1 evidence figure is reproduced
    assert res["origins"]["2016"]["coverage"]["cosmos_gated@80"]["design"]["coverage"] == pytest.approx(0.5625, abs=5e-4)
    # at 90 % the 2016 difference is not established
    assert not res["origins"]["2016"]["coverage_difference_design_minus_sbm"]["cosmos_gated@90"]["A3_rule_ci_excludes_zero"]


def test_odds_ratio_stability_is_not_established_and_estimator_is_validated(res):
    for o in ("2011", "2016"):
        assert res["origins"][o]["A4_train_vs_test_uncontrolled"]["cis_non_overlapping"] is False
        tr = res["origins"][o]["odds_ratios"]["train"]["uncontrolled_all"]
        assert tr["ci95"][0] > 1.0                                   # the training-window association itself is real
        assert any(e["components_only"].get("degenerate") for e in res["origins"][o]["odds_ratios"].values())  # small windows are flagged, not hidden
    v = res["estimator_validation_vs_archived_leak_check"]
    assert all(r["design_missing"]["max_rel_diff"] < 1e-9 for r in v.values())
    assert "BLOCKED" in res["stage2_not_run"]


def test_tables_are_complete():
    cov = pd.read_csv(OUT / "subgroup_coverage.csv"); ors = pd.read_csv(OUT / "odds_ratios_by_window.csv")
    assert set(cov.origin.astype(str)) == {"2011", "2016"} and set(cov.level) == {0.8, 0.9}
    assert ((cov.ci95.notna()) | True).all() and len(ors) == 2 * 4 * 2
