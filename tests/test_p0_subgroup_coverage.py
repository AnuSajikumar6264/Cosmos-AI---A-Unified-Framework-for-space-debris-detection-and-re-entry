"""P0.1 — the lifetime-interval subgroup-coverage cue (X6 Stage 1 evidence, descriptive only)."""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore, subgroup_coverage_cue

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
EVIDENCE = ROOT / S.AM_DESIGN_STAGE1
pytestmark = pytest.mark.skipif(not (SNAPSHOT.is_file() and EVIDENCE.is_file()), reason="snapshot or X6 evidence absent")


@pytest.fixture(scope="module")
def store() -> ArtifactStore:
    return ArtifactStore(ROOT)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(ROOT))


def test_design_derived_object_gets_the_under_coverage_cue_with_the_x6_figures(store):
    rec = store.object_record(37607)                         # ARIANE 5 R/B, am_source = design
    assert rec["physical"]["area_to_mass_source"] == "design"
    cue = rec["lifetime"]["subgroup_coverage"]
    assert cue["available"] and cue["design_derived"] is True and cue["under_coverage_flag"] is True
    o16 = cue["observed"]["2016"]["80"]
    assert o16["coverage"] == pytest.approx(0.5625, abs=1e-9)
    assert o16["ci95"][0] == pytest.approx(0.512, abs=5e-4) and o16["ci95"][1] == pytest.approx(0.614, abs=5e-4)
    assert o16["nominal"] == 0.80 and o16["below_nominal"] is True and o16["n"] == 656
    # 2011 is reported too, with its own (different) figure — no extrapolation between origins
    assert cue["observed"]["2011"]["80"]["coverage"] == pytest.approx(0.7921, abs=5e-4)
    assert "descriptive" in cue["evidence"] and "not a causal explanation" in cue["evidence"]
    assert "not this object's probability" in cue["not_individual"]
    assert "no outcomes" in cue["scope"] and "nothing is extrapolated" in cue["scope"]
    # the interval values themselves are untouched
    assert rec["lifetime"]["lo90_days"] == pytest.approx(6.9398, abs=1e-3) and rec["lifetime"]["hi90_days"] == pytest.approx(95.3244, abs=1e-3)


def test_class_prior_object_gets_its_own_subgroup_figure_and_no_under_coverage_flag(store):
    table = pd.read_csv(SNAPSHOT, low_memory=False)
    norad = int(table[(table.am_source == "class_prior_sbm") & table.median_days_lifetime.notna()].norad.iloc[0])
    cue = store.object_record(norad)["lifetime"]["subgroup_coverage"]
    assert cue["am_source"] == "class_prior_sbm" and cue["design_derived"] is False
    assert cue["available"] and cue["under_coverage_flag"] is False
    assert cue["observed"]["2016"]["80"]["coverage"] == pytest.approx(0.7606, abs=5e-4)


def test_unknown_source_is_shown_as_unknown_and_never_inferred(store):
    cue = subgroup_coverage_cue(None, store.subgroup_coverage_evidence())
    assert cue["am_source"] == "unknown" and cue["design_derived"] is None and not cue["available"]
    assert "not inferred" in cue["reason"] and cue["observed"] == {} and cue["under_coverage_flag"] is False
    assert S.AM_SOURCE_LABELS["unknown"].startswith("unknown")


def test_missing_evidence_yields_an_explicit_absence_not_a_number():
    cue = subgroup_coverage_cue("design", None)
    assert not cue["available"] and cue["observed"] == {} and "not present" in cue["reason"]
    assert cue["under_coverage_flag"] is False


def test_object_page_and_report_render_the_cue_values(client):
    page = html.unescape(client.get("/objects/37607").text)
    for needle in ("SUBGROUP UNDER-COVERAGE", "design-derived", "0.5625", "0.512–0.614", "nominal 0.80",
                   "descriptive evidence", "not this object's probability", "nothing is extrapolated"):
        assert needle in page, needle
    doc = client.get("/api/reports/object/37607").json()
    assert doc["lifetime"]["subgroup_coverage"]["under_coverage_flag"] is True
    assert any("subgroup under-coverage" in item and "0.5625" in item for item in doc["limitations"])
    assert "0.5625" in doc["uncertainty"]["lifetime"] and "not this object's probability" in doc["uncertainty"]["lifetime"]
    report_html = html.unescape(client.get("/reports/object/37607").text)
    assert "SUBGROUP UNDER-COVERAGE" in report_html and "0.5625" in report_html and "vs nominal 0.80" in report_html
