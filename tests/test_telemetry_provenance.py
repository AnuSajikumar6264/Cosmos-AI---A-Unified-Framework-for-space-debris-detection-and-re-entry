"""Provenance tests for the telemetry studies (completion directive, Phase 2.1).

Each test turns a claim that was previously made in prose into something the suite checks:

  * the vendored ESA-ADB metric code really is byte-identical to the upstream commit;
  * the archived 2026-10-24 OPS-SAT study is never overwritten by a regeneration run;
  * the OPS-SAT study entry point honours ``--out`` so a regeneration cannot hit the archive.

The upstream tarball is untrusted downloaded data: it is read member-by-member through
``tarfile.extractfile`` and never extracted to disk or executed.
"""
from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TARBALL = ROOT / "data/feature1_health/esa_adb/raw/kplabs-pl__ESA-ADB-67194d389c4a.tar.gz"
VENDORED = ROOT / "cosmos/ai/telemetry/esa_metrics"
OPSSAT_ARCHIVE = ROOT / "outputs/benchmarks/telemetry_opssat"
OPSSAT_PIN = ROOT / "outputs/audit/opssat_historical_sha256.txt"
UPSTREAM_COMMIT = "67194d3"


@pytest.mark.skipif(not TARBALL.is_file(), reason="upstream ESA-ADB tarball not downloaded")
def test_vendored_metric_code_is_byte_identical_to_upstream():
    """12 computing files identical; the package __init__ is a documented project-written shim."""
    identical, shim = [], []
    with tarfile.open(TARBALL, "r:gz") as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}
        top = next(iter(members)).split("/", 1)[0]
        for path in sorted(VENDORED.rglob("*.py")):
            rel = path.relative_to(VENDORED).as_posix()
            upstream = f"{top}/timeeval/metrics/{rel}"
            assert upstream in members, f"no upstream counterpart for {rel}"
            if rel == "__init__.py":
                shim.append(rel)
                continue
            up_bytes = tf.extractfile(members[upstream]).read()
            assert up_bytes == path.read_bytes(), f"{rel} differs from upstream {UPSTREAM_COMMIT}"
            identical.append(rel)
    assert len(identical) == 12, identical
    assert shim == ["__init__.py"]
    text = (VENDORED / "__init__.py").read_text()
    assert UPSTREAM_COMMIT in text and "unmodified" in text, (
        "the shim must state its provenance and that the computing files are unmodified")


@pytest.mark.skipif(not OPSSAT_PIN.is_file(), reason="OPS-SAT archive pin not taken")
def test_archived_opssat_study_is_untouched():
    """Every file of the 2026-10-24 study still hashes to the pin taken before regeneration."""
    lines = [l for l in OPSSAT_PIN.read_text().splitlines() if l.strip()]
    assert len(lines) == 10, "the archive held exactly ten files when pinned"
    for line in lines:
        digest, name = line.split(maxsplit=1)
        path = OPSSAT_ARCHIVE / name.strip()
        assert path.is_file(), f"{name} missing from the archive"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            f"{name} changed since the 2026-11-06 pin — the archive must not be regenerated in place")


def test_opssat_entry_point_honours_out_override(monkeypatch, tmp_path):
    """`--out` must reach run_study as cfg['out_dir']; without it the default is unchanged."""
    opssat = pytest.importorskip("cosmos.ai.telemetry.opssat")
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text("length: 256\nseeds: [0]\nprotocols: [official]\nmodels: [logreg]\n")
    captured = {}
    monkeypatch.setattr(opssat, "run_study", lambda cfg: captured.update(cfg))

    opssat.main(["--config", str(cfg_path), "--out", str(tmp_path / "elsewhere")])
    assert captured["out_dir"] == str(tmp_path / "elsewhere")
    assert captured["protocols"] == ["official"]

    captured.clear()
    opssat.main(["--config", str(cfg_path)])
    assert "out_dir" not in captured, "no override means the historical default path"


SELECTION = ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/selection"
TEST_RUNS = ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/test"
LAYERS = {"threshold", "conformal_bh", "conformal_bh_rolling", "aci", "aci_event"}


@pytest.mark.skipif(not SELECTION.is_dir(), reason="ESA-ADB protocol outputs absent")
def test_every_test_run_used_the_operating_point_chosen_at_selection():
    """The cross-fitted layers must be scored at exactly the (level, k, merge) the selection step
    chose, with the same selection score; the two ACI layers are never cross-fitted and sit at a
    fixed alpha. Verified 2026-11-06 on all 30 arms: 90 selected rows, 0 mismatches."""
    import json

    files = sorted(SELECTION.glob("*.json"))
    assert len(files) == 30, len(files)
    checked = 0
    for sel_path in files:
        chosen = json.loads(sel_path.read_text())["chosen"]
        rows = {r["calibrator"]: r for r in json.loads((TEST_RUNS / sel_path.name).read_text())}
        assert set(rows) == LAYERS, sel_path.name
        for cal, c in chosen.items():
            r = rows[cal]
            for key in ("level", "k", "merge"):
                assert r[key] == c[key], (sel_path.name, cal, key, r[key], c[key])
            assert abs(r["cv_EW_F0.5"] - c["cv_EW_F0.5"]) < 1e-12, (sel_path.name, cal)
            checked += 1
        for cal in set(rows) - set(chosen):
            assert cal.startswith("aci"), (sel_path.name, cal, "only the ACI layers are fixed")
            # the ACI rows carry no selection score at all (key absent), and sit at alpha = 0.01
            assert rows[cal].get("cv_EW_F0.5") is None and rows[cal]["level"] == 0.01, (sel_path.name, cal)
    assert checked == 90, checked


REGEN = ROOT / "outputs/benchmarks/telemetry_opssat_regen_20261106"
DETERMINISTIC = {"xgboost", "logreg", "iforest", "adaboost", "random_forest", "cosmos_robust_z",
                 # observed on 2026-11-06 to reproduce exactly across torch 2.13->2.14 and xpu:1->xpu:0
                 "fcnn", "transformer"}


@pytest.mark.skipif(not REGEN.is_dir(), reason="OPS-SAT regeneration not present")
def test_opssat_regeneration_reproduces_the_archive_where_it_should():
    """Deterministic arms (and the two deep arms that proved deterministic) must match the archived
    per-run table to numerical precision; the per-seed score archive the 2026-10-24 study lost must
    now exist with the keys report.py expects. Non-deterministic deep arms (cnn, hybrid, chronos
    probe) are deliberately NOT pinned here — their drift is a documented finding, not a target."""
    import numpy as np
    import pandas as pd

    keys = ["protocol", "model", "train_frac", "seed"]
    expected = {"official": (124, 529, 113), "time_blocked": (49, 531, 176)}
    for tag, (n_keys, n_test, n_pos) in expected.items():
        arch = pd.read_csv(OPSSAT_ARCHIVE / f"per_run_{tag}.csv")
        regen = pd.read_csv(REGEN / f"per_run_{tag}.csv")
        merged = arch.merge(regen, on=keys, suffixes=("_a", "_r"), how="outer", indicator=True)
        assert (merged["_merge"] == "both").all(), f"{tag}: cell coverage differs from the archive"
        det = merged[merged.model.isin(DETERMINISTIC)]
        for met in ("f1", "auc_pr", "mcc", "precision", "recall"):
            assert np.allclose(det[f"{met}_a"], det[f"{met}_r"], atol=1e-9), (tag, met)

        z = np.load(REGEN / f"test_scores_{tag}.npz")
        assert len(z.files) == n_keys, (tag, len(z.files))
        y = z[f"{tag}|y"]
        assert len(y) == n_test and int(y.sum()) == n_pos, (tag, len(y), int(y.sum()))
        assert sum(1 for k in z.files if k.startswith(f"{tag}|1.0|")) == 47, tag
