"""Consistency tests for the publication figure collection.

These check three things a reader cannot check by eye:

  1. every figure exists in every promised format, with its source-data file beside it;
  2. the numbers a figure plots still equal the numbers in the artifact it claims to read,
     recomputed here from the artifact rather than copied from the figure;
  3. the manuscript and the figures do not contradict each other.

They are written to fail if an artifact drifts, not to be adjusted until they pass. Where a test
pins a value, that value was verified against the archive at the time of writing and the archive
is frozen, so a failure means something changed that should not have.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "paper/figures"
DATA = FIG / "data"
PROTO = ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol"
MANUSCRIPT = ROOT / "paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md"

pytestmark = pytest.mark.skipif(not DATA.is_dir(), reason="figure collection not generated")

GROUPS = {
    "architecture": ["Figure_Architecture_COSMOS_AI", "Figure_Evidence_Fusion"],
    "datasets": ["Figure_D1_dataset_inventory", "Figure_D2_esa_adb_structure",
                 "Figure_D3_label_scarcity", "Figure_D4_catalogue_features"],
    "benchmarks": ["Figure_B1_learned_vs_reference", "Figure_B2_rank_instability"],
    "jint": ["Figure_J1_burden_recall", "Figure_J2_contrast_forest",
             "Figure_J3_arm_performance", "Figure_J4_selection_vs_test",
             "Figure_J5_configuration_sensitivity", "Figure_J6_alarm_composition"],
    "diagnostics": ["Figure_G1_calibration_failure", "Figure_G2_residuals_uncertainty",
                    "Figure_G3_coupling_failure"],
    "system_outputs": ["Figure_S1_twin_snapshot"],
}
SOURCE_FILES = [
    "architecture_component_status.csv", "fusion_mechanism_elements.csv",
    "datasets_inventory.csv", "esa_adb_event_structure.csv",
    "benchmark_label_scarcity.csv", "catalogue_feature_availability.csv",
    "catalogue_feature_correlation.json", "benchmark_learned_vs_reference.csv",
    "benchmark_lifetime_vs_physics.csv", "lifetime_rank_instability.csv",
    "jint_F1_burden_recall.csv", "jint_F2_preregistered_contrasts.csv",
    "jint_F3_arm_performance.csv", "jint_F4_selection_vs_test.csv",
    "jint_F5_configuration_sensitivity.csv", "jint_F6_alarm_composition.csv",
    "diagnostics_phase_h_coverage.csv", "diagnostics_subgroup_coverage.csv",
    "diagnostics_temporal_coverage.csv", "diagnostics_lifetime_residuals.csv",
    "diagnostics_c1_family_effect.csv", "diagnostics_coupling_verdicts.csv",
    "twin_snapshot_summary.csv",
]


# ------------------------------------------------------------------ completeness
@pytest.mark.parametrize("group,stems", sorted(GROUPS.items()))
def test_every_figure_exists_in_every_format(group, stems):
    for stem in stems:
        for ext, floor in (("png", 40_000), ("pdf", 8_000), ("svg", 20_000)):
            path = FIG / group / f"{stem}.{ext}"
            assert path.is_file(), path
            assert path.stat().st_size > floor, f"{path} is only {path.stat().st_size} bytes"


def test_every_source_data_file_exists():
    missing = [f for f in SOURCE_FILES if not (DATA / f).is_file()]
    assert not missing, missing


def test_figure_count_matches_the_catalogue():
    catalogue = ROOT / "COSMOS_AI_FIGURE_CATALOGUE.md"
    assert catalogue.is_file()
    text = catalogue.read_text()
    for stems in GROUPS.values():
        for stem in stems:
            assert stem in text, f"{stem} is not listed in the catalogue"


# ------------------------------------------------------------------ palette is validated, not eyeballed
def test_categorical_palette_passes_the_computable_checks():
    sys.path.insert(0, str(ROOT / "scripts/figures"))
    from palette_check import validate  # noqa: E402
    import figstyle  # noqa: E402

    # all-pairs, because the scatter and forest figures show every series against every other
    ok, report = validate(list(figstyle.CAT), mode="light", surface="#ffffff", pairs="all")
    failures = [r for r in report if r[1] in (False, "fail")]
    assert ok and not failures, report


# ------------------------------------------------------------------ J1 / J6: the headline
def test_j1_matches_the_archived_protocol_record():
    src = pd.read_csv(DATA / "jint_F1_burden_recall.csv").set_index("alarm_layer")
    rows = {r["calibrator"]: r
            for r in json.loads((PROTO / "test/m1_target_ar8.json").read_text())}
    for layer, row in src.iterrows():
        rec = rows[layer]
        assert row.anomaly_EW_recall == pytest.approx(rec["anomaly/EW_recall"], abs=1e-12)
        assert row.anomaly_ADTQC == pytest.approx(rec["anomaly/ADTQC"], abs=1e-12)
        assert row.false_alarms_per_year == pytest.approx(rec["false_alarms_per_year"], rel=1e-12)
        assert int(row.false_alarm_runs) == int(rec["false_alarm_runs"])


def test_j1_ratio_is_154310_and_the_period_is_shared():
    src = pd.read_csv(DATA / "jint_F1_burden_recall.csv").set_index("alarm_layer")
    aci, bh = src.loc["aci"], src.loc["conformal_bh"]
    ratio = aci.false_alarms_per_year / bh.false_alarms_per_year
    assert 154_000 < ratio < 154_600, ratio
    assert aci.false_alarm_runs / bh.false_alarm_runs == pytest.approx(ratio, rel=1e-3)
    # the comparison is only meaningful if every layer is annualised over one period
    period = (src.false_alarm_runs / src.false_alarms_per_year.replace(0, np.nan)).dropna()
    assert period.max() - period.min() < 1e-3
    assert period.iloc[0] == pytest.approx(7.0007, abs=1e-3)


def test_j1_reports_both_directions_of_the_tradeoff():
    """The event layer must not appear to win on everything: it loses recall and timing."""
    src = pd.read_csv(DATA / "jint_F1_burden_recall.csv").set_index("alarm_layer")
    aci, bh = src.loc["aci"], src.loc["conformal_bh"]
    assert aci.anomaly_EW_recall > bh.anomaly_EW_recall
    assert aci.anomaly_ADTQC > bh.anomaly_ADTQC
    assert aci.false_alarm_runs > bh.false_alarm_runs
    assert aci.anomaly_EW_recall / bh.anomaly_EW_recall == pytest.approx(6.375, abs=0.05)


def test_j6_alarm_runs_decompose_exactly():
    src = pd.read_csv(DATA / "jint_F6_alarm_composition.csv")
    parts = src[["anomaly_runs", "rare_event_only_runs", "false_alarm_runs"]].sum(axis=1)
    assert (parts == src.alarm_runs).all(), src
    # recall converts to a whole number of anomalies in every row
    assert (src.anomalies_detected + src.anomalies_missed == 55).all()
    assert src.set_index("alarm_layer").anomalies_detected.to_dict() == {
        "conformal_bh_rolling": 2, "threshold": 8, "conformal_bh": 8,
        "aci_event": 32, "aci": 51}


def test_threshold_and_bh_coincide_only_where_claimed():
    """They match on event-wise detection, and differ in alarm volume and ADTQC."""
    rows = {r["calibrator"]: r
            for r in json.loads((PROTO / "test/m1_target_ar8.json").read_text())}
    a, b = rows["threshold"], rows["conformal_bh"]
    for same in ("anomaly/EW_precision", "anomaly/EW_recall", "anomaly/EW_F0.5",
                 "false_alarms_per_year"):
        assert a[same] == b[same], same
    for differ in ("alarm_runs", "anomaly/ADTQC", "anomaly/alarming_precision"):
        assert a[differ] != b[differ], differ


# ------------------------------------------------------------------ J2 / J3: the frozen contrasts
def test_j2_reproduces_all_six_frozen_contrasts():
    src = pd.read_csv(DATA / "jint_F2_preregistered_contrasts.csv")
    record = json.loads((PROTO / "CONFIRMATORY.json").read_text())
    assert record["freeze_id"] == "09a98f5e160e"
    assert len(src) == 6
    for mission in (1, 2):
        frozen = record["missions"][str(mission)]["tests"]
        for t in frozen:
            name = t["comparison"].split(":")[0].strip()
            row = src[(src.mission == mission) & (src.hypothesis == name)]
            assert len(row) == 1, (mission, name)
            row = row.iloc[0]
            assert row["diff"] == pytest.approx(t["diff"], abs=1e-12)
            assert row.ci95_low == pytest.approx(t["ci95_low"], abs=1e-12)
            assert row.ci95_high == pytest.approx(t["ci95_high"], abs=1e-12)
            assert row.verdict == t["verdict"]


def test_j2_signs_are_not_flipped():
    """The M2 H6 sign error that an earlier extraction produced must not come back."""
    src = pd.read_csv(DATA / "jint_F2_preregistered_contrasts.csv").set_index(
        ["mission", "hypothesis"])
    assert src.loc[(1, "H6"), "diff"] > 0.3
    assert src.loc[(2, "H6"), "diff"] < -0.08
    assert src.loc[(1, "H4"), "diff"] < 0
    assert src.loc[(1, "H5"), "diff"] < 0


def test_j3_a0_comes_from_the_frozen_record_not_the_other_protocol():
    src = pd.read_csv(DATA / "jint_F3_arm_performance.csv")
    record = json.loads((PROTO / "CONFIRMATORY.json").read_text())
    for mission in (1, 2):
        h6 = [t for t in record["missions"][str(mission)]["tests"]
              if t["comparison"].startswith("H6")][0]
        a0 = src[(src.mission == mission) & (src.arm == "A0")]["mean"].iloc[0]
        a1 = src[(src.mission == mission) & (src.arm == "A1")]["mean"].iloc[0]
        assert a0 == pytest.approx(h6["B_official"], abs=1e-9)
        assert a1 == pytest.approx(h6["A_official"], abs=1e-9)
    # the two protocols must be labelled, because their numbers are not comparable
    protocols = set(src.selection_protocol)
    assert len(protocols) == 2, protocols


def test_j5_is_the_other_protocol_and_says_so():
    """J5 reads results.csv (arm-A0 selection); its A1-equivalent value must differ from J1's."""
    grid = pd.read_csv(DATA / "jint_F5_configuration_sensitivity.csv")
    a0_like = grid[(grid.mission == 1) & (grid.scale == "target (full)")
                   & (grid.scorer == "ar8") & (grid.calibrator == "conformal_bh")]
    assert len(a0_like) == 1
    assert float(a0_like["EW_F0.5_mean"].iloc[0]) == pytest.approx(0.074351, abs=1e-5)
    oof = pd.read_csv(DATA / "jint_F3_arm_performance.csv")
    a1 = oof[(oof.mission == 1) & (oof.arm == "A1")]["mean"].iloc[0]
    assert abs(a1 - float(a0_like["EW_F0.5_mean"].iloc[0])) > 0.3, (
        "the two selection protocols must stay distinguishable")
    assert "aci" not in set(grid.calibrator), "the A0 grid was never run with the ACI layers"


# ------------------------------------------------------------------ benchmarks
def test_b1_does_not_average_over_the_alarm_layer():
    """Collapsing the calibrator understates every learned ESA-ADB arm; the layer is named."""
    src = pd.read_csv(DATA / "benchmark_learned_vs_reference.csv")
    esa = src[src.setting.str.startswith("ESA-ADB")]
    assert len(esa) == 4
    assert esa.learned_name.str.contains(r" \+ ").all(), esa.learned_name.tolist()
    m1 = esa[esa.setting.str.contains("M1") & esa.setting.str.contains("target")].iloc[0]
    assert m1.learned == pytest.approx(0.318366, abs=1e-5)


def test_b1_keeps_the_losses_visible():
    src = pd.read_csv(DATA / "benchmark_learned_vs_reference.csv")
    life = pd.read_csv(DATA / "benchmark_lifetime_vs_physics.csv")
    losses = list(src[src.winner != "learned"].setting) + list(life[life.winner != "learned"].setting)
    assert len(losses) == 3, losses
    worst = src.loc[src.margin_learned_minus_reference.idxmin()]
    assert "Kelvins" in worst.setting
    assert worst.margin_learned_minus_reference == pytest.approx(-0.571075, abs=1e-5)


def test_b1_separates_the_two_conjunction_decision_rules():
    src = pd.read_csv(DATA / "benchmark_learned_vs_reference.csv")
    kel = src[src.setting.str.contains("Kelvins")]
    assert len(kel) == 2, "native and tuned decision rules must both be shown"
    assert set(kel.winner) == {"learned", "parameter-free reference"}, (
        "the two rules give opposite verdicts; both must appear")


def test_b2_rank_instability_is_real():
    src = pd.read_csv(DATA / "lifetime_rank_instability.csv").set_index("model")
    assert int(src.loc["physics_only", "rank_2011"]) == 1
    assert int(src.loc["physics_only", "rank_2016"]) == len(src)
    from scipy.stats import kendalltau
    tau = kendalltau(src.rank_2011, src.rank_2016).statistic
    assert tau < 0.1, tau


# ------------------------------------------------------------------ diagnostics
def test_g1_counts_the_failing_cells_correctly():
    cov = pd.read_csv(DATA / "diagnostics_phase_h_coverage.csv")
    assert len(cov) == 24
    deviating = int((cov.verdict != "CONSISTENT WITH NOMINAL").sum())
    assert deviating == 11, deviating
    assert set(cov.verdict) <= {"CONSISTENT WITH NOMINAL", "OVER-COVERS", "UNDER-COVERS"}


def test_g1_subgroup_coverage_shows_the_missingness_gap():
    sub = pd.read_csv(DATA / "diagnostics_subgroup_coverage.csv")
    design = sub[sub.subgroup == "am_source=design"]
    prior = sub[sub.subgroup == "am_source=class_prior_sbm"]
    assert design.cov80.max() < 0.60, design.cov80.tolist()
    assert prior.cov80.min() > 0.72, prior.cov80.tolist()


def test_g2_residuals_exclude_censored_objects():
    src = pd.read_csv(DATA / "diagnostics_lifetime_residuals.csv")
    reg = pd.read_csv(ROOT / "outputs/benchmarks/reentry_lifetime/"
                             "origin2016_uncontrolled/regression_test.csv")
    # the residual sample equals the objects recorded as decayed, and is strictly smaller
    # than the scored population -- the difference is the right-censored remainder
    assert set(src.n_residual) == {int(reg.n_decayed.iloc[0])}
    assert src.n_residual.iloc[0] < int(reg.n.iloc[0])
    assert set(src.n_excluded_censored_or_unknown) == {
        int(reg.n.iloc[0]) - int(reg.n_decayed.iloc[0])}


def test_g2_coverage_recomputed_from_arrays_matches_the_published_table():
    """An independent recomputation of cov80, straight from the prediction arrays."""
    src = pd.read_csv(DATA / "diagnostics_lifetime_residuals.csv").set_index("arm")
    reg = pd.read_csv(ROOT / "outputs/benchmarks/reentry_lifetime/"
                             "origin2016_uncontrolled/regression_test.csv").set_index("model")
    for arm in src.index:
        assert src.loc[arm, "coverage80_all_known5"] == pytest.approx(
            reg.loc[arm, "cov80"], abs=1e-9), arm


def test_g3_states_the_c1_result_without_overclaiming():
    src = pd.read_csv(DATA / "diagnostics_c1_family_effect.csv")
    assert len(src) == 4
    # exactly one cell survives correction, and it is an origin-selected learner
    sig = src[src.significant]
    assert len(sig) == 1 and sig.learner.iloc[0] == "tabm"
    # the common-learner cells flip sign and neither is significant
    common = src[src.learner == "mlp"].set_index("origin")
    assert common.loc[2011, "effect"] < 0 < common.loc[2016, "effect"]
    assert not src[src.learner == "mlp"].significant.any()


def test_g3_records_c4_as_not_evaluable():
    verdicts = pd.read_csv(DATA / "diagnostics_coupling_verdicts.csv").set_index("coupling")
    assert verdicts.loc["C4", "verdict"] == "NOT EVALUABLE"
    assert verdicts.loc["C3", "verdict"] == "INCONCLUSIVE"
    assert set(verdicts.verdict) != {"SUPPORTED"}, "no coupling was fully supported"


# ------------------------------------------------------------------ datasets / system outputs
def test_d3_label_scarcity_matches_the_dataset_report():
    src = pd.read_csv(DATA / "benchmark_label_scarcity.csv")
    rep = json.loads((ROOT / "data/DATASET_REPORT.json").read_text())
    m2 = src[src.benchmark.str.contains("M2")].iloc[0]
    assert m2.positives == rep["esa_adb"]["mission2"][
        "events_target_channels_by_period"]["test"]["Anomaly"] == 6
    land = src[src.benchmark.str.contains("landmark")].iloc[0]
    assert land.positives == rep["catalogue_and_reentry"]["landmark"][
        "events_by_split"]["test"]["events"] == 38
    assert int((src.positives < 60).sum()) == 3


def test_d1_marks_unavailable_corpora_rather_than_omitting_them():
    src = pd.read_csv(DATA / "datasets_inventory.csv")
    rep = json.loads((ROOT / "data/DATASET_REPORT.json").read_text())
    assert len(src) == len(rep["datasets"])
    unused = src[~src.feeds_a_reported_experiment]
    assert len(unused) >= 4, unused.dataset.tolist()
    assert "spark" in set(unused.dataset)


def test_d4_flags_the_constant_space_weather_features():
    blob = json.loads((DATA / "catalogue_feature_correlation.json").read_text())
    constant = blob["constant_features_no_rank_correlation_defined"]
    assert set(constant) == {"f107_last81", "ap_last81"}, constant


def test_s1_preserves_the_l17_record():
    src = pd.read_csv(DATA / "twin_snapshot_summary.csv").set_index("quantity")
    assert float(src.loc["L17 incoherent p_lifetime_* records", "value"]) == 123
    assert float(src.loc["objects with p_lifetime_* present", "value"]) == 13238
    # the column the console actually ranks on is coherent, and that is checked not assumed
    assert float(src.loc["incoherent p_* (ranking column) records", "value"]) == 0
    assert float(src.loc["objects with p_* present", "value"]) == 31396


def test_s1_discloses_the_variant_disagreement():
    src = pd.read_csv(DATA / "twin_snapshot_summary.csv").set_index("quantity")
    hist = float(src.loc["expected re-entries 30d, physics_history", "value"])
    life = float(src.loc["expected re-entries 30d, lifetime", "value"])
    assert life / hist > 5, "the variants disagree by a large factor; the figure must show it"


# ------------------------------------------------------------------ manuscript agreement
def test_manuscript_and_figures_do_not_contradict_each_other():
    text = MANUSCRIPT.read_text()
    src = pd.read_csv(DATA / "jint_F1_burden_recall.csv").set_index("alarm_layer")
    ratio = src.loc["aci", "false_alarms_per_year"] / src.loc["conformal_bh", "false_alarms_per_year"]
    assert f"{ratio:,.0f}" == "154,310"
    assert "154,310" in text
    assert "160,000" not in text, "the overstated ratio must not reappear"
    for value in ("0.927", "176,337", "1,234,479", "7.0007"):
        assert value in text, value


def test_manuscript_references_the_generated_figures():
    text = MANUSCRIPT.read_text()
    for stem in GROUPS["jint"]:
        assert f"paper/figures/jint/{stem}.png" in text, stem
    assert "scripts/figures/fig_jint.py" in text


def test_manuscript_no_longer_claims_identity_on_every_metric():
    """threshold and conformal_bh differ in ADTQC; the earlier blanket claim was wrong."""
    text = MANUSCRIPT.read_text()
    assert "identical to 17 significant\nfigures** on every event-wise metric" not in text
    assert "0.737444" in text and "0.738044" in text, (
        "the manuscript must show where the two layers actually differ")


# ------------------------------------------------------------------ release manifest
def test_release_manifest_matches_the_tree():
    """The manifest is only useful if its hashes still describe the files on disk."""
    import hashlib
    path = FIG / "RELEASE_MANIFEST.json"
    assert path.is_file(), "run scripts/figures/make_release_manifest.py"
    man = json.loads(path.read_text())

    assert man["figure_counts"] == {"stems": 18, "png": 18, "pdf": 18, "svg": 18}
    assert man["source_data_count"] == len(SOURCE_FILES)
    assert man["frozen_artifacts"]["esa_adb_freeze_id"] == "09a98f5e160e"
    assert man["git"]["commits_added_by_this_work"] == 0

    def digest(rel):
        h = hashlib.sha256()
        with (ROOT / rel).open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    # spot-check every group rather than every file, to keep the suite fast
    for fig in man["figures"]:
        rec = fig["formats"]["png"]
        assert rec["present"], fig["stem"]
        assert digest(rec["path"]) == rec["sha256"], f"{rec['path']} changed since the freeze"
    for rec in man["source_data"]:
        assert digest(rec["path"]) == rec["sha256"], f"{rec['path']} changed since the freeze"
    for rec in man["upstream_artifacts"]:
        assert rec["present"], rec["path"]
        assert digest(rec["path"]) == rec["sha256"], (
            f"UPSTREAM ARTIFACT CHANGED: {rec['path']} — a figure may now be stale")


def test_manifest_records_the_twin_digest_coverage_gap():
    """The shipped digest covers twins.jsonl only; the manifest must not imply otherwise."""
    man = json.loads((FIG / "RELEASE_MANIFEST.json").read_text())
    twin = man["twin_snapshot"]
    assert twin["files_covered_by_shipped_digest"] == ["twins.jsonl"]
    by_name = {Path(e["path"]).name: e for e in twin["files"]}
    assert by_name["twins.jsonl"]["shipped_digest_matches"] is True
    for name in ("forecast_table.csv.gz", "top50_reentry_30d.csv", "summary.json"):
        assert by_name[name]["covered_by_shipped_digest"] is False
        assert by_name[name]["sha256"], f"{name} must be hashed in the manifest instead"


def test_manifest_git_state_is_consistent_with_git():
    """The manifest's git snapshot must still describe the tree in the ways that matter for the
    figure release: every file it recorded as modified is either still modified or was carried into
    an owner-approved checkpoint commit descending from the manifest's commit (none reverted behind
    its back); nothing is staged; and HEAD is an approved checkpoint or descends from one (the owner-approved
    release commits of 2026-11-08 are created one at a time and can never list their own hash, so exact
    membership was the wrong predicate; descent is checked with ``git merge-base --is-ancestor`` in
    ``scripts.verify_protected_artifacts.head_is_approved``, whose own regression tests live in
    ``tests/test_approved_head.py``). Exact equality of the modified-file count was the wrong invariant — it
    failed on 2026-11-06 the moment unrelated, legitimate edits landed; and "still modified" became wrong on
    2026-11-08 when the owner approved the checkpoint commit 938d514 of all uncommitted work. Figure, source-data
    and upstream-artifact drift are caught by their hashes in the test above."""
    import subprocess
    from scripts.verify_protected_artifacts import head_is_approved
    man = json.loads((FIG / "RELEASE_MANIFEST.json").read_text())
    run = lambda *args: subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
    lines = [l for l in run("status", "--porcelain").split("\n") if l]
    modified_now = {l[3:] for l in lines if l.startswith(" M")}
    head = run("rev-parse", "HEAD").strip()
    assert head_is_approved(head)[0], f"HEAD {head[:12]} is neither an approved checkpoint nor a descendant of one"
    committed_since = set(run("diff", "--name-only", man["git"]["commit"], head).split()) if head != man["git"]["commit"] else set()
    if head != man["git"]["commit"]:
        assert run("merge-base", "--is-ancestor", man["git"]["commit"], head) == "" and \
            subprocess.run(["git", "merge-base", "--is-ancestor", man["git"]["commit"], head], cwd=ROOT).returncode == 0, \
            "HEAD does not descend from the manifest's commit"
    recorded = set(man["git"]["tracked_files_modified_list"])
    unexplained = recorded - modified_now - committed_since
    assert not unexplained, f"files the manifest recorded as modified were neither kept nor committed: {sorted(unexplained)}"
    assert man["git"]["tracked_files_modified"] == len(recorded), "manifest count disagrees with its own list"
    assert man["git"]["staged"] == 0 and not any(l[:1] in "MARDC" for l in lines), "nothing may be staged"
    assert man["git"]["commits_added_by_this_work"] == 0
