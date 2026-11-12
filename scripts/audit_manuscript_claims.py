"""Trace every quantitative claim in the JINT manuscript back to an archived artifact.

    python scripts/audit_manuscript_claims.py                 # audit, print table
    python scripts/audit_manuscript_claims.py --json out.json # also write machine-readable

Each check names the manuscript section, the claim, the artifact it must come from, and how the
value is recomputed. Nothing is compared against a previous audit's conclusion: every number is
re-derived from the archive on this run. A claim is only PASS if the recomputed value matches the
manuscript text within the tolerance implied by the manuscript's own precision.

Statuses
    PASS           recomputed and matches
    FAIL           recomputed and does not match -- requires a manuscript correction
    NOT_EVALUABLE  no artifact in this repository can confirm or refute it
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MS = ROOT / "paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md"
PROTO = ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol"
RESULTS = ROOT / "outputs/benchmarks/telemetry_esa_adb/results.csv"
REPORT = ROOT / "data/DATASET_REPORT.json"
CAL = "conformal_bh"
PRIMARY = "anomaly_and_rare/EW_F0.5"
ANOM = "anomaly/EW_F0.5"

checks: list[dict] = []


def record(section, claim, artifact, method, expected, actual, status, correction=""):
    checks.append({"section": section, "claim": claim, "artifact": artifact, "method": method,
                   "manuscript_value": expected, "recomputed_value": actual,
                   "status": status, "required_correction": correction})


def cmp_num(section, claim, artifact, method, expected, actual, tol, correction_hint=""):
    if actual is None:
        record(section, claim, artifact, method, expected, None, "NOT_EVALUABLE", correction_hint)
        return
    ok = abs(float(actual) - float(expected)) <= tol
    record(section, claim, artifact, method, expected, round(float(actual), 6),
           "PASS" if ok else "FAIL",
           "" if ok else (correction_hint or f"manuscript says {expected}, archive gives "
                                             f"{float(actual):.6g}"))


def text() -> str:
    return MS.read_text()


def in_text(section, claim, needle, artifact="manuscript", method="literal string present"):
    present = needle in text()
    record(section, claim, artifact, method, needle, present,
           "PASS" if present else "FAIL",
           "" if present else f"the string {needle!r} is absent from the manuscript")


# --------------------------------------------------------------------------- loaders
def proto_rows(tag: str) -> list[dict]:
    p = PROTO / "test" / f"{tag}.json"
    return json.loads(p.read_text()) if p.is_file() else []


def layer(tag: str, cal: str) -> dict | None:
    return {r["calibrator"]: r for r in proto_rows(tag)}.get(cal)


def arm_vals(tags: list[str], field: str, cal: str = CAL) -> list[float]:
    return [r[field] for t in tags for r in proto_rows(t) if r["calibrator"] == cal]


def results_frame() -> pd.DataFrame:
    f = pd.read_csv(RESULTS)
    f["scale"] = np.where(f.tag.str.contains("_target_"), "target", "lightweight")
    f["scorer"] = (f.tag.str.replace(r"^m\d_(target|lightweight)_", "", regex=True)
                        .str.replace(r"_s\d+$", "", regex=True))
    return f


def confirmatory() -> dict:
    return json.loads((PROTO / "CONFIRMATORY.json").read_text())


def tests_by_name() -> dict:
    out = {}
    for m, blk in confirmatory()["missions"].items():
        for t in blk["tests"]:
            out[f"M{m}_{t['comparison'].split(':')[0].strip()}"] = t
    return out


ARMS = {
    "A1": lambda m: [f"m{m}_target_ar8"],
    "A2": lambda m: [f"m{m}_target_gbt_ar8_s{s}_event" for s in range(5)],
    "A3": lambda m: [f"m{m}_target_event_ar8_all_c3_s{s}_event" for s in range(5)],
}


# =========================================================================== the audit
def audit() -> None:
    rep = json.loads(REPORT.read_text())
    T = tests_by_name()
    rframe = results_frame()

    # ---------------- §10 dataset and protocol specification
    m1 = rep["esa_adb"]["mission1"]
    m2 = rep["esa_adb"]["mission2"]
    ev1 = m1["events_target_channels_by_period"]
    train_events = sum(ev1[p]["events"] for p in ("fit", "es", "cal"))
    train_anom = sum(ev1[p].get("Anomaly", 0) for p in ("fit", "es", "cal"))
    train_rare = sum(ev1[p].get("Rare Event", 0) for p in ("fit", "es", "cal"))
    train_gaps = sum(ev1[p].get("Communication Gap", 0) for p in ("fit", "es", "cal"))
    cmp_num("§10", "M1 train: 109 annotated events on target channels", "DATASET_REPORT.json",
            "sum of events over fit+es+cal periods", 109, train_events, 0)
    cmp_num("§10", "M1 train: 63 anomalies", "DATASET_REPORT.json",
            "sum of Anomaly over fit+es+cal", 63, train_anom, 0)
    cmp_num("§10", "M1 train: 42 rare events", "DATASET_REPORT.json",
            "sum of Rare Event over fit+es+cal", 42, train_rare, 0)
    cmp_num("§10", "M1 train: 4 communication gaps", "DATASET_REPORT.json",
            "sum of Communication Gap over fit+es+cal", 4, train_gaps, 0)
    cmp_num("§10", "M1 test: 55 anomalies", "DATASET_REPORT.json",
            "esa_adb.mission1...test.Anomaly", 55, ev1["test"]["Anomaly"], 0)
    cmp_num("§10", "M1 test: 36 rare events", "DATASET_REPORT.json",
            "esa_adb.mission1...test['Rare Event']", 36, ev1["test"]["Rare Event"], 0)
    ev2 = m2["events_target_channels_by_period"]
    cmp_num("§10", "M2 test: 6 anomalies", "DATASET_REPORT.json",
            "esa_adb.mission2...test.Anomaly", 6, ev2["test"]["Anomaly"], 0)
    cmp_num("§10", "M2 test: 356 rare events", "DATASET_REPORT.json",
            "esa_adb.mission2...test['Rare Event']", 356, ev2["test"]["Rare Event"], 0)
    cmp_num("§10", "M1 target channels 58 of 76", "DATASET_REPORT.json",
            "esa_adb.mission1.target_channels", 58, m1["target_channels"], 0)
    cmp_num("§10", "M2 target channels 47 of 100", "DATASET_REPORT.json",
            "esa_adb.mission2.target_channels", 47, m2["target_channels"], 0)
    cmp_num("§10", "A0 selection period holds 9 M1 annotated events", "DATASET_REPORT.json",
            "esa_adb.mission1...cal.events", 9, ev1["cal"]["events"], 0)
    cmp_num("§8", "A1 selection uses 105 M1 annotated events",
            "DATASET_REPORT.json",
            "fit+es+cal events minus the 4 communication gaps = 109 - 4",
            105, train_events - train_gaps, 0)

    # block counts: derive from the official split dates and the 30-day block size
    for mission, blk, expect in ((1, m1, 86), (2, m2, 22)):
        start = pd.Timestamp(blk["test"]["start"])
        end = pd.Timestamp(blk["test"]["end"])
        n_blocks = int(np.ceil((end - start).days / 30))
        cmp_num("§10", f"M{mission} bootstrap blocks = {expect}",
                "DATASET_REPORT.json test window + 30-day block size",
                "ceil(test span in days / 30)", expect, n_blocks, 0,
                correction_hint=f"derived {n_blocks} from the archived split dates")

    # ---------------- §11 / §18 EventTCN capacity
    meta = ROOT / ("outputs/benchmarks/telemetry_esa_adb/event_model/"
                   "m1_target_event_ar8_all_c3_s4/meta.json")
    params = None
    if meta.is_file():
        j = json.loads(meta.read_text())
        for key in ("params", "n_params", "parameters"):
            if key in j:
                params = j[key]
                break
    cmp_num("§11/§18", "EventTCN has 220,739 parameters",
            "event_model/m1_target_event_ar8_all_c3_s4/meta.json", "read recorded param count",
            220739, params, 0)

    # ---------------- §12 pre-registration exists
    prereg = ROOT / "research_design/preregistration/PREREG_TELEMETRY_V1.md"
    record("§12", "hypotheses fixed in PREREG_TELEMETRY_V1.md", str(prereg.relative_to(ROOT)),
           "file exists on disk", "present", prereg.is_file(),
           "PASS" if prereg.is_file() else "FAIL")

    # ---------------- §13 reproduction of all six contrasts
    for name, t in T.items():
        a = np.mean(arm_vals(ARMS["A1"](name[1]), PRIMARY)) if "H6" in name else None
        # re-derive each contrast from the per-arm records
        mission = name[1]
        if name.endswith("H4"):
            got = np.mean(arm_vals(ARMS["A3"](mission), PRIMARY)) - \
                  np.mean(arm_vals(ARMS["A1"](mission), PRIMARY))
        elif name.endswith("H5"):
            got = np.mean(arm_vals(ARMS["A3"](mission), PRIMARY)) - \
                  np.mean(arm_vals(ARMS["A2"](mission), PRIMARY))
        else:
            sel = rframe[(rframe.mission == int(mission))
                         & (rframe.tag == f"m{mission}_target_ar8_s0")
                         & (rframe.calibrator == CAL)]
            got = float(np.mean(arm_vals(ARMS["A1"](mission), PRIMARY))) - \
                float(sel[PRIMARY].iloc[0])
        cmp_num("§13", f"{name} reproduces {t['diff_official']:+.4f}",
                "oof_protocol/test/*.json + results.csv",
                "re-derive the contrast from per-arm records, official metric",
                round(t["diff_official"], 4), got, 6e-4)

    # ---------------- §14.1 H6
    h6 = T["M1_H6"]
    cmp_num("§14.1", "H6 effect +0.353", "CONFIRMATORY.json", "diff_official",
            0.353, h6["diff_official"], 5e-4)
    cmp_num("§14.1", "H6 CI low +0.206", "CONFIRMATORY.json", "ci95_low",
            0.206, h6["ci95_low"], 5e-4)
    cmp_num("§14.1", "H6 CI high +0.488", "CONFIRMATORY.json", "ci95_high",
            0.488, h6["ci95_high"], 5e-4)
    cmp_num("§14.1", "H6 Holm p = 0.0015", "CONFIRMATORY.json", "p_holm",
            0.0015, h6["p_holm"], 1e-9)
    cmp_num("§14.1", "H6 bootstrap p = 0.0005 (floor)", "CONFIRMATORY.json", "p_boot",
            0.0005, h6["p_boot"], 1e-9)
    cmp_num("§14.1", "A0 Mission 1 = 0.0744", "CONFIRMATORY.json", "B_official",
            0.0744, h6["B_official"], 5e-5)
    cmp_num("§14.1", "A1 Mission 1 = 0.4278", "CONFIRMATORY.json", "A_official",
            0.4278, h6["A_official"], 5e-5)

    # ---------------- §14.2 H4, H5 and arm spreads
    cmp_num("§14.2", "H4 effect -0.222", "CONFIRMATORY.json", "diff_official",
            -0.222, T["M1_H4"]["diff_official"], 5e-4)
    cmp_num("§14.2", "H5 effect -0.338", "CONFIRMATORY.json", "diff_official",
            -0.338, T["M1_H5"]["diff_official"], 5e-4)
    cmp_num("§14.2", "H4 Holm p = 0.101", "CONFIRMATORY.json", "p_holm",
            0.101, T["M1_H4"]["p_holm"], 1e-9)
    cmp_num("§14.2", "H5 Holm p = 0.070", "CONFIRMATORY.json", "p_holm",
            0.070, T["M1_H5"]["p_holm"], 1e-9)
    for arm, mean_c, sd_c, lo_c, hi_c in (("A2", 0.5436, 0.2357, 0.1572, 0.7692),
                                          ("A3", 0.2054, 0.1142, 0.0854, 0.3582)):
        v = arm_vals(ARMS[arm](1), PRIMARY)
        cmp_num("§14.2", f"{arm} Mission 1 mean {mean_c}", "oof_protocol/test/*.json",
                "mean over 5 seeds, primary calibrator", mean_c, np.mean(v), 5e-5)
        cmp_num("§14.2", f"{arm} seed SD {sd_c}", "oof_protocol/test/*.json",
                "sample SD (ddof=1) over 5 seeds", sd_c, np.std(v, ddof=1), 5e-5)
        cmp_num("§14.2", f"{arm} seed min {lo_c}", "oof_protocol/test/*.json",
                "min over 5 seeds", lo_c, min(v), 5e-5)
        cmp_num("§14.2", f"{arm} seed max {hi_c}", "oof_protocol/test/*.json",
                "max over 5 seeds", hi_c, max(v), 5e-5)

    # ---------------- §14.3 the alarm-layer table, every cell
    table = {
        "threshold":            (0.4278, 0.3361, 0.500, 0.1455, 0.737, 90, 8, 1.14),
        "conformal_bh":         (0.4278, 0.3361, 0.500, 0.1455, 0.738, 123, 8, 1.14),
        "conformal_bh_rolling": (0.1010, 0.1587, 1.000, 0.0364, 1.000, 2, 0, 0.00),
        "aci_event":            (0.0085, 0.0048, 0.0039, 0.5818, 0.799, 9115, 8044, 1149.03),
        "aci":                  (0.00005, 0.0000, 0.000024, 0.9273, 0.906, 1383948, 1234479,
                                 176336.90),
    }
    fields = [(PRIMARY, 5e-5), (ANOM, 5e-5), ("anomaly/EW_precision", 5e-4),
              ("anomaly/EW_recall", 5e-5), ("anomaly/ADTQC", 5e-4),
              ("alarm_runs", 0), ("false_alarm_runs", 0), ("false_alarms_per_year", 5e-3)]
    for lay, expected in table.items():
        rec = layer("m1_target_ar8", lay)
        for (field, tol), exp in zip(fields, expected):
            cmp_num("§14.3", f"{lay} {field} = {exp}", "oof_protocol/test/m1_target_ar8.json",
                    "read archived per-layer record", exp, rec[field] if rec else None, tol)

    aci, bh = layer("m1_target_ar8", "aci"), layer("m1_target_ar8", CAL)
    cmp_num("§14.3/§21", "false-alarm ratio = 154,310", "oof_protocol/test/m1_target_ar8.json",
            "aci false_alarms_per_year / conformal_bh false_alarms_per_year",
            154310, aci["false_alarms_per_year"] / bh["false_alarms_per_year"], 1.0)
    cmp_num("§14.3", "ratio identical on run counts", "same",
            "aci false_alarm_runs / conformal_bh false_alarm_runs",
            154310, aci["false_alarm_runs"] / bh["false_alarm_runs"], 1.0)
    cmp_num("§14.3", "recall ratio 6.4x", "same", "aci recall / conformal_bh recall",
            6.4, aci["anomaly/EW_recall"] / bh["anomaly/EW_recall"], 0.05)
    periods = []
    for lay in table:
        r = layer("m1_target_ar8", lay)
        if r["false_alarms_per_year"]:
            periods.append(r["false_alarm_runs"] / r["false_alarms_per_year"])
    cmp_num("§14.3", "evaluation period 7.0007 years, identical across layers",
            "oof_protocol/test/m1_target_ar8.json",
            "false_alarm_runs / false_alarms_per_year for every layer with a non-zero rate",
            7.0007, np.mean(periods), 1e-3)
    record("§14.3", "the period is the same for every layer (spread < 1e-3)",
           "oof_protocol/test/m1_target_ar8.json", "max - min over layers",
           "< 1e-3", round(float(max(periods) - min(periods)), 9),
           "PASS" if max(periods) - min(periods) < 1e-3 else "FAIL")
    cmp_num("§14.3", "ACI recall is 51 of 55 anomalies", "same",
            "round(recall x 55)", 51, round(aci["anomaly/EW_recall"] * 55), 0)
    cmp_num("§14.3", "BH recall is 8 of 55 anomalies", "same",
            "round(recall x 55)", 8, round(bh["anomaly/EW_recall"] * 55), 0)

    # layer spread, non-pathological subset
    nonpath = [layer("m1_target_ar8", c)[ANOM]
               for c in ("threshold", CAL, "conformal_bh_rolling")]
    cmp_num("§14.3", "non-pathological layer spread 2.12x", "oof_protocol/test/m1_target_ar8.json",
            "max/min of anomaly-only F0.5 over threshold, conformal_bh, conformal_bh_rolling",
            2.12, max(nonpath) / min(nonpath), 0.01)
    cmp_num("§14.3", "non-pathological layer min 0.1587", "same", "min of that set",
            0.1587, min(nonpath), 5e-5)
    cmp_num("§14.3", "non-pathological layer max 0.3361", "same", "max of that set",
            0.3361, max(nonpath), 5e-5)

    # scorer spread under the primary layer, same mission and scale
    scorers = ("ar8", "patchtst", "patchtst_tc", "tcn", "tcn_tc", "chronos-bolt-small")
    sub = rframe[(rframe.mission == 1) & (rframe.scale == "target")
                 & (rframe.calibrator == CAL) & (rframe.scorer.isin(scorers))]
    by_scorer = sub.groupby("scorer")[ANOM].mean()
    cmp_num("§14.3", "scorer spread 4.35x under the primary layer", "results.csv",
            "max/min of anomaly-only F0.5 across learned scorers, M1 target, conformal_bh",
            4.35, by_scorer.max() / by_scorer.min() if len(by_scorer) else None, 0.02,
            correction_hint="recomputed from results.csv (arm-A0 selection protocol)")
    cmp_num("§14.3", "scorer spread lower bound 0.0073", "results.csv",
            "min of that set", 0.0073, by_scorer.min() if len(by_scorer) else None, 5e-4)
    cmp_num("§14.3", "scorer spread upper bound 0.0316", "results.csv",
            "max of that set", 0.0316, by_scorer.max() if len(by_scorer) else None, 5e-4)

    # A2 under threshold vs primary
    a2_thresh = arm_vals(ARMS["A2"](1), PRIMARY, cal="threshold")
    cmp_num("§14.3", "A2 Mission 1 under `threshold` = 0.6134", "oof_protocol/test/*.json",
            "mean over 5 seeds, threshold calibrator", 0.6134,
            np.mean(a2_thresh) if a2_thresh else None, 5e-5)

    # ---------------- §15 anomaly-only ablation
    def anom_contrast(mission, a, b):
        if b == "A0":
            sel = rframe[(rframe.mission == mission)
                         & (rframe.tag == f"m{mission}_target_ar8_s0")
                         & (rframe.calibrator == CAL)]
            bval = float(sel[ANOM].iloc[0])
        else:
            bval = float(np.mean(arm_vals(ARMS[b](mission), ANOM)))
        return float(np.mean(arm_vals(ARMS[a](mission), ANOM))) - bval

    cmp_num("§15", "H6 anomaly-only +0.3045", "oof_protocol + results.csv",
            "A1 - A0 on the anomaly-only metric", 0.3045, anom_contrast(1, "A1", "A0"), 5e-4)
    cmp_num("§15", "H4 anomaly-only -0.2112", "oof_protocol/test/*.json",
            "A3 - A1 on the anomaly-only metric", -0.2112, anom_contrast(1, "A3", "A1"), 5e-4)
    cmp_num("§15", "H5 anomaly-only -0.2017", "oof_protocol/test/*.json",
            "A3 - A2 on the anomaly-only metric", -0.2017, anom_contrast(1, "A3", "A2"), 5e-4)

    # ---------------- §16.1 cross-fitting optimism
    a1_t = layer("m1_target_ar8", CAL)
    cmp_num("§16.1", "M1 target selection score 0.6237", "oof_protocol/test/m1_target_ar8.json",
            "cv_EW_F0.5 for arm A1, primary calibrator", 0.6237, a1_t["cv_EW_F0.5"], 5e-5)
    cmp_num("§16.1", "M1 target test score 0.4278", "same", PRIMARY, 0.4278, a1_t[PRIMARY], 5e-5)
    a1_l = layer("m1_lightweight_ar8", CAL)
    cmp_num("§16.1", "M1 lightweight selection score 0.5278",
            "oof_protocol/test/m1_lightweight_ar8.json", "cv_EW_F0.5", 0.5278,
            a1_l["cv_EW_F0.5"] if a1_l else None, 5e-5)
    cmp_num("§16.1", "M1 lightweight test score 0.0247", "same", PRIMARY, 0.0247,
            a1_l[PRIMARY] if a1_l else None, 5e-5)
    if a1_l:
        cmp_num("§16.1", "lightweight optimism factor 21.4x", "same",
                "selection / test", 21.4, a1_l["cv_EW_F0.5"] / a1_l[PRIMARY], 0.15)
        cmp_num("§16.1", "target optimism factor 1.5x", "same", "selection / test",
                1.5, a1_t["cv_EW_F0.5"] / a1_t[PRIMARY], 0.05)

    # ---------------- §16.2 Mission 2 table
    m2_tab = {"A0": (0.9624, 0.1471, 0.143, 0.167),
              "A1": (0.8735, 0.0000, 0.000, 0.000),
              "A2": (0.9039, 0.1288, 0.130, 0.133),
              "A3": (0.8749, 0.1797, 0.307, 0.133)}
    for arm, (comp, anom, prec, rec) in m2_tab.items():
        if arm == "A0":
            sel = rframe[(rframe.mission == 2) & (rframe.tag == "m2_target_ar8_s0")
                         & (rframe.calibrator == CAL)]
            got = {PRIMARY: float(sel[PRIMARY].iloc[0]), ANOM: float(sel[ANOM].iloc[0]),
                   "anomaly/EW_precision": float(sel["anomaly/EW_precision"].iloc[0]),
                   "anomaly/EW_recall": float(sel["anomaly/EW_recall"].iloc[0])}
        else:
            got = {f: float(np.mean(arm_vals(ARMS[arm](2), f))) for f in
                   (PRIMARY, ANOM, "anomaly/EW_precision", "anomaly/EW_recall")}
        cmp_num("§16.2", f"M2 {arm} composite {comp}", "oof_protocol/results.csv",
                "mean over seeds, primary calibrator", comp, got[PRIMARY], 5e-5)
        cmp_num("§16.2", f"M2 {arm} anomaly-only {anom}", "same", "same", anom, got[ANOM], 5e-5)
        cmp_num("§16.2", f"M2 {arm} anomaly precision {prec}", "same", "same", prec,
                got["anomaly/EW_precision"], 5e-4)
        cmp_num("§16.2", f"M2 {arm} anomaly recall {rec}", "same", "same", rec,
                got["anomaly/EW_recall"], 5e-4)
    a1_m2 = layer("m2_target_ar8", CAL)
    cmp_num("§16.2", "M2 A1 raises 238 alarm runs", "oof_protocol/test/m2_target_ar8.json",
            "alarm_runs", 238, a1_m2["alarm_runs"] if a1_m2 else None, 0)
    cmp_num("§16.2", "M2 H6 composite -0.089", "CONFIRMATORY.json", "diff_official",
            -0.089, T["M2_H6"]["diff_official"], 5e-4)
    cmp_num("§16.2", "M2 H6 anomaly-only -0.147", "oof_protocol + results.csv",
            "A1 - A0 on the anomaly-only metric, Mission 2",
            -0.147, anom_contrast(2, "A1", "A0"), 5e-4)
    ool = rframe[(rframe.mission == 2) & (rframe.scale == "lightweight")
                 & (rframe.scorer == "out_of_limits")]
    if len(ool):
        r = ool.iloc[0]
        cmp_num("§16.2", "M2 lightweight out-of-limit composite 0.9648", "results.csv",
                "read row", 0.9648, r[PRIMARY], 5e-5)
        cmp_num("§16.2", "M2 lightweight out-of-limit anomaly-only 0.0877", "results.csv",
                "read row", 0.0877, r[ANOM], 5e-5)
        cmp_num("§16.2", "M2 lightweight out-of-limit 3,162 rare-event-only runs", "results.csv",
                "rare_event_only_runs", 3162, r.get("rare_event_only_runs"), 0)

    # ---------------- §17 selection-score correlations
    from scipy.stats import spearmanr
    for mission, exp_comp, exp_anom in ((1, 0.455, 0.282), (2, -0.118, -0.149)):
        xs, ys_c, ys_a = [], [], []
        for arm in ("A1", "A2", "A3"):
            for t in ARMS[arm](mission):
                for r in proto_rows(t):
                    if r["calibrator"] != CAL or r.get("cv_EW_F0.5") is None:
                        continue
                    xs.append(r["cv_EW_F0.5"])
                    ys_c.append(r[PRIMARY])
                    ys_a.append(r[ANOM])
        cmp_num("§17", f"M{mission} per-run Spearman composite {exp_comp:+.3f}",
                "oof_protocol/test/*.json", "spearmanr(cv_EW_F0.5, composite) over runs",
                exp_comp, spearmanr(xs, ys_c).statistic if len(xs) > 2 else None, 5e-4)
        cmp_num("§17", f"M{mission} per-run Spearman anomaly-only {exp_anom:+.3f}",
                "oof_protocol/test/*.json", "spearmanr(cv_EW_F0.5, anomaly-only) over runs",
                exp_anom, spearmanr(xs, ys_a).statistic if len(xs) > 2 else None, 5e-4)
        cmp_num("§17", f"M{mission} run count 11", "oof_protocol/test/*.json",
                "number of runs with a selection score", 11, len(xs), 0)

    # ---------------- §14.4 the disclosed discrepancy
    ool1 = rframe[(rframe.mission == 1) & (rframe.scale == "target")
                  & (rframe.scorer == "out_of_limits")]
    if len(ool1):
        cmp_num("§14.4", "our out-of-limit rule scores 0.0007", "results.csv",
                "M1 target out_of_limits, primary metric", 0.0007, ool1.iloc[0][PRIMARY], 5e-5)
        cmp_num("§14.4", "out-of-limit rule produces 11,627 false alarms per year", "results.csv",
                "false_alarms_per_year on that row", 11627,
                ool1.iloc[0].get("false_alarms_per_year"), 1.0)
    pt = rframe[(rframe.mission == 1) & (rframe.scale == "target")
                & (rframe.scorer == "patchtst") & (rframe.calibrator == CAL)]
    if len(pt):
        cmp_num("§14.4", "our PatchTST anomaly-only value 0.0163", "results.csv",
                "mean anomaly-only F0.5 over patchtst seeds, M1 target, conformal_bh",
                0.0163, pt[ANOM].mean(), 5e-4)

    # ---------------- claims with no artifact in this repository
    for section, claim, why in (
        ("§11/§14.4", "ported GlobalSTD reproduces published values to within 0.001 in all "
                      "eight configurations",
         "the published reference values (DMLR Table 4) are not stored in this repository, so the "
         "comparison cannot be recomputed here; only our own GlobalSTD outputs are archived"),
        ("§10", "the frozen code reproduces saved A0 and A1 alarms bit for bit",
         "no stored diff or hash-comparison record of that reproduction was found in outputs/"),
        ("§14.4", "Brancato et al. report 0.902 / 0.883 / 0.754 on Mission 1 full channels",
         "external publication, paywalled; full text was not obtained"),
        ("§14.4", "TC-CAD reports anomaly event-wise F0.5 of 0.090 at its baseline",
         "external artifact (Zenodo 10.5281/zenodo.23322711); not mirrored in this repository"),
        ("§18", "a sequential test pass over ~20 arms takes 5-6 hours",
         "recorded in the pre-registration as a plan, not measured into an archived timing file"),
        ("§20.2", "the restore step affects 51 Mission 1 grid points and has zero effect on "
                  "Mission 1 detections",
         "no archived artifact quantifying the restore-step effect was found"),
        ("§20.1", "per-channel score ratios span 0.52-4.70 with 37 of 58 channels at the sigma "
                  "floor",
         "the per-channel sigma diagnostic is not among the archived protocol outputs"),
    ):
        record(section, claim, "external or unarchived", "no recomputation possible here",
               "as stated", None, "NOT_EVALUABLE", why)

    # ---------------- figure/manuscript agreement
    f1 = pd.read_csv(ROOT / "paper/figures/data/jint_F1_burden_recall.csv").set_index("alarm_layer")
    ratio = f1.loc["aci", "false_alarms_per_year"] / f1.loc[CAL, "false_alarms_per_year"]
    in_text("§14.3", "manuscript states the corrected ratio 154,310", "154,310")
    record("§14.3", "figure J1 source data agrees with the manuscript ratio",
           "paper/figures/data/jint_F1_burden_recall.csv", "recompute from the figure's own CSV",
           "154,310", f"{ratio:,.0f}", "PASS" if f"{ratio:,.0f}" == "154,310" else "FAIL")
    record("§14.3", "the superseded ratio 160,000 is absent", "manuscript",
           "literal string search", "absent", "160,000" not in text(),
           "PASS" if "160,000" not in text() else "FAIL")

    # J2 plots the bootstrap point estimate; the tables quote the official one
    f2 = pd.read_csv(ROOT / "paper/figures/data/jint_F2_preregistered_contrasts.csv")
    h5_fig = float(f2[(f2.mission == 1) & (f2.hypothesis == "H5")]["diff"].iloc[0])
    disclosed = ("paired-bootstrap" in text() and "official-metric differences" in text()
                 and f"H5 {h5_fig:.3f} plotted".replace("-", "−") in text().replace("-", "−"))
    record("§14.2 vs Figure J2",
           "figure J2's point estimate and the §14.2 table use different estimators",
           "CONFIRMATORY.json diff vs diff_official",
           "the J2 caption must disclose the estimator difference with the plotted value",
           "table -0.338 (official)", f"figure {h5_fig:.3f} (bootstrap); caption disclosure {'present' if disclosed else 'absent'}",
           "PASS" if disclosed else "FAIL",
           "" if disclosed else "J2 plots the bootstrap point estimate while the tables quote the official-metric "
           "value; they differ by 0.0081 on M1 H5 and 0.0017 on M1 H6. Label the figure.")

    # §15 stale framing
    stale = "dominates the scorer by ~3 orders of magnitude" in text()
    record("§15", "ablation table describes the layer effect as ~3 orders of magnitude",
           "manuscript §15 vs §14.3", "literal string search",
           "absent after the §14.3 correction", "present" if stale else "absent",
           "FAIL" if stale else "PASS",
           "contradicts §14.3, which restricts the like-for-like spread to 2.12x and states the "
           "~11,000x figure is driven by one pathological configuration" if stale else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=None)
    ap.add_argument("--only", default=None, help="filter by status, e.g. FAIL")
    args = ap.parse_args(argv)

    audit()
    frame = pd.DataFrame(checks)
    counts = frame.status.value_counts().to_dict()

    show = frame if not args.only else frame[frame.status == args.only]
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 62)
    pd.set_option("display.max_rows", 400)
    print(show[["section", "claim", "manuscript_value", "recomputed_value", "status"]]
          .to_string(index=False))
    print(f"\n  total {len(frame)}   " + "   ".join(f"{k} {v}" for k, v in sorted(counts.items())))

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"counts": counts, "checks": checks}, indent=1, default=str) + "\n")
        print(f"  written {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
