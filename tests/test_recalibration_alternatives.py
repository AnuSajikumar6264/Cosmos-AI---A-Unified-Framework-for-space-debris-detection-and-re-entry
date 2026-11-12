"""Pins the G3′ recalibration study (Phase 3, 2026-11-06; protocol PHASE3_RECALIBRATION_PROTOCOL.md).

Pinned: the reproduction gate (the deployed Mondrian CQR refit on tune-B equals the archived
intervals exactly), and the direction of the pre-declared primary result — no alternative is
established as closer to nominal than the deployed construction; the recency-based ones are
farther from it. If a later change makes an alternative "win", this should fail and be examined.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/phase3_uncertainty/recalibration_alternatives"
pytestmark = pytest.mark.skipif(not (OUT / "results.json").is_file(), reason="G3' not generated")


@pytest.fixture(scope="module")
def results() -> dict:
    return json.loads((OUT / "results.json").read_text())


def test_protocol_was_declared_and_reproduction_gate_passed(results):
    assert (ROOT / results["protocol"]).is_file()
    gate = results["reproduction_gate_R0_max_abs_delta"]
    assert len(gate) == 18 and max(gate.values()) == 0.0        # 3 origins x 3 arms x 2 levels


def test_no_alternative_is_established_closer_to_nominal(results):
    p = results["primary_criterion_cosmos_gated"]
    assert set(p) == {"R0_deployed_mondrian", "R1_marginal", "R2_class_only", "R3_asymmetric",
                      "R4_recent_half_window", "R5_recency_weighted"}
    assert not any(v["closer_to_nominal_than_R0"] for v in p.values())
    r0 = p["R0_deployed_mondrian"]["mean_abs_deviation"]
    # the asymmetric construction has the lower point estimate but its interval includes zero
    assert p["R3_asymmetric"]["mean_abs_deviation"] < r0 and p["R3_asymmetric"]["paired_ci95"][1] > 0
    # recency windowing / weighting do not help: farther from nominal and wider
    for k in ("R4_recent_half_window", "R5_recency_weighted"):
        assert p[k]["mean_abs_deviation"] > r0 and p[k]["mean_width_ratio_vs_R0"] > 1.05, k


def test_table_is_complete_and_coverage_values_match_phase_h_for_the_deployed_construction():
    t = pd.read_csv(OUT / "coverage_by_construction.csv")
    assert set(t.origin.astype(str)) == {"2011", "2016", "2006"} and t.construction.nunique() == 6
    assert ((t.dev_ci95_lo <= t.deviation + 1e-12) & (t.deviation <= t.dev_ci95_hi + 1e-12)).all()
    ph = pd.read_csv(ROOT / "outputs/phase_h/coverage_table.csv")
    d = t[(t.construction == "R0_deployed_mondrian") & (t.arm == "cosmos_gated") & (t.origin.astype(str) != "2006")]
    m = d.merge(ph[ph.model == "cosmos_gated"], left_on=[d.origin.astype(int), "level"], right_on=["origin", "level"])
    assert len(m) == 4 and (abs(m.coverage - m.empirical_coverage) < 1e-9).all()
