"""Build a read-only HTML evidence dashboard from existing COSMOS-AI artifacts.

The dashboard never synthesizes predictions. Missing artifacts are shown as unavailable,
and individual trajectories/timelines are not drawn unless those records are present.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _table_section(
    root: Path,
    title: str,
    relative_path: str,
    columns: tuple[str, ...],
    note: str,
    limit: int = 30,
) -> str:
    source = root / relative_path
    heading = f"<h2>{html.escape(title)}</h2><p>{html.escape(note)}</p>"
    if not source.is_file():
        return heading + f"<p class='unavailable'>Artifact unavailable: {html.escape(relative_path)}</p>"
    table = pd.read_csv(source)
    missing = set(columns) - set(table.columns)
    if missing:
        raise ValueError(f"{relative_path} is missing required columns: {sorted(missing)}")
    shown = table.loc[:, columns].head(limit).copy()
    shown = shown.astype(object).where(pd.notna(shown), "")
    return heading + f"<p>Source: <code>{html.escape(relative_path)}</code>; showing {len(shown)} rows.</p>" + shown.to_html(
        index=False, escape=True, classes="data"
    )


def _model_registry(root: Path) -> str:
    title = "<h2>Model status and evidence</h2>"
    path = root / "outputs/registry/model_cards.json"
    if not path.is_file():
        return title + "<p class='unavailable'>Model registry is unavailable.</p>"
    cards = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for card in cards:
        checkpoint = card.get("checkpoint")
        checkpoint_exists = bool(checkpoint and Path(checkpoint).is_file())
        rows.append({
            "model": card.get("name", ""),
            "feature": card.get("feature", ""),
            "status": card.get("status", ""),
            "evidence": card.get("evidence", ""),
            "checkpoint": "present" if checkpoint_exists else ("not recorded" if not checkpoint else "missing"),
        })
    table = pd.DataFrame(rows)
    return title + "<p>Registry status is not a claim of independent validation.</p>" + table.to_html(
        index=False, escape=True, classes="data"
    )


def _forecast_sections(root: Path) -> str:
    title = "<h2>Dated twin forecasts</h2>"
    relative = "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"
    path = root / relative
    if not path.is_file():
        return title + f"<p class='unavailable'>Artifact unavailable: {html.escape(relative)}</p>"
    table = pd.read_csv(path)
    required = {
        "norad", "Name", "type1", "regime", "perigee", "apogee", "inc", "p_30d", "p_90d",
        "p_1yr", "median_days", "lo90_days", "hi90_days", "p_physics_prior_30d",
        "p_physics_history_30d", "p_lifetime_30d",
    }
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"{relative} is missing required columns: {sorted(missing)}")
    ranked = table.sort_values("p_30d", ascending=False, na_position="last").head(50)
    columns = (
        "norad", "Name", "type1", "regime", "perigee", "apogee", "inc", "p_30d", "p_90d",
        "p_1yr", "median_days", "lo90_days", "hi90_days",
    )
    display = ranked.loc[:, columns].astype(object).where(pd.notna(ranked.loc[:, columns]), "")
    comparison_cols = (
        "norad", "Name", "regime", "p_physics_prior_30d", "p_physics_history_30d",
        "p_lifetime_30d", "p_30d",
    )
    comparison = ranked.loc[:, comparison_cols].astype(object).where(
        pd.notna(ranked.loc[:, comparison_cols]), ""
    )
    text = (
        "<p>Source: <code>" + html.escape(relative) + "</code>. "
        "Forecast is dated 2026-10-27 and has not been verified against a later snapshot. "
        "The table is a ranking of this saved forecast, not an operational alert.</p>"
        "<h3>Highest saved 30-day probabilities</h3>"
        + display.to_html(index=False, escape=True, classes="data")
        + "<h3>Same-object model comparison (30 days)</h3>"
        + comparison.to_html(index=False, escape=True, classes="data")
    )
    digest_file = root / "outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt"
    if digest_file.is_file():
        digest_text = html.escape(digest_file.read_text(encoding="utf-8").strip())
        text += f"<p>Saved forecast digest record: <code>{digest_text}</code></p>"
    return title + text


#: Where `scripts/run_pipeline.py` writes its versioned run directories.
PIPELINE_RUNS = "outputs/pipeline"


def latest_run(root: Path) -> Path | None:
    """Most recent complete pipeline run directory, or None when there is no run.

    A directory counts only when it holds a `run_manifest.json`: a run that was interrupted
    before writing its manifest is incomplete and is not shown as if it had finished.
    """
    base = root / PIPELINE_RUNS
    if not base.is_dir():
        return None
    runs = sorted(
        (path for path in base.iterdir()
         if path.is_dir() and (path / "run_manifest.json").is_file()),
        key=lambda path: path.name,
    )
    return runs[-1] if runs else None


def _escalation_html(record: dict) -> str:
    status = html.escape(str(record.get("status", "")))
    reason = html.escape(str(record.get("reason", "")))
    label = "abstained" if status == "abstain" else status
    return (f"<p><strong>Cross-domain escalation (C4):</strong> {label}."
            f"<br><em>Reason recorded by the pipeline:</em> {reason}</p>")


def _pipeline_run_section(root: Path, run_dir: Path | None = None) -> str:
    """Render one versioned pipeline run: provenance, module status and abstentions.

    Exactly one run is rendered. Outputs from different runs are never combined, and a run
    whose modules disagree about the snapshot date is reported as inconsistent instead of
    being displayed as a single coherent result.
    """
    title = "<h2>Pipeline run (orchestrated modules)</h2>"
    run = run_dir if run_dir is not None else latest_run(root)
    if run is None:
        return (title + "<p class='unavailable'>No pipeline run is present. Generate one with "
                "<code>python scripts/run_pipeline.py --as-of 2026-10-27</code>.</p>")

    manifest_path = run / "run_manifest.json"
    if not manifest_path.is_file():
        return (title + "<p class='unavailable'>Run directory "
                f"<code>{html.escape(run.name)}</code> has no run_manifest.json; the run is "
                "incomplete and is not displayed.</p>")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    modules = manifest.get("modules", {})
    as_of_dates = sorted({
        record["provenance"]["as_of"]
        for record in modules.values()
        if isinstance(record.get("provenance"), dict) and record["provenance"].get("as_of")
    })
    git = manifest.get("git", {}) or {}
    dirty = git.get("tracked_worktree_dirty")

    header = (
        "<table class='data'>"
        f"<tr><th>Run ID</th><td><code>{html.escape(run.name)}</code></td></tr>"
        f"<tr><th>Started (UTC)</th><td>{html.escape(str(manifest.get('started_at', '')))}</td></tr>"
        f"<tr><th>Snapshot (as-of)</th><td>{html.escape(str(manifest.get('as_of', '')))}</td></tr>"
        f"<tr><th>Config SHA-256</th><td><code>{html.escape(str(manifest.get('config_sha256', '')))}</code></td></tr>"
        f"<tr><th>Git commit</th><td><code>{html.escape(str(git.get('git_commit')))}</code></td></tr>"
        f"<tr><th>Tracked worktree</th><td>{'modified (results may not match the commit)' if dirty else 'clean'}</td></tr>"
        f"<tr><th>Completed successfully</th><td>{'yes' if manifest.get('successful') else 'no'}</td></tr>"
        "</table>"
    )

    if len(as_of_dates) > 1:
        header += ("<p class='unavailable'><strong>Inconsistent snapshots:</strong> modules in "
                   f"this run report different as-of dates ({html.escape(', '.join(as_of_dates))}). "
                   "The run is not a single coherent snapshot and must not be read as one.</p>")

    rows = []
    for name, record in modules.items():
        provenance = record.get("provenance") or {}
        sources = ", ".join(provenance.get("input_sources", []) or [])
        detail = record.get("error") or record.get("reason") or ""
        rows.append({
            "module": name,
            "status": record.get("status", ""),
            "as_of": provenance.get("as_of", ""),
            "duration_s": (round(record["duration_s"], 2)
                           if isinstance(record.get("duration_s"), (int, float)) else ""),
            "abstained": record.get("abstained_total", ""),
            "inputs": sources,
            "detail": detail,
        })
    status_table = pd.DataFrame(rows).to_html(index=False, escape=True, classes="data")

    blocks = [title, header,
              "<h3>Module execution status</h3>"
              "<p>A failed module writes no output, and its dependants are reported as "
              "blocked rather than completed with substituted values.</p>" + status_table]

    # ---- abstentions, with the reason the pipeline recorded
    abstention_blocks = []
    for name, record in modules.items():
        grouped = record.get("abstentions")
        if not grouped:
            continue
        items = "".join(
            f"<li>{count} object(s): {html.escape(reason)}</li>"
            for reason, count in grouped.items()
        )
        abstention_blocks.append(f"<p><strong>{html.escape(name)}</strong></p><ul>{items}</ul>")
    if abstention_blocks:
        blocks.append("<h3>Abstentions and reasons</h3>"
                      "<p>An abstention means no value was produced for that object. Nothing "
                      "is imputed in its place.</p>" + "".join(abstention_blocks))

    # ---- lifetime coherence status (limitation L17)
    lifetime = modules.get("lifetime", {})
    noncoherent = lifetime.get("noncoherent_horizon_probabilities")
    if lifetime.get("status") == "success":
        coherence = ("<h3>Lifetime prediction coherence</h3>"
                     "<p>Rows reaching <code>lifetime_estimates.csv</code> are monotone across "
                     "horizons. The saved per-horizon <em>calibrated</em> columns "
                     "<code>p_lifetime_30d/90d/1yr</code> are produced by an independent isotonic "
                     "calibrator per horizon and are <strong>not</strong> guaranteed to form a "
                     "coherent CDF (limitation L17); the twin's final reported "
                     "<code>p_*</code> forecast is unaffected.</p>")
        if isinstance(noncoherent, int):
            detail = (f"{noncoherent} object(s) in this run were excluded for exactly this "
                      "reason and are listed in "
                      "<code>lifetime_noncoherent_horizons.csv</code>."
                      if noncoherent else
                      "No object in this run showed a cross-horizon violation.")
            coherence += f"<p>{detail}</p>"
        blocks.append(coherence)

    # ---- physical probability vs operational priority, kept apart
    collision = modules.get("collision", {})
    if collision.get("status") == "success":
        blocks.append(
            "<h3>Collision risk and operational priority</h3>"
            "<p><code>collision_risk.csv</code> holds the <strong>physical</strong> collision "
            "probability of each anonymised CAC event with a 0.05-0.95 interval; its "
            "<code>priority_score</code> is deliberately empty. Operational ordering lives only "
            "in <code>decision_ranking.csv</code> and never alters a physical probability.</p>")
    decision = modules.get("decision_priority", {})
    if isinstance(decision.get("health_escalation"), dict):
        blocks.append(_escalation_html(decision["health_escalation"]))

    # ---- re-entry evidence status
    reentry = modules.get("reentry", {})
    if reentry.get("status") == "success":
        blocks.append(
            "<h3>Re-entry evidence status</h3>"
            "<p>Intervals are physics Monte-Carlo quantiles over area-to-mass and space-weather "
            "draws. They are <strong>not</strong> conformal intervals and carry no "
            "distribution-free coverage guarantee. This run re-expresses a saved forecast; it is "
            "not a later-snapshot validation.</p>")

    # ---- tables actually written by this run
    tables = manifest.get("tables_written") or []
    if tables:
        links = "".join(
            f"<li><code>{html.escape(name)}</code>"
            + (f" ({len(pd.read_csv(run / name))} rows)" if (run / name).is_file() else " (absent)")
            + "</li>"
            for name in tables
        )
        blocks.append(f"<h3>Tables written by this run</h3><ul>{links}</ul>")

    not_established = (manifest.get("interpretation") or {}).get("not_established") or []
    if not_established:
        items = "".join(f"<li>{html.escape(str(entry))}</li>" for entry in not_established)
        blocks.append(f"<h3>What this run does not establish</h3><ul>{items}</ul>")

    return "".join(blocks)


def _json_section(root: Path, title: str, relative_path: str, note: str) -> str:
    heading = f"<h2>{html.escape(title)}</h2><p>{html.escape(note)}</p>"
    path = root / relative_path
    if not path.is_file():
        return heading + f"<p class='unavailable'>Artifact unavailable: {html.escape(relative_path)}</p>"
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{relative_path} must contain a JSON object")
    return heading + f"<p>Source: <code>{html.escape(relative_path)}</code></p><pre>{html.escape(json.dumps(data, indent=2, default=str))}</pre>"


def render_dashboard(root: str | Path, output: str | Path, overwrite: bool = False,
                     run_dir: str | Path | None = None) -> Path:
    """Render a static evidence dashboard using only artifacts already present under root.

    ``run_dir`` selects which pipeline run to display; the most recent complete run is used
    by default. Only one run is ever rendered, so outputs of different runs cannot be mixed.
    """
    project = Path(root).resolve()
    target = Path(output).resolve()
    selected_run = Path(run_dir).resolve() if run_dir is not None else None
    if target.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing dashboard: {target}")
    if not project.is_dir():
        raise NotADirectoryError(project)
    target.parent.mkdir(parents=True, exist_ok=True)

    sections = [
        _pipeline_run_section(project, selected_run),
        _model_registry(project),
        _table_section(
            project, "Satellite health benchmark", "outputs/benchmarks/telemetry_esa_adb/results.csv",
            ("mission", "encoder", "calibrator", "seed", "anomaly_and_rare/EW_F0.5",
             "alarm_runs", "false_alarm_runs", "false_alarms_per_year"),
            "Benchmark alarm metrics from saved ESA-ADB runs. Per-time anomaly traces are not present "
            "in this artifact, so no timeline is fabricated.",
        ),
        _table_section(
            project, "Debris detection benchmark", "outputs/benchmarks/vision_spotgeo/summary.csv",
            ("model", "inputs", "train_frac", "test_f1|mean", "test_precision|mean",
             "test_recall|mean", "n_seeds"),
            "SpotGEO benchmark summaries. Individual detector-coordinate outputs are not available "
            "here; synthetic results are not mixed into this real-benchmark table.",
        ),
        _forecast_sections(project),
        _table_section(
            project, "Collision-risk benchmark", "outputs/benchmarks/conjunction_kelvins_cac/test_results.csv",
            ("model", "L_clip", "precision_clip", "recall_clip", "auc_pr_high", "brier_high", "cov90"),
            "CAC event-level benchmark metrics. These are anonymised events, not linked spacecraft "
            "or a live collision-probability feed.",
        ),
        _table_section(
            project, "Breakup-cloud survival outputs", "outputs/twin/as_of_2026-10-27/c2_clouds.csv",
            ("breakup_parent", "fragments_in_orbit", "expected_remaining_30d",
             "expected_remaining_90d", "expected_remaining_1yr"),
            "Saved population forecasts, not later-snapshot validation. No covariance or independent "
            "cloud uncertainty is implied by expected counts alone.",
        ),
        _json_section(
            project, "Dated forecast summary", "outputs/twin/as_of_2026-10-27/summary.json",
            "Actual saved twin summary. Validation and exposure caveats remain in the audit documents.",
        ),
        "<h2>Unavailable views</h2><ul>"
        "<li>Re-entry ground-track/impact map: no validated trajectory or impact-coordinate data "
        "are present in the dated twin forecast.</li>"
        "<li>Identity-linked telemetry timeline: saved benchmark outputs contain aggregate alarm "
        "metrics, not a joined per-object telemetry timeline.</li>"
        "<li>Cross-domain health-to-collision scenario: C4 is a demonstration only because current "
        "health and CDM data cannot be linked to the same object.</li>"
        "</ul>",
    ]
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>COSMOS-AI evidence dashboard</title>
<style>
body{font:15px system-ui,sans-serif;max-width:1400px;margin:2rem auto;padding:0 1rem;color:#1c2633}
h1,h2{color:#14395b}h2{border-top:1px solid #ccd5de;padding-top:1.2rem;margin-top:2rem}
.banner{background:#fff4d6;padding:1rem;border-left:5px solid #c08000}
.unavailable{color:#8b2d2d}.data{border-collapse:collapse;width:100%;font-size:13px}
.data th,.data td{border:1px solid #d5dce3;padding:.35rem;text-align:left}
.data th{background:#edf2f7;position:sticky;top:0}pre{white-space:pre-wrap;background:#f4f6f8;padding:1rem}
code{overflow-wrap:anywhere}
</style></head><body>
<h1>COSMOS-AI evidence dashboard</h1>
<p class="banner"><strong>Evidence boundary:</strong> this page reads saved artifacts only. It does not
run models, join unpaired datasets, or generate missing predictions. Benchmark evidence is not
independent operational validation. The dated forecast has not been scored against a later snapshot.</p>
""" + "\n".join(sections) + "</body></html>"
    target.write_text(page, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--output", default="outputs/dashboard/index.html")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--run", default=None,
                        help="pipeline run directory to display (default: most recent complete run)")
    args = parser.parse_args(argv)
    output = render_dashboard(args.root, args.output, overwrite=args.overwrite,
                             run_dir=args.run)
    print(f"Dashboard written from saved artifacts: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
