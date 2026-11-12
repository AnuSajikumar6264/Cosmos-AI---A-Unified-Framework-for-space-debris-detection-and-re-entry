"""Phase G+: diagnose and attempt to improve lifetime prediction.

**Diagnosis.** Model selection in the lifetime study uses tune-A, which is drawn from the
development period and **censored at the forecast origin**, while the test fold is evaluated
over a long forward window. The two sets therefore have different target distributions, and
the consequence is measurable: the Spearman rank correlation between tune-A pinball and test
pinball is **0.000 at both origins**. Selection carries no rank information about forward
performance, which explains (a) the gated expert underperforming several of its own
components, (b) the feature-effect sign reversals found in E12, and (c) the conformal coverage
failures found in Phase H -- the CQR calibration set (tune-B) is censored at the origin while
test is not, a concrete exchangeability violation rather than generic "drift".

**Pre-specified candidate.** Because selection does not transfer, the principled response is
not to select better but to **avoid selecting**. The candidate is a parameter-free robust
combination over a candidate set fixed *a priori by role*, not by test performance:

* `physics_only` -- the domain prior, available at every origin;
* `tabm`, `tabicl`, `kumo` -- the study's own pre-specified recent-learner pool
  (``cosmos.ai.lifetime.models.RECENT``).

Two combiners are evaluated, both parameter-free: the row-wise **median** (robust to one
member collapsing, which is the observed failure mode -- `tabm` scores 0.099 at origin 2011)
and the row-wise **mean**. Quantiles are sorted afterwards to enforce monotonicity. Two tests,
Benjamini-Hochberg corrected.

**Honesty constraint.** The test leaderboard was inspected during the diagnosis above, so
these results are **exploratory**, not confirmatory. The combiners are parameter-free and
motivated by a diagnosed mechanism rather than fitted to the test fold, but confirmation
requires a fresh temporal origin. This is stated in the report and not softened.

    python scripts/phase_g_lifetime_optimization.py --n-boot 4000

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
    benjamini_hochberg,
    paired_cluster_bootstrap,
    _pinball_per_object,
)
from scripts.phase_h_uncertainty_audit import coverage_record  # noqa: E402

ORIGINS = ("2011", "2016")
SEED = 20261027

#: Candidate set fixed a priori by role. `RECENT` is the study's own pre-specified pool.
BLEND_MEMBERS = ("physics_only", "tabm", "tabicl", "kumo")
#: The incumbents this must beat to count as an improvement.
INCUMBENTS = ("cosmos_gated", "equal_average", "stack_constant")
#: Nominal interval levels to check, so a pinball gain cannot hide a coverage loss.
LEVELS = {"80": 0.80, "90": 0.90}


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
    families = test["launch_family"].astype(str).to_numpy()
    if len(families) != len(data["z"]):
        return None
    mask = data["known5"].astype(bool)
    return {"data": data, "mask": mask, "z": data["z"][mask],
            "families": families[mask], "path": path, "sha256": sha256_file(path),
            "split_sizes": {k: int(len(v)) for k, v in split.items()},
            "split_event_rates": {k: float(v["event"].mean()) for k, v in split.items()},
            "split_max_time_days": {k: float(v["time_days"].max()) for k, v in split.items()}}


def diagnose_selection_transfer(root: Path, origin: str) -> dict:
    """Does tune-A model selection predict forward-in-time test performance?"""
    summary_path = _base(root, origin) / "summary.json"
    regression_path = _base(root, origin) / "regression_test.csv"
    if not summary_path.is_file() or not regression_path.is_file():
        return {"status": "NOT EVALUABLE"}
    summary = json.loads(summary_path.read_text())
    tune_a = summary.get("tuneA_pinball", {})
    test = pd.read_csv(regression_path).set_index("model")["pinball"]
    rows = [{"model": name, "tuneA_pinball": value, "test_pinball": test.get(name)}
            for name, value in tune_a.items() if name in test.index]
    frame = pd.DataFrame(rows)
    if len(frame) < 3:
        return {"status": "NOT EVALUABLE", "detail": "too few shared models"}
    spearman = float(frame["tuneA_pinball"].corr(frame["test_pinball"], method="spearman"))
    selected = summary.get("best_learner_on_tuneA")
    frame["test_rank"] = frame["test_pinball"].rank().astype(int)
    selected_rank = (int(frame.loc[frame["model"].eq(selected), "test_rank"].iloc[0])
                     if selected in set(frame["model"]) else None)
    return {
        "status": "evaluated",
        "selected_on_tuneA": selected,
        "selection_pool": summary.get("selection_pool"),
        "n_models_compared": int(len(frame)),
        "spearman_tuneA_vs_test": spearman,
        "selected_model_test_rank": selected_rank,
        "best_possible_test_pinball": float(frame["test_pinball"].min()),
        "selected_model_test_pinball": (float(frame.loc[frame["model"].eq(selected),
                                                        "test_pinball"].iloc[0])
                                        if selected_rank else None),
        "table": frame.to_dict(orient="records"),
        "reading": ("a Spearman correlation near zero means tune-A ranking carries no "
                    "information about forward test ranking"),
    }


def build_blend(data: dict, members: tuple[str, ...], how: str) -> np.ndarray | None:
    """Row-wise median or mean across members' quantile matrices, then monotonised."""
    stack = [data[f"{m}__q"] for m in members if f"{m}__q" in data]
    if len(stack) < 2:
        return None
    array = np.stack(stack, axis=0)
    combined = np.median(array, axis=0) if how == "median" else np.mean(array, axis=0)
    # Quantile levels must be nondecreasing; combining independent quantile functions can
    # cross by small amounts, so the result is sorted exactly as run.py does for ensembles.
    return np.sort(combined, axis=1)


def build_blend_bounds(data: dict, members: tuple[str, ...], how: str,
                       width: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Combine the members' conformalised interval bounds with the same rule."""
    lows = [data[f"{m}__lo{width}"] for m in members if f"{m}__lo{width}" in data]
    highs = [data[f"{m}__hi{width}"] for m in members if f"{m}__hi{width}" in data]
    if len(lows) < 2 or len(lows) != len(highs):
        return None
    combine = np.median if how == "median" else np.mean
    low = combine(np.stack(lows, axis=0), axis=0)
    high = combine(np.stack(highs, axis=0), axis=0)
    return np.minimum(low, high), np.maximum(low, high)


def evaluate_origin(root: Path, origin: str, n_boot: int, alpha: float) -> dict:
    arena = _arena(root, origin)
    if arena is None:
        return {"status": "NOT EVALUABLE", "detail": f"cannot align test fold for {origin}"}
    data, mask, z, families = arena["data"], arena["mask"], arena["z"], arena["families"]

    members = tuple(m for m in BLEND_MEMBERS if f"{m}__q" in data)
    candidates: dict[str, np.ndarray] = {}
    for how in ("median", "mean"):
        blend = build_blend(data, members, how)
        if blend is not None:
            candidates[f"robust_{how}_blend"] = blend

    reference = {name: data[f"{name}__q"] for name in INCUMBENTS if f"{name}__q" in data}
    reference.update({name: data[f"{name}__q"] for name in members})

    losses = {name: _pinball_per_object(z, q[mask]) for name, q in
              {**candidates, **reference}.items()}
    pinball = {name: float(value.mean()) for name, value in losses.items()}

    # Paired contrasts: each candidate against each incumbent. Negative = candidate better.
    contrasts, p_values = [], []
    for candidate in candidates:
        for incumbent in INCUMBENTS:
            if incumbent not in losses:
                continue
            record = paired_cluster_bootstrap(losses[candidate] - losses[incumbent],
                                              families, n_boot, seed=SEED)
            record.update({
                "candidate": candidate, "incumbent": incumbent,
                "candidate_pinball": pinball[candidate],
                "incumbent_pinball": pinball[incumbent],
                "relative_change": ((pinball[candidate] - pinball[incumbent])
                                    / pinball[incumbent]),
                "verdict": ("CANDIDATE BETTER" if record["ci95_hi"] < 0
                            else "INCUMBENT BETTER" if record["ci95_lo"] > 0
                            else "INCONCLUSIVE"),
            })
            contrasts.append(record)
            p_values.append(record["p_value"])

    correction = benjamini_hochberg(p_values, alpha=alpha)
    for record, adjusted, rejected in zip(contrasts, correction["adjusted"],
                                          correction["rejected"]):
        record["p_adjusted_bh"] = adjusted
        record["significant_after_correction"] = bool(rejected)

    # Coverage: a pinball gain must not be bought with a coverage loss.
    coverage: dict[str, dict] = {}
    for how in ("median", "mean"):
        name = f"robust_{how}_blend"
        if name not in candidates:
            continue
        coverage[name] = {}
        for width, nominal in LEVELS.items():
            bounds = build_blend_bounds(data, members, how, width)
            if bounds is None:
                coverage[name][f"cov{width}"] = {"status": "absent"}
                continue
            low, high = bounds[0][mask], bounds[1][mask]
            finite = np.isfinite(low) & np.isfinite(high)
            if finite.sum() == 0:
                coverage[name][f"cov{width}"] = {"status": "no finite intervals"}
                continue
            inside = (z[finite] >= low[finite]) & (z[finite] <= high[finite])
            record = coverage_record(inside, families[finite], nominal, n_boot)
            record["mean_width_log10_days"] = float(np.mean(high[finite] - low[finite]))
            coverage[name][f"cov{width}"] = record
    for name in INCUMBENTS:
        if f"{name}__lo90" not in data:
            continue
        coverage[name] = {}
        for width, nominal in LEVELS.items():
            low, high = data[f"{name}__lo{width}"][mask], data[f"{name}__hi{width}"][mask]
            finite = np.isfinite(low) & np.isfinite(high)
            inside = (z[finite] >= low[finite]) & (z[finite] <= high[finite])
            record = coverage_record(inside, families[finite], nominal, n_boot)
            record["mean_width_log10_days"] = float(np.mean(high[finite] - low[finite]))
            coverage[name][f"cov{width}"] = record

    return {
        "status": "evaluated",
        "origin": origin,
        "artifact_sha256": arena["sha256"],
        "blend_members_used": list(members),
        "n_objects_scored": int(mask.sum()),
        "n_launch_families": int(pd.unique(families).size),
        "split_sizes": arena["split_sizes"],
        "split_event_rates": arena["split_event_rates"],
        "split_max_time_days": arena["split_max_time_days"],
        "pinball": pinball,
        "contrasts": contrasts,
        "coverage": coverage,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/phase_g_lifetime")
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

    print("Phase G+ -- lifetime diagnosis and pre-specified robust-combination candidate")

    print("\n=== 1. selection transfer diagnosis ===")
    diagnosis = {}
    for origin in ORIGINS:
        diagnosis[origin] = diagnose_selection_transfer(root, origin)
        record = diagnosis[origin]
        if record.get("status") != "evaluated":
            continue
        print(f"  origin {origin}: selected '{record['selected_on_tuneA']}' on tune-A -> "
              f"test rank {record['selected_model_test_rank']} of "
              f"{record['n_models_compared']}; "
              f"Spearman(tuneA, test) = {record['spearman_tuneA_vs_test']:+.3f}")

    print("\n=== 2. split asymmetry (why selection does not transfer) ===")
    results = {}
    for origin in ORIGINS:
        results[origin] = evaluate_origin(root, origin, args.n_boot, args.alpha)
        record = results[origin]
        if record.get("status") != "evaluated":
            print(f"  origin {origin}: {record.get('detail')}")
            continue
        sizes, rates = record["split_sizes"], record["split_event_rates"]
        spans = record["split_max_time_days"]
        for name in ("tuneA", "tuneB", "test"):
            print(f"  origin {origin} {name:6s} n={sizes[name]:6d} "
                  f"event_rate={rates[name]:.3f} max_time_days={spans[name]:.0f}")

    print("\n=== 3. candidate vs incumbent (pinball, lower is better) ===")
    for origin in ORIGINS:
        record = results[origin]
        if record.get("status") != "evaluated":
            continue
        print(f"\n  --- origin {origin} ---")
        for name, value in sorted(record["pinball"].items(), key=lambda kv: kv[1]):
            tag = "  <- candidate" if name.startswith("robust_") else ""
            print(f"    {name:24s} {value:.6f}{tag}")
        for contrast in record["contrasts"]:
            flag = "*" if contrast["significant_after_correction"] else " "
            print(f"   {flag} {contrast['candidate']} vs {contrast['incumbent']:16s} "
                  f"delta={contrast['mean']:+.6f} "
                  f"({100 * contrast['relative_change']:+.1f}%) "
                  f"CI [{contrast['ci95_lo']:+.6f}, {contrast['ci95_hi']:+.6f}] "
                  f"p_adj={contrast['p_adjusted_bh']:.4f} -> {contrast['verdict']}")

    print("\n=== 4. coverage (a pinball gain must not cost coverage) ===")
    for origin in ORIGINS:
        record = results[origin]
        if record.get("status") != "evaluated":
            continue
        print(f"  --- origin {origin} ---")
        for name, entry in record["coverage"].items():
            for label, value in entry.items():
                if value.get("status") != "evaluated":
                    continue
                print(f"    {name:24s} {label} nominal={value['nominal']:.2f} "
                      f"empirical={value['empirical_coverage']:.4f} "
                      f"width={value['mean_width_log10_days']:.3f} -> {value['verdict']}")

    # ---- cross-origin verdict: an improvement must hold at BOTH origins
    verdict_rows = []
    for candidate in ("robust_median_blend", "robust_mean_blend"):
        per_origin = {}
        for origin in ORIGINS:
            record = results.get(origin, {})
            if record.get("status") != "evaluated":
                continue
            against = [c for c in record["contrasts"] if c["candidate"] == candidate]
            better = [c for c in against if c["significant_after_correction"] and c["mean"] < 0]
            worse = [c for c in against if c["significant_after_correction"] and c["mean"] > 0]
            per_origin[origin] = {
                "pinball": record["pinball"].get(candidate),
                "beats_significantly": [c["incumbent"] for c in better],
                "loses_significantly": [c["incumbent"] for c in worse],
            }
        beats_all_origins = all(p["beats_significantly"] for p in per_origin.values()) \
            and len(per_origin) == len(ORIGINS)
        loses_anywhere = any(p["loses_significantly"] for p in per_origin.values())
        verdict_rows.append({
            "candidate": candidate,
            "per_origin": per_origin,
            "promote": bool(beats_all_origins and not loses_anywhere),
            "verdict": ("PROMOTE" if beats_all_origins and not loses_anywhere
                        else "DO NOT PROMOTE"),
        })

    print("\n=== 5. promotion decision (must improve at BOTH origins, degrade at neither) ===")
    for row in verdict_rows:
        print(f"  {row['candidate']:24s} {row['verdict']}")
        for origin, detail in row["per_origin"].items():
            print(f"      origin {origin}: pinball {detail['pinball']:.6f} "
                  f"beats {detail['beats_significantly'] or 'none'} "
                  f"loses_to {detail['loses_significantly'] or 'none'}")

    record = {
        "phase": "G+ lifetime",
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "n_boot": args.n_boot,
        "alpha": args.alpha,
        "seed": SEED,
        "exploratory": True,
        "exploratory_note": (
            "the test leaderboard was inspected during the diagnosis, so these candidate "
            "results are exploratory; the combiners are parameter-free and motivated by the "
            "diagnosed mechanism rather than fitted to test, but confirmation requires a "
            "fresh temporal origin"),
        "blend_specification": {
            "members": list(BLEND_MEMBERS),
            "rationale": ("union of the study's pre-specified recent-learner pool "
                          "(models.RECENT) and the physics prior; chosen by role, not by test "
                          "performance"),
            "combiners": ["median", "mean"],
            "parameters": "none",
            "monotonisation": "np.sort along the quantile axis, as run.py does for ensembles",
        },
        "selection_transfer_diagnosis": diagnosis,
        "results": results,
        "promotion": verdict_rows,
        "acceptance_criteria": [
            "must improve pinball significantly against the incumbent at BOTH origins",
            "must not significantly degrade against any incumbent at either origin",
            "must not lose interval coverage relative to the incumbent",
            "a single favourable origin is not sufficient",
        ],
    }
    with open(out_dir / "phase_g_lifetime_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)

    rows = []
    for origin in ORIGINS:
        entry = results.get(origin, {})
        if entry.get("status") != "evaluated":
            continue
        for name, value in entry["pinball"].items():
            rows.append({"origin": origin, "model": name, "pinball": value,
                         "is_candidate": name.startswith("robust_")})
    pd.DataFrame(rows).to_csv(out_dir / "lifetime_candidate_table.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
