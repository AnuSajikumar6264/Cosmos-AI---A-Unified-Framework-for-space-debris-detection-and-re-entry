"""Exploratory ranking-utility evaluation of the decision-priority rule on the archived T1 window.

    python scripts/t1_ranking_utility.py

Protocol: docs/research/T1_RANKING_UTILITY_PROTOCOL.md (declared before this script was run). Reads the archived
T1 object table only; writes outputs/t1_ranking_utility/{results.json, precision_at_k.csv, run.log}. Exploratory and
non-blind by construction; nothing is refit.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cosmos.ai.provenance import git_revision, sha256_file  # noqa: E402

TABLE = ROOT / "outputs/benchmarks/twin_prospective_t1/t1_objects.csv.gz"
OUT = ROOT / "outputs/t1_ranking_utility"
KS = (10, 25, 50, 100, 250)
SEED, B = 20261108, 2000
CONSEQUENCE_MASS_KG, MULTIPLIER = 500.0, 2.0   # the rule as recorded in run manifests (adapters.PRIORITY_RULE)


def rank_scores(df: pd.DataFrame) -> dict[str, np.ndarray]:
    p = df["p_30d"].fillna(0.0).to_numpy(float)
    mass = df["mass"].to_numpy(float)
    rule = p * np.where(np.nan_to_num(mass, nan=0.0) >= CONSEQUENCE_MASS_KG, MULTIPLIER, 1.0)
    return {
        "deployed_rule": rule,
        "p_30d_alone": p,
        "physics_prior": df["p_physics_prior_30d"].fillna(0.0).to_numpy(float),
        "lifetime_expert": df["p_lifetime_30d"].fillna(0.0).to_numpy(float),
        "perigee_ascending": -df["perigee"].fillna(np.inf).to_numpy(float),
    }


def order(score: np.ndarray, norad: np.ndarray) -> np.ndarray:
    return np.lexsort((norad, -score))                    # score descending, NORAD ascending for ties


def at_k(idx: np.ndarray, y: np.ndarray, mass: np.ndarray, k: int) -> dict:
    top = idx[:k]; hits = y[top] == 1
    hc = hits & (np.nan_to_num(mass[top], nan=0.0) >= CONSEQUENCE_MASS_KG)
    return {"k": k, "hits": int(hits.sum()), "precision": float(hits.mean()), "recall": float(hits.sum() / max(int(y.sum()), 1)),
            "high_consequence_hits": int(hc.sum()), "high_consequence_mass_kg": float(np.nansum(mass[top][hc]))}


def _topk(score: np.ndarray, norad: np.ndarray, k: int) -> np.ndarray:
    """Indices of the k highest scores, ties broken by NORAD ascending — identical to lexsort((norad, -score))[:k]."""
    if k >= len(score):
        return order(score, norad)
    cand = np.argpartition(-score, k)[: k + 1]                       # a superset containing all k best scores
    # include every element tied with the k-th score so that the tie-break can be applied exactly
    kth = np.sort(score[cand])[::-1][k - 1]
    cand = np.flatnonzero(score >= kth)
    return cand[np.lexsort((norad[cand], -score[cand]))][:k]


def cluster_bootstrap_diff(df: pd.DataFrame, a: np.ndarray, b: np.ndarray, y: np.ndarray, k: int, rng: np.random.Generator) -> dict:
    fam = df["launch_family"].fillna("none").to_numpy()
    norad = df["norad"].to_numpy()
    families, inverse = np.unique(fam, return_inverse=True)
    members = [np.flatnonzero(inverse == i) for i in range(len(families))]
    ia, ib = _topk(a, norad, k), _topk(b, norad, k)
    if np.array_equal(ia, ib):
        return {"k": k, "identical_top_k": True, "difference": 0.0, "ci95": [0.0, 0.0]}
    point = float((y[ia] == 1).mean() - (y[ib] == 1).mean())
    diffs = np.empty(B)
    for i in range(B):
        picked = rng.integers(0, len(families), size=len(families))
        rows = np.concatenate([members[f] for f in picked])
        ya = y[rows]; na = norad[rows]
        diffs[i] = float((ya[_topk(a[rows], na, k)] == 1).mean()) - float((ya[_topk(b[rows], na, k)] == 1).mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"k": k, "identical_top_k": False, "difference": point, "ci95": [float(lo), float(hi)], "B": B}


def main() -> int:
    t0 = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    full = pd.read_csv(TABLE, low_memory=False)
    rng = np.random.default_rng(SEED)
    result = {"protocol": "docs/research/T1_RANKING_UTILITY_PROTOCOL.md", "exploratory": True, "blind": False,
              "why_not_blind": "the T1 outcomes were analysed before this evaluation (X7, twin_prospective_t1)",
              "analysed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": git_revision(ROOT),
              "input": {"path": str(TABLE.relative_to(ROOT)), "sha256": sha256_file(TABLE), "rows": int(len(full))},
              "rule": {"formula": "priority = p_30d * (2.0 if mass_kg >= 500 else 1.0)", "consequence_mass_kg": CONSEQUENCE_MASS_KG,
                       "multiplier": MULTIPLIER, "source": "run manifest priority_rule (adapters.PRIORITY_RULE)"},
              "seed": SEED, "bootstrap_B": B, "populations": {}}
    rows_csv = []
    populations = (
        ("x7_uncontrolled_natural_decay_with_history", full[(full["regime"] == "natural_decay") & full["p_physics_history_30d"].notna()]),
        ("natural_decay_all", full[full["regime"] == "natural_decay"]),
        ("all_objects", full),
    )
    for pop_name, df in ((n, d.reset_index(drop=True)) for n, d in populations):
        scores = rank_scores(df); norad = df["norad"].to_numpy(); mass = df["mass"].to_numpy(float)
        pop: dict = {"n": int(len(df))}
        for horizon in ("y_30d", "y_72d"):
            y = df[horizon].fillna(0).to_numpy(int)
            h: dict = {"events": int(y.sum()), "base_rate": float(y.mean()), "rankings": {}}
            for name, score in scores.items():
                idx = order(score, norad)
                h["rankings"][name] = [at_k(idx, y, mass, k) for k in KS]
                for r, k in zip(h["rankings"][name], KS):          # the fast top-k must agree with the full ordering
                    assert set(_topk(score, norad, k).tolist()) == set(idx[:k].tolist())
                for r in h["rankings"][name]:
                    rows_csv.append({"population": pop_name, "horizon": horizon, "ranking": name, **r})
            h["rankings"]["base_rate_random"] = [{"k": k, "precision": float(y.mean()), "recall": float(k * y.mean() / max(int(y.sum()), 1))} for k in KS]
            h["paired_cluster_bootstrap"] = {
                f"rule_minus_p30d_k{k}": cluster_bootstrap_diff(df, scores["deployed_rule"], scores["p_30d_alone"], y, k, rng) for k in (25, 50)
            } | {
                f"rule_minus_perigee_k{k}": cluster_bootstrap_diff(df, scores["deployed_rule"], scores["perigee_ascending"], y, k, rng) for k in (25, 50)
            }
            pop[horizon] = h
        result["populations"][pop_name] = pop
    result["elapsed_s"] = round(time.perf_counter() - t0, 1)
    (OUT / "results.json").write_text(json.dumps(result, indent=1, default=str) + "\n")
    pd.DataFrame(rows_csv).to_csv(OUT / "precision_at_k.csv", index=False)
    lines = [f"T1 ranking utility (exploratory, non-blind) — {result['analysed_at']}"]
    for pop_name, pop in result["populations"].items():
        for horizon in ("y_30d", "y_72d"):
            h = pop[horizon]
            lines.append(f"{pop_name} n={pop['n']} {horizon} events={h['events']} base_rate={h['base_rate']:.5f}")
            for name, rows in h["rankings"].items():
                lines.append("  " + f"{name:18s} " + " ".join(f"P@{r['k']}={r['precision']:.3f}" for r in rows))
            for key, d in h["paired_cluster_bootstrap"].items():
                lines.append(f"  {key}: " + ("identical top-k" if d["identical_top_k"] else f"diff={d['difference']:+.3f} ci95={d['ci95'][0]:+.3f}..{d['ci95'][1]:+.3f}"))
    (OUT / "run.log").write_text("\n".join(lines) + "\n")
    print("\n".join(lines)); print("written", OUT.relative_to(ROOT), "in", result["elapsed_s"], "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
