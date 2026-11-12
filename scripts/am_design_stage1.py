"""X6 Stage 1 — am_design missingness: subgroup coverage and odds-ratio stability from archives only.

    python scripts/am_design_stage1.py

Protocol: docs/publication/AM_DESIGN_MISSINGNESS_ABLATION_PROTOCOL.md §4 (subgroup analysis, no refitting)
and §7 Stage 1. Nothing is fitted. Inputs: the archived test/tune-B predictions of origins 2011 and
2016, the cohort split function that produced them, and the physics class prior (built from each
origin's training split exactly as `run.py` does) to label each object's area-to-mass source.
Origin 2006 is not touched (protocol §9).

  RQ-D / A3  coverage and width of the deployed `cosmos_gated` 80 % and 90 % intervals split by
             am_source ∈ {design, class_prior_design, class_prior_sbm}; launch-family cluster bootstrap
             (4,000 draws, seed 20261027, protocol §5) for each subgroup and for the design − sbm
             difference; the pre-specified rule is "difference CI excludes 0".
  RQ-C / A4  cluster-robust adjusted odds ratio of 30-day decay given design-A/M missing
             (`cosmos.ai.lifetime.leak_check.adjusted_or`, unchanged) per calendar window — the split
             windows train / tune-A / tune-B / test, which are defined on t0 — for all uncontrolled
             classes and for components only (the subset the archived leak_check reported); A4 compares
             the training and test windows by CI overlap.
"""
from __future__ import annotations

import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cosmos.ai.lifetime import physics as PH  # noqa: E402
from cosmos.ai.lifetime import run as LR  # noqa: E402
try:  # the archived estimator needs statsmodels, which is not installed here
    import statsmodels  # noqa: F401
    from cosmos.ai.lifetime.leak_check import adjusted_or  # noqa: E402
    ESTIMATOR = "cosmos.ai.lifetime.leak_check.adjusted_or (statsmodels)"
except ModuleNotFoundError:
    from scripts.cluster_logit import adjusted_or, validate_against_archive  # noqa: E402
    ESTIMATOR = "scripts.cluster_logit.adjusted_or (numpy re-implementation; validated against leak_check.json before use)" 

ORIG = {"2011": "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled", "2016": "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled"}
OUT = ROOT / "outputs/am_design_stage1"
N_BOOT, SEED = 4000, 20261027
ARMS = ("cosmos_gated", "physics_only")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def am_source(df: pd.DataFrame, prior: dict) -> np.ndarray:
    """The rule of physics.sample_log_am, without drawing samples."""
    design = np.log10(df["am_design"].to_numpy(float))
    types = df["type1"].astype(str).to_numpy()
    has_d = np.isfinite(design)
    intact = ~has_d & np.isin(types, list(prior["am"]))
    src = np.where(has_d, "design", np.where(intact, "class_prior_design", "class_prior_sbm"))
    return src


def cluster_boot(values: np.ndarray, fam: np.ndarray, rng, n_boot: int) -> np.ndarray:
    codes, inv = np.unique(fam, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=len(codes)); cnt = np.bincount(inv, minlength=len(codes)).astype(float)
    draws = rng.integers(0, len(codes), size=(n_boot, len(codes)))
    return sums[draws].sum(1) / cnt[draws].sum(1)


def main() -> int:
    cohort = LR.load_cohort()
    res: dict = {"experiment": "X6 Stage 1 — am_design missingness, archives only (no fitting)",
                 "protocol": "docs/publication/AM_DESIGN_MISSINGNESS_ABLATION_PROTOCOL.md §4, §7 Stage 1", "n_boot": N_BOOT, "seed": SEED,
                 "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "origins": {}}
    cov_rows, or_rows = [], []
    for o, d in ORIG.items():
        dd = ROOT / d
        S = LR.split(cohort, o, "uncontrolled")
        summ = json.loads((dd / "summary.json").read_text())
        prior = PH.class_prior_from(S["train"])
        te = np.load(dd / "test_predictions.npz", allow_pickle=True)
        test = S["test"].reset_index(drop=True)
        assert len(test) == len(te["z"])
        src = am_source(test, prior)
        counts = pd.Series(src).value_counts().to_dict()
        assert counts == {k: v for k, v in summ["am_source_test"].items() if v}, (counts, summ["am_source_test"])
        src_tb = am_source(S["tuneB"], prior); counts_tb = pd.Series(src_tb).value_counts().to_dict()
        assert counts_tb == {k: v for k, v in summ["am_source_tuneB"].items() if v}, (counts_tb, summ["am_source_tuneB"])
        m = te["known5"].astype(bool); z = te["z"]; fam = test["launch_family"].astype(str).to_numpy()
        rng = np.random.default_rng(SEED)
        orig = {"selected_learner": summ["best_learner_on_tuneA"], "am_source_counts": {"train": summ["am_source_train"], "tuneB": counts_tb, "test": counts},
                "design_share": {k: round(v.get("design", 0) / sum(v.values()), 4) for k, v in (("train", summ["am_source_train"]), ("tuneB", counts_tb), ("test", counts))},
                "coverage": {}, "coverage_difference_design_minus_sbm": {}, "odds_ratios": {}}
        for arm in ARMS + (summ["best_learner_on_tuneA"],):
            for lev in ("80", "90"):
                lo, hi = te[f"{arm}__lo{lev}"], te[f"{arm}__hi{lev}"]
                cov = ((lo <= z) & (z <= hi)).astype(float); width = hi - lo
                groups = {}
                for g in ("design", "class_prior_design", "class_prior_sbm", "all"):
                    sel = m & ((src == g) if g != "all" else True)
                    if sel.sum() == 0:
                        continue
                    bt = cluster_boot(cov[sel], fam[sel], rng, N_BOOT)
                    groups[g] = {"n": int(sel.sum()), "coverage": float(cov[sel].mean()), "ci95": [float(np.percentile(bt, 2.5)), float(np.percentile(bt, 97.5))],
                                 "mean_width_log10": float(width[sel].mean())}
                    cov_rows.append({"origin": o, "arm": arm, "level": int(lev) / 100, "am_source": g, **groups[g]})
                orig["coverage"][f"{arm}@{lev}"] = groups
                if "design" in groups and "class_prior_sbm" in groups:
                    sd, ss = m & (src == "design"), m & (src == "class_prior_sbm")
                    rd = np.random.default_rng(SEED + 1)
                    diff = cluster_boot(cov[sd], fam[sd], rd, N_BOOT) - cluster_boot(cov[ss], fam[ss], np.random.default_rng(SEED + 2), N_BOOT)
                    point = float(cov[sd].mean() - cov[ss].mean()); lo_, hi_ = np.percentile(diff, [2.5, 97.5])
                    orig["coverage_difference_design_minus_sbm"][f"{arm}@{lev}"] = {"diff": point, "ci95": [float(lo_), float(hi_)],
                                                                                  "A3_rule_ci_excludes_zero": bool(lo_ > 0 or hi_ < 0)}
        # RQ-C / A4: adjusted OR per calendar window (the split windows are defined on t0)
        for win in ("train", "tuneA", "tuneB", "test"):
            w = S[win][S[win]["y_30d"].notna()].copy()
            w["design_missing"] = ~np.isfinite(w["am_design"].astype(float))
            entry = {"window": win, "t0_range": [str(w.t0.min().date()), str(w.t0.max().date())], "n": int(len(w)), "share_design_missing": float(w.design_missing.mean())}
            for pop, sub in (("uncontrolled_all", w), ("components_only", w[w.type1.eq("C")])):
                try:
                    r = adjusted_or(sub.copy(), "design_missing") if sub.design_missing.nunique() > 1 and sub.y_30d.sum() >= 5 else {"odds_ratio": None, "note": "not estimable"}
                except Exception as exc:  # recorded, not hidden
                    r = {"odds_ratio": None, "note": repr(exc)[:200]}
                if r.get("odds_ratio") is not None:
                    lo_, hi_ = r["ci95"]
                    # quasi-complete separation in a small window gives an unbounded estimate; flag it, keep it
                    r["degenerate"] = bool(r["odds_ratio"] > 1e3 or r["odds_ratio"] < 1e-3 or lo_ <= 0 or hi_ / max(lo_, 1e-300) > 1e3)
                entry[pop] = r
                or_rows.append({"origin": o, "window": win, "population": pop, **{k: v for k, v in r.items() if k != "se"}})
            orig["odds_ratios"][win] = entry
        tr, ts = orig["odds_ratios"]["train"]["uncontrolled_all"], orig["odds_ratios"]["test"]["uncontrolled_all"]
        if tr.get("odds_ratio") and ts.get("odds_ratio"):
            orig["A4_train_vs_test_uncontrolled"] = {"train_or": tr["odds_ratio"], "train_ci": tr["ci95"], "test_or": ts["odds_ratio"], "test_ci": ts["ci95"],
                                                     "cis_non_overlapping": bool(tr["ci95"][1] < ts["ci95"][0] or ts["ci95"][1] < tr["ci95"][0])}
        orig["inputs"] = {"test_predictions_sha256": sha(dd / "test_predictions.npz"), "summary_sha256": sha(dd / "summary.json")}
        res["origins"][o] = orig
        print(f"origin {o}: am_source test {counts} (validated against summary.json); tuneB design share {orig['design_share']['tuneB']}, test {orig['design_share']['test']}")
        for key, g in orig["coverage"].items():
            if key.startswith("cosmos_gated"):
                print(f"  {key}: " + "; ".join(f"{k} cov {v['coverage']:.3f} [{v['ci95'][0]:.3f},{v['ci95'][1]:.3f}] n={v['n']} w={v['mean_width_log10']:.2f}" for k, v in g.items()))
        for key, dlt in orig["coverage_difference_design_minus_sbm"].items():
            print(f"  Δ(design−sbm) {key}: {dlt['diff']:+.3f} [{dlt['ci95'][0]:+.3f},{dlt['ci95'][1]:+.3f}] excludes0={dlt['A3_rule_ci_excludes_zero']}")
        for win, e in orig["odds_ratios"].items():
            u, c = e["uncontrolled_all"], e["components_only"]
            print(f"  OR(design missing → 30d decay) {win:5s} {e['t0_range']} n={e['n']} missing={e['share_design_missing']:.2f}: all {u.get('odds_ratio') and round(u['odds_ratio'],3)} {u.get('ci95') and [round(x,3) for x in u['ci95']]} | components {c.get('odds_ratio') and round(c['odds_ratio'],3)} {c.get('ci95') and [round(x,3) for x in c['ci95']]}")
        if "A4_train_vs_test_uncontrolled" in orig:
            print("  A4 train vs test CIs non-overlapping:", orig["A4_train_vs_test_uncontrolled"]["cis_non_overlapping"])
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(cov_rows).to_csv(OUT / "subgroup_coverage.csv", index=False)
    pd.DataFrame(or_rows).to_csv(OUT / "odds_ratios_by_window.csv", index=False)
    res["odds_ratio_estimator"] = ESTIMATOR
    if "numpy" in ESTIMATOR:
        v = validate_against_archive()
        res["estimator_validation_vs_archived_leak_check"] = {o: {k: {"max_rel_diff": x["max_rel_diff"]} for k, x in r.items()} for o, r in v.items()}
        assert all(r["design_missing"]["max_rel_diff"] < 1e-6 for r in v.values()), "numpy estimator does not reproduce the archived design-missing ORs"
    res["stage2_not_run"] = "per authorisation; as specified it is BLOCKED (kumo/tabm backends absent)"
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(f"written {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
