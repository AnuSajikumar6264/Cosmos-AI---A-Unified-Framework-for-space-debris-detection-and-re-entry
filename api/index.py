"""Vercel serverless entry point for the COSMOS-AI Mission Intelligence Console.

Vercel's Python runtime serves the ASGI callable named ``app`` from this module. Nothing here
changes the console: it imports the same application that ``scripts/serve_console.py`` runs
locally, then applies the two adjustments a serverless platform requires.

    1. The scenario endpoint is disabled. ``POST /api/scenario`` spawns ``scripts/run_pipeline.py``
       as a subprocess and writes a new run directory; a serverless function has a read-only
       filesystem and no process lifetime for that, so the route returns 501 with an explanation
       instead of failing obscurely.
    2. A banner is injected into every HTML page stating that this is the hosted demonstration and
       which screens are unavailable here, so a visitor is never misled about what they are seeing.

The console runs no model and performs no inference at request time. It reads the archived
forecast table for the dated snapshot and nothing else, so the deployed payload is a few megabytes.

Required for a working deployment (see website/DEPLOYMENT.md):
    outputs/twin/as_of_<snapshot>/forecast_table.csv.gz   as a plain Git blob, not an LFS pointer
    outputs/twin/as_of_<snapshot>/FORECAST_SHA256.txt
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import Response                                    # noqa: E402
from fastapi.responses import JSONResponse                      # noqa: E402

from cosmos.product.api import create_app                       # noqa: E402

# The console reads its artifacts from a repository root. On Vercel the git clone does not smudge
# Git LFS, so the tracked outputs/twin/*.csv.gz would arrive as a pointer file; api/archive/ holds a
# plain copy of the two required artifacts (identical SHA-256) and is used as the root when present.
ARCHIVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "archive")
_required = os.path.join(ARCHIVE, "outputs", "twin", "as_of_2026-10-27", "forecast_table.csv.gz")
app = create_app(root=ARCHIVE if os.path.isfile(_required) else ROOT)

SCENARIO_MESSAGE = (
    "Scenario execution is not available in the hosted demonstration. This endpoint runs the "
    "pipeline as a subprocess and writes a new versioned run directory, which a serverless "
    "function cannot do (read-only filesystem, no process lifetime). Clone the repository and "
    "run `python scripts/serve_console.py` to use it: every other screen works here unchanged."
)

UNAVAILABLE_HERE = (
    "Telemetry channel plots and SpotGEO image frames need 78 MB and 3.3 GB of archived arrays "
    "respectively, which exceed the hosted payload; those two screens report their built-in "
    "'unavailable' state here."
)

BANNER = (
    '<div style="background:#1a1205;border-bottom:1px solid #6b4e12;color:#f0d9a0;'
    'padding:.5rem 1rem;font:13px/1.5 system-ui,sans-serif;text-align:center">'
    '<strong>Hosted demonstration</strong> &middot; archived snapshot, read-only, no model runs at '
    'request time. Scenario execution is disabled and two data-heavy screens are unavailable; '
    'everything else is the real console. '
    '<a href="https://github.com/AnuSajikumar6264/Cosmos-AI---A-Unified-Framework-for-space-debris-detection-and-re-entry"'
    ' style="color:#ffd270">Run it locally for the full build &rarr;</a></div>'
)


@app.middleware("http")
async def _hosted_demo_adjustments(request, call_next):
    """Block the one route that cannot work here; mark every HTML page as the hosted demo."""
    if request.url.path == "/api/scenario" and request.method == "POST":
        return JSONResponse(status_code=501,
                            content={"status": "unavailable", "reason": SCENARIO_MESSAGE,
                                     "also_unavailable": UNAVAILABLE_HERE})

    response = await call_next(request)
    if not response.headers.get("content-type", "").startswith("text/html"):
        return response

    body = b"".join([chunk async for chunk in response.body_iterator])
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return Response(content=body, status_code=response.status_code,
                        headers=dict(response.headers), media_type=response.media_type)

    marker = "<body"
    i = text.find(marker)
    if i != -1:
        j = text.find(">", i)
        if j != -1:
            text = text[: j + 1] + BANNER + text[j + 1:]

    data = text.encode("utf-8")
    headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
    headers["content-length"] = str(len(data))
    return Response(content=data, status_code=response.status_code, headers=headers,
                    media_type=response.media_type)
