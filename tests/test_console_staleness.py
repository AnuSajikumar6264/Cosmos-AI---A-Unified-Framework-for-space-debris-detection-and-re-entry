"""Phase 7 — the console states the age of the snapshot it serves (added 2026-11-06).

The dated forecast is fixed at 2026-10-27 and the console never ingests a later snapshot, so on any
later day every probability it shows is historical. The overview must say so explicitly, in the API
and on the page, rather than leaving the reader to infer it from a date in a heading. Read-only
checks against the real repository root (GET requests only; nothing is written).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as store_module
from cosmos.product.api import create_app

SNAPSHOT = ROOT / store_module.TWIN_SNAPSHOT.format(as_of="2026-10-27")
pytestmark = pytest.mark.skipif(not SNAPSHOT.is_file(), reason=f"missing {SNAPSHOT}")


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(ROOT))


def test_overview_api_reports_snapshot_age_and_a_stale_finding(client: TestClient) -> None:
    overview = client.get("/api/overview").json()
    age = overview["snapshot_age"]
    assert age["as_of"] == "2026-10-27"
    today = datetime.now(timezone.utc).date()
    assert age["evaluated_on_utc"] == today.isoformat()
    assert age["age_days"] == (today - date(2026, 10, 27)).days
    assert age["stale"] is (age["age_days"] > 0)
    stale = [f for f in overview["findings"] if f["level"] == "STALE"]
    if age["age_days"] > 0:
        assert len(stale) == 1 and "2026-10-27" in stale[0]["text"]
        assert "nothing here is a current forecast" in stale[0]["text"]
    else:
        assert stale == []


def test_overview_page_shows_the_stale_warning(client: TestClient) -> None:
    overview = client.get("/api/overview").json()
    page = client.get("/")
    assert page.status_code == 200
    if overview["snapshot_age"]["age_days"] > 0:
        assert "STALE" in page.text
        assert f"{overview['snapshot_age']['age_days']} days before today" in page.text
