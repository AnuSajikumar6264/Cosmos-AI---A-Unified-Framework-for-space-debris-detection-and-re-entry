"""X14 — difficulty-stratified re-scoring of the archived SpotGEO submissions (Phase 2.6).

    python scripts/spotgeo_difficulty_stratification.py [--workers 32] [--boot 1000]

Every archived arm — the classical COSMOS front end and the nine learned runs — left a full
per-frame test submission on disk. This script re-scores each of them *per sequence* with the
vendored official scorer (byte-identical to the starter kit; verified here against the manifest
hash), checks that the per-sequence scores sum back to the archived totals, and then stratifies
recall, precision and F1 by difficulty covariates **measured from the released data itself**:

  n_objects          annotated objects in the sequence (all five frames)
  target_contrast    for each annotated object, (peak pixel in a 5x5 window at the annotation
                     minus the median of the surrounding 31x31 window) / robust sigma of the frame;
                     sequence value = median over its objects.  A measured SNR *proxy* — the
                     release carries no SNR or magnitude labels, so nothing here is an SNR.
  bg_median          median pixel level over the five frames (sky background / cloud glow)
  bright_frac        fraction of pixels >= 200 (star streaks, clouds, saturation)
  drift_px           pointing drift: largest registration shift of frames 2-5 onto frame 1, from the
                     project's own phase-correlation estimator — the quantity the registration
                     front end has to compensate.

Nothing is retrained, no threshold is re-tuned and no archived file is modified. Outputs go to a
new directory, ``outputs/spotgeo_difficulty/``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cosmos.ai.vision import spotgeo_validation as official  # noqa: E402

DATA = ROOT / "data/feature2_debris/spotgeo"
RAW = DATA / "raw/extracted/SpotGEOv2"
BENCH = ROOT / "outputs/benchmarks/vision_spotgeo"
OUT = ROOT / "outputs/spotgeo_difficulty"
N_FRAMES, H, W = 5, 480, 640
SEED = 20261106


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hier(flat: list) -> dict:
    """Official flat JSON -> {seq: {frame: (k, 2)}}, with every frame present (empty if absent)."""
    h = official.flat_to_hierarchical(flat)
    return {s: {f: np.asarray(h[s].get(f, np.zeros((0, 2)))).reshape(-1, 2) for f in range(1, N_FRAMES + 1)}
            for s in h}


# ----------------------------------------------------------------------------- covariates
def _robust_sigma(x: np.ndarray) -> float:
    med = np.median(x)
    return float(1.4826 * np.median(np.abs(x - med))) or 1e-6


def sequence_covariates(args) -> dict:
    seq, labels = args
    from PIL import Image
    frames = np.stack([np.asarray(Image.open(RAW / "test" / str(seq) / f"{f}.png"), np.float32)
                       for f in range(1, N_FRAMES + 1)])
    sig = np.array([_robust_sigma(f) for f in frames])
    contrasts, edge = [], 0
    for fi in range(N_FRAMES):
        for x, y in labels[fi + 1]:
            xi, yi = int(round(x)), int(round(y))
            if xi < 10 or yi < 10 or xi >= W - 10 or yi >= H - 10:
                edge += 1
            x0, x1 = max(xi - 2, 0), min(xi + 3, W)
            y0, y1 = max(yi - 2, 0), min(yi + 3, H)
            peak = frames[fi, y0:y1, x0:x1].max()
            X0, X1 = max(xi - 15, 0), min(xi + 16, W)
            Y0, Y1 = max(yi - 15, 0), min(yi + 16, H)
            local = np.median(frames[fi, Y0:Y1, X0:X1])
            contrasts.append((peak - local) / sig[fi])
    n_obj = sum(len(labels[f]) for f in range(1, N_FRAMES + 1))
    row = {"seq": seq, "n_objects": n_obj,
           "n_objects_frame_max": max(len(labels[f]) for f in range(1, N_FRAMES + 1)),
           "edge_fraction": edge / n_obj if n_obj else np.nan,
           "target_contrast_median": float(np.median(contrasts)) if contrasts else np.nan,
           "target_contrast_min": float(np.min(contrasts)) if contrasts else np.nan,
           "bg_median": float(np.median(frames)),
           "noise_sigma": float(np.median(sig)),
           "bright_frac": float((frames >= 200).mean()),
           "p999": float(np.percentile(frames, 99.9))}
    try:
        from cosmos.debris.detect import estimate_shift
        shifts = [estimate_shift(frames[0], frames[j]) for j in range(1, N_FRAMES)]
        row["drift_px"] = float(max(np.hypot(dy, dx) for dy, dx in shifts))
    except Exception as exc:  # recorded, not hidden
        row["drift_px"] = np.nan
        row["drift_error"] = repr(exc)
    return row


# ----------------------------------------------------------------------------- scoring
def per_sequence_scores(pred: dict, labels: dict) -> pd.DataFrame:
    rows = []
    for s in sorted(labels):
        tp, fn, fp, mse = official.score_sequence(pred.get(s, {f: np.zeros((0, 2)) for f in range(1, 6)}),
                                                  labels[s])
        rows.append((s, int(tp), int(fn), int(fp), float(mse)))
    return pd.DataFrame(rows, columns=["seq", "tp", "fn", "fp", "mse"])


def prf(tp, fn, fp):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def boot_f1(df: pd.DataFrame, rng: np.random.Generator, n_boot: int) -> tuple[float, float]:
    tp, fn, fp = (df[c].to_numpy() for c in ("tp", "fn", "fp"))
    n = len(df)
    if n == 0:
        return np.nan, np.nan
    idx = rng.integers(0, n, size=(n_boot, n))
    T, N, P = tp[idx].sum(1), fn[idx].sum(1), fp[idx].sum(1)
    prec = np.divide(T, T + P, out=np.zeros(n_boot), where=(T + P) > 0)
    rec = np.divide(T, T + N, out=np.zeros(n_boot), where=(T + N) > 0)
    f1 = np.divide(2 * prec * rec, prec + rec, out=np.zeros(n_boot), where=(prec + rec) > 0)
    lo, hi = np.percentile(f1, [2.5, 97.5])
    return float(lo), float(hi)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args(argv)
    t0 = time.time()

    # 0. provenance: the scorer is the organisers' file
    manifest = json.loads((DATA / "MANIFEST.json").read_text())
    want = next(f["sha256"] for f in manifest["files"] if f["path"] == "starter_kit/raw/validation.py")
    scorer = ROOT / "cosmos/ai/vision/spotgeo_validation.py"
    assert sha256(scorer) == want == sha256(DATA / "starter_kit/raw/validation.py"), "scorer is not the official file"

    anno_path = RAW / "test_anno.json"
    labels = hier(json.loads(anno_path.read_text()))
    assert len(labels) == 5120

    # 1. the ten arms
    arms = {"classical_cosmos_frontend": {"submission": BENCH / "classical_cosmos_frontend_test_submission.json",
                                          "record": BENCH / "classical_cosmos_frontend.json", "kind": "classical"}}
    for rec in sorted((BENCH / "runs").glob("*.json")):
        r = json.loads(rec.read_text())
        arms[rec.stem.replace("spotgeo_", "")] = {
            "submission": ROOT / "outputs/experiments" / r["run_id"] / "test_submission.json",
            "record": rec, "kind": "learned", "run_id": r["run_id"]}

    scores, repro = [], {}
    for name, arm in arms.items():
        pred = hier(json.loads(arm["submission"].read_text()))
        df = per_sequence_scores(pred, labels)
        df.insert(0, "arm", name)
        scores.append(df)
        tp, fn, fp = int(df.tp.sum()), int(df.fn.sum()), int(df.fp.sum())
        p, r, f = prf(tp, fn, fp)
        rec = json.loads(arm["record"].read_text())
        archived = rec["test"] if arm["kind"] == "classical" else {k[5:]: v for k, v in rec.items() if k.startswith("test_")}
        checks = {"f1": abs(f - archived["f1"]) < 1e-9,
                  "official_mse_sum": abs(df.mse.sum() - archived["official_mse_sum"]) < 1e-6}
        if "tp" in archived:
            checks.update(tp=tp == archived["tp"], fn=fn == archived["fn"], fp=fp == archived["fp"])
        repro[name] = {"recomputed": {"tp": tp, "fn": fn, "fp": fp, "precision": p, "recall": r, "f1": f,
                                      "official_mse_sum": float(df.mse.sum())},
                       "archived": {k: archived.get(k) for k in ("tp", "fn", "fp", "f1", "official_mse_sum")},
                       "matches": checks, "all_match": all(checks.values()),
                       "submission_sha256": sha256(arm["submission"]), "run_id": arm.get("run_id")}
        print(f"  {name:38s} F1 {f:.4f}  archived {archived['f1']:.4f}  match={all(checks.values())}", flush=True)
    scores = pd.concat(scores, ignore_index=True)
    assert all(v["all_match"] for v in repro.values()), "per-sequence scores do not reproduce the archived totals"

    # 2. covariates from the released frames
    with ProcessPoolExecutor(a.workers) as ex:
        cov = pd.DataFrame(list(ex.map(sequence_covariates, [(s, labels[s]) for s in sorted(labels)], chunksize=16)))
    cov = cov.sort_values("seq").reset_index(drop=True)
    t_cov = time.time() - t0

    # 3. strata (defined once, on the sequences, independent of any arm)
    with_obj = cov[cov.n_objects > 0]
    strata: dict[str, pd.Series] = {}
    q = with_obj.target_contrast_median.quantile([0.25, 0.5, 0.75]).to_numpy()
    strata["target_contrast_quartile"] = pd.cut(cov.target_contrast_median, [-np.inf, *q, np.inf],
                                                labels=["Q1 faintest", "Q2", "Q3", "Q4 brightest"])
    strata["n_objects_bin"] = pd.cut(cov.n_objects, [-1, 0, 5, 10, 20, np.inf],
                                     labels=["0", "1-5", "6-10", "11-20", ">20"])
    for col in ("bg_median", "bright_frac", "drift_px", "noise_sigma"):
        if cov[col].notna().sum() > 100:
            t = cov[col].quantile([1 / 3, 2 / 3]).to_numpy()
            strata[f"{col}_tertile"] = pd.cut(cov[col], [-np.inf, *t, np.inf], labels=["low", "mid", "high"])
    for k, v in strata.items():
        cov[k] = v.astype(str)

    rng = np.random.default_rng(SEED)
    rows = []
    merged = scores.merge(cov, on="seq")
    for arm in arms:
        d_arm = merged[merged.arm == arm]
        for k in strata:
            for level, g in d_arm.groupby(k, sort=False):
                if level == "nan":
                    continue
                tp, fn, fp = int(g.tp.sum()), int(g.fn.sum()), int(g.fp.sum())
                p, r, f = prf(tp, fn, fp)
                lo, hi = boot_f1(g, rng, a.boot)
                rows.append({"arm": arm, "stratum": k, "level": level, "n_sequences": len(g), "n_objects": tp + fn,
                             "tp": tp, "fn": fn, "fp": fp, "precision": p, "recall": r, "f1": f,
                             "f1_ci95_lo": lo, "f1_ci95_hi": hi})
    strat = pd.DataFrame(rows)

    # per-arm rank correlation of per-sequence recall with the contrast proxy (sequences with objects)
    from scipy.stats import spearmanr
    corr = {}
    for arm in arms:
        d = merged[(merged.arm == arm) & (merged.n_objects > 0)]
        rec = d.tp / (d.tp + d.fn)
        rho, pval = spearmanr(rec, d.target_contrast_median)
        corr[arm] = {"spearman_recall_vs_contrast": float(rho), "p": float(pval), "n": int(len(d))}

    OUT.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT / "per_sequence_scores.csv", index=False)
    cov.to_csv(OUT / "sequence_covariates.csv", index=False)
    strat.to_csv(OUT / "stratified_results.csv", index=False)

    def pivot(stratum: str, metric: str) -> dict:
        t = strat[strat.stratum == stratum].pivot(index="arm", columns="level", values=metric)
        order = [lv for lv in strata[stratum].cat.categories.astype(str) if lv in t.columns]
        return t[order].round(4).to_dict(orient="index")

    results = {
        "experiment": "X14 difficulty-stratified re-scoring of archived SpotGEO submissions",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cost": {"seconds_total": round(time.time() - t0, 1), "seconds_to_covariates": round(t_cov, 1),
                 "workers": a.workers, "gpu": False, "retraining": False},
        "provenance": {"scorer_sha256": want, "scorer_byte_identical_to_starter_kit": True,
                       "test_anno_sha256": sha256(anno_path), "n_test_sequences": len(labels),
                       "n_test_objects": int(sum(len(labels[s][f]) for s in labels for f in range(1, 6))),
                       "arms": {k: {"submission": str(v["submission"].relative_to(ROOT)), "run_id": v.get("run_id")}
                                for k, v in arms.items()}},
        "reproduces_archived_totals": repro,
        "covariate_definitions": {
            "target_contrast": "(peak pixel in 5x5 at annotation - median of 31x31 neighbourhood) / 1.4826*MAD of frame; "
                               "sequence = median over objects. A measured proxy; the release has no SNR labels.",
            "bg_median": "median pixel value over the five 8-bit frames",
            "bright_frac": "fraction of pixels >= 200 over the five frames",
            "drift_px": "max over frames 2-5 of |phase-correlation shift onto frame 1| (cosmos.debris.detect.estimate_shift)",
            "noise_sigma": "median over frames of 1.4826*MAD",
            "n_objects": "annotated objects over the five frames"},
        "covariate_summary": cov.drop(columns=[c for c in cov.columns if c.endswith(("_quartile", "_bin", "_tertile"))])
                                .describe().round(4).to_dict(),
        "n_sequences_without_objects": int((cov.n_objects == 0).sum()),
        "strata_cutpoints": {"target_contrast_quartile": [float(x) for x in q]},
        "recall_by_target_contrast_quartile": pivot("target_contrast_quartile", "recall"),
        "f1_by_target_contrast_quartile": pivot("target_contrast_quartile", "f1"),
        "recall_by_n_objects": pivot("n_objects_bin", "recall"),
        "fp_by_n_objects": pivot("n_objects_bin", "fp"),
        "spearman_recall_vs_contrast": corr,
        "caveats": [
            "Strata are defined on the test set and the arms are compared on it post hoc; this is a descriptive "
            "decomposition of an already-reported test score, not a new blind evaluation.",
            "The classical arm's operating point (nsigma = 10) and every learned threshold were selected on "
            "validation sequences before the test set was scored; they are not re-tuned here.",
            "target_contrast is measured at the annotated position in the raw frame and is a proxy; objects "
            "fainter than the local noise return values near zero or negative.",
            "Sequences without annotated objects have undefined recall and are reported through false positives only."],
    }
    for k in ("drift_px_tertile", "bg_median_tertile", "bright_frac_tertile", "noise_sigma_tertile"):
        if k in strata:
            results[f"recall_by_{k}"] = pivot(k, "recall")
            results[f"f1_by_{k}"] = pivot(k, "f1")
    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=float) + "\n")

    print(f"\nsequences {len(cov)}  without objects {results['n_sequences_without_objects']}  "
          f"contrast quartile cuts {np.round(q, 2)}  drift computed for {cov.drift_px.notna().sum()}")
    print("\nrecall by target-contrast quartile:")
    print(pd.DataFrame(results["recall_by_target_contrast_quartile"]).T.to_string(float_format=lambda v: f"{v:.3f}"))
    if "recall_by_drift_px_tertile" in results:
        print("\nrecall by pointing-drift tertile:")
        print(pd.DataFrame(results["recall_by_drift_px_tertile"]).T.to_string(float_format=lambda v: f"{v:.3f}"))
    print("\nSpearman(recall, contrast):", {k: round(v["spearman_recall_vs_contrast"], 3) for k, v in corr.items()})
    print(f"\nwritten {OUT.relative_to(ROOT)}/  in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
