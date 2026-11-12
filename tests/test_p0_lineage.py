"""P0.2 — honest lineage: code, configuration, data artifact and model version kept apart; nothing inferred."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import lineage_for_module, model_version_unavailable, registry_association

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="snapshot absent")


def test_no_registry_card_is_associated_with_any_output():
    assert S.VERIFIED_MODEL_CARD_ASSOCIATIONS == {}
    assert registry_association("COSMOS dated twin (physics prior + history posterior + lifetime fusion)") is None
    assert registry_association(None) is None
    mv = model_version_unavailable("why")
    assert mv["status"] == "unavailable" and mv["digest"] is None and mv["registry_card"] is None and "none is inferred" in mv["registry_note"]


def test_lineage_for_incomplete_manifests_reports_unavailable_not_guesses():
    empty = lineage_for_module({})
    assert empty["code_version"]["git_commit"] == "unavailable"
    assert empty["configuration_version"]["config_sha256"] == "unavailable"
    assert empty["data_artifacts"] == {"unavailable": "no input hash recorded"}
    assert empty["model_version"]["status"] == "unavailable" and "no provenance" in empty["model_version"]["reason"]
    partial = lineage_for_module({"provenance": {"input_hashes": {"x.csv": "a" * 64}}})
    assert partial["code_version"]["git_commit"] == "unavailable" and partial["data_artifacts"] == {"x.csv": "a" * 64}
    upstream = lineage_for_module({"provenance": {"upstream_outputs": ["catalogue_state", "lifetime"], "code_revision": "c" * 40}})
    assert upstream["data_artifacts"] == {"derived_from_upstream_outputs": ["catalogue_state", "lifetime"]}
    recorded = lineage_for_module({"lineage": {"model_version": {"status": "recorded", "digest": "d" * 64}}})
    assert recorded["model_version"]["status"] == "recorded"         # a recorded lineage block is passed through unchanged


@needs_snapshot
def test_new_run_manifests_carry_lineage_with_model_version_unavailable(tmp_path):
    from scripts.run_pipeline import main as run_pipeline_main
    out = tmp_path / "run"
    assert run_pipeline_main(["--as-of", "2026-10-27", "--limit", "20", "--collision-limit", "5", "--debris-sequence-limit", "1",
                              "--health-calibrator", "conformal_bh", "--out", str(out)]) == 0
    manifest = json.loads((out / "run_manifest.json").read_text())
    for name, record in manifest["modules"].items():
        if record["status"] != "success":
            continue
        lin = record["lineage"]
        assert lin["model_version"]["status"] == "unavailable" and lin["model_version"]["digest"] is None
        assert lin["model_version"]["registry_card"] is None
        assert lin["code_version"]["git_commit"] == manifest["git"]["git_commit"]
        assert lin["configuration_version"]["config_sha256"] == manifest["config_sha256"]
        if name == "decision_priority":
            assert lin["data_artifacts"] == {"derived_from_upstream_outputs": ["catalogue_state", "lifetime", "reentry"]}
        else:
            assert all(len(v) == 64 for v in lin["data_artifacts"].values())
    # the four version notions are distinct values, not copies of one another
    lin = manifest["modules"]["lifetime"]["lineage"]
    assert lin["code_version"]["git_commit"] != lin["configuration_version"]["config_sha256"]
    assert lin["configuration_version"]["config_sha256"] not in lin["data_artifacts"].values()


@needs_snapshot
def test_console_shows_model_version_unavailable_and_derives_lineage_for_old_runs():
    client = TestClient(create_app(ROOT))
    runs = client.get("/api/runs").json()["runs"]
    run_id = next(r["run_id"] for r in runs if r["complete"])
    body = client.get(f"/api/runs/{run_id}").json()
    assert set(body["lineage"]) == set(body["modules"]) and set(body["evidence_class"]) == set(body["modules"])
    for name, lin in body["lineage"].items():
        if body["modules"][name]["status"] == "success":
            assert lin["model_version"]["status"] == "unavailable"
    page = client.get(f"/runs/{run_id}").text
    assert "Evidence class and lineage" in page and "UNAVAILABLE" in page and "not a spacecraft health state" in page
    obj = client.get("/api/objects/37607").json()
    assert obj["provenance"]["model_version"]["status"] == "unavailable" and obj["provenance"]["model_version"]["registry_card"] is None
    report = client.get("/api/reports/object/37607").json()
    assert report["provenance"]["model_version"]["status"] == "unavailable" and "distinct" in report["provenance"]["lineage_note"]
    assert "Model version" in client.get("/objects/37607").text


def test_synthetic_run_without_git_or_config_is_displayed_as_unavailable(tmp_path):
    root = tmp_path
    run_dir = root / "outputs" / "pipeline" / "run_nogit"
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "as_of": "2026-10-27", "started_at": "2026-10-27T00:00:00+00:00", "duration_s": 0.1, "successful": True,
        "requested": ["catalogue_state"], "tables_written": [],
        "modules": {"catalogue_state": {"status": "success", "provenance": {"as_of": "2026-10-27", "input_sources": ["x"]}}},
        "interpretation": {"not_established": []}}))
    client = TestClient(create_app(root))
    body = client.get("/api/runs/run_nogit").json()
    lin = body["lineage"]["catalogue_state"]
    assert lin["code_version"]["git_commit"] == "unavailable" and lin["configuration_version"]["config_sha256"] == "unavailable"
    assert lin["model_version"]["status"] == "unavailable"
    page = client.get("/runs/run_nogit")
    assert page.status_code == 200 and "unavailable" in page.text
