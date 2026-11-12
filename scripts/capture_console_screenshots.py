"""Open the running console in a real browser, capture PNG screenshots and report what the browser saw.

This is the diagnostic the project lacked: it drives headless Chromium over the running server, so a
visualisation can be *verified* rather than assumed. For every route it records console messages,
uncaught page errors, failed network requests, element geometry, and — for the globe — the live
WebGL diagnostics the renderer exposes (``window.CosmosExplorer.diagnostics()``), including the
frame counter, so a canvas that is present but not drawing is detected.

Chromium is **not** a project dependency: install Playwright into a throwaway environment and run
this script with that interpreter, so the project's own virtual environment stays untouched.

    python3.12 -m venv /tmp/cosmos_shot_venv
    /tmp/cosmos_shot_venv/bin/python -m pip install playwright
    PLAYWRIGHT_BROWSERS_PATH=/tmp/cosmos_pw_browsers /tmp/cosmos_shot_venv/bin/python -m playwright install chromium

    # with `python scripts/serve_console.py` already running:
    PLAYWRIGHT_BROWSERS_PATH=/tmp/cosmos_pw_browsers /tmp/cosmos_shot_venv/bin/python \\
        scripts/capture_console_screenshots.py --out outputs/product/screenshots

Headless Chromium renders WebGL through SwiftShader, so the globe in these captures is drawn by the
same code path a desktop browser uses, on the CPU instead of a GPU.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

#: Route, file name, and what has to be visible for the screen to count as working.
ROUTES = [
    ("/", "01_mission_overview", "globe stage, KPI strip, selected-object panel, timeline"),
    ("/explorer", "02_earth_explorer", "full-height globe, filters, object list, selected-object panel"),
    ("/objects/37607", "03_twin_37607", "digital twin: orbit view, lifetime and re-entry charts"),
    ("/objects/23806", "04_twin_23806", "digital twin with a lifetime abstention (L17)"),
    ("/objects/25544", "05_twin_25544", "operator-controlled object: re-entry abstention"),
    ("/objects/12", "06_twin_12", "object at the prediction cap"),
    ("/intelligence", "07_orbital_intelligence", "distribution charts and the priority queue"),
    ("/telemetry", "08_health_monitoring", "mission cards and the alarm-layer benchmark"),
    ("/telemetry/1/channel_12", "09_telemetry_channel", "real telemetry series with ground-truth intervals"),
    ("/risk", "10_conjunction_analysis", "risk distribution strip and event table"),
    ("/debris", "11_debris_monitoring", "SpotGEO sequences and benchmark arms"),
    ("/debris/1", "12_debris_detections", "real frame with detection overlay"),
    ("/decisions", "13_decision_intelligence", "ordering rule, queue, precision-at-k evidence"),
    ("/evidence", "14_evidence_validation", "digests, lineage, twin integrity"),
    ("/twin-state", "15_twin_state", "source policies and equivalence"),
    ("/demo", "16_guided_demo", "capability map and stages"),
    ("/runs", "17_run_explorer", "run history"),
    ("/scenario", "18_scenario", "scenario form"),
]

#: Elements that must exist and have a non-zero box on the given routes.
GEOMETRY_CHECKS = {
    "/": ["#globe-canvas", ".kpis", "#twin-record"],
    "/explorer": ["#globe-canvas", "#globe-list", "#twin-record", ".stage"],
    "/objects/37607": ["#globe-canvas", "svg.chart"],
    "/intelligence": [".meter", "table.data"],
    "/telemetry": [".kpis"],
    "/risk": ["svg.chart"],
    "/debris": [".kpis"],
    "/debris/1": ["svg.overlay"],
    "/decisions": ["table.data"],
    "/evidence": ["table.kv"],
}

DIAGNOSTICS_ROUTES = {"/", "/explorer", "/objects/37607", "/objects/23806", "/objects/25544", "/objects/12"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:8070")
    ap.add_argument("--out", default="outputs/product/screenshots")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--settle-ms", type=int, default=2600, help="time to let the globe draw frames")
    ap.add_argument("--full-page", action="store_true", help="also capture the full scrollable page")
    ap.add_argument("--only", default=None, help="substring filter on the route")
    a = ap.parse_args(argv)

    from playwright.sync_api import sync_playwright

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "base": a.base, "viewport": [a.width, a.height], "screens": []}

    routes = [r for r in ROUTES if not a.only or a.only in r[0]]
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
        context = browser.new_context(viewport={"width": a.width, "height": a.height},
                                      device_scale_factor=1)
        for route, name, expectation in routes:
            page = context.new_page()
            console: list[dict] = []
            page_errors: list[str] = []
            failed: list[dict] = []
            page.on("console", lambda m: console.append({"type": m.type, "text": m.text[:400]}))
            page.on("pageerror", lambda e: page_errors.append(str(e)[:400]))
            page.on("requestfailed", lambda r: failed.append({"url": r.url, "failure": (r.failure or "")[:200]}))
            page.on("response", lambda r: failed.append({"url": r.url, "status": r.status})
                    if r.status >= 400 else None)

            entry: dict = {"route": route, "file": f"{name}.png", "expect": expectation}
            try:
                response = page.goto(a.base + route, wait_until="domcontentloaded", timeout=45000)
                entry["status"] = response.status if response else None
                page.wait_for_load_state("networkidle", timeout=45000)
                if route in DIAGNOSTICS_ROUTES:
                    page.wait_for_timeout(a.settle_ms)
                    entry["globe"] = page.evaluate(
                        "() => (window.CosmosExplorer && window.CosmosExplorer.diagnostics) "
                        "? window.CosmosExplorer.diagnostics() : null")
                    entry["canvas_pixels"] = page.evaluate("""() => {
                      const c = document.getElementById('globe-canvas');
                      if (!c) return null;
                      const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
                      if (!gl) return {webgl: false};
                      const w = Math.min(c.width, 320), h = Math.min(c.height, 320);
                      const px = new Uint8Array(w * h * 4);
                      gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
                      let distinct = new Set(), lit = 0;
                      for (let i = 0; i < px.length; i += 4) {
                        const k = (px[i] >> 3) + ',' + (px[i+1] >> 3) + ',' + (px[i+2] >> 3);
                        distinct.add(k);
                        if (px[i] + px[i+1] + px[i+2] > 42) lit++;
                      }
                      return {webgl: true, sampled: w * h, distinctColours: distinct.size,
                              litFraction: +(lit / (w * h)).toFixed(4)};
                    }""")
                else:
                    page.wait_for_timeout(500)

                boxes = {}
                for selector in GEOMETRY_CHECKS.get(route, []):
                    boxes[selector] = page.evaluate(
                        """(sel) => { const el = document.querySelector(sel); if (!el) return null;
                             const r = el.getBoundingClientRect();
                             const cs = getComputedStyle(el);
                             return {w: Math.round(r.width), h: Math.round(r.height),
                                     visible: cs.display !== 'none' && cs.visibility !== 'hidden' && +cs.opacity > 0.01}; }""",
                        selector)
                entry["elements"] = boxes
                entry["layout"] = page.evaluate("""() => ({
                  scrollWidth: document.documentElement.scrollWidth,
                  clientWidth: document.documentElement.clientWidth,
                  horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
                  pageHeight: document.documentElement.scrollHeight,
                  textCharacters: document.body.innerText.replace(/\\s+/g, ' ').length,
                  paragraphs: document.querySelectorAll('p').length,
                  canvases: document.querySelectorAll('canvas').length,
                  svgCharts: document.querySelectorAll('svg.chart, svg.overlay').length
                })""")
                page.screenshot(path=str(out_dir / f"{name}.png"))
                if a.full_page:
                    page.screenshot(path=str(out_dir / f"{name}_full.png"), full_page=True)
            except Exception as exc:                      # a failing route must still be reported
                entry["error"] = f"{type(exc).__name__}: {exc}"[:400]
            entry["console_errors"] = [m for m in console if m["type"] == "error"]
            entry["console_warnings"] = [m for m in console if m["type"] == "warning"][:5]
            entry["page_errors"] = page_errors
            entry["failed_requests"] = [f for f in failed if f]
            report["screens"].append(entry)
            page.close()
            print(f"  {entry.get('status', '---')} {route:<28} "
                  f"errors={len(entry['console_errors']) + len(page_errors)} "
                  f"globe={(entry.get('globe') or {}).get('info', {}).get('frames') if entry.get('globe') else '-'}")
        context.close()
        browser.close()

    (out_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    bad = [s for s in report["screens"]
           if s.get("error") or s.get("page_errors") or s.get("console_errors")
           or (s.get("status") or 0) >= 400]
    print(json.dumps({"screens": len(report["screens"]), "with_problems": len(bad),
                      "out": str(out_dir)}, indent=None))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
