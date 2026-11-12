"""P1.3 — schema versioning: stamps, validation, legacy acceptance, clear rejection."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai import schema
from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="snapshot absent")


def test_policy_constants_and_stamps():
    assert schema.stamp("run_manifest") == "run_manifest/1.2" and schema.stamp("twin_state") == "twin_state/1.1"
    assert "1.0" in schema.ACCEPTED["twin_state"] and "1.0" in schema.ACCEPTED["run_manifest"]
    assert (ROOT / "docs/architecture/SCHEMA_VERSIONING.md").read_text().count("| `") >= 7


def test_legacy_records_validate_as_1_0_and_bad_records_are_named():
    legacy = {"as_of": "2026-10-27", "started_at": "t", "modules": {"a": {"status": "success"}}}
    assert schema.validate_run_manifest(legacy) == "1.0"
    with pytest.raises(schema.SchemaError, match="missing key 'modules'"):
        schema.validate_run_manifest({"as_of": "x", "started_at": "t"})
    with pytest.raises(schema.SchemaError, match="must carry lineage"):
        schema.validate_run_manifest({**legacy, "schema_version": "run_manifest/1.1"})
    with pytest.raises(schema.SchemaError, match="not accepted"):
        schema.validate_run_manifest({**legacy, "schema_version": "run_manifest/9.0"})
    with pytest.raises(schema.SchemaError, match="not a run_manifest version"):
        schema.validate_run_manifest({**legacy, "schema_version": "twin_state/1.1"})
    with pytest.raises(schema.SchemaError, match="missing columns"):
        schema.validate_forecast_columns(["norad", "Name"])
    rec = {"object_id": "1", "name": "n", "object_class": "P", "as_of": "2026-10-27", "orbit": {}, "physical": {}, "operational_status": None,
           "family": {}, "space_weather": {}, "regime": "unknown",
           "outputs": [{"module": "reentry", "model": "m", "validation": "v", "values": {}, "uncertainty": {}, "abstain": True, "reason": "", "provenance": None}]}
    with pytest.raises(schema.SchemaError, match="abstains without a reason"):
        schema.validate_twin_record(rec)
    rec["outputs"][0]["reason"] = "why"
    assert schema.validate_twin_record(rec) == "1.0"
    with pytest.raises(schema.SchemaError, match="source_record"):
        schema.validate_twin_record({**rec, "schema_version": "twin_state/1.1",
                                     "outputs": [{**rec["outputs"][0], "provenance": {"as_of": "2026-10-27", "input_hashes": {"a": "b"}}}]})


def test_adapters_share_the_forecast_column_set():
    from cosmos.ai import adapters
    src = (ROOT / "cosmos/ai/adapters.py").read_text()
    assert "REQUIRED_FORECAST_COLUMNS" in src and "p_lifetime_1yr" in schema.REQUIRED_FORECAST_COLUMNS


def test_malformed_run_manifest_is_reported_not_crashed(tmp_path):
    runs = tmp_path / "outputs" / "pipeline"
    (runs / "run_badjson").mkdir(parents=True); (runs / "run_badjson" / "run_manifest.json").write_text("{not json")
    (runs / "run_badschema").mkdir(); (runs / "run_badschema" / "run_manifest.json").write_text(json.dumps({"as_of": "2026-10-27"}))
    store = S.ArtifactStore(tmp_path)
    with pytest.raises(S.DataUnavailable, match="not valid JSON"):
        store.run_manifest("run_badjson")
    with pytest.raises(S.DataUnavailable, match="malformed"):
        store.run_manifest("run_badschema")
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/runs/run_badschema").status_code in (404, 409, 422, 503)


@needs_snapshot
def test_api_responses_and_new_manifests_are_stamped(tmp_path):
    client = TestClient(create_app(ROOT))
    assert client.get("/api/objects/37607").json()["schema_version"] == "object_record/1.1"
    assert client.get("/api/overview").json()["schema_version"] == "api/1.2"   # 1.1 → 1.2 (additive, P3-A/P3-B)
    assert client.get("/api/datasets").json()["schema_version"] == "api/1.2"
    run_id = next(r["run_id"] for r in client.get("/api/runs").json()["runs"] if r["complete"])
    assert client.get(f"/api/runs/{run_id}").json()["view_schema_version"] == "api/1.2"
    assert client.get("/api/reports/object/37607").json()["schema_version"] == "1.1"
    from scripts.run_pipeline import main as run_pipeline_main
    out = tmp_path / "run"
    assert run_pipeline_main(["--as-of", "2026-10-27", "--limit", "10", "--collision-limit", "3", "--debris-sequence-limit", "1", "--out", str(out)]) == 0
    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["schema_version"] == "run_manifest/1.2" and schema.validate_run_manifest(manifest) == "1.2"  # 1.1 → 1.2 under P3-A1
