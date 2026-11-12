"""Pins the Phase 3 twin uncertainty audit (2026-11-06).

Structure pinned, not flattering numbers: the reported re-entry probability and the reported time
quantiles describe one distribution (agreement up to Monte-Carlo granularity of 1/32); the isotonic
lifetime probabilities do *not* agree with the lifetime quantiles they travel with (an L17 facet),
while the coherent reading does; the decision ranking uses the point probability and a consequence
multiplier only, and reproduces exactly from those two columns.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/phase3_uncertainty"
RUN = OUT / "pipeline_full"

pytestmark = pytest.mark.skipif(not (OUT / "twin_uncertainty_audit.json").is_file(), reason="audit not generated")


@pytest.fixture(scope="module")
def audit() -> dict:
    return json.loads((OUT / "twin_uncertainty_audit.json").read_text())


def test_reported_probability_and_quantiles_describe_one_distribution(audit):
    c = audit["consistency_p30_vs_time_quantiles"]
    re = c["reentry_reported_p_30d_vs_lo90_median_hi90"]
    assert re["n_checked"] == 15010
    assert re["violations"]["median<30d_but_p<0.5"] == 0 and re["violations"]["median>30d_but_p>0.5"] == 0
    assert re["violations"]["q95<30d_but_p<0.95"] == 0
    assert re["any_violation"] <= 5                       # 1/32 Monte-Carlo granularity at the 5 % tail only
    assert re["max_abs_gap_median_rule"] == 0.0


def test_isotonic_lifetime_probabilities_disagree_with_their_quantiles_but_the_coherent_reading_does_not(audit):
    c = audit["consistency_p30_vs_time_quantiles"]
    iso = c["lifetime_isotonic_p_lifetime_30d_vs_lifetime_quantiles"]
    coh = c["lifetime_coherent_p_lifetime_raw_30d_vs_lifetime_quantiles"]
    assert iso["n_checked"] == coh["n_checked"] == 13238
    assert iso["any_violation"] > 300 and iso["max_abs_gap_median_rule"] > 0.2
    assert coh["any_violation"] == 0


def test_uncertainty_kinds_partition_the_snapshot(audit):
    k = audit["uncertainty_kinds"]
    assert k["reentry"]["with_time_quantiles"] + k["reentry"]["probabilities_only_no_quantiles"] == audit["n_objects"] == 31396
    assert k["reentry"]["by_regime_without_quantiles"] == {"operator_controlled": 16386}
    assert k["lifetime"]["present_but_isotonic_incoherent_abstained_by_adapter"] == 123
    assert k["mass"]["known_share_among_uncontrolled_with_quantiles"] < 0.3   # consequence multiplier reaches < 30 % of ranked objects


@pytest.mark.skipif(not (RUN / "decision_ranking.csv").is_file(), reason="full pipeline run absent")
def test_priority_score_is_exactly_point_probability_times_consequence_multiplier():
    r = pd.read_csv(RUN / "decision_ranking.csv")
    expected = r.p_reentry_30d * np.where(r.high_consequence, 2.0, 1.0)
    assert np.allclose(r.priority_score, expected, atol=1e-12)
    assert (r.priority_score.diff().dropna() <= 1e-12).all()              # sorted descending
    # every snapshot object with a re-entry probability is ranked; none dropped
    assert len(r) == 31396
    # mass-unknown objects can never receive the multiplier
    assert not (r.loc[~r.mass_known, "high_consequence"]).any()


def test_ranking_uses_no_interval_information(audit):
    pr = audit["pipeline_run"]
    assert "reentry_interval_available (flag)" in pr["uncertainty_fields_carried_but_not_used"]
    top = audit["ranking_vs_interval"]["top50"]
    assert top["with_quantiles"] == 50
    # a material share of the top 50 carries a 90 % interval that straddles the 30-day horizon
    assert top["interval_straddles_30d"] >= 15
    assert top["interval_straddles_30d"] + top["interval_entirely_before_30d"] + top["interval_entirely_after_30d"] == 50
