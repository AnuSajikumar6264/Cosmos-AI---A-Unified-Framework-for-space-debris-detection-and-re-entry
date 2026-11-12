"""Regression tests for the JINT manuscript's load-bearing numbers.

These assert that the figures a reviewer will check still match their source artifacts, and that
the frozen record, the L17 record and the ranking column are unchanged. They are written to fail
if an artifact drifts, not to be adjusted until they pass.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol"
TEST = PROTO / "test"
RESULTS = ROOT / "outputs/benchmarks/telemetry_esa_adb/results.csv"
FORECAST = ROOT / "outputs/twin/as_of_2026-10-27"
MANUSCRIPT = ROOT / "paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md"
CAL = "conformal_bh"

pytestmark = pytest.mark.skipif(not PROTO.is_dir(), reason="ESA-ADB protocol outputs absent")


def _rows(tag: str) -> list[dict]:
    path = TEST / f"{tag}.json"
    return json.loads(path.read_text()) if path.is_file() else []


def _layer(calibrator: str) -> dict:
    return {r["calibrator"]: r for r in _rows("m1_target_ar8")}[calibrator]


def _arm_mean(tags: list[str], field: str) -> float:
    vals = [r[field] for t in tags for r in _rows(t) if r["calibrator"] == CAL]
    assert vals, f"no records for {tags}"
    return float(np.mean(vals))


def _a0(mission: int) -> float:
    frame = pd.read_csv(RESULTS)
    sel = frame[(frame.mission == mission)
                & (frame.tag == f"m{mission}_target_ar8_s0")
                & (frame.calibrator == CAL)]
    assert len(sel) == 1
    return float(sel["anomaly_and_rare/EW_F0.5"].iloc[0])


# ---------------------------------------------------------------- frozen record
def test_esa_adb_freeze_identifier_unchanged():
    record = json.loads((PROTO / "CONFIRMATORY.json").read_text())
    assert record["freeze_id"] == "09a98f5e160e"


def test_six_preregistered_contrasts_reproduce():
    """Every pre-registered contrast must still be re-derivable from the per-arm records."""
    frozen = {(1, "H4"): -0.222, (1, "H5"): -0.338, (1, "H6"): +0.353,
              (2, "H4"): +0.001, (2, "H5"): -0.029, (2, "H6"): -0.089}
    for mission in (1, 2):
        a0 = _a0(mission)
        a1 = _arm_mean([f"m{mission}_target_ar8"], "anomaly_and_rare/EW_F0.5")
        a2 = _arm_mean([f"m{mission}_target_gbt_ar8_s{s}_event" for s in range(5)],
                       "anomaly_and_rare/EW_F0.5")
        a3 = _arm_mean([f"m{mission}_target_event_ar8_all_c3_s{s}_event" for s in range(5)],
                       "anomaly_and_rare/EW_F0.5")
        for label, value in (("H4", a3 - a1), ("H5", a3 - a2), ("H6", a1 - a0)):
            expected = frozen[(mission, label)]
            assert abs(value - expected) < 6e-4, (
                f"M{mission} {label}: re-derived {value:+.5f} vs frozen {expected:+.3f}")


# -------------------------------------------------- headline operator-burden result
def test_burden_recall_tradeoff_values():
    aci, bh = _layer("aci"), _layer(CAL)
    assert aci["anomaly/EW_recall"] == pytest.approx(0.9272727, abs=1e-6)
    assert bh["anomaly/EW_recall"] == pytest.approx(0.1454545, abs=1e-6)
    assert aci["false_alarms_per_year"] == pytest.approx(176336.9006, rel=1e-6)
    assert bh["false_alarms_per_year"] == pytest.approx(1.1427454, rel=1e-6)
    assert aci["false_alarm_runs"] == 1234479
    assert bh["false_alarm_runs"] == 8


def test_false_alarm_ratio_is_154310_not_160000():
    """The manuscript previously overstated this ratio; pin the true value."""
    aci, bh = _layer("aci"), _layer(CAL)
    ratio = aci["false_alarms_per_year"] / bh["false_alarms_per_year"]
    assert 154_000 < ratio < 154_600, ratio
    assert aci["false_alarm_runs"] / bh["false_alarm_runs"] == pytest.approx(ratio, rel=1e-3)


def test_evaluation_period_identical_across_layers():
    """The burden comparison is only meaningful if the annualisation matches."""
    periods = []
    for name in ("threshold", CAL, "aci", "aci_event"):
        rec = _layer(name)
        periods.append(rec["false_alarm_runs"] / rec["false_alarms_per_year"])
    assert max(periods) - min(periods) < 1e-3, periods
    assert periods[0] == pytest.approx(7.0007, abs=1e-3)


def test_event_layer_suppresses_detections_and_manuscript_says_so():
    aci, bh = _layer("aci"), _layer(CAL)
    assert aci["anomaly/EW_recall"] / bh["anomaly/EW_recall"] == pytest.approx(6.375, abs=0.05)
    text = MANUSCRIPT.read_text()
    assert "6.4" in text and "less recall" in text or "fewer anomalies" in text
    assert "154,310" in text
    assert "160,000" not in text, "the overstated ratio must not reappear"


def test_threshold_and_bh_are_coincident():
    """They select the same operating point; the manuscript states this."""
    a, b = _layer("threshold"), _layer(CAL)
    for field in ("anomaly/EW_precision", "anomaly/EW_recall", "anomaly/EW_F0.5"):
        assert a[field] == b[field]


# -------------------------------------------------------------- L17 / ranking
def test_l17_record_is_exactly_123_and_unchanged():
    frame = pd.read_csv(FORECAST / "forecast_table.csv.gz", low_memory=False)
    cols = ["p_lifetime_30d", "p_lifetime_90d", "p_lifetime_1yr"]
    sub = frame[cols].dropna()
    bad = ((sub[cols[0]] > sub[cols[1]] + 1e-12) | (sub[cols[1]] > sub[cols[2]] + 1e-12))
    assert int(bad.sum()) == 123, "the historical L17 record must be preserved, not fixed in place"
    assert len(sub) == 13238


def test_final_probability_columns_are_coherent():
    frame = pd.read_csv(FORECAST / "forecast_table.csv.gz", low_memory=False)
    cols = ["p_30d", "p_90d", "p_1yr"]
    sub = frame[cols].dropna()
    assert len(sub) == 31396
    bad = ((sub[cols[0]] > sub[cols[1]] + 1e-12) | (sub[cols[1]] > sub[cols[2]] + 1e-12))
    assert int(bad.sum()) == 0


def test_top50_ranks_on_the_clean_column_and_is_sorted():
    top = pd.read_csv(FORECAST / "top50_reentry_30d.csv")
    assert "p_30d" in top.columns
    assert not any(c.startswith("p_lifetime") for c in top.columns)
    assert (top.p_30d.diff().dropna() <= 1e-12).all(), "must be sorted descending by p_30d"


def test_affected_objects_in_top50_have_coherent_ranking_values():
    """NORAD 23806 and 41696 carry incoherent p_lifetime_* but coherent p_*."""
    frame = pd.read_csv(FORECAST / "forecast_table.csv.gz", low_memory=False)
    for norad in (23806, 41696):
        row = frame[frame.norad == norad].iloc[0]
        assert row.p_30d <= row.p_90d + 1e-12 <= row.p_1yr + 1e-12
        assert row.p_lifetime_30d > row.p_lifetime_90d + 1e-12


def test_known_issues_file_discloses_the_defect():
    path = FORECAST / "KNOWN_ISSUES.md"
    assert path.is_file()
    text = path.read_text()
    assert "123" in text and "L17" in text
    for norad in ("23806", "41696"):
        assert norad in text


def test_forecast_digest_still_verifies():
    import hashlib
    for line in (FORECAST / "FORECAST_SHA256.txt").read_text().split("\n"):
        parts = line.split()
        if len(parts) != 2:
            continue
        digest, name = parts
        actual = hashlib.sha256((FORECAST / name).read_bytes()).hexdigest()
        assert actual == digest, f"{name} digest changed"


# ------------------------------------------------------------------- figures
def test_three_figures_exist_and_are_nonempty():
    figures = ROOT / "paper/jint/figures"
    for name in ("Figure_1_burden_recall.png", "Figure_2_arm_contrasts.png",
                 "Figure_3_selection_vs_test.png"):
        path = figures / name
        assert path.is_file(), name
        assert path.stat().st_size > 20_000, name


def test_manuscript_forbids_the_claims_it_must_not_make():
    text = MANUSCRIPT.read_text().lower()
    for forbidden in ("state-of-the-art performance", "outperforms all",
                      "distribution-free guarantee", "physics-informed"):
        assert forbidden not in text, forbidden


def test_manuscript_retains_mandatory_disclosures():
    text = MANUSCRIPT.read_text()
    for required in ("five respects", "motivated by a test result", "6 anomalies",
                     "154,310", "ADTQC", "7.0007"):
        assert required in text, required
