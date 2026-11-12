"""End-to-end demonstration journey (Phase C.2): the thirteen stages of /demo executed in order against the real stored
outputs through the application, with the four established objects verified. The scenario stage runs on a fixture root so
that no run directory is added to the repository. Every assertion is a fact the evaluator will see on screen."""
from __future__ import annotations

import html as H
import json
import re

import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from test_p3b_twin_state import AS_OF, make_root

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")


@pytest.fixture(scope="module")
def c() -> TestClient:
    return TestClient(create_app(ROOT), raise_server_exceptions=False)


def flat(text: str) -> str:
    """Visible text only: tags removed, entities decoded, whitespace collapsed (templates wrap and mark up phrases)."""
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def test_stage_01_launch_and_readiness(c):
    assert c.get("/api/health").status_code == 200
    r = c.get("/api/ready"); body = r.json()
    assert r.status_code == 200 and body["ready"] and body["checks"]["dated_forecast_digest_state"] == "verified"
    assert body["checks"]["twin_state_source"]["status"] == "primary" and body["latest_run"]


def test_stage_02_overview(c):
    page = flat(c.get("/").text); ov = c.get("/api/overview").json()
    assert "System readiness" in page and "READY" in page and ov["latest_run"]["run_id"] in page
    assert ov["findings"][0]["level"] == "STALE" and "STALE" in page
    assert sum(1 for v in ov["module_status"].values() if v == "success") == 9
    assert "does not track satellites live" in page


def test_stage_03_satellite_selection(c):
    hit = c.get("/api/objects/search?q=37607").json()
    rows = hit if isinstance(hit, list) else hit.get("results", hit.get("rows", []))
    assert any(str(r.get("norad")) == "37607" and "ARIANE" in str(r.get("name")) for r in rows)
    assert "ARIANE 5 R/B" in c.get("/objects?q=37607").text
    demo_raw = c.get("/demo").text
    for norad in (37607, 23806, 25544, 12):
        assert f'href="/objects/{norad}"' in demo_raw


@pytest.mark.parametrize("norad,expect", [
    (37607, {"lifetime": True, "coherence": "coherent", "reentry_rel": "entirely_before", "lifetime_rel": "crosses", "rank": 2, "high": True}),
    (23806, {"lifetime": True, "coherence": "incoherent", "reentry_rel": "crosses", "rank": 21}),
    (25544, {"lifetime": False, "reentry_q": None, "status_contains": "operator-controlled", "high": True}),
    (12, {"lifetime": True, "reentry_rel": "censored_at_cap"}),
])
def test_stage_04_05_orbital_and_reentry_per_object(c, norad, expect):
    o = c.get(f"/api/objects/{norad}").json(); page = flat(c.get(f"/objects/{norad}").text)
    assert o["lifetime"]["available"] is expect["lifetime"]
    if "coherence" in expect:
        assert o["lifetime"]["horizon_coherence"]["status"] == expect["coherence"]
        if expect["coherence"] == "incoherent":
            assert "ABSTAIN" in page and "not monotone" in page
    if "reentry_rel" in expect:
        assert o["reentry"]["horizon_relation"]["relation"] == expect["reentry_rel"]
    if "lifetime_rel" in expect:
        assert o["lifetime"]["horizon_relation"]["relation"] == expect["lifetime_rel"]
    if "reentry_q" in expect:
        assert o["reentry"]["lo90_days"] is None and expect["status_contains"] in o["reentry"]["evidence_status"]
    if "rank" in expect:
        assert o["decision_priority"]["rank"] == expect["rank"] and f"{expect['rank']}" in page
    if expect.get("high"):
        assert o["decision_priority"]["row"]["high_consequence"] is True
    assert o["provenance"]["model_version"]["status"] == "unavailable" and "UNAVAILABLE" in page
    assert o["elements"]["state_vector"] is None


def test_stage_06_telemetry_and_health_semantics(c):
    raw = c.get("/telemetry").text; page = flat(raw)
    assert "ANONYMISED" in page and "not spacecraft health" in page and 'data-test="methodology"' in raw
    missions = c.get("/api/telemetry/missions").json()
    assert missions["missions"] if isinstance(missions, dict) else missions
    assert c.get("/telemetry/1/channel_1").status_code == 200
    obj = flat(c.get("/objects/37607").text)
    assert "not determinable" in obj and "benchmark screen (no object link)" in obj


def test_stage_07_collision(c):
    raw = c.get("/risk").text; page = flat(raw); ev = c.get("/api/risk/collision").json()
    assert ev["events_total"] == 2167 and 'data-test="methodology"' in raw and "ABSTAIN" in page and "not derived" in page
    assert "not a validated collision-avoidance capability" in page


def test_stage_08_debris(c):
    raw = c.get("/debris").text; page = flat(raw)
    assert "classical COSMOS front end" in page and "scores only" in page and 'data-test="vision-benchmark"' in raw
    seq = c.get("/api/debris/1").json(); assert seq["frames"]
    assert c.get("/api/debris/1/frame/1.png").headers["content-type"] == "image/png"
    assert "not reported" in flat(c.get("/debris/1").text)


def test_stage_09_decision_support(c):
    o = c.get("/api/objects/37607").json(); dp = o["decision_priority"]
    assert dp["rule"]["status"] == "recorded" and "priority_score = p_reentry_30d" in dp["rule"]["formula"]
    assert dp["row"]["priority_score"] == 2.0 and dp["health_escalation"]["status"] == "abstain"
    rid = c.get("/api/ready").json()["latest_run"]
    rk = c.get(f"/api/runs/{rid}/ranking?limit=5").json()
    assert rk["rows"][0]["rank"] == 1 and "horizon_relation" in rk["rows"][0]
    assert "operational ordering" in flat(c.get("/objects/37607").text) or "priority_score" in flat(c.get("/objects/37607").text)


def test_stage_10_twin_state_and_provenance(c):
    ts = c.get("/api/twin-state").json()
    assert ts["overall"]["status"] == "primary_verified" and ts["equivalence"]["records_equal"] == 31396 and ts["equivalence"]["records_different"] == 0
    assert any("operator-controlled" in k for k in ts["equivalence"]["not_comparable_reasons"]) and any("not monotone" in k for k in ts["equivalence"]["not_comparable_reasons"])
    page = flat(c.get("/twin-state").text)
    assert "RE-EMITTED · twin_state/1.1 · verified" in page and "not forced equal" in page
    archived = flat(c.get("/twin-state?policy=archived_only").text)
    assert "HISTORICAL ARCHIVE · twin_state/1.0 · explicit" in archived
    obj = c.get("/api/objects/25544/twin").json()
    assert obj["equivalence"]["status"] == "equal" and "reentry.abstained" in obj["equivalence"]["not_comparable"]
    assert ts["provenance"]["computed_sha256"] == ts["provenance"]["recorded_sha256"] and ts["model_version"]["status"] == "unavailable"


def test_stage_11_scenario_on_a_fixture_root(tmp_path):
    root = make_root(tmp_path)
    fc = TestClient(create_app(root), raise_server_exceptions=False)
    before = {p.name for p in (ROOT / S.PIPELINE_RUNS).iterdir()}
    r = fc.post("/api/scenario", json={"as_of": AS_OF, "limit": 5, "collision_limit": 3, "debris_sequence_limit": 1,
                                       "modules": ["catalogue_state", "lifetime", "reentry", "decision_priority"]})
    assert r.status_code == 200 and r.json()["successful"] and r.json()["assumptions"]
    assert {p.name for p in (ROOT / S.PIPELINE_RUNS).iterdir()} == before
    assert fc.get(f"/runs/{r.json()['run_id']}").status_code == 200


def test_stage_12_pipeline_and_research_evidence(c):
    rid = c.get("/api/ready").json()["latest_run"]
    runs = c.get("/api/runs").json(); runs = runs if isinstance(runs, list) else runs.get("runs")
    assert runs[0]["run_id"] == rid and runs[0]["complete"]
    man = c.get(f"/api/runs/{rid}").json()
    assert set(man["lineage"]) >= {"catalogue_state", "lifetime", "reentry", "decision_priority", "twin_state", "twin_equivalence"}
    page = flat(c.get(f"/runs/{rid}").text)
    assert "twin_equivalence" in page and "first 50 rows (JSON)" in page and "Open raw manifest" in page
    tab = c.get(f"/api/runs/{rid}/tables/decision_ranking.csv?limit=3").json()
    assert tab
    cmp = c.get(f"/api/compare?a={rid}&b=run_20261108T083402Z").json()
    assert cmp["comparable"] and cmp["tables"]["decision_ranking.csv"]["status"] == "identical"
    rep = c.get("/reports/object/37607/download")
    assert rep.status_code == 200 and "Redacted export" in rep.text and str(ROOT) not in rep.text


def test_stage_13_final_summary(c):
    page = flat(c.get("/demo").text)
    assert "Stage 13" in page and "Established" in page and "Outside the validated scope" in page
    assert "K6" in page and "K7" in page and "withdrawn" in page and "not supported" in page
