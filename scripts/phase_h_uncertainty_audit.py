"""Phase H: empirical audit of COSMOS-AI's uncertainty and evidence machinery.

The question is not whether an uncertainty mechanism is implemented — several are — but
whether its **nominal** guarantee is **observed**. Nominal conformal coverage and empirical
coverage are different quantities, and this script measures the second.

    python scripts/phase_h_uncertainty_audit.py
    python scripts/phase_h_uncertainty_audit.py --out outputs/phase_h --n-boot 4000

Method: recompute per-object interval coverage from the saved test predictions
(`<model>__lo90/__hi90/__lo80/__hi80` against the target `z`), then bootstrap by launch
family. Coverage is a mean of indicator variables over dependent observations, so an
independence interval would be too narrow and could call a deviation significant when it is
not.

No model is refitted; no published number is altered.
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
from scripts.phase_e_coupling_ablations import paired_cluster_bootstrap  # noqa: E402

ORIGINS = ("2011", "2016")
SEED = 20261027
#: Models of interest: the deployed expert, the physics baseline, each origin's best learner,
#: and the marginal-conformal variants that exist for comparison.
FOCUS = ("cosmos_gated", "cosmos_gated_marginal_conformal", "physics_only",
         "tabm", "tabm_marginal_conformal", "kumo", "kumo_marginal_conformal",
         "tabicl", "mlp")
LEVELS = {"cov80": 0.80, "cov90": 0.90}


def _base(root: Path, origin: str) -> Path:
    return root / "outputs" / "benchmarks" / "reentry_lifetime" / f"origin{origin}_uncontrolled"


def _arena(root: Path, origin: str) -> dict | None:
    path = _base(root, origin) / "test_predictions.npz"
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
    return {"data": data, "mask": mask, "z": data["z"][mask],
            "families": families[mask], "path": path, "sha256": sha256_file(path),
            "time_days": data["time_days"][mask], "event": data["event"][mask]}


def coverage_record(indicator: np.ndarray, families: np.ndarray, nominal: float,
                    n_boot: int) -> dict:
    """Empirical coverage with a launch-family cluster bootstrap interval.

    The deviation from nominal is tested by bootstrapping ``indicator - nominal``: if that
    interval excludes zero, the observed coverage differs from nominal beyond resampling
    noise under clustering.
    """
    record = paired_cluster_bootstrap(indicator.astype(float) - nominal, families,
                                      n_boot, seed=SEED)
    if record["mean"] is None:
        return {"status": "NOT EVALUABLE", "detail": record.get("detail")}
    empirical = float(indicator.mean())
    deviation = record["mean"]
    if record["ci95_hi"] < 0:
        verdict = "UNDER-COVERS"
    elif record["ci95_lo"] > 0:
        verdict = "OVER-COVERS"
    else:
        verdict = "CONSISTENT WITH NOMINAL"
    return {
        "status": "evaluated",
        "nominal": nominal,
        "empirical_coverage": empirical,
        "deviation": deviation,
        "deviation_ci95_lo": record["ci95_lo"],
        "deviation_ci95_hi": record["ci95_hi"],
        "p_value": record["p_value"],
        "n": record["n"],
        "n_launch_families": record["n_clusters"],
        "verdict": verdict,
    }


def audit_intervals(root: Path, origin: str, n_boot: int) -> dict:
    arena = _arena(root, origin)
    if arena is None:
        return {"status": "NOT EVALUABLE", "detail": f"cannot align test fold for {origin}"}
    data, mask, z, families = arena["data"], arena["mask"], arena["z"], arena["families"]

    models = {}
    for model in FOCUS:
        entry = {}
        for label, nominal in LEVELS.items():
            width = label.replace("cov", "")
            lo_key, hi_key = f"{model}__lo{width}", f"{model}__hi{width}"
            if lo_key not in data or hi_key not in data:
                entry[label] = {"status": "absent"}
                continue
            low, high = data[lo_key][mask], data[hi_key][mask]
            finite = np.isfinite(low) & np.isfinite(high) & np.isfinite(z)
            if finite.sum() == 0:
                entry[label] = {"status": "no finite intervals"}
                continue
            inside = (z[finite] >= low[finite]) & (z[finite] <= high[finite])
            entry[label] = coverage_record(inside, families[finite], nominal, n_boot)
            entry[label]["mean_interval_width_log10_days"] = float(
                np.mean(high[finite] - low[finite]))
        if any(v.get("status") == "evaluated" for v in entry.values()):
            models[model] = entry
    return {"status": "evaluated", "origin": origin, "artifact": str(arena["path"].name),
            "artifact_sha256": arena["sha256"],
            "n_objects_scored": int(mask.sum()),
            "n_launch_families": int(pd.unique(families).size),
            "models": models}


def temporal_drift(root: Path, origin: str) -> dict:
    """Per-year coverage from the study's saved table, to expose distribution shift."""
    path = _base(root, origin) / "temporal_coverage_test.csv"
    if not path.is_file():
        return {"status": "NOT EVALUABLE", "detail": "temporal_coverage_test.csv absent"}
    table = pd.read_csv(path)
    out = {}
    for model, group in table.groupby("model"):
        if model not in FOCUS:
            continue
        group = group.sort_values("year")
        years = group["year"].astype(int).tolist()
        values = group["cov90"].astype(float).tolist()
        counts = group["n"].astype(int).tolist()
        if len(values) < 2:
            continue
        # Spearman-style monotone trend via rank correlation, without scipy.
        rank_year = pd.Series(years).rank().to_numpy()
        rank_cov = pd.Series(values).rank().to_numpy()
        if np.std(rank_year) == 0 or np.std(rank_cov) == 0:
            trend = None
        else:
            trend = float(np.corrcoef(rank_year, rank_cov)[0, 1])
        out[model] = {
            "years": years, "cov90_by_year": values, "n_by_year": counts,
            "min_cov90": min(values), "max_cov90": max(values),
            "spread": max(values) - min(values),
            "rank_trend_with_year": trend,
            "worst_year": years[int(np.argmin(values))],
        }
    return {"status": "evaluated", "artifact": str(path.name),
            "artifact_sha256": sha256_file(path), "models": out}


def mechanism_inventory(root: Path) -> list[dict]:
    """Which uncertainty mechanisms exist, and whether each is empirically validated here."""
    return [
        {"mechanism": "Monte-Carlo propagation (drag, area-to-mass, space weather)",
         "implementation": "cosmos/ai/lifetime/physics.py:predict, sample_log_am",
         "type": "aleatoric + input uncertainty",
         "output": "32 sampled decay times per object -> quantiles",
         "assumptions": "class/history area-to-mass priors; NRLMSIS density; sample count 32",
         "validated_here": "PARTIAL — interval coverage measured (see interval audit); the "
                           "sampling distribution itself is not validated against truth",
         "status": "PARTIAL"},
        {"mechanism": "Quantile regression (pinball) over 7 levels",
         "implementation": "cosmos/ai/lifetime/models.py:QUANTILES, pinball",
         "type": "aleatoric",
         "output": "7 quantiles of log10 capped lifetime",
         "assumptions": "per-quantile fits are not jointly constrained; crossing repaired by sort",
         "validated_here": "YES — empirical coverage measured per origin",
         "status": "PASS"},
        {"mechanism": "Mondrian conformalised quantile regression (CQR)",
         "implementation": "cosmos/ai/lifetime/fusion.py:MondrianCQR",
         "type": "distribution-free interval calibration",
         "output": "conformalised 80 % / 90 % intervals",
         "assumptions": "exchangeability between calibration and test; group-wise correction",
         "validated_here": "YES — empirical coverage measured per origin with launch-family "
                           "cluster intervals; see `interval_coverage` for the per-level verdicts",
         "status": "MEASURED — see interval_coverage (verdict differs by origin and level)"},
        {"mechanism": "Marginal conformal (ungrouped) variant",
         "implementation": "fusion.py, `*_marginal_conformal` arms",
         "type": "distribution-free interval calibration",
         "output": "conformalised intervals without Mondrian grouping",
         "assumptions": "exchangeability",
         "validated_here": "YES — measured alongside the Mondrian variant where the arm exists",
         "status": "MEASURED — see interval_coverage"},
        {"mechanism": "Isotonic probability calibration per horizon",
         "implementation": "cosmos/ai/twin/engine.py:M['iso'][k]",
         "type": "calibration of horizon probabilities",
         "output": "p_lifetime_{30d,90d,1yr}",
         "assumptions": "each horizon calibrated independently",
         "validated_here": "YES — and it produces a NON-COHERENT CDF for 123/13,238 objects "
                           "(limitation L17)",
         "status": "FAIL (incoherent across horizons)"},
        {"mechanism": "Isotonic survival recalibration (C2)",
         "implementation": "cosmos/ai/twin/couplings.py:survival_calibrator",
         "type": "calibration of survival-at-age",
         "output": "calibrated S(age) per object",
         "assumptions": "tune-B fragments transfer to test fragments",
         "validated_here": "YES — materially improves cloud-count error for learned experts "
                           "(Phase E C2) and not for physics-only",
         "status": "PASS"},
        {"mechanism": "Conformal p-values / BH / Simes for telemetry alarms",
         "implementation": "cosmos/ai/uncertainty.py; telemetry/alarms.py",
         "type": "multiple-testing control on alarms",
         "output": "alarm decisions at a target rate",
         "assumptions": "exchangeability of calibration and test residuals; independence "
                        "assumptions of the combining rule",
         "validated_here": "NOT IN THIS PHASE — point-level alarm rate control was checked by "
                           "tests/test_ai.py under drift; event-level coverage is not a "
                           "coverage claim",
         "status": "NOT VALIDATED (here)"},
        {"mechanism": "Model disagreement across seeds",
         "implementation": "5-seed ensembles; seeds_test.csv",
         "type": "epistemic",
         "output": "per-seed losses; ensemble mean",
         "assumptions": "seed variation approximates fitting variability only",
         "validated_here": "PARTIAL — recorded, but not propagated as an uncertainty to "
                           "downstream consumers",
         "status": "PARTIAL"},
        {"mechanism": "Missing-data handling / abstention",
         "implementation": "cosmos/ai/adapters.py; store.py; contracts.py",
         "type": "epistemic / evidence coverage",
         "output": "explicit abstention with a recorded reason",
         "assumptions": "none — absence is reported, not modelled",
         "validated_here": "YES — enforced and asserted by tests (no imputation)",
         "status": "PASS"},
        {"mechanism": "Cross-module uncertainty propagation",
         "implementation": "contracts.Uncertainty carried through adapters",
         "type": "semantic preservation",
         "output": "kind/method/level/assumptions preserved per module",
         "assumptions": "representations are not collapsed to a scalar",
         "validated_here": "PARTIAL — semantic preservation is test-enforced; no end-to-end "
                           "numerical propagation is performed because the chain's endpoints "
                           "are not joined by a shared quantity",
         "status": "PARTIAL"},
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/phase_h")
    parser.add_argument("--n-boot", type=int, default=4000)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Phase H -- empirical uncertainty audit (recomputed from saved predictions)")
    intervals, drift = {}, {}
    rows = []
    for origin in ORIGINS:
        intervals[origin] = audit_intervals(root, origin, args.n_boot)
        drift[origin] = temporal_drift(root, origin)
        if intervals[origin].get("status") != "evaluated":
            print(f"  origin {origin}: {intervals[origin].get('detail')}")
            continue
        print(f"\n  === origin {origin} "
              f"({intervals[origin]['n_objects_scored']} objects, "
              f"{intervals[origin]['n_launch_families']} launch families) ===")
        print(f"  {'model':34s} {'level':>6s} {'empirical':>10s} {'deviation':>10s} "
              f"{'95% CI':>24s}  verdict")
        for model, entry in intervals[origin]["models"].items():
            for label, record in entry.items():
                if record.get("status") != "evaluated":
                    continue
                print(f"  {model:34s} {record['nominal']:6.2f} "
                      f"{record['empirical_coverage']:10.4f} {record['deviation']:+10.4f} "
                      f"[{record['deviation_ci95_lo']:+.4f},{record['deviation_ci95_hi']:+.4f}]"
                      f"  {record['verdict']}")
                rows.append({"origin": origin, "model": model, "level": record["nominal"],
                             "empirical_coverage": record["empirical_coverage"],
                             "deviation": record["deviation"],
                             "ci95_lo": record["deviation_ci95_lo"],
                             "ci95_hi": record["deviation_ci95_hi"],
                             "p_value": record["p_value"],
                             "verdict": record["verdict"],
                             "mean_width_log10_days": record.get(
                                 "mean_interval_width_log10_days")})

    print("\n  === temporal drift of 90 % coverage ===")
    for origin, record in drift.items():
        if record.get("status") != "evaluated":
            continue
        for model, entry in record["models"].items():
            print(f"  origin {origin} {model:24s} range "
                  f"{entry['min_cov90']:.3f}-{entry['max_cov90']:.3f} "
                  f"(spread {entry['spread']:.3f}, worst {entry['worst_year']}, "
                  f"rank trend {entry['rank_trend_with_year']})")

    mechanisms = mechanism_inventory(root)
    # Attach the measured verdicts for the deployed expert so the inventory cannot drift
    # from the numbers.
    deployed = {}
    for origin, record in intervals.items():
        if record.get("status") != "evaluated":
            continue
        entry = record["models"].get("cosmos_gated", {})
        deployed[origin] = {
            label: {"empirical": value.get("empirical_coverage"),
                    "verdict": value.get("verdict")}
            for label, value in entry.items() if value.get("status") == "evaluated"
        }
    for mechanism in mechanisms:
        if mechanism["mechanism"].startswith("Mondrian"):
            mechanism["measured_deployed_expert"] = deployed
    print("\n  === mechanism inventory ===")
    for entry in mechanisms:
        print(f"  {entry['status']:38s} {entry['mechanism']}")

    record = {
        "phase": "H",
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "n_boot": args.n_boot,
        "seed": SEED,
        "method": ("per-object interval coverage recomputed from saved test predictions; "
                   "deviation from nominal bootstrapped by launch family"),
        "post_hoc": True,
        "interval_coverage": intervals,
        "temporal_drift": drift,
        "mechanism_inventory": mechanisms,
        "not_established": [
            "nominal conformal coverage is a construction-time property; this audit measures "
            "the observed coverage and they are not the same quantity",
            "coverage is measured on objects with a known five-year outcome; censored objects "
            "are excluded and their coverage is unknown",
            "telemetry alarm conformal control is not audited in this phase",
        ],
    }
    with open(out_dir / "phase_h_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)
    pd.DataFrame(rows).to_csv(out_dir / "coverage_table.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
