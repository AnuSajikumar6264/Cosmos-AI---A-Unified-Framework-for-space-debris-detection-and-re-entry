"""Phase 5 — one artifact-backed compendium of every ablation and comparative arm that exists.

    python scripts/phase5_ablation_compendium.py

Nothing is re-run. Each section reads an archived artifact (path and SHA-256 recorded), restates
what the ablation varied, and gives the measured effect with its archived interval. Sections whose
question cannot be answered from any artifact are listed as NOT EVALUABLE or AWAITING APPROVAL with
the reason, so the compendium also says what is missing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/phase5_ablations"
ORIG = {"2011": "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled",
        "2016": "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled",
        "2006": "outputs/g5d_origin2006/lifetime"}
FUSION_ARMS = ("physics_only", "equal_average", "stack_constant", "cosmos_gated", "cosmos_gated_tuneA")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cite(rel: str) -> dict:
    p = ROOT / rel
    return {"artifact": rel, "sha256": sha(p) if p.is_file() else None, "present": p.is_file()}


def ci_excludes_zero(lo, hi) -> bool:
    return bool(lo > 0 or hi < 0)


def main() -> int:
    rows: list[dict] = []
    sections: dict = {}

    # ---- A. fusion of physics and learned experts (lifetime), all origins ---------------------
    lb_path = "outputs/lifetime_reference_predictors/leaderboard_with_intervals.csv"
    lb = pd.read_csv(ROOT / lb_path)
    a = {"question": "does reliability-gated fusion beat either expert alone and the trivial fusions?",
         "metric": "mean pinball over 7 quantiles of log10 capped lifetime (lower is better); launch-family cluster-bootstrap 95 % CI",
         "source": cite(lb_path), "origins": {}}
    for o, d in ORIG.items():
        summ = json.loads((ROOT / d / "summary.json").read_text())
        sel = summ["best_learner_on_tuneA"]
        g = lb[lb.origin.astype(str) == o].set_index("arm")
        arms = {}
        for arm in FUSION_ARMS + (sel,):
            if arm in g.index:
                r = g.loc[arm]
                arms[arm] = {"pinball": float(r.mean_pinball), "ci95": [float(r.ci95_lo), float(r.ci95_hi)]}
                rows.append({"section": "A_fusion", "origin": o, "ablation": arm, "value": float(r.mean_pinball),
                             "ci_lo": float(r.ci95_lo), "ci_hi": float(r.ci95_hi), "metric": "pinball", "artifact": lb_path})
        pw_path = f"{d}/pairwise_test.csv"
        pairs = {}
        if (ROOT / pw_path).is_file():
            pw = pd.read_csv(ROOT / pw_path)
            for _, r in pw[(pw.a == "cosmos_gated") | (pw.b == "cosmos_gated")].iterrows():
                other = r.b if r.a == "cosmos_gated" else r.a
                sign = 1.0 if r.a == "cosmos_gated" else -1.0        # express as gated minus other
                diff, lo, hi = sign * r.pinball_a_minus_b, min(sign * r.ci95_lo, sign * r.ci95_hi), max(sign * r.ci95_lo, sign * r.ci95_hi)
                pairs[other] = {"gated_minus_other": float(diff), "ci95": [float(lo), float(hi)], "significant": ci_excludes_zero(lo, hi)}
        a["origins"][o] = {"selected_learner": sel, "arms": arms, "paired_vs_cosmos_gated": pairs, "pairwise_source": cite(pw_path)}
    sections["A_fusion_physics_vs_learned"] = a

    # ---- B. the gate itself, per learner ------------------------------------------------------
    b = {"question": "what does the reliability gate add to each learner alone?", "origins": {},
         "metric": "pinball alone vs gated with physics; gain = alone - gated; bootstrap CI; mean gate weight on physics"}
    for o, d in ORIG.items():
        p = f"{d}/gate_all_learners.csv"
        if not (ROOT / p).is_file():
            b["origins"][o] = {"status": "NOT ARCHIVED", "source": cite(p)}
            continue
        g = pd.read_csv(ROOT / p)
        b["origins"][o] = {"source": cite(p), "learners": {
            r.learner: {"pinball_alone": float(r.pinball_alone), "pinball_gated": float(r.pinball_gated), "gain": float(r.gain),
                        "gain_ci95": [float(r.gain_ci95_lo), float(r.gain_ci95_hi)], "gain_significant": ci_excludes_zero(r.gain_ci95_lo, r.gain_ci95_hi),
                        "gate_weight_on_physics_mean": float(r.gate_weight_test_mean),
                        "cov90_alone": float(r.cov90_alone_marginal), "cov90_gated": float(r.cov90_gated_marginal)} for r in g.itertuples()}}
        for r in g.itertuples():
            rows.append({"section": "B_gate", "origin": o, "ablation": f"{r.learner}: alone -> gated", "value": float(r.gain),
                         "ci_lo": float(r.gain_ci95_lo), "ci_hi": float(r.gain_ci95_hi), "metric": "pinball gain", "artifact": p})
    sections["B_reliability_gate_per_learner"] = b

    # ---- C. feature-group ablations (incl. the labelled leak demonstration) --------------------
    c = {"question": "which input groups carry the learned lifetime signal? (refit without the group, selected learner's settings)",
         "metric": "pinball(ablation) - pinball(full); positive = the group helped; bootstrap CI", "origins": {}}
    for o, d in ORIG.items():
        p = f"{d}/ablation_effects_test.csv"
        if not (ROOT / p).is_file():
            c["origins"][o] = {"status": "NOT ARCHIVED (the 2006 refit saved per-arm predictions only; ablation deltas not tabulated)", "source": cite(p)}
            continue
        g = pd.read_csv(ROOT / p)
        c["origins"][o] = {"source": cite(p), "effects": {
            r.ablation: {"delta_pinball": float(r.pinball_ablation_minus_full), "ci95": [float(r.ci95_lo), float(r.ci95_hi)],
                         "significant": ci_excludes_zero(r.ci95_lo, r.ci95_hi),
                         "note": "LEAK DEMONSTRATION: 2026 RCS depends on the outcome; never a candidate" if r.ablation == "plus_rcs_2026" else ""}
            for r in g.itertuples()}}
        for r in g.itertuples():
            rows.append({"section": "C_feature_groups", "origin": o, "ablation": r.ablation, "value": float(r.pinball_ablation_minus_full),
                         "ci_lo": float(r.ci95_lo), "ci_hi": float(r.ci95_hi), "metric": "delta pinball vs full", "artifact": p})
    sections["C_feature_group_ablations"] = c

    # ---- D. uncertainty construction ------------------------------------------------------------
    d_sec = {"question": "how do interval constructions compare: fixed ±20/30 % rules vs conformal, and conformal variants?", "origins": {}}
    for o, d in ORIG.items():
        p = f"{d}/interval_rules.json"
        if (ROOT / p).is_file():
            ir = json.loads((ROOT / p).read_text())
            d_sec["origins"][o] = {"source": cite(p), "rules": ir}
            for k, v in ir.items():
                rows.append({"section": "D_interval_rules", "origin": o, "ablation": k, "value": float(v["coverage"]),
                             "ci_lo": np.nan, "ci_hi": np.nan, "metric": f"coverage (width {v['width_log10']:.3f} log10 d)", "artifact": p})
        else:
            d_sec["origins"][o] = {"status": "NOT ARCHIVED", "source": cite(p)}
    g3 = "outputs/phase3_uncertainty/recalibration_alternatives/results.json"
    if (ROOT / g3).is_file():
        r = json.loads((ROOT / g3).read_text())
        d_sec["conformal_constructions_G3prime"] = {"source": cite(g3), "primary_cosmos_gated": r["primary_criterion_cosmos_gated"],
                                                     "status": "pre-declared protocol; no alternative established closer to nominal"}
    sections["D_uncertainty_construction"] = d_sec

    # ---- E. telemetry alarm layers (ESA-ADB, A0 protocol) ---------------------------------------
    e_path = "outputs/benchmarks/telemetry_esa_adb/results.csv"
    e = {"question": "which alarm layer (calibrator) on top of a fixed scorer gives the best event-wise F0.5 and false-alarm rate?",
         "protocol": "A0 — 9-month calibration period (results.csv); NOT the OOF protocol (A1-A3), which must not be mixed with these numbers",
         "source": cite(e_path), "by_scorer": {}}
    er = pd.read_csv(ROOT / e_path)
    for tag, g in er.groupby("tag"):
        e["by_scorer"][tag] = {r.calibrator: {"EW_F0.5": float(g.loc[r.Index, "anomaly/EW_F0.5"]),
                                              "false_alarms_per_year": float(g.loc[r.Index, "false_alarms_per_year"]),
                                              "alarm_runs": int(g.loc[r.Index, "alarm_runs"])} for r in g.itertuples()}
        for r in g.itertuples():
            rows.append({"section": "E_alarm_layer_A0", "origin": tag, "ablation": r.calibrator, "value": float(g.loc[r.Index, "anomaly/EW_F0.5"]),
                         "ci_lo": np.nan, "ci_hi": np.nan, "metric": "anomaly/EW_F0.5 (A0)", "artifact": e_path})
    sections["E_telemetry_alarm_layers"] = e

    # ---- F. vision input channels ------------------------------------------------------------------
    f_path = "outputs/spotgeo_difficulty/results.json"
    fr = json.loads((ROOT / f_path).read_text())["reproduces_archived_totals"]
    f1 = {k: v["recomputed"]["f1"] for k, v in fr.items()}
    sections["F_vision_input_channels"] = {
        "question": "does the COSMOS registration front end (registered differences) help a learned detector?",
        "source": cite(f_path), "f1": {"raw_highpass_only": f1["unet_raw_f100_s0"], "diff_registered_only": f1["unet_diff_f100_s0"],
                                        "both_mean_3_seeds": float(np.mean([f1[k] for k in f1 if k.startswith("unet_both_f100")])),
                                        "both_sd_3_seeds": float(np.std([f1[k] for k in f1 if k.startswith("unet_both_f100")], ddof=1))},
        "verdict": "negative for the front end: raw >= both > diff; see X14 for drift/background strata", "seeds_note": "raw and diff single-seed"}
    for k, v in f1.items():
        rows.append({"section": "F_vision_inputs", "origin": "spotgeo_test", "ablation": k, "value": v, "ci_lo": np.nan, "ci_hi": np.nan,
                     "metric": "official F1", "artifact": f_path})

    # ---- G. abstention / coherence logic of the lifetime reading ---------------------------------
    x7 = "outputs/reentry_variant_decomposition/results.json"
    r7 = json.loads((ROOT / x7).read_text())["B_t1_observed_vs_expected"]["by_horizon"]
    sections["G_coherence_and_abstention_logic"] = {
        "question": "what changes if the twin used the coherent lifetime reading instead of abstaining on incoherent isotonic records?",
        "source": cite(x7),
        "t1_30d": {k: {"ratio_expected_over_observed": v["ratio_expected_over_observed"], "brier": v["brier"]} for k, v in r7["30d"].items()},
        "reading": ("the coherent reading removes the 123 incoherent records (0 violations) and has the better Brier on T1, but over-predicts "
                    "the 30-day count more (14.8x vs 10.5x of observed); neither lifetime variant is count-calibrated; the deployed gate "
                    "(physics_history for uncontrolled objects) is closest to observation at 1.5x — abstaining on the 123 records changes no "
                    "reported p_30d because the reported forecast does not use the isotonic reading"),
        "exploratory": True}

    # ---- H. what cannot be ablated here -------------------------------------------------------------
    sections["H_not_evaluable_or_awaiting_approval"] = {
        "evidence_validation_fusion_abstention_on_real_joined_evidence": "NOT EVALUABLE — no two modules share an identity (C4); `fusion.decide` is unit-validated only (tests/test_fusion_properties.py)",
        "shared_state_ablation": "NOT APPLICABLE — ObjectTwin is a typed container with no behaviour to remove; its consistency is tested (tests/test_twin_state_consistency.py)",
        "temporal_modelling_branches_telemetry_E6": "AWAITING APPROVAL (X10) — needs new training (hours); the regenerated OPS-SAT runs give per-model, not per-branch, results",
        "esa_adb_input_perturbation_X13": "AWAITING APPROVAL — would re-expose the pre-registered test half",
        "design_time_missingness_am_design_stage2_X6": "AWAITING APPROVAL",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "ablations_table.csv", index=False)
    (OUT / "compendium.json").write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                     "nothing_rerun": True, "sections": sections}, indent=1, default=float) + "\n")
    pd.set_option("display.width", 220)
    print("A. fusion arms (pinball, lower is better):")
    for o, v in sections["A_fusion_physics_vs_learned"]["origins"].items():
        print(f"  {o} selected={v['selected_learner']}: " + ", ".join(f"{k} {x['pinball']:.4f}" for k, x in v["arms"].items()))
        print(f"       gated vs: " + ", ".join(f"{k} {x['gated_minus_other']:+.4f}{'*' if x['significant'] else ''}" for k, x in v["paired_vs_cosmos_gated"].items()))
    print("B. gate gains:")
    for o, v in sections["B_reliability_gate_per_learner"]["origins"].items():
        if "learners" in v:
            print(f"  {o}: " + ", ".join(f"{k} {x['gain']:+.4f}{'*' if x['gain_significant'] else ''} (w={x['gate_weight_on_physics_mean']:.2f})" for k, x in v["learners"].items()))
    print("C. feature groups:")
    for o, v in sections["C_feature_group_ablations"]["origins"].items():
        if "effects" in v:
            print(f"  {o}: " + ", ".join(f"{k} {x['delta_pinball']:+.4f}{'*' if x['significant'] else ''}" for k, x in v["effects"].items()))
    print(f"rows {len(tab)}  written {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
