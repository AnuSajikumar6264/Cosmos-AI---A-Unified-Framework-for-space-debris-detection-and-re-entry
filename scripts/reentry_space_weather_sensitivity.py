"""Sensitivity of the physics re-entry expert to solar (F10.7) and geomagnetic (Ap) activity.

    python scripts/reentry_space_weather_sensitivity.py --per-cell 40 --n-samples 32

Why this experiment exists. In the deployed 2026-10-27 snapshot every object carries the same
trailing-81-day F10.7 (111.27) and Ap (9.12), evaluated at the as-of date. The learned lifetime
model therefore cannot express any space-weather sensitivity on that snapshot -- its space-weather
features are constants -- and the literature retrieved in Phase 1 (de Oliveira et al. 2025,
Frontiers; Ocaya & Malevu 2025, npj Space Exploration) shows solar and geomagnetic activity drive
re-entry timing at the event scale. This script measures how much the **physics expert's**
re-entry probabilities move when F10.7 and Ap are set to other values the project's own space-weather
history has actually taken.

Design, fixed before running:
  * objects: the uncontrolled classes (D, R, C) in the 2026-10-27 state, stratified by perigee band
    and class, up to ``--per-cell`` per cell, fixed seed;
  * perturbation grid: the 5th / 25th / 50th / 75th / 95th percentiles of the trailing-81-day F10.7
    and Ap series in the project's space-weather table (data-derived, not chosen), plus the
    observed as-of value; F10.7 varied with Ap at its observed value and vice versa;
  * model: ``cosmos.ai.lifetime.physics.predict`` with the class-prior area-to-mass draws (the
    ``physics_prior`` variant), ``--n-samples`` Monte-Carlo draws, seed 0, density from the cached
    NRLMSIS 2.1 table;
  * outputs: expected 30 d / 90 d / 1 yr re-entry counts over the sample per level, the fraction of
    objects whose P(30 d) moves by more than 0.1 relative to baseline, and the log-log elasticity of
    the 30-day expected count with respect to F10.7 and Ap.

This is a sensitivity analysis of a model, not a validation against observed re-entries; no
outcome data enter it. Read-only on every input; outputs go to
``outputs/reentry_space_weather_sensitivity/``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cosmos.ai.lifetime import physics as PH  # noqa: E402
from cosmos.ai.lifetime.catalogue import load_space_weather  # noqa: E402
from cosmos.ai.provenance import git_revision  # noqa: E402
from cosmos.ai.twin import engine as E  # noqa: E402

OUT = ROOT / "outputs/reentry_space_weather_sensitivity"
HORIZONS = {"30d": 30.0, "90d": 90.0, "1yr": 365.25}
PERCENTILES = (5, 25, 50, 75, 95)


def stratified_sample(state: pd.DataFrame, per_cell: int, seed: int) -> pd.DataFrame:
    unc = state[state["type1"].isin(("D", "R", "C")) & state["perigee"].notna()].copy()
    unc["perigee_band"] = pd.cut(unc["perigee"], bins=[0, 300, 400, 500, 600, 800, 2000], right=False,
                                 labels=["<300", "300-400", "400-500", "500-600", "600-800", "800-2000"])
    parts = [g.sample(min(len(g), per_cell), random_state=seed)
             for _, g in unc.groupby(["perigee_band", "type1"], observed=True)]
    return pd.concat(parts).reset_index(drop=True)


def run_level(sample: pd.DataFrame, prior: dict, f107: float, ap: float, n_samples: int) -> tuple[dict, np.ndarray]:
    frame = sample.copy()
    frame["f107_last81"], frame["ap_last81"] = f107, ap
    t0 = time.time()
    r = PH.predict(frame, prior, n_samples=n_samples, seed=0)
    T = r["samples_days"]
    rec = {"f107": f107, "ap": ap, "n_objects": int(len(frame)), "n_samples": n_samples,
           "seconds": round(time.time() - t0, 1),
           "median_predicted_days_across_objects": float(np.median(np.median(T, axis=1)))}
    for k, h in HORIZONS.items():
        rec[f"expected_{k}"] = float((T <= h).mean(axis=1).sum())
    return rec, (T <= HORIZONS["30d"]).mean(axis=1)


def elasticity(xs: list[float], ys: list[float]) -> float | None:
    x, y = np.log(np.asarray(xs, float)), np.log(np.asarray(ys, float))
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 3:
        return None
    return float(np.polyfit(x[ok], y[ok], 1)[0])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of", default="2026-10-27")
    ap.add_argument("--per-cell", type=int, default=40)
    ap.add_argument("--n-samples", type=int, default=32)
    ap.add_argument("--seed", type=int, default=20261027)
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)

    state = E.current_state(args.as_of)
    assert state["f107_last81"].nunique() == 1 and state["ap_last81"].nunique() == 1, (
        "the snapshot was expected to carry a single as-of space-weather value for every object")
    f_obs, a_obs = float(state["f107_last81"].iloc[0]), float(state["ap_last81"].iloc[0])
    sample = stratified_sample(state, args.per_cell, args.seed)
    prior = E.physics_prior_as_of(args.as_of)

    sw = load_space_weather()
    hist_f = sw["f107_last81"].dropna()
    hist_a = sw["ap_last81"].dropna()
    f_levels = sorted({round(float(np.percentile(hist_f, p)), 2) for p in PERCENTILES} | {round(f_obs, 2)})
    a_levels = sorted({round(float(np.percentile(hist_a, p)), 2) for p in PERCENTILES} | {round(a_obs, 2)})

    base, p30_base = run_level(sample, prior, f_obs, a_obs, args.n_samples)
    rows = [{"sweep": "baseline", **base, "frac_objects_p30d_shift_gt_0.1": 0.0}]
    print(f"sample: {len(sample)} uncontrolled objects over {sample['perigee_band'].nunique()} perigee bands x "
          f"{sample['type1'].nunique()} classes; baseline F10.7={f_obs:.2f} Ap={a_obs:.2f}; "
          f"expected 30d={base['expected_30d']:.2f}  ({base['seconds']} s)")
    for f in f_levels:
        if abs(f - f_obs) < 1e-9:
            continue
        rec, p30 = run_level(sample, prior, f, a_obs, args.n_samples)
        rec["frac_objects_p30d_shift_gt_0.1"] = float((np.abs(p30 - p30_base) > 0.1).mean())
        rows.append({"sweep": "f107", **rec})
        print(f"  F10.7={f:7.2f} Ap={a_obs:5.2f}  E[30d]={rec['expected_30d']:7.2f}  E[1yr]={rec['expected_1yr']:7.2f}  "
              f"shift>0.1: {rec['frac_objects_p30d_shift_gt_0.1']:.3f}  ({rec['seconds']} s)")
    for a in a_levels:
        if abs(a - a_obs) < 1e-9:
            continue
        rec, p30 = run_level(sample, prior, f_obs, a, args.n_samples)
        rec["frac_objects_p30d_shift_gt_0.1"] = float((np.abs(p30 - p30_base) > 0.1).mean())
        rows.append({"sweep": "ap", **rec})
        print(f"  F10.7={f_obs:7.2f} Ap={a:5.2f}  E[30d]={rec['expected_30d']:7.2f}  E[1yr]={rec['expected_1yr']:7.2f}  "
              f"shift>0.1: {rec['frac_objects_p30d_shift_gt_0.1']:.3f}  ({rec['seconds']} s)")

    table = pd.DataFrame(rows)
    table.to_csv(OUT / "sensitivity_grid.csv", index=False)
    fsw = table[table.sweep.isin(("baseline", "f107"))].sort_values("f107")
    asw = table[table.sweep.isin(("baseline", "ap"))].sort_values("ap")
    report = {
        "analysed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": git_revision(),
        "as_of": args.as_of, "model": "physics expert, class-prior A/m (physics_prior variant)",
        "n_objects": int(len(sample)), "per_cell": args.per_cell, "n_samples": args.n_samples, "seed": args.seed,
        "snapshot_space_weather": {"f107_last81": f_obs, "ap_last81": a_obs,
                                   "constant_across_objects": True},
        "space_weather_history": {"n_days": int(len(hist_f)),
                                  "f107_percentiles": dict(zip(map(str, PERCENTILES), [float(np.percentile(hist_f, p)) for p in PERCENTILES])),
                                  "ap_percentiles": dict(zip(map(str, PERCENTILES), [float(np.percentile(hist_a, p)) for p in PERCENTILES]))},
        "elasticity_log_expected_30d": {"wrt_f107": elasticity(fsw["f107"].tolist(), fsw["expected_30d"].tolist()),
                                        "wrt_ap": elasticity(asw["ap"].tolist(), asw["expected_30d"].tolist())},
        "elasticity_log_expected_1yr": {"wrt_f107": elasticity(fsw["f107"].tolist(), fsw["expected_1yr"].tolist()),
                                        "wrt_ap": elasticity(asw["ap"].tolist(), asw["expected_1yr"].tolist())},
        "range_expected_30d_over_f107_grid": [float(fsw["expected_30d"].min()), float(fsw["expected_30d"].max())],
        "range_expected_30d_over_ap_grid": [float(asw["expected_30d"].min()), float(asw["expected_30d"].max())],
        "learned_lifetime_model_note": ("not measured: its space-weather features take one value across the "
                                        "snapshot, so its sensitivity on this snapshot is zero by construction"),
        "what_this_is_not": "a validation against observed re-entries; no outcome data enter this analysis",
        "total_seconds": float(table["seconds"].sum()),
    }
    (OUT / "results.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
    e = report["elasticity_log_expected_30d"]
    print(f"\nelasticity of E[30d]: wrt F10.7 {e['wrt_f107']}, wrt Ap {e['wrt_ap']};  total {report['total_seconds']:.0f} s")
    print(f"written {OUT.relative_to(ROOT)}/sensitivity_grid.csv, results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
