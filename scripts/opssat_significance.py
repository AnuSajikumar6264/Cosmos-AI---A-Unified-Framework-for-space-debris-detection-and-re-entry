"""OPS-SAT paired significance on BOTH protocols, from regenerated per-seed scores. Read-only.

    python scripts/opssat_significance.py --regen outputs/benchmarks/telemetry_opssat_regen_20261106

The archived 2026-10-24 study computed paired bootstrap comparisons only for the ``official``
protocol (``report.py::opssat_tables``), whose split interleaves train and test in time. This script
repeats those comparisons on the regenerated ``official`` scores and -- the point of X2 -- runs the
identical procedure on the ``time_blocked`` protocol, which is the temporally valid one.

Procedure, matching ``report.py`` exactly so the two are comparable:
  * scores are averaged over the five seeds per model (train_frac = 1.0);
  * statistics are AUC-PR and F1 at the fixed 0.5 decision rule;
  * ``cosmos.ai.evaluation.paired_bootstrap_diff`` with its defaults (n_boot = 2000, seed = 0);
  * the same five model pairs.
Additions, clearly labelled: Holm-adjusted p-values across the five pairs within each metric, and a
reconciliation of per-seed AUC-PR recomputed from the scores against the per-run table (which must
agree, since both came from the same scores).

Writes ``paired_comparisons_<protocol>.csv`` and ``prauc_from_scores_<protocol>.csv`` into the
regeneration directory. The archive is not touched.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cosmos.ai.evaluation import holm, paired_bootstrap_diff  # noqa: E402  (frozen; read-only use)

PAIRS = (("hybrid", "fcnn"), ("hybrid", "xgboost"), ("fcnn", "xgboost"),
         ("hybrid", "chronos:amazon/chronos-bolt-small"), ("cnn", "fcnn"))


def seed_scores(z, tag: str, model: str) -> dict[int, np.ndarray]:
    prefix = f"{tag}|1.0|{model}|"
    return {int(k[len(prefix):]): z[k] for k in z.files if k.startswith(prefix)}


def run_protocol(regen: Path, tag: str) -> dict:
    from sklearn.metrics import average_precision_score, f1_score

    path = regen / f"test_scores_{tag}.npz"
    if not path.is_file():
        return {"protocol": tag, "status": "scores missing"}
    z = np.load(path)
    y = z[f"{tag}|y"]
    models = sorted({k.split("|")[2] for k in z.files if k.startswith(f"{tag}|1.0|")})

    # --- reconciliation: per-seed AUC-PR from scores vs the per-run table written by the same run
    per_run = pd.read_csv(regen / f"per_run_{tag}.csv")
    per_run = per_run[(per_run.protocol == tag) & (per_run.train_frac == 1.0)]
    rec_rows, worst = [], 0.0
    for m in models:
        for s, sc in seed_scores(z, tag, m).items():
            ap = float(average_precision_score(y, sc))
            tab = per_run[(per_run.model == m) & (per_run.seed == s)]
            table_ap = float(tab.auc_pr.iloc[0]) if len(tab) else np.nan
            d = abs(ap - table_ap) if np.isfinite(table_ap) else np.nan
            worst = max(worst, d) if np.isfinite(d) else worst
            rec_rows.append({"protocol": tag, "model": m, "seed": s, "auc_pr_from_scores": ap,
                             "auc_pr_per_run_table": table_ap, "abs_diff": d})
    recon = pd.DataFrame(rec_rows)
    recon.to_csv(regen / f"prauc_from_scores_{tag}.csv", index=False)

    # --- paired comparisons on seed-averaged scores, as report.py does
    mean = {m: np.mean(list(seed_scores(z, tag, m).values()), axis=0) for m in models}
    comps = []
    for a, b in PAIRS:
        if a not in mean or b not in mean:
            comps.append({"protocol": tag, "A": a, "B": b, "status": "model missing"})
            continue
        r1 = paired_bootstrap_diff(lambda yy, p: average_precision_score(yy, p), y, mean[a], mean[b])
        r2 = paired_bootstrap_diff(lambda yy, p: f1_score(yy, (p >= 0.5).astype(int)), y,
                                   mean[a], mean[b])
        comps.append({"protocol": tag, "A": a, "B": b, "metric": "AUC-PR (seed-averaged scores)", **r1})
        comps.append({"protocol": tag, "A": a, "B": b, "metric": "F1 @ 0.5 (seed-averaged scores)", **r2})
    c = pd.DataFrame(comps)
    if "p_two_sided" in c:
        c["p_holm_within_metric"] = np.nan
        for met, g in c.dropna(subset=["p_two_sided"]).groupby("metric"):
            adj = holm({f"{r.A}|{r.B}": float(r.p_two_sided) for r in g.itertuples()})
            for idx, r in g.iterrows():
                c.loc[idx, "p_holm_within_metric"] = adj[f"{r.A}|{r.B}"]
    c.to_csv(regen / f"paired_comparisons_{tag}.csv", index=False)

    return {"protocol": tag, "n_test": int(len(y)), "n_positive": int(y.sum()), "models": models,
            "reconciliation_max_abs_diff_auc_pr": float(worst), "n_reconciled": int(len(recon)),
            "comparisons": c.to_dict(orient="records")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regen", required=True)
    args = ap.parse_args(argv)
    regen = (ROOT / args.regen).resolve()
    pd.set_option("display.width", 220)

    report = {}
    for tag in ("official", "time_blocked"):
        res = run_protocol(regen, tag)
        report[tag] = res
        print(f"\n### {tag}: {res.get('status', '')}")
        if "comparisons" in res:
            print(f"  n_test={res['n_test']} positives={res['n_positive']} "
                  f"reconciliation max|ΔAUC-PR|={res['reconciliation_max_abs_diff_auc_pr']:.2e} "
                  f"over {res['n_reconciled']} (model, seed) cells")
            c = pd.DataFrame(res["comparisons"])
            cols = [x for x in ("A", "B", "metric", "diff", "ci_low", "ci_high", "p_two_sided",
                                "p_holm_within_metric") if x in c]
            print(c[cols].to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    # archived official comparisons, for side-by-side
    arch = ROOT / "outputs/benchmarks/telemetry_opssat/paired_comparisons.csv"
    if arch.is_file() and "comparisons" in report.get("official", {}):
        a = pd.read_csv(arch)
        n = pd.DataFrame(report["official"]["comparisons"])
        m = a.merge(n, on=["A", "B", "metric"], suffixes=("_archive", "_regen"))
        if len(m):
            m["abs_diff_of_diff"] = (m["diff_archive"] - m["diff_regen"]).abs()
            print("\n### official: archived vs regenerated point estimates")
            print(m[["A", "B", "metric", "diff_archive", "diff_regen", "abs_diff_of_diff"]]
                  .to_string(index=False, float_format=lambda v: f"{v:.4f}"))
            report["official_vs_archive"] = m.to_dict(orient="records")

    (regen / "significance_report.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(f"\nwritten {regen.relative_to(ROOT)}/significance_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
