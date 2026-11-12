"""Phase B of the completion mandate — the four demonstration tasks (2026-11-08).

B.1 demonstration protocol consistency; B.2 browser-facing HTML errors with JSON preserved for API, static and JSON
clients; B.3 three-policy twin-source selector on the object page; B.4 System readiness panel on the overview
reusing the readiness record. Fixture roots come from ``test_p3b_twin_state.make_root`` (slices of the real archives).
"""
from __future__ import annotations

import html as H
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from test_p3b_twin_state import AS_OF, make_root

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
needs_archive = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")
PROTOCOL = ROOT / "docs/product/DEMONSTRATION_PROTOCOL.md"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(ROOT), raise_server_exceptions=False)


# ====================================================================== B.1 protocol
def test_protocol_names_the_validated_run_readiness_and_launch_command():
    text = PROTOCOL.read_text()
    assert "run_20261108T121517Z" in text and "/api/ready" in text
    assert "python scripts/check_console_prerequisites.py && python scripts/serve_console.py" in text
    assert "ARCHIVED ONLY: versioned twin state" not in text
    assert "versioned twin state" in text and "GET /no-such-page" in text


# ====================================================================== B.2 errors
def test_unknown_browser_route_renders_the_error_page_with_request_id(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404 and r.headers["content-type"].startswith("text/html")
    assert "NOT FOUND" in r.text and "Mission Overview" in r.text and "/no-such-page" in r.text
    assert re.fullmatch(r"[0-9a-f]{16}", r.headers["x-request-id"])


def test_api_static_and_json_clients_keep_json_errors(client):
    r = client.get("/api/no-such-route")
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"} and "x-request-id" in r.headers
    r = client.get("/static/missing.css")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")
    r = client.get("/no-such-page", headers={"accept": "application/json"})
    assert r.status_code == 404 and r.json() == {"detail": "Not Found"}
    r = client.get("/api/objects/abc")
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)      # FastAPI's standard validation body


def test_invalid_parameters_and_wrong_methods_on_browser_routes_render_html(client):
    r = client.get("/objects/abc")
    assert r.status_code == 422 and r.headers["content-type"].startswith("text/html") and "INVALID" in r.text
    r = client.post("/objects")
    assert r.status_code == 405 and r.headers["content-type"].startswith("text/html") and "NOT ALLOWED" in r.text
    r = client.get("/api/scenario")
    assert r.status_code == 405 and r.headers["content-type"].startswith("application/json")


@needs_archive
def test_existing_error_semantics_are_unchanged(client):
    assert client.get("/api/objects/999999999").status_code == 404 and client.get("/api/objects/999999999").json()["error"] == "data_unavailable"
    page = client.get("/objects/999999999")
    assert page.status_code == 404 and "UNAVAILABLE" in page.text
    assert client.get("/api/runs/nope").status_code in (400, 404)


# ====================================================================== B.3 policy selector
@needs_archive
def test_object_page_offers_the_three_policies_and_default_is_unchanged(client):
    page = H.unescape(client.get("/objects/37607").text)
    assert 'data-test="twin-policy-selector"' in page
    for policy in S.TWIN_SOURCE_POLICIES:
        assert policy in page
    assert "RE-EMITTED · twin_state/1.1" in page and "(fallback)" not in page


@needs_archive
def test_archived_only_and_reemitted_only_policies_on_the_page_and_api(client):
    page = H.unescape(client.get("/objects/37607?policy=archived_only").text)
    assert "HISTORICAL ARCHIVE · twin_state/1.0 (explicit policy)" in page and "Explicit archived read:" in page
    assert "(fallback)" not in page and "Fallback:" not in page       # an explicit archived read is never called a fallback
    api = client.get("/api/objects/37607?policy=archived_only").json()["twin_state"]
    assert api["source"] == "archived" and api["schema_version"] == "twin_state/1.0"
    assert api["selection"]["status"] == "explicit_archived" and api["fallback"]["used"] is False
    only = client.get("/api/objects/37607?policy=reemitted_only").json()["twin_state"]
    assert only["source"] == "reemitted" and only["selection"]["status"] == "primary"
    default = client.get("/api/objects/37607").json()["twin_state"]
    assert default["selection"]["policy"] == S.DEFAULT_TWIN_SOURCE_POLICY and default["source"] == "reemitted"


@needs_archive
def test_invalid_policy_is_rejected_on_page_and_api(client):
    assert client.get("/objects/37607?policy=bogus").status_code == 422
    assert client.get("/api/objects/37607?policy=bogus").status_code == 422
    assert client.get("/api/objects/37607/twin?policy=bogus").status_code == 422


# ====================================================================== B.4 readiness panel
@needs_archive
def test_readiness_panel_shows_the_same_record_as_the_api(client):
    api = client.get("/api/ready"); body = api.json()
    page = H.unescape(client.get("/").text)
    assert 'data-test="system-readiness"' in page
    assert ("READY" in page) and (api.status_code == 200) == body["ready"]
    assert body["latest_run"] in page and body["checks"]["dated_forecast_digest_state"].upper() in page
    assert body["checks"]["twin_state_source"]["status"].upper() in page and body["checks"]["twin_state_source"]["policy"] in page
    assert "says nothing about any spacecraft" in page and (body["checks"]["git_commit"] or "unavailable")[:12] in page
    assert "/api/ready" in page and "failing_checks" in body and "warnings" in body


def test_readiness_panel_reports_not_ready_with_the_failing_check(tmp_path):
    root = make_root(tmp_path)
    (root / S.FORECAST_DIGEST).write_text("0" * 64 + " twins.jsonl\n")      # recorded digest no longer matches
    c = TestClient(create_app(root), raise_server_exceptions=False)
    api = c.get("/api/ready")
    assert api.status_code == 503 and api.json()["failing_checks"] == ["dated_forecast_digest_state"]
    page = H.unescape(c.get("/").text)
    assert "NOT READY" in page and "MISMATCH" in page and "dated_forecast_digest_state" in page


def test_readiness_warnings_name_a_missing_run_and_an_archived_fallback(tmp_path):
    root = make_root(tmp_path, reemitted=False, run=False)
    body = TestClient(create_app(root), raise_server_exceptions=False).get("/api/ready").json()
    assert body["ready"] is True
    assert any("no complete pipeline run" in w for w in body["warnings"])
    assert any("historical archive (fallback)" in w for w in body["warnings"])


# ====================================================================== B.6 run value comparison
import json as _json
from cosmos.ai import adapters as _adapters
from cosmos.ai.orchestration import Orchestrator as _Orchestrator
from scripts.run_pipeline import _module_manifest as _mm, _write_tables as _wt

RUN_NEW, RUN_PREV = "run_20261108T121517Z", "run_20261108T083402Z"
needs_runs = pytest.mark.skipif(not ((ROOT / S.PIPELINE_RUNS / RUN_NEW).is_dir() and (ROOT / S.PIPELINE_RUNS / RUN_PREV).is_dir()),
                                reason="demonstration runs absent")


def _fixture_run_with(root: Path, run_id: str, limit: int | None, as_of: str = AS_OF, select=("decision_priority",)) -> None:
    config = {"root": str(root), "as_of": as_of, "limit": limit, "collision_limit": None, "debris_sequence_limit": None,
              "health_calibrator": None, "collision_model": "cosmos_gated", "twin_source_policy": "prefer_reemitted"}
    ex = _Orchestrator(_adapters.default_modules()).run({}, selected=list(select), config=config)
    run_dir = root / S.PIPELINE_RUNS / run_id; run_dir.mkdir(parents=True, exist_ok=True)
    tables = _wt(ex, run_dir)
    (run_dir / "run_manifest.json").write_text(_json.dumps({
        "schema_version": "run_manifest/1.2", "as_of": as_of, "started_at": ex.started_at, "duration_s": 0.1, "requested": list(ex.requested),
        "config": config, "config_sha256": ex.config_sha256, "successful": ex.successful, "git": {"git_commit": None},
        "tables_written": tables, "modules": _mm(ex), "interpretation": {"not_established": ["FIXTURE"]}}, default=str))


@needs_runs
def test_identical_real_runs_compare_as_identical_by_digest(client):
    cmp = client.get(f"/api/compare?a={RUN_NEW}&b={RUN_PREV}").json()
    assert cmp["comparable"] is True and cmp["config_differences"] == {"twin_source_policy": ["prefer_reemitted", None]}
    statuses = {k: v["status"] for k, v in cmp["tables"].items()}
    assert all(statuses[t] == "identical" for t in ("decision_ranking.csv", "reentry_predictions.csv", "lifetime_estimates.csv", "collision_risk.csv"))
    assert statuses["twin_equivalence.csv"] == "not_compared" and "absent from run" in cmp["tables"]["twin_equivalence.csv"]["reason"]
    page = H.unescape(client.get(f"/compare?a={RUN_NEW}&b={RUN_PREV}").text)
    assert 'data-test="value-comparison"' in page and "IDENTICAL" in page and "Configuration differences" in page and "NOT COMPARED" in page


def test_limited_run_versus_full_run_reports_missing_objects_and_rank_changes(tmp_path):
    root = make_root(tmp_path)                                    # fixture run over 40 objects: run_20990101T000000Z
    _fixture_run_with(root, "run_20990102T000000Z", limit=20)
    from cosmos.product.store import ArtifactStore
    cmp = ArtifactStore(root).compare_runs("run_20990101T000000Z", "run_20990102T000000Z")
    t = cmp["tables"]["decision_ranking.csv"]
    assert cmp["comparable"] and t["status"] == "differences" and t["rows_common"] == 20 and t["only_in_a"] == 20 and t["only_in_b"] == 0
    assert t["rows_different"] == 0 and t["differing_columns"] == {}                  # same values for shared objects
    assert "rank_changes" in t and t["rank_changes"]["objects_moved"] == 0             # the top 20 keep their order
    assert cmp["config_differences"] == {"limit": [None, 20]}
    page = H.unescape(TestClient(create_app(root)).get("/compare?a=run_20990101T000000Z&b=run_20990102T000000Z").text)
    assert "DIFFERENCES" in page and "Only in run_20990101T000000Z" in page


def test_runs_with_different_snapshots_are_not_value_compared(tmp_path):
    root = make_root(tmp_path)
    _fixture_run_with(root, "run_20990103T000000Z", limit=None, as_of="2026-10-28")   # same table, different declared snapshot
    from cosmos.product.store import ArtifactStore
    cmp = ArtifactStore(root).compare_runs("run_20990101T000000Z", "run_20990103T000000Z")
    assert cmp["comparable"] is False and cmp["tables"] == {} and "not compared" in cmp["note"]
    page = H.unescape(TestClient(create_app(root)).get("/compare?a=run_20990101T000000Z&b=run_20990103T000000Z").text)
    assert "NOT DIRECTLY COMPARABLE" in page and "NOT COMPARED" in page


# ====================================================================== B.7 scenario
def test_scenario_page_offers_presets_policy_and_module_choice(client):
    page = client.get("/scenario").text
    assert 'data-test="scenario-presets"' in page and 'id="twin_source_policy"' in page and 'id="modules"' in page
    assert "archived_only" in page and "full_snapshot" in page and "Assumptions" in page


def test_scenario_rejects_an_invalid_twin_policy_and_runs_the_chain_with_an_explicit_archive(tmp_path):
    root = make_root(tmp_path)
    c = TestClient(create_app(root), raise_server_exceptions=False)
    assert c.post("/api/scenario", json={"as_of": AS_OF, "limit": 5, "twin_source_policy": "bogus"}).status_code == 422
    before = {p.name for p in (ROOT / S.PIPELINE_RUNS).iterdir()}
    r = c.post("/api/scenario", json={"as_of": AS_OF, "limit": 5, "collision_limit": 3, "debris_sequence_limit": 1,
                                      "twin_source_policy": "archived_only",
                                      "modules": ["catalogue_state", "lifetime", "reentry", "decision_priority", "twin_state", "twin_equivalence"]})
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body["successful"] is True and body["config"]["twin_source_policy"] == "archived_only" and len(body["config_sha256"]) == 64
    assert any("archived_only" in a for a in body["assumptions"]) and any("plus their dependencies" in a for a in body["assumptions"])
    tw = body["manifest"]["modules"]["twin_state"]["outputs"]
    assert tw["source"] == "archived" and tw["selection_status"] == "explicit_archived" and tw["fallback_used"] is False
    assert body["manifest"]["modules"]["collision"]["status"] == "not_requested"
    assert (root / S.PIPELINE_RUNS / body["run_id"]).is_dir()
    assert {p.name for p in (ROOT / S.PIPELINE_RUNS).iterdir()} == before            # the repository's runs are untouched


# ====================================================================== B.8 methodology blocks, B.9 loading indicator
def test_benchmark_screens_carry_methodology_blocks_and_name_the_served_detector(client):
    for path in ("/telemetry", "/risk", "/debris"):
        page = client.get(path).text
        assert page.count('data-test="methodology"') == 1, path
        assert "Limitations" in page and "Dataset" in page, path
    debris = " ".join(H.unescape(client.get("/debris").text).split())          # templates wrap lines
    assert "classical COSMOS front end" in debris and 'data-test="vision-benchmark"' in debris
    assert "unet" in debris and "scores only" in debris and "no archived per-detection submission" in debris
    assert "classical COSMOS front end" in " ".join(H.unescape(client.get("/debris/1").text).split())


def test_navigation_loading_indicator_is_present(client):
    page = client.get("/").text
    assert 'id="nav-progress"' in page and "nav-progress-pulse" in client.get("/static/console.css").text


# ====================================================================== B.5 / C.1 guided demonstration page
DEMO_PAGES = ("/", "/demo", "/objects", "/objects/37607", "/objects/23806", "/objects/25544", "/objects/12", "/twin-state",
              "/telemetry", "/debris", "/risk", "/runs", "/scenario", "/prospective")


@needs_archive
def test_demo_page_has_thirteen_stages_driven_by_live_values(client):
    page = H.unescape(client.get("/demo").text)
    assert page.count('data-test="demo-stage"') == 13 and 'data-test="demo-capabilities"' in page
    for norad in (37607, 23806, 25544, 12):
        assert f'href="/objects/{norad}"' in page
    o = client.get("/api/objects/37607").json()
    assert f"{o['decision_priority']['rank']} / {o['decision_priority']['ranked_objects']}" in page
    ready = client.get("/api/ready").json()
    assert (ready["latest_run"] or "none") in page
    assert "ABSTAIN (L17)" in page                                   # 23806
    assert "no live telemetry, no on-demand model inference" in page
    assert "Guided Demonstration" in client.get("/").text              # nav entry on every page


@needs_archive
def test_no_broken_internal_links_on_the_demonstration_journey(client):
    seen: set[str] = set()
    for path in DEMO_PAGES:
        page = client.get(path)
        assert page.status_code == 200, path
        for href in set(re.findall(r'href="(/[^"#]*)"', page.text)):
            if href.startswith("/static/") or href in seen:
                continue
            seen.add(href)
            r = client.get(href)
            assert r.status_code < 400, f"{href} (linked from {path}) -> {r.status_code}"
    assert len(seen) > 40


@needs_archive
def test_object_page_links_benchmark_rows_to_their_screens(client):
    page = H.unescape(client.get("/objects/37607").text)
    assert "benchmark screen (no object link)" in page
    for screen in ("/telemetry", "/risk", "/debris", "/twin-state"):
        assert f'href="{screen}"' in page


def test_demo_page_degrades_gracefully_without_artifacts(tmp_path):
    c = TestClient(create_app(tmp_path), raise_server_exceptions=False)
    r = c.get("/demo")
    assert r.status_code == 200 and "NOT READY" in r.text and "NOT IN THIS CHECKOUT" in r.text
