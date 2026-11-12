"""X10 / E6 — OPS-SAT branch comparison from the regenerated per-seed score archives. Read-only.

    python scripts/e6_opssat_branch_analysis.py

Arms: `cnn` (CNN branch alone on the raw fragment), `fcnn` (MLP branch alone on the engineered
features), `hybrid` (both branches, late fusion). Protocols: official (interleaved) and time_blocked.
Statistical protocol = the one already used for X2 (`scripts/opssat_significance.py`): scores averaged
over the five seeds (train_frac 1.0); `cosmos.ai.evaluation.paired_bootstrap_diff` with its defaults
(n_boot 2000, seed 0) resampling the same test fragments for both arms; Holm within each metric family
over the three pairwise contrasts. Metrics: AUC-PR, F1 at 0.5, Brier, ECE (10 equal-width bins, the
project's `expected_calibration_error`). Seed stability: per-seed metric values and their SD; the SD
ratio is reported with a 5-seed resampling interval that is descriptive only (five values).
Nothing is trained; no score is regenerated; no archived file is written.
"""
from __future__ import annotations

import hashlib, itertools, json, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cosmos.ai.evaluation import brier_score, expected_calibration_error, holm, paired_bootstrap_diff  # noqa: E402

REGEN = ROOT / "outputs/benchmarks/telemetry_opssat_regen_20261106"
OUT = ROOT / "outputs/e6_opssat_branch"
ARMS = ("cnn", "fcnn", "hybrid")
PAIRS = (("hybrid", "cnn"), ("hybrid", "fcnn"), ("cnn", "fcnn"))
THRESHOLD_FOR_K8 = {"ece_hybrid_vs_cnn_claimed": (0.035, 0.121), "f1_sd_hybrid_vs_cnn_claimed": (0.0066, 0.0977)}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def metrics(y, p) -> dict:
    from sklearn.metrics import average_precision_score, f1_score
    return {"auc_pr": float(average_precision_score(y, p)), "f1": float(f1_score(y, (p >= 0.5).astype(int))),
            "brier": brier_score(y, p), "ece": expected_calibration_error(y, p)}


STAT = {"auc_pr": lambda y, p: __import__("sklearn.metrics", fromlist=["average_precision_score"]).average_precision_score(y, p),
        "f1": lambda y, p: __import__("sklearn.metrics", fromlist=["f1_score"]).f1_score(y, (p >= 0.5).astype(int)),
        "brier": brier_score, "ece": expected_calibration_error}


def protocol(tag: str, rng: np.random.Generator) -> dict:
    z = np.load(REGEN / f"test_scores_{tag}.npz")
    y = z[f"{tag}|y"].astype(int)
    per_run = pd.read_csv(REGEN / f"per_run_{tag}.csv")
    seeds = {m: {int(k.split("|")[3]): z[k] for k in z.files if k.startswith(f"{tag}|1.0|{m}|")} for m in ARMS}
    assert all(len(v) == 5 for v in seeds.values()), {m: len(v) for m, v in seeds.items()}
    # per-seed metrics, reconciled against the per-run table written by the regeneration itself
    rows, recon = [], []
    for m in ARMS:
        for s, p in sorted(seeds[m].items()):
            mt = metrics(y, p)
            tab = per_run[(per_run.model == m) & (per_run.seed == s) & (per_run.train_frac == 1.0)]
            if len(tab) == 1:
                recon.append({"model": m, "seed": s, "d_f1": abs(mt["f1"] - float(tab.f1.iloc[0])), "d_brier": abs(mt["brier"] - float(tab.brier.iloc[0])),
                              "d_ece": abs(mt["ece"] - float(tab.ece.iloc[0])), "d_auc_pr": abs(mt["auc_pr"] - float(tab.auc_pr.iloc[0]))})
            rows.append({"protocol": tag, "model": m, "seed": s, **mt})
    per_seed = pd.DataFrame(rows)
    recon = pd.DataFrame(recon)
    stab = per_seed.groupby("model")[["auc_pr", "f1", "brier", "ece"]].agg(["mean", "std"])
    stab.columns = [f"{a}_{b}" for a, b in stab.columns]
    # SD ratio hybrid / cnn with a 5-seed resampling interval (descriptive only)
    sd_ratio = {}
    for metric in ("f1", "ece", "brier", "auc_pr"):
        h = per_seed[per_seed.model == "hybrid"][metric].to_numpy(); c = per_seed[per_seed.model == "cnn"][metric].to_numpy()
        ratios = []
        for _ in range(2000):
            ih, ic = rng.integers(0, 5, 5), rng.integers(0, 5, 5)
            sh, sc = np.std(h[ih], ddof=1), np.std(c[ic], ddof=1)
            if sc > 0:
                ratios.append(sh / sc)
        sd_ratio[metric] = {"sd_hybrid": float(np.std(h, ddof=1)), "sd_cnn": float(np.std(c, ddof=1)),
                            "ratio": float(np.std(h, ddof=1) / np.std(c, ddof=1)) if np.std(c, ddof=1) > 0 else None,
                            "resample_ci95_descriptive": [float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5))] if ratios else None,
                            "n_seeds": 5}
    # paired comparisons on seed-averaged scores (the X2 protocol), Holm within metric
    mean = {m: np.mean([seeds[m][s] for s in sorted(seeds[m])], axis=0) for m in ARMS}
    comps = []
    for metric, stat in STAT.items():
        pv = {}
        for a, b in PAIRS:
            r = paired_bootstrap_diff(stat, y, mean[a], mean[b])
            comps.append({"protocol": tag, "metric": metric, "A": a, "B": b, **r})
            pv[f"{a}|{b}"] = r["p_two_sided"]
        adj = holm(pv)
        for c in comps:
            if c["metric"] == metric and c["protocol"] == tag:
                c["p_holm_within_metric"] = adj[f"{c['A']}|{c['B']}"]
                c["better_is"] = "higher" if metric in ("auc_pr", "f1") else "lower"
    return {"protocol": tag, "n_test": int(len(y)), "n_positive": int(y.sum()), "per_seed": per_seed, "stability": stab,
            "sd_ratio_hybrid_over_cnn": sd_ratio, "comparisons": pd.DataFrame(comps),
            "reconciliation_max_abs_diff": recon[["d_f1", "d_brier", "d_ece", "d_auc_pr"]].max().to_dict(), "n_reconciled": int(len(recon)),
            "seed_averaged_metrics": {m: metrics(y, mean[m]) for m in ARMS}}


def main() -> int:
    rng = np.random.default_rng(20261108)
    OUT.mkdir(parents=True, exist_ok=True)
    res = {t: protocol(t, rng) for t in ("official", "time_blocked")}
    per_seed = pd.concat([r["per_seed"] for r in res.values()]); comps = pd.concat([r["comparisons"] for r in res.values()])
    per_seed.to_csv(OUT / "per_seed_metrics.csv", index=False); comps.to_csv(OUT / "paired_comparisons.csv", index=False)
    # decision for K8: does the fusion contribute calibration or stability beyond the single branches, with significance?
    def sig(tag, metric, a, b):
        c = comps[(comps.protocol == tag) & (comps.metric == metric) & (comps.A == a) & (comps.B == b)].iloc[0]
        return {"diff": float(c["diff"]), "ci95": [float(c.ci_low), float(c.ci_high)], "p_holm": float(c.p_holm_within_metric),
                "significant_holm_0.05": bool(c.p_holm_within_metric < 0.05)}
    verdict = {}
    for tag in res:
        verdict[tag] = {"ece_hybrid_minus_cnn": sig(tag, "ece", "hybrid", "cnn"), "ece_hybrid_minus_fcnn": sig(tag, "ece", "hybrid", "fcnn"),
                        "brier_hybrid_minus_cnn": sig(tag, "brier", "hybrid", "cnn"), "brier_hybrid_minus_fcnn": sig(tag, "brier", "hybrid", "fcnn"),
                        "auc_pr_hybrid_minus_cnn": sig(tag, "auc_pr", "hybrid", "cnn"), "auc_pr_hybrid_minus_fcnn": sig(tag, "auc_pr", "hybrid", "fcnn"),
                        "f1_hybrid_minus_cnn": sig(tag, "f1", "hybrid", "cnn"), "f1_hybrid_minus_fcnn": sig(tag, "f1", "hybrid", "fcnn"),
                        "seed_sd": {m: {k: float(res[tag]["stability"].loc[m, f"{k}_std"]) for k in ("f1", "ece", "brier", "auc_pr")} for m in ARMS},
                        "sd_ratio_hybrid_over_cnn": res[tag]["sd_ratio_hybrid_over_cnn"]}
    out = {"experiment": "X10 / E6 OPS-SAT branch comparison from regenerated per-seed archives (no training)",
           "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed_resampling": 20261108,
           "inputs": {str(p.relative_to(ROOT)): sha(p) for p in sorted(REGEN.glob("test_scores_*.npz")) + sorted(REGEN.glob("per_run_*.csv"))},
           "statistical_protocol": "X2 protocol: seed-averaged scores, paired_bootstrap_diff(n_boot=2000, seed=0), Holm within metric over 3 contrasts",
           "k8_claims_under_test": THRESHOLD_FOR_K8,
           "protocols": {t: {k: v for k, v in r.items() if k not in ("per_seed", "comparisons", "stability")} | {"stability": r["stability"].round(5).to_dict()} for t, r in res.items()},
           "verdict": verdict,
           "caveats": ["the single-branch arms are separately trained models (cnn, fcnn), not lesioned copies of the fused network",
                       "cnn is not seed-reproducible (Phase 2.1); all numbers come from the 2026-11-06 regeneration",
                       "seed-SD intervals rest on five values and are descriptive",
                       "the official split interleaves in time; time_blocked is the temporally valid protocol"]}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    pd.set_option("display.width", 220)
    for t, r in res.items():
        print(f"\n=== {t}: n={r['n_test']}, positives={r['n_positive']}; reconciliation max|Δ| {r['reconciliation_max_abs_diff']}")
        print(r["stability"].round(4).to_string())
        c = r["comparisons"]; print(c[["metric", "A", "B", "diff", "ci_low", "ci_high", "p_two_sided", "p_holm_within_metric"]].to_string(index=False, float_format=lambda v: f"{v:.4f}"))
        print("SD ratio hybrid/cnn:", {k: (round(v["ratio"], 3) if v["ratio"] else None, [round(x, 2) for x in v["resample_ci95_descriptive"]] if v["resample_ci95_descriptive"] else None) for k, v in r["sd_ratio_hybrid_over_cnn"].items()})
    print(f"\nwritten {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
