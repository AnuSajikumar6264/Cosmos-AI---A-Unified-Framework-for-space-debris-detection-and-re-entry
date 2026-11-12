"""Dataset characterisation figures, generated from the on-disk validation report and the data.

    python scripts/figures/fig_datasets.py

Sources
-------
``data/DATASET_REPORT.json``  -- written by ``python -m cosmos.ai.data.validate`` from the files
actually present on disk, so a dataset that was never downloaded shows up as such rather than being
silently described from its publication.

``outputs/twin/as_of_2026-10-27/forecast_table.csv.gz`` -- the catalogue feature table the
re-entry and lifetime modules consume, 31,396 objects.

Two rules are enforced throughout. First, a dataset named in the project is not assumed to be
available: availability is read from the report, and the unavailable ones are drawn, not omitted.
Second, no figure correlates features across incompatible corpora -- the only correlation matrix
here is within one table of one population.
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
import figstyle as S  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REPORT = "data/DATASET_REPORT.json"
TWIN = "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"

# Which corpora actually feed a reported experiment. Each entry names the output directory that
# demonstrates the use, so the claim is checkable rather than asserted.
USED_IN = {
    "esa_adb": "outputs/benchmarks/telemetry_esa_adb",
    "opssat_ad": "outputs/benchmarks/telemetry_opssat",
    "smap_msl": "outputs/benchmarks/telemetry_smap_msl",
    "spotgeo": "outputs/benchmarks/vision_spotgeo",
    "kelvins_cac": "outputs/benchmarks/conjunction_kelvins_cac",
    "celestrak": "outputs/benchmarks/reentry_lifetime, reentry_landmark, outputs/twin",
    "gcat": "outputs/benchmarks/reentry_lifetime (launch families, object class)",
    "reentry_historical": "descriptive only (235 recovered fragments; no model scored on it)",
    "cosmos_synthetic_vision": "outputs/benchmarks/vision_cosmos_synthetic "
                               "(results archived; images not on disk)",
    "cosmos_synthetic_telemetry": "outputs/benchmarks/telemetry_cosmos_synthetic",
    "kelvins_debris_origin": "none — referenced only by cosmos/ai/data/download.py",
    "spark": "none — access-gated",
    "spacesense_bench": "none — different task, non-commercial licence",
    "reentry_simulated": "none — incomplete on disk",
}


# =============================================================== D1 inventory and availability
def fig_d1(root: Path, out: Path, data: Path):
    rep = json.loads((root / REPORT).read_text())
    rows = []
    for name, meta in rep["datasets"].items():
        rows.append({
            "dataset": name,
            "folder": meta["folder"],
            "data_class": meta["class"],
            "status_on_disk": meta["status"],
            "size_on_disk_mb": meta["size_on_disk_mb"],
            "licence": meta.get("licence"),
            "used_in": USED_IN.get(name, "unclassified"),
            "feeds_a_reported_experiment": not USED_IN.get(name, "none").startswith("none"),
            "reason_if_unavailable": meta.get("reason_if_unavailable"),
        })
    src = pd.DataFrame(rows).sort_values("size_on_disk_mb", ascending=True).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(9.8, 6.8))
    y = np.arange(len(src))
    FLOOR = 0.04                     # 0 MB cannot sit on a log axis; labelled explicitly
    widths = src.size_on_disk_mb.where(src.size_on_disk_mb > 0, FLOOR)

    def colour(r):
        if not r.feeds_a_reported_experiment:
            return "#d9d9d4"
        return S.C1 if r.data_class.startswith("REAL") else S.C3

    cols = [colour(r) for r in src.itertuples()]
    ax.barh(y, widths, color=cols, edgecolor="white", linewidth=1.0, height=0.68, zorder=3)
    def size_text(mb: float) -> str:
        if mb == 0:
            return "nothing on disk"
        if mb >= 1000:
            return f"{mb / 1000:.1f} GB"
        if mb >= 10:
            return f"{mb:.0f} MB"
        return f"{mb:.1f} MB"

    for yi, r, w in zip(y, src.itertuples(), widths):
        ax.text(w * 1.25, yi, size_text(r.size_on_disk_mb), va="center", ha="left",
                fontsize=7.4, color=S.INK2)
    ax.set_yticks(y)
    # The status matters as much as the size: "incomplete" and "not downloaded" are different
    # failures, and a corpus can have archived results while its data is gone.
    ax.set_yticklabels([f"{r.dataset}\n[{r.status_on_disk}"
                        + ("" if r.feeds_a_reported_experiment else "; unused")
                        + "]" for r in src.itertuples()], fontsize=7.6)
    for tick, r in zip(ax.get_yticklabels(), src.itertuples()):
        if not r.feeds_a_reported_experiment:
            tick.set_color(S.INK2)
    ax.set_xscale("log")
    ax.set_xlim(FLOOR * 0.6, 4.0e4)
    ax.set_xlabel("size on disk, megabytes  (log scale)")
    S.panel_title(ax, "Data corpora named by COSMOS-AI: what is actually present, and what is used")
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[
        Patch(facecolor=S.C1, edgecolor="white", label="real observations, feeds an experiment"),
        Patch(facecolor=S.C3, edgecolor="white",
              label="synthetic, feeds an experiment (results archived)"),
        Patch(facecolor="#d9d9d4", edgecolor="white",
              label="present or named, feeds no reported experiment"),
    ], loc="lower right", fontsize=7.6)

    fig.tight_layout()
    S.footnote(fig,
               "Sizes are measured from the files on disk by cosmos.ai.data.validate, not taken "
               "from the datasets' publications; four corpora the project names are absent or "
               "unused and are drawn here rather than omitted. SPARK is distributed on request "
               "and no request was made; Space-Track and ESA DISCOSweb require accounts and the "
               "re-entry API answers HTTP 401; SpaceSense addresses resolved-spacecraft pose, a "
               "different task, under a non-commercial licence; the synthetic vision images are "
               "no longer on disk although their results are archived. Per-dataset licences and "
               "reasons are in paper/figures/data/datasets_inventory.csv.", y=-0.015)
    S.save_source(src, data, "datasets_inventory")
    return S.save(fig, out, "Figure_D1_dataset_inventory"), src


# =============================================================== D2 ESA-ADB protocol structure
def fig_d2(root: Path, out: Path, data: Path):
    rep = json.loads((root / REPORT).read_text())["esa_adb"]
    periods = ["fit", "es", "cal", "test"]
    pretty = {"fit": "fit", "es": "early stop", "cal": "calibration", "test": "TEST"}
    kinds = ["Anomaly", "Rare Event", "Communication Gap"]
    rows = []
    for m in (1, 2):
        blk = rep[f"mission{m}"]
        for p in periods:
            ev = blk["events_target_channels_by_period"].get(p, {})
            rows.append({"mission": m, "period": p, "events_total": ev.get("events", 0),
                         **{k: ev.get(k, 0) for k in kinds}})
    src = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    cols = {"Anomaly": S.C4, "Rare Event": S.C3, "Communication Gap": S.C5}
    for ax, m in zip(axes, (1, 2)):
        blk = rep[f"mission{m}"]
        sub = src[src.mission == m].set_index("period").loc[periods]
        x = np.arange(len(periods))
        bottom = np.zeros(len(periods))
        for k in kinds:
            v = sub[k].to_numpy(float)
            ax.bar(x, v, bottom=bottom, color=cols[k], edgecolor="white", linewidth=1.1,
                   width=0.62, label=k, zorder=3)
            bottom += v
        for xi, (p, tot) in enumerate(zip(periods, sub.events_total)):
            ax.text(xi, tot + max(sub.events_total) * 0.03, f"{int(tot)}",
                    ha="center", fontsize=8.2, color=S.INK)
        # the number that governs what Mission 2 can and cannot show
        n_anom_test = int(sub.loc["test", "Anomaly"])
        # On Mission 2 the anomaly segment is only six events tall, so the label needs a leader
        # line out of the bar rather than a horizontal offset at the same height.
        offset = (-52, 0) if m == 1 else (-58, 42)
        ax.annotate(f"{n_anom_test} anomalies", (3, max(sub.loc["test", "Anomaly"] / 2, 1)),
                    xytext=offset, textcoords="offset points", fontsize=8.0,
                    color=S.C4, ha="right", va="center", fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=S.C4, lw=1.0,
                                    connectionstyle="arc3,rad=0.0"))
        ax.set_xticks(x)
        ax.set_xticklabels([pretty[p] for p in periods], fontsize=8.4)
        ax.set_ylim(0, max(sub.events_total) * 1.30)
        S.grid(ax, "y")
        S.panel_title(ax, f"({'ab'[m - 1]}) Mission {m} — {blk['grid_seconds']} s grid, "
                          f"{blk['target_channels']} of {blk['channels']} channels targeted")
        ax.set_ylabel("labelled events on target channels" if m == 1 else "")
        ax.text(0.03, 0.97,
                f"train {blk['train']['n']:,} rows\n"
                f"{blk['train']['start'][:10]} → {blk['train']['end'][:10]}\n"
                f"test  {blk['test']['n']:,} rows\n"
                f"{blk['test']['start'][:10]} → {blk['test']['end'][:10]}",
                transform=ax.transAxes, fontsize=7.4, color=S.INK2, ha="left", va="top",
                linespacing=1.6, family="DejaVu Sans")
        if m == 1:
            ax.legend(loc="upper right", fontsize=7.6)
    fig.tight_layout()
    S.footnote(fig,
               "fit, early stop and calibration all lie inside the official training half; TEST "
               "is the official held-out half. The event counts are what the pre-registered study "
               "could resolve: Mission 1's test half carries 55 anomalies, Mission 2's carries "
               "six, and almost all of Mission 2's labels are rare events rather than anomalies. "
               "That is why Mission 2 is reported as a replication without inference and not as a "
               "cross-mission generalisation test. Both missions are single spacecraft, so no "
               "figure in this project can speak to generalisation across spacecraft.", y=-0.015)
    S.save_source(src, data, "esa_adb_event_structure")
    return S.save(fig, out, "Figure_D2_esa_adb_structure"), src


# =============================================================== D3 label scarcity
def fig_d3(root: Path, out: Path, data: Path):
    """How many positive events each benchmark actually offers. The power ceiling, in one view."""
    rep = json.loads((root / REPORT).read_text())
    kelvins = json.loads(
        (root / "outputs/benchmarks/conjunction_kelvins_cac/summary.json").read_text())
    life = pd.read_csv(root / "outputs/benchmarks/reentry_lifetime/"
                              "origin2016_uncontrolled/regression_test.csv")
    landmark = rep["catalogue_and_reentry"]["landmark"]
    opssat = rep["opssat_ad"]["class_counts"]
    spot = rep["spotgeo"]["test"]

    rows = [
        {"benchmark": "ESA-ADB M1 — anomalies\n(test half)", "units": "labelled events",
         "n_eval": 91, "positives": 55,
         "source": "DATASET_REPORT.json esa_adb.mission1.events_target_channels_by_period.test"},
        {"benchmark": "ESA-ADB M2 — anomalies\n(test half)", "units": "labelled events",
         "n_eval": 362, "positives": 6,
         "source": "DATASET_REPORT.json esa_adb.mission2.events_target_channels_by_period.test"},
        {"benchmark": "re-entry landmark\n(68-day follow-up)", "units": "objects at risk",
         "n_eval": landmark["events_by_split"]["test"]["n"],
         "positives": landmark["events_by_split"]["test"]["events"],
         "source": "DATASET_REPORT.json catalogue_and_reentry.landmark.events_by_split.test"},
        {"benchmark": "conjunction — Kelvins CAC\n(high-risk)", "units": "conjunction events",
         "n_eval": kelvins["data"]["test_events"],
         "positives": kelvins["data"]["test_high_risk"],
         "source": "conjunction_kelvins_cac/summary.json data.test_high_risk"},
        {"benchmark": "OPS-SAT-AD\n(official test split)", "units": "fragments",
         "n_eval": opssat["train=0,anomaly=0"] + opssat["train=0,anomaly=1"],
         "positives": opssat["train=0,anomaly=1"],
         "source": "DATASET_REPORT.json opssat_ad.class_counts"},
        {"benchmark": "orbital lifetime\n(origin 2016)", "units": "scored objects",
         "n_eval": int(life.n.iloc[0]),
         "positives": int(life.n_decayed.iloc[0]),
         "source": "reentry_lifetime/origin2016_uncontrolled/regression_test.csv n, n_decayed"},
        # Counted as frames, not annotated objects: every annotated object is by definition a
        # target, so an object-level "positive rate" would be 100% and carry no information.
        {"benchmark": "debris — SpotGEO\n(official test split)", "units": "frames",
         "n_eval": spot["frames_on_disk"],
         "positives": spot["frames_on_disk"] - spot["frames_without_objects"],
         "source": "DATASET_REPORT.json spotgeo.test.frames_on_disk "
                   "minus spotgeo.test.frames_without_objects"},
    ]
    src = pd.DataFrame(rows)
    src["positive_rate"] = src.positives / src.n_eval

    fig, ax = plt.subplots(figsize=(9.8, 5.4))
    order = src.sort_values("positives").reset_index(drop=True)
    y = np.arange(len(order))
    ax.barh(y, order.n_eval, color="#e6e6e1", edgecolor="white", linewidth=1.0,
            height=0.66, label="evaluation units", zorder=2)
    ax.barh(y, order.positives, color=[S.C4 if p < 60 else S.C1 for p in order.positives],
            edgecolor="white", linewidth=1.0, height=0.66, label="positive events", zorder=3)
    for yi, r in zip(y, order.itertuples()):
        ax.text(r.n_eval * 1.3, yi, f"{r.positives:,} of {r.n_eval:,}   "
                                   f"({r.positive_rate * 100:.1f}%)",
                va="center", ha="left", fontsize=7.6, color=S.INK2)
    ax.axvline(60, color=S.C4, lw=1.1, ls=(0, (4, 3)), zorder=4)
    ax.annotate("60 positives", xy=(60, -0.62), xytext=(60, -1.08),
                textcoords="data", color=S.C4, fontsize=7.4, ha="center", va="top",
                annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color=S.C4, lw=0.9))
    ax.set_yticks(y)
    # the unit travels with the row, because the rows do not share one
    ax.set_yticklabels([f"{r.benchmark}\n[{r.units}]" for r in order.itertuples()], fontsize=7.6)
    ax.set_xscale("log")
    ax.set_xlim(2, 4.0e6)
    ax.set_ylim(-0.75, len(order) - 0.25)
    ax.set_xlabel("count  (log scale)")
    S.panel_title(ax, "Positive events available for evaluation, by benchmark")
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower right", fontsize=7.8)

    fig.tight_layout()
    S.footnote(fig,
               "Each benchmark's positive count is the ceiling on what any method evaluated on it "
               "can demonstrate, and it is the single most important limitation of this project's "
               "results. Three of the seven settings offer fewer than 60 positives; Mission 2 "
               "offers six, and the re-entry landmark 38. The unit of evaluation differs by row "
               "and is printed in brackets under each row label, so the bars are per-benchmark "
               "magnitudes and must not be compared with one another as though they measured the "
               "same thing. Two definitions need stating: orbital lifetime counts objects whose "
               "five-year outcome is known, and its 'positives' are those observed to decay — the "
               "remainder are right-censored, not negative; SpotGEO is counted in frames holding "
               "at least one target, because every annotated object is a target and an "
               "object-level rate would be 100% by construction. Row-level sources are in "
               "paper/figures/data/benchmark_label_scarcity.csv.", y=-0.015)
    S.save_source(src, data, "benchmark_label_scarcity")
    return S.save(fig, out, "Figure_D3_label_scarcity"), src


# =============================================================== D4 catalogue features
def fig_d4(root: Path, out: Path, data: Path):
    """Feature availability and distributions in the one table the twin actually consumes."""
    frame = pd.read_csv(root / TWIN, low_memory=False)
    feats = ["perigee", "apogee", "inc", "mass", "rcs_m2", "f107_last81", "ap_last81",
             "ops_status", "type1", "launch_family", "breakup_family"]
    miss = pd.DataFrame({
        "feature": feats,
        "n_objects": len(frame),
        "n_present": [int(frame[f].notna().sum()) for f in feats],
    })
    miss["fraction_missing"] = 1 - miss.n_present / miss.n_objects

    fig = plt.figure(figsize=(10.6, 7.4))
    gs = fig.add_gridspec(2, 3, hspace=0.46, wspace=0.30,
                          left=0.075, right=0.985, top=0.920, bottom=0.175)

    # ---- (a) missingness per feature
    ax = fig.add_subplot(gs[0, :2])
    order = miss.sort_values("fraction_missing", ascending=False).reset_index(drop=True)
    y = np.arange(len(order))
    ax.barh(y, order.fraction_missing * 100,
            color=[S.C4 if v > 0.25 else S.C1 for v in order.fraction_missing],
            edgecolor="white", linewidth=1.0, height=0.66, zorder=3)
    for yi, r in zip(y, order.itertuples()):
        ax.text(r.fraction_missing * 100 + 1.2, yi,
                f"{r.fraction_missing * 100:.1f}%  ({r.n_present:,} present)",
                va="center", ha="left", fontsize=7.2, color=S.INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(order.feature, fontsize=7.8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("missing (% of 31,396 catalogued objects)")
    S.panel_title(ax, "(a) Feature availability in the catalogue table")
    S.grid(ax, "x")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    # ---- (b) where area-to-mass comes from
    bx = fig.add_subplot(gs[0, 2])
    am = frame.am_source.fillna("missing").value_counts()
    # One colour: this project's own subgroup analysis finds the design-derived objects are the
    # worse-covered group, so colouring "design" as the favourable case would mislead.
    bx.bar(np.arange(len(am)), am.values, color=S.C1,
           edgecolor="white", linewidth=1.1, width=0.62, zorder=3)
    for i, v in enumerate(am.values):
        bx.text(i, v + am.values.max() * 0.025, f"{v:,}", ha="center", fontsize=7.4,
                color=S.INK)
    bx.set_xticks(np.arange(len(am)))
    bx.set_xticklabels(am.index, rotation=22, ha="right", fontsize=7.4)
    bx.set_ylim(0, am.values.max() * 1.18)
    bx.set_ylabel("objects")
    S.panel_title(bx, "(b) Area-to-mass provenance")
    S.grid(bx, "y")

    # ---- (c) orbit distribution by object class
    cx = fig.add_subplot(gs[1, 0])
    classes = ["DEB", "PAY", "R/B", "UNK"] if frame.type1.isin(["DEB"]).any() else \
        frame.type1.value_counts().index[:4].tolist()
    present = [c for c in classes if (frame.type1 == c).sum() > 30]
    dat = [frame.loc[(frame.type1 == c) & frame.perigee.notna(), "perigee"].to_numpy()
           for c in present]
    parts = cx.violinplot(dat, showextrema=False, widths=0.82)
    for pc, col in zip(parts["bodies"], (S.C1, S.C2, S.C3, S.C4)):
        pc.set_facecolor(col)
        pc.set_alpha(0.55)
        pc.set_edgecolor(col)
    for i, d in enumerate(dat, start=1):
        cx.plot([i], [np.median(d)], marker="o", color="white", markersize=5,
                markeredgecolor=S.INK, zorder=5)
    cx.set_xticks(range(1, len(present) + 1))
    cx.set_xticklabels([f"{c}\nn={int((frame.type1 == c).sum()):,}" for c in present],
                       fontsize=7.4)
    cx.set_ylabel("perigee (km)")
    cx.set_ylim(0, 2600)
    S.panel_title(cx, "(c) Perigee by object class")
    S.grid(cx, "y")

    # ---- (d) RCS, where available
    dx = fig.add_subplot(gs[1, 1])
    rcs = frame.loc[frame.rcs_m2.notna() & (frame.rcs_m2 > 0), "rcs_m2"]
    dx.hist(np.log10(rcs), bins=44, color=S.C1, edgecolor="white", linewidth=0.5, zorder=3)
    dx.set_xlabel("log₁₀ radar cross-section (m²)")
    dx.set_ylabel("objects")
    S.panel_title(dx, f"(d) RCS where reported (n = {len(rcs):,})")
    S.grid(dx, "y")
    dx.text(0.97, 0.95, f"absent for\n{len(frame) - len(rcs):,} objects",
            transform=dx.transAxes, fontsize=7.2, color=S.C4, ha="right", va="top",
            linespacing=1.5)

    # ---- (e) correlation, within this one table only
    ex = fig.add_subplot(gs[1, 2])
    num = ["perigee", "apogee", "inc", "mass", "rcs_m2", "f107_last81", "ap_last81"]
    corr = frame[num].corr(method="spearman", min_periods=200)
    im = ex.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ex.set_xticks(range(len(num)))
    ex.set_xticklabels(num, rotation=90, fontsize=6.4)
    ex.set_yticks(range(len(num)))
    ex.set_yticklabels(num, fontsize=6.4)
    constant = [c for c in num if frame[c].nunique(dropna=True) <= 1]
    for i in range(len(num)):
        for j in range(len(num)):
            v = corr.iat[i, j]
            if np.isfinite(v):
                ex.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.4,
                        color="white" if abs(v) > 0.55 else S.INK)
            else:
                ex.text(j, i, "n/d", ha="center", va="center", fontsize=5.0, color=S.MUTED)
    # `constant` is recorded in the source-data file and explained in the caption; an in-panel
    # note here collided with the footnote, so the "n/d" cells carry the signal on their own.
    S.panel_title(ex, "(e) Spearman ρ, pairwise-complete"
                      + (f"   ({len(constant)} constant)" if constant else ""))
    cb = fig.colorbar(im, ax=ex, fraction=0.046, pad=0.04)
    cb.ax.tick_params(labelsize=6.4)

    S.save_source(miss, data, "catalogue_feature_availability")
    S.save_source_json({"spearman_within_catalogue_table": corr.round(4).to_dict(),
                        "n_objects": int(len(frame)),
                        "constant_features_no_rank_correlation_defined": constant,
                        "note": "pairwise-complete, min_periods=200; one population, one table"},
                       data, "catalogue_feature_correlation")
    fig.suptitle("Catalogue features consumed by the lifetime and re-entry modules "
                 "(31,396 objects, snapshot 2026-10-27)",
                 x=0.006, ha="left", fontsize=10.2, color=S.INK, y=0.985)
    S.footnote(fig,
               "Panel (a) is the reason the uncertainty results in this project carry a "
               "missingness caveat: mass is absent for 39.8% of objects and radar cross-section "
               "for 60.7%, so the area-to-mass ratio is derived from a class prior for 12,621 of "
               "them (panel b). Panel (b) is drawn in a single colour deliberately — the "
               "project's own subgroup analysis finds the design-derived objects to be the "
               "worse-covered group, so colouring either provenance as the favourable case would "
               "mislead. Panel (e) is computed within this single table and population only; "
               "nothing here is correlated against a different corpus, because none of these "
               "objects can be matched to the telemetry or conjunction corpora. The two "
               "space-weather features take one value across all 31,396 objects in this snapshot, "
               "being evaluated at the common as-of date rather than per object, so they carry no "
               "cross-object information and no rank correlation is defined for them — which is "
               "consistent with the lifetime study's finding that removing the space-weather "
               "group had no detectable effect. Violins in (c) show distribution shape, with the "
               "white marker at the median.", y=0.060)
    return S.save(fig, out, "Figure_D4_catalogue_features"), miss


FIGURES = [("D1", fig_d1), ("D2", fig_d2), ("D3", fig_d3), ("D4", fig_d4)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="paper/figures/datasets")
    ap.add_argument("--data", default="paper/figures/data")
    ap.add_argument("--only", default=None)
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
