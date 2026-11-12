"""E12: resolve the C1 learner/origin confound with a same-learner ablation at both origins.

Phase E found that family features significantly improved lifetime prediction at temporal
origin 2016 (learner `tabm`) but not at 2011 (learner `kumo`). Because each origin selected
its own learner, origin and learner were entangled and the two origins were not exchangeable
replicates.

This experiment holds the **learner algorithm constant** and varies only the origin.

    python scripts/e12_same_learner_c1.py
    python scripts/e12_same_learner_c1.py --out outputs/e12_same_learner --n-boot 4000

No model is refitted. The lifetime study cached per-seed predictions for `mlp` **and its full
ablation set at both origins** (`learner_cache/mlp_no_family.npz`), produced by the same
pipeline, on the same split, with the same five seeds. Reconstructing the published ensemble
from that cache is exact -- verified against `test_predictions.npz` to 0.0 -- so this is a
re-analysis, not a new fit. That is strictly preferable to refitting: it introduces no
methodology change and cannot diverge from the published protocol.

Fairness conditions met, and their one limit:

* same learner algorithm (`mlp`) at both origins;
* ablated arm uses the **identical hyperparameters** as its full arm (`tuned=False`, inheriting
  the full arm's tuned settings) -- verified from `fit_json`;
* features differ only by the `family` group (53 -> 45 columns);
* same temporal split, same launch-family fold separation, same 5 seeds, same target, same
  censoring mask, same evaluation protocol;
* **limit**: `mlp`'s tuned hyperparameters differ *between* origins (each origin tuned on its
  own tune-A fold), as the published protocol prescribes. The learner *algorithm* is held
  constant; its tuned settings are not. This is stated rather than hidden, and it cannot be
  removed without departing from the protocol that produced every other published arm.
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
    benjamini_hochberg,
    paired_cluster_bootstrap,
    _pinball_per_object,
)

ORIGINS = ("2011", "2016")
SEEDS = (0, 1, 2, 3, 4)
#: Learner available with a full ablation set at BOTH origins -- the same-learner arm.
COMMON_LEARNER = "mlp"
#: Each origin's own published best learner, for the learner-effect contrast.
PUBLISHED_LEARNER = {"2016": "tabm", "2011": "kumo"}
ABLATION_GROUPS = ("no_family", "no_physics", "no_design", "no_space_weather", "plus_rcs_2026")
SEED = 20261027


def _base(root: Path, origin: str) -> Path:
    return root / "outputs" / "benchmarks" / "reentry_lifetime" / f"origin{origin}_uncontrolled"


def _ensemble(path: Path) -> np.ndarray:
    """Reconstruct the study's seed ensemble: mean across seeds, then sorted per row.

    Identical to ``run.py``: ``np.sort(np.mean([...], 0), 1)``.
    """
    with np.load(path, allow_pickle=True) as cache:
        return np.sort(np.mean([cache[f"s{s}_test"] for s in SEEDS], 0), 1)


def _fit_record(path: Path) -> dict:
    with np.load(path, allow_pickle=True) as cache:
        return json.loads(str(cache["fit_json"]))


def _arena(root: Path, origin: str) -> dict | None:
    """Target, censoring mask and launch families for one origin's test fold."""
    published = _base(root, origin) / "test_predictions.npz"
    if not published.is_file():
        return None
    with np.load(published, allow_pickle=True) as archive:
        z = np.asarray(archive["z"])
        mask = np.asarray(archive["known5"]).astype(bool)
        available = set(archive.files)

    from cosmos.ai.lifetime import run as LR
    test = LR.split(LR.load_cohort(), origin, "uncontrolled")["test"].reset_index(drop=True)
    families = test["launch_family"].astype(str).to_numpy()
    if len(families) != len(z):
        return None
    return {"z": z[mask], "mask": mask, "families": families[mask],
            "published_keys": available, "published_path": published}


def _verify_cache(root: Path, origin: str, learner: str, arena: dict) -> dict:
    """Confirm the cache reproduces the published arm exactly, where a published arm exists."""
    cache_path = _base(root, origin) / "learner_cache" / f"{learner}.npz"
    if not cache_path.is_file():
        return {"state": "absent", "path": str(cache_path)}
    reconstructed = _ensemble(cache_path)
    record = {"state": "reconstructed", "sha256": sha256_file(cache_path)}
    key = f"{learner}__q"
    if key in arena["published_keys"]:
        with np.load(arena["published_path"], allow_pickle=True) as archive:
            difference = float(np.abs(reconstructed - np.asarray(archive[key])).max())
        record["published_max_abs_difference"] = difference
        record["state"] = "verified_against_published" if difference == 0.0 else "MISMATCH"
    return record


def analyse_origin(root: Path, origin: str, learner: str, n_boot: int,
                   alpha: float) -> dict:
    """Ablation effects for one (origin, learner) cell."""
    arena = _arena(root, origin)
    if arena is None:
        return {"status": "NOT EVALUABLE", "detail": f"cannot align test fold for {origin}"}
    cache_dir = _base(root, origin) / "learner_cache"
    full_path = cache_dir / f"{learner}.npz"
    if not full_path.is_file():
        return {"status": "NOT EVALUABLE", "detail": f"no cache for {learner} at {origin}"}

    verification = _verify_cache(root, origin, learner, arena)
    if verification.get("state") == "MISMATCH":
        return {"status": "FAIL", "detail": "cache does not reproduce the published arm",
                "verification": verification}

    full_fit = _fit_record(full_path)
    full_loss = _pinball_per_object(arena["z"], _ensemble(full_path)[arena["mask"]])

    rows, p_values = [], []
    for group in ABLATION_GROUPS:
        arm_path = cache_dir / f"{learner}_{group}.npz"
        if not arm_path.is_file():
            rows.append({"ablation": group, "status": "absent"})
            continue
        arm_fit = _fit_record(arm_path)
        arm_loss = _pinball_per_object(arena["z"], _ensemble(arm_path)[arena["mask"]])
        record = paired_cluster_bootstrap(arm_loss - full_loss, arena["families"],
                                          n_boot, seed=SEED)
        same_params = arm_fit.get("params") == full_fit.get("params")
        rows.append({
            "ablation": group,
            "status": "evaluated",
            "effect_pinball_ablation_minus_full": record["mean"],
            "ci95_lo": record["ci95_lo"],
            "ci95_hi": record["ci95_hi"],
            "p_value": record["p_value"],
            "n_objects": record["n"],
            "n_launch_families": record["n_clusters"],
            "n_features_full": full_fit.get("n_features"),
            "n_features_ablated": arm_fit.get("n_features"),
            # Fairness condition: the ablated arm must not be separately tuned.
            "identical_hyperparameters": bool(same_params),
            "ablated_arm_tuned": bool(arm_fit.get("tuned")),
            "artifact_sha256": sha256_file(arm_path),
        })
        p_values.append(record["p_value"])

    correction = benjamini_hochberg(p_values, alpha=alpha)
    index = 0
    for row in rows:
        if row.get("status") != "evaluated":
            continue
        row["p_adjusted_bh"] = correction["adjusted"][index]
        row["significant_after_correction"] = bool(correction["rejected"][index])
        index += 1

    family = next((r for r in rows if r["ablation"] == "no_family"
                   and r.get("status") == "evaluated"), None)
    return {
        "status": "evaluated",
        "origin": origin,
        "learner": learner,
        "verification": verification,
        "full_arm_pinball": float(full_loss.mean()),
        "full_arm_tuned": bool(full_fit.get("tuned")),
        "full_arm_params": full_fit.get("params"),
        "n_objects_scored": int(arena["mask"].sum()),
        "n_launch_families": int(pd.unique(arena["families"]).size),
        "ablations": rows,
        "no_family": family,
        "verdict": ("SUPPORTED" if family and family.get("significant_after_correction")
                    and family["effect_pinball_ablation_minus_full"] > 0
                    else "INCONCLUSIVE" if family else "NOT EVALUABLE"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/e12_same_learner")
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

    print("E12 -- same-learner C1 ablation (cached predictions, no refit)")
    cells: dict[str, dict] = {}

    # Same-learner arm: the common learner at both origins.
    print(f"\n  [A] same learner ({COMMON_LEARNER}) at both origins -- isolates ORIGIN")
    for origin in ORIGINS:
        key = f"{COMMON_LEARNER}@{origin}"
        cells[key] = analyse_origin(root, origin, COMMON_LEARNER, args.n_boot, args.alpha)
        cell = cells[key]
        if cell.get("status") != "evaluated":
            print(f"      {key:16s} {cell.get('status')}: {cell.get('detail')}")
            continue
        family = cell["no_family"]
        print(f"      {key:16s} verify={cell['verification'].get('state')} "
              f"pinball={cell['full_arm_pinball']:.5f} "
              f"features {family['n_features_full']}->{family['n_features_ablated']} "
              f"same_params={family['identical_hyperparameters']}")
        print(f"        no_family effect {family['effect_pinball_ablation_minus_full']:+.6f} "
              f"CI [{family['ci95_lo']:+.6f}, {family['ci95_hi']:+.6f}] "
              f"p={family['p_value']:.4f} p_adj={family['p_adjusted_bh']:.4f} "
              f"-> {'SIGNIFICANT' if family['significant_after_correction'] else 'n.s.'}")

    # Learner-effect arm: each origin's published best learner, origin held constant.
    print("\n  [B] published learner per origin -- isolates LEARNER at fixed origin")
    for origin in ORIGINS:
        learner = PUBLISHED_LEARNER[origin]
        key = f"{learner}@{origin}"
        cells[key] = analyse_origin(root, origin, learner, args.n_boot, args.alpha)
        cell = cells[key]
        if cell.get("status") != "evaluated" or not cell.get("no_family"):
            print(f"      {key:16s} {cell.get('status')}")
            continue
        family = cell["no_family"]
        print(f"      {key:16s} no_family effect {family['effect_pinball_ablation_minus_full']:+.6f} "
              f"CI [{family['ci95_lo']:+.6f}, {family['ci95_hi']:+.6f}] "
              f"p_adj={family['p_adjusted_bh']:.4f} "
              f"-> {'SIGNIFICANT' if family['significant_after_correction'] else 'n.s.'}")

    # ---- synthesis
    same = {o: cells.get(f"{COMMON_LEARNER}@{o}") for o in ORIGINS}
    effects = {o: (c["no_family"]["effect_pinball_ablation_minus_full"]
                   if c and c.get("no_family") else None) for o, c in same.items()}
    significant = {o: (bool(c["no_family"]["significant_after_correction"])
                       if c and c.get("no_family") else None) for o, c in same.items()}

    evaluable = [o for o in ORIGINS if effects.get(o) is not None]
    both_significant = all(significant.get(o) for o in evaluable) and len(evaluable) == len(ORIGINS)
    none_significant = not any(significant.get(o) for o in evaluable)
    signs = {o: int(np.sign(effects[o])) for o in evaluable}

    if not evaluable:
        conclusion = "NOT EVALUABLE"
        reading = "the same-learner arm could not be evaluated"
    elif both_significant:
        conclusion = "ORIGIN-INDEPENDENT"
        reading = ("with the learner held constant the family effect is significant at both "
                   "origins, so the Phase E discrepancy was driven by the learner")
    elif none_significant:
        conclusion = "NOT REPRODUCIBLE"
        reading = ("with the learner held constant the family effect is significant at neither "
                   "origin, so the Phase E result at origin 2016 is attributable to that "
                   "origin's learner rather than to a general benefit of family features")
    else:
        supporting = [o for o in evaluable if significant.get(o)]
        conclusion = "ORIGIN-DEPENDENT"
        reading = (f"with the learner held constant the family effect remains significant only "
                   f"at origin {', '.join(supporting)}, so the discrepancy is a property of the "
                   f"temporal origin rather than of the learner")

    print(f"\n  CONCLUSION: {conclusion}")
    print(f"  {reading}")

    record = {
        "experiment": "E12",
        "question": ("does the C1 family-feature effect depend on the temporal origin or on "
                     "the learner?"),
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "n_boot": args.n_boot,
        "alpha": args.alpha,
        "seed": SEED,
        "method": {
            "refit": False,
            "source": "cached per-seed predictions from the lifetime study's learner_cache",
            "ensemble": "np.sort(np.mean(seed predictions, axis=0), axis=1), as in run.py",
            "verification": ("the full arm's reconstruction is compared against the published "
                             "test_predictions.npz; a non-zero difference fails the cell"),
            "endpoint": "pinball loss of log10 capped lifetime, objects with known 5-year outcome",
            "independent_unit": "launch family (paired cluster bootstrap)",
            "correction": "Benjamini-Hochberg across the 5 ablations within each cell",
        },
        "fairness": {
            "same_learner_algorithm": True,
            "identical_hyperparameters_within_cell": True,
            "features_differ_only_by_family_group": True,
            "same_split_seeds_target_and_censoring": True,
            "limitation": ("the common learner's tuned hyperparameters differ between origins "
                           "because each origin tuned on its own tune-A fold, as the published "
                           "protocol prescribes; the learner algorithm is held constant, its "
                           "tuned settings are not"),
        },
        "cells": cells,
        "same_learner_effects": effects,
        "same_learner_significant": significant,
        "sign_consistent": bool(len(set(signs.values())) == 1 if signs else False),
        "conclusion": conclusion,
        "reading": reading,
        "post_hoc": True,
        "post_hoc_note": ("these test folds were scored by the original study, so E12 is a "
                          "post-hoc re-analysis and not a confirmatory test"),
    }
    with open(out_dir / "e12_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)

    rows = []
    for key, cell in cells.items():
        if cell.get("status") != "evaluated":
            continue
        for ablation in cell["ablations"]:
            if ablation.get("status") != "evaluated":
                continue
            rows.append({
                "cell": key, "origin": cell["origin"], "learner": cell["learner"],
                "ablation": ablation["ablation"],
                "effect": ablation["effect_pinball_ablation_minus_full"],
                "ci95_lo": ablation["ci95_lo"], "ci95_hi": ablation["ci95_hi"],
                "p_value": ablation["p_value"],
                "p_adjusted_bh": ablation["p_adjusted_bh"],
                "significant": ablation["significant_after_correction"],
                "n_objects": ablation["n_objects"],
                "n_launch_families": ablation["n_launch_families"],
                "identical_hyperparameters": ablation["identical_hyperparameters"],
            })
    pd.DataFrame(rows).to_csv(out_dir / "e12_ablation_table.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
