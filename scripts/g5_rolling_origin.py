"""G5: rolling evaluation across launch-epoch slices.

**What this is, precisely.** A full rolling-origin experiment would refit every learner at
each new forecast origin. That is not done here (it needs hours of GPU time and new tuning
passes). Instead this holds the fitted models fixed and advances the **evaluation population**
through 11 chronological launch-year slices of the two existing test folds:

* origin 2011 -> launch years 2011..2015 (5 slices, 201-764 objects, 79-136 launch families)
* origin 2016 -> launch years 2016..2021 (6 slices, 284-843 objects, 89-152 launch families)

So it tests **evaluation-population sensitivity**, not retraining sensitivity. That is a
weaker design than rolling-origin retraining and the distinction is stated wherever a result
is reported. It is still informative, because the slices differ enormously in composition: the
at-cap share runs from 0.874 (launch year 2017) to 0.283 (2019), and the event rate inversely
from 0.304 to 0.754.

**Why it matters for promotion.** Phase G+ could not promote any candidate because it had only
two evaluation populations. Eleven slices give a much stronger test of the pre-specified
criterion "improves across multiple eligible temporal origins, degrades at none".

    python scripts/g5_rolling_origin.py --n-boot 2000

Evidential status: the parent test folds have been scored repeatedly, so this is a robustness
re-analysis and **not** independent confirmation. No model is retrained; no artifact modified.
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
from scripts.phase_g_lifetime_optimization import build_blend, build_blend_bounds  # noqa: E402
from scripts.phase_h_uncertainty_audit import coverage_record  # noqa: E402

ORIGINS = ("2011", "2016")
SEED = 20261027
Z_CAP = float(np.log10(1826.25))

#: Candidate (pre-specified in Phase G+, unchanged here) and the incumbent it must beat.
BLEND_MEMBERS = ("physics_only", "tabm", "tabicl", "kumo")
DEPLOYED = "cosmos_gated"
#: Reference models tracked for ranking stability.
TRACKED = ("cosmos_gated", "physics_only", "tabm", "tabicl", "kumo", "equal_average",
           "stack_constant", "mlp", "xgboost")
#: A slice needs enough independent units for a cluster bootstrap to mean anything.
MIN_FAMILIES = 40
MIN_OBJECTS = 150


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
    if len(test) != len(data["z"]):
        return None
    mask = data["known5"].astype(bool)
    return {
        "data": data, "mask": mask, "z": data["z"][mask],
        "families": test["launch_family"].astype(str).to_numpy()[mask],
        "years": test["t0"].dt.year.to_numpy()[mask],
        "path": path, "sha256": sha256_file(path),
    }


def evaluate_slices(root: Path, origin: str, n_boot: int) -> list[dict]:
    arena = _arena(root, origin)
    if arena is None:
        return []
    data, mask, z = arena["data"], arena["mask"], arena["z"]
    families, years = arena["families"], arena["years"]

    members = tuple(m for m in BLEND_MEMBERS if f"{m}__q" in data)
    predictions = {name: data[f"{name}__q"] for name in TRACKED if f"{name}__q" in data}
    for how in ("median", "mean"):
        blend = build_blend(data, members, how)
        if blend is not None:
            predictions[f"robust_{how}_blend"] = blend

    out = []
    for year in sorted(set(years.tolist())):
        select = years == year
        n_families = int(pd.unique(families[select]).size)
        if select.sum() < MIN_OBJECTS or n_families < MIN_FAMILIES:
            out.append({"origin": origin, "launch_year": int(year), "status": "too_small",
                        "n": int(select.sum()), "n_families": n_families})
            continue
        z_slice = z[select]
        fam_slice = families[select]
        at_cap = float(np.isclose(z_slice, Z_CAP, atol=1e-6).mean())

        losses = {name: _pinball_per_object(z_slice, q[mask][select])
                  for name, q in predictions.items()}
        pinball = {name: float(v.mean()) for name, v in losses.items()}
        order = sorted(pinball, key=lambda k: pinball[k])
        ranks = {name: i + 1 for i, name in enumerate(order)}

        # Candidate vs deployed incumbent, cluster bootstrap within the slice.
        contrasts = {}
        for candidate in ("robust_median_blend", "robust_mean_blend"):
            if candidate not in losses or DEPLOYED not in losses:
                continue
            record = paired_cluster_bootstrap(losses[candidate] - losses[DEPLOYED],
                                              fam_slice, n_boot, seed=SEED)
            record["verdict"] = ("CANDIDATE BETTER" if record["ci95_hi"] < 0
                                 else "INCUMBENT BETTER" if record["ci95_lo"] > 0
                                 else "INCONCLUSIVE")
            contrasts[candidate] = record

        # Coverage of the candidate and the incumbent within the slice.
        coverage = {}
        for name in (DEPLOYED, "robust_mean_blend", "robust_median_blend"):
            entry = {}
            for width, nominal in (("80", 0.80), ("90", 0.90)):
                if name.startswith("robust_"):
                    bounds = build_blend_bounds(data, members,
                                                name.split("_")[1], width)
                    if bounds is None:
                        continue
                    low, high = bounds[0][mask][select], bounds[1][mask][select]
                elif f"{name}__lo{width}" in data:
                    low = data[f"{name}__lo{width}"][mask][select]
                    high = data[f"{name}__hi{width}"][mask][select]
                else:
                    continue
                finite = np.isfinite(low) & np.isfinite(high)
                if finite.sum() == 0:
                    continue
                inside = (z_slice[finite] >= low[finite]) & (z_slice[finite] <= high[finite])
                entry[f"cov{width}"] = coverage_record(inside, fam_slice[finite],
                                                       nominal, n_boot)
            if entry:
                coverage[name] = entry

        out.append({
            "origin": origin, "launch_year": int(year), "status": "evaluated",
            "n": int(select.sum()), "n_families": n_families, "at_cap_fraction": at_cap,
            "pinball": pinball, "ranks": ranks, "best_model": order[0],
            "contrasts_vs_deployed": contrasts, "coverage": coverage,
        })
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/g5_rolling")
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} exists and is not empty; results are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("G5 -- rolling evaluation across launch-epoch slices")
    print("  (models held fixed; evaluation population advances)\n")

    slices = []
    for origin in ORIGINS:
        slices.extend(evaluate_slices(root, origin, args.n_boot))

    usable = [s for s in slices if s["status"] == "evaluated"]
    print(f"  {len(usable)} usable slices of {len(slices)}\n")

    print(f"  {'slice':16s} {'n':>5s} {'fam':>4s} {'at_cap':>7s}  {'best model':22s} "
          f"{'deployed rank':>13s}")
    for s in usable:
        print(f"  {s['origin']}/{s['launch_year']:<11d} {s['n']:5d} {s['n_families']:4d} "
              f"{s['at_cap_fraction']:7.3f}  {s['best_model']:22s} "
              f"{s['ranks'].get(DEPLOYED, -1):13d}")

    # ---- ranking stability across slices
    tracked = sorted({m for s in usable for m in s["ranks"]})
    rank_frame = pd.DataFrame(
        [{**{"slice": f"{s['origin']}/{s['launch_year']}"},
          **{m: s["ranks"].get(m) for m in tracked}} for s in usable]).set_index("slice")
    stability = {}
    for model in tracked:
        series = rank_frame[model].dropna()
        if len(series) >= 3:
            stability[model] = {
                "mean_rank": float(series.mean()),
                "min_rank": int(series.min()),
                "max_rank": int(series.max()),
                "rank_range": int(series.max() - series.min()),
                "times_best": int((series == 1).sum()),
                "n_slices": int(len(series)),
            }
    print("\n  === ranking stability across slices (rank 1 = best) ===")
    print(f"  {'model':22s} {'mean':>6s} {'min':>4s} {'max':>4s} {'range':>6s} {'#best':>6s}")
    for model, record in sorted(stability.items(), key=lambda kv: kv[1]["mean_rank"]):
        print(f"  {model:22s} {record['mean_rank']:6.2f} {record['min_rank']:4d} "
              f"{record['max_rank']:4d} {record['rank_range']:6d} {record['times_best']:6d}")

    # Pairwise Spearman of model ranks between slices: is the ordering stable at all?
    pairwise = []
    names = list(rank_frame.index)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = rank_frame.loc[names[i]], rank_frame.loc[names[j]]
            both = a.notna() & b.notna()
            if both.sum() >= 4:
                pairwise.append(float(a[both].corr(b[both], method="spearman")))
    rank_agreement = {
        "n_pairs": len(pairwise),
        "mean_spearman": float(np.mean(pairwise)) if pairwise else None,
        "median_spearman": float(np.median(pairwise)) if pairwise else None,
        "min_spearman": float(np.min(pairwise)) if pairwise else None,
        "fraction_negative": float(np.mean([p < 0 for p in pairwise])) if pairwise else None,
    }
    print(f"\n  pairwise rank agreement between slices: mean Spearman "
          f"{rank_agreement['mean_spearman']:+.3f}, "
          f"median {rank_agreement['median_spearman']:+.3f}, "
          f"min {rank_agreement['min_spearman']:+.3f}, "
          f"{100 * rank_agreement['fraction_negative']:.0f}% of pairs negative")

    # ---- promotion test across slices, BH-corrected over slices per candidate
    promotion = {}
    for candidate in ("robust_median_blend", "robust_mean_blend"):
        entries = [(s, s["contrasts_vs_deployed"].get(candidate)) for s in usable
                   if candidate in s["contrasts_vs_deployed"]]
        p_values = [record["p_value"] for _, record in entries]
        correction = benjamini_hochberg(p_values, alpha=args.alpha)
        per_slice = []
        for (s, record), adjusted, rejected in zip(entries, correction["adjusted"],
                                                   correction["rejected"]):
            per_slice.append({
                "slice": f"{s['origin']}/{s['launch_year']}",
                "delta": record["mean"], "ci95_lo": record["ci95_lo"],
                "ci95_hi": record["ci95_hi"], "p_value": record["p_value"],
                "p_adjusted_bh": adjusted,
                "significant": bool(rejected),
                "direction": ("better" if record["mean"] < 0 else "worse"),
            })
        better = [e for e in per_slice if e["significant"] and e["delta"] < 0]
        worse = [e for e in per_slice if e["significant"] and e["delta"] > 0]
        accuracy_ok = bool(len(better) > len(per_slice) / 2 and not worse)
        promotion[candidate] = {
            "n_slices": len(per_slice),
            "significantly_better_in": [e["slice"] for e in better],
            "significantly_worse_in": [e["slice"] for e in worse],
            "per_slice": per_slice,
            "accuracy_criterion_met": accuracy_ok,
            # The coverage criterion is filled in below, once coverage is summarised. All
            # three stated criteria are enforced in code so a verdict cannot drift from them.
            "coverage_criterion_met": None,
            "promote": None,
            "verdict": "PENDING COVERAGE CHECK",
        }

    print("\n  === accuracy criterion (majority better, none worse) ===")
    for candidate, record in promotion.items():
        print(f"  {candidate:22s} accuracy_met={record['accuracy_criterion_met']}  "
              f"better in {len(record['significantly_better_in'])}/{record['n_slices']}, "
              f"worse in {len(record['significantly_worse_in'])}")
        if record["significantly_worse_in"]:
            print(f"      degrades at: {', '.join(record['significantly_worse_in'])}")

    # ---- coverage stability across slices
    coverage_rows = []
    for s in usable:
        for model, entry in s["coverage"].items():
            for label, record in entry.items():
                if record.get("status") != "evaluated":
                    continue
                coverage_rows.append({
                    "slice": f"{s['origin']}/{s['launch_year']}", "model": model,
                    "level": label, "nominal": record["nominal"],
                    "empirical": record["empirical_coverage"],
                    "verdict": record["verdict"],
                })
    coverage_frame = pd.DataFrame(coverage_rows)
    coverage_summary = {}
    if not coverage_frame.empty:
        for (model, level), group in coverage_frame.groupby(["model", "level"]):
            nominal_cells = int((group["verdict"] == "CONSISTENT WITH NOMINAL").sum())
            coverage_summary[f"{model}/{level}"] = {
                "slices": int(len(group)),
                "at_nominal": nominal_cells,
                "under": int((group["verdict"] == "UNDER-COVERS").sum()),
                "over": int((group["verdict"] == "OVER-COVERS").sum()),
                "empirical_min": float(group["empirical"].min()),
                "empirical_max": float(group["empirical"].max()),
            }
    print("\n  === coverage across slices ===")
    for key, record in sorted(coverage_summary.items()):
        print(f"  {key:34s} at-nominal {record['at_nominal']}/{record['slices']}  "
              f"under {record['under']} over {record['over']}  "
              f"range {record['empirical_min']:.3f}-{record['empirical_max']:.3f}")

    # ---- enforce the coverage criterion: a candidate must not reach nominal coverage in
    # fewer slices than the incumbent, at any level.
    for candidate, entry in promotion.items():
        comparisons, met = {}, True
        for level in ("cov80", "cov90"):
            candidate_key, incumbent_key = f"{candidate}/{level}", f"{DEPLOYED}/{level}"
            if candidate_key not in coverage_summary or incumbent_key not in coverage_summary:
                continue
            candidate_nominal = coverage_summary[candidate_key]["at_nominal"]
            incumbent_nominal = coverage_summary[incumbent_key]["at_nominal"]
            ok = candidate_nominal >= incumbent_nominal
            comparisons[level] = {
                "candidate_at_nominal": candidate_nominal,
                "incumbent_at_nominal": incumbent_nominal,
                "not_degraded": bool(ok),
            }
            met = met and ok
        entry["coverage_comparison"] = comparisons
        entry["coverage_criterion_met"] = bool(met) if comparisons else None
        entry["promote"] = bool(entry["accuracy_criterion_met"] and met) if comparisons \
            else bool(entry["accuracy_criterion_met"])
        entry["verdict"] = "PROMOTE" if entry["promote"] else "DO NOT PROMOTE"

    print("\n  === promotion decision (accuracy AND coverage) ===")
    for candidate, entry in promotion.items():
        print(f"  {candidate:22s} {entry['verdict']:16s} "
              f"accuracy={entry['accuracy_criterion_met']} "
              f"coverage={entry['coverage_criterion_met']}")
        for level, comparison in (entry.get("coverage_comparison") or {}).items():
            print(f"      {level}: candidate at-nominal "
                  f"{comparison['candidate_at_nominal']} vs incumbent "
                  f"{comparison['incumbent_at_nominal']} -> "
                  f"{'ok' if comparison['not_degraded'] else 'DEGRADED'}")

    record = {
        "experiment": "G5 rolling evaluation",
        "design": ("models held fixed; evaluation population advances through launch-year "
                   "slices. This is evaluation-population sensitivity, NOT rolling-origin "
                   "retraining"),
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "git": git_revision(root),
        "n_boot": args.n_boot,
        "alpha": args.alpha,
        "seed": SEED,
        "exploratory": True,
        "exploratory_note": ("the parent test folds have been scored repeatedly; this is a "
                             "robustness re-analysis and not independent confirmation"),
        "min_objects": MIN_OBJECTS,
        "min_families": MIN_FAMILIES,
        "slices": slices,
        "ranking_stability": stability,
        "rank_agreement_between_slices": rank_agreement,
        "promotion": promotion,
        "coverage_summary": coverage_summary,
        "promotion_criteria": [
            "significantly better (BH-corrected) in a majority of eligible slices",
            "significantly worse in none",
            "coverage not degraded relative to the incumbent",
        ],
        "not_established": [
            "models were not refitted per slice, so this does not test selection under "
            "rolling-origin retraining",
            "slices are sub-populations of already-scored test folds",
            "slice sample sizes (150-843 objects) limit power within each slice",
        ],
    }
    with open(out_dir / "g5_rolling_results.json", "w") as stream:
        json.dump(record, stream, indent=2, default=str)
    rank_frame.to_csv(out_dir / "g5_rank_by_slice.csv")
    if not coverage_frame.empty:
        coverage_frame.to_csv(out_dir / "g5_coverage_by_slice.csv", index=False)
    pd.DataFrame([{"slice": f"{s['origin']}/{s['launch_year']}", **s["pinball"]}
                  for s in usable]).to_csv(out_dir / "g5_pinball_by_slice.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
