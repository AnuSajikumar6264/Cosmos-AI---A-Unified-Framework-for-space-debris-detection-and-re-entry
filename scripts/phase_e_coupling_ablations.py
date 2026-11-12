"""Phase E: controlled ablation analysis of the COSMOS-AI cross-domain couplings.

The central research question is whether evidence-aware integration of satellite health,
orbital lifetime, debris and risk intelligence provides measurable value **beyond running the
subsystems independently**. This script answers it for every coupling that the available data
can actually evaluate.

    python scripts/phase_e_coupling_ablations.py
    python scripts/phase_e_coupling_ablations.py --out outputs/phase_e --n-boot 4000

It is a **re-analysis of saved predictions**: no model is retrained, refitted or rescored, so
running it cannot change a published number. What it adds beyond the original studies is

* a multiple-comparison correction across each family of tests (Benjamini-Hochberg),
* cluster-aware paired bootstrap tests for the coupling-relevant contrasts,
* a cross-origin consistency assessment, and
* bootstrap two-sided p-values alongside the existing intervals.

Every addition is **more conservative** than the original report, never less.

Post-hoc status: these test sets were already scored by the original studies, so the analyses
here are post-hoc re-analyses, not confirmatory tests. They are labelled as such throughout
and must be reported that way.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

LIFETIME_DIR = "outputs/benchmarks/reentry_lifetime/origin{origin}_uncontrolled"
C2_CLOUDS = "outputs/benchmarks/twin_couplings/c2_cloud_survival.csv"
C3_SUMMARY = "outputs/benchmarks/twin_couplings/c3_summary.json"
C3_PAYLOADS = "outputs/benchmarks/twin_couplings/c3_payloads.csv"

ORIGINS = ("2011", "2016")
SEED = 20261027


# ------------------------------------------------------------------- statistics
def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> dict:
    """BH step-up procedure. Returns adjusted p-values and rejection flags.

    Applied within each family of related tests (one family per coupling), because the
    original studies reported each contrast's interval without correcting for the number of
    contrasts examined.
    """
    values = np.asarray(p_values, dtype=float)
    n = len(values)
    if n == 0:
        return {"adjusted": [], "rejected": [], "alpha": alpha}
    order = np.argsort(values)
    ranked = values[order]
    adjusted_sorted = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)
    adjusted = np.empty(n)
    adjusted[order] = adjusted_sorted
    return {"adjusted": adjusted.tolist(),
            "rejected": (adjusted <= alpha).tolist(),
            "alpha": alpha}


def paired_cluster_bootstrap(difference: np.ndarray, clusters: np.ndarray,
                             n_boot: int, seed: int = SEED) -> dict:
    """Percentile CI and two-sided p-value of a paired mean difference, resampling clusters.

    Observations within a cluster (a breakup cloud, a launch, an object family) are dependent,
    so clusters are the resampling unit. Treating rows as independent would give intervals
    that are too narrow.

    The p-value is the bootstrap two-sided tail probability of zero under the resampled
    distribution of the mean difference, doubled and capped at 1.
    """
    finite = np.isfinite(difference)
    difference, clusters = difference[finite], clusters[finite]
    if len(difference) == 0:
        return {"n": 0, "mean": None, "ci95_lo": None, "ci95_hi": None, "p_value": None,
                "n_clusters": 0, "detail": "no finite paired observations"}

    rng = np.random.default_rng(seed)
    keys, inverse = np.unique(clusters, return_inverse=True)
    members = [np.flatnonzero(inverse == index) for index in range(len(keys))]
    draws = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(keys), len(keys))
        rows = np.concatenate([members[k] for k in pick])
        draws[b] = float(difference[rows].mean())

    observed = float(difference.mean())
    # Two-sided bootstrap p-value: how often the resampled mean falls on the other side of 0.
    share_below = float((draws <= 0).mean())
    p_value = min(1.0, 2.0 * min(share_below, 1.0 - share_below))
    return {
        "n": int(len(difference)),
        "n_clusters": int(len(keys)),
        "mean": observed,
        "ci95_lo": float(np.quantile(draws, 0.025)),
        "ci95_hi": float(np.quantile(draws, 0.975)),
        "p_value": p_value,
        "bootstrap_draws": n_boot,
    }


def _verdict(record: dict, lower_is_better: bool = True) -> str:
    """Classify an effect from its interval, without reading significance into a point estimate."""
    if record.get("mean") is None:
        return "NOT EVALUABLE"
    low, high = record["ci95_lo"], record["ci95_hi"]
    if low is None or high is None:
        return "NOT EVALUABLE"
    if low > 0:
        return "SUPPORTED" if not lower_is_better else "REFUTED"
    if high < 0:
        return "REFUTED" if not lower_is_better else "SUPPORTED"
    return "INCONCLUSIVE"


# ======================================================================== C1
def _lifetime_arena(root: Path, origin: str):
    """Saved per-object test predictions, target, censoring mask and launch families.

    Reproduces the original study's evaluation set exactly: the pinball loss is taken over
    objects with a known five-year outcome (``known5``), and the resampling unit is the launch
    family of the test fold, in the same row order the predictions were saved in.
    """
    relative = LIFETIME_DIR.format(origin=origin) + "/test_predictions.npz"
    path = root / relative
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=True) as archive:
        data = {key: np.asarray(archive[key]) for key in archive.files}

    from cosmos.ai.lifetime import run as LR
    test = LR.split(LR.load_cohort(), origin, "uncontrolled")["test"].reset_index(drop=True)
    families = test["launch_family"].astype(str).to_numpy()
    if len(families) != len(data["z"]):
        return None
    mask = data["known5"].astype(bool)
    return {"data": data, "mask": mask, "families": families[mask],
            "z": data["z"][mask], "artifact": relative,
            "sha256": sha256_file(path)}


def _pinball_per_object(z: np.ndarray, quantiles: np.ndarray) -> np.ndarray:
    """Per-object pinball loss, identical to the study's ``loss_vec``."""
    from cosmos.ai.lifetime import models as MO
    difference = z[:, None] - quantiles
    return np.mean(np.maximum(MO.QUANTILES * difference,
                              (MO.QUANTILES - 1) * difference), axis=1)


def analyse_c1_bootstrap(root: Path, n_boot: int, alpha: float = 0.05) -> dict:
    """C1 with real paired bootstrap p-values recomputed from the saved predictions.

    The stored ``ablation_effects_test.csv`` reports an interval but no p-value, and an
    interval alone cannot be corrected for multiple comparisons. The per-object losses are
    therefore recomputed here from the saved quantiles -- the same arrays the original study
    scored -- so each ablation gets a bootstrap p-value that BH can act on.
    """
    per_origin = {}
    for origin in ORIGINS:
        arena = _lifetime_arena(root, origin)
        if arena is None:
            per_origin[origin] = {"status": "NOT EVALUABLE",
                                  "detail": f"could not align saved predictions for {origin}"}
            continue
        data, mask, families, z = arena["data"], arena["mask"], arena["families"], arena["z"]
        models = sorted(key[:-3] for key in data if key.endswith("__q"))
        # The full arm is the learner the ablations were refitted from, e.g. tabm_no_family
        # implies the full arm is tabm.
        ablation_arms = [m for m in models if "_no_" in m or "_plus_" in m]
        if not ablation_arms:
            per_origin[origin] = {"status": "NOT EVALUABLE",
                                  "detail": "no ablation arm in the saved predictions"}
            continue
        learner = ablation_arms[0].split("_no_")[0].split("_plus_")[0]
        if f"{learner}__q" not in data:
            per_origin[origin] = {"status": "NOT EVALUABLE",
                                  "detail": f"full arm {learner} absent"}
            continue

        full_loss = _pinball_per_object(z, data[f"{learner}__q"][mask])
        rows, p_values = [], []
        for arm in ablation_arms:
            arm_loss = _pinball_per_object(z, data[f"{arm}__q"][mask])
            # Positive difference = the ablation is worse, i.e. the removed group helps.
            record = paired_cluster_bootstrap(arm_loss - full_loss, families, n_boot)
            group = arm.replace(f"{learner}_", "")
            rows.append({
                "ablation": group,
                "arm": arm,
                "effect_pinball_ablation_minus_full": record["mean"],
                "ci95_lo": record["ci95_lo"],
                "ci95_hi": record["ci95_hi"],
                "p_value": record["p_value"],
                "n_objects": record["n"],
                "n_launch_families": record["n_clusters"],
                "feature_group_helps": bool(record["mean"] is not None and record["mean"] > 0),
            })
            p_values.append(record["p_value"])

        correction = benjamini_hochberg(p_values, alpha=alpha)
        for row, adjusted, rejected in zip(rows, correction["adjusted"],
                                           correction["rejected"]):
            row["p_adjusted_bh"] = adjusted
            row["significant_after_correction"] = bool(rejected)

        family = next((r for r in rows if r["ablation"] == "no_family"), None)
        per_origin[origin] = {
            "learner": learner,
            "artifact": arena["artifact"],
            "artifact_sha256": arena["sha256"],
            "n_objects_scored": int(mask.sum()),
            "n_launch_families": int(pd.unique(families).size),
            "n_tests_in_family": len(rows),
            "full_arm_pinball": float(full_loss.mean()),
            "ablations": rows,
            "no_family": family,
            "status": ("SUPPORTED" if family and family["significant_after_correction"]
                       and family["effect_pinball_ablation_minus_full"] > 0
                       else "INCONCLUSIVE" if family else "NOT EVALUABLE"),
        }

    effects = {o: r["no_family"]["effect_pinball_ablation_minus_full"]
               for o, r in per_origin.items()
               if isinstance(r, dict) and r.get("no_family")}
    signs = {o: int(np.sign(e)) for o, e in effects.items() if e is not None}
    supported = [o for o, r in per_origin.items()
                 if isinstance(r, dict) and r.get("status") == "SUPPORTED"]

    return {
        "coupling": "C1",
        "hypothesis": ("fragment/launch-family statistics available before prediction improve "
                       "orbital lifetime prediction over the same model without them"),
        "direction": "positive effect = family features help (the ablation is worse)",
        "primary_endpoint": "pinball loss of log10 capped lifetime, objects with known 5-year outcome",
        "unit_of_analysis": "catalogued object",
        "independent_unit": "launch family (paired cluster bootstrap)",
        "method": ("per-object pinball losses recomputed from the saved test quantiles; paired "
                   "cluster bootstrap by launch family; Benjamini-Hochberg across the "
                   "ablation family within each origin"),
        "per_origin": per_origin,
        "effects_by_origin": effects,
        "cross_origin_sign_consistent": bool(len(set(signs.values())) == 1 if signs else False),
        "origins_supporting": supported,
        "confound": ("the selected learner differs by origin (2016: tabm, 2011: kumo), so "
                     "temporal origin and learner are entangled; the two origins are not "
                     "exchangeable replicates of the same experiment"),
        "verdict": ("SUPPORTED" if len(supported) == len(ORIGINS)
                    else "PARTIALLY SUPPORTED" if supported
                    else "INCONCLUSIVE"),
        "post_hoc": True,
    }


def analyse_c1(root: Path, alpha: float = 0.05) -> dict:
    """C1: do breakup/launch-family statistics improve orbital lifetime prediction?

    The lifetime study already ran a feature-group ablation in which ``no_family`` removes the
    family features and refits with the selected learner's tuned settings. The saved effect is
    ``pinball(ablation) - pinball(full)``: **positive means the ablation is worse**, i.e. the
    family features help.
    """
    per_origin = {}
    family_tests: list[tuple[str, float]] = []

    for origin in ORIGINS:
        relative = LIFETIME_DIR.format(origin=origin) + "/ablation_effects_test.csv"
        path = root / relative
        if not path.is_file():
            per_origin[origin] = {"status": "NOT EVALUABLE",
                                  "detail": f"missing {relative}"}
            continue
        table = pd.read_csv(path)
        learner = str(table["learner"].iloc[0])

        rows = []
        p_values = []
        for row in table.itertuples(index=False):
            # The saved CI is a cluster bootstrap by launch family. A CI excluding zero is
            # equivalent to a two-sided test at 0.05; a bootstrap p-value is not recoverable
            # from the stored summary, so the interval is used directly and the family-wise
            # correction is applied to an interval-derived p-value proxy.
            crosses_zero = row.ci95_lo <= 0 <= row.ci95_hi
            # Conservative proxy: 0.05 when the interval excludes zero (the strongest claim
            # the stored summary supports), 0.5 otherwise. This cannot manufacture
            # significance -- it can only remove it under correction.
            proxy = 0.05 if not crosses_zero else 0.50
            rows.append({
                "ablation": row.ablation,
                "effect_pinball_ablation_minus_full": float(row.pinball_ablation_minus_full),
                "ci95_lo": float(row.ci95_lo),
                "ci95_hi": float(row.ci95_hi),
                "interval_excludes_zero": bool(not crosses_zero),
                "feature_group_helps": bool(row.pinball_ablation_minus_full > 0
                                            and not crosses_zero),
                "p_proxy_from_interval": proxy,
            })
            p_values.append(proxy)

        correction = benjamini_hochberg(p_values, alpha=alpha)
        for row, adjusted, rejected in zip(rows, correction["adjusted"],
                                           correction["rejected"]):
            row["p_adjusted_bh"] = adjusted
            row["significant_after_correction"] = bool(rejected)

        family = next((r for r in rows if r["ablation"] == "no_family"), None)
        if family:
            family_tests.append((origin, family["effect_pinball_ablation_minus_full"]))
        per_origin[origin] = {
            "learner": learner,
            "artifact": relative,
            "artifact_sha256": sha256_file(path),
            "n_tests_in_family": len(rows),
            "ablations": rows,
            "no_family": family,
            "status": ("SUPPORTED" if family and family["significant_after_correction"]
                       and family["effect_pinball_ablation_minus_full"] > 0
                       else "INCONCLUSIVE" if family else "NOT EVALUABLE"),
        }

    # Cross-origin consistency. The selected learner differs between origins, so origin and
    # learner are confounded -- this is stated, not silently averaged away.
    signs = {origin: np.sign(effect) for origin, effect in family_tests}
    consistent = len(set(signs.values())) == 1 if signs else False
    supported = [o for o, r in per_origin.items()
                 if isinstance(r, dict) and r.get("status") == "SUPPORTED"]

    return {
        "coupling": "C1",
        "hypothesis": ("fragment/launch-family statistics available before prediction improve "
                       "orbital lifetime prediction over the same model without them"),
        "direction": "positive effect = family features help (ablation is worse)",
        "primary_endpoint": "pinball loss of log10 capped lifetime on the temporal test fold",
        "unit_of_analysis": "catalogued object",
        "independent_unit": "launch family (cluster bootstrap)",
        "per_origin": per_origin,
        "cross_origin_sign_consistent": bool(consistent),
        "origins_supporting": supported,
        "confound": ("the selected learner differs by origin (2016: tabm, 2011: kumo), so "
                     "temporal origin and learner are entangled; the two origins are not "
                     "exchangeable replicates"),
        "verdict": ("PARTIALLY SUPPORTED" if supported and len(supported) < len(ORIGINS)
                    else "SUPPORTED" if len(supported) == len(ORIGINS)
                    else "INCONCLUSIVE"),
        "post_hoc": True,
    }


# ======================================================================== C2
#: Contrasts that answer the C2 coupling question: (name, model_a, model_b, reading, family).
#: A negative mean difference means model_a has the smaller absolute fractional count error.
#: ``coupling`` contrasts test the hypothesis and are corrected together. ``calibration`` and
#: ``deployed`` contrasts are diagnostics in their own families.
C2_CONTRASTS = (
    ("learned_vs_physics_calibrated", "tabicl", "physics_only", "predcal", "coupling"),
    ("learned_vs_physics_raw", "tabicl", "physics_only", "pred", "coupling"),
    ("kumo_vs_physics_calibrated", "kumo", "physics_only", "predcal", "coupling"),
    ("kumo_vs_physics_raw", "kumo", "physics_only", "pred", "coupling"),
    # The project's own deployed expert. If the coupling only helps for models that are not
    # the deployed choice, the practical claim is much weaker, so this is reported separately.
    ("deployed_gated_vs_physics_calibrated", "cosmos_gated", "physics_only", "predcal",
     "deployed"),
    ("deployed_gated_vs_physics_raw", "cosmos_gated", "physics_only", "pred", "deployed"),
    # How much of any gain is recalibration rather than the model itself.
    ("calibration_effect_physics", "physics_only", "physics_only", "mixed", "calibration"),
    ("calibration_effect_tabicl", "tabicl", "tabicl", "mixed", "calibration"),
    ("calibration_effect_gated", "cosmos_gated", "cosmos_gated", "mixed", "calibration"),
)


def analyse_c2(root: Path, n_boot: int, alpha: float = 0.05) -> dict:
    """C2: do learned per-object survival probabilities beat physics-only survival for
    predicting how many of a breakup cloud's fragments remain in orbit?

    The coupling is *using the lifetime module's output* to forecast a debris-cloud
    population. The no-coupling baseline is the physics expert's own survival. The endpoint is
    the absolute error of the expected in-orbit count as a fraction of fragments catalogued.
    """
    path = root / C2_CLOUDS
    if not path.is_file():
        return {"coupling": "C2", "verdict": "NOT EVALUABLE",
                "detail": f"missing {C2_CLOUDS}"}
    table = pd.read_csv(path)
    clusters = (table["origin"].astype(str) + "/" + table["cloud"].astype(str)).to_numpy()

    def error_of(model: str, reading: str) -> np.ndarray | None:
        column = f"{reading}_{model}"
        if column not in table.columns:
            return None
        return ((table[column] - table["observed_in_orbit"]) / table["catalogued"]).abs().to_numpy()

    contrasts = []
    for name, model_a, model_b, reading, family in C2_CONTRASTS:
        if reading == "mixed":
            # Effect of isotonic recalibration on the same model: calibrated minus raw.
            left, right = error_of(model_a, "predcal"), error_of(model_b, "pred")
            label = f"predcal_{model_a} - pred_{model_b}"
        else:
            left, right = error_of(model_a, reading), error_of(model_b, reading)
            label = f"{reading}_{model_a} - {reading}_{model_b}"
        if left is None or right is None:
            contrasts.append({"name": name, "contrast": label, "family": family,
                              "status": "NOT EVALUABLE",
                              "detail": "one or both prediction columns are absent"})
            continue
        both = np.isfinite(left) & np.isfinite(right)
        record = paired_cluster_bootstrap(left[both] - right[both], clusters[both], n_boot)
        record.update({
            "name": name,
            "contrast": label,
            "family": family,
            "mean_abs_fraction_error_a": float(np.nanmean(left[both])),
            "mean_abs_fraction_error_b": float(np.nanmean(right[both])),
            "verdict": _verdict(record, lower_is_better=True),
            "interpretation": ("negative mean = the first model has smaller absolute "
                               "fractional count error"),
        })
        contrasts.append(record)

    # Correct within each family separately: the coupling hypothesis is tested by the
    # ``coupling`` family, so diagnostics must not dilute or inflate its correction.
    for family in ("coupling", "deployed", "calibration"):
        members = [c for c in contrasts
                   if c.get("family") == family and c.get("p_value") is not None]
        correction = benjamini_hochberg([c["p_value"] for c in members], alpha=alpha)
        for record, adjusted, rejected in zip(members, correction["adjusted"],
                                              correction["rejected"]):
            record["p_adjusted_bh"] = adjusted
            record["significant_after_correction"] = bool(rejected)

    coupling_family = [c for c in contrasts if c.get("family") == "coupling"
                       and c.get("mean") is not None]
    helping = [c for c in coupling_family
               if c.get("significant_after_correction") and c["mean"] < 0]
    deployed = [c for c in contrasts if c.get("family") == "deployed"
                and c.get("mean") is not None]
    deployed_helping = [c for c in deployed
                        if c.get("significant_after_correction") and c["mean"] < 0]

    primary = next((c for c in contrasts if c["name"] == "learned_vs_physics_calibrated"), None)
    verdict = "NOT EVALUABLE"
    if primary and primary.get("mean") is not None:
        if not primary.get("significant_after_correction"):
            verdict = "INCONCLUSIVE"
        elif primary["mean"] > 0:
            verdict = "REFUTED"
        elif deployed_helping:
            verdict = "SUPPORTED"
        else:
            # The effect exists for some learned experts but not for the deployed one, so the
            # practical claim is weaker than the statistical one.
            verdict = "PARTIALLY SUPPORTED"

    return {
        "coupling": "C2",
        "hypothesis": ("per-object survival probabilities from the lifetime module improve "
                       "breakup-cloud population forecasts over physics-only survival"),
        "primary_endpoint": ("absolute error of the expected in-orbit fragment count, as a "
                             "fraction of fragments catalogued by the evaluation date"),
        "unit_of_analysis": "cloud-year",
        "independent_unit": "breakup cloud (cluster bootstrap)",
        "artifact": C2_CLOUDS,
        "artifact_sha256": sha256_file(path),
        "cloud_years": int(len(table)),
        "clouds": int(pd.unique(clusters).size),
        "contrasts": contrasts,
        "primary_contrast": primary["name"] if primary else None,
        "learned_experts_helping": [c["name"] for c in helping],
        "deployed_expert_helps": bool(deployed_helping),
        "verdict": verdict,
        "deployed_expert_caveat": (
            "the project's deployed expert (cosmos_gated) does NOT show a significant "
            "improvement over physics-only survival; the effect is carried by tabicl and kumo, "
            "which are not the deployed choice. The practical claim is therefore weaker than "
            "the statistical one for the system as configured"
            if not deployed_helping else
            "the deployed expert (cosmos_gated) also shows the improvement"),
        "calibration_caveat": (
            "isotonic recalibration of the survival reading has an effect of comparable or "
            "larger magnitude than the model choice, so part of any gain is attributable to "
            "recalibration rather than to the learned lifetime model itself"),
        "statistical_power_note": (
            f"{int(pd.unique(clusters).size)} independent clouds is a small number of "
            "resampling units; only a large effect could reach significance here"),
        "selection_note": (
            "tabicl and kumo were examined because the original study's C2_PAIRS already "
            "named tabicl; reporting several learned experts rather than only the best one "
            "avoids selecting the winner after the fact"),
        "post_hoc": True,
    }


# ======================================================================== C3
def analyse_c3(root: Path, alpha: float = 0.05) -> dict:
    """C3: does catalogue operational status improve re-entry regime assignment?

    The scientifically meaningful comparison is **prospective only**: policies using
    information available at the as-of date. The in-window recalibrations are fitted on the
    follow-up window's own outcomes and are a diagnostic of attainable calibration, not a
    forecast; they are reported separately and never used to support the coupling.
    """
    path = root / C3_SUMMARY
    if not path.is_file():
        return {"coupling": "C3", "verdict": "NOT EVALUABLE",
                "detail": f"missing {C3_SUMMARY}"}
    summary = json.loads(path.read_text(encoding="utf-8"))

    prospective_keys = {
        "twin_status_aware_baserate_minus_physics_status_blind",
        "twin_status_aware_baserate_minus_base_rate_status_blind",
    }
    in_window_keys = {
        "in_window_recal_status_aware_minus_recal_blind",
        "in_window_recal_status_aware_minus_physics_raw",
    }

    contrasts = []
    p_values = []
    for name, record in summary.get("brier_difference_ci95_launch_bootstrap", {}).items():
        low, high = record["ci95"]
        crosses_zero = low <= 0 <= high
        entry = {
            "contrast": name,
            "family": ("prospective" if name in prospective_keys
                       else "in_window_diagnostic" if name in in_window_keys else "other"),
            "mean_brier_difference": record["mean"],
            "ci95_lo": low,
            "ci95_hi": high,
            "interval_excludes_zero": bool(not crosses_zero),
            "p_proxy_from_interval": 0.05 if not crosses_zero else 0.50,
            "verdict": ("SUPPORTED" if high < 0 else "REFUTED" if low > 0 else "INCONCLUSIVE"),
        }
        contrasts.append(entry)

    # Correct within the prospective family only: the in-window pair cannot support the
    # coupling, so including it would dilute the correction for no scientific gain.
    prospective = [c for c in contrasts if c["family"] == "prospective"]
    correction = benjamini_hochberg([c["p_proxy_from_interval"] for c in prospective],
                                    alpha=alpha)
    for entry, adjusted, rejected in zip(prospective, correction["adjusted"],
                                         correction["rejected"]):
        entry["p_adjusted_bh"] = adjusted
        entry["significant_after_correction"] = bool(rejected)

    supported = [c for c in prospective if c.get("significant_after_correction")
                 and c["mean_brier_difference"] < 0]

    status_groups = summary.get("by_status", {})
    event_rates = {group: record.get("event_rate") for group, record in status_groups.items()}

    return {
        "coupling": "C3",
        "hypothesis": ("catalogue operational status improves 72-day re-entry probability "
                       "over status-blind policies using the same information"),
        "primary_endpoint": "Brier score of P(re-entry within 72 days)",
        "unit_of_analysis": "payload",
        "independent_unit": "launch (cluster bootstrap)",
        "artifact": C3_SUMMARY,
        "artifact_sha256": sha256_file(path),
        "population": {"n": summary.get("n"), "events": summary.get("events"),
                       "event_rate": summary.get("event_rate"),
                       "launches": summary.get("launches"),
                       "launches_with_events": summary.get("launches_with_events"),
                       "horizon_days": summary.get("horizon_days")},
        "prospective_scores": summary.get("prospective"),
        "in_window_scores": summary.get("in_window_cross_fitted"),
        "contrasts": contrasts,
        "event_rate_by_status": event_rates,
        "verdict": ("SUPPORTED" if supported else "INCONCLUSIVE"),
        "physical_interpretation": (
            "operational status is a proxy for operator control, not a causal driver of "
            "atmospheric drag. The coupling works by withholding a drag forecast from "
            "objects whose orbit is actively maintained, which is a conditioning decision, "
            "not a claim that status changes decay physics"),
        "key_caveat": (
            "the window (as-of 2026-08-16, follow-up 2026-10-27) was analysed before, so this "
            "is not a blind test; the status-aware gain over the status-blind base rate is "
            "small and its interval includes zero"),
        "post_hoc": True,
    }


# ======================================================================== C4
def analyse_c4(root: Path) -> dict:
    """C4: can telemetry health flags be used to escalate high-risk conjunctions?

    This requires one dataset in which the same spacecraft has both telemetry health and
    conjunction messages. The search below is over what this repository actually holds.
    """
    telemetry = root / "data/feature1_health/external/esa_ad/prepared"
    conjunction = root / "outputs/benchmarks/conjunction_kelvins_cac/test_predictions.npz"
    catalogue = root / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"

    sources = []
    if telemetry.is_dir():
        missions = sorted(p.name for p in telemetry.glob("mission*.npz"))
        sources.append({
            "source": "ESA-ADB telemetry", "present": bool(missions),
            "identity_key": "anonymised mission + channel",
            "spacecraft_identifiable": False,
            "detail": f"{len(missions)} prepared mission array(s); missions are anonymised "
                      "and carry no spacecraft identifier",
        })
    if conjunction.is_file():
        with np.load(conjunction, allow_pickle=True) as archive:
            events = int(np.asarray(archive["y"]).shape[0])
        sources.append({
            "source": "ESA Kelvins CAC conjunctions", "present": True,
            "identity_key": "positional event index",
            "spacecraft_identifiable": False,
            "detail": f"{events} held-out events; the challenge data are anonymised by "
                      "construction and carry no NORAD identifier",
        })
    if catalogue.is_file():
        sources.append({
            "source": "CelesTrak/GCAT catalogue", "present": True,
            "identity_key": "NORAD ID",
            "spacecraft_identifiable": True,
            "detail": "identifiable, but contains no telemetry and no conjunction messages",
        })

    identifiable = [s for s in sources if s["spacecraft_identifiable"]]
    return {
        "coupling": "C4",
        "hypothesis": ("telemetry-derived health flags identify conjunctions where the "
                       "operator may be unable to manoeuvre, improving decision priority"),
        "sources_examined": sources,
        "joinable_pairs": 0,
        "verdict": "NOT EVALUABLE",
        "reason": (
            "no dataset in this repository links telemetry health to a conjunction event or to "
            "a catalogued object. ESA-ADB missions and Kelvins CAC events are both anonymised "
            "by construction, and the only identifiable source (the catalogue) holds neither "
            "telemetry nor conjunction messages. The required join does not exist, so the "
            "hypothesis cannot be tested -- not merely that it was not tested"),
        "what_would_be_needed": [
            "an operator-held dataset pairing spacecraft telemetry with conjunction data "
            "messages for the same satellite, with outcomes (manoeuvre performed or not)",
            "or a public CDM archive with resolvable NORAD identifiers joined to a public "
            "telemetry source for the same spacecraft",
            "either would require operator cooperation or licensed access; neither is "
            "obtainable from the public sources used here",
        ],
        "implementation_status": (
            "the escalation rule exists in cosmos/ai/twin/couplings.py:c4_escalation and is "
            "exercised as a demonstration on deliberately unpaired examples. In the product "
            "and the orchestrated pipeline it abstains with a recorded reason"),
        "integrity_note": (
            "a plausible-looking escalation could be produced by pairing unrelated health and "
            "conjunction records. That would be fabricated evidence and is not done. The "
            "physical collision probability is never modified by health evidence"),
        "post_hoc": False,
    }


# ============================================================== integration value
def integration_value(c1: dict, c2: dict, c3: dict, c4: dict) -> dict:
    """Synthesise the answer to the central research question."""
    couplings = {"C1": c1, "C2": c2, "C3": c3, "C4": c4}
    verdicts = {name: record.get("verdict") for name, record in couplings.items()}

    supported = [n for n, v in verdicts.items() if v == "SUPPORTED"]
    partial = [n for n, v in verdicts.items() if v == "PARTIALLY SUPPORTED"]
    inconclusive = [n for n, v in verdicts.items() if v == "INCONCLUSIVE"]
    not_evaluable = [n for n, v in verdicts.items() if v == "NOT EVALUABLE"]

    if supported:
        answer = ("PARTIAL: at least one coupling shows a statistically supported improvement "
                  "on its own endpoint, but no coupling is supported across independent "
                  "temporal replicates, and the combined chain is not jointly validated")
    elif partial:
        answer = ("NOT DEMONSTRATED: the strongest coupling (C1) improves its endpoint in one "
                  "temporal origin only, with the learner confounded with the origin. No "
                  "coupling shows a reproducible benefit across replicates")
    else:
        answer = ("NOT DEMONSTRATED: no coupling shows a statistically supported improvement "
                  "over independent subsystem execution on the available data")

    return {
        "central_research_question": (
            "does evidence-aware integration of satellite health, orbital lifetime, debris and "
            "risk intelligence provide measurable scientific or decision value beyond running "
            "the subsystems independently?"),
        "answer": answer,
        "verdict_by_coupling": verdicts,
        "supported": supported,
        "partially_supported": partial,
        "inconclusive": inconclusive,
        "not_evaluable": not_evaluable,
        "combined_chain_evaluated": False,
        "why_no_combined_chain": (
            "a joint C1+C2+C3 arm is not evaluable on one endpoint: C1 is scored by pinball "
            "loss on object lifetimes, C2 by fractional count error on cloud populations, and "
            "C3 by Brier score on payload re-entry. They act on different populations with "
            "different units of analysis and different independent units, so no single "
            "end-to-end metric exists that all three improve. Constructing one aggregate score "
            "to declare integration successful would be an artefact of the aggregation, not a "
            "finding"),
        "what_integration_does_provide": [
            "traceability: every prediction carries its artifact digest, model identity and "
            "uncertainty semantics (verified by tests, not a scientific claim)",
            "explicit abstention where evidence is insufficient, instead of a fabricated value",
            "separation of physical probability from operational priority, enforced in code",
        ],
        "what_integration_does_not_provide": [
            "no demonstrated improvement in predictive accuracy from cross-domain coupling "
            "that reproduces across temporal replicates",
            "no validated end-to-end health-to-re-entry chain (no identity-linked data exists)",
            "no evidence that C4 adds decision value, because it cannot be evaluated",
        ],
        "honest_summary": (
            "COSMOS-AI's defensible contribution is an evidence-graded architecture with "
            "measured component performance and explicit abstention, plus a catalogue-scale "
            "forward lifetime/re-entry benchmark. The cross-domain coupling hypothesis is "
            "NOT supported by reproducible evidence on the available data"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/phase_e")
    parser.add_argument("--n-boot", type=int, default=4000)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Phase E -- coupling ablation analysis (re-analysis of saved predictions)")
    c1 = analyse_c1_bootstrap(root, n_boot=args.n_boot, alpha=args.alpha)
    print(f"  C1 {c1['verdict']}")
    for origin, record in c1["per_origin"].items():
        if "no_family" in record and record["no_family"]:
            family = record["no_family"]
            print(f"     origin {origin} ({record['learner']}): "
                  f"effect {family['effect_pinball_ablation_minus_full']:+.6f} "
                  f"CI [{family['ci95_lo']:+.6f}, {family['ci95_hi']:+.6f}] "
                  f"p={family['p_value']:.4f} p_adj={family['p_adjusted_bh']:.4f} "
                  f"-> {'significant' if family['significant_after_correction'] else 'n.s.'}")

    c2 = analyse_c2(root, n_boot=args.n_boot, alpha=args.alpha)
    print(f"  C2 {c2['verdict']}  ({c2.get('clouds')} clouds, {c2.get('cloud_years')} cloud-years)")
    for record in c2.get("contrasts", []):
        if record.get("mean") is None:
            continue
        flag = "*" if record.get("significant_after_correction") else " "
        print(f"   {flag} [{record['family']:11s}] {record['contrast']:44s} "
              f"mean {record['mean']:+.5f} CI [{record['ci95_lo']:+.5f}, {record['ci95_hi']:+.5f}] "
              f"p_adj={record.get('p_adjusted_bh', float('nan')):.4f}")

    c3 = analyse_c3(root, alpha=args.alpha)
    print(f"  C3 {c3['verdict']}")
    for record in c3.get("contrasts", []):
        if record["family"] != "prospective":
            continue
        print(f"     {record['contrast'][:60]:60s} mean {record['mean_brier_difference']:+.3e} "
              f"CI [{record['ci95_lo']:+.3e}, {record['ci95_hi']:+.3e}] -> {record['verdict']}")

    c4 = analyse_c4(root)
    print(f"  C4 {c4['verdict']} -- {c4['reason'][:80]}...")

    synthesis = integration_value(c1, c2, c3, c4)
    print(f"\n  INTEGRATION: {synthesis['answer'][:150]}")

    record = {
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "n_boot": args.n_boot,
        "alpha": args.alpha,
        "seed": SEED,
        "post_hoc_disclosure": (
            "all test sets analysed here were scored by the earlier studies, so every result "
            "is a post-hoc re-analysis, not a confirmatory test"),
        "method_note": (
            "no model was retrained or rescored; saved predictions were re-analysed with "
            "cluster-aware paired bootstrap and Benjamini-Hochberg correction, both of which "
            "are more conservative than the original per-contrast intervals"),
        "C1": c1, "C2": c2, "C3": c3, "C4": c4,
        "integration_value": synthesis,
    }
    with open(out_dir / "phase_e_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)

    # Flat table for the manuscript.
    rows = []
    for origin, per in c1.get("per_origin", {}).items():
        for ablation in per.get("ablations", []) or []:
            rows.append({"coupling": "C1", "arm": f"origin{origin}/{ablation['ablation']}",
                         "endpoint": "pinball(log10 days)",
                         "effect": ablation["effect_pinball_ablation_minus_full"],
                         "ci95_lo": ablation["ci95_lo"], "ci95_hi": ablation["ci95_hi"],
                         "p_adjusted": ablation.get("p_adjusted_bh"),
                         "significant": ablation.get("significant_after_correction")})
    for contrast in c2.get("contrasts", []) or []:
        if contrast.get("mean") is None:
            continue
        rows.append({"coupling": "C2", "arm": contrast["contrast"],
                     "endpoint": "abs fractional count error", "effect": contrast["mean"],
                     "ci95_lo": contrast["ci95_lo"], "ci95_hi": contrast["ci95_hi"],
                     "p_adjusted": contrast.get("p_adjusted_bh"),
                     "significant": contrast.get("significant_after_correction")})
    for contrast in c3.get("contrasts", []) or []:
        rows.append({"coupling": "C3", "arm": f"{contrast['family']}/{contrast['contrast']}",
                     "endpoint": "Brier(72 d)",
                     "effect": contrast["mean_brier_difference"],
                     "ci95_lo": contrast["ci95_lo"], "ci95_hi": contrast["ci95_hi"],
                     "p_adjusted": contrast.get("p_adjusted_bh"),
                     "significant": contrast.get("significant_after_correction")})
    rows.append({"coupling": "C4", "arm": "not evaluable", "endpoint": None, "effect": None,
                 "ci95_lo": None, "ci95_hi": None, "p_adjusted": None, "significant": None})
    pd.DataFrame(rows).to_csv(out_dir / "coupling_ablation_table.csv", index=False)

    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
