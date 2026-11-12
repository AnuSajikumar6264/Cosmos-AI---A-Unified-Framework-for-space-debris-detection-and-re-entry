"""Capture the console's real rendered pages as self-contained HTML files.

Each file is the actual server response for that route, with the stylesheet inlined and
image/API references rewritten to absolute URLs, so it opens in a browser without the server
running. These are genuine captures of working screens, not mock-ups.

    python scripts/capture_console_screens.py
    python scripts/capture_console_screens.py --out outputs/product/screens

This is **not** a screenshot tool: no headless browser is installed in this environment, so
no PNG is produced. See docs/product/PRODUCT_VALIDATION_REPORT.md for that limitation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT  # noqa: E402

#: Route, output file, and what the screen demonstrates.
SCREENS = [
    ("/", "01_mission_overview.html", "Mission Overview: snapshot statistics, findings, module status, abstentions, dataset inventory"),
    ("/objects?q=ARIANE", "02_object_search.html", "Object search by name over the dated catalogue snapshot"),
    ("/objects/37607", "03_object_assessment.html", "Orbital/lifetime/re-entry assessment for NORAD 37607 with coherence status and unsupported assessments"),
    ("/telemetry", "04_satellite_intelligence.html", "Anonymised ESA-ADB missions and saved benchmark arm evidence"),
    ("/telemetry/1/channel_12", "05_telemetry_channel.html", "Real telemetry series with ground-truth anomaly intervals shaded"),
    ("/debris", "06_debris_sequences.html", "SpotGEO test sequences with saved detections"),
    ("/debris/1", "07_debris_detections.html", "Real SpotGEO frame with detection overlay; confidence and timestamp unavailable"),
    ("/risk", "08_risk_intelligence.html", "Physical collision probability distribution, priority kept separate, C4 abstention"),
    ("/runs", "09_run_explorer.html", "Versioned pipeline runs and operating modes"),
    ("/prospective", "10_prospective_blocked.html", "Prospective evaluation disabled with the fixed protocol and BLOCKED status"),
    ("/scenario", "11_scenario_analysis.html", "Scenario execution form writing a new run directory"),
    ("/explorer", "18_earth_orbit_explorer.html", "Earth & orbit explorer: interactive globe (WebGL), schematic orbit geometry with its basis stated on screen"),
    ("/intelligence", "19_lifetime_reentry_intelligence.html", "Lifetime and re-entry intelligence: catalogue-wide counts, interval kinds, abstentions, subgroup coverage cue"),
    ("/decisions", "20_decision_intelligence.html", "Decision intelligence: recorded ordering rule, current queue, exploratory non-blind ranking-utility evidence"),
    ("/evidence", "21_evidence_provenance.html", "Evidence, provenance and validation: digests, module lineage, twin integrity, readiness"),
    ("/twin-state", "22_twin_state.html", "Twin-state explorer: source policies, integrity and chain equivalence"),
    ("/demo", "23_guided_demonstration.html", "Guided demonstration: capability map and thirteen stages with live values"),
]

#: Routes discovered at capture time (newest run, and a comparison when two exist).
DYNAMIC = [
    ("run_detail", "12_run_detail.html", "Run manifest, module provenance, abstentions and tables"),
    ("run_compare", "13_run_compare.html", "Two runs compared side by side without mixing artifacts"),
    ("report", "14_assessment_report.html", "Exported assessment report with full provenance"),
]


def _inline(html: str, css: str, base_url: str) -> str:
    """Inline the stylesheet and absolutise asset/API links so the file stands alone."""
    html = html.replace('<link rel="stylesheet" href="/static/console.css">',
                        f"<style>\n{css}\n</style>")
    # Images and API links must point at a running server; make them absolute.
    html = re.sub(r'(href|src|href=)="(/(?:api|static)/)', rf'\1="{base_url}\2', html)
    html = html.replace('href="/api/', f'href="{base_url}/api/')
    html = html.replace('src="/api/', f'src="{base_url}/api/')
    html = html.replace('href="/static/', f'href="{base_url}/static/')
    html = html.replace('xlink:href="/api/', f'xlink:href="{base_url}/api/')
    html = html.replace('href="/api/debris', f'href="{base_url}/api/debris')
    return html.replace("<image href=\"/api/", f"<image href=\"{base_url}/api/")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="outputs/product/screens")
    parser.add_argument("--base-url", default="http://127.0.0.1:8070",
                        help="server URL used for image and API links in the captures")
    args = parser.parse_args(argv)

    from fastapi.testclient import TestClient
    from cosmos.product.api import create_app

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    css_path = ROOT / "cosmos" / "product" / "static" / "console.css"
    css = css_path.read_text(encoding="utf-8") if css_path.is_file() else ""

    client = TestClient(create_app())
    runs = client.get("/api/runs").json()["runs"]

    routes = list(SCREENS)
    if runs:
        routes.append((f"/runs/{runs[0]['run_id']}", DYNAMIC[0][1], DYNAMIC[0][2]))
        if len(runs) >= 2:
            routes.append((f"/compare?a={runs[0]['run_id']}&b={runs[1]['run_id']}",
                           DYNAMIC[1][1], DYNAMIC[1][2]))
    routes.append(("/reports/object/37607", DYNAMIC[2][1], DYNAMIC[2][2]))

    captured = []
    for route, filename, description in routes:
        response = client.get(route)
        record = {"route": route, "file": filename, "description": description,
                  "status_code": response.status_code,
                  "bytes": len(response.content)}
        if response.status_code != 200:
            record["captured"] = False
            record["detail"] = "route did not return 200; no capture written"
            captured.append(record)
            print(f"  SKIP {response.status_code} {route}")
            continue
        page = _inline(response.text, css, args.base_url.rstrip("/"))
        (out_dir / filename).write_text(page, encoding="utf-8")
        record["captured"] = True
        captured.append(record)
        print(f"  ok   {response.status_code} {route} -> {filename} ({len(page)} bytes)")

    index = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "base_url_for_assets": args.base_url,
        "screens": captured,
        "note": ("each file is the real server response for that route with CSS inlined; "
                 "images and API links require the server to be running at base_url"),
        "not_a_screenshot": ("no headless browser is installed in this environment, so no PNG "
                             "was produced; these HTML captures are the rendered screens"),
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"\n{sum(1 for r in captured if r['captured'])}/{len(captured)} screens captured")
    print(f"written: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
