"""P3-B performance follow-up — the one narrowly scoped optimisation implemented (debris availability by presence)
and the run-table cache behaviour it relies on. Display-only; no value changes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import api as A
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
SPOTGEO = ROOT / S.SPOTGEO_SUBMISSION


@pytest.mark.skipif(not SPOTGEO.is_file(), reason="SpotGEO submission absent")
def test_debris_availability_is_by_presence_and_matches_the_listing():
    st = ArtifactStore(ROOT)
    d = st.debris_available()
    assert d["available"] is True and d["artifact"] == S.SPOTGEO_SUBMISSION and d["size_bytes"] > 0
    row = [x for x in A._datasets(st)["datasets"] if x["key"] == "debris"][0]
    assert row["available"] is True and row["detail"] == "test split with saved detections"


def test_debris_availability_false_on_an_empty_root(tmp_path):
    st = ArtifactStore(tmp_path)
    assert st.debris_available()["available"] is False and "not present" in st.debris_available()["detail"]
    row = [x for x in A._datasets(st)["datasets"] if x["key"] == "debris"][0]
    assert row["available"] is False and row["detail"] == "not present"


@pytest.mark.skipif(not (SNAPSHOT.is_file() and SPOTGEO.is_file()), reason="artifacts absent")
def test_overview_and_datasets_never_parse_the_detections(monkeypatch):
    def boom(self):
        raise AssertionError("the overview / datasets listing must not parse the SpotGEO detections")
    monkeypatch.setattr(ArtifactStore, "_spotgeo_detections", boom)
    c = TestClient(create_app(ROOT))
    assert c.get("/").status_code == 200
    assert c.get("/api/datasets").status_code == 200
    assert c.get("/api/overview").status_code == 200


@pytest.mark.skipif(not SPOTGEO.is_file(), reason="SpotGEO submission absent")
def test_debris_screens_still_parse_and_serve_the_detections():
    c = TestClient(create_app(ROOT))
    r = c.get("/api/debris/sequences")
    assert r.status_code == 200
    body = r.json()
    seqs = body["sequences"] if isinstance(body, dict) and "sequences" in body else body
    assert seqs and "sequence_id" in seqs[0]


@pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")
def test_indexed_chain_view_equals_the_full_table_comparison_and_is_cheap():
    import time
    from cosmos.ai.twin import reader as R
    st = ArtifactStore(ROOT)
    rid = st.latest_run_id()
    rec = st.twin_record(37607)
    full_view = R.chain_view_from_tables(st.catalogue(), st.run_table(rid, "decision_ranking.csv"),
                                         st.run_table(rid, "reentry_predictions.csv"), st.run_table(rid, "lifetime_estimates.csv"))
    direct = R.compare_record(rec["record"], full_view["37607"])
    assert {k: rec["equivalence"][k] for k in ("status", "fields_compared", "fields_equal", "fields_different")} == \
           {k: direct[k] for k in ("status", "fields_compared", "fields_equal", "fields_different")}
    st.twin_record(25544)                                     # warm every index
    t0 = time.perf_counter()
    for norad in (37607, 23806, 25544, 12, 37607):
        st.twin_record(norad)
    per_call = (time.perf_counter() - t0) / 5
    assert per_call < 0.08, per_call                          # generous: the scan-based version measured ~27 ms of pure overhead
    st.invalidate_caches()
    assert not st._frame_index_cache and not st._frame_cache
