"""Dashboard rendering must only show supplied artifacts and must not overwrite by default."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cosmos.ai.dashboard import render_dashboard


def test_dashboard_renders_artifacts_and_explicit_unavailable_sections(tmp_path: Path) -> None:
    cards = tmp_path / "outputs/registry/model_cards.json"
    cards.parent.mkdir(parents=True)
    cards.write_text(json.dumps([{
        "name": "fixture-model", "feature": "health", "status": "validated-synthetic",
        "evidence": "fixture.csv", "checkpoint": None,
    }]))
    results = tmp_path / "outputs/benchmarks/telemetry_esa_adb/results.csv"
    results.parent.mkdir(parents=True)
    pd.DataFrame([{
        "mission": 1, "encoder": "fixture", "calibrator": "threshold", "seed": 0,
        "anomaly_and_rare/EW_F0.5": 0.25, "alarm_runs": 2, "false_alarm_runs": 1,
        "false_alarms_per_year": 3.0,
    }]).to_csv(results, index=False)
    output = tmp_path / "dashboard/index.html"

    result = render_dashboard(tmp_path, output)

    page = result.read_text()
    assert "fixture-model" in page
    assert "0.25" in page
    assert "Re-entry ground-track/impact map" in page
    assert "not available" in page.lower() or "unavailable" in page.lower()


def test_dashboard_refuses_overwrite_without_explicit_opt_in(tmp_path: Path) -> None:
    output = tmp_path / "index.html"
    output.write_text("keep")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        render_dashboard(tmp_path, output)
    assert output.read_text() == "keep"


# ------------------------------------------------- versioned pipeline run rendering
def _write_run(root: Path, run_id: str, modules: dict, *, successful: bool = True,
               as_of: str = "2026-10-27", manifest: bool = True,
               tables: list[str] | None = None) -> Path:
    """Build a minimal pipeline run directory of the shape run_pipeline.py writes."""
    run_dir = root / "outputs/pipeline" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if not manifest:
        return run_dir
    record = {
        "as_of": as_of,
        "started_at": f"{as_of}T00:00:00+00:00",
        "config_sha256": "c" * 64,
        "successful": successful,
        "git": {"git_commit": "a" * 40, "tracked_worktree_dirty": False},
        "tables_written": tables or [],
        "modules": modules,
        "interpretation": {"not_established": ["fixture run establishes nothing scientific"]},
    }
    (run_dir / "run_manifest.json").write_text(json.dumps(record))
    return run_dir


def _module(status: str, as_of: str = "2026-10-27", **extra) -> dict:
    record = {"status": status, "reason": "", "error": "", "duration_s": 0.1,
              "outputs": {}, "provenance": {"as_of": as_of, "input_sources": ["fixture"]}}
    record.update(extra)
    return record


def _render(tmp_path: Path, name: str = "index.html", **kwargs) -> str:
    return render_dashboard(tmp_path, tmp_path / "dash" / name, **kwargs).read_text()


def test_dashboard_reports_a_fully_successful_run(tmp_path: Path) -> None:
    _write_run(tmp_path, "run_20261104T000000Z", {
        "catalogue_state": _module("success"),
        "lifetime": _module("success"),
        "reentry": _module("success"),
        "collision": _module("success"),
        "decision_priority": _module("success"),
    }, tables=["decision_ranking.csv"])

    page = _render(tmp_path)

    assert "run_20261104T000000Z" in page
    assert "Completed successfully" in page
    assert "a" * 40 in page           # git commit provenance
    assert "c" * 64 in page           # configuration digest
    assert "2026-10-27" in page       # snapshot identifier
    # Physical probability and operational priority must be described separately.
    assert "physical" in page.lower() and "priority" in page.lower()
    assert "fixture run establishes nothing scientific" in page


def test_dashboard_shows_no_run_when_none_exists(tmp_path: Path) -> None:
    page = _render(tmp_path)
    assert "No pipeline run is present" in page
    assert "run_pipeline.py" in page


def test_dashboard_reports_an_incomplete_run_without_displaying_it(tmp_path: Path) -> None:
    """A run directory with no manifest is incomplete and must not look finished."""
    _write_run(tmp_path, "run_20261104T000000Z", {}, manifest=False)

    page = _render(tmp_path)

    # With no manifest the run is not selectable at all, so the section reports no run.
    assert "No pipeline run is present" in page
    assert "Completed successfully" not in page


def test_dashboard_reports_failed_and_blocked_modules(tmp_path: Path) -> None:
    """A required input being unavailable must surface as failure plus blocked dependants."""
    _write_run(tmp_path, "run_20261104T000000Z", {
        "catalogue_state": _module(
            "failed",
            error="ArtifactUnavailable: required artifact is not present: forecast_table.csv.gz",
        ),
        "lifetime": _module("blocked", reason="dependencies did not succeed: catalogue_state"),
        "debris": _module("success"),
    }, successful=False)

    page = _render(tmp_path)

    assert "failed" in page
    assert "ArtifactUnavailable" in page
    assert "blocked" in page
    assert "dependencies did not succeed: catalogue_state" in page
    assert "Completed successfully" in page and ">no<" in page


def test_dashboard_reports_an_optional_module_that_was_not_requested(tmp_path: Path) -> None:
    _write_run(tmp_path, "run_20261104T000000Z", {
        "catalogue_state": _module("success"),
        "debris": {"status": "not_requested", "reason": "", "error": "", "outputs": {}},
    })

    page = _render(tmp_path)

    assert "not_requested" in page
    # An unrequested optional module must not be presented as a failure of the run.
    assert "Completed successfully" in page


def test_dashboard_shows_abstentions_with_their_recorded_reasons(tmp_path: Path) -> None:
    _write_run(tmp_path, "run_20261104T000000Z", {
        "lifetime": _module(
            "success",
            abstained_total=463,
            abstentions={
                "saved lifetime expert produced no value for this object": 461,
                "saved per-horizon calibrated probabilities are not monotone across horizons": 2,
            },
            noncoherent_horizon_probabilities=2,
        ),
        "decision_priority": _module("success", health_escalation={
            "status": "abstain",
            "reason": "health evidence is present but not identity-linked to these objects",
        }),
    })

    page = _render(tmp_path)

    assert "Abstentions and reasons" in page
    assert "461 object(s)" in page
    assert "not monotone across horizons" in page
    assert "Nothing is imputed in its place" in page
    # C4 abstention and its reason must both be visible.
    assert "abstained" in page
    assert "not identity-linked" in page
    # L17 must be stated, including that the final forecast is unaffected.
    assert "L17" in page
    assert "lifetime_noncoherent_horizons.csv" in page


def test_dashboard_flags_a_run_mixing_different_snapshots(tmp_path: Path) -> None:
    """Modules disagreeing on the as-of date must be reported, not silently combined."""
    _write_run(tmp_path, "run_20261104T000000Z", {
        "catalogue_state": _module("success", as_of="2026-10-27"),
        "lifetime": _module("success", as_of="2026-08-16"),
    })

    page = _render(tmp_path)

    assert "Inconsistent snapshots" in page
    assert "2026-08-16" in page and "2026-10-27" in page
    assert "must not be read as one" in page


def test_dashboard_renders_only_one_run_and_prefers_the_latest(tmp_path: Path) -> None:
    """Outputs of different runs must never be combined into one view."""
    _write_run(tmp_path, "run_20261101T000000Z",
               {"catalogue_state": _module("success")}, tables=["older_table.csv"])
    _write_run(tmp_path, "run_20261104T000000Z",
               {"catalogue_state": _module("success")}, tables=["newer_table.csv"])

    page = _render(tmp_path)

    assert "run_20261104T000000Z" in page
    assert "run_20261101T000000Z" not in page
    assert "newer_table.csv" in page
    assert "older_table.csv" not in page


def test_dashboard_can_render_an_explicitly_selected_older_run(tmp_path: Path) -> None:
    older = _write_run(tmp_path, "run_20261101T000000Z",
                       {"catalogue_state": _module("success")}, tables=["older_table.csv"])
    _write_run(tmp_path, "run_20261104T000000Z", {"catalogue_state": _module("success")})

    page = _render(tmp_path, run_dir=older)

    assert "run_20261101T000000Z" in page
    assert "run_20261104T000000Z" not in page


def test_dashboard_marks_a_dirty_worktree_as_possibly_mismatched(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "run_20261104T000000Z",
                         {"catalogue_state": _module("success")})
    manifest = json.loads((run_dir / "run_manifest.json").read_text())
    manifest["git"]["tracked_worktree_dirty"] = True
    (run_dir / "run_manifest.json").write_text(json.dumps(manifest))

    page = _render(tmp_path)

    assert "may not match the commit" in page
