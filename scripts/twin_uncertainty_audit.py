"""Phase 3 — how uncertainty is carried, used and dropped in the deployed twin (2026-11-06).

    python scripts/twin_uncertainty_audit.py --run outputs/phase3_uncertainty/pipeline_full

Measures, on the full as-of 2026-10-27 snapshot and on a full pipeline run over it:

  1. which objects reach the console with which *kind* of uncertainty (time quantiles, horizon
     probabilities only, abstention) and why;
  2. whether the horizon probabilities and the time quantiles that travel together are mutually
     consistent (both describe the same predictive distribution, so p(30 d) must agree with where
     30 days falls among the quantiles);
  3. how much of the reported uncertainty the decision ranking actually uses — it ranks on the point
     probability p(30 d) times a consequence multiplier and carries the interval as a flag only — and
     how different the ordering would be under other summaries of the same distribution.

Nothing is modelled, refitted or modified; the snapshot and the run are read only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"
OUT = ROOT / "outputs/phase3_uncertainty"
H30 = 30.0
TOL = 1e-9


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def consistency(p30: pd.Series, q05: pd.Series, q50: pd.Series, q95: pd.Series) -> dict:
    """p(T <= 30 d) against the position of 30 d among the 5/50/95 % quantiles of T."""
    ok = p30.notna() & q05.notna() & q50.notna() & q95.notna()
    p, a, m, b = p30[ok], q05[ok], q50[ok], q95[ok]
    v_hi = (b < H30) & (p < 0.95 - TOL)          # 95 % of mass before 30 d, yet p < 0.95
    v_med = (m < H30) & (p < 0.5 - TOL)          # median before 30 d, yet p < 0.5
    v_med2 = (m > H30) & (p > 0.5 + TOL)         # median after 30 d, yet p > 0.5
    v_lo = (a > H30) & (p > 0.05 + TOL)          # 5 % quantile after 30 d, yet p > 0.05
    return {"n_checked": int(ok.sum()),
            "violations": {"q95<30d_but_p<0.95": int(v_hi.sum()), "median<30d_but_p<0.5": int(v_med.sum()),
                           "median>30d_but_p>0.5": int(v_med2.sum()), "q05>30d_but_p>0.05": int(v_lo.sum())},
            "any_violation": int((v_hi | v_med | v_med2 | v_lo).sum()),
            "max_abs_gap_median_rule": float(np.where(m < H30, np.clip(0.5 - p, 0, None), np.clip(p - 0.5, 0, None)).max())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default=str(OUT / "pipeline_full"))
    a = ap.parse_args(argv)
    run = Path(a.run)
    t = pd.read_csv(SNAPSHOT, low_memory=False)
    n = len(t)
    res: dict = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "snapshot": str(SNAPSHOT.relative_to(ROOT)), "snapshot_sha256": sha256(SNAPSHOT), "n_objects": n}

    # 1. what kind of uncertainty each object carries ------------------------------------------
    has_re_q = t[["lo90_days", "median_days", "hi90_days"]].notna().all(1)
    has_lt = t[["lifetime_lo90_days", "median_days_lifetime", "lifetime_hi90_days",
                "p_lifetime_30d", "p_lifetime_90d", "p_lifetime_1yr"]].notna().all(1)
    iso_bad = has_lt & ((t.p_lifetime_30d > t.p_lifetime_90d + 1e-12) | (t.p_lifetime_90d > t.p_lifetime_1yr + 1e-12))
    res["uncertainty_kinds"] = {
        "reentry": {"horizon_probabilities_present": int(t[["p_30d", "p_90d", "p_1yr"]].notna().all(1).sum()),
                    "with_time_quantiles": int(has_re_q.sum()),
                    "probabilities_only_no_quantiles": int((~has_re_q).sum()),
                    "by_regime_with_quantiles": t[has_re_q].regime.value_counts().to_dict(),
                    "by_regime_without_quantiles": t[~has_re_q].regime.value_counts().to_dict()},
        "lifetime": {"learned_reading_present": int(has_lt.sum()), "absent_physics_only": int((~has_lt).sum()),
                     "present_but_isotonic_incoherent_abstained_by_adapter": int(iso_bad.sum())},
        "mass": {"known": int(t.mass.notna().sum()), "unknown": int(t.mass.isna().sum()),
                 "known_share_among_uncontrolled_with_quantiles": float(t.loc[has_re_q, "mass"].notna().mean())},
    }

    # 2. internal consistency of probabilities vs quantiles ---------------------------------------
    res["consistency_p30_vs_time_quantiles"] = {
        "reentry_reported_p_30d_vs_lo90_median_hi90": consistency(t.p_30d, t.lo90_days, t.median_days, t.hi90_days),
        "lifetime_isotonic_p_lifetime_30d_vs_lifetime_quantiles": consistency(
            t.p_lifetime_30d, t.lifetime_lo90_days, t.median_days_lifetime, t.lifetime_hi90_days),
        "lifetime_coherent_p_lifetime_raw_30d_vs_lifetime_quantiles": consistency(
            t.p_lifetime_raw_30d, t.lifetime_lo90_days, t.median_days_lifetime, t.lifetime_hi90_days),
        "physics_history_p_30d_vs_reentry_quantiles": consistency(
            t.p_physics_history_30d, t.lo90_days, t.median_days, t.hi90_days),
        "note": ("the reported reentry quantiles (lo90/median/hi90) and the reported p_30d need not come "
                 "from one distribution if the gate mixes variants; violations quantify that, they are not "
                 "a bug by themselves — but a consumer reading both as one forecast would be misled"),
    }

    # 3. what the decision ranking uses --------------------------------------------------------------
    rank = None
    if (run / "decision_ranking.csv").is_file():
        rank = pd.read_csv(run / "decision_ranking.csv")
        re = pd.read_csv(run / "reentry_predictions.csv")
        man = json.loads((run / "run_manifest.json").read_text())
        res["pipeline_run"] = {
            "dir": str(run.relative_to(ROOT)) if run.is_relative_to(ROOT) else str(run),
            "duration_s": man.get("duration_s"),
            "modules": {k: {"status": v["status"], "outputs": v.get("outputs"), "abstentions": v.get("abstentions"),
                            "abstained_total": v.get("abstained_total")} for k, v in man["modules"].items()},
            "reentry_uncertainty_kind_counts": re.uncertainty_kind.value_counts().to_dict(),
            "ranking_rows": int(len(rank)),
            "ranking_columns": list(rank.columns),
            "uncertainty_fields_entering_priority_score": ["p_reentry_30d (point)", "high_consequence (mass >= 500 kg)"],
            "uncertainty_fields_carried_but_not_used": ["reentry_interval_available (flag)", "days_q05/q50/q95 (in reentry table only)"],
        }
        m = rank.merge(re[["object_id", "days_q05", "days_q50", "days_q95"]], on="object_id", how="left")
        res["ranking_vs_interval"] = {}
        for top in (50, 200, 1000):
            h = m.head(top)
            q = h.dropna(subset=["days_q05", "days_q95"])
            res["ranking_vs_interval"][f"top{top}"] = {
                "with_quantiles": int(len(q)),
                "interval_entirely_before_30d": int((q.days_q95 < H30).sum()),
                "interval_straddles_30d": int(((q.days_q05 <= H30) & (q.days_q95 >= H30)).sum()),
                "interval_entirely_after_30d": int((q.days_q05 > H30).sum()),
                "median_width_ratio_q95_over_q05": float((q.days_q95 / q.days_q05.clip(lower=1e-9)).median()),
                "p30_min": float(h.p_reentry_30d.min()), "mass_unknown": int((~h.mass_known).sum()),
                "high_consequence": int(h.high_consequence.sum()),
            }
        # how much the ordering depends on the summary used (same distribution, different statistic)
        top = m.head(1000).dropna(subset=["days_q50", "days_q95"]).copy()
        base = (-top.priority_score).rank(method="average")
        alts = {"by_median_days_ascending": top.days_q50.rank(method="average"),
                "by_q95_days_ascending_pessimistic": top.days_q95.rank(method="average"),
                "by_q05_days_ascending_optimistic": top.days_q05.rank(method="average"),
                "by_p30_without_consequence_multiplier": (-top.p_reentry_30d).rank(method="average")}
        res["ranking_sensitivity_top1000"] = {k: {"kendall_tau_vs_deployed": float(kendalltau(base, v)[0]),
                                                  "top50_overlap": int(len(set(top.object_id[base.argsort()[:50]])
                                                                           & set(top.object_id[v.argsort()[:50]])))}
                                             for k, v in alts.items()}
        res["ties_in_priority_score"] = {"top50_distinct_scores": int(rank.head(50).priority_score.round(12).nunique()),
                                         "objects_at_priority_2.0": int((rank.priority_score >= 2.0 - 1e-12).sum()),
                                         "objects_at_p30_1.0": int((rank.p_reentry_30d >= 1.0 - 1e-12).sum())}
    else:
        res["pipeline_run"] = {"status": "not found", "dir": str(run)}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "twin_uncertainty_audit.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: res[k] for k in ("uncertainty_kinds", "consistency_p30_vs_time_quantiles")}, indent=1, default=float))
    if rank is not None:
        print(json.dumps({k: res[k] for k in ("ranking_vs_interval", "ranking_sensitivity_top1000", "ties_in_priority_score")},
                         indent=1, default=float))
        print("modules:", {k: (v["status"], v.get("abstained_total")) for k, v in res["pipeline_run"]["modules"].items()})
    print(f"written {OUT.relative_to(ROOT)}/twin_uncertainty_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
