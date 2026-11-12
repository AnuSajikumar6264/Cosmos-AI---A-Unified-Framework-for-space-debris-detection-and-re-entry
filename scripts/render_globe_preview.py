"""Render the globe scene server-side as a PNG, from the very payload the browser draws.

    python scripts/render_globe_preview.py                       # -> outputs/product/screens/globe_preview_*.png
    python scripts/render_globe_preview.py --norad 37607         # one object
    python scripts/render_globe_preview.py --limit 120 --label wide

**This is not a browser screenshot.** No headless browser is installed in this environment
(limitation P15), so the WebGL canvas cannot be captured. What this script does instead is read
``GET /api/globe/objects`` and draw the same vertices with numpy and matplotlib in an orthographic
camera, with the same Earth land mask and the same occlusion rule. It is therefore an independent
check that the geometry the browser receives is the geometry intended: if this image looks right,
the vertices are right, and only the WebGL camera (perspective instead of orthographic) and the
shading differ.

Nothing is computed here that the payload does not already contain: the orbit polylines, the
marker points and the Earth texture all arrive from the repository.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEXTURE = "cosmos/product/static/earth-land-mask.png"
OUT_DIR = "outputs/product/screens"


def _camera(azimuth_deg: float, elevation_deg: float) -> np.ndarray:
    """Orthonormal camera basis: rows are (right, up, view) in the geocentric frame."""
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    view = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    view /= np.linalg.norm(view)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(world_up, view)
    if np.linalg.norm(right) < 1e-9:
        right = np.array([1.0, 0.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(view, right)
    return np.vstack([right, up, view])


def _earth_image(basis: np.ndarray, pixels: int) -> tuple[np.ndarray, np.ndarray]:
    """The visible hemisphere, by inverse mapping each pixel to a surface point and sampling the mask."""
    from PIL import Image
    texture = np.asarray(Image.open(ROOT / TEXTURE).convert("RGB"), dtype=np.float32) / 255.0
    rows, cols, _ = texture.shape

    span = np.linspace(-1.0, 1.0, pixels)
    px, py = np.meshgrid(span, -span)
    inside = px ** 2 + py ** 2 <= 1.0
    pz = np.zeros_like(px)
    pz[inside] = -np.sqrt(np.clip(1.0 - px[inside] ** 2 - py[inside] ** 2, 0.0, 1.0))

    # camera coordinates -> world coordinates (basis rows are orthonormal)
    world = (px[..., None] * basis[0] + py[..., None] * basis[1] + pz[..., None] * basis[2])
    lat = np.degrees(np.arcsin(np.clip(world[..., 2], -1.0, 1.0)))
    lon = np.degrees(np.arctan2(world[..., 1], world[..., 0]))
    row = np.clip(((90.0 - lat) / 180.0 * (rows - 1)).astype(int), 0, rows - 1)
    col = np.clip(((lon + 180.0) / 360.0 * (cols - 1)).astype(int), 0, cols - 1)

    image = np.zeros((pixels, pixels, 4), dtype=np.float32)
    image[..., :3] = texture[row, col]
    # the same view-facing shading term the fragment shader uses, so the image reads the same way
    facing = np.clip(-pz, 0.0, 1.0)
    image[..., :3] *= (0.42 + 0.58 * np.power(facing, 0.65))[..., None]
    rim = np.power(1.0 - facing, 3.0)
    image[..., 0] += 0.11 * rim * 0.55
    image[..., 1] += 0.42 * rim * 0.55
    image[..., 2] += 0.62 * rim * 0.55
    image[..., 3] = inside.astype(np.float32)
    return np.clip(image, 0.0, 1.0), inside


CLASS_COLOUR = {"P": "#4fc7f0", "R": "#a67de8", "C": "#8ca6c7", "D": "#e6ad54"}


def render(payload: dict, out: Path, *, azimuth: float = -60.0, elevation: float = 24.0,
           pixels: int = 1400, highlight: int | None = None) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    basis = _camera(azimuth, elevation)
    objects = payload["objects"]
    # Frame on the bulk of the drawn population rather than on its single widest orbit, so the Earth
    # stays the primary object; wider orbits simply leave the frame, as they do on screen.
    apoapses = sorted(float(o["derived_elements"]["apoapsis_earth_radii"]) for o in objects) or [1.2]
    if highlight is not None:
        for obj in objects:
            if obj["norad"] == highlight:
                apoapses.append(float(obj["derived_elements"]["apoapsis_earth_radii"]))
    reference = apoapses[int(0.72 * (len(apoapses) - 1))] if len(objects) > 1 else apoapses[-1]
    extent = float(min(max(1.62, reference * 1.12), 4.2))

    fig = plt.figure(figsize=(pixels / 150, pixels / 150), dpi=150)
    fig.patch.set_facecolor("#070d18")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#070d18")
    ax.set_xlim(-extent, extent)
    ax.set_ylim(-extent, extent)
    ax.set_aspect("equal")
    ax.axis("off")

    # atmospheric glow: concentric rings outside the limb, matching the additive shell
    for k in range(26):
        r = 1.0 + 0.085 * k / 25.0
        ax.add_patch(plt.Circle((0, 0), r, color="#3c9fe0", alpha=0.045 * (1 - k / 25.0),
                                lw=0, zorder=1))

    earth, _ = _earth_image(basis, 1100)
    ax.imshow(earth, extent=(-1, 1, -1, 1), zorder=2, interpolation="bilinear")

    drawn = 0
    for obj in objects:
        flat = np.asarray(obj["orbit_earth_radii"], dtype=float).reshape(-1, 3)
        cam = flat @ basis.T                      # columns: right, up, view
        x, y, z = cam[:, 0], cam[:, 1], cam[:, 2]
        hidden = (z > 0) & (x ** 2 + y ** 2 <= 1.0)       # behind the sphere, inside the limb
        colour = CLASS_COLOUR.get(str(obj.get("object_class") or "").upper(), "#94a8c0")
        selected = highlight is not None and obj["norad"] == highlight
        segments_x, segments_y = x.copy(), y.copy()
        segments_x[hidden] = np.nan
        segments_y[hidden] = np.nan
        ax.plot(segments_x, segments_y, color=colour, lw=1.7 if selected else 0.8,
                alpha=0.95 if selected else 0.45, zorder=5 if selected else 3,
                solid_capstyle="round")
        marker = np.asarray(obj["marker_earth_radii"], dtype=float) @ basis.T
        if not ((marker[2] > 0) and (marker[0] ** 2 + marker[1] ** 2 <= 1.0)):
            ax.plot([marker[0]], [marker[1]], marker="o", color=colour,
                    markersize=7.5 if selected else 3.4,
                    markeredgecolor="#ffffff" if selected else "none",
                    markeredgewidth=0.9 if selected else 0, zorder=6)
        drawn += 1

    label = (f"COSMOS-AI · archived snapshot {payload['as_of']} · {drawn} schematic orbits\n"
             "orbit size, shape and tilt from the archive; orientation about the pole and marker phase "
             "are a screen layout, not a measurement\n"
             "server-side orthographic preview of the browser payload — not a browser screenshot; "
             "no position at a time, no ground track, nothing propagated")
    ax.text(0.015, 0.985, label, transform=ax.transAxes, va="top", ha="left",
            color="#9bacc2", fontsize=7.4, family="monospace", linespacing=1.6)
    legend = "  ".join(f"● {name}" for name in ("payload", "rocket body", "component", "fragment"))
    ax.text(0.015, 0.02, legend, transform=ax.transAxes, va="bottom", ha="left",
            color="#6e8099", fontsize=7.2, family="monospace")

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)
    return {"output": str(out.relative_to(ROOT)), "objects_drawn": drawn,
            "extent_earth_radii": round(extent, 3), "azimuth_deg": azimuth, "elevation_deg": elevation}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--norad", type=int, default=None, help="render one object only")
    ap.add_argument("--highlight", type=int, default=37607)
    ap.add_argument("--azimuth", type=float, default=-60.0)
    ap.add_argument("--elevation", type=float, default=24.0)
    ap.add_argument("--label", default=None)
    ap.add_argument("--out", default=OUT_DIR)
    a = ap.parse_args(argv)

    from fastapi.testclient import TestClient
    from cosmos.product.api import create_app

    client = TestClient(create_app(ROOT))
    if a.norad:
        response = client.get(f"/api/globe/object/{a.norad}")
    else:
        include = ",".join(str(n) for n in (37607, 23806, 25544, 12))
        response = client.get(f"/api/globe/objects?limit={a.limit}&include={include}")
    response.raise_for_status()
    payload = response.json()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = a.label or (f"object_{a.norad}" if a.norad else f"scene_{payload['object_count']}")
    out = ROOT / a.out / f"globe_preview_{name}_{stamp}.png"
    record = render(payload, out, azimuth=a.azimuth, elevation=a.elevation,
                    highlight=a.norad or a.highlight)
    record.update({"as_of": payload["as_of"], "schema_version": payload["schema_version"],
                   "catalogue_objects": payload.get("catalogue_objects"),
                   "is_browser_screenshot": False,
                   "note": "orthographic server-side preview of the same payload the WebGL canvas draws"})
    print(json.dumps(record, indent=None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
