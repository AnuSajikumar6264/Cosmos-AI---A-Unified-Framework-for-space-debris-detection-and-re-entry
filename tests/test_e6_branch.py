"""Pins the X10 / E6 OPS-SAT branch comparison (2026-11-08), computed from archives only.

Structure pinned: metrics recomputed from the per-seed scores agree exactly with the per-run table; the
fusion's ECE advantage over the CNN branch alone is significant on both protocols, but there is no
significant ECE, Brier or F1 advantage over the feature-MLP branch alone; the claimed 15x seed-stability
gain is not reproduced (the regenerated cnn seed SD of F1 is an order of magnitude below 0.0977).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/e6_opssat_branch"
pytestmark = pytest.mark.skipif(not (OUT / "results.json").is_file(), reason="E6 analysis not generated")


@pytest.fixture(scope="module")
def res() -> dict:
    return json.loads((OUT / "results.json").read_text())


def test_metrics_reconcile_exactly_with_the_regeneration_table(res):
    for tag in ("official", "time_blocked"):
        p = res["protocols"][tag]
        assert p["n_reconciled"] == 15
        assert all(v == 0.0 for v in p["reconciliation_max_abs_diff"].values()), p["reconciliation_max_abs_diff"]


def test_fusion_calibration_gain_is_against_the_cnn_branch_only(res):
    for tag in ("official", "time_blocked"):
        v = res["verdict"][tag]
        assert v["ece_hybrid_minus_cnn"]["diff"] < 0 and v["ece_hybrid_minus_cnn"]["significant_holm_0.05"], tag
        assert not v["ece_hybrid_minus_fcnn"]["significant_holm_0.05"], tag
        assert not v["brier_hybrid_minus_fcnn"]["significant_holm_0.05"], tag
        assert not v["f1_hybrid_minus_cnn"]["significant_holm_0.05"] and not v["f1_hybrid_minus_fcnn"]["significant_holm_0.05"], tag


def test_claimed_seed_stability_gain_is_not_reproduced(res):
    claimed_cnn_f1_sd = res["k8_claims_under_test"]["f1_sd_hybrid_vs_cnn_claimed"][1]     # 0.0977
    for tag in ("official", "time_blocked"):
        sd = res["verdict"][tag]["seed_sd"]
        assert sd["cnn"]["f1"] < claimed_cnn_f1_sd / 4, (tag, sd["cnn"]["f1"])
        ratio = res["verdict"][tag]["sd_ratio_hybrid_over_cnn"]["f1"]
        lo, hi = ratio["resample_ci95_descriptive"]
        assert lo < 1.0 < hi, (tag, ratio)       # five seeds cannot separate the two SDs


def test_tables_are_complete():
    per_seed = pd.read_csv(OUT / "per_seed_metrics.csv"); comps = pd.read_csv(OUT / "paired_comparisons.csv")
    assert per_seed.groupby(["protocol", "model"]).size().eq(5).all() and set(per_seed.model) == {"cnn", "fcnn", "hybrid"}
    assert len(comps) == 2 * 4 * 3 and comps.p_holm_within_metric.between(0, 1).all()
