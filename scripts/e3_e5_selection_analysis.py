"""E3 + E5: selection regret, and a correct reference distribution for ranking instability.

Both analyses read archived per-object predictions only. **No model is refitted, no frozen
artifact is modified, and no pre-registered outcome is changed.**

    python scripts/e3_e5_selection_analysis.py --out outputs/e3_e5 --n-boot 4000

**E5 — selection regret.** Rank correlation says whether the selection ordering carries rank
information. Regret says what following it costs. For a candidate set ``A`` with tune-A losses
``L_v`` and test losses ``L_t``, the selected arm is ``a_hat = argmin L_v(a)`` and

    regret = L_t(a_hat) - min_a L_t(a)

reported absolutely and as a percentage of the best achievable loss. Three candidate sets are
reported because the answer depends on what the practitioner was choosing between.

**E3 — reference distribution for the ranking-instability criterion.** The pre-registered G5d H2
criterion is met by chance with probability 0.1985 under *independent uniform random* rankings
(exact enumeration over all 4!x4!x3! = 3456 configurations; reproduced here). That null asks
"could pure chance do this?". The scientifically apt question is different: *could sampling noise
around a stable underlying ordering do this?* This script answers it by resampling launch families
within each origin's test fold, holding the fitted arms fixed, recomputing ranks per resample, and
reporting how often the criterion is met. That bootstrap frequency is the correct reference.

Neither analysis alters the recorded H2 verdict, which stands as pre-registered.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

SEED = 20261027
Z_CAP = float(np.log10(1826.25))

ORIGINS = {
    "2011": "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled",
    "2016": "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled",
    "2006": "outputs/g5d_origin2006/lifetime",
}
ORIGIN_2006_SPLIT = ("1999-01-01", "2001-01-01", "2006-01-01", "2011-01-01")

#: Arms used for the H2 instability criterion, as in the pre-registered analysis.
COMMON_ARMS = ("physics_only", "xgboost", "mlp", "tabm")
H2_MIN_PHYSICS_RANGE = 3


def pinball_per_object(z: np.ndarray, q: np.ndarray) -> np.ndarray:
    from cosmos.ai.lifetime import models as MO
    d = z[:, None] - q
    return np.mean(np.maximum(MO.QUANTILES * d, (MO.QUANTILES - 1) * d), axis=1)


def load_origin(root: Path, origin: str) -> dict | None:
    directory = root / ORIGINS[origin]
    npz = directory / "test_predictions.npz"
    if not npz.is_file():
        return None
    with np.load(npz, allow_pickle=True) as archive:
        data = {k: np.asarray(archive[k]) for k in archive.files}

    from cosmos.ai.lifetime import run as LR
    if origin not in LR.ORIGINS:
        LR.ORIGINS[origin] = ORIGIN_2006_SPLIT
    test = LR.split(LR.load_cohort(), origin, "uncontrolled")["test"].reset_index(drop=True)
    if len(test) != len(data["z"]):
        raise SystemExit(f"origin {origin}: split length {len(test)} != archive {len(data['z'])}")

    mask = data["known5"].astype(bool)
    z = data["z"][mask]
    families = test["launch_family"].astype(str).to_numpy()[mask]
    losses = {k[:-3]: pinball_per_object(z, data[k][mask])
              for k in data if k.endswith("__q")}

    summary = directory / "summary.json"
    record = json.loads(summary.read_text()) if summary.is_file() else {}
    return {"z": z, "families": families, "losses": losses,
            "tuneA": record.get("tuneA_pinball", {}) or {},
            "selection_pool": record.get("selection_pool") or [],
            "selected": record.get("best_learner_on_tuneA"),
            "n_scored": int(mask.sum()), "n_families": int(pd.unique(families).size),
            "artifact": str(npz.relative_to(root)), "sha256": sha256_file(npz)}


# ------------------------------------------------------------------------------- E5
def selection_regret(arena: dict) -> dict:
    """Test-loss penalty for following the tune-A selection rule."""
    test = {a: float(v.mean()) for a, v in arena["losses"].items()}
    tune = {a: float(v) for a, v in arena["tuneA"].items() if v is not None and np.isfinite(v)}

    sets = {
        "learners_with_tuneA_score": sorted(tune),
        "deployed_selection_pool": [a for a in arena["selection_pool"] if a in tune],
        "all_point_forecast_arms": sorted(a for a in test if "conformal" not in a),
    }
    out = {}
    for name, candidates in sets.items():
        scored = [a for a in candidates if a in test]
        selectable = [a for a in scored if a in tune]
        if not selectable:
            out[name] = {"status": "no arm in this set carries a tune-A score"}
            continue
        chosen = min(selectable, key=lambda a: tune[a])
        best = min(scored, key=lambda a: test[a])
        regret = test[chosen] - test[best]
        # Oracle-relative position of the chosen arm.
        order = sorted(scored, key=lambda a: test[a])
        out[name] = {
            "n_candidates": len(scored),
            "n_selectable_on_tuneA": len(selectable),
            "selected_arm": chosen,
            "selected_test_loss": test[chosen],
            "best_arm_on_test": best,
            "best_test_loss": test[best],
            "regret_absolute": regret,
            "regret_percent_of_best": 100.0 * regret / test[best],
            "selected_arm_test_rank": order.index(chosen) + 1,
            "worst_case_regret_in_set": max(test[a] for a in scored) - test[best],
            "regret_as_fraction_of_worst_case":
                (regret / (max(test[a] for a in scored) - test[best]))
                if max(test[a] for a in scored) > test[best] else 0.0,
        }
    return out


def regret_bootstrap(arena: dict, candidates: list[str], n_boot: int, seed: int) -> dict:
    """Cluster-bootstrap interval for the regret of the tune-A rule.

    Selection is held fixed (tune-A is a separate split and is not resampled); the *test* fold is
    resampled by launch family, so the interval reflects test-set uncertainty in the penalty.
    """
    tune = {a: float(v) for a, v in arena["tuneA"].items()
            if v is not None and np.isfinite(v) and a in arena["losses"]}
    scored = [a for a in candidates if a in arena["losses"]]
    selectable = [a for a in scored if a in tune]
    if not selectable or len(scored) < 2:
        return {"status": "insufficient arms"}
    chosen = min(selectable, key=lambda a: tune[a])

    families = arena["families"]
    groups = pd.unique(families)
    index = {g: np.flatnonzero(families == g) for g in groups}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        picked = rng.choice(groups, size=len(groups), replace=True)
        rows = np.concatenate([index[g] for g in picked])
        means = {a: float(arena["losses"][a][rows].mean()) for a in scored}
        draws.append(means[chosen] - min(means.values()))
    draws = np.asarray(draws)
    return {"selected_arm": chosen, "n_boot": n_boot,
            "regret_mean": float(draws.mean()),
            "regret_ci95": [float(np.percentile(draws, 2.5)),
                            float(np.percentile(draws, 97.5))],
            "fraction_of_resamples_with_zero_regret": float((draws <= 1e-12).mean())}


# ------------------------------------------------------------------------------- E3
def h2_criterion(ranks: dict[str, dict[str, int]]) -> dict:
    """The pre-registered H2 criterion, evaluated on a rank table.

    Met when (a) no arm present at *every* origin holds the same rank everywhere, and
    (b) physics_only's rank range across origins is >= 3.
    """
    table = pd.DataFrame(ranks)
    complete = [a for a in table.index if table.loc[a].notna().all()]
    constant = [a for a in complete if table.loc[a].nunique(dropna=True) == 1]
    if "physics_only" in table.index:
        row = table.loc["physics_only"].dropna()
        physics_range = int(row.max() - row.min()) if len(row) else 0
    else:
        physics_range = 0
    met = (not constant) and physics_range >= H2_MIN_PHYSICS_RANGE
    return {"met": bool(met), "constant_arms": constant,
            "physics_only_rank_range": physics_range,
            "arms_present_at_every_origin": complete}


def exact_uniform_null() -> dict:
    """Exact enumeration of the H2 criterion under independent uniform random rankings.

    Arms 0,1,2 present at all three origins; arm 3 only at 2011 and 2016. Origin arm counts
    4 / 4 / 3. All 4! x 4! x 3! = 3456 configurations are equiprobable under the null.
    """
    total = clause1 = clause2 = both = 0
    for a in permutations(range(1, 5)):
        for b in permutations(range(1, 5)):
            for c in permutations(range(1, 4)):
                total += 1
                no_const = not any(a[i] == b[i] == c[i] for i in range(3))
                rng = max(a[0], b[0], c[0]) - min(a[0], b[0], c[0])
                clause1 += no_const
                clause2 += rng >= H2_MIN_PHYSICS_RANGE
                both += no_const and (rng >= H2_MIN_PHYSICS_RANGE)
    return {"configurations": total,
            "p_no_arm_retains_rank": clause1 / total,
            "p_physics_range_ge_3": clause2 / total,
            "p_criterion_met": both / total,
            "h3_closure_threshold": 1 / 6,
            "note": "exact enumeration, not Monte Carlo"}


def stability_bootstrap(arenas: dict, n_boot: int, seed: int) -> dict:
    """Bootstrap reference distribution for the H2 criterion.

    The arms are held fixed; each origin's test fold is resampled by launch family. Under this
    reference the arms *do* have whatever stable quality ordering the fitted models possess, so the
    criterion's frequency measures how often sampling noise alone reproduces the observed
    instability. This is the null the uniform-permutation calculation cannot express.
    """
    prepared = {}
    for origin, arena in arenas.items():
        arms = [a for a in COMMON_ARMS if a in arena["losses"]]
        families = arena["families"]
        groups = pd.unique(families)
        prepared[origin] = {"arms": arms, "groups": groups,
                            "index": {g: np.flatnonzero(families == g) for g in groups},
                            "losses": arena["losses"]}

    rng = np.random.default_rng(seed)
    met = 0
    ranges: list[int] = []
    constant_counts: list[int] = []
    for _ in range(n_boot):
        ranks = {}
        for origin, prep in prepared.items():
            picked = rng.choice(prep["groups"], size=len(prep["groups"]), replace=True)
            rows = np.concatenate([prep["index"][g] for g in picked])
            means = {a: float(prep["losses"][a][rows].mean()) for a in prep["arms"]}
            order = pd.Series(means).rank().astype(int)
            ranks[origin] = order.to_dict()
        verdict = h2_criterion(ranks)
        met += verdict["met"]
        ranges.append(verdict["physics_only_rank_range"])
        constant_counts.append(len(verdict["constant_arms"]))
    ranges_arr = np.asarray(ranges)
    return {
        "n_boot": n_boot,
        "p_criterion_met_under_sampling_noise": met / n_boot,
        "physics_only_rank_range": {
            "mean": float(ranges_arr.mean()),
            "p_ge_3": float((ranges_arr >= H2_MIN_PHYSICS_RANGE).mean()),
            "distribution": {int(k): int(v) for k, v in
                             zip(*np.unique(ranges_arr, return_counts=True))}},
        "mean_n_rank_constant_arms": float(np.mean(constant_counts)),
        "interpretation": (
            "frequency with which the pre-registered H2 criterion is met when the fitted arms are "
            "held fixed and only the test folds are resampled. A high frequency means the observed "
            "instability is reproduced by sampling noise alone and is therefore weak evidence; a "
            "low frequency means the observed instability exceeds sampling noise."),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/e3_e5")
    parser.add_argument("--n-boot", type=int, default=4000)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    arenas = {}
    for origin in ORIGINS:
        arena = load_origin(root, origin)
        if arena is None:
            print(f"origin {origin}: archive absent, skipped")
            continue
        arenas[origin] = arena
        print(f"origin {origin}: {arena['n_scored']} scored objects, "
              f"{arena['n_families']} launch families, {len(arena['losses'])} arms")

    # ---------------------------------------------------------------- E5
    print("\n" + "=" * 78)
    print("E5 - SELECTION REGRET: what following the tune-A rule costs on the test fold")
    print("=" * 78)
    e5 = {}
    for origin, arena in arenas.items():
        e5[origin] = {"regret": selection_regret(arena)}
        print(f"\n--- origin {origin}")
        for name, rec in e5[origin]["regret"].items():
            if "status" in rec:
                print(f"  {name:28s} {rec['status']}")
                continue
            print(f"  {name:28s} n={rec['n_candidates']:2d}  "
                  f"selected={rec['selected_arm']:12s} (test rank {rec['selected_arm_test_rank']})")
            print(f"  {'':28s} loss {rec['selected_test_loss']:.6f} vs best "
                  f"{rec['best_test_loss']:.6f} ({rec['best_arm_on_test']})")
            print(f"  {'':28s} REGRET {rec['regret_absolute']:+.6f} "
                  f"= {rec['regret_percent_of_best']:+.2f} % of best; "
                  f"{100 * rec['regret_as_fraction_of_worst_case']:.1f} % of worst-case")
        pool = [a for a in arena["selection_pool"] if a in arena["losses"]] or \
               sorted(a for a in arena["tuneA"] if a in arena["losses"])
        boot = regret_bootstrap(arena, pool, args.n_boot, SEED)
        e5[origin]["bootstrap_deployed_pool"] = boot
        if "status" not in boot:
            print(f"  cluster bootstrap ({boot['n_boot']} draws, deployed pool): "
                  f"regret {boot['regret_mean']:+.6f} "
                  f"95% CI [{boot['regret_ci95'][0]:+.6f}, {boot['regret_ci95'][1]:+.6f}]; "
                  f"zero-regret in {100 * boot['fraction_of_resamples_with_zero_regret']:.1f} % of resamples")

    # ---------------------------------------------------------------- E3
    print("\n" + "=" * 78)
    print("E3 - REFERENCE DISTRIBUTION for the pre-registered H2 instability criterion")
    print("=" * 78)
    observed_ranks = {}
    for origin, arena in arenas.items():
        arms = [a for a in COMMON_ARMS if a in arena["losses"]]
        means = {a: float(arena["losses"][a].mean()) for a in arms}
        observed_ranks[origin] = pd.Series(means).rank().astype(int).to_dict()
    observed = h2_criterion(observed_ranks)
    print(f"\nobserved rank table: {json.dumps(observed_ranks)}")
    print(f"observed criterion met: {observed['met']}  "
          f"(physics_only range {observed['physics_only_rank_range']}, "
          f"rank-constant arms {observed['constant_arms']})")

    uniform = exact_uniform_null()
    print(f"\nnull A - independent uniform random rankings (exact, "
          f"{uniform['configurations']} configurations):")
    print(f"  P(no arm retains its rank)   = {uniform['p_no_arm_retains_rank']:.4f}")
    print(f"  P(physics range >= 3)        = {uniform['p_physics_range_ge_3']:.4f}")
    print(f"  P(criterion met)             = {uniform['p_criterion_met']:.4f}")
    print(f"  (H3 was closed at           = {uniform['h3_closure_threshold']:.4f})")

    noise = stability_bootstrap(arenas, args.n_boot, SEED)
    print(f"\nnull B - sampling noise around the fitted arms "
          f"({noise['n_boot']} cluster-bootstrap resamples of each test fold):")
    print(f"  P(criterion met)             = {noise['p_criterion_met_under_sampling_noise']:.4f}")
    print(f"  physics_only rank range: mean {noise['physics_only_rank_range']['mean']:.2f}, "
          f"P(>=3) = {noise['physics_only_rank_range']['p_ge_3']:.4f}")
    print(f"  rank range distribution: {noise['physics_only_rank_range']['distribution']}")
    print(f"  mean number of rank-constant arms = {noise['mean_n_rank_constant_arms']:.2f}")

    payload = {
        "experiments": ["E5 selection regret", "E3 instability reference distribution"],
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root), "seed": SEED, "n_boot": args.n_boot,
        "refitting_performed": False,
        "frozen_artifacts_modified": False,
        "preregistered_verdict_changed": False,
        "artifacts": {o: {"path": a["artifact"], "sha256": a["sha256"],
                          "n_scored": a["n_scored"], "n_families": a["n_families"]}
                      for o, a in arenas.items()},
        "E5_selection_regret": e5,
        "E3_instability_reference": {
            "observed_rank_table": observed_ranks,
            "observed_criterion": observed,
            "null_A_uniform_permutation_exact": uniform,
            "null_B_sampling_noise_bootstrap": noise,
        },
    }
    with open(out_dir / "e3_e5_results.json", "w") as stream:
        json.dump(payload, stream, indent=2, default=str)
    print(f"\nwritten: {out_dir / 'e3_e5_results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
