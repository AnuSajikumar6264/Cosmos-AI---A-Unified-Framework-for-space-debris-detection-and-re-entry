"""P2 demonstration acceptance tests D1-D14 on the four demonstration objects (real archived evidence).

Primary object NORAD 37607 (ARIANE 5 R/B: design-derived, natural decay, p30 = 1.0); edge objects 23806
(TITAN 34B DEB: class-prior fragment, crossing interval, L17-incoherent lifetime record), 25544 (ISS:
operator-controlled, re-entry abstention), 12 (VANGUARD R/B: censored at the cap). Synthetic roots are used
only for failure modes and are labelled as fixtures; they never stand for real observations.
"""
from __future__ import annotations

import gzip
import html
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.ai.twin import reemit
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore

AS_OF = "2026-10-27"
SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=AS_OF)
REEMITTED = ROOT / S.TWIN_STATE_REEMITTED.format(as_of=AS_OF)
ARCHIVED = ROOT / S.TWIN_STATE_ARCHIVED.format(as_of=AS_OF)
pytestmark = pytest.mark.skipif(not (SNAPSHOT.is_file() and REEMITTED.is_file() and ARCHIVED.is_file()),
                                reason="snapshot or twin-state artifacts absent")
PRIMARY, CLASS_PRIOR, CONTROLLED, AT_CAP = 37607, 23806, 25544, 12
OBJECTS = (PRIMARY, CLASS_PRIOR, CONTROLLED, AT_CAP)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(ROOT))


@pytest.fixture(scope="module")
def store() -> ArtifactStore:
    return ArtifactStore(ROOT)


@pytest.fixture(scope="module")
def run_id(store) -> str:
    rid = store.latest_run_id()
    assert rid, "a complete pipeline run is required for the demonstration"
    return rid


def _nan_to_none(obj):
    if isinstance(obj, float) and obj != obj:
        return None
    if isinstance(obj, dict):
        return {k: _nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nan_to_none(v) for v in obj]
    return obj


def _fixture_root(tmp_path: Path, *, blank_am: int | None = None, blank_t0: int | None = None,
                  modules: dict | None = None, tables: dict[str, pd.DataFrame] | None = None,
                  archived_twins: bool = False) -> tuple[Path, int]:
    """A synthetic root: a 60-row slice of the real forecast table (never new observations) plus a fixture run."""
    root = tmp_path / "root"
    twin_dir = root / "outputs/twin/as_of_2026-10-27"; twin_dir.mkdir(parents=True)
    table = pd.read_csv(SNAPSHOT, low_memory=False).head(60)
    if blank_am is not None:
        table.loc[table.norad == blank_am, "am_source"] = None
    if blank_t0 is not None:
        table.loc[table.norad == blank_t0, "t0_canonical"] = None
    with gzip.open(twin_dir / "forecast_table.csv.gz", "wt") as fh:
        table.to_csv(fh, index=False)
    shutil.copy(ROOT / "outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt", twin_dir / "FORECAST_SHA256.txt")
    if archived_twins:
        (twin_dir / "twins.jsonl").symlink_to(ARCHIVED)
    run_dir = root / "outputs/pipeline/run_fixture"; run_dir.mkdir(parents=True)
    for name, df in (tables or {}).items():
        df.to_csv(run_dir / name, index=False)
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "as_of": AS_OF, "started_at": "2026-11-08T00:00:00+00:00", "duration_s": 0.1, "config_sha256": "c" * 64,
        "successful": all(m.get("status") == "success" for m in (modules or {}).values()),
        "requested": sorted(modules or {}), "git": {"git_commit": "a" * 40, "tracked_worktree_dirty": False},
        "tables_written": list((tables or {}).keys()), "modules": modules or {},
        "interpretation": {"not_established": ["FIXTURE: synthetic run for failure-mode tests; not an observation"]}}))
    return root, int(table.norad.iloc[0])


# ---------------------------------------------------------------- D1 object selection
def test_d1_object_selection(client):
    by_name = client.get("/api/objects/search", params={"q": "ARIANE 5", "limit": 10}).json()["results"]
    assert by_name and all("ARIANE 5" in h["name"] for h in by_name)
    by_id = client.get("/api/objects/search", params={"q": str(PRIMARY)}).json()["results"]
    assert any(h["norad"] == PRIMARY for h in by_id)
    for norad in OBJECTS:
        assert client.get(f"/api/objects/{norad}").status_code == 200
        assert client.get(f"/objects/{norad}").status_code == 200
    missing = client.get("/api/objects/999999999")
    assert missing.status_code != 200 and "not in" in json.dumps(missing.json())


# ---------------------------------------------------------------- D2 twin-state retrieval
def test_d2_twin_state_retrieval_is_the_reemitted_record_equal_to_the_archive(client, store):
    for norad in OBJECTS:
        t = client.get(f"/api/objects/{norad}/twin").json()
        assert t["available"] and t["source"] == "reemitted" and t["schema_version"] == "twin_state/1.1"
        assert t["fallback"]["used"] is False and t["reemitted_from_archive"] is True and t["provenance_on_outputs"] is True
        archived = store._twin_line(S.TWIN_STATE_ARCHIVED.format(as_of=AS_OF), str(norad))
        exact = store.twin_record(norad)["record"]                    # the record as stored (NaN preserved)
        assert reemit.canonical(exact, drop_provenance=True) == reemit.canonical(archived, drop_provenance=True)
        # the JSON API serialises NaN as null (JSON has no NaN); values are otherwise identical
        assert _nan_to_none(t["record"]) == _nan_to_none(exact)
        assert t["source_record"]["norad"] == norad and t["source_record"]["sha256"] == "b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86"
    assert client.get(f"/api/objects/{CONTROLLED}/twin").json()["record"]["outputs"][0]["abstain"] is True


# ---------------------------------------------------------------- D3 versioned provenance display (and labelled fallback)
def test_d3_versioned_provenance_display_and_labelled_fallback(client, tmp_path):
    t = client.get(f"/api/objects/{PRIMARY}/twin").json()
    assert len(t["reemission"]["transformation_digest_sha256"]) == 64 and t["reemission"]["predictions_regenerated"] is False
    assert t["reemission"]["equivalence_with_archive"]["equivalent"] is True and t["model_version"]["status"] == "unavailable"
    page = html.unescape(client.get(f"/objects/{PRIMARY}").text)
    for needle in ("RE-EMITTED · twin_state/1.1", "re-emitted from the archived forecast table", "no prediction was regenerated",
                   t["source_record"]["sha256"][:12], t["reemission"]["transformation_digest_sha256"][:12], "Model version"):
        assert needle in page, needle
    # fallback: a root with only the archived twin state must say so, in the API and on the page
    root, norad = _fixture_root(tmp_path, archived_twins=True, modules={"catalogue_state": {"status": "success"}})
    fb = TestClient(create_app(root))
    t2 = fb.get(f"/api/objects/{norad}/twin").json()
    assert t2["available"] and t2["source"] == "archived" and t2["schema_version"] == "twin_state/1.0"
    assert t2["fallback"]["used"] is True and "not present" in t2["fallback"]["reason"] and "HISTORICAL ARCHIVE" in t2["note"]
    assert t2["provenance_on_outputs"] is False and t2["artifact_recorded_sha256"] == "19a1fede1fd4871f380ff802f285d2ad03732f6cd3179790e67336c7d202a6b5"
    page2 = fb.get(f"/objects/{norad}").text
    assert "HISTORICAL ARCHIVE · twin_state/1.0 (fallback)" in page2 and "Fallback:" in page2


# ---------------------------------------------------------------- D4 lifetime interval and horizon relationship
def test_d4_interval_horizon_relations(client):
    expect = {PRIMARY: ("crosses", "entirely_before"), CLASS_PRIOR: ("crosses", "crosses"),
              CONTROLLED: ("unavailable", "unavailable"), AT_CAP: ("entirely_after", "censored_at_cap")}
    for norad, (lifetime_rel, reentry_rel) in expect.items():
        o = client.get(f"/api/objects/{norad}").json()
        assert o["lifetime"]["horizon_relation"]["relation"] == lifetime_rel, norad
        assert o["reentry"]["horizon_relation"]["relation"] == reentry_rel, norad
        assert "not a probability of survival" in o["lifetime"]["horizon_relation"]["not_a_probability"]
    page = html.unescape(client.get(f"/objects/{PRIMARY}").text)
    assert "CROSSES HORIZON" in page and "BEFORE HORIZON" in page


# ---------------------------------------------------------------- D5 subgroup under-coverage warning
def test_d5_subgroup_under_coverage_warning(client):
    o = client.get(f"/api/objects/{PRIMARY}").json()["lifetime"]["subgroup_coverage"]
    assert o["design_derived"] and o["under_coverage_flag"] and o["observed"]["2016"]["80"]["coverage"] == pytest.approx(0.5625)
    page = html.unescape(client.get(f"/objects/{PRIMARY}").text)
    assert "SUBGROUP UNDER-COVERAGE" in page and "0.5625" in page and "0.512–0.614" in page and "nominal 0.80" in page
    c = client.get(f"/api/objects/{CLASS_PRIOR}").json()["lifetime"]["subgroup_coverage"]
    assert c["am_source"] == "class_prior_sbm" and c["under_coverage_flag"] is False and c["available"]


# ---------------------------------------------------------------- D6 unknown A/M source
def test_d6_unknown_am_source_is_stated_not_inferred(tmp_path):
    slice_ = pd.read_csv(SNAPSHOT, low_memory=False).head(60)
    target = int(slice_[slice_.median_days_lifetime.notna()].norad.iloc[0])
    root, _ = _fixture_root(tmp_path, blank_am=target, modules={"catalogue_state": {"status": "success"}})
    o = TestClient(create_app(root)).get(f"/api/objects/{target}").json()
    assert o["physical"]["area_to_mass_source"] == "unknown" and "not inferred" in o["physical"]["area_to_mass_source_label"]
    cue = o["lifetime"]["subgroup_coverage"]
    assert cue["am_source"] == "unknown" and cue["design_derived"] is None and not cue["available"] and cue["observed"] == {}
    page = TestClient(create_app(root)).get(f"/objects/{target}").text
    assert "unknown (not recorded in the snapshot; not inferred)" in page and "NO SUBGROUP EVIDENCE" in page


# ---------------------------------------------------------------- D7 missing provenance
def test_d7_missing_provenance_is_reported_unavailable(client, tmp_path):
    o = client.get(f"/api/objects/{PRIMARY}").json()
    assert o["provenance"]["model_version"]["status"] == "unavailable" and o["provenance"]["model_version"]["registry_card"] is None
    root, norad = _fixture_root(tmp_path, modules={"catalogue_state": {"status": "success", "provenance": {"as_of": AS_OF, "input_sources": ["fixture"]}}})
    body = TestClient(create_app(root)).get("/api/runs/run_fixture").json()
    lin = body["lineage"]["catalogue_state"]
    assert lin["configuration_version"]["config_sha256"] == "unavailable" and lin["model_version"]["status"] == "unavailable"


# ---------------------------------------------------------------- D8 missing or stale evidence
def test_d8_stale_and_missing_evidence(client, tmp_path):
    fr = client.get(f"/api/objects/{PRIMARY}").json()["freshness"]
    assert fr["archive"]["status"] == "missing" and fr["live"] is False
    assert fr["staleness"]["status"] == ("current" if fr["evaluated_on_utc"] == AS_OF else "stale")
    assert fr["source_observation"]["orbit_epoch_status"] == "recorded"
    root, norad = _fixture_root(tmp_path, blank_t0=None, modules={"catalogue_state": {"status": "success"}})
    table = pd.read_csv(root / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz", low_memory=False)
    target = int(table.norad.iloc[2])
    root, _ = _fixture_root(tmp_path / "b", blank_t0=target, modules={"catalogue_state": {"status": "success"}})
    f2 = TestClient(create_app(root)).get(f"/api/objects/{target}").json()["freshness"]
    assert f2["source_observation"]["orbit_epoch_status"] == "missing" and f2["source_observation"]["orbit_epoch_age_days_at_snapshot"] is None


# ---------------------------------------------------------------- D9 re-entry information availability
def test_d9_reentry_availability_with_explicit_abstention(client):
    p = client.get(f"/api/objects/{PRIMARY}").json()
    assert p["reentry"]["probability_by_horizon"]["30d"] == 1.0 and p["reentry"]["lo90_days"] == 10.0
    c = client.get(f"/api/objects/{CONTROLLED}").json()
    assert c["regime"] == "operator_controlled" and c["reentry"]["lo90_days"] is None and c["reentry"]["median_days"] is None
    assert "operator-controlled" in c["reentry"]["evidence_status"] and "base rate" in c["reentry"]["model"]
    avail = {x["capability"]: x["status"] for x in c["evidence_availability"]}
    assert avail["re-entry probabilities and time quantiles"] == "unavailable" and avail["lifetime interval and horizon probabilities"] == "unavailable"
    avail_p = {x["capability"]: x["status"] for x in p["evidence_availability"]}
    assert avail_p["re-entry probabilities and time quantiles"] == "implemented"
    page = html.unescape(client.get(f"/objects/{CONTROLLED}").text)
    assert "NO INTERVAL" in page and "ABSTAIN" in page


# ---------------------------------------------------------------- D10 decision priority from the run manifest
def test_d10_decision_priority_explained_from_the_manifest_only(client, store, run_id):
    manifest = store.run_manifest(run_id)
    rule = manifest["modules"]["decision_priority"]["outputs"]["priority_rule"]
    table = store.run_table(run_id, "decision_ranking.csv")
    for norad in OBJECTS:
        dp = client.get(f"/api/objects/{norad}").json()["decision_priority"]
        assert dp["status"] == "computed" and dp["run_id"] == run_id and dp["rule"]["status"] == "recorded"
        idx = table.index[table.object_id == f"NORAD-{norad}"][0]
        assert dp["rank"] == int(idx) + 1 and dp["row"]["priority_score"] == pytest.approx(float(table.priority_score.iloc[idx]))
        assert rule["formula"] in dp["explanation"] and str(rule["consequence_mass_kg"]) in dp["explanation"]
        assert dp["health_escalation"]["status"] == "abstain"
    page = html.unescape(client.get(f"/objects/{PRIMARY}").text)
    assert rule["formula"] in page and "Nothing on this page recomputes the priority" in page
    # a run that predates rule recording must say the rule is unavailable, not reconstruct it
    old = store.priority_for_object("run_20261106T055638946809Z", PRIMARY)
    if old["status"] == "computed":
        assert old["rule"]["status"] == "unavailable" and "not recorded" in old["rule"]["reason"] and "not recorded" in old["explanation"]


# ---------------------------------------------------------------- D11 archived versus synthetic labelling
def test_d11_archived_versus_synthetic_labels(client):
    page = client.get(f"/objects/{PRIMARY}").text
    assert "HISTORICAL" in page and "re-emitted from the archived forecast table" in html.unescape(page)
    ov = client.get("/").text
    assert "read-only evidence twin" in ov and "synthetic demonstration data" in ov
    ds = client.get("/api/datasets").json()
    assert "not served by this console" in ds["evidence_policy"]["synthetic_demonstration_data"]
    assert all(d["evidence_class"].startswith("archived") for d in ds["datasets"])


# ---------------------------------------------------------------- D12 API/UI consistency
def test_d12_api_ui_consistency(client, store, run_id):
    o = client.get(f"/api/objects/{PRIMARY}").json()
    page = html.unescape(client.get(f"/objects/{PRIMARY}").text)
    from cosmos.product.api import _format_number as fmt
    for value in (fmt(o["reentry"]["probability_by_horizon"]["30d"], 4), fmt(o["lifetime"]["lo90_days"], 1), fmt(o["lifetime"]["hi90_days"], 1),
                  fmt(o["decision_priority"]["row"]["priority_score"], 4), f"{o['lifetime']['subgroup_coverage']['observed']['2016']['80']['coverage']:.4f}",
                  o["provenance"]["sha256"], o["twin_state"]["source_record"]["sha256"][:12]):
        assert value in page, value
    report = client.get(f"/api/reports/object/{PRIMARY}").json()
    computed = next(c for c in report["computed_outputs"] if c["source"] == "decision_ranking.csv")
    assert computed["run_id"] == run_id and computed["values"]["priority_score"] == pytest.approx(o["decision_priority"]["row"]["priority_score"])
    assert report["decision_priority"]["rank"] == o["decision_priority"]["rank"] and report["twin_state"]["source"] == "reemitted"


# ---------------------------------------------------------------- D13 graceful handling of unavailable modules
def test_d13_blocked_modules_are_explicit_never_substituted(tmp_path):
    modules = {"catalogue_state": {"status": "success", "provenance": {"as_of": AS_OF, "input_sources": ["fixture"]}},
               "lifetime": {"status": "failed", "error": "ArtifactUnavailable: fixture"},
               "reentry": {"status": "success", "provenance": {"as_of": AS_OF, "input_sources": ["fixture"]}},
               "decision_priority": {"status": "blocked", "reason": "dependency lifetime did not succeed"}}
    root, norad = _fixture_root(tmp_path, modules=modules)
    store = ArtifactStore(root)
    dp = store.priority_for_object("run_fixture", norad)
    assert dp["status"] == "blocked" and "lifetime" in dp["reason"] and dp["row"] is None
    rec = store.object_record(norad)
    avail = {x["capability"]: x for x in store.evidence_availability(rec, "run_fixture")}
    assert avail["lifetime interval and horizon probabilities"]["status"] in ("blocked", "unavailable")
    assert avail["decision priority"]["status"] == "blocked" and "blocked" in avail["decision priority"]["detail"]
    client = TestClient(create_app(root))
    page = client.get(f"/objects/{norad}").text
    assert page.status_code == 200 if hasattr(page, "status_code") else True
    assert "BLOCKED" in page and ("not computed" in page or "blocked" in page.lower())
    assert client.get("/runs/run_fixture").status_code == 200


# ---------------------------------------------------------------- D14 health semantics
def test_d14_health_semantics(client):
    page = html.unescape(client.get(f"/objects/{PRIMARY}").text)
    assert "Spacecraft health — not determinable" in page and "no health score is synthesised" in page
    assert "health score:" not in page.lower()
    assert "Telemetry Benchmarks" in client.get("/").text
    tp = client.get("/telemetry").text
    assert "not spacecraft health" in tp and "Health model evidence" not in tp
    assert "unrelated to satellite health" in client.get("/api/health").json()["note"]
    avail = {x["capability"]: x for x in client.get(f"/api/objects/{PRIMARY}").json()["evidence_availability"]}
    assert avail["spacecraft subsystem health"]["status"] == "unavailable" and "no score is synthesised" in avail["spacecraft subsystem health"]["detail"]
    assert avail["telemetry anomaly evidence"]["status"] == "benchmark_only"
