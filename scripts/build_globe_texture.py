"""Build the console globe's Earth texture from the archived land mask. Deterministic, offline.

    python scripts/build_globe_texture.py            # -> cosmos/product/static/earth-land-mask.png

The only geographic input is ``land_fraction`` in
``data/feature3_reentry/external/population_grid_0p25deg.npz`` (0.25 deg, north-up, longitude from
-180), already in the repository: GHS-POP E2020 R2023A (JRC, CC BY 4.0) with Natural Earth 1:50m
land (public domain). Nothing is downloaded and no geography is invented: land, ocean, coastline
and a 30-degree graticule are drawn from that one array, in the console's palette.

The build asserts eight known land/ocean coordinates before writing, so the map cannot be
produced flipped or shifted without failing. A sidecar JSON records the source, the colours and
the SHA-256 of the written image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GRID = "data/feature3_reentry/external/population_grid_0p25deg.npz"
OUT = "cosmos/product/static/earth-land-mask.png"
#: Power-of-two raster for WebGL 1 compatibility (see build()).
POT_WIDTH, POT_HEIGHT = 2048, 1024

#: Palette, matching cosmos/product/static/console.css.
OCEAN = (10, 22, 40)
OCEAN_DEEP = (7, 16, 30)
LAND = (31, 62, 88)
COAST = (78, 168, 222)
GRATICULE = (22, 44, 70)
EQUATOR = (34, 62, 92)

#: (label, latitude, longitude, is_land) — the orientation guard.
PROBES = (
    ("Gulf of Guinea", 0.0, 0.0, False),
    ("central Africa", 5.0, 20.0, True),
    ("North America", 45.0, -100.0, True),
    ("Australia", -25.0, 135.0, True),
    ("Siberia", 65.0, 100.0, True),
    ("mid Pacific", 0.0, -150.0, False),
    ("Antarctica", -80.0, 0.0, True),
    ("mid Atlantic", 30.0, -40.0, False),
)


def _index(lat: float, lon: float, shape: tuple[int, int], res: float) -> tuple[int, int]:
    row = int((90.0 - lat) / res)
    col = int((lon + 180.0) / res)
    return min(max(row, 0), shape[0] - 1), min(max(col, 0), shape[1] - 1)


def check_orientation(land: np.ndarray, res: float) -> list[str]:
    """Return the probes that disagree with the known geography (empty list = correct)."""
    bad = []
    for label, lat, lon, is_land in PROBES:
        r, c = _index(lat, lon, land.shape, res)
        if bool(land[r, c]) is not is_land:
            bad.append(f"{label} ({lat:+.1f}, {lon:+.1f}): mask says {'land' if land[r, c] else 'ocean'}")
    return bad


def build(root: Path = ROOT) -> dict:
    grid_path = root / GRID
    data = np.load(grid_path)
    res = float(data["res_deg"])
    land_fraction = np.asarray(data["land_fraction"], dtype=np.float32)
    land = land_fraction > 0.5

    bad = check_orientation(land, res)
    if bad:
        raise SystemExit("land mask orientation check failed:\n  " + "\n  ".join(bad))

    h, w = land.shape
    img = np.empty((h, w, 3), dtype=np.uint8)
    # Ocean with a faint depth gradient towards the poles: a purely decorative shade of one colour,
    # carrying no data (sea depth is not in the archive).
    lat = 90.0 - (np.arange(h) + 0.5) * res
    shade = (np.abs(lat) / 90.0)[:, None]
    for k in range(3):
        img[:, :, k] = (OCEAN[k] * (1.0 - shade) + OCEAN_DEEP[k] * shade).astype(np.uint8)
    img[land] = LAND

    # Coastline: land cells with at least one ocean neighbour.
    neighbour_ocean = np.zeros_like(land)
    for axis, shift in ((0, 1), (0, -1), (1, 1), (1, -1)):
        neighbour_ocean |= ~np.roll(land, shift, axis=axis)
    img[land & neighbour_ocean] = COAST

    # Graticule every 30 degrees, equator slightly brighter. A coordinate aid, not data.
    for deg in range(-180, 181, 30):
        col = int((deg + 180.0) / res) % w
        img[:, col] = np.where(land[:, col][:, None], img[:, col], GRATICULE)
    for deg in range(-60, 61, 30):
        row = int((90.0 - deg) / res)
        if 0 <= row < h:
            colour = EQUATOR if deg == 0 else GRATICULE
            img[row] = np.where(land[row][:, None], img[row], colour)

    from PIL import Image  # pillow is already a product dependency (serves SpotGEO frames)
    out_path = root / OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.fromarray(img)
    # WebGL 1 only accepts mipmaps and REPEAT wrapping on power-of-two textures, and 1440x720 is
    # not one: an NPOT texture would sample black. Resample to 2048x1024 with NEAREST, which maps
    # each output pixel to the 0.25 deg cell that contains it and therefore invents no geography.
    native = image.size
    image = image.resize((POT_WIDTH, POT_HEIGHT), Image.NEAREST)
    image.save(out_path, format="PNG", optimize=True)
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()

    record = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output": OUT,
        "sha256": digest,
        "bytes": out_path.stat().st_size,
        "size_px": [POT_WIDTH, POT_HEIGHT],
        "native_grid_px": list(native),
        "resample": ("nearest-neighbour from the 0.25 deg grid to a power-of-two raster; WebGL 1 requires "
                     "power-of-two textures for mipmaps and REPEAT wrapping. No geography is added: each "
                     "output pixel takes the value of the 0.25 deg cell that contains it"),
        "projection": "equirectangular, north-up, longitude -180..180",
        "source_array": {"path": GRID, "member": "land_fraction",
                         "sha256": hashlib.sha256(grid_path.read_bytes()).hexdigest(),
                         "resolution_deg": res, "attribution": str(data["source"])},
        "palette": {"ocean": OCEAN, "ocean_deep": OCEAN_DEEP, "land": LAND,
                    "coast": COAST, "graticule": GRATICULE, "equator": EQUATOR},
        "land_cells": int(land.sum()), "cells": int(land.size),
        "contains_no_invented_geography": True,
        "orientation_probes_passed": len(PROBES),
        "command": "python scripts/build_globe_texture.py",
    }
    (out_path.with_suffix(".provenance.json")).write_text(json.dumps(record, indent=1) + "\n")
    return record


def main(argv=None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    record = build()
    print(json.dumps({k: record[k] for k in ("output", "sha256", "bytes", "size_px", "land_cells",
                                             "orientation_probes_passed")}, indent=None))
    print("provenance:", OUT.replace(".png", ".provenance.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
