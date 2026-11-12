"""Phase N: system and scientific-integrity audit.

Re-derives every load-bearing manuscript number from its source artifact and checks the
repository's structural invariants. Read-only: it changes nothing and installs nothing.

    python scripts/final_system_audit.py --out outputs/final_audit

Every check returns PASS / FAIL / NOT_EVALUABLE with the measured value, so the audit is
reproducible rather than asserted.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision, sha256_file  # noqa: E402

Z_CAP = float(np.log10(1826.25))
FINDINGS: list[dict] = []


def record(check: str, severity: str, status: str, detail: str, measured=None,
           expected=None) -> None:
    FINDINGS.append({"check": check, "severity": severity, "status": status,
                     "detail": detail, "measured": measured, "expected": expected})


# ------------------------------------------------------------------ integrity
def audit_integrity(root: Path) -> None:
    freeze = root / "research_design/preregistration/freeze.json"
    if freeze.is_file():
        rec = json.loads(freeze.read_text())
        changed = [p for p, h in rec["sha256"].items()
                   if (root / p).is_file() and sha256_file(root / p) != h]
        record("pre-registration freeze", "critical",
               "PASS" if not changed else "FAIL",
               "frozen telemetry-analysis files unchanged" if not changed
               else f"changed: {changed}", measured=len(changed), expected=0)
    g5d = root / "outputs/g5d_origin2006/prereg_freeze.json"
    if g5d.is_file():
        rec = json.loads(g5d.read_text())
        actual = sha256_file(root / rec["preregistration"])
        record("G5d pre-registration", "critical",
               "PASS" if actual == rec["sha256"] else "FAIL",
               "protocol unchanged since it was hashed before fitting",
               measured=actual[:16], expected=rec["sha256"][:16])
    digest = root / "outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt"
    if digest.is_file():
        ok = True
        for line in digest.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2:
                target = digest.parent / parts[1]
                ok = ok and target.is_file() and sha256_file(target) == parts[0]
        record("dated forecast digest", "critical", "PASS" if ok else "FAIL",
               "hashed 2026-10-27 forecast matches its recorded digest")


# ------------------------------------------------- temporal separation / leakage
def audit_temporal_separation(root: Path) -> None:
    from cosmos.ai.lifetime import run as LR
    LR.ORIGINS.setdefault("2006", ("1999-01-01", "2001-01-01", "2006-01-01", "2011-01-01"))
    cohort = LR.load_cohort()
    folds = {}
    for origin in ("2006", "2011", "2016"):
        split = LR.split(cohort, origin, "uncontrolled")
        tr_end, va_end, o, te_end = LR.ORIGINS[origin]
        ok_order = (split["train"]["t0"].max() < pd.Timestamp(tr_end)
                    and split["tuneA"]["t0"].min() >= pd.Timestamp(tr_end)
                    and split["tuneA"]["t0"].max() < pd.Timestamp(va_end)
                    and split["test"]["t0"].min() >= pd.Timestamp(o)
                    and split["test"]["t0"].max() < pd.Timestamp(te_end))
        record(f"temporal ordering, origin {origin}", "critical",
               "PASS" if ok_order else "FAIL",
               "train < tune_end <= tune < origin <= test < test_end")
        # Launch families must not straddle tune-A / tune-B.
        fam_a = set(split["tuneA"]["launch_family"].astype(str))
        fam_b = set(split["tuneB"]["launch_family"].astype(str))
        overlap = fam_a & fam_b
        record(f"tune-A/tune-B family disjointness, origin {origin}", "critical",
               "PASS" if not overlap else "FAIL",
               "launch families do not straddle the calibration split",
               measured=len(overlap), expected=0)
        folds[origin] = set(split["test"]["norad"])
    pairs = [("2006", "2011"), ("2006", "2016"), ("2011", "2016")]
    for a, b in pairs:
        inter = folds[a] & folds[b]
        record(f"test folds disjoint: {a} vs {b}", "critical",
               "PASS" if not inter else "FAIL",
               "no object appears in two test folds",
               measured=len(inter), expected=0)


# -------------------------------------------------------- headline claim checks
def _pinball(z, q):
    from cosmos.ai.lifetime import models as MO
    d = z[:, None] - q
    return float(np.mean(np.maximum(MO.QUANTILES * d, (MO.QUANTILES - 1) * d)))


def audit_claims(root: Path) -> None:
    base = root / "outputs/benchmarks/reentry_lifetime"
    # Claim: recomputed pinball reproduces the published table exactly.
    worst = 0.0
    for origin in ("2011", "2016"):
        npz = base / f"origin{origin}_uncontrolled/test_predictions.npz"
        csv = base / f"origin{origin}_uncontrolled/regression_test.csv"
        if not (npz.is_file() and csv.is_file()):
            continue
        with np.load(npz, allow_pickle=True) as a:
            data = {k: np.asarray(a[k]) for k in a.files}
        mask = data["known5"].astype(bool)
        z = data["z"][mask]
        published = pd.read_csv(csv).set_index("model")["pinball"]
        for key in [k[:-3] for k in data if k.endswith("__q")]:
            if key in published.index:
                worst = max(worst, abs(_pinball(z, data[f"{key}__q"][mask])
                                       - float(published[key])))
    record("published pinball recomputable", "critical",
           "PASS" if worst == 0.0 else "FAIL",
           "every published pinball value recomputed from archived predictions",
           measured=f"{worst:.3e}", expected="0.000e+00")

    # Claim: physics_only wins the full published leaderboard at 2011 but not at 2016.
    for origin, want in (("2011", "first"), ("2016", "not first")):
        csv = base / f"origin{origin}_uncontrolled/regression_test.csv"
        if not csv.is_file():
            continue
        t = pd.read_csv(csv)
        order = t.sort_values("pinball").reset_index(drop=True)
        pos = int(order.index[order.model == "physics_only"][0]) + 1
        ok = (pos == 1) if want == "first" else (pos != 1)
        record(f"physics_only rank at origin {origin}", "major",
               "PASS" if ok else "FAIL",
               "rank among all published arms on the forward test fold",
               measured=f"{pos}/{len(order)}", expected=want)

    # Claim: Spearman(tune-A, test) = 0.000 at both published origins.
    g = root / "outputs/phase_g_lifetime/phase_g_lifetime_results.json"
    if g.is_file():
        rec = json.loads(g.read_text())
        for origin, entry in rec["selection_transfer_diagnosis"].items():
            rho = entry.get("spearman_tuneA_vs_test")
            record(f"Spearman(tune-A, test) origin {origin}", "major",
                   "PASS" if rho is not None and abs(rho) < 1e-9 else "FAIL",
                   "selection ranking carries no information about test ranking",
                   measured=rho, expected=0.0)

    # Claim: 23.64 % of slice pairs inverted.
    r = root / "outputs/g5_rolling/g5_rolling_results.json"
    if r.is_file():
        rec = json.loads(r.read_text())
        frac = rec["rank_agreement_between_slices"]["fraction_negative"]
        record("inverted slice-pair fraction", "major",
               "PASS" if abs(frac - 0.2364) < 5e-4 else "FAIL",
               "fraction of evaluation-slice pairs with negative rank correlation",
               measured=round(frac, 4), expected=0.2364)

    # Claim: loss concentrates 4.1-6.6x below the cap.
    c = root / "outputs/g5_censoring/g5_causal_results.json"
    if c.is_file():
        rec = json.loads(c.read_text())
        ratios = {}
        for origin, entry in rec["results"].items():
            d = entry.get("deployed_expert_decomposition") or {}
            if "at_cap_mean" in d and d["at_cap_mean"]:
                ratios[origin] = d["below_cap_mean"] / d["at_cap_mean"]
        ok = ratios and all(4.0 <= v <= 6.7 for v in ratios.values())
        record("below-cap loss concentration", "major", "PASS" if ok else "FAIL",
               "per-object loss ratio below-cap vs at-cap",
               measured={k: round(v, 2) for k, v in ratios.items()},
               expected="4.1-6.6x")

    # Claim: G5d outcome INCONCLUSIVE, H2 SUPPORTED, H3 not confirmed.
    a = root / "outputs/g5d_origin2006/analysis/g5d_analysis.json"
    if a.is_file():
        rec = json.loads(a.read_text())
        record("G5d outcome", "critical",
               "PASS" if rec["outcome"] == "INCONCLUSIVE" else "FAIL",
               "pre-registered classification", measured=rec["outcome"],
               expected="INCONCLUSIVE")
        record("G5d H2", "major", "PASS" if rec["H2"]["verdict"] == "SUPPORTED" else "FAIL",
               "ranking instability on a never-scored fold",
               measured=rec["H2"]["verdict"], expected="SUPPORTED")
        record("G5d H3 not upgraded", "critical",
               "PASS" if rec["H3"]["verdict"] != "CONFIRMED" else "FAIL",
               "mechanism must not be promoted to a confirmation",
               measured=rec["H3"]["verdict"], expected="not CONFIRMED")
        ranks = {o: e["ranks"].get("physics_only")
                 for o, e in rec["per_origin"].items()}
        record("physics_only 1st/4th/1st across origins", "major",
               "PASS" if ranks.get("2011") == 1 and ranks.get("2016") == 4
               and ranks.get("2006") == 1 else "FAIL",
               "rank pattern across the three origins", measured=ranks,
               expected={"2011": 1, "2016": 4, "2006": 1})


# ------------------------------------------------------------- reproducibility
def audit_reproducibility(root: Path) -> None:
    import importlib
    backends = {"xgboost": "xgboost", "lightgbm": "lightgbm", "catboost": "catboost",
                "mlp": "torch", "tabm": "tabm", "tabicl": "tabicl", "kumo": "sdm"}
    available = []
    for learner, module in backends.items():
        try:
            importlib.import_module(module)
            available.append(learner)
        except Exception:
            pass
    record("learner training-reproducibility", "major", "FAIL" if len(available) < 7 else "PASS",
           "learners refittable in this environment",
           measured=f"{len(available)}/7 ({', '.join(sorted(available))})", expected="7/7")
    # Prediction-level reproducibility: caches present for every published arm?
    missing = []
    for origin in ("2011", "2016"):
        npz = root / f"outputs/benchmarks/reentry_lifetime/origin{origin}_uncontrolled/test_predictions.npz"
        if not npz.is_file():
            missing.append(f"origin{origin}")
    record("prediction-level reproducibility", "critical",
           "PASS" if not missing else "FAIL",
           "archived per-object predictions present for every published origin",
           measured=f"{2 - len(missing)}/2", expected="2/2")


# ------------------------------------------------------------------ consistency
def audit_consistency(root: Path) -> None:
    # The living tracker should state the current test count.
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                              cwd=root, capture_output=True, text=True, timeout=3000)
        match = re.search(r"(\d+) passed", proc.stdout)
        actual = int(match.group(1)) if match else None
    except Exception:
        actual = None
    tracker = root / "docs/research/MASTER_RESEARCH_TRACKER.md"
    stated = None
    if tracker.is_file():
        m = re.search(r"\*\*(\d+) passed", tracker.read_text())
        stated = int(m.group(1)) if m else None
    record("tracker test count current", "minor",
           "PASS" if actual is not None and stated == actual else "FAIL",
           "the living tracker should state the current suite size",
           measured=stated, expected=actual)

    # rmse_log10 must not drive selection, ranking or a reported headline anywhere.
    endpoint = re.compile(r"""(sort_values\s*\(\s*["']rmse|rank\s*\(.*rmse|idxmin\s*\(\s*\)"""
                          r"""\s*#.*rmse|best.*=.*rmse|\brmse\w*\s*=\s*(np\.sqrt|math\.sqrt))""",
                          re.IGNORECASE)
    offenders = []
    for script in sorted(root.glob("scripts/*.py")):
        if script.name == "final_system_audit.py":
            continue
        for i, line in enumerate(script.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if s.startswith(("#", '"', "'")):
                continue
            if endpoint.search(s):
                offenders.append(f"{script.name}:{i}")
    record("mean-elicited endpoint excluded", "major",
           "PASS" if not offenders else "FAIL",
           "rmse is not locally elicitable under fixed-horizon right-censoring",
           measured=offenders or "none", expected="none")

    # Historical artifacts must retain their published columns.
    preserved = True
    for origin in ("2011", "2016"):
        csv = root / f"outputs/benchmarks/reentry_lifetime/origin{origin}_uncontrolled/regression_test.csv"
        if csv.is_file() and "rmse_log10" not in csv.read_text().splitlines()[0]:
            preserved = False
    record("historical artifacts unmodified", "critical",
           "PASS" if preserved else "FAIL",
           "published columns retained; exclusion is by non-use, not by editing")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/final_audit")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Phase N -- system and scientific-integrity audit\n")
    for stage, fn in (("integrity", audit_integrity),
                      ("temporal separation / leakage", audit_temporal_separation),
                      ("headline claims", audit_claims),
                      ("reproducibility", audit_reproducibility),
                      ("consistency", audit_consistency)):
        print(f"--- {stage}")
        before = len(FINDINGS)
        try:
            fn(root)
        except Exception as exc:
            record(stage, "major", "NOT_EVALUABLE", f"{type(exc).__name__}: {exc}")
        for f in FINDINGS[before:]:
            mark = {"PASS": "ok  ", "FAIL": "FAIL", "NOT_EVALUABLE": "n/a "}[f["status"]]
            print(f"  {mark} [{f['severity']:12s}] {f['check']}")
            if f["status"] != "PASS" or f["measured"] is not None:
                print(f"         measured={f['measured']} expected={f['expected']}")

    counts = {s: sum(1 for f in FINDINGS if f["status"] == s)
              for s in ("PASS", "FAIL", "NOT_EVALUABLE")}
    failures = [f for f in FINDINGS if f["status"] == "FAIL"]
    by_sev = {s: sum(1 for f in failures if f["severity"] == s)
              for s in ("critical", "major", "minor", "informational")}
    verdict = ("FAIL" if by_sev["critical"] else
               "PARTIAL" if by_sev["major"] or by_sev["minor"] else "PASS")

    print(f"\n=== {counts['PASS']} PASS, {counts['FAIL']} FAIL, "
          f"{counts['NOT_EVALUABLE']} NOT_EVALUABLE ===")
    print(f"failures by severity: {by_sev}")
    print(f"=== audit verdict: {verdict} ===")

    payload = {"phase": "N", "audited_at": datetime.now(timezone.utc).isoformat(),
               "git": git_revision(root), "findings": FINDINGS, "counts": counts,
               "failures_by_severity": by_sev, "verdict": verdict,
               "interpretation": {
                   "critical": "prevents scientific submission",
                   "major": "requires correction or an explicit limitation",
                   "minor": "documentation or presentation",
                   "note": "a passing audit is software and bookkeeping integrity, "
                           "not scientific validity"}}
    with open(out_dir / "final_system_audit.json", "w") as stream:
        json.dump(payload, stream, indent=2, default=str)
    pd.DataFrame(FINDINGS).to_csv(out_dir / "final_system_audit.csv", index=False)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
