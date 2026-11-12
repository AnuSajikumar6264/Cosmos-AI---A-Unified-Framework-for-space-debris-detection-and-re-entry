"""G5d analysis: evaluate the pre-registered hypotheses at the unexamined origin 2006.

Reads the pre-registration, refuses to run if it changed, and evaluates H1/H2/H3 exactly as
specified there. The outcome is classified by the pre-registered table, not by inspection.

    python scripts/g5d_analyse.py --n-boot 4000

Deviations from the pre-registered arm set are recorded in
``research_design/G5D_DEVIATIONS.md`` and are reflected in the power statements below.
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
from scripts.g5d_origin2006_refit import ORIGIN_KEY, ORIGIN_SPLIT, check_preregistration  # noqa: E402

Z_CAP = float(np.log10(1826.25))
SEED = 20261027

#: Arms present in the published caches at 2011/2016 AND fittable at 2006 (see deviation log).
COMMON_ARMS = ("physics_only", "xgboost", "mlp", "tabm")
#: Learners only (physics_only has no tune-A selection score of the same kind).
COMMON_LEARNERS = ("xgboost", "mlp", "tabm")

PUBLISHED = {
    "2011": "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled",
    "2016": "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled",
}
NEW = "outputs/g5d_origin2006/lifetime"

#: Pre-registered thresholds.
H1_NO_ASSOCIATION = 0.5      # |rho| < 0.5 supports H1
H1_REFUTES = 0.7             # rho >= 0.7 refutes H1
H2_MIN_PHYSICS_RANGE = 3     # physics_only rank must vary by >= 3 positions
H3_CONFIRMS = 0.5            # rho >= +0.5 confirms H3
H3_MIN_ARMS = 5              # below this a rank correlation cannot confirm


def _arena(root: Path, origin: str, directory: str) -> dict | None:
    path = root / directory / "test_predictions.npz"
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=True) as archive:
        data = {k: np.asarray(archive[k]) for k in archive.files}
    from cosmos.ai.lifetime import run as LR
    if origin not in LR.ORIGINS:
        LR.ORIGINS[origin] = ORIGIN_SPLIT
    test = LR.split(LR.load_cohort(), origin, "uncontrolled")["test"].reset_index(drop=True)
    if len(test) != len(data["z"]):
        return None
    mask = data["known5"].astype(bool)
    summary = root / directory / "summary.json"
    tune_a = json.loads(summary.read_text()).get("tuneA_pinball", {}) if summary.is_file() else {}
    return {"data": data, "mask": mask, "z": data["z"][mask],
            "families": test["launch_family"].astype(str).to_numpy()[mask],
            "tuneA_pinball": tune_a, "sha256": sha256_file(path),
            "artifact": str(path.relative_to(root))}


def evaluate(root: Path, n_boot: int) -> dict:
    arenas = {}
    for origin, directory in list(PUBLISHED.items()) + [(ORIGIN_KEY, NEW)]:
        arena = _arena(root, origin, directory)
        if arena is not None:
            arenas[origin] = arena

    if ORIGIN_KEY not in arenas:
        return {"outcome": "NOT_EVALUABLE",
                "detail": f"origin {ORIGIN_KEY} predictions are absent; the refit did not "
                          "produce test_predictions.npz"}

    # ---- per-origin pinball for the common arm set
    per_origin = {}
    for origin, arena in arenas.items():
        data, mask, z, families = arena["data"], arena["mask"], arena["z"], arena["families"]
        at_cap = np.isclose(z, Z_CAP, atol=1e-6)
        rows = []
        for arm in COMMON_ARMS:
            key = f"{arm}__q"
            if key not in data:
                rows.append({"arm": arm, "status": "absent"})
                continue
            quantiles = data[key][mask]
            loss = _pinball_per_object(z, quantiles)
            median = quantiles[:, 3]
            rows.append({
                "arm": arm, "status": "ok",
                "test_pinball": float(loss.mean()),
                "tuneA_pinball": arena["tuneA_pinball"].get(arm),
                "implied_cap_mass": float((median >= Z_CAP - 1e-3).mean()),
            })
        frame = pd.DataFrame([r for r in rows if r.get("status") == "ok"])
        if frame.empty:
            continue
        frame["rank"] = frame["test_pinball"].rank().astype(int)
        actual_cap_mass = float(at_cap.mean())
        frame["cap_mass_error"] = frame["implied_cap_mass"] - actual_cap_mass
        per_origin[origin] = {
            "artifact": arena["artifact"], "artifact_sha256": arena["sha256"],
            "n_objects_scored": int(mask.sum()),
            "n_launch_families": int(pd.unique(families).size),
            "test_at_cap_fraction": actual_cap_mass,
            "arms": frame.to_dict(orient="records"),
            "ranks": dict(zip(frame["arm"], frame["rank"].astype(int))),
            "best_arm": frame.sort_values("test_pinball")["arm"].iloc[0],
        }

    # ---- H1: selection transfer at origin 2006
    new = per_origin.get(ORIGIN_KEY, {})
    learner_frame = pd.DataFrame([a for a in new.get("arms", [])
                                  if a["arm"] in COMMON_LEARNERS
                                  and a.get("tuneA_pinball") is not None])
    h1 = {"hypothesis": "selection on tune-A carries no rank information about forward test",
          "n_learners": int(len(learner_frame))}
    if len(learner_frame) >= 3:
        rho = float(learner_frame["tuneA_pinball"].corr(learner_frame["test_pinball"],
                                                        method="spearman"))
        h1.update({
            "spearman_tuneA_vs_test": rho,
            "supports_h1": bool(abs(rho) < H1_NO_ASSOCIATION),
            "refutes_h1": bool(rho >= H1_REFUTES),
            "verdict": ("REFUTED" if rho >= H1_REFUTES
                        else "SUPPORTED" if abs(rho) < H1_NO_ASSOCIATION
                        else "AMBIGUOUS"),
            "power_note": (f"only {len(learner_frame)} learners available (deviation 1); a "
                           "Spearman correlation on this few points is very weakly powered"),
        })
    else:
        h1.update({"verdict": "NOT_EVALUABLE",
                   "power_note": "fewer than 3 learners with a tune-A score"})

    # ---- H2: ranking instability across origins, identical arm set
    rank_table = pd.DataFrame({o: r["ranks"] for o, r in per_origin.items()})
    h2 = {"hypothesis": "model ranking is unstable across temporal origins",
          "origins": list(rank_table.columns),
          "rank_table": rank_table.to_dict()}
    if len(rank_table.columns) >= 2:
        # Only arms present at EVERY origin can speak to rank stability. An arm that could
        # not be fitted at one origin (e.g. tabm at 2006, backend unavailable) would otherwise
        # look "constant" on the strength of its two surviving observations.
        complete = [arm for arm in rank_table.index if rank_table.loc[arm].notna().all()]
        incomplete = [arm for arm in rank_table.index if arm not in complete]
        h2["arms_present_at_every_origin"] = complete
        h2["arms_excluded_incomplete"] = incomplete
        constant = [arm for arm in complete
                    if rank_table.loc[arm].nunique(dropna=True) == 1]
        physics_range = (int(rank_table.loc["physics_only"].max()
                             - rank_table.loc["physics_only"].min())
                         if "physics_only" in rank_table.index else None)
        h2.update({
            "arms_with_identical_rank_everywhere": constant,
            "physics_only_rank_range": physics_range,
            "best_arm_by_origin": {o: r["best_arm"] for o, r in per_origin.items()},
            "supports_h2": bool(not constant and (physics_range or 0) >= H2_MIN_PHYSICS_RANGE),
            "verdict": ("SUPPORTED"
                        if not constant and (physics_range or 0) >= H2_MIN_PHYSICS_RANGE
                        else "REFUTED" if constant else "AMBIGUOUS"),
        })
    else:
        h2["verdict"] = "NOT_EVALUABLE"

    # ---- H3: does cap-mass error predict test loss at origin 2006?
    h3 = {"hypothesis": "point-mass composition shift predicts test loss",
          "prediction": "positive and >= +0.5 at origin 2006 (shift +0.267, same sign as 2011)"}
    frame = pd.DataFrame(new.get("arms", []))
    if len(frame) >= 3:
        rho = float(frame["cap_mass_error"].abs().corr(frame["test_pinball"], method="spearman"))
        # A Spearman correlation needs enough arms to be informative. With 3 arms the
        # maximum value 1.0 arises by chance with probability 1/6 under random ordering, so a
        # numerical pass cannot license a confirmation. The pre-registration forbids upgrading
        # the novelty claim on one favourable statistic; this encodes that.
        underpowered = len(frame) < H3_MIN_ARMS
        if rho <= 0:
            verdict = "FALSIFIED"
        elif underpowered:
            verdict = "UNDERPOWERED"
        elif rho >= H3_CONFIRMS:
            verdict = "CONFIRMED"
        else:
            verdict = "WEAK"
        h3.update({
            "spearman_abs_cap_mass_error_vs_test_pinball": rho,
            "n_arms": int(len(frame)),
            "min_arms_for_confirmation": H3_MIN_ARMS,
            "underpowered": bool(underpowered),
            "confirms_h3": bool(verdict == "CONFIRMED"),
            "falsifies_h3": bool(rho <= 0),
            "verdict": verdict,
            "power_note": (
                f"{len(frame)} arms; a Spearman correlation needs at least {H3_MIN_ARMS} arms "
                "to be informative. With 3 arms rho = 1.0 occurs with probability 1/6 under "
                "random ordering, so a numerical pass is not evidence."),
        })
    else:
        h3["verdict"] = "NOT_EVALUABLE"

    # ---- pre-registered outcome classification
    h1_ok = h1.get("verdict") == "SUPPORTED"
    h2_ok = h2.get("verdict") == "SUPPORTED"
    if h1.get("verdict") == "NOT_EVALUABLE" or h2.get("verdict") == "NOT_EVALUABLE":
        outcome = "INCONCLUSIVE"
    elif h1_ok and h2_ok and h3.get("verdict") == "CONFIRMED":
        outcome = "CONFIRMED"
    elif h1_ok and h2_ok and h3.get("verdict") in ("WEAK", "UNDERPOWERED"):
        outcome = "PARTIALLY_SUPPORTED"
    elif h1_ok and h2_ok and h3.get("verdict") == "FALSIFIED":
        outcome = "NOT_CONFIRMED"
    else:
        outcome = "INCONCLUSIVE"

    return {
        "outcome": outcome,
        "per_origin": per_origin,
        "H1": h1, "H2": h2, "H3": h3,
        "arm_set_used": list(COMMON_ARMS),
        "deviation_log": "research_design/G5D_DEVIATIONS.md",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/g5d_origin2006/analysis")
    parser.add_argument("--n-boot", type=int, default=4000)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    record = check_preregistration(root)
    print(f"pre-registration verified: {record['sha256'][:16]}...")

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    result = evaluate(root, args.n_boot)
    if result["outcome"] == "NOT_EVALUABLE":
        print(f"\nOUTCOME: NOT_EVALUABLE -- {result.get('detail')}")
    else:
        print("\n=== per-origin pinball, identical arm set ===")
        for origin, entry in result["per_origin"].items():
            print(f"\n  origin {origin} (n={entry['n_objects_scored']}, "
                  f"{entry['n_launch_families']} families, "
                  f"test at-cap {entry['test_at_cap_fraction']:.3f})")
            for arm in sorted(entry["arms"], key=lambda a: a["test_pinball"]):
                tune = arm.get("tuneA_pinball")
                tune_text = f"{tune:.6f}" if tune is not None else "    n/a"
                print(f"    {arm['arm']:14s} rank {arm['rank']}  test {arm['test_pinball']:.6f}"
                      f"  tuneA {tune_text}  cap_mass_err {arm['cap_mass_error']:+.3f}")

        print("\n=== pre-registered hypotheses ===")
        h1 = result["H1"]
        print(f"  H1 {h1['verdict']:12s} "
              f"Spearman(tuneA, test) at origin {ORIGIN_KEY} = "
              f"{h1.get('spearman_tuneA_vs_test', float('nan')):+.4f} "
              f"(n={h1.get('n_learners')})")
        print(f"     {h1.get('power_note', '')}")
        h2 = result["H2"]
        print(f"  H2 {h2['verdict']:12s} identical-rank arms: "
              f"{h2.get('arms_with_identical_rank_everywhere')}; "
              f"physics_only rank range = {h2.get('physics_only_rank_range')}")
        print(f"     best arm by origin: {h2.get('best_arm_by_origin')}")
        h3 = result["H3"]
        print(f"  H3 {h3['verdict']:12s} "
              f"Spearman(|cap-mass error|, test) = "
              f"{h3.get('spearman_abs_cap_mass_error_vs_test_pinball', float('nan')):+.4f} "
              f"(n={h3.get('n_arms')} arms)")
        print(f"\n  OUTCOME (pre-registered classification): {result['outcome']}")

    payload = {
        "experiment": "G5d analysis",
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "preregistration_sha256": record["sha256"],
        "confirmatory": True,
        "confirmatory_basis": ("origin 2006's test fold had never been constructed or scored "
                               "before the G5d refit"),
        "n_boot": args.n_boot, "seed": SEED,
        **result,
    }
    with open(out_dir / "g5d_analysis.json", "w") as stream:
        json.dump(payload, stream, indent=2, default=str)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
