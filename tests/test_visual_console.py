"""Tests for the visual digital-twin layer: orbit geometry, globe API, new screens, Earth texture.

The geometry assertions are the point of this file. The globe is the one place in the console where
a viewer could mistake a drawing for a measurement, so these tests pin down three things:

* the orbit *size, shape and tilt* are the archived values (checked against closed-form two-body
  results and against the object record the rest of the console serves);
* the orbit *orientation and phase* are declared non-physical, deterministic and derived from
  nothing but the NORAD id;
* no endpoint returns a position at a time, a velocity, a sub-satellite point or a ground track,
  and the payload says so itself.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from cosmos.product.api import create_app
from cosmos.product.geometry import (MU_EARTH_KM3_S2, ORBIT_SAMPLES, ORBIT_SAMPLES_DETAIL, R_EARTH_KM,
                                     geometry_basis, globe_payload, layout_angles, marker_point,
                                     object_geometry, orbit_polyline, orbit_shape)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz"
STATIC = ROOT / "cosmos/product/static"
DEMO = (37607, 23806, 25544, 12)

needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(ROOT), raise_server_exceptions=False)


# ------------------------------------------------------------------ geometry: known physics
@pytest.mark.parametrize("perigee, apogee, period_min", [
    (400.0, 400.0, 92.56),        # circular 400 km, the textbook low-Earth value
    (35786.0, 35786.0, 1436.07),  # geostationary
    (0.0, 0.0, 84.49),            # surface-grazing: the Schuler period
])
def test_period_matches_the_two_body_result(perigee, apogee, period_min):
    shape = orbit_shape(perigee, apogee, 0.0)
    assert shape is not None
    assert shape["period_min"] == pytest.approx(period_min, abs=0.02)
    # and the period is exactly Kepler's third law on the derived semi-major axis
    a = shape["semi_major_axis_km"]
    assert shape["period_min"] == pytest.approx(2 * math.pi * math.sqrt(a ** 3 / MU_EARTH_KM3_S2) / 60.0, rel=1e-12)


def test_shape_is_the_archived_geometry_and_nothing_more():
    shape = orbit_shape(200.0, 800.0, 63.0)
    assert shape["periapsis_radius_km"] == pytest.approx(R_EARTH_KM + 200.0)
    assert shape["apoapsis_radius_km"] == pytest.approx(R_EARTH_KM + 800.0)
    assert shape["semi_major_axis_km"] == pytest.approx(R_EARTH_KM + 500.0)
    assert shape["eccentricity"] == pytest.approx(600.0 / (2 * R_EARTH_KM + 1000.0))
    assert shape["inclination_deg"] == 63.0


@pytest.mark.parametrize("row", [
    {"norad": 1, "perigee_km": None, "apogee_km": 500.0, "inclination_deg": 10.0},
    {"norad": 2, "perigee_km": float("nan"), "apogee_km": 500.0, "inclination_deg": 10.0},
    {"norad": 3, "perigee_km": 900.0, "apogee_km": 400.0, "inclination_deg": 10.0},   # never reordered
    {"norad": 4, "perigee_km": 400.0, "apogee_km": 500.0, "inclination_deg": 200.0},
    {"norad": 5, "perigee_km": 400.0, "apogee_km": 500.0, "inclination_deg": None},
])
def test_unusable_rows_produce_no_orbit(row):
    assert object_geometry(row) is None


def test_polyline_stays_between_periapsis_and_apoapsis_and_closes():
    shape = orbit_shape(122.0, 11622.0, 2.46)
    angles = layout_angles(37607)
    flat = orbit_polyline(shape, angles)
    assert len(flat) == 3 * (ORBIT_SAMPLES + 1)
    assert flat[:3] == flat[-3:], "the strip must close on its first point"
    radii = [math.sqrt(flat[i] ** 2 + flat[i + 1] ** 2 + flat[i + 2] ** 2) for i in range(0, len(flat), 3)]
    assert min(radii) == pytest.approx(shape["periapsis_earth_radii"], abs=2e-3)
    assert max(radii) == pytest.approx(shape["apoapsis_earth_radii"], abs=2e-3)
    assert min(radii) > 1.0, "a drawn orbit must stay outside the Earth's surface"


def test_orbit_plane_tilt_equals_the_archived_inclination():
    """The strongest statement the drawing makes: the plane's tilt is the archived inclination."""
    for inclination in (0.0, 2.46, 51.6, 63.0, 98.7, 144.0):
        shape = orbit_shape(500.0, 900.0, inclination)
        angles = layout_angles(25544)
        expected = inclination if inclination <= 90 else 180 - inclination

        def tilt_of(places):
            flat = orbit_polyline(shape, angles, places=places)
            points = np.array(flat, dtype=float).reshape(-1, 3)[:-1]
            normal = np.cross(points[0], points[len(points) // 3])
            normal /= np.linalg.norm(normal)
            return math.degrees(math.acos(min(1.0, abs(float(normal[2])))))

        assert tilt_of(12) == pytest.approx(expected, abs=1e-6), "exact geometry"
        assert tilt_of(4) == pytest.approx(expected, abs=0.01), "after rounding for transport"


def test_marker_lies_on_the_drawn_ellipse():
    shape = orbit_shape(650.0, 3800.0, 34.3)
    angles = layout_angles(12)
    marker = marker_point(shape, angles)
    r = math.sqrt(sum(v * v for v in marker))
    assert shape["periapsis_earth_radii"] - 1e-3 <= r <= shape["apoapsis_earth_radii"] + 1e-3
    flat = orbit_polyline(shape, angles, samples=720)
    points = np.array(flat, dtype=float).reshape(-1, 3)
    assert float(np.min(np.linalg.norm(points - np.array(marker), axis=1))) < 2e-2


def test_layout_angles_are_deterministic_and_declared_non_physical():
    first, second = layout_angles(37607), layout_angles(37607)
    assert first == second, "a marker that moved between loads would look like propagation"
    assert first["not_physical"] is True and "no node" in first["reason"]
    assert layout_angles(37607) != layout_angles(37608)
    for key in ("node_deg", "perigee_argument_deg", "phase_deg"):
        assert 0.0 <= first[key] < 360.0


def test_geometry_basis_states_what_is_not_available():
    basis = geometry_basis()
    missing = " ".join(basis["not_available_and_not_invented"]).lower()
    for absent in ("node", "argument of perigee", "epoch", "anomaly", "position", "velocity", "ground track"):
        assert absent in missing
    assert "perigee altitude" in basis["from_archive"] and "inclination" in basis["from_archive"]
    assert "layout" in basis["layout_angles"] and "NORAD id" in basis["layout_angles"]
    assert "P5" in basis["limitation"]


def test_payload_reports_what_it_could_not_draw():
    rows = [{"norad": 1, "name": "ok", "perigee_km": 400.0, "apogee_km": 500.0, "inclination_deg": 51.0},
            {"norad": 2, "name": "no geometry", "perigee_km": None, "apogee_km": None, "inclination_deg": None}]
    payload = globe_payload(rows, as_of="2026-10-27", catalogue_objects=2)
    assert payload["object_count"] == 1 and payload["excluded_count"] == 1
    assert payload["excluded"][0]["norad"] == 2 and "no usable" in payload["excluded"][0]["reason"]
    assert payload["live"] is False and payload["as_of"] == "2026-10-27"
    assert payload["earth_radius_km"] == pytest.approx(R_EARTH_KM)


def test_include_is_honoured_before_the_selection():
    rows = [{"norad": n, "name": str(n), "perigee_km": 400.0, "apogee_km": 500.0, "inclination_deg": 51.0}
            for n in (10, 11, 12)]
    payload = globe_payload(rows, as_of="2026-10-27", include=[12, 11])
    assert [o["norad"] for o in payload["objects"]][:2] == [12, 11]


# ------------------------------------------------------------------ the API
@needs_snapshot
def test_globe_endpoint_carries_its_own_basis(client):
    payload = client.get("/api/globe/objects?limit=20").json()
    assert payload["schema_version"] == "globe/1.0"
    assert payload["live"] is False
    assert payload["geometry_basis"]["not_available_and_not_invented"]
    assert payload["catalogue_objects"] >= payload["object_count"] > 0
    allowed = {"norad", "name", "object_class", "regime", "p_reentry_30d", "archived_elements",
               "derived_elements", "layout", "marker_earth_radii", "orbit_earth_radii", "orbit_points"}
    for obj in payload["objects"]:
        assert set(obj) == allowed, "the payload must not grow fields the geometry cannot support"
        assert obj["layout"]["not_physical"] is True
        assert len(obj["orbit_earth_radii"]) == 3 * (ORBIT_SAMPLES + 1)


@needs_snapshot
def test_no_endpoint_returns_a_position_a_velocity_or_a_ground_track(client):
    """A viewer must not be able to read a sub-satellite point out of any response."""
    forbidden = ("latitude", "longitude", "sub_satellite", "ground_track", "velocity_km_s",
                 "state_vector_value", "x_km", "y_km", "z_km")
    for path in ("/api/globe/objects?limit=5", "/api/globe/object/37607", "/api/objects/37607"):
        body = client.get(path).text.lower()
        for key in forbidden:
            assert f'"{key}"' not in body, f"{path} exposes {key}"
    record = client.get("/api/objects/37607").json()
    assert record["elements"]["state_vector"] is None
    assert "mean elements" in record["elements"]["state_vector_note"]


@needs_snapshot
@pytest.mark.parametrize("norad", DEMO)
def test_drawn_geometry_equals_the_object_record(client, norad):
    """The globe and the digital twin page must not disagree about the three archived quantities."""
    geom = client.get(f"/api/globe/object/{norad}").json()["objects"][0]
    elements = client.get(f"/api/objects/{norad}").json()["elements"]
    assert geom["archived_elements"]["perigee_km"] == pytest.approx(elements["perigee_altitude_km"])
    assert geom["archived_elements"]["apogee_km"] == pytest.approx(elements["apogee_altitude_km"])
    assert geom["archived_elements"]["inclination_deg"] == pytest.approx(elements["inclination_deg"])
    assert geom["orbit_points"] == ORBIT_SAMPLES_DETAIL + 1


@needs_snapshot
def test_globe_filters_and_rejections(client):
    assert client.get("/api/globe/objects?limit=5&regime=operator_controlled").status_code == 200
    assert client.get("/api/globe/objects?limit=5&object_class=R").status_code == 200
    assert client.get("/api/globe/objects?regime=nonsense").status_code == 400
    assert client.get("/api/globe/objects?object_class=Z").status_code == 400
    assert client.get("/api/globe/objects?include=abc").status_code == 400
    assert client.get("/api/globe/objects?limit=0").status_code == 422
    assert client.get("/api/globe/objects?limit=9999").status_code == 422
    assert client.get("/api/globe/object/99999999").status_code == 404
    classes = {o["object_class"] for o in client.get("/api/globe/objects?limit=25&object_class=R").json()["objects"]}
    assert classes <= {"R"}


# ------------------------------------------------------------------ the screens
@needs_snapshot
@pytest.mark.parametrize("path", ["/", "/explorer", "/objects/37607", "/intelligence", "/decisions",
                                  "/evidence", "/telemetry", "/risk", "/debris"])
def test_screens_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@needs_snapshot
def test_explorer_states_the_schematic_orientation_on_screen(client):
    page = client.get("/explorer").text
    assert 'id="globe-canvas"' in page
    assert "/static/js/cosmos-globe.js" in page and "/static/js/cosmos-explorer.js" in page
    assert 'id="globe-fallback"' in page, "a WebGL-less browser must get a labelled fallback"
    normalised = " ".join(page.split())
    assert "screen layout, not a measurement" in normalised
    assert "no ground track is drawn" in normalised
    assert "Only the camera moves" in normalised
    config = json.loads(page.split('id="globe-config">')[1].split("</script>")[0])
    assert config["include"] == list(DEMO)


@needs_snapshot
def test_object_page_carries_the_same_statement(client):
    normalised = " ".join(client.get("/objects/37607").text.split())
    assert "Orbit, lifetime and re-entry at a glance" in normalised
    assert "deterministic screen layout" in normalised
    assert "no position at a time and no ground track" in normalised
    assert '"single": 37607' in normalised.replace(" ", "") or '"single":37607' in normalised.replace(" ", "")


@needs_snapshot
def test_overview_hero_does_not_claim_live_data(client):
    normalised = " ".join(client.get("/").text.split())
    assert "archived, not live" in normalised
    assert "no position at a time, no ground track, nothing propagated" in normalised.lower()
    assert 'id="globe-canvas"' in normalised


@needs_snapshot
def test_health_screen_refuses_to_invent_subsystem_semantics(client):
    normalised = " ".join(client.get("/telemetry").text.split())
    assert "Power / thermal / attitude" in normalised and "not available" in normalised
    assert "channels are anonymised" in normalised
    assert "Telemetry Benchmarks" in client.get("/").text, "the demonstration script links by this label"


@needs_snapshot
def test_decision_screen_labels_the_exploratory_evidence(client):
    normalised = " ".join(client.get("/decisions").text.split())
    assert "non-blind" in normalised
    assert "no operational effectiveness is claimed" in normalised or "not a prospective test" in normalised
    assert "not a probability" in normalised


# ------------------------------------------------------------------ static assets
def test_renderer_and_controller_are_served_and_have_no_dependencies(client):
    for name in ("cosmos-globe.js", "cosmos-explorer.js"):
        response = client.get(f"/static/js/{name}")
        assert response.status_code == 200 and len(response.text) > 2000
        source = response.text
        assert "import " not in source.split("/*", 1)[-1].split("*/", 1)[-1][:200], "no module imports"
        for forbidden in ("cdn.", "https://unpkg", "THREE.", "require("):
            assert forbidden not in source, f"{name} must not depend on {forbidden}"


def test_earth_texture_is_built_from_the_archived_land_mask_and_is_not_flipped():
    png = STATIC / "earth-land-mask.png"
    sidecar = STATIC / "earth-land-mask.provenance.json"
    assert png.is_file() and sidecar.is_file()
    record = json.loads(sidecar.read_text())
    import hashlib
    assert hashlib.sha256(png.read_bytes()).hexdigest() == record["sha256"]
    assert record["source_array"]["member"] == "land_fraction"
    assert "GHS-POP" in record["source_array"]["attribution"]
    assert record["contains_no_invented_geography"] is True

    grid = ROOT / record["source_array"]["path"]
    if not grid.is_file():
        pytest.skip("population grid absent")
    from scripts.build_globe_texture import PROBES, check_orientation
    data = np.load(grid)
    land = np.asarray(data["land_fraction"], dtype=np.float32) > 0.5
    assert check_orientation(land, float(data["res_deg"])) == [], "the land mask orientation is wrong"
    assert record["orientation_probes_passed"] == len(PROBES)


def test_the_console_still_serves_no_external_assets():
    """Offline by construction: no page may reference a network origin."""
    for template in sorted((ROOT / "cosmos/product/templates").glob("*.html")):
        text = template.read_text()
        for forbidden in ("http://", "https://cdn", "unpkg.com", "jsdelivr", "googleapis"):
            if forbidden == "http://" and "http://127.0.0.1" in text:
                continue
            assert forbidden not in text, f"{template.name} references {forbidden}"


# ------------------------------------------------------------------ static check of the JavaScript
def _strip_js(source: str) -> str:
    """Remove comments, string literals and regex literals so delimiters can be counted.

    No JavaScript engine is installed in this environment (node, deno, quickjs and the Python
    bindings are all absent), so the renderer cannot be executed or parsed here. This scanner is the
    partial substitute: it catches the failure that editing is most likely to introduce, an
    unbalanced brace, parenthesis or bracket. Actual rendering still has to be confirmed in a
    browser, and the implementation report says so.
    """
    out = []
    i, n = 0, len(source)
    prev_significant = ""
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            i = source.find("\n", i)
            if i < 0:
                break
            continue
        if ch == "/" and nxt == "*":
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if ch in "\"'`":
            quote, i = ch, i + 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == quote:
                    i += 1
                    break
                i += 1
            out.append('""')
            prev_significant = '"'
            continue
        if ch == "/" and prev_significant in "(,=:[!&|?{};+return":
            i += 1
            while i < n:
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == "/":
                    i += 1
                    break
                if source[i] == "\n":
                    break
                i += 1
            out.append("RE")
            prev_significant = "RE"
            continue
        out.append(ch)
        if not ch.isspace():
            prev_significant = ch
        i += 1
    return "".join(out)


@pytest.mark.parametrize("name", ["cosmos-globe.js", "cosmos-explorer.js"])
def test_javascript_delimiters_balance(name):
    source = _strip_js((STATIC / "js" / name).read_text())
    stack: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for index, ch in enumerate(source):
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            assert stack and stack[-1] == pairs[ch], f"{name}: unbalanced {ch!r} at offset {index}"
            stack.pop()
    assert not stack, f"{name}: {len(stack)} unclosed delimiter(s): {''.join(stack)}"


@pytest.mark.parametrize("name", ["cosmos-globe.js", "cosmos-explorer.js"])
def test_javascript_is_strict_and_scoped(name):
    source = (STATIC / "js" / name).read_text()
    assert "'use strict';" in source
    assert source.lstrip().startswith("/*"), "each file opens with its own statement of scope"
    assert "innerHTML" not in source, "values are written as text nodes, never as markup"
    assert "eval(" not in source and "new Function" not in source


def test_renderer_only_reads_geometry_the_payload_carries():
    """The renderer must not derive a position of its own from anything in the payload."""
    source = (STATIC / "js" / "cosmos-globe.js").read_text()
    assert "orbit_earth_radii" in source and "marker_earth_radii" in source
    for invented in ("Date.now() *", "latitude", "longitude", "propagate", "meanAnomaly",
                     "trueAnomaly", "raan"):
        assert invented not in source, f"the renderer must not reference {invented}"


# ------------------------------------------------------------------ layout regressions
# These lock in the second-pass redesign (2026-11-09). The first pass passed every content test
# while being, in the browser, a 5044 px text page with the globe as a 22 %-of-viewport card; the
# browser measurements now live in outputs/product/screenshots/report.json and
# outputs/audit/console_interactions_*.json. The checks below are the part a browser-less suite can
# enforce: the visual containers exist, the prose is inside a disclosure, and the charts are real.

@needs_snapshot
def test_dashboard_is_a_dashboard_not_an_article(client):
    page = client.get("/").text
    assert 'class="dash"' in page, "the overview must use the viewport dashboard grid"
    assert page.count('class="dash-tile"') >= 3, "three bottom tiles carry the compact visuals"
    assert 'id="globe-canvas"' in page and 'class="stage"' in page
    assert page.count('<svg class="chart"') >= 2, "the dashboard must carry real charts"
    assert '<details class="scope"' in page, "the scope prose must be collapsed, not a wall of text"
    assert '<details class="more"' in page, "the evidence tables must be one click away"
    # the explanatory text still exists; it is simply inside the disclosures
    assert "Evidence boundary" in page and "read-only evidence twin" in page


@needs_snapshot
@pytest.mark.parametrize("path, minimum", [("/intelligence", 3), ("/decisions", 2), ("/telemetry", 2),
                                           ("/risk", 1), ("/debris", 2)])
def test_analysis_screens_carry_real_charts(client, path, minimum):
    page = client.get(path).text
    assert page.count('<svg class="chart"') >= minimum, f"{path} should draw at least {minimum} charts"
    assert '<details class="scope"' in page, f"{path} should collapse its scope prose"
    assert "svg" in page and "viewBox" in page


@needs_snapshot
def test_debris_screen_shows_a_real_annotated_frame(client):
    page = client.get("/debris").text
    assert '<svg class="overlay"' in page, "a real SpotGEO frame with its detections must be shown"
    assert page.index('<svg class="overlay"') < page.index("Observation sequences"), \
        "the image belongs above the table"
    assert "/api/debris/" in page and "frame/1.png" in page, "the overlay must reference the real frame"
    assert "no confidence" in page, "the missing confidence channel must stay labelled"


@needs_snapshot
def test_object_page_leads_with_the_visual(client):
    page = client.get("/objects/37607").text
    hero = page.index("Orbit, lifetime and re-entry at a glance")
    assert hero < page.index("Evidence availability for this object"), \
        "the digital twin page must open with the orbit and its charts"
    assert 'class="twin-hero"' in page
    assert page.count('<svg class="chart"') >= 4, "horizon bars and interval plots for both quantities"


@needs_snapshot
@pytest.mark.parametrize("path, title", [("/", "Mission Overview"), ("/explorer", "Earth &amp; Orbit Explorer"),
                                         ("/telemetry", "Health &amp; Telemetry Benchmarks"),
                                         ("/risk", "Conjunction &amp; Collision Analysis"),
                                         ("/debris", "Debris Detection"),
                                         ("/intelligence", "Lifetime &amp; Re-entry Intelligence"),
                                         ("/decisions", "Mission Decision Intelligence"),
                                         ("/evidence", "Evidence, Provenance &amp; Validation")])
def test_page_titles_match_the_navigation(client, path, title):
    assert title in client.get(path).text


@needs_snapshot
def test_evidence_page_never_dumps_a_record_into_a_badge(client):
    """A dict rendered inside a nowrap status badge widened the page to 2314 px in the first pass."""
    page = client.get("/evidence").text
    assert "records_total" not in page.split('class="status')[1][:400] if 'class="status' in page else True
    assert "all records valid" in page or "findings" in page
    assert "reemitted" in page, "the selected source must be named (the field is selected_source)"
