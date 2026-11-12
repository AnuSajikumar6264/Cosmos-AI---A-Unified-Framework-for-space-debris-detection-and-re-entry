"""Cluster-robust logistic regression without statsmodels, mirroring `leak_check.adjusted_or`.

The archived estimator is `statsmodels.Logit(...).fit(cov_type="cluster", cov_kwds={"groups": g})`
(Newton MLE; sandwich covariance with statsmodels' default small-sample correction
G/(G-1) * (N-1)/(N-K)). statsmodels is not installed in this environment, so the same model is
computed here in numpy with the SAME design matrix as `leak_check.adjusted_or`. It is validated
against the archived `leak_check.json` values before being used (see `validate_against_archive`).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys as _sys
_sys.path.insert(0, str(ROOT))


def design(d: pd.DataFrame, flag: str) -> pd.DataFrame:
    X = pd.DataFrame({"log_perigee": np.log10(d["perigee"].clip(lower=100)), "log_apogee": np.log10(d["apogee"].clip(lower=100)),
                      "inc": d["inc"] / 90.0, flag: d[flag].astype(float)})
    cats = [pd.get_dummies(d["t0"].dt.year // 10 * 10, prefix="dec", drop_first=True)]
    if d["type1"].nunique() > 1:
        cats.append(pd.get_dummies(d["type1"], prefix="cls", drop_first=True))
    X = pd.concat([X] + cats, axis=1).astype(float)
    X.insert(0, "const", 1.0)
    return X


def logit_mle(X: np.ndarray, y: np.ndarray, max_iter: int = 100, tol: float = 1e-10) -> np.ndarray:
    b = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None]) + 1e-12 * np.eye(X.shape[1])
        step = np.linalg.solve(H, X.T @ (y - p))
        b = b + step
        if np.max(np.abs(step)) < tol:
            break
    return b


def cluster_robust_se(X: np.ndarray, y: np.ndarray, b: np.ndarray, groups: np.ndarray) -> np.ndarray:
    p = 1 / (1 + np.exp(-X @ b))
    H = X.T @ (X * (p * (1 - p))[:, None])
    Hinv = np.linalg.inv(H)
    scores = X * (y - p)[:, None]
    G = groups.max() + 1
    S = np.zeros((X.shape[1], X.shape[1]))
    for g in range(G):
        s = scores[groups == g].sum(0)
        S += np.outer(s, s)
    n, k = X.shape
    corr = G / (G - 1.0) * ((n - 1.0) / (n - k))
    V = Hinv @ S @ Hinv * corr
    return np.sqrt(np.diag(V))


def adjusted_or(d: pd.DataFrame, flag: str) -> dict:
    X = design(d, flag)
    y = d["y_30d"].to_numpy(float)
    groups = pd.factorize(d["launch_family"].astype(str))[0]
    b = logit_mle(X.to_numpy(float), y)
    se = cluster_robust_se(X.to_numpy(float), y, b, groups)
    j = list(X.columns).index(flag)
    return {"odds_ratio": float(np.exp(b[j])), "ci95": [float(np.exp(b[j] - 1.96 * se[j])), float(np.exp(b[j] + 1.96 * se[j]))], "n": int(len(d)),
            "clusters": int(groups.max() + 1), "se": "cluster-robust (launch family), numpy re-implementation of statsmodels Logit cov_type=cluster"}


def validate_against_archive() -> dict:
    """Recompute the archived components-only ORs (train split, both origins) and compare."""
    from cosmos.ai.lifetime import run as LR
    arch = json.loads((ROOT / "outputs/benchmarks/reentry_lifetime/leak_check.json").read_text())
    df = LR.load_cohort()
    out = {}
    for o in ("2016", "2011"):
        S = LR.split(df, o, "uncontrolled")
        d = S["train"][S["train"]["y_30d"].notna()].copy()
        d["rcs_missing"] = d["rcs_m2"].isna()
        c = d[d["type1"].eq("C")].copy(); c["design_missing"] = ~np.isfinite(c["am_design"])
        mine = adjusted_or(c, "design_missing"); ref = arch[f"o{o}.train"]["components_adjusted_or_design_missing"]
        mine_r = adjusted_or(d, "rcs_missing"); ref_r = arch[f"o{o}.train"]["adjusted_or_rcs_missing"]
        out[o] = {"design_missing": {"mine": mine, "archived": ref, "max_rel_diff": max(abs(mine["odds_ratio"] - ref["odds_ratio"]) / ref["odds_ratio"],
                                                                                   *[abs(a - b) / b for a, b in zip(mine["ci95"], ref["ci95"])])},
                  "rcs_missing": {"mine": mine_r, "archived": ref_r, "max_rel_diff": max(abs(mine_r["odds_ratio"] - ref_r["odds_ratio"]) / ref_r["odds_ratio"],
                                                                                    *[abs(a - b) / b for a, b in zip(mine_r["ci95"], ref_r["ci95"])])}}
    return out


if __name__ == "__main__":
    v = validate_against_archive()
    for o, r in v.items():
        for k, x in r.items():
            print(o, k, "mine", round(x["mine"]["odds_ratio"], 4), [round(z, 4) for z in x["mine"]["ci95"]], "archived", round(x["archived"]["odds_ratio"], 4),
                  [round(z, 4) for z in x["archived"]["ci95"]], "max rel diff", f"{x['max_rel_diff']:.2e}")
