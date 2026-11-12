"""Product tests for the COSMOS-AI Mission Intelligence Console.

Covers the seventeen behaviours required of the product: page loading, search and selection,
historical run loading and provenance, scenario execution, failure and absence handling,
missing telemetry and missing debris confidence, lifetime horizon incoherence, C4 abstention,
the physical-probability/operational-priority separation, snapshot mismatch, report generation
and provenance, refusal to overwrite historical artifacts, and the prospective mode staying
disabled while blocked.

Tests that need the large saved artifacts skip (never pass) when they are absent. Tests of
failure behaviour build a synthetic repository root so they do not depend on a broken state
existing in the real workspace.

Passing these tests demonstrates product behaviour under tested conditions. It is not
scientific validation of any prediction.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cosmos.ai.provenance import ROOT
from cosmos.product import store as store_module
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore

SNAPSHOT = ROOT / store_module.TWIN_SNAPSHOT.format(as_of="2026-10-27")
TELEMETRY = ROOT / store_module.TELEMETRY_DIR / "mission1.npz"
SPOTGEO = ROOT / store_module.SPOTGEO_SUBMISSION
CONJUNCTION = ROOT / store_module.CONJUNCTION_PREDICTIONS

needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason=f"missing {SNAPSHOT}")
needs_telemetry = pytest.mark.skipif(not TELEMETRY.is_file(), reason=f"missing {TELEMETRY}")
needs_spotgeo = pytest.mark.skipif(not SPOTGEO.is_file(), reason=f"missing {SPOTGEO}")
needs_conjunction = pytest.mark.skipif(not CONJUNCTION.is_file(), reason=f"missing {CONJUNCTION}")


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    """The console bound to a disposable root that mirrors the repository read-only.

    `data`, `outputs/benchmarks` and `outputs/twin` are symlinks to the real directories, and
    `outputs/pipeline` is a fresh directory holding a symlink to every existing run. Scenario tests
    therefore create run directories only inside the temporary root — the repository's
    `outputs/pipeline/` is never written to by the test suite (Phase 6 determinism item, 2026-11-06).
    """
    root = tmp_path_factory.mktemp("console_root")
    # a git repository of its own, so provenance records a real (fixture) commit instead of an error
    # and nothing ever touches the repository's .git
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=cosmos-tests", "-c", "user.email=tests@example.invalid",
                    "commit", "-q", "--allow-empty", "-m", "disposable console root for tests"], check=True)
    (root / "outputs").mkdir()
    for relative in ("data", "outputs/benchmarks", "outputs/twin"):
        (root / relative).symlink_to(ROOT / relative, target_is_directory=True)
    runs = root / "outputs" / "pipeline"
    runs.mkdir()
    for run in (ROOT / "outputs" / "pipeline").iterdir():
        if run.is_dir():
            (runs / run.name).symlink_to(run, target_is_directory=True)
    return TestClient(create_app(root))


def _client_root(client: TestClient) -> Path:
    return Path(client.app.state.root)


@pytest.fixture
def synthetic_root(tmp_path: Path) -> Path:
    """A repository root holding only pipeline runs, for failure-behaviour tests."""
    (tmp_path / "outputs" / "pipeline").mkdir(parents=True)
    return tmp_path


def _write_run(root: Path, run_id: str, modules: dict, *, successful: bool = True,
               as_of: str = "2026-10-27", manifest: bool = True,
               tables: list[str] | None = None) -> Path:
    run_dir = root / "outputs" / "pipeline" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if manifest:
        (run_dir / "run_manifest.json").write_text(json.dumps({
            "as_of": as_of,
            "started_at": f"{as_of}T00:00:00+00:00",
            "duration_s": 0.5,
            "config_sha256": "c" * 64,
            "successful": successful,
            "requested": sorted(modules),
            "git": {"git_commit": "a" * 40, "tracked_worktree_dirty": False},
            "tables_written": tables or [],
            "modules": modules,
            "interpretation": {"not_established": ["fixture run establishes nothing scientific"]},
        }))
    return run_dir


def _flat(text: str) -> str:
    """Collapse whitespace so an assertion is not broken by template line wrapping."""
    return " ".join(text.split())


def _module(status: str, as_of: str = "2026-10-27", **extra) -> dict:
    record = {"status": status, "reason": "", "error": "", "duration_s": 0.1, "outputs": {},
              "provenance": {"as_of": as_of, "input_sources": ["fixture"],
                             "input_hashes": {}, "config_digest": "c" * 64}}
    record.update(extra)
    return record


# ============================================================ 1. dashboard loading
@needs_snapshot
def test_01_dashboard_pages_load(client: TestClient) -> None:
    for path in ("/", "/objects", "/telemetry", "/debris", "/risk", "/runs",
                 "/scenario", "/prospective"):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert "COSMOS-AI" in response.text

    overview = client.get("/api/overview").json()
    assert overview["catalogue"]["objects"] > 0
    # The evidence boundary must be stated on the landing page.
    landing = client.get("/").text
    assert "does <strong>not</strong> track satellites live" in _flat(landing)
    assert "not scientific validation" in landing


def test_01b_app_health_is_not_a_satellite_health_claim(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "unrelated to satellite health" in body["note"]


# ================================================== 2. object search and selection
@needs_snapshot
def test_02_object_search_and_selection(client: TestClient) -> None:
    by_name = client.get("/api/objects/search", params={"q": "ARIANE", "limit": 5}).json()
    assert by_name["results"], "name search returned nothing"
    assert all("ARIANE" in row["name"].upper() for row in by_name["results"])

    norad = by_name["results"][0]["norad"]
    by_id = client.get("/api/objects/search", params={"q": str(norad)}).json()
    assert any(row["norad"] == norad for row in by_id["results"])

    page = client.get(f"/objects/{norad}")
    assert page.status_code == 200
    assert str(norad) in page.text

    record = client.get(f"/api/objects/{norad}").json()
    assert record["norad"] == norad
    assert record["as_of"] == "2026-10-27"
    # Mean elements must not be presented as a state vector.
    assert record["elements"]["state_vector"] is None
    assert "mean elements" in record["elements"]["element_set"]


@needs_snapshot
def test_02b_unknown_object_reports_absence_not_a_guess(client: TestClient) -> None:
    response = client.get("/objects/999999999")
    assert response.status_code == 404
    assert "not in the" in response.text
    assert client.get("/api/objects/999999999").status_code == 404
    # A malformed identifier is rejected before any lookup.
    assert client.get("/api/objects/abc").status_code == 422


# ===================================================== 3. historical run loading
@needs_snapshot
def test_03_historical_run_loads_without_recomputation(client: TestClient) -> None:
    runs = client.get("/api/runs").json()["runs"]
    assert runs, "no pipeline run available"
    run_id = next(run["run_id"] for run in runs if run["complete"])

    manifest_path = _client_root(client) / "outputs" / "pipeline" / run_id / "run_manifest.json"
    before = manifest_path.read_bytes()
    page = client.get(f"/runs/{run_id}")
    assert page.status_code == 200
    assert run_id in page.text
    assert "HISTORICAL" in page.text
    assert "never recomputed" in page.text
    after = manifest_path.read_bytes()
    assert before == after, "loading a historical run modified its manifest"


# ======================================================= 4. correct run provenance
@needs_snapshot
def test_04_run_provenance_is_complete_and_displayed(client: TestClient) -> None:
    runs = client.get("/api/runs").json()["runs"]
    run_id = next(run["run_id"] for run in runs if run["complete"])
    manifest = client.get(f"/api/runs/{run_id}").json()

    assert len(manifest["config_sha256"]) == 64
    assert manifest["git"]["git_commit"]
    assert manifest["as_of"]
    for name, record in manifest["modules"].items():
        if record["status"] == "success":
            assert record["provenance"]["config_digest"] == manifest["config_sha256"], name
            assert record["provenance"]["as_of"] == manifest["as_of"], name

    page = client.get(f"/runs/{run_id}").text
    assert manifest["config_sha256"] in page
    assert manifest["git"]["git_commit"] in page


# ========================================================== 5. scenario execution
@needs_snapshot
def test_05_scenario_execution_creates_a_new_run(client: TestClient) -> None:
    runs_dir = _client_root(client) / "outputs" / "pipeline"
    repo_runs_before = {path.name for path in (ROOT / "outputs" / "pipeline").iterdir()}
    before = {path.name for path in runs_dir.iterdir()}
    response = client.post("/api/scenario", json={
        "as_of": "2026-10-27", "limit": 40, "collision_limit": 10,
        "debris_sequence_limit": 1, "health_calibrator": "conformal_bh",
    })
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "scenario"
    assert result["exit_code"] == 0
    assert result["successful"] is True

    after = {path.name for path in runs_dir.iterdir()}
    # the repository's own run directory is untouched by the test
    assert {path.name for path in (ROOT / "outputs" / "pipeline").iterdir()} == repo_runs_before
    created = after - before
    assert created == {result["run_id"]}, "scenario did not create exactly one new run"
    # Previous runs must all survive.
    assert before <= after
    assert "does not retrain" in result["note"]


@needs_snapshot
def test_05b_scenario_rejects_invalid_input(client: TestClient) -> None:
    assert client.post("/api/scenario", json={"as_of": "nonsense"}).status_code == 422
    assert client.post("/api/scenario", json={"as_of": "2026-10-27",
                                              "limit": -1}).status_code == 422
    unknown = client.post("/api/scenario", json={"as_of": "2026-10-27",
                                                 "modules": ["not_a_module"]})
    assert unknown.status_code == 400
    assert "not_a_module" in unknown.json()["detail"]


# ===================================================== 6. failed module handling
def test_06_failed_module_is_shown_with_blocked_dependants(synthetic_root: Path) -> None:
    _write_run(synthetic_root, "run_20261104T000000Z", {
        "catalogue_state": _module(
            "failed",
            error="ArtifactUnavailable: required artifact is not present: forecast_table.csv.gz"),
        "lifetime": _module("blocked", reason="dependencies did not succeed: catalogue_state"),
        "debris": _module("success"),
    }, successful=False)
    client = TestClient(create_app(synthetic_root))

    page = client.get("/runs/run_20261104T000000Z")
    assert page.status_code == 200
    assert "ArtifactUnavailable" in page.text
    assert "dependencies did not succeed: catalogue_state" in page.text
    assert "status-failed" in page.text and "status-blocked" in page.text

    runs = client.get("/api/runs").json()["runs"]
    assert runs[0]["successful"] is False
    assert runs[0]["module_counts"]["failed"] == 1
    assert runs[0]["module_counts"]["blocked"] == 1

    overview = client.get("/api/overview").json()
    levels = {finding["level"] for finding in overview["findings"]}
    assert "FAIL" in levels


# ==================================================== 7. optional module absence
def test_07_optional_module_absence_is_neutral(synthetic_root: Path) -> None:
    _write_run(synthetic_root, "run_20261104T000000Z", {
        "catalogue_state": _module("success"),
        "debris": {"status": "not_requested", "reason": "", "error": "", "outputs": {}},
    })
    client = TestClient(create_app(synthetic_root))

    page = client.get("/runs/run_20261104T000000Z")
    assert "not_requested" in page.text
    runs = client.get("/api/runs").json()["runs"]
    # An unrequested optional module must not make the run a failure.
    assert runs[0]["successful"] is True
    assert runs[0]["module_counts"]["not_requested"] == 1

    overview = client.get("/api/overview").json()
    assert "FAIL" not in {finding["level"] for finding in overview["findings"]}


def test_07b_absent_datasets_are_reported_as_unavailable(synthetic_root: Path) -> None:
    client = TestClient(create_app(synthetic_root))
    datasets = client.get("/api/datasets").json()["datasets"]
    assert datasets, "dataset inventory should still be returned"
    assert all(entry["available"] is False for entry in datasets)

    page = client.get("/")
    assert page.status_code == 200
    assert "UNAVAILABLE" in page.text
    # Absent data must never be rendered as a zero or a placeholder figure.
    assert "no catalogue snapshot is present" in _flat(page.text)


# ========================================================= 8. missing telemetry
@needs_snapshot
def test_08_catalogue_object_reports_no_telemetry(client: TestClient) -> None:
    record = client.get("/api/objects/37607").json()
    assert record["telemetry"]["available"] is False
    assert "anonymised" in record["telemetry"]["reason"]

    page = client.get("/objects/37607").text
    assert "UNSUPPORTED for this object" in page
    # No fabricated series or score may appear for this object.
    assert "anomaly score" not in page.lower()


@needs_telemetry
def test_08b_telemetry_is_real_and_anonymised(client: TestClient) -> None:
    missions = client.get("/api/telemetry/missions").json()
    assert missions["available"] is True
    assert all(mission["anonymised"] for mission in missions["missions"])
    assert "cannot be matched to a NORAD" in missions["identity_note"]

    series = client.get("/api/telemetry/1/channel_12", params={"max_points": 300}).json()
    assert series["returned_points"] <= 300
    assert series["total_samples"] > series["returned_points"]
    assert series["decimation_stride"] > 1
    assert series["missing_samples"] >= 0
    # Missing samples are preserved as nulls, not filled.
    # Missing samples are counted and surfaced; the strided subsample need not hit one.
    assert all(value is None or isinstance(value, float) for value in series["values"])
    full = client.get("/api/telemetry/1/channel_12", params={"max_points": 20000}).json()
    assert full["missing_samples"] == series["missing_samples"]
    assert "no per-sample anomaly score" in series["score_note"]

    unknown = client.get("/api/telemetry/1/channel_99999")
    assert unknown.status_code == 404
    assert client.get("/api/telemetry/9/channel_1").status_code == 400


# =================================================== 9. missing debris confidence
@needs_spotgeo
def test_09_debris_confidence_and_timestamp_absent(client: TestClient) -> None:
    record = client.get("/api/debris/1").json()
    assert record["confidence_available"] is False
    assert record["timestamp_available"] is False
    assert record["astrometric_calibration"] is False
    for frame in record["frames"]:
        for detection in frame["detections"]:
            assert detection["confidence"] is None

    page = client.get("/debris/1").text
    assert "not reported" in page
    assert "UNAVAILABLE" in page
    assert "none is invented" in _flat(page)


@needs_spotgeo
def test_09b_debris_image_is_served_and_path_traversal_refused(client: TestClient) -> None:
    image = client.get("/api/debris/1/frame/1.png")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert client.get("/api/debris/1/frame/99.png").status_code == 400


# ================================================ 10. lifetime horizon incoherence
@needs_snapshot
def test_10_lifetime_horizon_incoherence_is_surfaced(client: TestClient) -> None:
    table = pd.read_csv(SNAPSHOT, usecols=["norad", "p_lifetime_30d", "p_lifetime_90d",
                                           "p_lifetime_1yr"])
    values = table.dropna()
    violating = values[(values["p_lifetime_30d"] > values["p_lifetime_90d"]) |
                       (values["p_lifetime_90d"] > values["p_lifetime_1yr"])]
    if violating.empty:
        pytest.skip("no non-coherent object in this snapshot")

    norad = int(violating.iloc[0]["norad"])
    record = client.get(f"/api/objects/{norad}").json()
    coherence = record["lifetime"]["horizon_coherence"]
    assert coherence["status"] == "incoherent"
    assert "independent isotonic" in coherence["explanation"]
    # The decision not to recalibrate must be visible, and the final forecast exempted.
    assert "final reported forecast is unaffected" in coherence["explanation"]

    page = client.get(f"/objects/{norad}").text
    assert "INCOHERENT" in page

    coherent = client.get("/api/objects/37607").json()["lifetime"]["horizon_coherence"]
    assert coherent["status"] in {"coherent", "unavailable"}


@needs_snapshot
def test_10b_capped_and_zero_width_intervals_are_not_shown_as_precision(
    client: TestClient,
) -> None:
    """A quantile pile-up at the study cap must not read as a precise prediction."""
    table = pd.read_csv(SNAPSHOT, usecols=["norad", "median_days", "lo90_days", "hi90_days"])
    capped = table[table["median_days"] == store_module.CAP_DAYS]
    if capped.empty:
        pytest.skip("no capped object in this snapshot")

    norad = int(capped.iloc[0]["norad"])
    quality = client.get(f"/api/objects/{norad}").json()["reentry"]["interval_quality"]
    assert quality["kind"] == "at_cap"
    assert quality["censored_at_cap"] is True
    assert "not as an estimated lifetime" in quality["detail"]

    page = client.get(f"/objects/{norad}").text
    assert "AT CAP" in page
    assert "not estimable" in _flat(page)
    assert "Do not read this interval as precision" in _flat(page)


# ============================================================= 11. C4 abstention
@needs_conjunction
def test_11_c4_escalation_abstains_with_a_reason(client: TestClient) -> None:
    evidence = client.get("/api/risk/collision", params={"limit": 5}).json()
    assert evidence["escalation_available"] is False
    assert "no dataset links telemetry health" in evidence["escalation_reason"]

    page = client.get("/risk").text
    assert "ABSTAIN" in page
    assert "No health-driven escalation" in page
    assert "must never change the physical probability" in _flat(page)


@needs_snapshot
def test_11b_c4_abstention_appears_in_the_run_and_overview(client: TestClient) -> None:
    overview = client.get("/api/overview").json()
    texts = " ".join(finding["text"] for finding in overview["findings"])
    assert "C4" in texts
    assert "not identity-linked" in texts or "identity" in texts


# ======================= 12. physical probability vs operational priority
@needs_conjunction
def test_12_physical_probability_is_separate_from_operational_priority(
    client: TestClient,
) -> None:
    evidence = client.get("/api/risk/collision", params={"limit": 50}).json()
    assert evidence["identity_linkable"] is False
    for event in evidence["events"]:
        assert 0.0 <= event["collision_probability"] <= 1.0
        assert event["interval_lower"] <= event["interval_upper"]
        # Priority must never be attached to a physical probability record.
        assert event["operational_priority"] is None
    assert "not derived here" in evidence["priority_note"]

    page = client.get("/risk").text
    assert "not derived" in page
    assert "never computed from, or fused into, a physical probability" in _flat(page)


@needs_snapshot
def test_12b_decision_priority_does_not_alter_upstream_probabilities(
    client: TestClient,
) -> None:
    runs = client.get("/api/runs").json()["runs"]
    run_id = next(run["run_id"] for run in runs
                  if run["complete"] and "decision_ranking.csv" in run["tables"]
                  and "reentry_predictions.csv" in run["tables"])
    ranking = client.get(f"/api/runs/{run_id}/tables/decision_ranking.csv",
                         params={"limit": 50}).json()["records"]
    reentry = client.get(f"/api/runs/{run_id}/tables/reentry_predictions.csv",
                         params={"limit": 20000}).json()["records"]
    source = {row["object_id"]: row for row in reentry}

    assert ranking
    for row in ranking:
        upstream = source.get(row["object_id"])
        if upstream is None:
            continue
        assert row["p_reentry_30d"] == upstream["p_30d"], row["object_id"]


# ========================================================= 13. snapshot mismatch
def test_13_snapshot_mismatch_within_a_run_is_flagged(synthetic_root: Path) -> None:
    _write_run(synthetic_root, "run_20261104T000000Z", {
        "catalogue_state": _module("success", as_of="2026-10-27"),
        "lifetime": _module("success", as_of="2026-08-16"),
    })
    client = TestClient(create_app(synthetic_root))

    runs = client.get("/api/runs").json()["runs"]
    assert runs[0]["snapshot_consistent"] is False
    assert set(runs[0]["as_of_dates"]) == {"2026-08-16", "2026-10-27"}

    assert "MIXED" in client.get("/runs").text
    page = client.get("/runs/run_20261104T000000Z").text
    assert "MIXED" in page

    overview = client.get("/api/overview").json()
    assert any("mixes snapshots" in finding["text"] for finding in overview["findings"])


def test_13b_runs_with_different_snapshots_are_not_called_comparable(
    synthetic_root: Path,
) -> None:
    _write_run(synthetic_root, "run_20261101T000000Z",
               {"catalogue_state": _module("success", as_of="2026-08-16")},
               as_of="2026-08-16")
    _write_run(synthetic_root, "run_20261104T000000Z",
               {"catalogue_state": _module("success", as_of="2026-10-27")},
               as_of="2026-10-27")
    client = TestClient(create_app(synthetic_root))

    page = client.get("/compare", params={"a": "run_20261101T000000Z",
                                          "b": "run_20261104T000000Z"}).text
    assert "NOT DIRECTLY COMPARABLE" in page
    assert "not combined" in _flat(page)


def test_13c_one_run_is_rendered_at_a_time(synthetic_root: Path) -> None:
    _write_run(synthetic_root, "run_20261101T000000Z",
               {"catalogue_state": _module("success")}, tables=["older_table.csv"])
    _write_run(synthetic_root, "run_20261104T000000Z",
               {"catalogue_state": _module("success")}, tables=["newer_table.csv"])
    client = TestClient(create_app(synthetic_root))

    page = client.get("/runs/run_20261104T000000Z").text
    assert "newer_table.csv" in page
    assert "older_table.csv" not in page


def test_13d_incomplete_run_is_not_presented_as_finished(synthetic_root: Path) -> None:
    _write_run(synthetic_root, "run_20261104T000000Z", {}, manifest=False)
    client = TestClient(create_app(synthetic_root))

    runs = client.get("/api/runs").json()["runs"]
    assert runs[0]["complete"] is False
    assert runs[0]["successful"] is None
    assert "INCOMPLETE" in client.get("/runs").text
    # A manifest-less run cannot be opened as if it held results.
    assert client.get("/runs/run_20261104T000000Z").status_code == 404


# ========================================================= 14. report generation
@needs_snapshot
def test_14_report_generation(client: TestClient) -> None:
    document = client.get("/api/reports/object/37607").json()
    assert document["report_type"] == "object_assessment"
    assert document["subject"]["norad"] == 37607
    assert document["limitations"]
    assert document["unsupported_assessments"]

    html_report = client.get("/reports/object/37607")
    assert html_report.status_code == 200
    assert "COSMOS-AI assessment report" in html_report.text
    assert "ARIANE 5 R/B" in html_report.text

    download = client.get("/reports/object/37607/download")
    assert download.status_code == 200
    disposition = download.headers["content-disposition"]
    assert "attachment" in disposition and "NORAD37607" in disposition


@needs_snapshot
def test_14b_report_separates_computed_historical_and_unsupported(
    client: TestClient,
) -> None:
    document = client.get("/api/reports/object/37607").json()
    assert document["historical_outputs"]
    for row in document["historical_outputs"]:
        assert "not recomputed" in row["note"]
        assert len(row["sha256"]) == 64

    statuses = {row["status"] for row in document["unsupported_assessments"]}
    assert statuses <= {"UNSUPPORTED", "BLOCKED"}
    assessments = " ".join(row["assessment"] for row in document["unsupported_assessments"])
    assert "Telemetry" in assessments
    assert "Impact location" in assessments
    assert "state vector" in assessments.lower()

    rendered = client.get("/reports/object/37607").text
    assert "HISTORICAL" in rendered
    assert "COMPUTED" in rendered
    assert "not real-time" in _flat(rendered)


# ========================================================= 15. report provenance
@needs_snapshot
def test_15_report_provenance_is_traceable(client: TestClient) -> None:
    runs = client.get("/api/runs").json()["runs"]
    run_id = next(run["run_id"] for run in runs if run["complete"])
    document = client.get("/api/reports/object/37607", params={"run_id": run_id}).json()

    assert document["provenance"]["run"]["run_id"] == run_id
    assert document["provenance"]["run"]["explicitly_requested"] is True
    assert document["provenance"]["git_commit"]
    assert len(document["inputs"]["catalogue_sha256"]) == 64
    assert document["inputs"]["snapshot_as_of"] == "2026-10-27"
    assert document["inputs"]["catalogue_artifact"].endswith(".csv.gz")

    # The digest must match the artifact on disk.
    from cosmos.ai.provenance import sha256_file
    assert sha256_file(ROOT / document["inputs"]["catalogue_artifact"]) == \
        document["inputs"]["catalogue_sha256"]

    rendered = client.get("/reports/object/37607", params={"run_id": run_id}).text
    assert run_id in rendered
    assert document["inputs"]["catalogue_sha256"] in rendered


@needs_snapshot
def test_15b_report_records_an_unavailable_run_instead_of_omitting_it(
    client: TestClient,
) -> None:
    document = client.get("/api/reports/object/37607",
                          params={"run_id": "run_does_not_exist"}).json()
    assert document["provenance"]["run"]["state"] == "unavailable"
    assert document["computed_outputs"] == []


# ============================================= 16. no overwrite of historical artifacts
@needs_snapshot
def test_16_scenario_does_not_overwrite_historical_artifacts(client: TestClient) -> None:
    runs = client.get("/api/runs").json()["runs"]
    existing = next(run["run_id"] for run in runs if run["complete"])
    run_dir = _client_root(client) / "outputs" / "pipeline" / existing
    before = {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()}
    snapshot_before = SNAPSHOT.read_bytes()[:4096]

    response = client.post("/api/scenario", json={
        "as_of": "2026-10-27", "limit": 20, "collision_limit": 5,
        "debris_sequence_limit": 1,
    })
    assert response.status_code == 200
    new_run_id = response.json()["run_id"]
    assert new_run_id != existing

    after = {path.name: path.read_bytes() for path in run_dir.iterdir() if path.is_file()}
    assert before == after, "an existing run directory was modified"
    assert SNAPSHOT.read_bytes()[:4096] == snapshot_before, "a source artifact was modified"


def test_16b_run_directory_collision_is_refused(synthetic_root: Path) -> None:
    """The pipeline refuses to write into a non-empty run directory."""
    from scripts.run_pipeline import main as run_pipeline_main

    occupied = synthetic_root / "outputs" / "pipeline" / "run_existing"
    occupied.mkdir(parents=True)
    (occupied / "decision_ranking.csv").write_text("object_id\nNORAD-1\n")

    with pytest.raises(SystemExit, match="never overwritten"):
        run_pipeline_main(["--as-of", "2026-10-27", "--out", str(occupied)])
    # The original content survives.
    assert (occupied / "decision_ranking.csv").read_text() == "object_id\nNORAD-1\n"


# ============================= 17. prospective evaluation disabled when blocked
def test_17_prospective_evaluation_is_disabled_while_blocked(client: TestClient) -> None:
    status = client.get("/api/prospective").json()
    assert status["mode"] == "prospective"
    if status["status"] == "READY":
        pytest.skip("a qualifying later snapshot is now present; this test covers BLOCKED")

    assert status["status"] == "BLOCKED"
    assert status["enabled"] is False
    assert "no prospective validation is claimed" in status["note"]
    for name, record in status["assessment"]["horizons"].items():
        assert record["ready"] is False, name
        assert record["qualifying_snapshots"] == [], name

    page = client.get("/prospective")
    assert page.status_code == 200
    assert "BLOCKED" in page.text
    assert "Prospective evaluation is disabled" in page.text
    # The scoring control must be disabled, not merely hidden.
    assert "btn disabled" in page.text and "disabled" in page.text
    assert "nothing has been scored" in _flat(page.text)
    # The protocol must be visible before any outcome is seen.
    assert "Fixed evaluation protocol" in page.text


def test_17b_overview_reports_the_prospective_blocker(client: TestClient) -> None:
    overview = client.get("/api/overview").json()
    if overview["prospective"] == "READY":
        pytest.skip("prospective evaluation is no longer blocked")
    assert any(finding["level"] == "BLOCKED" for finding in overview["findings"])


# ------------------------------------------------------------- store-level checks
@needs_snapshot
def test_store_never_substitutes_a_value_for_a_missing_one() -> None:
    store = ArtifactStore(ROOT)
    table = pd.read_csv(SNAPSHOT, usecols=["norad", "mass"])
    without_mass = table[table["mass"].isna()]
    if without_mass.empty:
        pytest.skip("every object has a catalogued mass")

    record = store.object_record(int(without_mass.iloc[0]["norad"]))
    # A missing mass must be None, never 0.0.
    assert record["physical"]["mass_kg"] is None
