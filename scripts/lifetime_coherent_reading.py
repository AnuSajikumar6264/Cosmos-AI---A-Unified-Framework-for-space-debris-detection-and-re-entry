"""Emit the coherent multi-horizon lifetime reading as a separately versioned derived table.

    python scripts/lifetime_coherent_reading.py --as-of 2026-10-27

Limitation L17: the published per-horizon probabilities ``p_lifetime_{30d,90d,1yr}`` in
``outputs/twin/as_of_<date>/forecast_table.csv.gz`` are calibrated by three independent isotonic
regressors and are not a coherent CDF -- 123 of 13,238 objects violate monotonicity (max drop 0.18).
The recorded decision (``docs/research/L17_METHODOLOGY_DECISION.md``, 2026-11-04) is to preserve
that published calibration and never repair it in place. **This script does not modify it.**

What it does instead. The same table already carries a second reading of the same lifetime model,
``p_lifetime_raw_*``, obtained by reading horizon probabilities off the model's monotone quantile
function. That reading is coherent across horizons by construction. Phase G+ compared the two on
the T1 window (``outputs/phase_g_multihorizon/``): 0 vs 54 violations and a better Brier score at
both horizons (p < 0.0001) -- exploratory evidence, because T1 is not a blind window and its event
counts are small, and on a *different* population (as-of 2026-08-16) than the snapshot read here.

This script therefore:
  1. reads the published snapshot read-only and records its SHA-256;
  2. validates monotonicity of every probability column set on every object;
  3. writes the coherent reading, the published isotonic reading and an incoherence flag side by
     side to a new versioned directory, so a consumer can choose the coherent reading without the
     published artifact changing;
  4. writes ``validation.json`` with counts, provenance and the exact scope of the evidence.

The twin's *reported* forecast (``p_30d``, ``p_90d``, ``p_1yr``) is a gated mixture and is coherent
already; L17 concerns only the lifetime-variant columns, and that is stated in the output.
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

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = ("30d", "90d", "1yr")
VERSION = "v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def violations(frame: pd.DataFrame, cols: list[str]) -> tuple[int, int, float]:
    sub = frame.dropna(subset=cols)
    v = (sub[cols[0]] > sub[cols[1]] + 1e-12) | (sub[cols[1]] > sub[cols[2]] + 1e-12)
    drop = np.maximum(sub[cols[0]] - sub[cols[1]], sub[cols[1]] - sub[cols[2]])
    return int(v.sum()), int(len(sub)), float(drop.max()) if len(sub) else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--as-of", default="2026-10-27")
    args = ap.parse_args(argv)

    src = ROOT / f"outputs/twin/as_of_{args.as_of}/forecast_table.csv.gz"
    if not src.is_file():
        print(f"missing {src}", file=sys.stderr)
        return 1
    digest = sha256(src)
    table = pd.read_csv(src, low_memory=False)

    iso = [f"p_lifetime_{h}" for h in HORIZONS]
    raw = [f"p_lifetime_raw_{h}" for h in HORIZONS]
    final = [f"p_{h}" for h in HORIZONS]
    sets = {"isotonic_p_lifetime": iso, "coherent_p_lifetime_raw": raw, "final_p": final,
            "physics_prior": [f"p_physics_prior_{h}" for h in HORIZONS],
            "physics_history": [f"p_physics_history_{h}" for h in HORIZONS]}
    report = {name: dict(zip(("violations", "n_objects", "max_drop"), violations(table, cols)))
              for name, cols in sets.items()}

    scored = table.dropna(subset=iso + raw).copy()
    bad = ((scored[iso[0]] > scored[iso[1]] + 1e-12) | (scored[iso[1]] > scored[iso[2]] + 1e-12))
    out = pd.DataFrame({
        "norad": scored["norad"].astype(int),
        "Name": scored["Name"],
        "type1": scored["type1"],
        "regime": scored["regime"],
        "am_source": scored["am_source"],
        **{f"p_coherent_{h}": scored[f"p_lifetime_raw_{h}"] for h in HORIZONS},
        **{f"p_isotonic_published_{h}": scored[f"p_lifetime_{h}"] for h in HORIZONS},
        "isotonic_incoherent": bad.to_numpy(),
        "isotonic_max_drop": np.maximum(scored[iso[0]] - scored[iso[1]],
                                        scored[iso[1]] - scored[iso[2]]).clip(lower=0),
    })
    # the coherent reading must be coherent on every object, or this script has no business
    coh_v = int(((out["p_coherent_30d"] > out["p_coherent_90d"] + 1e-12)
                 | (out["p_coherent_90d"] > out["p_coherent_1yr"] + 1e-12)).sum())
    assert coh_v == 0, f"coherent reading has {coh_v} violations; refusing to publish it as coherent"

    dest = ROOT / f"outputs/lifetime_coherent_reading/as_of_{args.as_of}_{VERSION}"
    dest.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest / "lifetime_coherent_reading.csv", index=False)

    base = scored["am_source"].value_counts(normalize=True).round(4).to_dict()
    inc = scored.loc[bad, "am_source"].value_counts(normalize=True).round(4).to_dict()
    # How far apart the two readings are on the flagged objects. A consumer choosing the coherent
    # reading must know it moves these probabilities materially, not cosmetically.
    disagreement = {
        h: {"mean_abs_diff_flagged": float((scored.loc[bad, f"p_lifetime_raw_{h}"]
                                            - scored.loc[bad, f"p_lifetime_{h}"]).abs().mean()),
            "mean_abs_diff_all_scored": float((scored[f"p_lifetime_raw_{h}"]
                                               - scored[f"p_lifetime_{h}"]).abs().mean())}
        for h in HORIZONS}
    validation = {
        "as_of": args.as_of,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(src.relative_to(ROOT)),
        "source_sha256": digest,
        "source_modified": False,
        "n_objects_in_snapshot": int(len(table)),
        "n_objects_with_lifetime_reading": int(len(out)),
        "monotonicity_by_column_set": report,
        "incoherent_isotonic_records": int(bad.sum()),
        "incoherent_split": {
            "30d_gt_90d": int((scored[iso[0]] > scored[iso[1]] + 1e-12).sum()),
            "90d_gt_1yr": int((scored[iso[1]] > scored[iso[2]] + 1e-12).sum()),
        },
        "incoherent_by_class": scored.loc[bad, "type1"].value_counts().to_dict(),
        "incoherent_by_am_source": scored.loc[bad, "am_source"].value_counts().to_dict(),
        "am_source_share_scored": base,
        "am_source_share_incoherent": inc,
        "coherent_vs_isotonic_disagreement": disagreement,
        "what_the_coherent_reading_is": (
            "p_lifetime_raw_* from the same lifetime model, read off its monotone quantile "
            "function; coherent across horizons by construction; NOT a recalibration"),
        "evidence_for_preferring_it": {
            "artifact": "outputs/phase_g_multihorizon/multihorizon_results.json",
            "population": "T1 window, as-of 2026-08-16, 13,186 objects, 1,814 launches",
            "result": "isotonic 54 violations vs coherent 0; Brier better at both horizons, "
                      "p < 0.0001 (cluster bootstrap by launch, 4000 draws)",
            "status": "EXPLORATORY: T1 is not a blind window (29 and 64 events); the "
                      "population differs from this snapshot, which has no outcomes yet",
        },
        "count_calibration_caveat": {
            "finding": ("coherence is not calibration. Summed over the 13,238 uncontrolled objects "
                        "the coherent reading expects MORE 30-day re-entries than the isotonic one "
                        "(404.0 vs 229.1 on this snapshot; physics_history 21.6), and on the T1 "
                        "window it over-predicts observed events by 14.8x [10.2, 23.6] against "
                        "10.5x for the isotonic reading and 1.5x for physics_history — while "
                        "having the better Brier score (0.0026 vs 0.0087)"),
            "source": "outputs/reentry_variant_decomposition/results.json (X7, 2026-11-06)",
            "consequence": ("prefer the coherent reading for per-object ordering and horizon "
                            "consistency; do not read either lifetime variant as a calibrated "
                            "expected count. The twin's reported forecast uses physics_history "
                            "for uncontrolled objects, which is the variant closest to observation"),
        },
        "scope_note": ("L17 concerns the lifetime-variant columns only. The twin's reported "
                       "forecast p_30d/p_90d/p_1yr is a gated mixture and has 0 violations; the "
                       "top-50 ranking uses p_30d and is unaffected."),
        "published_artifact_policy": ("preserved unchanged per L17_METHODOLOGY_DECISION.md; this "
                                      "directory is a derived, versioned reading beside it"),
    }
    (dest / "validation.json").write_text(json.dumps(validation, indent=1, default=str) + "\n")

    print(f"source {src.relative_to(ROOT)}  sha256 {digest[:16]}…  (not modified)")
    for name, r in report.items():
        print(f"  {name:26s} violations={r['violations']:4d} / {r['n_objects']}  max_drop={r['max_drop']:.4f}")
    print(f"incoherent isotonic records: {int(bad.sum())}  → coherent reading violations: {coh_v}")
    print(f"written {dest.relative_to(ROOT)}/lifetime_coherent_reading.csv ({len(out):,} rows), validation.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
