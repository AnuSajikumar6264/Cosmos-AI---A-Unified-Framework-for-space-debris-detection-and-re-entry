"""The versioned coherent lifetime reading must be derived from the untouched published snapshot,
be coherent on every object, flag exactly the 123 incoherent isotonic records, and carry the
published isotonic values unchanged beside it (Phase 2.3 / X9, 2026-11-06)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-10-27"
PUBLISHED = ROOT / f"outputs/twin/as_of_{AS_OF}/forecast_table.csv.gz"
DERIVED = ROOT / f"outputs/lifetime_coherent_reading/as_of_{AS_OF}_v1"
MANIFEST = ROOT / "paper/figures/RELEASE_MANIFEST.json"
H = ("30d", "90d", "1yr")

pytestmark = pytest.mark.skipif(not (DERIVED.is_dir() and PUBLISHED.is_file()),
                                reason="coherent reading not generated")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_derived_from_the_published_snapshot_which_is_unchanged():
    v = json.loads((DERIVED / "validation.json").read_text())
    now = _sha256(PUBLISHED)
    assert v["source_sha256"] == now, "derived reading does not match the current published table"
    assert v["source_modified"] is False
    if MANIFEST.is_file():
        twin = json.loads(MANIFEST.read_text())["twin_snapshot"]["files"]
        rec = next(e for e in twin if e["path"].endswith("forecast_table.csv.gz"))
        assert rec["sha256"] == now, "published forecast table changed since the figure release froze it"


def test_counts_and_coherence():
    v = json.loads((DERIVED / "validation.json").read_text())
    m = v["monotonicity_by_column_set"]
    assert m["isotonic_p_lifetime"]["violations"] == 123
    assert m["coherent_p_lifetime_raw"]["violations"] == 0
    assert m["final_p"]["violations"] == 0
    assert v["n_objects_with_lifetime_reading"] == 13238
    assert v["incoherent_isotonic_records"] == 123
    assert v["incoherent_split"] == {"30d_gt_90d": 47, "90d_gt_1yr": 76}
    assert v["evidence_for_preferring_it"]["status"].startswith("EXPLORATORY")


def test_table_is_coherent_and_carries_published_values_unchanged():
    d = pd.read_csv(DERIVED / "lifetime_coherent_reading.csv")
    assert len(d) == 13238
    assert int(d["isotonic_incoherent"].sum()) == 123
    coh = [f"p_coherent_{h}" for h in H]
    assert ((d[coh[0]] <= d[coh[1]] + 1e-12) & (d[coh[1]] <= d[coh[2]] + 1e-12)).all()
    assert (d[coh].ge(0).all() & d[coh].le(1).all()).all()

    pub = pd.read_csv(PUBLISHED, low_memory=False)[["norad"] + [f"p_lifetime_{h}" for h in H]]
    merged = d.merge(pub, on="norad", how="left", validate="one_to_one")
    for h in H:
        assert (merged[f"p_isotonic_published_{h}"] == merged[f"p_lifetime_{h}"]).all(), h
    # the two readings differ materially on the flagged objects -- that disagreement must be stated
    v = json.loads((DERIVED / "validation.json").read_text())
    dis = v["coherent_vs_isotonic_disagreement"]
    assert dis["30d"]["mean_abs_diff_flagged"] > 0.2 and dis["90d"]["mean_abs_diff_flagged"] > 0.2
