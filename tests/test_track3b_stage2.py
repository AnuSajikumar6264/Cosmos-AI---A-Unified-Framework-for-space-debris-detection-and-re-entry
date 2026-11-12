"""Pins X4 — the exactly specified cells of 3b Stage 2 (2026-11-08; EXPLORATORY).

Pinned: the regenerated AR(8) OOF scores reproduce the archived sample hash; the validity gate (c0 = A0,
c5 = A1 and every re-run P1 cell identical to the archive) passed; the frozen files were unchanged by the
run; the two protocol gaps are recorded as blockers; and the structure of the contrasts — residual scale
immaterial at every level, calibration pool positive but below the +0.05 threshold, selection data
carrying about +0.30 of the +0.353 gain at both score levels, no sigma x pool interaction.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/benchmarks/telemetry_esa_adb/track3b_stage2/m1_target_conformal_bh.json"
pytestmark = pytest.mark.skipif(not OUT.is_file(), reason="X4 cells not generated")


@pytest.fixture(scope="module")
def res() -> dict:
    return json.loads(OUT.read_text())


def test_regeneration_and_validity_gate(res):
    assert res["oof_regeneration"]["reproduces_archived_sample"] is True
    r = res["reproduction"]
    assert r["passed"] is True and r["c0"] == r["A0_official"] and r["c5"] == r["A1_official"]
    assert all(r["p1_cells_reproduced"].values())
    assert res["freeze_unchanged"] is True
    assert len(res["blockers"]) >= 2 and any("P_cal, D_half" in b for b in res["blockers"])


def _c(res, label):
    return next(s for s in res["contrasts"] if s["contrast"].startswith(label))


def test_residual_scale_is_immaterial_at_every_level(res):
    for label in ("F2 sigma at P_half, D_cal", "F2 sigma at P_half, D_half", "F2 sigma at P_cal, D_cal"):
        s = _c(res, label)
        assert abs(s["delta_official"]) < 0.01 and s["ci95_high"] <= 1e-9, s
    assert abs(res["interaction_F2xF3_at_Dcal_point"]) < 0.01
    # the A1 configuration with A0's sigma selects the same operating point and scores identically
    assert res["cells"]["n_sh_half_half"]["official_EW_F0.5"] == res["cells"]["c5"]["official_EW_F0.5"]
    assert (res["cells"]["n_sh_half_half"]["chosen_level"], res["cells"]["n_sh_half_half"]["chosen_k"]) == (res["cells"]["c5"]["chosen_level"], res["cells"]["c5"]["chosen_k"])


def test_pool_is_positive_but_below_threshold_and_selection_data_carries_the_gain(res):
    for label in ("F3 pool at Sh, D_cal", "F3 pool at S1, D_cal"):
        s = _c(res, label)
        assert 0 < s["delta_official"] < 0.05 and s["ci95_low"] > 0, s
        assert s["material_at_0.05"] is False
    for label in ("F4 selection data at Sh, P_half", "F4 selection data at S1, P_half"):
        s = _c(res, label)
        assert s["delta_official"] > 0.25 and s["ci95_low"] > 0.1 and s["material_at_0.05"], s
    a0, a1 = res["reproduction"]["A0_official"], res["reproduction"]["A1_official"]
    share = _c(res, "F4 selection data at S1, P_half")["delta_official"] / (a1 - a0)
    assert 0.8 < share < 0.9
