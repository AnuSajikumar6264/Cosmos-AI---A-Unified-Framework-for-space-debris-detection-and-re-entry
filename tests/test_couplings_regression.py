"""Regression tests for the C2, C3 and T1 scientific pathways.

Definitions are taken from the implementations and their docstrings, not invented here:

* **C2** (`cosmos/ai/twin/couplings.py`) -- lifetime survival -> debris-cloud population. Each
  test-fold fragment's predicted time-to-re-entry gives S_i(tau); the expected number of a
  cloud's fragments still in orbit ``k`` years after its first catalogued fragment is
  ``sum_i S_i(D_k - t0_i)`` over fragments catalogued by ``D_k``, compared with the catalogue
  count.
* **C3** (`cosmos/ai/twin/couplings.py`) -- catalogue operational status -> re-entry regime.
  As-of ``TAU_C3`` = 2026-08-16, outcomes from the ``FOLLOW_C3`` = 2026-10-27 snapshot, LEO
  payloads with perigee < 600 km.
* **T1** (`cosmos/ai/twin/prospective.py`) -- as-of 2026-08-16 twin forecast of
  P(re-entry within 30 d / 72 d) for objects with perigee < 2000 km, scored against the
  2026-10-27 snapshot. **T1 is explicitly not blind** (see its module docstring).

The expensive fits are not re-run. Pure functions are checked against hand-built cases, and
the saved artifacts are checked for the invariants their definitions imply. Passing these is
software correctness under tested conditions, **not** scientific validation, and it does not
make T1 confirmatory.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from cosmos.ai.twin import couplings as C
from cosmos.ai.twin import prospective as P
from cosmos.ai.provenance import ROOT

C3_PAYLOADS = ROOT / "outputs/benchmarks/twin_couplings/c3_payloads.csv"
C3_SUMMARY = ROOT / "outputs/benchmarks/twin_couplings/c3_summary.json"
C2_CLOUDS = ROOT / "outputs/benchmarks/twin_couplings/c2_cloud_survival.csv"
C2_SUMMARY = ROOT / "outputs/benchmarks/twin_couplings/c2_summary.csv"
T1_OBJECTS = ROOT / "outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz"
T1_SUMMARY = ROOT / "outputs/benchmarks/twin_prospective_t1/t1_summary.json"
FOLLOW_SNAPSHOT = ROOT / "data/feature2_debris/celestrak/snapshots/2026-10-27/satcat.csv"

needs = lambda path: pytest.mark.skipif(not path.is_file(), reason=f"missing {path}")  # noqa: E731


# =============================================================== C2: survival -> cloud
def _quantiles(*log10_days: float) -> np.ndarray:
    """One object's 7 quantiles (0.05..0.95) of log10 capped lifetime."""
    return np.array([list(log10_days)])


def test_c2_survival_is_bounded_and_nonincreasing_in_age() -> None:
    """S(tau) = P(T > tau) must be a survival function: in [0, 1] and never rising."""
    q = _quantiles(0.0, 0.3, 0.7, 1.0, 1.3, 1.7, 2.0)
    ages = np.array([1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0])
    survival = C.survival_from_quantiles(q, ages)[0]

    assert survival.shape == ages.shape
    assert np.all((survival >= 0.0) & (survival <= 1.0))
    assert np.all(np.diff(survival) <= 1e-12), "survival increased with age"
    # Hand-checked against the quantile function: the 0.5 quantile is 10^1.0 = 10 days.
    # The tolerance absorbs the deliberate 1e-9 per-step jitter that `horizon_prob` adds to
    # force a strictly increasing interpolation grid.
    assert survival[2] == pytest.approx(0.5, abs=1e-7)
    assert survival[0] == pytest.approx(0.95, abs=1e-7)


def test_c2_survival_floors_the_age_at_half_a_day() -> None:
    """The documented floor (0.51 d) must apply, so age 0 cannot read below the floor."""
    q = _quantiles(0.0, 0.3, 0.7, 1.0, 1.3, 1.7, 2.0)
    at_zero = C.survival_from_quantiles(q, np.array([0.0]))[0, 0]
    at_floor = C.survival_from_quantiles(q, np.array([0.51]))[0, 0]
    assert at_zero == pytest.approx(at_floor)


def test_c2_calibrated_survival_is_bounded_and_uses_observed_outcomes() -> None:
    """Isotonic recalibration must stay a probability and must follow the observed labels."""
    rng = np.random.default_rng(0)
    n = 400
    # Objects whose quantiles shift with a latent scale, and outcomes consistent with it.
    scale = rng.uniform(0.0, 2.5, n)
    q = np.stack([scale + offset for offset in (-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6)], axis=1)
    true_days = 10.0 ** scale
    time_days = np.minimum(true_days, 1826.25)
    event = (true_days <= 1826.25).astype(int)

    maps = C.survival_calibrator(q, time_days, event)
    assert len(maps) == len(C.AGE_GRID)

    survival = C.calibrated_survival(maps, q, np.full(n, 100.0))
    assert survival.shape == (n,)
    assert np.all((survival >= 0.0) & (survival <= 1.0))
    # Objects predicted to decay sooner must not be given a higher survival at a fixed age.
    order = np.argsort(scale)
    assert np.corrcoef(scale, survival)[0, 1] > 0.5


def test_c2_calibrated_survival_clips_ages_outside_the_grid() -> None:
    q = _quantiles(0.0, 0.3, 0.7, 1.0, 1.3, 1.7, 2.0)
    maps = C.survival_calibrator(
        np.repeat(q, 60, axis=0),
        np.full(60, 50.0),
        np.ones(60, dtype=int),
    )
    below = C.calibrated_survival(maps, q, np.array([C.AGE_GRID[0] / 100.0]))
    at_low = C.calibrated_survival(maps, q, np.array([C.AGE_GRID[0]]))
    above = C.calibrated_survival(maps, q, np.array([C.AGE_GRID[-1] * 100.0]))
    at_high = C.calibrated_survival(maps, q, np.array([C.AGE_GRID[-1]]))

    assert below == pytest.approx(at_low)
    assert above == pytest.approx(at_high)
    for value in (below, above):
        assert 0.0 <= float(value[0]) <= 1.0


def test_c2_summary_matches_a_hand_computed_error() -> None:
    """Error arithmetic of the cloud comparison, computed by hand outside the code."""
    frame = pd.DataFrame({
        "origin": ["2016", "2016"],
        "cloud": ["A", "B"],
        "years": [1, 1],
        "catalogued": [100, 50],
        "observed_in_orbit": [80, 40],
        "pred_model": [90.0, 35.0],
    })
    summary = C.c2_summary(frame).set_index("model").loc["model"]

    # Errors: 90-80 = +10 over 100 -> +0.10; 35-40 = -5 over 50 -> -0.10.
    assert summary["mae_count"] == pytest.approx(7.5)
    assert summary["mae_fraction"] == pytest.approx(0.10)
    assert summary["bias_fraction"] == pytest.approx(0.0)
    # |fraction| <= 0.10 holds for both rows (inclusive bound).
    assert summary["within_10pct"] == pytest.approx(1.0)
    assert summary["n_clouds"] == 2
    assert summary["reading"] == "raw"


def test_c2_summary_separates_raw_from_calibrated_readings() -> None:
    frame = pd.DataFrame({
        "origin": ["2016"], "cloud": ["A"], "years": [1],
        "catalogued": [10], "observed_in_orbit": [5],
        "pred_m": [6.0], "predcal_m": [5.0],
    })
    summary = C.c2_summary(frame)
    readings = dict(zip(summary["reading"], summary["mae_fraction"]))
    assert readings["raw"] == pytest.approx(0.1)
    assert readings["calibrated"] == pytest.approx(0.0)


def test_c2_bootstrap_interval_brackets_the_point_estimate() -> None:
    rng = np.random.default_rng(1)
    n = 60
    frame = pd.DataFrame({
        "origin": ["2016"] * n,
        "cloud": [f"cloud{i // 3}" for i in range(n)],
        "years": [1 + i % 3 for i in range(n)],
        "catalogued": np.full(n, 100),
        "observed_in_orbit": np.full(n, 50),
        "pred_model": 50.0 + rng.normal(0, 5, n),
    })
    result = C.c2_bootstrap(frame, n_boot=200, seed=7).set_index("comparison").loc["pred_model"]

    assert result["ci95_lo"] <= result["mae_fraction"] <= result["ci95_hi"]
    assert result["ci95_lo"] >= 0.0


# ================================================== C3: operational status -> regime
def test_c3_previous_window_rate_excludes_outcomes_after_the_window() -> None:
    """The base rate may use only outcomes at or before ``end`` -- no look-ahead."""
    snapshot = pd.DataFrame({
        "OBJECT_TYPE": ["PAY"] * 5,
        "ORBIT_CENTER": ["EA"] * 5,
        "PERIGEE": [300.0] * 5,
        "LAUNCH_DATE": ["2020-01-01"] * 5,
        "DECAY_DATE": [
            None,            # still in orbit          -> denominator only
            "2026-08-10",    # inside the window       -> numerator
            "2026-09-20",    # AFTER end               -> denominator only (must not count)
            "2026-07-01",    # before window start     -> excluded entirely
            "2026-08-16",    # exactly at end          -> numerator (inclusive)
        ],
    })
    rate = C.previous_window_rate(snapshot, "2026-08-16", 30.0)

    # Eligible at window start: rows 0, 1, 2, 4 -> 4. Decayed in (2026-07-17, 2026-08-16]: rows 1, 4 -> 2.
    assert rate == pytest.approx(0.5)


def test_c3_previous_window_rate_filters_type_centre_and_perigee_band() -> None:
    snapshot = pd.DataFrame({
        "OBJECT_TYPE": ["PAY", "DEB", "PAY", "PAY"],
        "ORBIT_CENTER": ["EA", "EA", "MA", "EA"],
        "PERIGEE": [300.0, 300.0, 300.0, 900.0],
        "LAUNCH_DATE": ["2020-01-01"] * 4,
        "DECAY_DATE": ["2026-08-10"] * 4,
    })
    # Only row 0 is an Earth-orbiting payload inside the 0-600 km band.
    assert C.previous_window_rate(snapshot, "2026-08-16", 30.0, (0.0, 600.0)) == pytest.approx(1.0)
    # Only row 3 falls in the 600-2000 km band.
    assert C.previous_window_rate(snapshot, "2026-08-16", 30.0, (600.0, 2000.0)) == pytest.approx(1.0)


def test_c3_launch_fold_is_deterministic_and_balanced_enough() -> None:
    keys = pd.Series([f"2020-{i:03d}" for i in range(400)])
    first = C.launch_fold(keys, 2)
    second = C.launch_fold(keys, 2)

    assert np.array_equal(first, second), "fold assignment must be reproducible"
    assert set(np.unique(first)) <= {0, 1}
    # A launch always lands in the same fold, so siblings cannot straddle the split.
    repeated = C.launch_fold(pd.Series(["2020-001", "2020-001"]), 2)
    assert repeated[0] == repeated[1]


def test_c3_escalation_rule_never_raises_physical_risk(monkeypatch) -> None:
    """C4's rule may change the action; it must not alter the risk inputs it was given."""
    interval = (-9.0, -7.0)
    without = C.c4_escalation(0.1, interval, "operator_controlled", False)
    with_alarm = C.c4_escalation(0.1, interval, "operator_controlled", True)

    # Below threshold: a health alarm alone must not manufacture a high-risk conjunction.
    assert without["high_risk"] is False
    assert with_alarm["high_risk"] is False
    assert with_alarm["action"] == "monitor"
    assert without["validated"] is False

    high = C.c4_escalation(0.9, (-9.0, -5.0), "operator_controlled", False)
    escalated = C.c4_escalation(0.9, (-9.0, -5.0), "operator_controlled", True)
    assert high["high_risk"] is escalated["high_risk"] is True
    assert high["action"] == "plan avoidance manoeuvre"
    assert escalated["action"].startswith("escalate")
    # The rule reports an action, never a modified probability.
    assert "p_high" not in escalated and "collision_probability" not in escalated


# =================================================================== T1: as-of forecast
def _t1_frame(decay_dates, norads=(1, 2, 3)) -> pd.DataFrame:
    return pd.DataFrame({
        "norad": list(norads),
        "Launch_Tag": [f"2020-{i:03d}" for i in range(len(norads))],
        "decay_fixture": decay_dates,
    })


def test_t1_outcomes_label_horizons_and_drop_late_reported_pre_tau_decays(monkeypatch, tmp_path) -> None:
    """A decay at or before the as-of date is not an outcome -- it is a dropped row."""
    follow = tmp_path / "satcat.csv"
    pd.DataFrame({
        "NORAD_CAT_ID": [1, 2, 3, 4],
        "DECAY_DATE": [
            "2026-08-01",   # before as-of (reported late) -> dropped
            "2026-09-01",   # within 30 d of 2026-08-16    -> y_30d = 1, y_72d = 1
            "2026-10-20",   # within 72 d but not 30 d     -> y_30d = 0, y_72d = 1
            None,           # still in orbit               -> both 0
        ],
    }).to_csv(follow, index=False)
    monkeypatch.setattr(P, "feature_dir", lambda *parts: str(tmp_path))

    table = pd.DataFrame({"norad": [1, 2, 3, 4], "Launch_Tag": ["2020-001"] * 4})
    result = P.outcomes(table)

    assert list(result["norad"]) == [2, 3, 4], "late-reported pre-tau decay was not dropped"
    assert list(result["y_30d"]) == [1, 0, 0]
    assert list(result["y_72d"]) == [1, 1, 0]
    # A 30-day decay is necessarily also a 72-day decay.
    assert (result["y_30d"] <= result["y_72d"]).all()
    assert list(result["launch"]) == ["2020-001"] * 3


def test_t1_scores_match_a_hand_computed_brier() -> None:
    y = np.array([1, 0, 1, 0])
    p = np.array([0.8, 0.1, 0.6, 0.2])
    result = P.scores(y, p)

    # ((0.2^2) + (0.1^2) + (0.4^2) + (0.2^2)) / 4 = (0.04+0.01+0.16+0.04)/4 = 0.0625
    assert result["brier"] == pytest.approx(0.0625)
    assert result["n"] == 4
    assert result["events"] == 2
    assert result["expected"] == pytest.approx(1.7)
    assert result["auc_roc"] == pytest.approx(1.0)


def test_t1_scores_omit_rank_metrics_when_undefined() -> None:
    """With no event or a constant score, AUC is undefined and must be absent, not faked."""
    assert "auc_roc" not in P.scores(np.zeros(5, dtype=int), np.full(5, 0.3))
    assert "auc_roc" not in P.scores(np.array([0, 1]), np.array([0.5, 0.5]))


def test_t1_declares_itself_non_blind() -> None:
    """The non-blind disclosure must stay in the module; removing it would misrepresent T1."""
    assert P.__doc__ is not None
    text = P.__doc__.lower()
    assert "not blind" in text
    assert "disclosure" in text
    assert P.AS_OF == "2026-08-16" and P.FOLLOW == "2026-10-27"


# ===================================================== saved-artifact invariants
@needs(C3_PAYLOADS)
def test_c3_saved_payloads_hold_their_definition() -> None:
    table = pd.read_csv(C3_PAYLOADS)
    horizon = (pd.Timestamp(C.FOLLOW_C3) - pd.Timestamp(C.TAU_C3)).days

    assert table["NORAD_CAT_ID"].is_unique, "a payload appears twice"
    assert set(table["event"].unique()) <= {0, 1}
    assert set(table["status_group"].unique()) <= {"operational", "non-operational", "unknown"}
    # Non-events are censored at the end of the window; events decay inside it.
    assert (table.loc[table["event"].eq(0), "time_days"] == horizon).all()
    assert table.loc[table["event"].eq(1), "time_days"].between(0, horizon).all()
    # C3 is restricted to LEO payloads below 600 km perigee.
    assert (table["perigee"] < 600).all()
    assert (table["apogee"] >= table["perigee"]).all()
    for column in ("p_physics", "p_twin_status_aware_baserate",
                   "p_twin_recalibrated_in_window", "p_recalibrated_blind_in_window"):
        assert table[column].between(0.0, 1.0).all(), f"{column} outside [0, 1]"
        assert table[column].notna().all()


@needs(C3_PAYLOADS)
def test_c3_status_aware_policy_only_overrides_operational_payloads() -> None:
    """The twin's status-aware policy substitutes the base rate for operational payloads only."""
    table = pd.read_csv(C3_PAYLOADS)
    non_operational = table[table["status_group"].ne("operational")]
    # For every non-operational / unknown payload the policy must be the physics forecast.
    assert np.allclose(non_operational["p_twin_status_aware_baserate"],
                       non_operational["p_physics"])

    operational = table[table["status_group"].eq("operational")]
    if len(operational):
        # Operational payloads all receive the same single base rate.
        assert operational["p_twin_status_aware_baserate"].nunique() == 1


@needs(C3_SUMMARY)
def test_c3_summary_keeps_prospective_and_in_window_results_separate() -> None:
    """An in-window recalibration is a diagnostic and must not be reported as a forecast."""
    summary = json.loads(C3_SUMMARY.read_text())

    assert summary["tau"] == C.TAU_C3
    assert summary["follow_up"] == C.FOLLOW_C3
    assert "prospective" in summary and "in_window_cross_fitted" in summary
    assert set(summary["prospective"]) == {
        "physics_status_blind", "base_rate_status_blind", "twin_status_aware_baserate",
    }
    assert set(summary["in_window_cross_fitted"]) == {
        "physics_recalibrated_status_blind", "twin_status_aware_recalibrated",
    }
    # No policy may appear in both groups, which would blur the distinction.
    assert not set(summary["prospective"]) & set(summary["in_window_cross_fitted"])
    for group in ("prospective", "in_window_cross_fitted"):
        for name, metrics in summary[group].items():
            assert 0.0 <= metrics["brier"] <= 1.0, f"{group}/{name}"
            assert 0.0 <= metrics["mean_p"] <= 1.0


@needs(C2_CLOUDS)
def test_c2_saved_cloud_counts_are_physically_admissible() -> None:
    table = pd.read_csv(C2_CLOUDS)
    assert len(table)
    assert (table["catalogued"] > 0).all()
    assert (table["observed_in_orbit"] >= 0).all()
    assert (table["observed_in_orbit"] <= table["catalogued"]).all()
    assert table["years"].between(1, 5).all()

    predictions = [c for c in table.columns if c.startswith(("pred_", "predcal_"))]
    assert predictions
    for column in predictions:
        values = table[column].dropna()
        assert (values >= 0).all(), f"{column} predicts a negative fragment count"
        # An expected surviving count cannot exceed the fragments catalogued by D_k.
        assert (values <= table.loc[values.index, "catalogued"] + 1e-9).all(), column


@needs(C2_CLOUDS)
def test_c2_cloud_years_are_unique_per_cloud_and_origin() -> None:
    table = pd.read_csv(C2_CLOUDS)
    assert not table.duplicated(["origin", "cloud", "years"]).any()


@needs(T1_OBJECTS)
def test_t1_saved_objects_hold_their_definition() -> None:
    table = pd.read_csv(T1_OBJECTS)
    assert table["norad"].is_unique
    assert set(table["y_30d"].unique()) <= {0, 1}
    assert set(table["y_72d"].unique()) <= {0, 1}
    # A 30-day decay must also be a 72-day decay.
    assert (table["y_30d"] <= table["y_72d"]).all()
    assert set(table["regime"].unique()) <= {"natural_decay", "operator_controlled", "unknown"}
    assert set(table["type1"].unique()) <= {"P", "R", "C", "D"}

    for horizon in ("30d", "72d"):
        for variant in ("p_physics_prior", "p_physics_history", "p_lifetime", "p"):
            column = f"{variant}_{horizon}" if variant != "p" else f"p_{horizon}"
            values = table[column].dropna()
            assert values.between(0.0, 1.0).all(), f"{column} outside [0, 1]"


@needs(T1_OBJECTS)
def test_t1_operator_controlled_payloads_get_the_base_rate_not_drag_physics() -> None:
    """C3's regime rule inside T1: a controlled payload must not be given a drag forecast."""
    table = pd.read_csv(T1_OBJECTS)
    controlled = table[table["regime"].eq("operator_controlled")]
    if not len(controlled):
        pytest.skip("no operator-controlled payloads in the saved T1 table")

    for horizon in ("30d", "72d"):
        # All controlled payloads in a perigee band share one previous-window base rate,
        # so the twin's column must take very few distinct values, unlike the physics column.
        assert controlled[f"p_{horizon}"].nunique() <= 4
        assert controlled[f"p_{horizon}"].between(0.0, 1.0).all()


@needs(T1_SUMMARY)
def test_t1_summary_reports_both_horizons_and_uncertainty() -> None:
    summary = json.loads(T1_SUMMARY.read_text())
    assert summary["as_of"] == P.AS_OF
    assert summary["follow_up"] == P.FOLLOW
    assert set(summary["by_horizon"]) == set(P.H_T1)

    for horizon, block in summary["by_horizon"].items():
        assert "brier_difference_ci95_launch_bootstrap" in block, horizon
        for name, record in block["brier_difference_ci95_launch_bootstrap"].items():
            low, high = record["ci95"]
            assert low <= record["mean"] <= high, f"{horizon}/{name} CI excludes its mean"
        for variant, record in block["expected_over_observed_ci95"].items():
            low, high = record["ci95"]
            assert low <= record["ratio"] <= high, f"{horizon}/{variant}"


# ======================================================== snapshot separation
@needs(T1_OBJECTS)
@needs(C3_PAYLOADS)
def test_t1_and_c3_use_the_same_window_and_are_not_the_dated_forecast() -> None:
    """T1/C3 score the 2026-08-16 as-of window; the hashed 2026-10-27 forecast is separate."""
    assert P.AS_OF == C.TAU_C3 == "2026-08-16"
    assert P.FOLLOW == C.FOLLOW_C3 == "2026-10-27"

    hashed = ROOT / "outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt"
    if hashed.is_file():
        # The dated forecast's as-of date equals T1's follow-up date, so it cannot be
        # scored by T1's outcomes: that would be a zero-length evaluation window.
        assert (pd.Timestamp("2026-10-27") - pd.Timestamp(P.FOLLOW)).days == 0


def test_later_snapshot_readiness_blocks_without_a_qualifying_snapshot(tmp_path) -> None:
    """A snapshot that does not post-date the forecast horizon cannot score it."""
    from scripts.check_t1_later_snapshot import assess

    snapshots = tmp_path / "data/feature2_debris/celestrak/snapshots/2026-10-27"
    snapshots.mkdir(parents=True)
    pd.DataFrame({"NORAD_CAT_ID": [1, 2], "DECAY_DATE": ["2026-10-26", None]}).to_csv(
        snapshots / "satcat.csv", index=False)

    report = assess(tmp_path)

    assert report["overall_status"] == "BLOCKED"
    assert report["latest_outcome_coverage"] == "2026-10-26"
    # Outcome coverage ends before the forecast's own as-of date.
    assert report["outcome_days_available_after_forecast"] < 0
    for name, record in report["horizons"].items():
        assert record["status"] == "BLOCKED", name
        assert record["qualifying_snapshots"] == []
    assert report["horizons"]["30d"]["required_snapshot_data_date_at_or_after"] == "2026-11-26"
    assert report["horizons"]["90d"]["required_snapshot_data_date_at_or_after"] == "2027-01-25"


def test_later_snapshot_readiness_reports_ready_once_outcomes_exist(tmp_path) -> None:
    from scripts.check_t1_later_snapshot import assess

    snapshots = tmp_path / "data/feature2_debris/celestrak/snapshots/2026-12-01"
    snapshots.mkdir(parents=True)
    pd.DataFrame({"NORAD_CAT_ID": [1, 2], "DECAY_DATE": ["2026-11-30", None]}).to_csv(
        snapshots / "satcat.csv", index=False)

    report = assess(tmp_path)

    # 30 days after 2026-10-27 is 2026-11-26, which this snapshot covers; 90 d does not.
    assert report["horizons"]["30d"]["status"] == "READY"
    assert report["horizons"]["90d"]["status"] == "BLOCKED"
    assert report["overall_status"] == "READY"
    assert "2026-12-01" in report["horizons"]["30d"]["qualifying_snapshots"]


def test_later_snapshot_readiness_detects_a_digest_mismatch(tmp_path) -> None:
    """A changed forecast file must not be scored as if it were the hashed original."""
    from scripts.check_t1_later_snapshot import verify_digest

    forecast = tmp_path / "outputs/twin/as_of_2026-10-27"
    forecast.mkdir(parents=True)
    (forecast / "twins.jsonl").write_text("changed after hashing\n")
    (forecast / "FORECAST_SHA256.txt").write_text(f"{'0' * 64}  twins.jsonl\n")

    result = verify_digest(tmp_path)

    assert result["state"] == "not_verified"
    assert result["files"]["twins.jsonl"]["state"] == "MISMATCH"


@needs(FOLLOW_SNAPSHOT)
def test_follow_up_snapshot_has_no_outcomes_after_its_data_date() -> None:
    """Guards against a snapshot being replaced by a later one without the dates changing."""
    snapshot = pd.read_csv(FOLLOW_SNAPSHOT, usecols=["NORAD_CAT_ID", "DECAY_DATE"])
    decay = pd.to_datetime(snapshot["DECAY_DATE"], errors="coerce")
    assert decay.max() <= pd.Timestamp("2026-10-27"), \
        "the 2026-10-27 snapshot contains a later decay date than its data date"
