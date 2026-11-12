"""Pins the Kelvins collision-avoidance result and its external check (Phase 2.5 / X12, 2026-11-06).

The archived `test_results.csv` is a negative result: a trivial latest-risk rule beats every learned
arm under the organisers' metric. Two things are pinned so neither can drift silently:

1. the external check — the `latest_risk_point` row reproduces the Latest Risk Prediction baseline
   that Uriot et al. (2021, DOI 10.1007/s42064-021-0101-5) report as L = 0.694 on the complete test
   set, which ties the project's metric implementation and test inputs to the organisers';
2. the structure of the negative finding — the verdict under the native decision rule, its
   reversal under a tuned threshold (both must stay visible), and the interval coverage of the
   deployed arm, which is nominal overall but covers fewer than half of the true high-risk events.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs/benchmarks/conjunction_kelvins_cac/test_results.csv"
pytestmark = pytest.mark.skipif(not RESULTS.is_file(), reason="conjunction benchmark not archived")

PUBLISHED_LRP_L = 0.694         # Uriot et al. 2021, Table/Section on baselines, complete test set
PUBLISHED_CRP_L = 2.5           # constant-risk baseline, same source
LEARNED = ("persistence", "xgboost", "lightgbm", "catboost", "mlp", "tabm", "tabicl", "kumo",
           "cosmos_gated", "stack_constant")


@pytest.fixture(scope="module")
def table() -> pd.DataFrame:
    return pd.read_csv(RESULTS).set_index("model")


def test_latest_risk_rule_reproduces_the_published_lrp_baseline(table):
    lrp = table.loc["latest_risk_point"]
    assert lrp.L_clip == pytest.approx(PUBLISHED_LRP_L, abs=5e-4), lrp.L_clip
    assert lrp.F2_clip == pytest.approx(0.7391, abs=1e-3)
    # the baseline *is* the rule; it has no threshold to tune, so the decision columns must be empty
    assert np.isnan(lrp.L_decision_clip) and np.isnan(lrp.decision_threshold)


def test_under_the_native_rule_every_learned_arm_loses_to_the_latest_risk_rule(table):
    assert set(LEARNED) <= set(table.index) and len(table) == 11
    lrp_f2 = table.loc["latest_risk_point", "F2_clip"]
    learned = table.loc[list(LEARNED)]
    assert (learned.F2_clip < lrp_f2 - 0.5).all(), learned.F2_clip.to_dict()
    assert (learned.L_clip > PUBLISHED_LRP_L).all()
    # arms with F2 = 0 have an undefined (infinite) L; that must be recorded as inf, not dropped
    zero = learned[learned.F2_clip == 0]
    assert len(zero) >= 5 and np.isinf(zero.L_clip).all()


def test_tuned_threshold_reverses_the_verdict_for_persistence_only(table):
    lrp_f2 = table.loc["latest_risk_point", "F2_clip"]
    tuned = table.loc[list(LEARNED), "F2_decision_clip"]
    beats = tuned[tuned > lrp_f2].index.tolist()
    assert beats == ["persistence"], beats          # 0.7535 vs 0.7391 — and nothing else
    # the deployed arm does not beat the rule even with its threshold tuned on the test set
    assert table.loc["cosmos_gated", "F2_decision_clip"] < lrp_f2
    # the tuned learned arms land near the paper's constant-risk baseline, not near LRP
    best_tuned_L = table.loc[list(LEARNED), "L_decision_clip"].min()
    assert PUBLISHED_LRP_L < best_tuned_L < 1.2 * PUBLISHED_CRP_L + 0.5, best_tuned_L


def test_deployed_arm_coverage_is_nominal_overall_but_not_on_high_risk_events(table):
    g = table.loc["cosmos_gated"]
    assert g.cov80 >= 0.80 and g.cov90 >= 0.90
    assert g.cov90_high < 0.5, g.cov90_high
    # the gated arm inherits the selected learner's intervals; coverage must agree with it closely
    assert g.cov90_high == pytest.approx(table.loc["kumo", "cov90_high"], abs=1e-9)
    assert abs(g.width90 - table.loc["kumo", "width90"]) < 1e-3
