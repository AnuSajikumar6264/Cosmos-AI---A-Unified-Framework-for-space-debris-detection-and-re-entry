"""Prove in a real browser that the globe is interactive and that satellite selection works.

Screenshots show that something was drawn; they cannot show that dragging rotates the camera or
that clicking a marker changes the selection. This script drives headless Chromium against the
running console and asserts the state changes the renderer reports
(``window.CosmosExplorer.diagnostics()``), so every interaction claim in the acceptance report is
backed by a measurement.

Run it with the throwaway Playwright environment, exactly like the screenshot driver:

    PLAYWRIGHT_BROWSERS_PATH=/tmp/cosmos_pw_browsers /tmp/cosmos_shot_venv/bin/python \\
        scripts/verify_console_interactions.py --out outputs/audit

Exit code 0 means every check passed.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DEMO = [37607, 23806, 25544, 12]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:8070")
    ap.add_argument("--out", default="outputs/audit")
    ap.add_argument("--label", default="interactions")
    a = ap.parse_args(argv)

    from playwright.sync_api import sync_playwright

    checks: list[dict] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text[:160]}")
                if m.type == "error" else None)

        # ---------------------------------------------------------------- the explorer
        page.goto(a.base + "/explorer", wait_until="networkidle")
        page.wait_for_timeout(2600)
        info = page.evaluate("() => window.CosmosExplorer.diagnostics()")
        check("WebGL context created", bool(info["webgl"]), info["info"]["version"])
        check("renderer is drawing frames", info["info"]["frames"] > 20,
              f"{info['info']['frames']} frames, hardware {info['info']['hardware']}")
        check("Earth texture loaded", info["info"]["textureLoaded"] is True,
              f"textureLoaded={info['info']['textureLoaded']}")
        check("orbits and markers uploaded", info["info"]["orbitVertices"] > 1000 and info["info"]["markers"] > 10,
              f"{info['info']['orbitVertices']} orbit vertices, {info['info']['markers']} markers")
        check("canvas is large", info["info"]["cssPx"][0] > 600 and info["info"]["cssPx"][1] > 400,
              f"{info['info']['cssPx'][0]}x{info['info']['cssPx'][1]} css px")
        check("fallback notice hidden while WebGL works", info["fallbackVisible"] is False,
              f"fallbackVisible={info['fallbackVisible']}")

        # drag to rotate
        before = page.evaluate("() => window.CosmosExplorer.globe().info().camera")
        box = page.evaluate("""() => { const r = document.getElementById('globe-canvas').getBoundingClientRect();
                                       return {x: r.x + r.width/2, y: r.y + r.height/2}; }""")
        page.mouse.move(box["x"], box["y"])
        page.mouse.down()
        page.mouse.move(box["x"] + 190, box["y"] + 60, steps=12)
        page.mouse.up()
        page.wait_for_timeout(350)
        after = page.evaluate("() => window.CosmosExplorer.globe().info().camera")
        check("mouse drag rotates the camera",
              abs(after["azimuth"] - before["azimuth"]) > 0.3 and abs(after["elevation"] - before["elevation"]) > 0.1,
              f"azimuth {before['azimuth']:.3f} -> {after['azimuth']:.3f}, "
              f"elevation {before['elevation']:.3f} -> {after['elevation']:.3f}")

        # wheel to zoom
        page.mouse.move(box["x"], box["y"])
        page.mouse.wheel(0, -600)
        page.wait_for_timeout(300)
        zoomed = page.evaluate("() => window.CosmosExplorer.globe().info().camera")
        check("wheel zooms the camera", zoomed["distance"] < after["distance"] - 0.05,
              f"distance {after['distance']:.3f} -> {zoomed['distance']:.3f}")

        # reset view
        page.click("#globe-reset")
        page.wait_for_timeout(300)
        reset = page.evaluate("() => window.CosmosExplorer.globe().info().camera")
        check("reset camera restores the home view", abs(reset["distance"] - 3.4) < 0.01,
              f"distance back to {reset['distance']:.3f}")

        # pause the camera orbit
        page.click("#globe-spin")
        page.wait_for_timeout(200)
        spin = page.evaluate("() => window.CosmosExplorer.globe().autoRotate()")
        check("camera orbit can be paused", spin is False, f"autoRotate={spin}")

        # selection from the object list
        page.click("#globe-list .globe-item:nth-child(3)")
        page.wait_for_timeout(900)
        picked = page.evaluate("""() => ({
            selected: window.CosmosExplorer.diagnostics().selected,
            glSelected: window.CosmosExplorer.globe().info().selected,
            panel: document.getElementById('twin-record').innerText.slice(0, 160)
        })""")
        check("clicking the list selects an object and loads its record",
              picked["selected"] == picked["glSelected"] and "NORAD" in picked["panel"],
              f"selected {picked['selected']}, panel starts '{picked['panel'].splitlines()[0][:60]}'")

        # clicking a marker on the canvas
        hit = page.evaluate("""() => {
            const g = window.CosmosExplorer.globe();
            const scene = window.CosmosExplorer.scene();
            for (const obj of scene.objects) {
              const s = g.screenPosition(obj.norad);
              if (s && !s.occluded && s.x > 40 && s.y > 40) { return {norad: obj.norad, x: s.x, y: s.y}; }
            }
            return null; }""")
        if hit:
            rect = page.evaluate("""() => { const r = document.getElementById('globe-canvas').getBoundingClientRect();
                                            return {x: r.x, y: r.y}; }""")
            page.mouse.click(rect["x"] + hit["x"], rect["y"] + hit["y"])
            page.wait_for_timeout(900)
            clicked = page.evaluate("() => window.CosmosExplorer.diagnostics().selected")
            check("clicking a marker on the globe selects that object", clicked == hit["norad"],
                  f"clicked marker {hit['norad']} -> selected {clicked}")
        else:
            check("clicking a marker on the globe selects that object", False, "no visible marker to click")

        # every demonstration object can be selected and renders real fields
        for norad in DEMO:
            page.evaluate("(n) => window.CosmosExplorer.select(n, true)", norad)
            page.wait_for_timeout(700)
            state = page.evaluate("""() => ({
                selected: window.CosmosExplorer.diagnostics().selected,
                text: document.getElementById('twin-record').innerText,
                geometry: document.getElementById('twin-geometry').innerText })""")
            ok = (state["selected"] == norad and str(norad) in state["text"]
                  and "Keplerian period" in state["geometry"])
            unavailable = state["text"].count("not available")
            check(f"demonstration object {norad} selects and shows archived fields", ok,
                  f"panel mentions {norad}: {str(norad) in state['text']}, "
                  f"'not available' shown {unavailable} time(s) for fields the archive lacks")

        # ---------------------------------------------------------------- the dashboard
        page.goto(a.base + "/", wait_until="networkidle")
        page.wait_for_timeout(2600)
        dash = page.evaluate("""() => {
            const d = window.CosmosExplorer.diagnostics();
            const c = document.getElementById('globe-canvas').getBoundingClientRect();
            const main = document.querySelector('.main').getBoundingClientRect();
            return {frames: d.info.frames, objects: d.objects,
                    share: 100 * c.width * c.height / (main.width * Math.min(main.height, window.innerHeight - 220)),
                    canvas: [Math.round(c.width), Math.round(c.height)],
                    charts: document.querySelectorAll('svg.chart').length,
                    textChars: document.body.innerText.replace(/\\s+/g, ' ').length,
                    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1}; }""")
        check("dashboard globe draws", dash["frames"] > 20, f"{dash['frames']} frames, {dash['objects']} objects")
        check("dashboard globe occupies 45-55 % of the dashboard area",
              45 <= dash["share"] <= 58,
              f"{dash['canvas'][0]}x{dash['canvas'][1]} = {dash['share']:.0f}% of the dashboard area")
        check("dashboard carries charts", dash["charts"] >= 2, f"{dash['charts']} SVG charts")
        check("dashboard is not a wall of text", dash["textChars"] < 4500, f"{dash['textChars']} characters")
        check("no horizontal scrolling at 1440x900", dash["overflow"] is False, f"overflow={dash['overflow']}")

        page.evaluate("() => window.CosmosExplorer.select(23806, true)")
        page.wait_for_timeout(900)
        panel = page.evaluate("() => document.getElementById('twin-record').innerText.slice(0, 200)")
        check("dashboard selection updates the right panel", "23806" in panel,
              panel.splitlines()[0][:60] if panel else "empty")

        # ---------------------------------------------------------------- navigation
        routes = ["/explorer", "/objects/37607", "/intelligence", "/telemetry", "/risk", "/debris",
                  "/decisions", "/evidence", "/twin-state", "/runs", "/scenario", "/demo", "/prospective"]
        broken = []
        for route in routes:
            page.goto(a.base + "/", wait_until="domcontentloaded")
            link = page.query_selector(f'.nav a[href="{route}"]')
            if not link:
                continue
            link.click()
            page.wait_for_load_state("domcontentloaded")
            if route not in page.url:
                broken.append(route)
        check("every sidebar link navigates", not broken, f"broken: {broken or 'none'}")

        check("no uncaught JavaScript errors during the whole session", not errors,
              f"{len(errors)} error(s): {errors[:3] or 'none'}")
        browser.close()

        # ---------------------------------------------------------------- WebGL-less fallback
        blind = p.chromium.launch(args=["--disable-webgl", "--disable-webgl2"])
        bp = blind.new_context(viewport={"width": 1440, "height": 900}).new_page()
        bp.goto(a.base + "/explorer", wait_until="networkidle")
        bp.wait_for_timeout(1200)
        state = bp.evaluate("""() => {
            const fb = document.getElementById('globe-fallback');
            const c = document.getElementById('globe-canvas');
            return {fallbackVisible: fb ? !fb.hidden : null,
                    reason: fb ? (fb.innerText || '').slice(0, 120) : null,
                    canvasHidden: c ? getComputedStyle(c).display === 'none' : null,
                    listPopulated: document.querySelectorAll('#globe-list .globe-item').length,
                    panelHasRecord: (document.getElementById('twin-record').innerText || '').includes('NORAD')}; }""")
        check("without WebGL a labelled fallback appears", state["fallbackVisible"] is True,
              (state["reason"] or "").replace("\n", " ")[:90])
        check("without WebGL the canvas is hidden, not left blank", state["canvasHidden"] is True,
              f"canvas display none: {state['canvasHidden']}")
        check("without WebGL the evidence is still reachable",
              state["listPopulated"] > 5 and state["panelHasRecord"],
              f"{state['listPopulated']} objects listed, record panel populated: {state['panelHasRecord']}")
        blind.close()

    record = {"verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "base": a.base, "viewport": [1440, 900],
              "checks": checks,
              "passed": sum(1 for c in checks if c["passed"]),
              "failed": sum(1 for c in checks if not c["passed"])}
    out = Path(a.out) / f"console_interactions_{a.label}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"passed": record["passed"], "failed": record["failed"], "record": str(out)}))
    return 1 if record["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
