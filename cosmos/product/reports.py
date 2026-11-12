"""Assessment report generation.

A report is a traceable snapshot of what the system actually holds about one object. It
separates three classes of content, and never lets one stand in for another:

``computed``     produced by a pipeline run that this report names
``historical``   read from a saved artifact that predates this report
``unsupported``  not available for this object, with the reason stated

Every report carries the run ID, Git commit, artifact digests, snapshot date, uncertainty
description, abstentions and limitations, so a number in a report can be traced back to the
file it came from.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..ai.provenance import ROOT
from .store import ArtifactStore, DataUnavailable

#: Limitations that apply to every assessment this product can produce.
STANDING_LIMITATIONS = (
    "No dataset in this repository links telemetry health, conjunction messages and "
    "catalogue outcomes for the same spacecraft, so no end-to-end health-to-re-entry chain "
    "is empirically validated (limitation L1).",
    "Re-entry intervals are physics Monte-Carlo quantiles over area-to-mass and space-weather "
    "draws. They are not conformal intervals and carry no distribution-free coverage "
    "guarantee (limitation L8).",
    "The existing as-of 2026-08-16 temporal evaluation (T1) is not blind and is exploratory "
    "evidence, not confirmatory (limitations L2, L3).",
    "Prospective evaluation of the dated 2026-10-27 forecast is blocked: no qualifying later "
    "outcome snapshot exists (limitation L3b).",
    "The saved per-horizon calibrated lifetime probabilities are calibrated independently per "
    "horizon and are not guaranteed to form a coherent CDF (limitation L17). The twin's final "
    "reported forecast is unaffected.",
    "No validated impact coordinate, ground track, footprint or recovered-fragment location "
    "is available for any object (limitation L5).",
    "Software tests passing is not scientific validation.",
)


def object_report(store: ArtifactStore, norad: int,
                  run_id: str | None = None) -> dict[str, Any]:
    """Build an assessment report for one catalogue object."""
    record = store.object_record(norad)
    generated_at = datetime.now(timezone.utc).isoformat()
    repository = store.repository_provenance()

    run_context: dict[str, Any] = {"run_id": None, "state": "none",
                                   "detail": "no pipeline run was referenced by this report"}
    computed: list[dict[str, Any]] = []
    resolved_run = run_id or store.latest_run_id()
    if resolved_run:
        try:
            manifest = store.run_manifest(resolved_run)
        except DataUnavailable as exc:
            run_context = {"run_id": resolved_run, "state": "unavailable",
                           "detail": exc.message}
        else:
            run_context = {
                "run_id": resolved_run,
                "state": "loaded",
                "started_at": manifest.get("started_at"),
                "as_of": manifest.get("as_of"),
                "config_sha256": manifest.get("config_sha256"),
                "git_commit": (manifest.get("git") or {}).get("git_commit"),
                "tracked_worktree_dirty": (manifest.get("git") or {}).get(
                    "tracked_worktree_dirty"),
                "successful": manifest.get("successful"),
                "requested": manifest.get("requested"),
                "tables_written": manifest.get("tables_written"),
                "explicitly_requested": bool(run_id),
                "detail": ("the run named in the request" if run_id else
                           "the most recent complete run, selected automatically"),
            }
            if manifest.get("as_of") != record["as_of"]:
                run_context["snapshot_mismatch"] = (
                    f"run snapshot {manifest.get('as_of')} differs from the object snapshot "
                    f"{record['as_of']}; outputs of the two are not combined in this report")
            computed = _computed_rows(store, resolved_run, norad, manifest)

    historical = _historical_rows(record)
    unsupported = _unsupported_rows(record)
    abstentions = _abstentions(record, computed)

    return {
        "report_type": "object_assessment",
        "schema_version": "1.1",
        "freshness": record["freshness"],
        "generated_at": generated_at,
        "subject": {
            "kind": "catalogue_object",
            "norad": record["norad"],
            "name": record["name"],
            "object_class": record["object_class"],
            "object_class_label": record["object_class_label"],
            "operational_status": record["operational_status"],
            "regime": record["regime"],
            "launch_tag": record["launch_tag"],
        },
        "inputs": {
            "snapshot_as_of": record["as_of"],
            "catalogue_artifact": record["provenance"]["artifact"],
            "catalogue_sha256": record["provenance"]["sha256"],
            "catalogue_objects": record["provenance"]["objects"],
            "sources": record["provenance"]["sources"],
            "space_weather": record["space_weather"],
        },
        "provenance": {
            "git_commit": repository.get("git_commit") or "unavailable",
            "tracked_worktree_dirty": repository.get("tracked_worktree_dirty"),
            "dated_forecast_digest_state": repository.get("dated_forecast_digest_state"),
            "repository": str(ROOT),
            "run": run_context,
            "model_version": record["provenance"]["model_version"],
            "lineage_note": ("code version = Git commit; configuration version = run configuration SHA-256; "
                             "data artifact version = catalogue SHA-256 above; model version = unavailable "
                             "(no fitted model is persisted); these are distinct and none is inferred from another"),
        },
        "orbital_elements": record["elements"],
        "physical": record["physical"],
        "lifetime": record["lifetime"],
        "reentry": record["reentry"],
        "horizon_relation": {"decision_horizon_days": 30.0, "reentry": record["reentry"]["horizon_relation"],
                             "lifetime": record["lifetime"]["horizon_relation"]},
        "twin_state": {k: v for k, v in record["twin_state"].items() if k != "record"} | {
            "outputs": [{"module": o["module"], "model": o["model"], "validation": o["validation"], "abstain": o["abstain"],
                         "reason": o["reason"], "values": o["values"], "provenance": o.get("provenance")}
                        for o in (record["twin_state"]["record"] or {}).get("outputs", [])]},
        "decision_priority": record["decision_priority"],
        "evidence_availability": record["evidence_availability"],
        "computed_outputs": computed,
        "historical_outputs": historical,
        "unsupported_assessments": unsupported,
        "abstentions": abstentions,
        "uncertainty": {
            "lifetime": ("5-95 % Mondrian conformalised quantile interval where available; "
                         "capped at the study horizon; " + _subgroup_sentence(record["lifetime"]["subgroup_coverage"])),
            "reentry": record["reentry"]["uncertainty_note"],
            "collision": "not applicable: no conjunction evidence is linkable to this object",
            "health": "not applicable: no telemetry exists for this object",
        },
        "limitations": list(STANDING_LIMITATIONS) + _subgroup_limitations(record["lifetime"]["subgroup_coverage"]),
        "interpretation": {
            "scope": ("evidence summary assembled from saved COSMOS-AI artifacts for one "
                      "catalogue object"),
            "not_established": [
                "this report is not a validated operational assessment",
                "this report is not real-time: it describes a dated catalogue snapshot",
                "no live satellite tracking feed is connected to this system",
                "no validated collision-avoidance or impact-location capability is claimed",
                "the four cross-domain couplings have no demonstrated scientific benefit "
                "without ablation evidence, which this report does not contain",
            ],
        },
    }


def redact(document: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Remove environment-specific details from an exported report; keep every scientific lineage field.

    Redacted: the absolute repository path (wherever a string contains it) and the machine hostname.
    Preserved untouched: artifact SHA-256 digests, git commit, configuration digests, run ids, timestamps,
    every value. The document records that redaction was applied and which fields were touched.
    """
    import copy
    import socket
    root_str = str(Path(root or ROOT).resolve())
    host = socket.gethostname()
    doc = copy.deepcopy(document)
    touched: list[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            return {k: walk(v, f"{path}.{k}" if path else k) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v, f"{path}[]") for v in node]
        if isinstance(node, str):
            out = node
            if root_str and root_str in out:
                out = out.replace(root_str, "<repository root (redacted)>")
                touched.append(path)
            if host and host in out:
                out = out.replace(host, "<host (redacted)>")
                touched.append(path)
            return out
        return node

    doc = walk(doc)
    doc["redaction"] = {"applied": True, "redacted_fields": sorted(set(touched)),
                        "preserved": ["artifact SHA-256 digests", "git commit", "configuration digests", "run ids",
                                      "timestamps", "all scientific values"],
                        "note": "environment-specific details were removed for export; scientific lineage is unchanged"}
    return doc


def _subgroup_sentence(cue: dict[str, Any]) -> str:
    """One sentence on the observed subgroup coverage (X6 Stage 1), descriptive only."""
    if not cue.get("available"):
        return f"subgroup coverage evidence: {cue.get('reason')}"
    parts = [f"origin {o}, {lv} %: {v['coverage']:.4f} (95 % CI {v['ci95'][0]:.3f}-{v['ci95'][1]:.3f}, n = {v['n']}) against nominal {v['nominal']:.2f}"
             for o, levels in cue["observed"].items() for lv, v in levels.items()]
    return (f"observed coverage for {cue['am_source']} objects in the archived evaluations — " + "; ".join(parts)
            + f". {cue['not_individual']}; {cue['scope']}")


def _subgroup_limitations(cue: dict[str, Any]) -> list[str]:
    if cue.get("under_coverage_flag"):
        v = cue["observed"].get("2016", {}).get("80")
        return [("subgroup under-coverage (descriptive, X6 Stage 1): this object's area-to-mass value is design-derived; "
                 f"at the archived evaluation origin 2016 the 80 % intervals of this construction covered "
                 f"{v['coverage']:.4f} (95 % CI {v['ci95'][0]:.3f}-{v['ci95'][1]:.3f}) of design-derived objects against a nominal 0.80. "
                 "This is an observed subgroup frequency, not this object's coverage probability, not a causal explanation, "
                 "and not a statement about the deployed snapshot, which has no outcomes")] if v else [
                 "subgroup under-coverage (descriptive, X6 Stage 1): design-derived objects were under-covered at 80 % in the archived evaluations"]
    if cue.get("am_source") == "unknown":
        return ["area-to-mass source unknown for this object: it is not inferred, and no subgroup coverage evidence applies"]
    return []


def _computed_rows(store: ArtifactStore, run_id: str, norad: int,
                   manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Rows for this object in the named run's output tables."""
    object_id = f"NORAD-{norad}"
    rows: list[dict[str, Any]] = []
    for table_name, label in (("decision_ranking.csv", "decision priority"),
                              ("reentry_predictions.csv", "re-entry prediction"),
                              ("lifetime_estimates.csv", "lifetime estimate")):
        if table_name not in (manifest.get("tables_written") or []):
            continue
        try:
            table = store.run_table(run_id, table_name)
        except DataUnavailable:
            continue
        if "object_id" not in table.columns:
            continue
        matched = table[table["object_id"].astype(str).eq(object_id)]
        if matched.empty:
            rows.append({
                "source": table_name, "label": label, "present": False,
                "detail": (f"this object is not in {table_name} for run {run_id}; the run may "
                           "have been limited to a subset, or the module abstained"),
            })
            continue
        record = json.loads(matched.head(1).to_json(orient="records"))[0]
        rows.append({"source": table_name, "label": label, "present": True,
                     "run_id": run_id, "values": record})
    return rows


def _historical_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": "Dated twin re-entry forecast",
            "artifact": record["provenance"]["artifact"],
            "sha256": record["provenance"]["sha256"],
            "as_of": record["as_of"],
            "values": record["reentry"]["probability_by_horizon"],
            "model": record["reentry"]["model"],
            "evidence_status": record["reentry"]["evidence_status"],
            "note": "historical saved forecast; not recomputed for this report",
        },
        {
            "label": "Learned lifetime expert",
            "artifact": record["provenance"]["artifact"],
            "sha256": record["provenance"]["sha256"],
            "as_of": record["as_of"],
            "values": record["lifetime"]["horizon_probabilities"],
            "model": "COSMOS lifetime expert (fused learned + physics)",
            "evidence_status": (
                "horizon coherence: " + record["lifetime"]["horizon_coherence"]["status"]),
            "note": "historical saved estimate; not recomputed for this report",
        },
    ]


def _unsupported_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"assessment": "Telemetry anomaly detection for this object",
         "status": "UNSUPPORTED", "reason": record["telemetry"]["reason"]},
        {"assessment": "Collision probability for this object",
         "status": "UNSUPPORTED", "reason": record["conjunction"]["reason"]},
        {"assessment": "Health-driven conjunction escalation (coupling C4)",
         "status": "UNSUPPORTED",
         "reason": ("no dataset links telemetry health to a conjunction event or a catalogued "
                    "object, so no escalation can be computed")},
        {"assessment": "Impact location, ground track or debris footprint",
         "status": "UNSUPPORTED", "reason": record["reentry"]["impact_location_note"]},
        {"assessment": "Instantaneous position and velocity state vector",
         "status": "UNSUPPORTED", "reason": record["elements"]["state_vector_note"]},
        {"assessment": "Prospective (blind) validation of this forecast",
         "status": "BLOCKED",
         "reason": ("no qualifying later outcome snapshot exists; the newest catalogue "
                    "coverage predates the dated forecast")},
    ]


def _abstentions(record: dict[str, Any],
                 computed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    coherence = record["lifetime"]["horizon_coherence"]
    if coherence["status"] == "incoherent":
        found.append({
            "module": "lifetime", "status": "ABSTAIN",
            "reason": ("saved per-horizon calibrated probabilities are not monotone across "
                       "horizons, so no coherent lifetime CDF is reported for this object"),
            "detail": coherence.get("detail", ""),
        })
    elif coherence["status"] == "unavailable":
        found.append({"module": "lifetime", "status": "ABSTAIN",
                      "reason": coherence.get("detail", "no lifetime estimate for this object")})
    if record["regime"] == "operator_controlled":
        found.append({
            "module": "reentry", "status": "ABSTAIN",
            "reason": ("operator-controlled payload: drag physics does not determine its "
                       "re-entry, so a previous-window base rate is reported instead of a "
                       "drag forecast"),
        })
    for row in computed:
        if not row.get("present"):
            found.append({"module": row["label"], "status": "ABSTAIN",
                          "reason": row.get("detail", "not present in the referenced run")})
    return found


# ---------------------------------------------------------------------- rendering
def render_html(document: dict[str, Any]) -> str:
    """Self-contained, printable HTML report. No external assets, so it works offline."""
    subject = document["subject"]
    inputs = document["inputs"]
    provenance = document["provenance"]
    run = provenance["run"]

    def esc(value: Any) -> str:
        return html.escape("—" if value is None else str(value))

    def kv_table(pairs: list[tuple[str, Any]]) -> str:
        rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in pairs)
        return f"<table class='kv'>{rows}</table>"

    parts: list[str] = [f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>COSMOS-AI assessment — NORAD {esc(subject['norad'])}</title>
<style>
 body{{font:13px/1.5 "Helvetica Neue",Arial,sans-serif;color:#15202b;max-width:900px;
   margin:2rem auto;padding:0 1.5rem}}
 h1{{font-size:21px;margin-bottom:.2rem}} h2{{font-size:15px;margin-top:1.8rem;
   border-bottom:1px solid #c9d3dd;padding-bottom:.3rem;color:#1b3d5c}}
 h3{{font-size:13px;margin:1rem 0 .3rem}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0;font-size:12px}}
 th,td{{border:1px solid #d3dbe3;padding:.35rem .5rem;text-align:left;vertical-align:top}}
 th{{background:#eef3f8;font-weight:600;width:28%}}
 table.data th{{width:auto;background:#eef3f8}}
 .banner{{background:#fff6e0;border-left:4px solid #b8860b;padding:.7rem .9rem;margin:1rem 0}}
 .tag{{display:inline-block;padding:.08rem .4rem;border-radius:3px;font-size:11px;
   font-weight:600;letter-spacing:.02em}}
 .tag.hist{{background:#dfe8f2;color:#1b3d5c}} .tag.comp{{background:#d9ecdc;color:#1d5c2e}}
 .tag.unsup{{background:#f0dede;color:#7a2222}} .tag.abst{{background:#e8dff2;color:#4a2a70}}
 .tag.blocked{{background:#e2e2e2;color:#444}}
 ul{{margin:.4rem 0 .4rem 1.1rem;padding:0}} li{{margin:.2rem 0}}
 code{{font-size:11px;overflow-wrap:anywhere}} footer{{margin-top:2rem;font-size:11px;
   color:#5b6b7b;border-top:1px solid #c9d3dd;padding-top:.6rem}}
</style></head><body>
<h1>COSMOS-AI assessment report</h1>
<p><strong>{esc(subject['name'])}</strong> — NORAD {esc(subject['norad'])}
 ({esc(subject['object_class_label'])})</p>
<div class="banner"><strong>Scope.</strong> This report summarises evidence held in saved
COSMOS-AI artifacts for one catalogue object at a dated snapshot. It is
<strong>not real-time</strong>, not a validated operational assessment, and no live satellite
tracking feed is connected. Software tests passing is not scientific validation.</div>"""]

    parts.append("<h2>1. Subject and input data</h2>")
    parts.append(kv_table([
        ("NORAD ID", subject["norad"]),
        ("Name", subject["name"]),
        ("Object class", f"{subject['object_class']} — {subject['object_class_label']}"),
        ("Operational status (catalogue)", subject["operational_status"]),
        ("Re-entry regime", subject["regime"]),
        ("Launch tag", subject["launch_tag"]),
        ("Snapshot as-of", inputs["snapshot_as_of"]),
        ("Catalogue artifact", inputs["catalogue_artifact"]),
        ("Catalogue SHA-256", inputs["catalogue_sha256"]),
        ("Objects in snapshot", f"{inputs['catalogue_objects']:,}"),
        ("Sources", ", ".join(inputs["sources"])),
        ("F10.7 (81-day mean)", inputs["space_weather"].get("f107_last81")),
        ("Ap (81-day mean)", inputs["space_weather"].get("ap_last81")),
    ]))

    parts.append("<h2>2. Run and code provenance</h2>")
    parts.append(kv_table([
        ("Report generated (UTC)", document["generated_at"]),
        ("Pipeline run referenced", run.get("run_id")),
        ("Run selection", run.get("detail")),
        ("Run state", run.get("state")),
        ("Run started (UTC)", run.get("started_at")),
        ("Run snapshot as-of", run.get("as_of")),
        ("Run configuration SHA-256", run.get("config_sha256")),
        ("Run completed successfully", run.get("successful")),
        ("Git commit (code version)", provenance.get("git_commit")),
        ("Tracked worktree modified", provenance.get("tracked_worktree_dirty")),
        ("Dated forecast digest (data artifact)", provenance.get("dated_forecast_digest_state")),
        ("Model version", f"{(provenance.get('model_version') or {}).get('status', 'unavailable').upper()} — "
                          f"{(provenance.get('model_version') or {}).get('reason', 'no model version recorded')}"),
        ("Lineage note", provenance.get("lineage_note")),
    ]))
    if run.get("snapshot_mismatch"):
        parts.append(f"<div class='banner'><strong>Snapshot mismatch.</strong> "
                     f"{esc(run['snapshot_mismatch'])}</div>")

    elements = document["orbital_elements"]
    parts.append("<h2>3. Orbital elements and physical properties</h2>")
    parts.append(kv_table([
        ("Element set", elements["element_set"]),
        ("Perigee altitude (km)", elements["perigee_altitude_km"]),
        ("Apogee altitude (km)", elements["apogee_altitude_km"]),
        ("Inclination (deg)", elements["inclination_deg"]),
        ("Reference radius (km)", elements["reference_radius_km"]),
        ("State vector", elements["state_vector_note"]),
        ("Mass (kg)", document["physical"]["mass_kg"]),
        ("Radar cross-section (m²)", document["physical"]["rcs_m2"]),
        ("Area-to-mass source", document["physical"]["area_to_mass_source"]),
    ]))

    parts.append("<h2>4. Historical outputs <span class='tag hist'>HISTORICAL</span></h2>")
    for row in document["historical_outputs"]:
        parts.append(f"<h3>{esc(row['label'])}</h3>")
        values = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"
                         for k, v in (row["values"] or {}).items())
        parts.append(f"<table class='kv'>{values}"
                     f"<tr><th>Model</th><td>{esc(row['model'])}</td></tr>"
                     f"<tr><th>Evidence status</th><td>{esc(row['evidence_status'])}</td></tr>"
                     f"<tr><th>Artifact</th><td><code>{esc(row['artifact'])}</code></td></tr>"
                     f"<tr><th>Artifact SHA-256</th><td><code>{esc(row['sha256'])}</code></td></tr>"
                     f"<tr><th>Note</th><td>{esc(row['note'])}</td></tr></table>")

    parts.append("<h2>5. Computed outputs <span class='tag comp'>COMPUTED</span></h2>")
    if not document["computed_outputs"]:
        parts.append("<p>No pipeline run output was attached to this report.</p>")
    for row in document["computed_outputs"]:
        parts.append(f"<h3>{esc(row['label'])} — <code>{esc(row['source'])}</code></h3>")
        if row.get("present"):
            values = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>"
                             for k, v in row["values"].items())
            parts.append(f"<table class='kv'>{values}"
                         f"<tr><th>Run</th><td>{esc(row['run_id'])}</td></tr></table>")
        else:
            parts.append(f"<p><span class='tag abst'>NOT PRESENT</span> {esc(row['detail'])}</p>")

    parts.append("<h2>6. Uncertainty</h2>")
    parts.append(kv_table(list(document["uncertainty"].items())))
    cue = (document.get("lifetime") or {}).get("subgroup_coverage") or {}
    parts.append("<h3>Lifetime interval — subgroup coverage evidence (X6 Stage 1, descriptive)</h3>")
    rows = [("Area-to-mass source", cue.get("am_source_label")),
            ("Design-derived", cue.get("design_derived"))]
    for origin, levels in (cue.get("observed") or {}).items():
        for lv, v in levels.items():
            rows.append((f"Observed coverage, origin {origin}, {lv} % interval",
                         f"{v['coverage']:.4f} (95 % CI {v['ci95'][0]:.3f}-{v['ci95'][1]:.3f}, n = {v['n']}) vs nominal {v['nominal']:.2f}"
                         + (" — observed below nominal" if v.get("below_nominal") else "")))
    if not cue.get("available"):
        rows.append(("Status", cue.get("reason")))
    rows += [("What this is", cue.get("evidence")), ("What this is not", cue.get("not_individual")), ("Scope", cue.get("scope"))]
    parts.append(kv_table(rows))
    if cue.get("under_coverage_flag"):
        parts.append("<div class='banner'><strong>SUBGROUP UNDER-COVERAGE (observed).</strong> The interval values are "
                     "unchanged; in the archived evaluations, 80 % intervals of design-derived objects held less often "
                     "than nominal. This is a subgroup frequency, not this object's coverage probability.</div>")
    reentry = document["reentry"]
    quality = reentry.get("interval_quality") or {}
    parts.append("<h3>Re-entry time quantiles</h3>")
    parts.append(kv_table([
        ("5 % (days)", reentry["lo90_days"]),
        ("Median (days)", reentry["median_days"]),
        ("95 % (days)", reentry["hi90_days"]),
        ("Interval kind", reentry["uncertainty_kind"]),
        ("Interval meaning", quality.get("label")),
        ("Caveat", reentry["uncertainty_note"]),
    ]))
    if quality.get("kind") in {"at_cap", "degenerate"}:
        tag = "CENSORED AT CAP" if quality.get("censored_at_cap") else "ZERO-WIDTH INTERVAL"
        parts.append(f"<div class='banner'><strong>{esc(tag)}.</strong> "
                     f"{esc(quality.get('detail'))} This interval must not be read as "
                     f"precision.</div>")
    hr = document.get("horizon_relation") or {}
    parts.append("<h3>Interval versus the 30-day decision horizon (display only)</h3>")
    rows = []
    for key in ("reentry", "lifetime"):
        rel = hr.get(key) or {}
        rows.append((f"{key}: relation", f"{rel.get('label')} — {rel.get('explanation')}"))
    rows.append(("What the interval is not", (hr.get("reentry") or {}).get("not_a_probability")))
    parts.append(kv_table(rows))
    fr = document.get("freshness") or {}
    parts.append("<h3>Evidence freshness</h3>")
    so, ar, pr, st, co = (fr.get(k) or {} for k in ("source_observation", "archive", "processing", "staleness", "consistency"))
    parts.append(kv_table([
        ("Evaluated on (UTC)", fr.get("evaluated_on_utc")),
        ("Source observation: catalogue snapshot date", so.get("catalogue_snapshot_date")),
        ("Source observation: orbit canonical epoch", f"{so.get('orbit_canonical_epoch')} ({so.get('orbit_epoch_status')})"),
        ("Archive: forecast generation time", f"{ar.get('forecast_generation_time')} ({ar.get('status')}) — {ar.get('note')}"),
        ("Processing: latest run started", f"{pr.get('latest_run_started_at')} ({pr.get('status')})"),
        ("Staleness", f"{st.get('status')} — snapshot age {st.get('snapshot_age_days')} days; {st.get('rule')}"),
        ("Consistency", f"{co.get('status')}" + (": " + "; ".join(co.get("issues") or []) if co.get("issues") else "")),
        ("Live", fr.get("live")),
    ]))

    ts = document.get("twin_state") or {}
    parts.append("<h2>6a. Versioned twin state</h2>")
    if ts.get("available"):
        src_label = ("RE-EMITTED twin_state/1.1 (provenance on every output)" if ts.get("source") == "reemitted"
                     else "HISTORICAL ARCHIVE twin_state/1.0 — fallback, no provenance")
        rows = [("Source", src_label), ("Artifact", ts.get("artifact")), ("Recorded SHA-256", ts.get("artifact_recorded_sha256")),
                ("Fallback used", ts.get("fallback", {}).get("used")), ("Source record", ts.get("source_record")),
                ("Model version", f"{ts['model_version']['status'].upper()} — {ts['model_version']['reason']}")]
        if ts.get("reemission"):
            re_ = ts["reemission"]
            rows += [("Re-emission method", re_.get("method")), ("Transformation digest", re_.get("transformation_digest_sha256")),
                     ("Predictions regenerated", re_.get("predictions_regenerated")),
                     ("Equivalence with archive", re_.get("equivalence_with_archive"))]
        parts.append(kv_table(rows))
        orows = "".join(f"<tr><td>{esc(o['module'])}</td><td>{esc(o['model'])}</td><td>{esc(o['validation'])}</td>"
                        f"<td>{'ABSTAIN: ' + esc(o['reason']) if o['abstain'] else 'value'}</td>"
                        f"<td>{esc((o.get('provenance') or {}).get('config_digest', 'none')[:12]) if o.get('provenance') else 'none'}</td></tr>"
                        for o in ts.get("outputs", []))
        parts.append("<table class='data'><tr><th>Module</th><th>Model</th><th>Validation</th><th>Output</th><th>Provenance digest</th></tr>"
                     f"{orows}</table>")
    else:
        parts.append(f"<p><span class='tag unsup'>UNAVAILABLE</span> {esc(ts.get('fallback', {}).get('reason') or ts.get('malformed') or 'no twin-state record')}</p>")
    dp = document.get("decision_priority") or {}
    parts.append("<h2>6b. Decision priority (from the run manifest)</h2>")
    parts.append(kv_table([("Status", dp.get("status")), ("Run", dp.get("run_id")), ("Rank", dp.get("rank")),
                           ("Ranked objects", dp.get("ranked_objects")), ("Rule", (dp.get("rule") or {}).get("status")),
                           ("Explanation", dp.get("explanation") or dp.get("reason")),
                           ("Health escalation", (dp.get("health_escalation") or {}).get("status"))]))
    ea = document.get("evidence_availability") or []
    parts.append("<h2>6c. Evidence availability</h2>")
    erows = "".join(f"<tr><td>{esc(c['capability'])}</td><td><span class='tag'>{esc(c['status'].upper())}</span></td><td>{esc(c['detail'])}</td></tr>" for c in ea)
    parts.append(f"<table class='data'><tr><th>Capability</th><th>Status</th><th>Detail</th></tr>{erows}</table>")

    parts.append("<h2>7. Abstentions <span class='tag abst'>ABSTAIN</span></h2>")
    if not document["abstentions"]:
        parts.append("<p>No module abstained for this object.</p>")
    else:
        rows = "".join(
            f"<tr><td>{esc(a['module'])}</td><td>{esc(a['status'])}</td>"
            f"<td>{esc(a['reason'])}{(' — ' + esc(a['detail'])) if a.get('detail') else ''}</td></tr>"
            for a in document["abstentions"])
        parts.append("<table class='data'><tr><th>Module</th><th>Status</th><th>Reason</th></tr>"
                     f"{rows}</table>")

    parts.append("<h2>8. Unsupported assessments</h2>")
    rows = "".join(
        f"<tr><td>{esc(u['assessment'])}</td>"
        f"<td><span class='tag {'blocked' if u['status'] == 'BLOCKED' else 'unsup'}'>"
        f"{esc(u['status'])}</span></td><td>{esc(u['reason'])}</td></tr>"
        for u in document["unsupported_assessments"])
    parts.append("<table class='data'><tr><th>Assessment</th><th>Status</th>"
                 f"<th>Why not available</th></tr>{rows}</table>")

    if document.get("redaction", {}).get("applied"):
        parts.append(f"<div class='banner'><strong>Redacted export.</strong> {esc(document['redaction']['note'])}. "
                     f"Redacted fields: {esc(', '.join(document['redaction']['redacted_fields']) or 'none')}.</div>")
    parts.append("<h2>9. Limitations</h2><ul>")
    parts.extend(f"<li>{esc(item)}</li>" for item in document["limitations"])
    parts.append("</ul>")

    parts.append("<h2>10. What this report does not establish</h2><ul>")
    parts.extend(f"<li>{esc(item)}</li>"
                 for item in document["interpretation"]["not_established"])
    parts.append("</ul>")

    parts.append(
        f"<footer>COSMOS-AI Mission Intelligence Console · report schema "
        f"{esc(document['schema_version'])} · generated {esc(document['generated_at'])} · "
        f"run {esc(run.get('run_id'))} · commit {esc(provenance.get('git_commit'))}"
        f"</footer></body></html>")
    return "".join(parts)
