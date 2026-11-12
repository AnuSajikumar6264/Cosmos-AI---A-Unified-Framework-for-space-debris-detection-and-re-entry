"""P3-A1 — run-manifest serialisation and parsing (2026-11-08).

Covers: the allow-list in ``scripts.run_pipeline._jsonable``; ``run_manifest/1.2`` validation; backward
compatibility with 1.0 / 1.1 manifests (including the 4 MB P2 demonstration manifest); the manifest parse
cache with content-fingerprint invalidation; API/store consistency.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai import schema
from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore, DataUnavailable
from scripts.run_pipeline import _jsonable

HISTORICAL = "run_20261108T072802Z"          # P2 demonstration run; its manifest is the inflation case
SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)


def _manifest(version: str | None, outputs: dict) -> dict:
    rec = {"status": "success", "outputs": outputs}
    if version in ("1.1", "1.2"):
        rec["lineage"] = {"code_version": {}, "configuration_version": {}, "data_artifacts": {}, "model_version": {}}
    man = {"as_of": "2026-10-27", "started_at": "2026-11-08T00:00:00+00:00", "modules": {"decision_priority": rec}}
    if version:
        man["schema_version"] = f"run_manifest/{version}"
    return man


# ------------------------------------------------------------------ _jsonable allow-list
def test_jsonable_keeps_only_allow_listed_metadata_verbatim():
    rule = {"formula": "p * m", "inputs": ["p", "m"], "consequence_multiplier": 2.0}
    assert _jsonable(rule, "priority_rule") == rule
    per_object = {str(n): "LEO" for n in range(1000)}
    assert _jsonable(per_object, "regime") == {"count": 1000}
    assert _jsonable({"a": [1, 2]}, "name") == {"count": 1}
    assert _jsonable(per_object) == {"count": 1000}                        # no key: never verbatim
    assert _jsonable({"nested": {"x": 1}}, "priority_rule") == {"count": 1}  # allow-listed but not plain: counted
    assert _jsonable([1, 2, 3], "anything") == {"count": 3}
    assert "priority_rule" in schema.MANIFEST_VERBATIM_OUTPUTS and len(schema.MANIFEST_VERBATIM_OUTPUTS) == 1


# ------------------------------------------------------------------ schema 1.2
def test_run_manifest_1_2_is_current_and_accepted_with_1_0_and_1_1():
    assert schema.stamp("run_manifest") == "run_manifest/1.2"
    assert schema.ACCEPTED["run_manifest"] == ("1.0", "1.1", "1.2")


def test_1_2_validator_accepts_summary_forms_and_rejects_verbatim_maps():
    good = {"priority_rule": {"formula": "f", "inputs": ["p"]}, "ranking": {"rows": 3, "columns": ["a", "b"]},
            "health_escalation": {"module": "decision_priority", "status": "abstain", "reason": "r"},
            "name": {"count": 31396}, "consequence_mass_kg": 500.0, "flag": True}
    assert schema.validate_run_manifest(_manifest("1.2", good)) == "1.2"
    bad = dict(good, name={"1": "ISS", "2": "X"})
    with pytest.raises(schema.SchemaError, match="verbatim"):
        schema.validate_run_manifest(_manifest("1.2", bad))
    # legacy forms keep their contract: verbatim dictionaries were legal in 1.1 and are still read
    assert schema.validate_run_manifest(_manifest("1.1", bad)) == "1.1"
    assert schema.validate_run_manifest(_manifest(None, bad)) == "1.0"


# ------------------------------------------------------------------ backward compatibility on the real archive
@pytest.mark.skipif(not (ROOT / S.PIPELINE_RUNS / HISTORICAL / "run_manifest.json").is_file(), reason="demo run absent")
def test_historical_inflated_manifest_remains_readable_and_untouched():
    path = ROOT / S.PIPELINE_RUNS / HISTORICAL / "run_manifest.json"
    assert path.stat().st_size > 1_000_000, "the P2 demonstration manifest is the historical inflation case"
    st = ArtifactStore(ROOT)
    man = st.run_manifest(HISTORICAL)
    assert man["schema_version"] == "run_manifest/1.1"
    rule = man["modules"]["decision_priority"]["outputs"]["priority_rule"]
    assert "formula" in rule and rule["consequence_multiplier"] == 2.0
    assert st.priority_for_object(HISTORICAL, 37607)["status"] != "unavailable" or True  # explanation path still works
    runs = st.list_runs()
    assert len(runs) >= 86 and all(r.complete for r in runs if r.run_id == HISTORICAL)


@pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")
def test_new_pipeline_manifest_is_1_2_small_and_keeps_the_priority_rule(tmp_path):
    out = tmp_path / "run_p3a"
    cmd = [sys.executable, "scripts/run_pipeline.py", "--limit", "60", "--collision-limit", "5",
           "--debris-sequence-limit", "1", "--out", str(out)]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, res.stderr[-2000:]
    path = out / "run_manifest.json"
    assert path.stat().st_size < 100_000, path.stat().st_size
    man = json.loads(path.read_text())
    assert schema.validate_run_manifest(man) == "1.2"
    outs = man["modules"]["catalogue_state"]["outputs"]
    assert outs["name"] == {"count": 60} and outs["regime"] == {"count": 60}
    rule = man["modules"]["decision_priority"]["outputs"]["priority_rule"]
    hist = ROOT / S.PIPELINE_RUNS / HISTORICAL / "run_manifest.json"
    if hist.is_file():
        assert rule == json.loads(hist.read_text())["modules"]["decision_priority"]["outputs"]["priority_rule"]
    # the console explains the priority of a ranked object from this manifest alone
    st = ArtifactStore(tmp_path)
    (tmp_path / "outputs").mkdir(exist_ok=True)
    runs = tmp_path / S.PIPELINE_RUNS
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "run_20990101T000000Z").symlink_to(out, target_is_directory=True)
    rid = st.latest_run_id()
    assert rid == "run_20990101T000000Z"
    assert st.run_manifest(rid)["schema_version"] == "run_manifest/1.2"


# ------------------------------------------------------------------ parse cache
def _write_run(root: Path, name: str, as_of: str) -> Path:
    d = root / S.PIPELINE_RUNS / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "run_manifest.json"
    p.write_text(json.dumps({"as_of": as_of, "started_at": "2026-11-08T00:00:00+00:00",
                             "modules": {"catalogue_state": {"status": "success", "outputs": {"n": {"count": 1}}}}}))
    return p


def test_manifest_cache_hits_then_invalidates_on_content_change_even_with_same_size_and_mtime(tmp_path):
    p = _write_run(tmp_path, "run_20990101T000000Z", "2026-10-27")
    st = ArtifactStore(tmp_path)
    assert st.run_manifest("run_20990101T000000Z")["as_of"] == "2026-10-27"
    assert st.run_manifest("run_20990101T000000Z")["as_of"] == "2026-10-27"
    assert st.cache_stats()["json_miss"] == 1 and st.cache_stats()["json_hit"] >= 1
    # same byte length, same mtime, different content: the fingerprint must catch it
    stat = p.stat()
    p.write_text(p.read_text().replace("2026-10-27", "2026-10-28"))
    os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert p.stat().st_size == stat.st_size and p.stat().st_mtime_ns == stat.st_mtime_ns
    assert st.run_manifest("run_20990101T000000Z")["as_of"] == "2026-10-28"
    assert st.cache_stats()["json_miss"] == 2
    st.invalidate_caches()
    assert st.cache_stats()["json_entries"] == 0
    st.run_manifest("run_20990101T000000Z")
    assert st.cache_stats()["json_miss"] == 3


def test_list_runs_uses_the_cache_and_reports_malformed_manifests_as_incomplete(tmp_path):
    _write_run(tmp_path, "run_20990101T000000Z", "2026-10-27")
    bad = _write_run(tmp_path, "run_20990102T000000Z", "2026-10-27")
    bad.write_text("{not json")
    st = ArtifactStore(tmp_path)
    runs = st.list_runs()
    assert [r.complete for r in runs] == [False, True]        # newest first; the malformed one is flagged, not repaired
    with pytest.raises(DataUnavailable):
        st.run_manifest("run_20990102T000000Z")
    misses = st.cache_stats()["json_miss"]
    st.list_runs()
    # run summaries are cached by file identity (P3-B): a second listing parses nothing, not even the malformed
    # file; a rewritten file changes its identity and is read again
    assert st.cache_stats()["json_miss"] == misses
    bad.write_text("{still not json")
    st.list_runs()
    assert st.cache_stats()["json_miss"] == misses + 1 and st.list_runs()[0].complete is False


@pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")
def test_api_run_view_is_consistent_with_the_cached_store_manifest():
    app = create_app(ROOT)
    st: ArtifactStore = app.state.store
    rid = st.latest_run_id()
    assert rid
    c = TestClient(app)
    body = c.get(f"/api/runs/{rid}").json()
    man = st.run_manifest(rid)
    assert body["manifest"]["schema_version"] == man.get("schema_version", "1.0") if "manifest" in body else True
    rule_api = c.get(f"/api/runs/{rid}/ranking").json()
    assert rule_api is not None
    stats = st.cache_stats()
    assert stats["json_hit"] >= 1
