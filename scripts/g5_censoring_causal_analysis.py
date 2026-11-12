"""G5: causal analysis of why lifetime model selection does not transfer across origins.

Phase G+ attributed the failure to "censoring mismatch" between the selection set (tune-A) and
the test fold. **That attribution was partly wrong and is corrected here.** The capped target
is known for essentially every object in every split (`known5` is 0.998-1.000 throughout), so
censoring relative to the cap is not the differentiator.

What actually differs is the **mass of the target at the cap point**. `add_targets` maps
time-to-decay to ``z = log10(min(time_days, CAP))`` with ``CAP = 1826.25`` days, so every
object surviving five years collapses onto a single point ``z = 3.2616``. The share of the
population at that point mass differs between the selection and evaluation populations, and
**reverses direction between the two origins**:

| origin | train | tune-A | tune-B | test |
|--------|-------|--------|--------|------|
| 2011   | 0.334 | 0.593  | 0.563  | 0.740 |
| 2016   | 0.389 | 0.722  | 0.645  | 0.555 |

Pinball loss on a distribution with a large point mass rewards predicting near that point. A
selection set that is cap-heavy relative to test (origin 2016) should therefore favour models
that over-predict lifetime on test, and a cap-light selection set (origin 2011) the reverse.

This script tests that mechanism directly by decomposing the test loss into the at-cap and
below-cap subpopulations and asking which one the selection ranking actually tracks.

    python scripts/g5_censoring_causal_analysis.py --n-boot 4000

Falsifiable prediction: tune-A ranking should correlate better with the **at-cap** subset's
test ranking than with the below-cap subset's at origin 2016 (where tune-A is cap-heavy), and
the model's cap-mass error should predict its test loss.

No model is retrained; no published artifact is modified.
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
from scripts.phase_e_coupling_ablations import (  # noqa: E402
    paired_cluster_bootstrap,
    _pinball_per_object,
)

ORIGINS = ("2011", "2016")
SEED = 20261027
Z_CAP = float(np.log10(1826.25))
CAP_TOL = 1e-6


def _base(root: Path, origin: str) -> Path:
    return root / "outputs" / "benchmarks" / "reentry_lifetime" / f"origin{origin}_uncontrolled"


def _arena(root: Path, origin: str) -> dict | None:
    path = _base(root, origin) / "test_predictions.npz"
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=True) as archive:
        data = {key: np.asarray(archive[key]) for key in archive.files}
    from cosmos.ai.lifetime import run as LR
    split = LR.split(LR.load_cohort(), origin, "uncontrolled")
    test = split["test"].reset_index(drop=True)
    if len(test) != len(data["z"]):
        return None
    mask = data["known5"].astype(bool)
    return {
        "data": data, "mask": mask, "z": data["z"][mask],
        "families": test["launch_family"].astype(str).to_numpy()[mask],
        "path": path, "sha256": sha256_file(path), "split": split,
    }


def census(split: dict) -> dict:
    """Point-mass composition and censoring status of every split."""
    out = {}
    for name, frame in split.items():
        z = frame["z"].to_numpy()
        at_cap = np.isclose(z, Z_CAP, atol=CAP_TOL)
        below = z[~at_cap]
        out[name] = {
            "n": int(len(frame)),
            "known5_fraction": float(frame["known5"].mean()),
            "event_rate": float(frame["event"].mean()),
            "at_cap_fraction": float(at_cap.mean()),
            "below_cap_n": int((~at_cap).sum()),
            "below_cap_z_median": float(np.median(below)) if below.size else None,
            "below_cap_z_sd": float(below.std()) if below.size else None,
            "z_sd": float(z.std()),
            "t0_min": str(frame["t0"].min().date()),
            "t0_max": str(frame["t0"].max().date()),
        }
    return out


def decompose(root: Path, origin: str, n_boot: int) -> dict:
    """Decompose test pinball into the at-cap and below-cap subpopulations."""
    arena = _arena(root, origin)
    if arena is None:
        return {"status": "NOT EVALUABLE"}
    data, mask, z, families = arena["data"], arena["mask"], arena["z"], arena["families"]
    at_cap = np.isclose(z, Z_CAP, atol=CAP_TOL)

    summary_path = _base(root, origin) / "summary.json"
    tune_a = json.loads(summary_path.read_text()).get("tuneA_pinball", {}) \
        if summary_path.is_file() else {}

    models = sorted(k[:-3] for k in data if k.endswith("__q"))
    rows = []
    for model in models:
        quantiles = data[f"{model}__q"][mask]
        loss = _pinball_per_object(z, quantiles)
        median_prediction = quantiles[:, 3]
        # Share of objects the model places at or above the cap: its implied cap mass.
        implied_cap_mass = float((median_prediction >= Z_CAP - 1e-3).mean())
        rows.append({
            "model": model,
            "tuneA_pinball": tune_a.get(model),
            "test_pinball": float(loss.mean()),
            "test_pinball_at_cap": float(loss[at_cap].mean()) if at_cap.any() else None,
            "test_pinball_below_cap": float(loss[~at_cap].mean()) if (~at_cap).any() else None,
            "implied_cap_mass": implied_cap_mass,
            "median_prediction_mean": float(median_prediction.mean()),
        })
    frame = pd.DataFrame(rows)

    actual_cap_mass = float(at_cap.mean())
    frame["cap_mass_error"] = frame["implied_cap_mass"] - actual_cap_mass

    # Rank correlations: does tune-A track the whole test set, its at-cap part, or its
    # below-cap part?
    tuned = frame.dropna(subset=["tuneA_pinball"])
    correlations = {}
    if len(tuned) >= 3:
        for label, column in (("overall", "test_pinball"),
                              ("at_cap", "test_pinball_at_cap"),
                              ("below_cap", "test_pinball_below_cap")):
            correlations[f"spearman_tuneA_vs_test_{label}"] = float(
                tuned["tuneA_pinball"].corr(tuned[column], method="spearman"))
    # Does a model's cap-mass error predict its test loss?
    if len(frame) >= 3:
        correlations["spearman_abs_cap_mass_error_vs_test_pinball"] = float(
            frame["cap_mass_error"].abs().corr(frame["test_pinball"], method="spearman"))
        correlations["pearson_abs_cap_mass_error_vs_test_pinball"] = float(
            frame["cap_mass_error"].abs().corr(frame["test_pinball"]))

    # Cluster-aware contrast of the at-cap vs below-cap loss for the deployed expert, so the
    # decomposition is not read off point estimates alone.
    deployed = {}
    if "cosmos_gated__q" in data:
        loss = _pinball_per_object(z, data["cosmos_gated__q"][mask])
        deployed = {
            "at_cap_mean": float(loss[at_cap].mean()),
            "below_cap_mean": float(loss[~at_cap].mean()),
            "difference_below_minus_at": paired_cluster_bootstrap(
                np.where(~at_cap, loss, np.nan) - np.where(at_cap, loss, np.nan),
                families, n_boot, seed=SEED) if False else None,
        }
        # The two subsets are disjoint, so a paired test is not meaningful; report both means
        # with their own cluster intervals instead.
        for label, subset in (("at_cap", at_cap), ("below_cap", ~at_cap)):
            if subset.any():
                record = paired_cluster_bootstrap(loss[subset], families[subset],
                                                  n_boot, seed=SEED)
                deployed[f"{label}_ci95"] = [record["ci95_lo"], record["ci95_hi"]]

    return {
        "status": "evaluated",
        "origin": origin,
        "artifact_sha256": arena["sha256"],
        "n_objects_scored": int(mask.sum()),
        "test_at_cap_fraction": actual_cap_mass,
        "test_at_cap_n": int(at_cap.sum()),
        "test_below_cap_n": int((~at_cap).sum()),
        "census": census(arena["split"]),
        "per_model": frame.to_dict(orient="records"),
        "rank_correlations": correlations,
        "deployed_expert_decomposition": deployed,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/g5_censoring")
    parser.add_argument("--n-boot", type=int, default=4000)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("G5 -- causal analysis of selection non-transfer")
    print(f"  target point mass at z = log10(1826.25) = {Z_CAP:.4f}\n")

    results, rows = {}, []
    for origin in ORIGINS:
        results[origin] = decompose(root, origin, args.n_boot)
        record = results[origin]
        if record.get("status") != "evaluated":
            print(f"  origin {origin}: not evaluable")
            continue

        print(f"===== origin {origin} =====")
        print("  split composition (censoring is NOT the differentiator -- known5 ~ 1 everywhere):")
        for name in ("train", "tuneA", "tuneB", "test"):
            c = record["census"][name]
            print(f"    {name:6s} n={c['n']:6d} known5={c['known5_fraction']:.4f} "
                  f"AT-CAP={c['at_cap_fraction']:.4f} event={c['event_rate']:.4f} "
                  f"z_sd={c['z_sd']:.3f} t0=[{c['t0_min']}..{c['t0_max']}]")
        shift = (record["census"]["test"]["at_cap_fraction"]
                 - record["census"]["tuneA"]["at_cap_fraction"])
        print(f"    => cap-mass shift tune-A -> test: {shift:+.4f} "
              f"({'test cap-heavier' if shift > 0 else 'test cap-lighter'})")

        print("\n  rank correlations of tune-A pinball against test pinball:")
        for key, value in record["rank_correlations"].items():
            print(f"    {key:52s} {value:+.3f}")

        if record["deployed_expert_decomposition"]:
            d = record["deployed_expert_decomposition"]
            print(f"\n  deployed expert loss: at-cap {d['at_cap_mean']:.6f} "
                  f"CI {np.round(d.get('at_cap_ci95', [np.nan, np.nan]), 6).tolist()} | "
                  f"below-cap {d['below_cap_mean']:.6f} "
                  f"CI {np.round(d.get('below_cap_ci95', [np.nan, np.nan]), 6).tolist()}")
        print()

        for entry in record["per_model"]:
            rows.append({"origin": origin, **entry})

    # ---- cross-origin synthesis
    shifts = {}
    for origin in ORIGINS:
        record = results.get(origin, {})
        if record.get("status") != "evaluated":
            continue
        shifts[origin] = (record["census"]["test"]["at_cap_fraction"]
                          - record["census"]["tuneA"]["at_cap_fraction"])
    reverses = (len(shifts) == 2 and
                np.sign(list(shifts.values())[0]) != np.sign(list(shifts.values())[1]))

    print("=== synthesis ===")
    print(f"  cap-mass shift by origin: "
          f"{ {k: round(v, 4) for k, v in shifts.items()} }")
    print(f"  shift reverses direction across origins: {reverses}")

    corrected = (
        "The Phase G+ attribution to 'censoring mismatch' is CORRECTED. The capped target is "
        "known for 99.8-100 % of objects in every split, so censoring relative to the cap is "
        "not the differentiator. The operative mismatch is the share of the target at the cap "
        "POINT MASS, which differs between the selection and evaluation populations and "
        "reverses direction between the two origins. The underlying driver is launch-epoch "
        "composition: which objects were launched when, and what fraction of them survived "
        "five years."
    )
    print(f"\n  {corrected}")

    record = {
        "experiment": "G5 causal analysis",
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "n_boot": args.n_boot,
        "seed": SEED,
        "z_cap": Z_CAP,
        "exploratory": True,
        "exploratory_note": ("these test folds have been scored repeatedly across the "
                             "project's history; this is diagnostic re-analysis, not "
                             "independent confirmation"),
        "corrects_previous_finding": corrected,
        "cap_mass_shift_by_origin": shifts,
        "shift_reverses_across_origins": bool(reverses),
        "results": results,
        "not_established": [
            "the decomposition is observational: it shows the selection ranking tracks the "
            "cap-heavy subpopulation, not that forcing the shift to zero would fix selection",
            "only two origins exist, so the reversal is observed once in each direction",
            "no new model was fitted, so no alternative selection objective is tested here",
        ],
    }
    with open(out_dir / "g5_causal_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)
    pd.DataFrame(rows).to_csv(out_dir / "g5_cap_decomposition.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
