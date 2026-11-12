"""P1.4 — evidence freshness: observation, archive and processing times kept apart; stale/current/missing/inconsistent."""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import freshness

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="snapshot absent")


def test_stale_current_missing_and_inconsistent_cases():
    stale = freshness("2026-10-27", "2011-05-23", "2026-11-06T05:56:38+00:00", "a" * 64, today=date(2026, 11, 8))
    assert stale["staleness"]["status"] == "stale" and stale["staleness"]["snapshot_age_days"] == 12
    assert stale["source_observation"]["orbit_epoch_status"] == "recorded" and stale["source_observation"]["orbit_epoch_age_days_at_snapshot"] == (date(2026, 10, 27) - date(2011, 5, 23)).days
    assert stale["archive"]["status"] == "missing" and stale["archive"]["forecast_generation_time"] is None
    assert stale["processing"]["status"] == "recorded" and stale["consistency"]["status"] == "consistent" and stale["live"] is False
    current = freshness("2026-10-27", "2011-05-23", None, today=date(2026, 10, 27))
    assert current["staleness"]["status"] == "current" and current["processing"]["status"] == "missing"
    missing = freshness("2026-10-27", None, None, today=date(2026, 11, 8))
    assert missing["source_observation"]["orbit_epoch_status"] == "missing" and missing["source_observation"]["orbit_epoch_age_days_at_snapshot"] is None
    assert missing["consistency"]["status"] == "consistent"              # missing is stated, not treated as an error
    bad = freshness("2026-10-27", "2027-01-01", "2026-10-01T00:00:00+00:00", today=date(2026, 11, 8))
    assert bad["consistency"]["status"] == "inconsistent" and len(bad["consistency"]["issues"]) == 2
    future = freshness("2026-10-27", None, None, today=date(2026, 10, 1))
    assert future["staleness"]["status"] == "inconsistent" and future["consistency"]["status"] == "inconsistent"
    assert "no defensible threshold" in stale["staleness"]["orbit_epoch"] and "threshold 0 days" in stale["staleness"]["rule"]
    assert stale["schema_version"] == "freshness/1.0"


@needs_snapshot
def test_object_api_page_and_report_expose_freshness_honestly():
    client = TestClient(create_app(ROOT))
    obj = client.get("/api/objects/37607").json()
    fr = obj["freshness"]
    assert fr["source_observation"]["catalogue_snapshot_date"] == "2026-10-27" and fr["source_observation"]["orbit_canonical_epoch"] == "2011-05-23"
    assert fr["archive"]["status"] == "missing" and fr["live"] is False and fr["staleness"]["status"] in ("stale", "current")
    page = client.get("/objects/37607").text
    assert "Evidence freshness" in page and "MISSING" in page and "nothing here is live" in page
    report = client.get("/api/reports/object/37607").json()
    assert report["freshness"]["archive"]["status"] == "missing" and report["schema_version"] == "1.1"
    assert "Evidence freshness" in client.get("/reports/object/37607").text
    run_id = next(r["run_id"] for r in client.get("/api/runs").json()["runs"] if r["complete"])
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["freshness"]["snapshot_as_of"] == "2026-10-27" and "did not observe" in run["freshness"]["note"]
