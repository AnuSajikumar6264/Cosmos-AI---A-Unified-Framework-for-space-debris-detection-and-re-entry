# Dashboard integration report

Date: 2026-11-04. The evidence dashboard now reads the versioned pipeline run directories
written by `scripts/run_pipeline.py`.

```bash
python scripts/run_pipeline.py --as-of 2026-10-27 --limit 500 --collision-limit 200 \
    --debris-sequence-limit 5 --health-calibrator conformal_bh     # exit 0
python -m cosmos.ai.dashboard --output outputs/run_phase_d/dashboard/index.html   # exit 0
python -m cosmos.ai.dashboard --run outputs/pipeline/run_20261104T053528Z --output <path>
```

Rendered from run `run_20261104T053528Z`. All data come from saved artifacts; no value is
synthesised to fill a component.

## What the dashboard exposes

| Required item | Source | Shown as |
|---|---|---|
| Run ID and timestamp | run directory name, `started_at` | header table |
| Git commit and config provenance | `git.git_commit`, `config_sha256` | header table, plus a worktree-clean indicator |
| Dataset and snapshot identifiers | `as_of`, per-module `provenance.input_sources` | header table and the module table's `as_of` / `inputs` columns |
| Module execution status | `modules[*].status` | module table (`success`, `failed`, `blocked`, `not_requested`) |
| Successful outputs | `tables_written`, with live row counts | "Tables written by this run" |
| Failed modules | `modules[*].error` | module table `detail`, with the exception text |
| Abstentions and reasons | `modules[*].abstentions` | "Abstentions and reasons", grouped by reason with counts |
| Missing inputs / optional data | `blocked` reason, `not_requested` status | module table `detail` |
| Lifetime predictions and coherence status | `noncoherent_horizon_probabilities` | "Lifetime prediction coherence", citing L17 |
| Collision probability vs operational priority | `collision_risk.csv` / `decision_ranking.csv` | "Collision risk and operational priority" |
| Re-entry outputs and evidence status | `reentry` module | "Re-entry evidence status" |
| Figures, tables, benchmark results | existing benchmark sections | unchanged registry/benchmark sections |

Example of the live rendering (run `run_20261104T053528Z`): all seven modules `success`;
`lifetime` reports **463** abstentions, split as **461** "saved lifetime expert produced no
value for this object" and **2** "per-horizon calibrated probabilities are not monotone across
horizons"; C4 escalation **abstained** with its recorded reason; the worktree is flagged as
modified, so a reader is told results may not match the named commit.

## Guarantees built in

1. **One run only.** `latest_run` picks the most recent directory that contains a
   `run_manifest.json`; `--run` selects a specific one. Outputs of two runs are never combined.
2. **Snapshot mixing is reported, not hidden.** If modules within a run disagree on
   `provenance.as_of`, the section prints "Inconsistent snapshots … must not be read as one"
   and lists the dates.
3. **An incomplete run is not displayed as finished.** A directory without a manifest is not
   selectable, so an interrupted run cannot appear complete.
4. **Failure is distinguished from absence.** `failed` carries the exception; `blocked` names
   the dependency; `not_requested` is neutral and does not mark the run unsuccessful.
5. **Abstention is distinguished from a value.** The section states "Nothing is imputed in its
   place."
6. **Physical probability is kept apart from priority.** The dashboard states that
   `collision_risk.csv`'s `priority_score` is deliberately empty and that ordering lives only
   in `decision_ranking.csv`.
7. **No overwrite by default.** `render_dashboard` raises `FileExistsError` unless
   `--overwrite` is passed.
8. **Uncertainty is not relabelled.** The re-entry section states the intervals are Monte-Carlo
   quantiles, **not** conformal, with no distribution-free coverage guarantee.

## Scenario tests

`tests/test_dashboard.py` — **12 tests, all passing**. Every scenario requested is covered.

| Scenario | Test | Asserted behaviour |
|---|---|---|
| All modules succeed | `test_dashboard_reports_a_fully_successful_run` | run ID, commit, config digest, snapshot, probability/priority separation, "does not establish" text |
| Optional module missing | `test_dashboard_reports_an_optional_module_that_was_not_requested` | `not_requested` shown; run still successful |
| Required input unavailable | `test_dashboard_reports_failed_and_blocked_modules` | `ArtifactUnavailable` surfaced, dependant `blocked` with its reason, run marked unsuccessful |
| Module abstains | `test_dashboard_shows_abstentions_with_their_recorded_reasons` | grouped counts, reasons, C4 abstention, L17 note, no imputation |
| Pipeline run incomplete | `test_dashboard_reports_an_incomplete_run_without_displaying_it` | manifest-less run not shown as complete |
| Different scientific snapshots | `test_dashboard_flags_a_run_mixing_different_snapshots` | "Inconsistent snapshots" with both dates |
| No run at all | `test_dashboard_shows_no_run_when_none_exists` | explicit absence plus the command to generate one |
| Runs not mixed | `test_dashboard_renders_only_one_run_and_prefers_the_latest` | older run's ID and tables absent |
| Explicit run selection | `test_dashboard_can_render_an_explicitly_selected_older_run` | selected run shown, newest excluded |
| Dirty worktree | `test_dashboard_marks_a_dirty_worktree_as_possibly_mismatched` | mismatch warning present |
| Artifacts only / unavailable views | `test_dashboard_renders_artifacts_and_explicit_unavailable_sections` | unavailable views labelled |
| Overwrite protection | `test_dashboard_refuses_overwrite_without_explicit_opt_in` | existing file untouched |

## Changes made

- `cosmos/ai/dashboard.py`: added `PIPELINE_RUNS`, `latest_run`, `_escalation_html` and
  `_pipeline_run_section`; `render_dashboard` gained a `run_dir` parameter; the CLI gained
  `--run`. The pipeline section is rendered first, above the registry.
- `scripts/run_pipeline.py`: the manifest now records grouped `abstentions` with
  `abstained_total`, the `health_escalation` evidence (status and reason) and the count of
  non-coherent horizon rows. Previously these were reduced to bare counts, which a reader
  could not interpret.

No existing dashboard section was removed, and no benchmark artifact was modified.

## Limits

The dashboard is a **static evidence view**, not an operational console. It renders saved
artifacts and does not run models, join unpaired datasets or generate predictions. The
"Unavailable views" section still correctly reports that there is no re-entry ground-track or
impact map, no identity-linked telemetry timeline, and no validated health-to-collision
scenario. A green dashboard is not evidence of scientific validity.

## Status

| Item | Status |
|---|---|
| Dashboard reads versioned pipeline runs | **PASS** |
| All twelve required items exposed | **PASS** |
| Six requested failure/abstention scenarios tested | **PASS** |
| Run and snapshot mixing prevented and tested | **PASS** |
| Data sourced only from real artifacts | **PASS** |
| Operational / live dashboard | **NOT IMPLEMENTED** — out of scope by design |
