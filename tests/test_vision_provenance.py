"""SpotGEO scorer provenance and the X14 difficulty decomposition (Phase 2.6, 2026-11-06).

Pins (1) that the vendored scorer is the organisers' file, (2) that every archived SpotGEO test
score is reproduced exactly from the per-sequence submission left on disk, and (3) the structure
of the X14 finding: recall rises with measured target contrast for every arm, the classical front
end is the most contrast-dependent, and the registration front end does not help — the arm
trained on high-passed frames alone matches the two-channel arm and is the only one whose recall
is flat across pointing-drift tertiles. A later change that makes the front end *appear* to help
should fail here and be examined, not absorbed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/feature2_debris/spotgeo"
OUT = ROOT / "outputs/spotgeo_difficulty"
SCORER = ROOT / "cosmos/ai/vision/spotgeo_validation.py"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.skipif(not (DATA / "starter_kit/raw/validation.py").is_file(), reason="starter kit not downloaded")
def test_vendored_scorer_is_byte_identical_to_the_starter_kit_file():
    manifest = json.loads((DATA / "MANIFEST.json").read_text())
    entry = next(f for f in manifest["files"] if f["path"] == "starter_kit/raw/validation.py")
    assert entry["md5_verified"] is True
    assert sha256(SCORER) == sha256(DATA / "starter_kit/raw/validation.py") == entry["sha256"]


needs_results = pytest.mark.skipif(not (OUT / "results.json").is_file(), reason="X14 not generated")


@pytest.fixture(scope="module")
def results() -> dict:
    return json.loads((OUT / "results.json").read_text())


@needs_results
def test_every_archived_test_score_is_reproduced_from_its_submission(results):
    r = results["reproduces_archived_totals"]
    assert len(r) == 10 and "classical_cosmos_frontend" in r
    for arm, v in r.items():
        assert v["all_match"] is True, (arm, v["matches"])
    learned = [k for k, v in r.items() if v["run_id"]]
    assert len(learned) == 9 and all(v["recomputed"]["tp"] == v["archived"]["tp"] for k, v in r.items() if k in learned)
    assert results["cost"]["retraining"] is False and results["cost"]["gpu"] is False
    assert results["provenance"]["scorer_byte_identical_to_starter_kit"] is True


@needs_results
def test_recall_rises_with_measured_target_contrast_for_every_arm(results):
    rec = results["recall_by_target_contrast_quartile"]
    order = ["Q1 faintest", "Q2", "Q3", "Q4 brightest"]
    for arm, by_q in rec.items():
        vals = [by_q[q] for q in order]
        assert vals == sorted(vals), (arm, vals)
        assert vals[-1] - vals[0] > 0.3, (arm, vals)
    rho = {k: v["spearman_recall_vs_contrast"] for k, v in results["spearman_recall_vs_contrast"].items()}
    assert max(rho, key=rho.get) == "classical_cosmos_frontend" and rho["classical_cosmos_frontend"] > 0.65
    assert all(0.4 < v < 0.65 for k, v in rho.items() if k != "classical_cosmos_frontend"), rho


@needs_results
def test_registration_front_end_does_not_help_on_spotgeo(results):
    f1 = {k: v["recomputed"]["f1"] for k, v in results["reproduces_archived_totals"].items()}
    both = [f1[k] for k in f1 if k.startswith("unet_both_f100")]
    assert len(both) == 3
    # high-passed frames alone are at least as good as frames + registered differences ...
    assert f1["unet_raw_f100_s0"] >= min(both) - 1e-9 and f1["unet_raw_f100_s0"] > sum(both) / 3 - 0.01
    # ... and registered differences alone are clearly worse
    assert f1["unet_diff_f100_s0"] < min(both) - 0.05
    drift = results["recall_by_drift_px_tertile"]
    span = {arm: max(v.values()) - min(v.values()) for arm, v in drift.items()}
    assert span["unet_raw_f100_s0"] < 0.02, span
    assert all(s > 0.04 for arm, s in span.items() if arm != "unet_raw_f100_s0"), span


@needs_results
def test_outputs_are_internally_consistent():
    strat = pd.read_csv(OUT / "stratified_results.csv")
    per = pd.read_csv(OUT / "per_sequence_scores.csv")
    assert per.groupby("arm").size().eq(5120).all()
    q = strat[strat.stratum == "target_contrast_quartile"]
    for arm, g in q.groupby("arm"):
        tot = per[per.arm == arm]
        # the quartiles partition the sequences that have objects; counts must add up exactly
        assert g.n_objects.sum() == int((tot.tp + tot.fn).sum()), arm
        assert ((g.f1_ci95_lo <= g.f1 + 1e-12) & (g.f1 <= g.f1_ci95_hi + 1e-12)).all(), arm
