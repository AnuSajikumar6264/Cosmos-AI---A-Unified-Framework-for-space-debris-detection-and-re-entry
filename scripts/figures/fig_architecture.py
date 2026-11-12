"""COSMOS-AI architecture diagrams: the whole system, and the evidence-fusion mechanism.

    python scripts/figures/fig_architecture.py

These two are *diagrams*, not plots: they carry no measured quantity on an axis. Every box is
therefore annotated with its implementation and validation state, and those states are not a
matter of opinion -- they are transcribed from this repository's own audit records and verified
against the code. The provenance of each state is written to
``paper/figures/data/architecture_component_status.csv`` so a reader can check any box against an
artifact.

The structure is read from the code, not from an intention:

  * the module graph is ``cosmos/ai/adapters.py:default_modules()`` -- catalogue_state feeds
    lifetime and reentry, those three feed decision_priority, and collision/health/debris are
    independent roots that cannot block the catalogue chain;
  * the fusion mechanism is ``cosmos/ai/fusion.py:decide()`` -- five compatibility gates, a
    noisy-OR combination, a conflict test on the probability spread, and abstention;
  * the health -> decision edge is gated by ``health_identity_linked``, which defaults to False.
    That default is the C4 finding expressed in code: no dataset here links telemetry health to a
    conjunction or to a catalogued object, so the edge exists but cannot be evaluated.

Nothing in these diagrams asserts that the integrated architecture outperforms independent
components. The project's own coupling experiments did not establish that, and the diagram says so
on its face.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figstyle as S  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

# ---------------------------------------------------------------------------- state vocabulary
# face colour, edge colour, line style, short legend text
STATE = {
    "validated":   ("#dbe6f6", S.STATUS["validated"], "-",
                    "implemented and scientifically validated"),
    # Same hue as `validated` because the evaluation is equally sound; a dash-dot border and a
    # paler fill mark that what it established was a negative or null result.
    "validated_neg": ("#f0f4fb", S.STATUS["validated"], (0, (7, 2, 1.5, 2)),
                      "validated, result negative or null"),
    "implemented": ("#e3f3ee", S.STATUS["implemented"], "-",
                    "implemented, not yet validated"),
    "partial":     ("#fbeedd", S.STATUS["partial"], (0, (5, 2)),
                    "partially implemented"),
    "blocked":     ("#f7e6ef", S.STATUS["blocked"], (0, (2, 2)),
                    "cannot be evaluated with available data"),
    "source":      ("#f2f2ef", "#9a9a94", "-", "external data source"),
    "absent":      ("#ffffff", "#b4b4ae", (0, (1, 2)), "named but not available / not used"),
}


def node(ax, x, y, w, h, label, state, *, fontsize=7.2, weight="normal"):
    face, edge, ls, _ = STATE[state]
    S.box(ax, x, y, w, h, label, face=face, edge=edge, ls=ls, lw=1.2,
          fontsize=fontsize, weight=weight)


def band(ax, y, h, title, *, tint="#fafaf8"):
    ax.add_patch(Rectangle((0.005, y), 0.99, h, facecolor=tint, edgecolor="none", zorder=0))
    ax.text(0.014, y + h - 0.009, title, fontsize=8.4, color=S.INK2,
            ha="left", va="top", fontweight="bold", zorder=1)


# ============================================================ Figure A1: overall architecture
# (name, state, evidence pointer) -- the pointer is what makes the state checkable
COMPONENTS = [
    # data sources
    ("ESA-ADB telemetry (2 missions)", "source", "data/DATASET_REPORT.md; Zenodo 10.5281/zenodo.12528696"),
    ("OPS-SAT-AD telemetry", "source", "data/DATASET_REPORT.md; 2,123 fragments, 9 channels"),
    ("SMAP / MSL telemetry", "source", "data/DATASET_REPORT.md; telemanom release"),
    ("CelesTrak SATCAT + GP/TLE", "source", "data/DATASET_REPORT.md; 71,132 objects"),
    ("GCAT catalogue", "source", "data/DATASET_REPORT.md"),
    ("SpotGEO optical imagery", "source", "data/DATASET_REPORT.md; 32,000 frames"),
    ("Kelvins CAC conjunctions", "source", "data/DATASET_REPORT.md; anonymised by construction"),
    ("NOAA F10.7 / GFZ Ap", "source", "data/DATASET_REPORT.md"),
    ("ESA recovered-debris records", "source", "data/DATASET_REPORT.md; 235 fragment rows"),
    ("Space-Track / DISCOSweb", "absent", "credentials required; HTTP 401; not attempted"),
    ("SPARK / SpaceSense", "absent", "access-gated or different task; not used"),
    # ingestion
    ("evidence adapters\n(cosmos/ai/adapters.py)", "implemented", "7 module specs, typed outputs"),
    ("typed evidence contracts\n(cosmos/ai/contracts.py)", "implemented",
     "11 dataclasses with __post_init__ validation"),
    ("provenance capture\n(cosmos/ai/provenance.py)", "implemented", "used at adapters.py:43"),
    ("snapshot & timestamp\ncompatibility", "implemented", "contracts._validate_time_provenance"),
    ("missingness detection\n& quality flags", "implemented", "area_to_mass_source, am_source subgroups"),
    ("identity resolution\nacross corpora", "blocked", "0 joinable pairs: telemetry corpora are anonymised"),
    # digital state
    ("identity &\ncatalogue record", "implemented", "adapters.catalogue_state"),
    ("orbital elements\n& derived orbit", "implemented", "contracts.OrbitalElements"),
    ("object characteristics\n(mass, area/mass, RCS)", "implemented", "contracts.ObjectCharacteristics"),
    ("telemetry / health\nstate", "implemented", "contracts.HealthEstimate"),
    ("visual observations", "implemented", "contracts.DebrisDetection"),
    ("evidence freshness\n& provenance", "implemented", "contracts.Provenance"),
    ("prediction history\n(versioned runs)", "implemented", "outputs/twin/as_of_*, outputs/registry"),
    # intelligence modules
    ("telemetry anomaly detection\nESA-ADB · pre-registered", "validated",
     "freeze 09a98f5e160e; official metric byte-identical to upstream 67194d3"),
    ("telemetry anomaly detection\nSMAP / MSL", "validated",
     "outputs/benchmarks/telemetry_smap_msl/summary.csv; 3 robustness protocols"),
    ("telemetry anomaly detection\nOPS-SAT", "implemented",
     "significance only on the interleaved split; score archive absent"),
    ("satellite health monitoring\n(cosmos/health)", "partial",
     "ties a trivial out-of-limits rule on M1 lightweight; collapses at full scale"),
    ("orbital lifetime prediction", "validated_neg",
     "3 origins; selection regret significant at 2016; gated arm ranks 9th of 19"),
    ("orbital decay / re-entry\nlandmark", "validated",
     "tau 2026-08-16; 5-check leakage report; 38 test events"),
    ("re-entry footprint\nsurrogate", "implemented",
     "n = 40,000 against the simulator; never a recorded re-entry"),
    ("debris detection\nSpotGEO", "validated_neg", "official metric; test F1 0.084"),
    ("collision / conjunction\nrisk", "validated_neg",
     "trivial latest_risk_point F2 0.739 beats best learned arm 0.168"),
    # couplings
    ("C1  family evidence\n-> lifetime", "partial",
     "E12: -0.0514 at origin 2011, +0.0026 at 2016; significant at neither"),
    ("C2  survival\n-> debris-cloud count", "partial",
     "deployed arm p = 0.364; recalibration effect comparable or larger"),
    ("C3  status\n-> re-entry regime", "partial", "Phase E verdict INCONCLUSIVE"),
    ("C4  health\n-> conjunction priority", "blocked",
     "0 joinable pairs; gated off by health_identity_linked = False"),
    # integration layer
    ("evidence normalisation\n& compatibility gates", "implemented",
     "fusion.decide: claim, object, window, status, domain"),
    ("uncertainty quantification\n(Mondrian CQR)", "implemented",
     "coverage deviates significantly in 3 of 4 Phase H cells"),
    ("multimodal fusion\n(noisy-OR)", "implemented",
     "fusion.decide; conditional independence is an assumption, not a finding"),
    ("conflict detection\n& abstention", "implemented", "spread > 0.6 -> abstain"),
    ("missing-modality\nhandling", "implemented", "independent roots; explicit ArtifactUnavailable"),
    ("decision support\n& prioritisation", "implemented",
     "adapters.decision_priority; no decision-quality metric exists"),
    ("demonstrated advantage over\nindependent components", "blocked",
     "Phase E integration_value: NOT DEMONSTRATED"),
    # application layer
    ("Mission Intelligence Console\n(14 screens)", "implemented",
     "outputs/product/screens; reads real artifacts; no outcome-scored evaluation"),
    ("risk assessment &\nprediction views", "implemented", "outputs/product/reports"),
    ("scenario analysis", "implemented", "screens/11_scenario_analysis.html"),
    ("historical run explorer\n& provenance reports", "implemented",
     "screens/09_run_explorer.html, 12_run_detail.html, 13_run_compare.html"),
    ("prospective validation", "blocked",
     "screens/10_prospective_blocked.html; the follow-up window has not elapsed"),
]


def fig_architecture(root: Path, out: Path, data: Path):
    src = pd.DataFrame(COMPONENTS, columns=["component", "state", "evidence"])
    src["state_meaning"] = src.state.map(lambda s: STATE[s][3])

    fig = plt.figure(figsize=(13.2, 16.4))
    ax = S.blank_axes(fig)

    L, R = 0.018, 0.982
    def cols(n, gap=0.012, left=L, right=R):
        w = (right - left - gap * (n - 1)) / n
        return [(left + i * (w + gap), w) for i in range(n)], w

    # ---------------------------------------------------------------- 1 data sources
    band(ax, 0.846, 0.108, "DATA SOURCES   (external, read-only)")
    pos, w = cols(5)
    srcs = ["ESA-ADB telemetry\n2 missions · 30 s / 18 s grids",
            "OPS-SAT-AD telemetry\n2,123 fragments · 9 channels",
            "SMAP / MSL telemetry\n55 + 27 channels",
            "CelesTrak SATCAT + GP/TLE\n71,132 objects · GCAT",
            "SpotGEO optical imagery\n32,000 frames · 55,800 objects"]
    for (x, _), lab in zip(pos, srcs):
        node(ax, x, 0.898, w, 0.040, lab, "source", fontsize=6.6)
    srcs2 = ["Kelvins CAC conjunctions\nanonymised by construction",
             "NOAA F10.7 / GFZ Ap\nspace weather",
             "ESA recovered-debris records\n235 fragments · 86 objects",
             "Space-Track · ESA DISCOSweb\ncredentials required — not used",
             "SPARK · SpaceSense\naccess-gated / different task — not used"]
    for (x, _), lab in zip(pos, srcs2):
        st = "absent" if "not used" in lab else "source"
        node(ax, x, 0.852, w, 0.040, lab, st, fontsize=6.6)

    # ---------------------------------------------------------------- 2 ingestion
    band(ax, 0.726, 0.108, "INGESTION, PROVENANCE AND COMPATIBILITY")
    pos, w = cols(6)
    ing = [("evidence adapters\n7 typed modules", "implemented"),
           ("typed evidence contracts\n11 validated dataclasses", "implemented"),
           ("provenance capture\nsource · digest · as-of", "implemented"),
           ("timestamp & snapshot\ncompatibility", "implemented"),
           ("missingness detection\n& quality flags", "implemented"),
           ("identity resolution\nACROSS corpora", "blocked")]
    for (x, _), (lab, st) in zip(pos, ing):
        node(ax, x, 0.742, w, 0.062, lab, st, fontsize=6.7)

    # ---------------------------------------------------------------- 3 digital state
    band(ax, 0.606, 0.108, "SATELLITE DIGITAL STATE   (one common representation per object)")
    pos, w = cols(7)
    st_nodes = ["identity &\ncatalogue record", "orbital elements\n& derived orbit",
                "object characteristics\nmass · area/mass · RCS", "telemetry &\nhealth state",
                "visual\nobservations", "evidence freshness\n& provenance",
                "prediction history\nversioned runs"]
    for (x, _), lab in zip(pos, st_nodes):
        node(ax, x, 0.620, w, 0.064, lab, "implemented", fontsize=6.6)

    # ---------------------------------------------------------------- 4 intelligence modules
    band(ax, 0.374, 0.220, "INTELLIGENCE MODULES   (each evaluated on its own benchmark)")
    pos, w = cols(5)
    mods_top = [("telemetry anomaly detection\nESA-ADB — pre-registered\nfreeze 09a98f5e160e",
                 "validated"),
                ("telemetry anomaly detection\nSMAP / MSL\n3 robustness protocols", "validated"),
                ("telemetry anomaly detection\nOPS-SAT\nsplit not temporal", "implemented"),
                ("satellite health monitoring\ncosmos/health\nties a trivial rule", "partial"),
                ("orbital lifetime prediction\n3 temporal origins\ngated arm ranks 9/19",
                 "validated_neg")]
    for (x, _), (lab, st) in zip(pos, mods_top):
        node(ax, x, 0.496, w, 0.074, lab, st, fontsize=6.6)
    mods_bot = [("orbital decay / re-entry landmark\nc-index 0.976 — 38 test events", "validated"),
                ("re-entry footprint surrogate\nvalidated against the simulator only", "implemented"),
                ("debris detection — SpotGEO\nofficial metric · test F1 0.084", "validated_neg"),
                ("collision / conjunction risk\ntrivial rule F2 0.739 > learned 0.168",
                 "validated_neg"),
                ("multimodal evidence fusion\nmechanism implemented · gain not shown", "blocked")]
    for (x, _), (lab, st) in zip(pos, mods_bot):
        node(ax, x, 0.392, w, 0.074, lab, st, fontsize=6.6)

    # ---------------------------------------------------------------- 5 couplings
    band(ax, 0.254, 0.108, "CROSS-MODULE COUPLINGS   (the integration claim, as actually tested)",
         tint="#f5f2f5")
    pos, w = cols(4)
    cps = [("C1  family evidence → lifetime\nPARTIALLY SUPPORTED\nsign inconsistent across origins",
            "partial"),
           ("C2  survival → debris-cloud count\nPARTIALLY SUPPORTED\ndeployed arm p = 0.364",
            "partial"),
           ("C3  status → re-entry regime\nINCONCLUSIVE", "partial"),
           ("C4  health → conjunction priority\nNOT EVALUABLE\n0 joinable pairs", "blocked")]
    for (x, _), (lab, st) in zip(pos, cps):
        node(ax, x, 0.272, w, 0.066, lab, st, fontsize=6.6)

    # ---------------------------------------------------------------- 6 integration layer
    band(ax, 0.112, 0.130, "INTEGRATION AND DECISION LAYER")
    pos, w = cols(6)
    integ = [("evidence normalisation\n5 compatibility gates", "implemented"),
             ("uncertainty quantification\nMondrian CQR", "implemented"),
             ("multimodal fusion\nnoisy-OR", "implemented"),
             ("conflict detection\nspread > 0.6 → abstain", "implemented"),
             ("missing-modality handling\nindependent roots", "implemented"),
             ("decision support\n& prioritisation", "implemented")]
    for (x, _), (lab, st) in zip(pos, integ):
        node(ax, x, 0.158, w, 0.058, lab, st, fontsize=6.6)
    node(ax, L, 0.120, R - L, 0.032,
         "demonstrated advantage over independent components  —  NOT DEMONSTRATED "
         "(Phase E: one coupling not reproducible, one with no gain in its deployed arm, "
         "one inconclusive, one not evaluable)", "blocked", fontsize=6.9, weight="bold")

    # ---------------------------------------------------------------- 7 application layer
    band(ax, 0.004, 0.096, "APPLICATION LAYER")
    pos, w = cols(5)
    app = [("Mission Intelligence Console\n14 screens · real artifacts", "implemented"),
           ("satellite monitoring\n& risk assessment", "implemented"),
           ("prediction & uncertainty\nvisualisation", "implemented"),
           ("scenario analysis\n& historical runs", "implemented"),
           ("prospective validation\nwindow not yet elapsed", "blocked")]
    for (x, _), (lab, st) in zip(pos, app):
        node(ax, x, 0.016, w, 0.060, lab, st, fontsize=6.6)

    # ---------------------------------------------------------------- flow arrows
    for x in (0.16, 0.38, 0.60, 0.82):
        for y_from, y_to in ((0.846, 0.8360), (0.726, 0.7160), (0.606, 0.5960),
                             (0.374, 0.3640), (0.254, 0.2440), (0.112, 0.1020)):
            S.arrow(ax, (x, y_from), (x, y_to), lw=1.4, color="#8c8b85")

    # The one edge the available data cannot support. Drawn as a severed arrow between two module
    # boxes it was more confusing than informative, so it is named in words instead.
    ax.text(0.5, 0.2700,
            "C4 would connect satellite health monitoring to collision / conjunction risk. The "
            "edge exists in cosmos/ai/twin/couplings.py:c4_escalation but is gated off by "
            "health_identity_linked = False,\nbecause no dataset in this repository links "
            "telemetry health to a conjunction or to a catalogued object.",
            fontsize=6.4, color=S.STATUS["blocked"], ha="center", va="top", linespacing=1.45)

    # ---------------------------------------------------------------- legend & title
    ax.text(0.005, 0.999, "COSMOS-AI: uncertainty-aware multimodal satellite digital twin",
            fontsize=12.5, color=S.INK, ha="left", va="top", fontweight="bold")
    ax.text(0.005, 0.977,
            "Architecture as implemented on 2026-11-05. Box colour and border encode "
            "implementation and validation state; no box asserts a performance claim.",
            fontsize=7.8, color=S.INK2, ha="left", va="top")

    seen, handles = set(), []
    for key in ("validated", "validated_neg", "implemented", "partial", "blocked",
                "source", "absent"):
        face, edge, ls, text = STATE[key]
        if text in seen:
            continue
        seen.add(text)
        handles.append(Patch(facecolor=face, edgecolor=edge, linestyle=ls, label=text))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, -0.030), ncol=4,
              fontsize=7.4, frameon=False, handlelength=1.8, columnspacing=1.6)

    S.footnote(fig,
               "Read this diagram as a map of what exists, not as a claim. The flow arrows show "
               "data dependence as declared in adapters.default_modules(); the catalogue chain is "
               "dependency-linked while health, collision and debris are independent roots, so a "
               "missing telemetry or imagery artifact cannot block the rest. The couplings band "
               "reports the project's own cross-module experiments with their recorded verdicts, "
               "and the integration claim is marked NOT DEMONSTRATED because those experiments "
               "did not establish it. Per-component evidence pointers are in "
               "paper/figures/data/architecture_component_status.csv.", y=-0.055)

    S.save_source(src, data, "architecture_component_status")
    return S.save(fig, out, "Figure_Architecture_COSMOS_AI"), src


# ============================================================ Figure A2: evidence fusion
def fig_fusion(root: Path, out: Path, data: Path):
    """The fusion mechanism exactly as cosmos/ai/fusion.py:decide() implements it."""
    gates = [
        ("claim match", "it.claim != claim → reported, not used"),
        ("object identity", "it.object_id not in (None, object_id) → reported"),
        ("time-window overlap", "_overlap(it.window, window) is False → reported"),
        ("validation status", "not it.status.startswith('validated') → reported"),
        ("input in domain", "not it.in_domain → reported"),
    ]
    src = pd.DataFrame(
        [{"stage": "compatibility gate", "element": g, "implementation": impl}
         for g, impl in gates]
        + [{"stage": "sufficiency", "element": "min_items",
            "implementation": "len(used) < min_items → abstain 'insufficient compatible evidence'"},
           {"stage": "conflict", "element": "spread test",
            "implementation": "ps.max() - ps.min() > 0.6 → abstain 'conflicting evidence'"},
           {"stage": "combination", "element": "noisy-OR",
            "implementation": "p = 1 - prod(1 - ps); assumes conditional independence"},
           {"stage": "disclosure", "element": "assumptions list",
            "implementation": "records the independence assumption and any synthetic-only item"},
           {"stage": "output", "element": "Decision",
            "implementation": "claim, probability|None, abstain, reason, used, reported_only, assumptions"}])

    fig = plt.figure(figsize=(12.4, 8.3))
    ax = S.blank_axes(fig)

    ax.text(0.005, 0.995, "COSMOS-AI evidence fusion: implemented mechanism",
            fontsize=12.5, color=S.INK, ha="left", va="top", fontweight="bold")
    ax.text(0.005, 0.962,
            "Every element below is in cosmos/ai/fusion.py. The mechanism is implemented and "
            "unit-tested; it is NOT shown to improve decisions, because no decision-quality "
            "metric, regret measure or operator study exists in this project.",
            fontsize=7.8, color=S.INK2, ha="left", va="top")

    # ---- 1 subsystem outputs
    band(ax, 0.790, 0.115, "1  INDEPENDENT SUBSYSTEM OUTPUTS")
    subs = [("health\nLearnedHealthMonitor\nscore in [0,1]", "implemented"),
            ("re-entry\nP(re-entry ≤ h)\nphysics or learned", "validated"),
            ("debris\nDebrisDetection\nper-frame objects", "validated_neg"),
            ("lifetime\nquantiles + interval\nMondrian CQR", "validated_neg")]
    xs = [0.035, 0.265, 0.495, 0.725]
    for x, (lab, st) in zip(xs, subs):
        node(ax, x, 0.800, 0.21, 0.072, lab, st, fontsize=6.9)

    # ---- 2 evidence contract
    band(ax, 0.672, 0.100, "2  EVIDENCE CONTRACT   (fusion.Evidence — one dataclass per item)")
    node(ax, 0.035, 0.684, 0.90, 0.062,
         "feature · model (registry card) · claim · probability · status · in_domain · "
         "object_id · window · details\n"
         "A probability here is a reporting convention where the subsystem does not supply a "
         "calibrated posterior, and is labelled as such in `details`.",
         "implemented", fontsize=7.0)

    # ---- 3 gates
    band(ax, 0.470, 0.185, "3  COMPATIBILITY GATES   (an item that fails any gate is reported, "
                           "never combined)")
    # Short rules sit under each gate as a caption; no per-gate arrow, because an arrow from each
    # box to the row below printed straight through its own caption.
    gw = 0.172
    short = ["claim differs", "object differs", "window does not overlap",
             "status not 'validated…'", "input out of domain"]
    for i, ((name, rule), brief) in enumerate(zip(gates, short)):
        x = 0.035 + i * (gw + 0.009)
        node(ax, x, 0.566, gw, 0.052, f"{name}", "implemented", fontsize=7.2, weight="bold")
        ax.text(x + gw / 2, 0.5565, f"fails if {brief}", fontsize=6.4, color=S.INK2,
                ha="center", va="top", linespacing=1.3)
    node(ax, 0.035, 0.482, 0.44, 0.036, "used  →  carried into the combination",
         "implemented", fontsize=7.2)
    node(ax, 0.495, 0.482, 0.44, 0.036,
         "reported_only  →  surfaced with its reason, never combined", "partial", fontsize=7.2)

    # ---- 4 decision
    band(ax, 0.262, 0.190, "4  SUFFICIENCY, CONFLICT AND COMBINATION")
    node(ax, 0.035, 0.366, 0.28, 0.058,
         "sufficiency\nlen(used) < min_items\n→ ABSTAIN", "blocked", fontsize=7.0)
    node(ax, 0.360, 0.366, 0.28, 0.058,
         "conflict test\nmax(p) − min(p) > 0.6\n→ ABSTAIN", "blocked", fontsize=7.0)
    node(ax, 0.685, 0.366, 0.25, 0.058,
         "noisy-OR\np = 1 − ∏(1 − pᵢ)", "implemented", fontsize=7.4, weight="bold")
    S.arrow(ax, (0.315, 0.395), (0.358, 0.395), lw=1.2)
    S.arrow(ax, (0.640, 0.395), (0.683, 0.395), lw=1.2)
    node(ax, 0.035, 0.278, 0.90, 0.058,
         "recorded assumptions  ·  \"noisy-OR: the evidence items are treated as conditionally "
         "independent\"  ·  \"at least one item is validated on synthetic data only\"\n"
         "Conditional independence is an assumption of the implementation, not a property "
         "established for these subsystems.", "partial", fontsize=6.9)

    # ---- 5 output
    band(ax, 0.128, 0.120, "5  UNIFIED DECISION OUTPUT   (fusion.Decision)")
    node(ax, 0.035, 0.140, 0.90, 0.066,
         "claim  ·  probability | None  ·  abstain  ·  reason  ·  used  ·  reported_only  ·  "
         "assumptions\n"
         "A None probability with abstain = True is a first-class outcome, not an error: the "
         "console renders it as an explicit refusal to answer.", "implemented", fontsize=7.0)

    for y0, y1 in ((0.790, 0.7725), (0.672, 0.6555), (0.262, 0.2485)):
        for x in (0.22, 0.50, 0.78):
            S.arrow(ax, (x, y0), (x, y1), lw=1.3, color="#8c8b85")
    # Only the `used` items enter the combination; an arrow under reported_only would assert the
    # opposite of what decide() does. reported_only reaches the output directly, down the margin.
    for x in (0.17, 0.34):
        S.arrow(ax, (x, 0.470), (x, 0.4525), lw=1.3, color="#8c8b85")
    S.arrow(ax, (0.960, 0.482), (0.960, 0.208), lw=1.1, ls=(0, (4, 3)), color=S.STATUS["partial"])

    # ---- what is NOT established
    node(ax, 0.035, 0.012, 0.90, 0.098,
         "NOT ESTABLISHED BY THIS PROJECT\n"
         "that fusing these subsystems yields better decisions than using them independently\n"
         "(Phase E: C1 partially supported with inconsistent signs · C2 no gain in the deployed "
         "arm · C3 inconclusive · C4 not evaluable, 0 joinable pairs)\n"
         "and that the combined probability is calibrated — no decision-quality metric,\n"
         "regret measure or operator study exists in this project.",
         "blocked", fontsize=6.9, weight="bold")

    handles = []
    for key in ("validated", "validated_neg", "implemented", "partial", "blocked"):
        face, edge, ls, text = STATE[key]
        handles.append(Patch(facecolor=face, edgecolor=edge, linestyle=ls, label=text))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, -0.062), ncol=5,
              fontsize=7.4, frameon=False, handlelength=1.8, columnspacing=1.4)

    S.footnote(fig,
               "Gate rules are quoted from the source; the full predicate for each is in the "
               "source-data file. The conflict threshold of 0.6 and min_items are call-site "
               "parameters with those defaults, not tuned quantities. Only `used` items enter "
               "the combination; the dashed line on the right marks `reported_only` travelling to "
               "the output without being combined. Element-by-element provenance is in "
               "paper/figures/data/fusion_mechanism_elements.csv.", y=-0.085)

    S.save_source(src, data, "fusion_mechanism_elements")
    return S.save(fig, out, "Figure_Evidence_Fusion"), src


FIGURES = [("A1", fig_architecture), ("A2", fig_fusion)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="paper/figures/architecture")
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
        print(f"{fid}: {paths[0].relative_to(root)}  ({len(src)} documented elements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
