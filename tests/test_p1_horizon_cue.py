"""P1.1 — interval-versus-horizon cue (display only; values and ranking untouched)."""
from __future__ import annotations

import html

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore, horizon_relation

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="snapshot absent")


def test_relations_are_classified_correctly_and_never_as_probabilities():
    assert horizon_relation(5.0, 10.0, 20.0)["relation"] == "entirely_before"
    assert horizon_relation(40.0, 100.0, 400.0)["relation"] == "entirely_after"
    assert horizon_relation(6.9, 27.5, 95.3)["relation"] == "crosses"
    assert horizon_relation(30.0, 30.0, 30.0)["relation"] == "crosses"                 # boundary counts as crossing
    assert horizon_relation(1826.25, 1826.25, 1826.25)["relation"] == "censored_at_cap"
    assert horizon_relation(None, 10.0, 20.0)["relation"] == "unavailable"
    r = horizon_relation(6.9, 27.5, 95.3, p_horizon=0.78)
    assert r["display_only"] is True and r["horizon_days"] == 30.0 and r["p_horizon"] == 0.78
    assert "not a probability of survival" in r["not_a_probability"] and "not a guarantee" in r["not_a_probability"]
    assert "spans the 30-day decision horizon" in r["explanation"]


def test_object_record_carries_both_cues_with_unchanged_values():
    rec = ArtifactStore(ROOT).object_record(37607)
    re_rel, lt_rel = rec["reentry"]["horizon_relation"], rec["lifetime"]["horizon_relation"]
    assert re_rel["relation"] == "entirely_before" and re_rel["interval"] == {"lo": 10.0, "median": 10.0, "hi": 10.0}
    assert re_rel["p_horizon"] == 1.0
    assert lt_rel["relation"] == "crosses" and lt_rel["interval"]["lo"] == pytest.approx(6.9398, abs=1e-3)
    assert rec["reentry"]["lo90_days"] == 10.0 and rec["lifetime"]["hi90_days"] == pytest.approx(95.3244, abs=1e-3)


def test_ranking_view_preserves_order_and_values_and_adds_the_cue():
    store = ArtifactStore(ROOT)
    run_id = store.latest_run_id()
    rows = store.ranking_with_horizon(run_id, limit=10)
    table = store.run_table(run_id, "decision_ranking.csv").head(10)
    assert [r["object_id"] for r in rows] == list(table.object_id)
    assert [r["priority_score"] for r in rows] == pytest.approx(list(table.priority_score))
    assert [r["rank"] for r in rows] == list(range(1, 11))
    assert all(r["horizon_relation"]["relation"] in {"entirely_before", "entirely_after", "crosses", "censored_at_cap", "unavailable"} for r in rows)
    # the run's own tables are untouched
    assert set(store.run_table(run_id, "decision_ranking.csv").columns) == set(table.columns)


def test_console_renders_the_cue_on_object_run_api_and_report():
    client = TestClient(create_app(ROOT))
    page = html.unescape(client.get("/objects/37607").text)
    assert "BEFORE HORIZON" in page and "CROSSES HORIZON" in page and "30-day decision horizon" in page
    assert "not a probability of survival" in page
    run_id = client.get("/api/runs").json()["runs"][0]["run_id"]
    run_id = next(r["run_id"] for r in client.get("/api/runs").json()["runs"] if r["complete"])
    rp = client.get(f"/runs/{run_id}").text
    assert "interval-versus-horizon cue" in rp and "Versus 30-day horizon" in rp and "Display only" in rp
    api = client.get(f"/api/runs/{run_id}/ranking", params={"limit": 5}).json()
    assert api["returned"] == 5 and api["horizon_days"] == 30.0 and "display only" in api["note"]
    assert all("horizon_relation" in r and "priority_score" in r for r in api["rows"])
    doc = client.get("/api/reports/object/37607").json()
    assert doc["horizon_relation"]["decision_horizon_days"] == 30.0 and doc["horizon_relation"]["reentry"]["relation"] == "entirely_before"
    assert "30-day decision horizon" in client.get("/reports/object/37607").text
