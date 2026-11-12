"""X4 — 3b Stage 2: the exactly-specified cells of the (score level x pool x selection data) space.

    POSTHOC_TMP=/data2/anupa/tmp_posthoc python scripts/track3b_stage2_cells.py

Lineage: POSTHOC_PLAN_V2.md P1 (cell definitions, selection procedures, score levels S0/Sh/S1, paired
block bootstrap seed 20261024) and TRACK3B_FACTORIAL_EXPERIMENT_PROPOSAL.md (Stage 2 = F1 fit data x
F2 residual scale x F3 calibration pool at both F4 levels, grid at the A1 level). EXPLORATORY; the
confirmatory verdicts are not touched.

What had to be regenerated and how. The AR(8) residual-score caches were lost to the `*.npy` ignore
rule. They are recomputed with the FROZEN code only: `oof.ar8_oof` via `oof.run` (A1 scores, K = 5,
purge 1 day, seed 0) and `forecasting.forecast_record` / `residual_scale` / `nonconformity` (A0
scores: fit-period AR(8), `es`-period sigma). `oof.oof_dir` is redirected at runtime to a NEW directory
so the historical `oof/*/folds.json` is never rewritten; the regenerated OOF scores are checked against
the archived `sha256_sample` of the lost array. P1's cell runner is reused unchanged (imported), with its
alarm-array output redirected to this directory.

Cells run: the P1 endpoints c0 (= A0) and c5 (= A1) as the validity gate (must equal the frozen official
values to 1e-9), the P1 cells c2, c3, c4 (recomputed so that paired bootstrap tables exist), and the two
cells of the P1 factor space that P1 did not run and that are fully defined: (Sh, P_half, D_cal, G1) and
(Sh, P_half, D_half, G1). Blockers (recorded in the output, not improvised): (i) F1 = fit data at the
P_half level is undefined — A0's fit-period model has no out-of-fold scores over the training half, so
(S0, P_half, .) has no pool; (ii) (P_cal, D_half) is defined neither in the plan nor in the proposal.
Hence the 2^3 main effects of protocol §6 cannot be estimated; the cells below give the F2 (sigma)
contrast at the P_half level and the F3 (pool) and F4 (selection data) contrasts at the Sh level.
"""
from __future__ import annotations

import hashlib, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/posthoc_v2"))
NEW = ROOT / "outputs/benchmarks/telemetry_esa_adb/track3b_stage2"
NEW.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("POSTHOC_TMP", "/data2/anupa/tmp_posthoc")

from scripts.phase8_acceptance_gate import verify_hashes  # noqa: E402
import common  # noqa: E402  (posthoc_v2)
from cosmos.ai.telemetry import oof, oof_benchmark as OB  # noqa: E402
from cosmos.ai.telemetry.forecasting import DELTA, ForecastConfig, MissionData, forecast_record, nonconformity, residual_scale  # noqa: E402
from cosmos.ai.data.preprocess_telemetry import official_test_labels  # noqa: E402

M, CH, LAYER = 1, "target", "conformal_bh"
ARCHIVED_OOF_SAMPLE = json.loads((ROOT / "outputs/benchmarks/telemetry_esa_adb/oof/m1_target_ar8/folds.json").read_text())["sha256_sample"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def freeze_state() -> dict:
    out = {}
    for name in ("freeze.json", "freeze_09a98f5e160e.json"):
        fz = json.loads((ROOT / "research_design/preregistration" / name).read_text())
        n, bad = verify_hashes(list(fz["sha256"].items()))
        out[name] = {"n": n, "bad": bad}
    out["posthoc_plan"] = common.check_plan()["sha256"]
    out["p1_archive"] = {p.name: sha(p) for p in sorted((ROOT / "outputs/benchmarks/telemetry_esa_adb/posthoc_v2/p1_decompose").glob("*.json"))}
    return out


def main() -> int:
    t_start = time.time()
    before = freeze_state()
    assert not before["freeze.json"]["bad"] and before["freeze_09a98f5e160e.json"]["bad"] == ["research_design/preregistration/PREREG_TELEMETRY_V1.md"], before
    log = {"started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "freeze_before": before, "steps": []}

    # --- redirect the frozen OOF module's output location (computation untouched) ------------
    regen_root = NEW / "oof_regen"

    def oof_dir_new(mission, channels, encoder):
        d = regen_root / f"m{mission}_{channels}_{encoder}"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)
    oof.oof_dir = oof_dir_new
    d_oof = Path(oof_dir_new(M, CH, "ar8"))
    if not (d_oof / "scores_train_oof.npy").is_file():
        t0 = time.time()
        oof.run(M, CH)                                   # frozen oof.ar8_oof, K=5, purge 1 d, seed 0
        log["steps"].append({"step": "oof.run(1, target)", "seconds": round(time.time() - t0, 1)})
    meta = json.loads((d_oof / "folds.json").read_text())
    log["oof_regeneration"] = {"dir": str(d_oof.relative_to(ROOT)), "sha256_sample": meta["sha256_sample"], "archived_sha256_sample": ARCHIVED_OOF_SAMPLE,
                               "reproduces_archived_sample": meta["sha256_sample"] == ARCHIVED_OOF_SAMPLE, "seconds": meta["seconds"], "folds": meta["folds"]}
    print("OOF regenerated:", log["oof_regeneration"], flush=True)

    import p1_decompose as P1  # noqa: E402  (after the redirect; P1 reads oof.load / oof.oof_dir)
    def out_path_new(*parts):
        p = NEW / "alarms" / Path(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    P1.out_path = out_path_new

    # --- data and score levels ---------------------------------------------------------------
    t0 = time.time()
    D = MissionData(M, CH); D.channels_set = CH
    merge = int(OB.MERGE_H * 3600 / D.train.rule_s)
    ts_te = D.test.timestamps()
    lab_te = official_test_labels(M, D.test); lab_te = lab_te[lab_te.Channel.isin(D.channels)]
    cfg = ForecastConfig(mission=M, encoder="ar8", channels=CH)
    sig0 = residual_scale(D, cfg, None)                                   # A0's es-period sigma (frozen code)
    Y, q25, q50, q75, _ = forecast_record(None, D, "cal", cfg); S0_cal = nonconformity(Y, q25, q50, q75, sig0)
    Y, q25, q50, q75, _ = forecast_record(None, D, "test", cfg); S0_te = nonconformity(Y, q25, q50, q75, sig0)
    S1_tr, S1_te, meta = oof.load(M, CH, "ar8")
    sig = np.load(d_oof / "sigma.npy"); sig_fold, sig_full = sig[:-1], sig[-1]
    S1_tr = np.asarray(S1_tr, np.float32); S1_te = np.asarray(S1_te, np.float32)
    Sh_tr = np.empty_like(S1_tr)
    for b, (a, e) in enumerate(meta["folds"]):
        Sh_tr[a:e] = S1_tr[a:e] * (np.maximum(sig_fold[b], DELTA) / np.maximum(sig0, DELTA))[None, :]
    Sh_te = (S1_te * (np.maximum(sig_full, DELTA) / np.maximum(sig0, DELTA))[None, :]).astype(np.float32)
    scores = {"S0": (S0_cal, S0_te), "Sh": (Sh_tr, Sh_te), "S1": (S1_tr, S1_te)}
    log["steps"].append({"step": "score levels S0 (recomputed in memory, frozen forecasting code), Sh, S1", "seconds": round(time.time() - t0, 1)})
    print(f"score levels ready in {time.time() - t0:.0f} s", flush=True)

    # --- cells ---------------------------------------------------------------------------------
    CELLS = [("c0", "S0", "cal", "cal", P1.G0), ("c2", "Sh", "cal", "cal", P1.G1), ("c3", "S1", "cal", "cal", P1.G1),
             ("c4", "S1", "half", "cal", P1.G1), ("c5", "S1", "half", "half", P1.G1),
             ("n_sh_half_cal", "Sh", "half", "cal", P1.G1), ("n_sh_half_half", "Sh", "half", "half", P1.G1)]
    rows, tabs = {}, {}
    for name, S_key, P, Dsel, grid in CELLS:
        rows[name], tabs[name] = P1.run_cell(name, D, M, LAYER, scores, S_key, P, Dsel, grid, merge, ts_te, lab_te)
        (NEW / "cells_partial.json").write_text(json.dumps(rows, indent=1, default=float) + "\n")

    # --- validity gate against the frozen official values and the archived P1 cells ------------
    arms = json.loads((ROOT / "outputs/benchmarks/telemetry_esa_adb/arms" / f"m{M}_{CH}_ar8_s0.json").read_text())["rows"]
    a0_off = [r for r in arms if r["calibrator"] == LAYER][0]["anomaly_and_rare/EW_F0.5"]
    a1_off = [r for r in json.loads((ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/test" / f"m{M}_{CH}_ar8.json").read_text()) if r["calibrator"] == LAYER][0]["anomaly_and_rare/EW_F0.5"]
    p1 = json.loads((ROOT / "outputs/benchmarks/telemetry_esa_adb/posthoc_v2/p1_decompose" / f"m{M}_{CH}_{LAYER}.json").read_text())["cells"]
    repro = {"A0_official": a0_off, "c0": rows["c0"]["official_EW_F0.5"], "A1_official": a1_off, "c5": rows["c5"]["official_EW_F0.5"],
             "p1_cells_reproduced": {k: abs(rows[k]["official_EW_F0.5"] - p1[k]["official_EW_F0.5"]) < 1e-9 and rows[k]["chosen_level"] == p1[k]["chosen_level"] and rows[k]["chosen_k"] == p1[k]["chosen_k"]
                                     for k in ("c0", "c2", "c3", "c4", "c5")}}
    repro["passed"] = bool(abs(a0_off - repro["c0"]) < 1e-9 and abs(a1_off - repro["c5"]) < 1e-9 and all(repro["p1_cells_reproduced"].values()))
    print("reproduction:", repro, flush=True)

    # --- contrasts: paired block bootstrap (P3 machinery), seed as P1 ---------------------------
    import exact_metric as XM
    rng = np.random.default_rng(20261024)
    CONTRASTS = [("F2 sigma at P_half, D_cal (S1 - Sh)", "n_sh_half_cal", "c4"), ("F2 sigma at P_half, D_half (S1 - Sh)", "n_sh_half_half", "c5"),
                 ("F2 sigma at P_cal, D_cal (S1 - Sh)", "c2", "c3"), ("F3 pool at Sh, D_cal (half - cal)", "c2", "n_sh_half_cal"),
                 ("F3 pool at S1, D_cal (half - cal)", "c3", "c4"), ("F4 selection data at Sh, P_half (half - cal)", "n_sh_half_cal", "n_sh_half_half"),
                 ("F4 selection data at S1, P_half (half - cal)", "c4", "c5")]
    steps = []
    for label, x, y in CONTRASTS:
        r = XM.compare([tabs[y]], [tabs[x]], rng); r.pop("replicates", None)
        steps.append({"contrast": label, "from": x, "to": y, "delta_official": rows[y]["official_EW_F0.5"] - rows[x]["official_EW_F0.5"],
                      "delta_exact": r["diff"], "ci95_low": r["ci95_low"], "ci95_high": r["ci95_high"], "p_boot": r["p_boot"],
                      "material_at_0.05": bool(rows[y]["official_EW_F0.5"] - rows[x]["official_EW_F0.5"] >= 0.05 and r["ci95_low"] > 0)})
    # F2 x F3 interaction at D_cal: sigma effect with pool half minus sigma effect with pool cal
    inter = (rows["c4"]["official_EW_F0.5"] - rows["n_sh_half_cal"]["official_EW_F0.5"]) - (rows["c3"]["official_EW_F0.5"] - rows["c2"]["official_EW_F0.5"])
    after = freeze_state()
    out = {"experiment": "X4 / 3b Stage 2 — exactly specified cells only (EXPLORATORY)", "mission": M, "channels": CH, "layer": LAYER,
           "started_at": log["started_at"], "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seconds_total": round(time.time() - t_start, 1),
           "provenance": {"p1_script_sha256": sha(ROOT / "scripts/posthoc_v2/p1_decompose.py"), "this_script_sha256": sha(Path(__file__)),
                          "posthoc_plan_sha256": before["posthoc_plan"], "proposal_sha256": sha(ROOT / "docs/publication/TRACK3B_FACTORIAL_EXPERIMENT_PROPOSAL.md")},
           "oof_regeneration": log["oof_regeneration"], "steps": log["steps"], "reproduction": repro, "cells": rows, "contrasts": steps,
           "interaction_F2xF3_at_Dcal_point": inter,
           "blockers": ["F1 (fit data) at the P_half level is undefined: A0's fit-period model has no out-of-fold scores over the training half, so (S0, P_half, .) has no pool — "
                        "the full 2^3 of protocol §3.3 cannot be run without a protocol decision on how A0's model would supply a half pool",
                        "(P_cal, D_half) is defined neither in POSTHOC_PLAN_V2 P1 nor in the 3b proposal (cross-fitting over the training half with a calibration-window pool)",
                        "consequently the Stage-2 main effects and Holm correction of proposal §6 are not estimated; the contrasts above are conditional one-factor contrasts inside the defined cell space"],
           "freeze_after": after, "freeze_unchanged": before == after,
           "test_half_exposure": "7 further scorings of the pre-registered M1 test half; exploratory; no operating point was selected on test data"}
    (NEW / f"m{M}_{CH}_{LAYER}.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    for s in steps:
        print(f"  {s['contrast']:48s} {s['from']:>14s}->{s['to']:<14s} {s['delta_official']:+.4f} [{s['ci95_low']:+.4f}, {s['ci95_high']:+.4f}] p={s['p_boot']:.3f}")
    print(f"F2xF3 interaction at D_cal (point): {inter:+.4f}")
    print(f"freeze unchanged: {out['freeze_unchanged']}; total {out['seconds_total']} s; written {NEW.relative_to(ROOT)}/m{M}_{CH}_{LAYER}.json")
    return 0 if repro["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
