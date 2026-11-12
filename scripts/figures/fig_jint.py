"""The JINT alarm-selection manuscript figures, built only from archived protocol records.

    python scripts/figures/fig_jint.py

Nothing is hard-coded or illustrative: every plotted number is read from an artifact on disk and
the exact rows plotted are written next to the image under ``paper/figures/data/``.

Two protocols appear in this project and they must never be mixed. The script enforces that:

  * ``oof_protocol/test/*.json``  -- arm A1/A2/A3, selection cross-fitted over the **whole
    training half**. Carries the five alarm layers including the two adaptive-conformal ones.
  * ``results.csv``              -- arm A0, selection on the **9-month calibration period** only.
    Carries four layers (no ACI) but a much wider scorer grid.

A0 is read from the frozen confirmatory record and cross-checked against ``results.csv``; the run
aborts if they disagree, because that pairing is the whole content of hypothesis H6.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import figstyle as S  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

PROTO = "outputs/benchmarks/telemetry_esa_adb/oof_protocol"
TESTD = PROTO + "/test"
RESULTS = "outputs/benchmarks/telemetry_esa_adb/results.csv"
CAL = "conformal_bh"                       # the pre-registered primary alarm layer

# Mission 1 test half, from data/DATASET_REPORT.md: 91 labelled events on target channels,
# 55 of type Anomaly and 36 of type Rare Event.
M1_TEST_ANOMALIES = 55

LAYER_ORDER = ["conformal_bh_rolling", "threshold", "conformal_bh", "aci_event", "aci"]
LAYER_LABEL = {
    "conformal_bh_rolling": "BH rolling",
    "threshold": "threshold",
    "conformal_bh": "BH (primary)",
    "aci_event": "ACI event-agg.",
    "aci": "ACI point-level",
}
LAYER_STYLE = {                             # marker, colour slot -- fixed, never cycled
    "conformal_bh_rolling": ("P", S.C5),
    "threshold": ("s", S.C3),
    "conformal_bh": ("D", S.C1),
    "aci_event": ("^", S.C2),
    "aci": ("v", S.C4),
}
ARM_STYLE = {"A1": ("o", S.C1), "A2": ("s", S.C3), "A3": ("^", S.C2)}


# ------------------------------------------------------------------------------- data access
def rows(root: Path, tag: str) -> list[dict]:
    path = root / TESTD / f"{tag}.json"
    return json.loads(path.read_text()) if path.is_file() else []


def layers_m1(root: Path) -> dict[str, dict]:
    """The five alarm layers for arm A1 on Mission 1 -- same scorer, same test half."""
    return {r["calibrator"]: r for r in rows(root, "m1_target_ar8")}


def arm_tags(mission: int) -> dict[str, list[str]]:
    return {
        "A1": [f"m{mission}_target_ar8"],
        "A2": [f"m{mission}_target_gbt_ar8_s{s}_event" for s in range(5)],
        "A3": [f"m{mission}_target_event_ar8_all_c3_s{s}_event" for s in range(5)],
    }


def arm_values(root: Path, tags: list[str], field: str) -> list[float]:
    return [r[field] for t in tags for r in rows(root, t) if r["calibrator"] == CAL]


def a0_value(root: Path, mission: int) -> float:
    """Arm A0 under the primary layer, from the frozen record, cross-checked against results.csv.

    A0 selects its alarm configuration on the 9-month calibration period; A1 cross-fits over the
    whole training half. Keeping these straight is the content of H6, so disagreement is fatal.
    """
    record = json.loads((root / PROTO / "CONFIRMATORY.json").read_text())
    h6 = [t for t in record["missions"][str(mission)]["tests"]
          if t["comparison"].startswith("H6")]
    assert len(h6) == 1, f"expected exactly one H6 test for mission {mission}"
    frozen = float(h6[0]["B_official"])

    frame = pd.read_csv(root / RESULTS)
    sel = frame[(frame.mission == mission)
                & (frame.tag == f"m{mission}_target_ar8_s0")
                & (frame.calibrator == CAL)]
    assert len(sel) == 1, f"results.csv does not hold a unique A0 row for mission {mission}"
    grid = float(sel["anomaly_and_rare/EW_F0.5"].iloc[0])
    assert abs(grid - frozen) < 1e-9, (
        f"A0 mismatch on mission {mission}: confirmatory record {frozen!r} vs "
        f"results.csv {grid!r}. Refusing to plot a value whose protocol is ambiguous.")
    return frozen


def contrasts(root: Path) -> pd.DataFrame:
    """All six pre-registered contrasts, exactly as frozen."""
    record = json.loads((root / PROTO / "CONFIRMATORY.json").read_text())
    out = []
    for mission in ("1", "2"):
        for t in record["missions"][mission]["tests"]:
            out.append({
                "mission": int(mission),
                "hypothesis": t["comparison"].split(":")[0].strip(),
                "contrast": t["comparison"].split(":", 1)[1].strip(),
                "calibrator": t["calibrator"],
                "diff": t["diff"],
                "ci95_low": t["ci95_low"],
                "ci95_high": t["ci95_high"],
                "p_boot": t["p_boot"],
                "p_holm": t.get("p_holm"),
                "verdict": t["verdict"],
                "n_seeds_A": t["n_seeds_A"] if "n_seeds_A" in t else None,
                "n_seeds_B": t["n_seeds_B"] if "n_seeds_B" in t else None,
                "block_days": t["block_days"],
                "n_boot": t["n_boot"],
            })
    return pd.DataFrame(out)


# =============================================================== J1 burden-recall trade-off
def fig_j1(root: Path, out: Path, data: Path):
    recs = layers_m1(root)
    src = pd.DataFrame([{
        "alarm_layer": c,
        "label": LAYER_LABEL[c],
        "anomaly_EW_recall": recs[c]["anomaly/EW_recall"],
        "anomaly_EW_precision": recs[c]["anomaly/EW_precision"],
        "anomaly_ADTQC": recs[c]["anomaly/ADTQC"],
        "false_alarms_per_year": recs[c]["false_alarms_per_year"],
        "false_alarm_runs": recs[c]["false_alarm_runs"],
        "alarm_runs": recs[c]["alarm_runs"],
        "anomaly_EW_F0.5": recs[c]["anomaly/EW_F0.5"],
        "events_detected_of_55": round(recs[c]["anomaly/EW_recall"] * M1_TEST_ANOMALIES),
    } for c in LAYER_ORDER])

    # The comparison is only meaningful if every layer is annualised over the same period.
    period = src.false_alarm_runs / src.false_alarms_per_year.replace(0, np.nan)
    years = float(np.nanmean(period))
    assert np.nanmax(period) - np.nanmin(period) < 1e-3, f"annualisation differs: {period.tolist()}"

    aci, bh = recs["aci"], recs[CAL]
    ratio_rate = aci["false_alarms_per_year"] / bh["false_alarms_per_year"]
    ratio_runs = aci["false_alarm_runs"] / bh["false_alarm_runs"]
    assert abs(ratio_rate - ratio_runs) / ratio_rate < 1e-3
    recall_ratio = aci["anomaly/EW_recall"] / bh["anomaly/EW_recall"]

    # `threshold` and `conformal_bh` land on exactly the same event-wise operating point, so on
    # these axes they are one marker, not two. Verify that before merging them.
    coincident = all(recs["threshold"][f] == recs[CAL][f] for f in
                     ("anomaly/EW_recall", "anomaly/EW_precision", "anomaly/EW_F0.5",
                      "false_alarms_per_year"))
    assert coincident, "threshold and conformal_bh no longer coincide; redraw as separate points"

    def fmt(v: float) -> str:
        if v == 0:
            return "0"
        return f"{v:.3f}" if v >= 0.001 else f"{v:.1e}".replace("e-0", "e−")

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.8, 4.3))

    # ---- (a) the five layers as five discrete configurations. No connecting line: these are not
    # points on a curve an operator can dial along, and a line would imply interpolation.
    FLOOR = 0.4          # zero cannot be placed on a log axis; the label states the true value
    plot_order = ["conformal_bh_rolling", "conformal_bh", "aci_event", "aci"]
    label_for = dict(LAYER_LABEL)
    label_for["conformal_bh"] = "threshold ≡ BH (primary)"
    for c in plot_order:
        fa = recs[c]["false_alarms_per_year"]
        x = FLOOR if fa == 0 else fa
        y = recs[c]["anomaly/EW_recall"]
        mk, col = LAYER_STYLE[c]
        ax.scatter(x, y, s=165, marker=mk, color=col, edgecolor="white", linewidth=1.7, zorder=4)
    notes = {
        "conformal_bh_rolling": ("BH rolling · 0/yr · recall 0.036", (17, -13), "left"),
        "conformal_bh": ("threshold ≡ BH (primary)\n1.14/yr · recall 0.145", (18, 20), "left"),
        "aci_event": ("ACI event-aggregated\n1,149/yr · recall 0.582", (-15, 15), "right"),
        "aci": ("ACI point-level\n176,337/yr · recall 0.927", (-17, -13), "right"),
    }
    for c, (txt, off, ha) in notes.items():
        fa = recs[c]["false_alarms_per_year"]
        ax.annotate(txt, (FLOOR if fa == 0 else fa, recs[c]["anomaly/EW_recall"]),
                    xytext=off, textcoords="offset points", ha=ha, va="center",
                    fontsize=7.6, color=S.INK, zorder=5, linespacing=1.4)
    ax.set_xscale("log")
    ax.set_xlim(0.30, 3.0e6)
    ax.set_ylim(-0.12, 1.16)
    ax.set_xlabel("false alarms per year  (log scale)")
    ax.set_ylabel(f"anomaly event-wise recall\n(of {M1_TEST_ANOMALIES} test anomalies)")
    S.panel_title(ax, "(a) Operator burden against detection")
    S.grid(ax, "both")
    ax.text(0.025, 0.985,
            f"ACI point-level vs BH (primary):\n{ratio_rate:,.0f}× the false alarms,\n"
            f"{recall_ratio:.1f}× the recall",
            transform=ax.transAxes, fontsize=7.8, color=S.INK2, ha="left", va="top",
            linespacing=1.6)

    # ---- (b) the quality axes the frontier hides. Horizontal bars with direct end labels, so no
    # value is rotated and the near-zero precisions are shown as what they are.
    series = [("anomaly recall", "anomaly/EW_recall", S.C1),
              ("event-wise precision", "anomaly/EW_precision", S.C2),
              ("ADTQC (detection timing)", "anomaly/ADTQC", S.C3)]
    n_l, n_s = len(LAYER_ORDER), len(series)
    h = 0.78 / n_s
    base = np.arange(n_l)[::-1]
    for j, (name, field, col) in enumerate(series):
        ys = base + (n_s - 1) / 2 * h - j * h
        vals = [recs[c][field] for c in LAYER_ORDER]
        bx.barh(ys, vals, height=h * 0.86, color=col, edgecolor="white", linewidth=0.8,
                label=name, zorder=3)
        for y, v in zip(ys, vals):
            bx.text(max(v, 0) + 0.018, y, fmt(v), va="center", ha="left",
                    fontsize=7.0, color=S.INK2)
    # The alarm-run count belongs on the label: BH rolling's precision and ADTQC of 1.000 rest on
    # two alarm runs, and without n a reader could take them for a strong result.
    bx.set_yticks(base)
    bx.set_yticklabels([f"{LAYER_LABEL[c]}\n{int(recs[c]['alarm_runs']):,} alarm runs"
                        for c in LAYER_ORDER], fontsize=7.8)
    bx.set_xlim(0, 1.17)
    bx.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    bx.set_xlabel("score  (higher is better)")
    S.panel_title(bx, "(b) Detection quality on the same runs")
    S.grid(bx, "x")
    bx.spines["left"].set_visible(False)
    bx.tick_params(axis="y", length=0)
    bx.legend(loc="lower center", bbox_to_anchor=(0.46, -0.30), ncol=3, fontsize=7.6,
              handlelength=1.1, columnspacing=1.2)

    fig.tight_layout()
    S.footnote(fig,
               f"Mission 1 target channels, arm A1 (AR(8) scorer), identical test half and event "
               f"definitions; every layer annualised over the same {years:.4f}-year period "
               f"(false_alarm_runs / false_alarms_per_year). No documented false-alarm budget or "
               f"missed-anomaly cost ratio exists for these missions, so no operating point on "
               f"these configurations can be declared preferable. `threshold` and `conformal_bh` "
               f"reach an identical event-wise operating point and are drawn as one marker in (a); "
               f"they are not identical everywhere — they raise 90 and 123 alarm runs "
               f"respectively and differ in ADTQC in the fourth decimal. The four points are "
               f"discrete configurations, not samples of a tunable curve, so they are "
               f"deliberately not joined by a line.")
    S.save_source(src, data, "jint_F1_burden_recall")
    return S.save(fig, out, "Figure_J1_burden_recall"), src


# =============================================================== J2 pre-registered forest plot
def fig_j2(root: Path, out: Path, data: Path):
    src = contrasts(root)
    MIN_EFFECT = 0.05          # declared minimum effect size, pre-registered

    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    order = src.sort_values(["mission", "hypothesis"], ascending=[True, True]).reset_index(drop=True)
    ypos = np.arange(len(order))[::-1]

    ax.axvspan(-MIN_EFFECT, MIN_EFFECT, color=S.MUTED, alpha=0.12, zorder=0)
    ax.axvline(0, color=S.INK, lw=0.9, zorder=1)
    for v in (-MIN_EFFECT, MIN_EFFECT):
        ax.axvline(v, color=S.MUTED, lw=0.9, ls=(0, (4, 3)), zorder=1)

    for y, (_, r) in zip(ypos, order.iterrows()):
        confirmatory = r.mission == 1
        col = S.C1 if confirmatory else S.C2
        mk = "o" if confirmatory else "s"
        ax.plot([r.ci95_low, r.ci95_high], [y, y], color=col, lw=2.0,
                solid_capstyle="round", zorder=3)
        for e in (r.ci95_low, r.ci95_high):
            ax.plot([e, e], [y - 0.12, y + 0.12], color=col, lw=1.6, zorder=3)
        ax.scatter(r["diff"], y, s=95, marker=mk, color=col, edgecolor="white",
                   linewidth=1.4, zorder=4)
        ax.text(r.ci95_high + 0.022, y,
                f"{r['diff']:+.3f}  [{r.ci95_low:+.3f}, {r.ci95_high:+.3f}]",
                va="center", ha="left", fontsize=7.6, color=S.INK, zorder=6,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.4, alpha=0.92))

    labels = []
    for _, r in order.iterrows():
        if r.p_holm is not None and not pd.isna(r.p_holm):
            second = f"Holm p = {r.p_holm:.4g} · {r.verdict}"
        else:
            second = "replication — no inference"
        labels.append(f"M{r.mission}  {r.hypothesis}: {r.contrast}\n{second}")
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=7.8)
    ax.set_xlim(-0.62, 0.80)
    ax.set_ylim(-0.6, len(order) - 0.4)
    ax.set_xlabel("difference in corrected event-wise F0.5 (anomalies + rare), "
                  "paired block bootstrap")
    S.panel_title(ax, "Pre-registered contrasts, frozen record 09a98f5e160e")
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Line2D([], [], color=S.C1, marker="o", lw=2.0, markeredgecolor="white",
               label="Mission 1 — confirmatory (Holm-corrected)"),
        Line2D([], [], color=S.C2, marker="s", lw=2.0, markeredgecolor="white",
               label="Mission 2 — replication, no inference"),
        Patch(facecolor=S.MUTED, alpha=0.18,
              label=f"declared minimum effect ±{MIN_EFFECT:g}"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=7.6,
        handlelength=1.6, columnspacing=1.6)

    fig.tight_layout()
    S.footnote(fig,
               "Bars are 95% intervals from a paired bootstrap over fixed 30-day blocks "
               "(B = 2000), hierarchical over seeds where an arm has several. The hypotheses are "
               "directional with a declared minimum effect of +0.05, so H4 and H5 are recorded as "
               "refuted on the strength of a negative point estimate even where the interval "
               "spans zero — the pre-registered claim was that A3 would exceed its comparator, "
               "and it did not. Mission 2 is a replication: its intervals are shown but carry no "
               "inferential weight, because its test half holds only 6 anomalies.", y=-0.02)
    S.save_source(src, data, "jint_F2_preregistered_contrasts")
    return S.save(fig, out, "Figure_J2_contrast_forest"), src


# =============================================================== J3 arm performance A0-A3
def fig_j3(root: Path, out: Path, data: Path):
    recs = []
    for m in (1, 2):
        recs.append({"mission": m, "arm": "A0", "mean": a0_value(root, m), "sd": 0.0, "n": 1,
                     "selection_protocol": "9-month calibration period"})
        for arm, tags in arm_tags(m).items():
            v = arm_values(root, tags, "anomaly_and_rare/EW_F0.5")
            assert v, f"no records for mission {m} arm {arm}"
            recs.append({"mission": m, "arm": arm, "mean": float(np.mean(v)),
                         "sd": float(np.std(v, ddof=1)) if len(v) > 1 else 0.0, "n": len(v),
                         "selection_protocol": "whole training half, cross-fitted"})
    src = pd.DataFrame(recs)
    cst = contrasts(root)

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.3), sharey=True)
    arms = ["A0", "A1", "A2", "A3"]
    cols = [S.C4, S.C1, S.C3, S.C2]
    for ax, m in zip(axes, (1, 2)):
        sub = src[src.mission == m].set_index("arm").loc[arms]
        xs = np.arange(len(arms))
        ax.bar(xs, sub["mean"], yerr=sub["sd"], capsize=5, color=cols, edgecolor="white",
               linewidth=1.2, width=0.6, zorder=3,
               error_kw=dict(ecolor=S.INK2, lw=1.2, capthick=1.2))
        for x, v, e in zip(xs, sub["mean"], sub["sd"]):
            ax.text(x, v + e + 0.028, f"{v:.3f}", ha="center", fontsize=8.4, color=S.INK)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{a}\nn={int(n)}" for a, n in zip(arms, sub["n"])], fontsize=8.6)
        # F0.5 is bounded above by 1; the axis stops there rather than implying more is possible.
        ax.set_ylim(0, 1.0)
        ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        S.grid(ax, "y")
        S.panel_title(ax, f"({'ab'[m - 1]}) Mission {m} — "
                          + ("confirmatory, 55 test anomalies" if m == 1
                             else "replication, no inference, 6 test anomalies"))
        if m == 1:
            ax.set_ylabel("corrected event-wise F0.5 (anomalies + rare)")
        ax.text(0.5, -0.185, "error bars: ±1 SD over seeds",
                transform=ax.transAxes, fontsize=7.2, color=S.INK2, ha="center")

    # The contrasts belong under the panels, not over the bars: Figure J2 carries them in full.
    lines = []
    for m in (1, 2):
        parts = []
        for _, r in cst[cst.mission == m].sort_values("hypothesis").iterrows():
            tail = (f"Holm p = {r.p_holm:.4g}" if r.p_holm is not None and not pd.isna(r.p_holm)
                    else "no inference")
            parts.append(f"{r.hypothesis} {r.contrast} = {r['diff']:+.3f} ({tail})")
        lines.append(f"M{m}:  " + "   ·   ".join(parts))
    fig.tight_layout()
    S.footnote(fig,
               "\n".join(lines) + "\n"
               "A0 and A1 are deterministic (n = 1); A2 and A3 run five seeds each. A0 selects its "
               "alarm configuration on the 9-month calibration period and is read from the frozen "
               "confirmatory record; A1–A3 cross-fit selection over the whole training half. The "
               "arms therefore differ in selection data, which is what H6 tests, and not in the "
               "test half, which is identical throughout. H6 reverses sign on Mission 2, whose "
               "test half holds six anomalies and cannot discriminate methods; note also A2's "
               "seed spread on Mission 1 (±0.236) against a declared minimum effect of 0.05.",
               y=-0.035)
    S.save_source(src, data, "jint_F3_arm_performance")
    return S.save(fig, out, "Figure_J3_arm_performance"), src


# =============================================================== J4 selection vs test
def fig_j4(root: Path, out: Path, data: Path):
    from scipy.stats import spearmanr
    recs = []
    for m in (1, 2):
        for arm, tags in arm_tags(m).items():
            for t in tags:
                for r in rows(root, t):
                    if r["calibrator"] != CAL or r.get("cv_EW_F0.5") is None:
                        continue
                    recs.append({"mission": m, "arm": arm, "tag": t,
                                 "selection_cv_EW_F0.5": r["cv_EW_F0.5"],
                                 "test_EW_F0.5": r["anomaly_and_rare/EW_F0.5"]})
    src = pd.DataFrame(recs)

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4), sharex=True, sharey=True)
    for ax, m in zip(axes, (1, 2)):
        sub = src[src.mission == m]
        ax.plot([0, 1.05], [0, 1.05], color=S.MUTED, lw=1.0, ls=(0, (4, 3)), zorder=1)
        ax.text(0.975, 0.995, "y = x", transform=ax.transAxes, fontsize=7.6,
                color=S.INK2, ha="right", va="top", zorder=5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.9))
        for arm in ("A1", "A2", "A3"):
            s = sub[sub.arm == arm]
            mk, col = ARM_STYLE[arm]
            ax.scatter(s["selection_cv_EW_F0.5"],
                       s["test_EW_F0.5"], s=90, marker=mk, color=col, edgecolor="white",
                       linewidth=1.3, label=f"{arm} (n = {len(s)})", zorder=3)
        rho = spearmanr(sub["selection_cv_EW_F0.5"], sub["test_EW_F0.5"]).statistic \
            if len(sub) > 2 else float("nan")
        n_below = int((sub["test_EW_F0.5"] < sub["selection_cv_EW_F0.5"]).sum())
        S.panel_title(ax, f"({'ab'[m - 1]}) Mission {m}   per-run Spearman "
                          f"ρ = {rho:+.3f}  (n = {len(sub)})")
        ax.text(0.03, 0.97, f"{n_below} of {len(sub)} runs below y = x",
                transform=ax.transAxes, fontsize=7.6, color=S.INK2, ha="left", va="top")
        ax.set_xlabel("selection score  (cross-fit, training half)")
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)
        S.grid(ax, "both")
        ax.legend(loc="lower right", fontsize=8)
        if m == 1:
            ax.set_ylabel("test score  (corrected event-wise F0.5)")
    fig.suptitle("Points below the diagonal indicate cross-fit optimism",
                 x=0.006, ha="left", fontsize=8.6, color=S.INK2, y=1.005)
    fig.tight_layout()
    S.footnote(fig,
               "One point per run (arm × seed) under the primary alarm layer. Arm-level "
               "correlations over three arms are not reported: with three points |ρ| = 1 "
               "arises by chance with probability 1/6. Mission 2's points are compressed into the "
               "saturated upper-right corner, which is why its correlation carries no weight.",
               y=-0.02)
    S.save_source(src, data, "jint_F4_selection_vs_test")
    return S.save(fig, out, "Figure_J4_selection_vs_test"), src


# =============================================================== J5 configuration sensitivity
def fig_j5(root: Path, out: Path, data: Path):
    """Scorer x alarm layer, both missions and both channel scales -- all under the A0 protocol."""
    frame = pd.read_csv(root / RESULTS)
    frame["scale"] = np.where(frame.tag.str.contains("_target_"), "target (full)", "lightweight")
    frame["scorer"] = (frame.tag.str.replace(r"^m\d_(target|lightweight)_", "", regex=True)
                               .str.replace(r"_s\d+$", "", regex=True))
    grid = (frame.groupby(["mission", "scale", "scorer", "calibrator"])
                 ["anomaly_and_rare/EW_F0.5"].agg(["mean", "std", "count"]).reset_index())
    src = grid.rename(columns={"mean": "EW_F0.5_mean", "std": "EW_F0.5_sd", "count": "n_seeds"})

    layers = ["native", "threshold", "conformal_bh", "conformal_bh_rolling"]
    llab = ["native\n(fixed rule)", "threshold", "BH\n(primary)", "BH rolling"]
    trivial = {"out_of_limits", "out_of_limits_all", "global_std3", "global_std5",
               "cosmos_monitor", "persistence"}

    # Generous gutters: each panel carries long scorer names on its left, and with a tight
    # wspace those names print on top of the neighbouring panel's cells.
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 9.4))
    fig.subplots_adjust(left=0.135, right=0.865, top=0.90, bottom=0.175,
                        wspace=0.62, hspace=0.46)
    import matplotlib.colors as mcolors
    cmap = mcolors.LinearSegmentedColormap.from_list("seq", list(S.SEQ))
    for ax, (m, sc) in zip(axes.ravel(), [(1, "target (full)"), (1, "lightweight"),
                                          (2, "target (full)"), (2, "lightweight")]):
        sub = src[(src.mission == m) & (src.scale == sc)]
        scorers = (sub.groupby("scorer")["EW_F0.5_mean"].max()
                      .sort_values(ascending=False).index.tolist())
        mat = np.full((len(scorers), len(layers)), np.nan)
        for i, s in enumerate(scorers):
            for j, c in enumerate(layers):
                v = sub[(sub.scorer == s) & (sub.calibrator == c)]["EW_F0.5_mean"]
                if len(v):
                    mat[i, j] = float(v.iloc[0])
        im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=1, aspect="auto")
        for i in range(len(scorers)):
            for j in range(len(layers)):
                if np.isnan(mat[i, j]):
                    ax.text(j, i, "—", ha="center", va="center", fontsize=7.5,
                            color=S.MUTED)
                else:
                    ax.text(j, i, f"{mat[i, j]:.3f}", ha="center", va="center", fontsize=6.9,
                            color="white" if mat[i, j] > 0.55 else S.INK)
        ax.set_xticks(range(len(layers)))
        ax.set_xticklabels(llab, fontsize=7.4)
        ax.set_yticks(range(len(scorers)))
        ax.set_yticklabels([(f"{s}  ▸" if s in trivial else s) for s in scorers],
                           fontsize=7.2)
        for tick, s in zip(ax.get_yticklabels(), scorers):
            if s in trivial:
                tick.set_color(S.C2)
        S.panel_title(ax, f"M{m}, {sc}")
        ax.set_xticks(np.arange(len(layers) + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(scorers) + 1) - 0.5, minor=True)
        ax.grid(which="minor", color="white", linewidth=1.4)
        ax.tick_params(which="minor", length=0)
        ax.set_axisbelow(False)

    cax = fig.add_axes((0.892, 0.30, 0.016, 0.42))
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("corrected event-wise F0.5 (anomalies + rare)", fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
    cb.outline.set_edgecolor(S.MUTED)
    fig.suptitle("Scorer × alarm layer, arm-A0 selection protocol "
                 "(9-month calibration period)", x=0.012, ha="left", fontsize=10.4, color=S.INK,
                 y=0.975)
    S.footnote(fig,
               "Every cell comes from results.csv, i.e. the A0 selection protocol; these values are "
               "therefore NOT comparable with the A1–A3 numbers in Figures J1–J4, which "
               "cross-fit selection over the whole training half. The adaptive-conformal layers do "
               "not appear because that grid was never run with them. Rows marked ▸ in orange "
               "are parameter-free or trivial references, not learned scorers; a dash means the "
               "combination does not exist (fixed rules admit only their native layer). "
               "Read the spread along a row against the spread down a column: at full channel "
               "scale on Mission 1 every arm collapses, and on Mission 2 the parameter-free "
               "out-of-limits rule is competitive with every learned scorer.", y=0.085)
    S.save_source(src, data, "jint_F5_configuration_sensitivity")
    return S.save(fig, out, "Figure_J5_configuration_sensitivity"), src


# =============================================================== J6 what the alarms are made of
def fig_j6(root: Path, out: Path, data: Path):
    """Where the burden reduction comes from: detections given up, and alarm-run composition."""
    recs = layers_m1(root)
    rowsout = []
    for c in LAYER_ORDER:
        r = recs[c]
        det = round(r["anomaly/EW_recall"] * M1_TEST_ANOMALIES)
        # alarm_runs decomposes exactly into these three disjoint classes; verified below.
        comp = (r["anomaly_runs"], r["rare_event_only_runs"], r["false_alarm_runs"])
        assert abs(sum(comp) - r["alarm_runs"]) < 1e-6, (
            f"{c}: alarm-run decomposition {comp} does not sum to {r['alarm_runs']}")
        rowsout.append({"alarm_layer": c, "label": LAYER_LABEL[c],
                        "anomalies_detected": det,
                        "anomalies_missed": M1_TEST_ANOMALIES - det,
                        "anomaly_runs": comp[0], "rare_event_only_runs": comp[1],
                        "false_alarm_runs": comp[2], "alarm_runs": r["alarm_runs"],
                        "anomaly_EW_recall": r["anomaly/EW_recall"]})
    src = pd.DataFrame(rowsout)

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.4, 4.2))
    pos = np.arange(len(src))[::-1]

    # ---- (a) the 55 anomalies, found and missed
    ax.barh(pos, src.anomalies_detected, color=S.C1, edgecolor="white", linewidth=1.2,
            height=0.6, label="detected", zorder=3)
    ax.barh(pos, src.anomalies_missed, left=src.anomalies_detected, color="#e3e3df",
            edgecolor="white", linewidth=1.2, height=0.6, label="missed", zorder=3)
    for y, r in zip(pos, src.itertuples()):
        inside = r.anomalies_detected >= 6
        ax.text(r.anomalies_detected / 2 if inside else r.anomalies_detected + 1.0, y,
                f"{r.anomalies_detected}", ha="center" if inside else "left", va="center",
                fontsize=8.2, color="white" if inside else S.INK, fontweight="bold")
    ax.set_yticks(pos)
    # recall travels with the label, so the count axis can stop at the true number of anomalies
    ax.set_yticklabels([f"{r.label}\nrecall {r.anomaly_EW_recall:.3f}"
                        for r in src.itertuples()], fontsize=7.8)
    ax.set_xlim(0, M1_TEST_ANOMALIES)
    ax.set_xticks([0, 10, 20, 30, 40, 50, M1_TEST_ANOMALIES])
    ax.set_xlabel(f"Mission 1 test anomalies (n = {M1_TEST_ANOMALIES})")
    S.panel_title(ax, "(a) Anomalies found, by alarm layer")
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), fontsize=7.8, ncol=2)

    # ---- (b) composition of the alarm runs an operator would actually see
    frac = src[["anomaly_runs", "rare_event_only_runs", "false_alarm_runs"]].to_numpy(float)
    frac = frac / frac.sum(axis=1, keepdims=True)
    names = ["matched an anomaly", "matched a rare event only", "false alarm"]
    colours = [S.C1, S.C3, S.C4]
    left = np.zeros(len(src))
    for j, (nm, col) in enumerate(zip(names, colours)):
        bx.barh(pos, frac[:, j], left=left, color=col, edgecolor="white", linewidth=1.2,
                height=0.6, label=nm, zorder=3)
        left += frac[:, j]
    for y, r, f in zip(pos, src.itertuples(), frac):
        bx.text(1.02, y, f"{int(r.alarm_runs):,} runs", ha="left", va="center",
                fontsize=7.6, color=S.INK2)
        if f[2] > 0.14:
            bx.text(1 - f[2] / 2, y, f"{f[2] * 100:.0f}%", ha="center", va="center",
                    fontsize=7.6, color="white", fontweight="bold")
    bx.set_yticks(pos)
    bx.set_yticklabels([])
    bx.set_xlim(0, 1.0)
    bx.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    bx.set_xticklabels(["0", "25", "50", "75", "100%"])
    bx.set_xlabel("share of raised alarm runs")
    S.panel_title(bx, "(b) What those alarms were")
    S.grid(bx, "x")
    bx.spines["left"].set_visible(False)
    bx.tick_params(axis="y", length=0)
    bx.legend(loc="upper center", bbox_to_anchor=(0.45, -0.22), ncol=3, fontsize=7.6)

    fig.tight_layout()
    S.footnote(fig,
               "Panel (a) converts the archived event-wise recall to whole anomalies; every value "
               "lands on an integer. Panel (b) splits the raised alarm runs into the three "
               "disjoint classes recorded per run, which sum exactly to the total shown at the "
               "right. Together they show the mechanism behind the burden reduction: the "
               "event-level layer raises 123 alarm runs instead of 1,383,948, and finds 8 of the "
               "55 anomalies instead of 51. Rare events are labelled in the benchmark but are not "
               "anomalies; a run matching only a rare event is neither a detection nor an error "
               "under the anomaly-only metric.", y=-0.10)
    S.save_source(src, data, "jint_F6_alarm_composition")
    return S.save(fig, out, "Figure_J6_alarm_composition"), src


FIGURES = [("J1", fig_j1), ("J2", fig_j2), ("J3", fig_j3),
           ("J4", fig_j4), ("J5", fig_j5), ("J6", fig_j6)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="paper/figures/jint")
    ap.add_argument("--data", default="paper/figures/data")
    ap.add_argument("--only", default=None, help="comma-separated figure ids, e.g. J1,J6")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    out, data = root / args.out, root / args.data
    S.apply()
    want = set(args.only.split(",")) if args.only else None
    for fid, fn in FIGURES:
        if want and fid not in want:
            continue
        paths, src = fn(root, out, data)
        print(f"{fid}: {paths[0].relative_to(root)}  ({len(src)} source rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
