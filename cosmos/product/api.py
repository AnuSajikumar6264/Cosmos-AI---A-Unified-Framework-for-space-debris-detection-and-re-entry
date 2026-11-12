"""FastAPI application for the COSMOS-AI Mission Intelligence Console.

The application is a presentation and orchestration layer. It contains **no scientific
engine**: catalogue, telemetry, debris and conjunction values are read by
:mod:`cosmos.product.store`, and a scenario run is executed by calling
``scripts/run_pipeline.py``'s own ``main`` so that a run started from the console writes
byte-identical artifacts to one started from the command line.

Three operating modes are exposed and never blurred:

``historical``    load a verified existing run; nothing is recomputed
``scenario``      execute the supported pipeline into a **new** versioned run directory
``prospective``   research-only; disabled while the required later snapshot is unavailable
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from ..ai.provenance import ROOT
from . import charts, geometry, reports
import logging
import sys
import time
import traceback
import uuid

from ..ai import schema as _schema
from ..ai.schema import stamp
from .logging_setup import APP_LOGGER, REQUEST_LOGGER, log_fields
from .store import (DEFAULT_AS_OF, DEFAULT_TWIN_SOURCE_POLICY, MODULE_EVIDENCE_CLASS, TWIN_SNAPSHOT, TWIN_SOURCE_POLICIES,
                    TWIN_STATE_REEMITTED, ArtifactStore, DataUnavailable, InvalidSelection, freshness, lineage_for_module)

_POLICY_PATTERN = "^(" + "|".join(TWIN_SOURCE_POLICIES) + ")$"

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"

MODES = {
    "historical": "Historical Run — verified saved outputs, never recomputed",
    "scenario": "Scenario Analysis — executes the supported pipeline into a new run",
    "prospective": "Prospective Evaluation — research-only, blocked pending outcome data",
}


class ScenarioRequest(BaseModel):
    """Validated parameters for a scenario run. Only supported knobs are accepted."""

    as_of: str = Field(default="2026-10-27", pattern=r"^\d{4}-\d{2}-\d{2}$")
    limit: int | None = Field(default=500, ge=1, le=40000)
    collision_limit: int | None = Field(default=200, ge=1, le=3000)
    debris_sequence_limit: int | None = Field(default=5, ge=1, le=200)
    health_calibrator: str | None = Field(default="conformal_bh", max_length=40)
    collision_model: str = Field(default="cosmos_gated", max_length=40)
    twin_source_policy: str = Field(default=DEFAULT_TWIN_SOURCE_POLICY, pattern=_POLICY_PATTERN)
    modules: list[str] | None = None


def _scenario_assumptions(request: "ScenarioRequest") -> list[str]:
    """What each accepted knob changes, stated for the run record; nothing scientific is altered by any of them."""
    notes = [f"snapshot as-of {request.as_of}: every value is read from that dated archive; no later data is ingested"]
    notes.append(f"object limit {request.limit}: the {request.limit} highest 30-day re-entry probabilities are kept" if request.limit
                 else "no object limit: the full snapshot population is processed")
    notes.append(f"conjunction events limited to {request.collision_limit}" if request.collision_limit else "all held-out conjunction events scored")
    notes.append(f"debris sequences limited to {request.debris_sequence_limit}" if request.debris_sequence_limit else "all saved debris sequences read")
    notes.append(f"health benchmark rows restricted to calibrator {request.health_calibrator}" if request.health_calibrator
                 else "all health benchmark calibrators included")
    notes.append(f"collision model {request.collision_model} (archived predictions; no model executed)")
    notes.append(f"twin-state source policy {request.twin_source_policy}")
    notes.append("modules: " + (", ".join(request.modules) + " plus their dependencies" if request.modules else "all nine"))
    notes.append("no retraining, rescoring or revalidation: the run re-expresses saved artifacts through the shared contracts")
    return notes


def create_app(root: str | Path = ROOT) -> FastAPI:
    store = ArtifactStore(root)
    app = FastAPI(
        title="COSMOS-AI Mission Intelligence Console",
        version="1.0.0",
        description="Evidence-graded satellite intelligence over verified COSMOS-AI artifacts.",
    )
    app.state.store = store
    app.state.root = Path(root).resolve()
    request_logger = logging.getLogger(REQUEST_LOGGER)
    app_logger = logging.getLogger(APP_LOGGER)

    @app.middleware("http")
    async def _request_log(request: Request, call_next):
        """One structured record per request: id, method, path, status, duration. No bodies, no query values."""
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:                                   # the generic handler below also sees unhandled errors
            log_fields(request_logger, logging.ERROR, "request failed", request_id=request_id, method=request.method,
                       path=request.url.path, status=500, duration_ms=round((time.perf_counter() - started) * 1000, 1))
            raise
        log_fields(request_logger, logging.INFO, "request", request_id=request_id, method=request.method,
                   path=request.url.path, status=response.status_code,
                   duration_ms=round((time.perf_counter() - started) * 1000, 1))
        response.headers["X-Request-ID"] = request_id
        return response

    if STATIC.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES))
    templates.env.filters["fmt"] = _format_number
    templates.env.filters["pct"] = _format_percent
    templates.env.globals["MODES"] = MODES
    templates.env.globals["mission_bar"] = lambda: _safe(lambda: _mission_bar(store))

    def get_store() -> ArtifactStore:
        return app.state.store

    # ------------------------------------------------------------- error handling
    @app.exception_handler(DataUnavailable)
    async def _unavailable(request: Request, exc: DataUnavailable):
        payload = {"error": "data_unavailable", "message": exc.message, "detail": exc.detail}
        if _wants_json(request):
            return JSONResponse(payload, status_code=404)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Data unavailable", "kind": "UNAVAILABLE", **payload},
            status_code=404,
        )

    @app.exception_handler(Exception)
    async def _internal(request: Request, exc: Exception):
        """Unexpected errors: log the traceback server-side under the request id; never return it to the client."""
        request_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex[:16]
        app_logger.error("unhandled error %s", type(exc).__name__,
                         extra={"fields": {"request_id": request_id, "path": request.url.path,
                                           "error_type": type(exc).__name__,
                                           "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]}})
        payload = {"error": "internal", "message": "an internal error occurred; it was logged under the request id",
                   "request_id": request_id, "detail": ""}
        headers = {"X-Request-ID": request_id}          # the middleware cannot set it on this path: the handler does
        if _wants_json(request):
            return JSONResponse(payload, status_code=500, headers=headers)
        return templates.TemplateResponse(request, "error.html",
                                          {"title": "Internal error", "kind": "ERROR", **payload,
                                           "detail": f"Request id {request_id} — quote it when reporting; the server log holds the details."},
                                          status_code=500, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        """Unknown or unsupported browser routes render the error page; API, static and JSON clients keep FastAPI's
        standard JSON body and status code (404, 405, 409, 400 …). Request ids are added by the middleware."""
        if _wants_json(request) or request.url.path.startswith("/static/"):
            return await http_exception_handler(request, exc)
        kinds = {404: ("Page not found", "NOT FOUND", "unavailable", f"There is no page at {request.url.path}"),
                 405: ("Method not allowed", "NOT ALLOWED", "blocked", f"{request.method} is not supported for {request.url.path}")}
        title, kind, tone, message = kinds.get(exc.status_code, ("Request error", "ERROR", "unavailable", str(exc.detail)))
        detail = "" if exc.status_code in (404, 405) else str(exc.detail)
        return templates.TemplateResponse(request, "error.html",
                                          {"title": title, "kind": kind, "tone": tone, "message": message, "detail": detail},
                                          status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        """Invalid parameters: FastAPI's standard 422 JSON for API and JSON clients; the error page for browsers."""
        if _wants_json(request):
            return await request_validation_exception_handler(request, exc)
        parts = []
        for err in exc.errors()[:4]:
            loc = ".".join(str(x) for x in err.get("loc", ())[1:]) or "request"
            parts.append(f"{loc}: {err.get('msg')}")
        return templates.TemplateResponse(request, "error.html",
                                          {"title": "Invalid request", "kind": "INVALID", "tone": "blocked",
                                           "message": "The request parameters are not valid for this page",
                                           "detail": "; ".join(parts)}, status_code=422)

    @app.exception_handler(InvalidSelection)
    async def _invalid(request: Request, exc: InvalidSelection):
        payload = {"error": "invalid_selection", "message": str(exc), "detail": ""}
        if _wants_json(request):
            return JSONResponse(payload, status_code=400)
        return templates.TemplateResponse(
            request, "error.html",
            {"title": "Invalid selection", "kind": "INVALID", **payload},
            status_code=400,
        )

    # =========================================================== JSON API
    @app.get("/api/health")
    def api_health() -> dict[str, Any]:
        """Application liveness. Not a spacecraft health assessment."""
        return {"status": "ok", "service": "cosmos-ai-console", "version": app.version,
                "note": "application liveness only; unrelated to satellite health"}

    @app.get("/api/ready")
    def api_ready(store: ArtifactStore = Depends(get_store)) -> Response:
        """Readiness: required artifacts present and the dated-forecast digest verified. 503 when not ready.

        Reports no secrets and no paths outside the repository; it says nothing about any spacecraft. The same
        ``_readiness`` result feeds the overview's System readiness panel.
        """
        body = _readiness(store)
        return JSONResponse(body, status_code=200 if body["ready"] else 503)

    @app.get("/api/datasets")
    def api_datasets(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return _datasets(store)

    @app.get("/api/overview")
    def api_overview(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return _overview(store)

    @app.get("/api/objects/search")
    def api_object_search(q: str = Query(default="", max_length=64),
                          limit: int = Query(default=50, ge=1, le=500),
                          as_of: str = Query(default="2026-10-27",
                                             pattern=r"^\d{4}-\d{2}-\d{2}$"),
                          store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return {"query": q, "as_of": as_of,
                "results": store.search_objects(q, as_of=as_of, limit=limit)}

    @app.get("/api/objects/{norad}")
    def api_object(norad: int,
                   policy: str = Query(default=DEFAULT_TWIN_SOURCE_POLICY, pattern=_POLICY_PATTERN),
                   store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        """One object's evidence record; ``policy`` selects the twin-state source exactly as the page does."""
        return store.object_record(norad, twin_policy=policy)

    @app.get("/api/objects/{norad}/twin")
    def api_object_twin(norad: int,
                        as_of: str = Query(default="2026-10-27", pattern=r"^\d{4}-\d{2}-\d{2}$"),
                        policy: str = Query(default=DEFAULT_TWIN_SOURCE_POLICY, pattern=_POLICY_PATTERN),
                        store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        """The object's twin-state record from the source chosen by an explicit policy; fallback is always labelled."""
        if not store.catalogue(as_of).norad.eq(norad).any():
            raise DataUnavailable(f"NORAD {norad} is not in the {as_of} snapshot")
        return {"schema_version": stamp("api"), "norad": norad, **store.twin_record(norad, as_of, policy)}

    @app.get("/api/globe/objects")
    def api_globe_objects(limit: int = Query(default=120, ge=1, le=300),
                          regime: str = Query(default="", max_length=32),
                          object_class: str = Query(default="", max_length=2),
                          include: str = Query(default="", max_length=160),
                          sort: str = Query(default="p_reentry_30d",
                                            pattern="^(p_reentry_30d|perigee_km|apogee_km|inclination_deg|norad)$"),
                          as_of: str = Query(default=DEFAULT_AS_OF, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                          store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        """Schematic orbit geometry for the globe, with its own statement of what it is.

        The payload carries ``geometry_basis``: orbit size, shape and tilt come from the archived
        perigee, apogee and inclination; node, perigee argument and phase are a deterministic screen
        layout because the snapshot publishes no node, epoch or anomaly. Nothing is propagated, no
        position at a time is implied and no ground track is produced (limitation P5).
        """
        rows, included, total = _globe_rows(store, as_of=as_of, limit=limit, regime=regime,
                                            object_class=object_class, sort=sort, include=include)
        return geometry.globe_payload(rows, as_of=as_of, include=included, catalogue_objects=total)

    @app.get("/api/globe/object/{norad}")
    def api_globe_object(norad: int,
                         as_of: str = Query(default=DEFAULT_AS_OF, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                         store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        """One object's schematic geometry at full resolution, with the same ``geometry_basis``."""
        rows, _, total = _globe_rows(store, as_of=as_of, limit=1, regime="", object_class="",
                                     sort="norad", include=str(norad), only_included=True)
        if not rows:
            raise DataUnavailable(f"NORAD {norad} is not in the {as_of} snapshot")
        payload = geometry.globe_payload(rows, as_of=as_of, detail_norad=norad,
                                         include=[norad], catalogue_objects=total)
        if not payload["objects"]:
            raise DataUnavailable(
                f"NORAD {norad} has no usable orbit geometry in the {as_of} snapshot",
                detail=(payload["excluded"][0]["reason"] if payload["excluded"] else ""))
        return payload

    @app.get("/api/twin-state")
    def api_twin_state(as_of: str = Query(default="2026-10-27", pattern=r"^\d{4}-\d{2}-\d{2}$"),
                       policy: str = Query(default=DEFAULT_TWIN_SOURCE_POLICY, pattern=_POLICY_PATTERN),
                       run_id: str | None = Query(default=None),
                       store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        """Twin-state evidence root: source selection, provenance, integrity and equivalence with the catalogue chain.

        Computed on first request by streaming the selected archive once; cached until any candidate file or
        run table changes. Archived evidence only — nothing is regenerated.
        """
        return store.twin_state_integration(as_of, policy, run_id)

    @app.get("/api/telemetry/missions")
    def api_missions(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        missions = store.missions()
        return {
            "missions": missions,
            "identity_note": ("ESA-ADB missions are anonymised; they are not catalogue objects "
                              "and cannot be matched to a NORAD ID"),
            "available": bool(missions),
        }

    @app.get("/api/telemetry/{mission}/channels")
    def api_channels(mission: str,
                     store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return {"mission": mission, "channels": store.channels(mission)}

    @app.get("/api/telemetry/{mission}/{channel}")
    def api_channel(mission: str, channel: str,
                    max_points: int = Query(default=2000, ge=10, le=20000),
                    store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return store.channel_series(mission, channel, max_points=max_points)

    @app.get("/api/debris/sequences")
    def api_debris_sequences(limit: int = Query(default=40, ge=1, le=500),
                             store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return {"sequences": store.debris_sequences(limit=limit)}

    @app.get("/api/debris/{sequence_id}")
    def api_debris_sequence(sequence_id: int,
                            store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return store.debris_sequence(sequence_id)

    @app.get("/api/debris/{sequence_id}/frame/{frame}.png")
    def api_debris_frame(sequence_id: int, frame: int,
                         store: ArtifactStore = Depends(get_store)) -> FileResponse:
        path = store.debris_image_path(sequence_id, frame)
        return FileResponse(path, media_type="image/png")

    @app.get("/api/risk/collision")
    def api_collision(limit: int = Query(default=200, ge=1, le=3000),
                      model: str = Query(default="cosmos_gated", max_length=40),
                      store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return store.collision_events(limit=limit, model=model)

    @app.get("/api/runs")
    def api_runs(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return {"runs": [_run_json(summary) for summary in store.list_runs()]}

    @app.get("/api/runs/{run_id}")
    def api_run(run_id: str, store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        manifest = store.run_manifest(run_id)
        modules = manifest.get("modules", {}) or {}
        # lineage is derived for old manifests and read for new ones; never written back to the file
        return {**manifest,
                "view_schema_version": stamp("api"),
                "lineage": {name: lineage_for_module(record) for name, record in modules.items()},
                "evidence_class": {name: MODULE_EVIDENCE_CLASS.get(name, "not classified") for name in modules},
                "freshness": {"processing_started_at": manifest.get("started_at"), "snapshot_as_of": manifest.get("as_of"),
                              "source_observation_time": manifest.get("as_of"),
                              "note": "the run processed a dated snapshot; it did not observe anything"}}

    @app.get("/api/runs/{run_id}/ranking")
    def api_run_ranking(run_id: str, limit: int = Query(default=25, ge=1, le=1000),
                        store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        rows = store.ranking_with_horizon(run_id, limit=limit)
        return {"run_id": run_id, "schema_version": stamp("api"), "rows": rows, "returned": len(rows),
                "horizon_days": 30.0,
                "note": ("display only: the ranking order and every value are the run's own tables; the horizon "
                         "relation is computed at read time from the run's re-entry quantiles")}

    @app.get("/api/runs/{run_id}/tables/{name}")
    def api_run_table(run_id: str, name: str,
                      limit: int = Query(default=200, ge=1, le=20000),
                      store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        table = store.run_table(run_id, name, limit=limit)
        return {"run_id": run_id, "table": name, "rows": len(table),
                "columns": list(table.columns),
                "records": json.loads(table.to_json(orient="records"))}

    @app.get("/api/prospective")
    def api_prospective(store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        status = store.prospective_status()
        return {
            "mode": "prospective",
            "enabled": status["overall_status"] == "READY",
            "status": status["overall_status"],
            "assessment": status,
            "note": ("prospective evaluation is research-only and remains disabled until a "
                     "qualifying later snapshot exists; no prospective validation is claimed"),
        }

    @app.post("/api/scenario")
    def api_scenario(request: ScenarioRequest,
                     store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        return _execute_scenario(app.state.root, store, request)

    # =========================================================== HTML pages
    @app.get("/", response_class=HTMLResponse)
    def page_overview(request: Request, store: ArtifactStore = Depends(get_store)):
        overview = _overview(store)
        collision = _safe(lambda: store.collision_events(limit=400))
        strip = ""
        if collision:
            strip = charts.log_probability_strip(
                [event["log10_probability"] for event in collision["events"]])
        return templates.TemplateResponse(request, "overview.html", {
            "nav": "overview", "title": "Mission Overview", "overview": overview,
            "collision": collision, "collision_chart": strip,
            "datasets": _datasets(store),
            "readiness": _readiness(store),            # the same record GET /api/ready returns
            "timeline": _safe(lambda: _timeline(store)) or [],
            "p30_chart": _safe(lambda: charts.category_bars(
                [b["label"] for b in _p30_bands(store)],
                [b["count"] for b in _p30_bands(store)],
                width=420, height=150, value_digits=0,
                note="objects by reported 30-day re-entry probability")) or "",
            "config_json": json.dumps({"limit": 60, "include": [norad for norad, _ in DEMO_OBJECTS],
                                       "select": DEMO_OBJECTS[0][0], "autoRotate": True,
                                       "texture": "/static/earth-land-mask.png"}),
        })

    @app.get("/demo", response_class=HTMLResponse)
    def page_demo(request: Request, store: ArtifactStore = Depends(get_store)):
        """Guided demonstration: thirteen stages over the real stored outputs, each linking to the live screen."""
        return templates.TemplateResponse(request, "demo.html", {
            "nav": "demo", "title": "Guided demonstration", **_demo_context(store),
        })

    @app.get("/objects", response_class=HTMLResponse)
    def page_objects(request: Request, q: str = Query(default="", max_length=64),
                     store: ArtifactStore = Depends(get_store)):
        results = store.search_objects(q, limit=60)
        return templates.TemplateResponse(request, "objects.html", {
            "nav": "objects", "title": "Satellite Digital Twin — object search", "query": q, "results": results,
            "provenance": store.catalogue_provenance(),
        })

    @app.get("/explorer", response_class=HTMLResponse)
    def page_explorer(request: Request,
                      select: int | None = Query(default=None, ge=1),
                      limit: int = Query(default=120, ge=20, le=300),
                      store: ArtifactStore = Depends(get_store)):
        """Interactive globe over the archived snapshot geometry (schematic orientation; see geometry.py)."""
        table = store.catalogue(DEFAULT_AS_OF)
        regimes = sorted(str(v) for v in table["regime"].dropna().unique())
        demo = [(norad, why.split(":")[0]) for norad, why in DEMO_OBJECTS]
        config = {"limit": limit, "include": [norad for norad, _ in DEMO_OBJECTS],
                  "select": select if select is not None else DEMO_OBJECTS[0][0],
                  "texture": "/static/earth-land-mask.png", "autoRotate": True}
        return templates.TemplateResponse(request, "explorer.html", {
            "nav": "explorer", "title": "Earth & Orbit Explorer",
            "overview": store.catalogue_overview(DEFAULT_AS_OF),
            "provenance": store.catalogue_provenance(DEFAULT_AS_OF),
            "basis": geometry.geometry_basis(),
            "regimes": regimes, "classes": _GLOBE_CLASSES, "limit": limit,
            "demo_objects": demo, "config_json": json.dumps(config),
        })

    @app.get("/objects/{norad}", response_class=HTMLResponse)
    def page_object(request: Request, norad: int,
                    policy: str = Query(default=DEFAULT_TWIN_SOURCE_POLICY, pattern=_POLICY_PATTERN),
                    store: ArtifactStore = Depends(get_store)):
        record = store.object_record(norad, twin_policy=policy)
        incoherent = record["lifetime"]["horizon_coherence"]["status"] == "incoherent"
        return templates.TemplateResponse(request, "object.html", {
            "nav": "objects", "title": f"NORAD {norad}", "object": record,
            "twin_policy": policy, "twin_policies": TWIN_SOURCE_POLICIES,
            "reentry_chart": charts.horizon_bars(record["reentry"]["probability_by_horizon"]),
            "lifetime_chart": charts.horizon_bars(
                record["lifetime"]["horizon_probabilities"], incoherent=incoherent),
            "reentry_interval": charts.interval_plot(
                record["reentry"]["lo90_days"], record["reentry"]["median_days"],
                record["reentry"]["hi90_days"],
                label="re-entry time, 5-95 % Monte-Carlo spread"),
            "lifetime_interval": charts.interval_plot(
                record["lifetime"]["lo90_days"], record["lifetime"]["median_days"],
                record["lifetime"]["hi90_days"],
                label="lifetime, 5-95 % Mondrian CQR interval"),
            "globe_config": json.dumps({"single": norad, "select": norad, "autoRotate": True,
                                        "texture": "/static/earth-land-mask.png"}),
        })

    @app.get("/intelligence", response_class=HTMLResponse)
    def page_intelligence(request: Request, store: ArtifactStore = Depends(get_store)):
        """Lifetime and re-entry intelligence: catalogue-wide counts from the archived snapshot."""
        data = _intelligence(store)
        def bars(key, note, colour=None, width=430, height=190):
            return charts.category_bars([b["label"] for b in data[key]],
                                        [b["count"] for b in data[key]],
                                        width=width, height=height, note=note, colour=colour)
        return templates.TemplateResponse(request, "intelligence.html", {
            "nav": "intelligence", "title": "Lifetime & Re-entry Intelligence", **data,
            "p30_chart": bars("p30_bands", "objects by reported 30-day re-entry probability"),
            "lifetime_chart": bars("lifetime_bands", "objects by median lifetime", colour="#9a7fb8"),
            "inclination_chart": bars("inclination_bands", "objects by inclination"),
            "queue_chart": charts.category_bars(
                [(r.get("name") or r.get("object_id") or "?")[:24] for r in (data.get("ranking") or [])[:12]],
                [r.get("priority_score") for r in (data.get("ranking") or [])[:12]],
                width=860, height=320, horizontal=True, value_digits=3,
                note="priority score of the highest-ranked objects") if data.get("ranking") else "",
        })

    @app.get("/decisions", response_class=HTMLResponse)
    def page_decisions(request: Request, store: ArtifactStore = Depends(get_store)):
        """Decision intelligence: the recorded ordering rule and the exploratory evidence about it."""
        data = _decisions(store)
        rows = (data.get("ranking") or [])[:14]
        arms = ((data.get("t1") or {}).get("arms") or [])
        return templates.TemplateResponse(request, "decisions.html", {
            "nav": "decisions", "title": "Mission Decision Intelligence", **data,
            "queue_chart": charts.category_bars(
                [(r.get("name") or r.get("object_id") or "?")[:24] for r in rows],
                [r.get("priority_score") for r in rows],
                width=860, height=330, horizontal=True, value_digits=3,
                note="priority score of the current queue") if rows else "",
            "precision_chart": charts.category_bars(
                [a["arm"].replace("_", " ")[:22] for a in arms],
                [a["precision"].get(25) for a in arms],
                width=820, height=260, horizontal=True, value_digits=2,
                note="precision at k = 25 by ordering") if arms else "",
        })

    @app.get("/evidence", response_class=HTMLResponse)
    def page_evidence(request: Request, store: ArtifactStore = Depends(get_store)):
        """Evidence, provenance and validation: digests, module lineage, twin integrity, readiness."""
        return templates.TemplateResponse(request, "evidence.html", {
            "nav": "evidence", "title": "Evidence, Provenance & Validation", **_evidence(store),
        })

    @app.get("/twin-state", response_class=HTMLResponse)
    def page_twin_state(request: Request,
                        policy: str = Query(default=DEFAULT_TWIN_SOURCE_POLICY, pattern=_POLICY_PATTERN),
                        run_id: str | None = Query(default=None),
                        store: ArtifactStore = Depends(get_store)):
        status = store.twin_state_integration(DEFAULT_AS_OF, policy, run_id)
        return templates.TemplateResponse(request, "twin_state.html", {
            "nav": "twin", "title": "Twin state", "ts": status, "policies": TWIN_SOURCE_POLICIES, "policy": policy,
        })

    @app.get("/telemetry", response_class=HTMLResponse)
    def page_telemetry(request: Request, store: ArtifactStore = Depends(get_store)):
        missions = store.missions()
        arms = _safe(lambda: store.health_arms("conformal_bh"))
        arm_rows = []
        if arms is not None and len(arms):
            columns = ["mission", "tag", "encoder", "anomaly_and_rare/EW_F0.5",
                       "anomaly_and_rare/EW_precision", "anomaly_and_rare/EW_recall",
                       "alarm_runs", "false_alarm_runs"]
            present = [c for c in columns if c in arms.columns]
            arm_rows = json.loads(arms[present].head(30).to_json(orient="records"))
        key = "anomaly_and_rare/EW_F0.5"
        scored = [r for r in arm_rows if r.get(key) is not None][:10]
        return templates.TemplateResponse(request, "telemetry.html", {
            "nav": "telemetry", "title": "Health & Telemetry Benchmarks", "missions": missions,
            "arms": arm_rows,
            "arm_chart": charts.category_bars(
                [f"{r.get('encoder') or r.get('tag') or '?'} · m{r.get('mission')}" for r in scored],
                [r.get(key) for r in scored], width=760, height=280, horizontal=True,
                value_digits=3, note="event-wise F0.5 by benchmark arm") if scored else "",
            "channel_chart": charts.category_bars(
                [f"mission {m['mission']}" for m in missions],
                [m.get("labelled_intervals") for m in missions],
                width=480, height=190, value_digits=0,
                note="labelled ground-truth intervals per mission") if missions else "",
        })

    @app.get("/telemetry/{mission}/{channel}", response_class=HTMLResponse)
    def page_channel(request: Request, mission: str, channel: str,
                     points: int = Query(default=1800, ge=200, le=8000),
                     store: ArtifactStore = Depends(get_store)):
        series = store.channel_series(mission, channel, max_points=points)
        return templates.TemplateResponse(request, "channel.html", {
            "nav": "telemetry", "title": f"Mission {mission} / {channel}", "series": series,
            "channels": store.channels(mission),
            "chart": charts.telemetry_series(series["times"], series["values"],
                                             series["labelled_intervals"]),
        })

    @app.get("/debris", response_class=HTMLResponse)
    def page_debris(request: Request, store: ArtifactStore = Depends(get_store)):
        sequences = _safe(lambda: store.debris_sequences(limit=48)) or []
        vision_arms = _safe(store.vision_benchmark_arms) or []
        featured, featured_overlay = None, ""
        if sequences:
            record = _safe(lambda: store.debris_sequence(sequences[0]["sequence_id"]))
            frame = (record or {}).get("frames", [None])[0] if record else None
            if frame:
                url = (f"/api/debris/{record['sequence_id']}/frame/{frame['frame']}.png"
                       if frame["image_available"] else None)
                featured = {"sequence_id": record["sequence_id"], "frame": frame["frame"],
                            "detections": len(frame["detections"]), "detector": record.get("detector")}
                featured_overlay = charts.detection_overlay(frame["detections"], image_url=url)
        scored = [a for a in vision_arms if a.get("f1_mean") is not None]
        return templates.TemplateResponse(request, "debris.html", {
            "nav": "debris", "title": "Debris Detection", "sequences": sequences,
            "vision_arms": vision_arms, "served_detector": store.VISION_SERVED_DETECTOR,
            "featured": featured, "featured_overlay": featured_overlay,
            "arm_chart": charts.category_bars([f"{a.get('model')} · {a.get('inputs')}"[:26] for a in scored],
                                              [a.get("f1_mean") for a in scored], width=760, height=250,
                                              horizontal=True, value_digits=3,
                                              note="official SpotGEO F1 by detector") if scored else "",
            "detections_chart": charts.category_bars(
                [f"seq {s['sequence_id']}" for s in sequences[:12]],
                [s.get("detections") for s in sequences[:12]], width=520, height=200,
                value_digits=0, note="saved detections per sequence") if sequences else "",
        })

    @app.get("/debris/{sequence_id}", response_class=HTMLResponse)
    def page_debris_sequence(request: Request, sequence_id: int, frame: int = Query(default=1),
                             store: ArtifactStore = Depends(get_store)):
        record = store.debris_sequence(sequence_id)
        selected = next((f for f in record["frames"] if f["frame"] == frame),
                        record["frames"][0] if record["frames"] else None)
        overlay = ""
        if selected:
            url = (f"/api/debris/{sequence_id}/frame/{selected['frame']}.png"
                   if selected["image_available"] else None)
            overlay = charts.detection_overlay(selected["detections"], image_url=url)
        return templates.TemplateResponse(request, "sequence.html", {
            "nav": "debris", "title": f"SpotGEO sequence {sequence_id}", "record": record,
            "selected": selected, "overlay": overlay,
        })

    @app.get("/risk", response_class=HTMLResponse)
    def page_risk(request: Request, limit: int = Query(default=300, ge=1, le=3000),
                  store: ArtifactStore = Depends(get_store)):
        evidence = store.collision_events(limit=limit)
        return templates.TemplateResponse(request, "risk.html", {
            "nav": "risk", "title": "Conjunction & Collision Analysis", "evidence": evidence,
            "chart": charts.log_probability_strip(
                [event["log10_probability"] for event in evidence["events"]]),
            "high_risk": [e for e in evidence["events"] if e["high_risk_threshold_exceeded"]],
        })

    @app.get("/runs", response_class=HTMLResponse)
    def page_runs(request: Request, store: ArtifactStore = Depends(get_store)):
        return templates.TemplateResponse(request, "runs.html", {
            "nav": "runs", "title": "Run Explorer", "runs": store.list_runs(),
            "prospective": store.prospective_status(),
        })

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def page_run(request: Request, run_id: str,
                 store: ArtifactStore = Depends(get_store)):
        manifest = store.run_manifest(run_id)
        summary = store.run_summary(run_id)
        modules = manifest.get("modules", {}) or {}
        ranking = _safe(lambda: store.ranking_with_horizon(run_id, limit=25)) or []
        return templates.TemplateResponse(request, "run.html", {
            "nav": "runs", "title": f"Run {run_id}", "run_id": run_id,
            "manifest": manifest, "summary": summary,
            "modules": modules, "ranking": ranking,
            "lineage": {name: lineage_for_module(record) for name, record in modules.items()},
            "evidence_class": MODULE_EVIDENCE_CLASS,
        })

    @app.get("/compare", response_class=HTMLResponse)
    def page_compare(request: Request, a: str = Query(...), b: str = Query(...),
                     store: ArtifactStore = Depends(get_store)):
        left, right = store.run_manifest(a), store.run_manifest(b)
        cmp = store.compare_runs(a, b)
        rows = [{"module": r["module"], "left": r["a"], "right": r["b"]} for r in cmp["module_status"]]
        return templates.TemplateResponse(request, "compare.html", {
            "nav": "runs", "title": "Compare runs", "a": a, "b": b,
            "left": left, "right": right, "rows": rows, "comparable": cmp["comparable"], "cmp": cmp,
        })

    @app.get("/api/compare")
    def api_compare(a: str = Query(...), b: str = Query(...), store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        """Value-level comparison of two runs (same record the compare page renders); incomparability is explicit."""
        return {"schema_version": stamp("api"), **store.compare_runs(a, b)}

    @app.get("/prospective", response_class=HTMLResponse)
    def page_prospective(request: Request, store: ArtifactStore = Depends(get_store)):
        status = store.prospective_status()
        return templates.TemplateResponse(request, "prospective.html", {
            "nav": "prospective", "title": "Prospective Evaluation",
            "status": status, "enabled": status["overall_status"] == "READY",
        })

    @app.get("/scenario", response_class=HTMLResponse)
    def page_scenario(request: Request, store: ArtifactStore = Depends(get_store)):
        return templates.TemplateResponse(request, "scenario.html", {
            "nav": "scenario", "title": "Scenario Analysis",
            "runs": store.list_runs()[:5],
            "modules": [spec.name for spec in _module_specs()],
        })

    # ------------------------------------------------------------------- reports
    @app.get("/reports/object/{norad}", response_class=HTMLResponse)
    def report_object(request: Request, norad: int,
                      run_id: str | None = Query(default=None),
                      store: ArtifactStore = Depends(get_store)):
        document = reports.object_report(store, norad, run_id=run_id)
        return HTMLResponse(reports.render_html(document))

    @app.get("/api/reports/object/{norad}")
    def report_object_json(norad: int, run_id: str | None = Query(default=None),
                           redact: bool = Query(default=False),
                           store: ArtifactStore = Depends(get_store)) -> dict[str, Any]:
        document = reports.object_report(store, norad, run_id=run_id)
        return reports.redact(document, root=store.root) if redact else document

    @app.get("/reports/object/{norad}/download")
    def report_object_download(norad: int, run_id: str | None = Query(default=None),
                               redact: bool = Query(default=True),
                               store: ArtifactStore = Depends(get_store)) -> Response:
        document = reports.object_report(store, norad, run_id=run_id)
        if redact:                                         # exported files leave the machine: no hostname, no absolute paths
            document = reports.redact(document, root=store.root)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"cosmos_assessment_NORAD{norad}_{stamp}.html"
        return Response(
            content=reports.render_html(document),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app


# --------------------------------------------------------------------- internals
def _module_specs():
    from ..ai.adapters import default_modules
    return default_modules()


def _wants_json(request: Request) -> bool:
    if request.url.path.startswith("/api/"):
        return True
    return "application/json" in (request.headers.get("accept") or "")


def _safe(call):
    """Run an accessor, returning None when its data is simply absent.

    Used only for optional panels. A missing optional artifact must not take down a page, but
    it must also never be replaced by a placeholder value -- callers render an explicit
    "unavailable" state when this returns None.
    """
    try:
        return call()
    except (DataUnavailable, InvalidSelection):
        return None


def _run_json(summary) -> dict[str, Any]:
    return {
        "run_id": summary.run_id, "started_at": summary.started_at, "as_of": summary.as_of,
        "successful": summary.successful, "git_commit": summary.git_commit,
        "config_sha256": summary.config_sha256, "module_counts": summary.module_counts,
        "tables": list(summary.tables), "complete": summary.complete,
        "snapshot_consistent": summary.snapshot_consistent,
        "as_of_dates": list(summary.as_of_dates),
    }


#: Object classes of the catalogue's ``type1`` column, as the globe filter accepts them.
_GLOBE_CLASSES = {"P": "payload", "R": "rocket body", "C": "component", "D": "fragment"}
_GLOBE_SORTS = {"p_reentry_30d": ("p_30d", False), "perigee_km": ("perigee", True),
                "apogee_km": ("apogee", True), "inclination_deg": ("inc", True),
                "norad": ("norad", True)}


def _globe_rows(store: ArtifactStore, *, as_of: str, limit: int, regime: str, object_class: str,
                sort: str, include: str,
                only_included: bool = False) -> tuple[list[dict[str, Any]], list[int], int]:
    """Catalogue rows for the globe: the filtered selection plus any explicitly included NORAD ids.

    Reads the dated snapshot through the store and reshapes it; it computes nothing. Explicitly
    included objects (the demonstration set, or a deep link) are always returned even when a filter
    would exclude them, so a link to an object never silently shows nothing.
    """
    table = store.catalogue(as_of)
    total = int(len(table))

    wanted: list[int] = []
    for piece in (include or "").split(","):
        piece = piece.strip()
        if not piece:
            continue
        if not piece.isdigit():
            raise InvalidSelection(f"malformed NORAD id in include: {piece!r}")
        value = int(piece)
        if value not in wanted:
            wanted.append(value)
    if len(wanted) > 16:
        raise InvalidSelection("include accepts at most 16 NORAD ids")

    selected = table
    if regime:
        known = sorted(str(v) for v in table["regime"].dropna().unique())
        if regime not in known:
            raise InvalidSelection(f"unknown regime: {regime!r} (known: " + ", ".join(known) + ")")
        selected = selected[selected["regime"].astype(str) == regime]
    if object_class:
        code = object_class.strip().upper()
        if code not in _GLOBE_CLASSES:
            raise InvalidSelection(f"unknown object class: {object_class!r} (known: "
                                   + ", ".join(f"{k} = {v}" for k, v in _GLOBE_CLASSES.items()) + ")")
        selected = selected[selected["type1"].astype(str).str.upper() == code]

    column, ascending = _GLOBE_SORTS[sort]
    if only_included:
        selected = selected.iloc[0:0]
    else:
        selected = selected.sort_values(column, ascending=ascending, na_position="last").head(limit)
    if wanted:
        extra = table[table["norad"].isin(wanted) & ~table["norad"].isin(selected["norad"])]
        selected = pd.concat([selected, extra]) if len(extra) else selected

    def value(raw: Any) -> float | None:
        try:
            out = float(raw)
        except (TypeError, ValueError):
            return None
        return out if out == out and out not in (float("inf"), float("-inf")) else None

    rows = [{
        "norad": int(r.norad),
        "name": None if str(r.Name) in ("nan", "None", "") else str(r.Name),
        "object_class": None if str(r.type1) in ("nan", "None", "") else str(r.type1),
        "regime": None if str(r.regime) in ("nan", "None", "") else str(r.regime),
        "perigee_km": value(r.perigee),
        "apogee_km": value(r.apogee),
        "inclination_deg": value(r.inc),
        "p_reentry_30d": value(r.p_30d),
    } for r in selected.itertuples(index=False)]
    return rows, wanted, total


def _bands(series, edges: list[tuple[str, Any, Any]]) -> list[dict[str, Any]]:
    """Counts of a catalogue column inside named bands. Pure counting of archived values."""
    import math
    out = []
    values = [float(v) for v in series.tolist() if v == v and v is not None and math.isfinite(float(v))]
    total = len(values)
    for label, low, high in edges:
        n = sum(1 for v in values
                if (low is None or v > low) and (high is None or v <= high))
        out.append({"label": label, "count": n,
                    "share": (n / total) if total else None})
    return out


def _intelligence(store: ArtifactStore) -> dict[str, Any]:
    """Catalogue-wide lifetime and re-entry aggregates, counted from the archived snapshot columns.

    Every figure is a count or a sum over ``forecast_table.csv.gz``; nothing is modelled here. The
    run-derived ranking is labelled with its run id because a scenario run may cover a subset.
    """
    table = store.catalogue(DEFAULT_AS_OF)
    overview = store.catalogue_overview(DEFAULT_AS_OF)
    cap = 1826.25
    lifetime = table["median_days_lifetime"]
    reentry = table["median_days"]
    zero_width = int(((table["lo90_days"] - table["hi90_days"]).abs() < 1e-9).sum())
    at_cap = int((reentry >= cap - 1e-6).sum())
    coherent = table[["p_lifetime_30d", "p_lifetime_90d", "p_lifetime_1yr"]]
    monotone = (coherent["p_lifetime_30d"] <= coherent["p_lifetime_90d"]) & \
               (coherent["p_lifetime_90d"] <= coherent["p_lifetime_1yr"])
    has_all = coherent.notna().all(axis=1)
    incoherent = int((has_all & ~monotone).sum())
    run_id = store.latest_run_id()
    ranking = _safe(lambda: store.ranking_with_horizon(run_id, limit=25)) if run_id else None
    return {
        "as_of": DEFAULT_AS_OF,
        "overview": overview,
        "counts": {
            "objects": int(len(table)),
            "with_lifetime_estimate": int(lifetime.notna().sum()),
            "without_lifetime_estimate": int(lifetime.isna().sum()),
            "with_reentry_median": int(reentry.notna().sum()),
            "zero_width_interval": zero_width,
            "at_cap": at_cap,
            "incoherent_horizons": incoherent,
            "p30_above_half": overview["objects_p30d_above_half"],
            "expected_reentries_30d": overview["expected_reentries_30d"],
            "with_mass": overview["with_mass"],
        },
        "p30_bands": _bands(table["p_30d"], [("= 0", None, 0.0), ("0 to 0.01", 0.0, 0.01),
                                             ("0.01 to 0.1", 0.01, 0.1), ("0.1 to 0.5", 0.1, 0.5),
                                             ("0.5 to 0.9", 0.5, 0.9), ("above 0.9", 0.9, None)]),
        "lifetime_bands": _bands(lifetime, [("under 30 d", None, 30.0), ("30 to 90 d", 30.0, 90.0),
                                            ("90 to 365 d", 90.0, 365.0), ("1 to 5 years", 365.0, cap),
                                            ("at or beyond the cap", cap - 1e-6, None)]),
        "inclination_bands": _bands(table["inc"], [("under 30°", None, 30.0), ("30 to 60°", 30.0, 60.0),
                                                   ("60 to 90°", 60.0, 90.0), ("above 90° (retrograde)", 90.0, None)]),
        "ranking": ranking, "run_id": run_id,
        "subgroup": store.subgroup_coverage_evidence(),
        "cap_days": cap,
    }


def _decisions(store: ArtifactStore) -> dict[str, Any]:
    """The deployed ordering, its recorded rule, and the exploratory evidence about its usefulness."""
    run_id = store.latest_run_id()
    manifest = _safe(lambda: store.run_manifest(run_id)) if run_id else None
    module = ((manifest or {}).get("modules") or {}).get("decision_priority") or {}
    outputs = module.get("outputs") or {}
    ranking = _safe(lambda: store.ranking_with_horizon(run_id, limit=25)) if run_id else None
    t1 = store.ranking_utility_evidence()
    arms = None
    if t1:
        population = (t1.get("populations") or {}).get("x7_uncontrolled_natural_decay_with_history")
        horizon = (population or {}).get("y_30d") or {}
        arms = []
        for name, rows in (horizon.get("rankings") or {}).items():
            at = {int(r["k"]): r for r in rows}
            arms.append({"arm": name,
                         "precision": {k: (at.get(k) or {}).get("precision") for k in (10, 25, 50, 100)},
                         "hits_at_25": (at.get(25) or {}).get("hits"),
                         "high_consequence_at_25": (at.get(25) or {}).get("high_consequence_hits")})
        arms.sort(key=lambda a: (a["precision"].get(25) is None, -(a["precision"].get(25) or 0)))
        t1 = {**t1, "x7": horizon, "arms": arms}
    return {
        "run_id": run_id, "rule": outputs.get("priority_rule"),
        "consequence_mass_kg": outputs.get("consequence_mass_kg"),
        "health_escalation": outputs.get("health_escalation"),
        "ranking_rows": (outputs.get("ranking") or {}).get("rows"),
        "ranking": ranking, "t1": t1,
        "module_status": module.get("status"),
    }


def _evidence(store: ArtifactStore) -> dict[str, Any]:
    """Provenance and validation state: digests, lineage, twin integrity, readiness. All read, none computed."""
    run_id = store.latest_run_id()
    manifest = _safe(lambda: store.run_manifest(run_id)) if run_id else None
    lineage = []
    for name, record in ((manifest or {}).get("modules") or {}).items():
        lineage.append({"module": name, "status": record.get("status"),
                        "evidence_class": MODULE_EVIDENCE_CLASS.get(name),
                        "lineage": lineage_for_module(record),
                        "reason": record.get("reason") or record.get("error") or ""})
    lineage.sort(key=lambda item: item["module"])
    return {
        "readiness": _readiness(store),
        "catalogue": store.catalogue_provenance(DEFAULT_AS_OF),
        "repository": store.repository_provenance(),
        "twin": _safe(lambda: store.twin_state_integration(DEFAULT_AS_OF, DEFAULT_TWIN_SOURCE_POLICY, run_id)),
        "datasets": _datasets(store),
        "run_id": run_id, "manifest": manifest, "lineage": lineage,
        "schema_versions": _schema.CURRENT,
        "globe_basis": geometry.geometry_basis(),
    }


def _p30_bands(store: ArtifactStore) -> list[dict[str, Any]]:
    """Objects per reported 30-day probability band. A count of archived values, cached by the store."""
    table = store.catalogue(DEFAULT_AS_OF)
    return _bands(table["p_30d"], [("= 0", None, 0.0), ("0–0.01", 0.0, 0.01), ("0.01–0.1", 0.01, 0.1),
                                   ("0.1–0.5", 0.1, 0.5), ("0.5–0.9", 0.5, 0.9), ("> 0.9", 0.9, None)])


def _timeline(store: ArtifactStore) -> list[dict[str, Any]]:
    """Mission activity: dated facts of the archive and the run history. No event is invented.

    Entries are the catalogue snapshot date, the T1 window the exploratory evaluation used, the
    prospective-evaluation block and the most recent pipeline runs with their outcome.
    """
    items: list[dict[str, Any]] = []
    for summary in store.list_runs()[:6]:
        started = (summary.started_at or "")[:19].replace("T", " ")
        ok = summary.successful
        items.append({
            "when": started or summary.run_id,
            "what": ("pipeline run completed" if ok else "pipeline run incomplete"),
            "note": f"{summary.run_id} · {sum((summary.module_counts or {}).values())} modules",
            "tone": "" if ok else "warn",
        })
    items.append({"when": DEFAULT_AS_OF, "what": "catalogue snapshot and dated forecast",
                  "note": "every object value on this console is read from this archive", "tone": "violet"})
    items.append({"when": "2026-08-16 to 2026-10-27", "what": "T1 window used by the exploratory ranking evaluation",
                  "note": "non-blind: the outcomes were analysed before the evaluation was declared", "tone": "warn"})
    items.append({"when": "pending", "what": "prospective (blind) evaluation",
                  "note": "blocked until a catalogue snapshot dated on or after 2026-11-26 exists", "tone": "muted"})
    return items


def _mission_bar(store: ArtifactStore) -> dict[str, Any]:
    """The one-line mission status strip shown on every page by ``base.html``.

    Only facts: the snapshot date, whether the console's own artifacts are ready, the catalogue
    size, the latest run and the selected twin-state source. It says nothing about any spacecraft
    and nothing about live data, because there is none.
    """
    readiness = _readiness(store)
    checks = readiness.get("checks") or {}
    twin = checks.get("twin_state_source") or {}
    latest = readiness.get("latest_run") or {}
    return {
        "as_of": DEFAULT_AS_OF,
        "ready": bool(readiness.get("ready")),
        "objects": f"{len(store.catalogue(DEFAULT_AS_OF)):,}",
        "run_id": latest.get("run_id") if isinstance(latest, dict) else None,
        "twin_source": twin.get("selected"),
        "api_schema": (readiness.get("schema_versions") or {}).get("api") or stamp("api"),
        "live": False,
    }


def _datasets(store: ArtifactStore) -> dict[str, Any]:
    """Datasets the console can actually read, each with its availability stated."""
    catalogue = _safe(store.catalogue_provenance)
    missions = store.missions()
    debris = store.debris_available()                  # presence only: never parse the detections for a listing
    collision = _safe(lambda: store.collision_events(limit=1))
    arms = _safe(lambda: store.health_arms())
    return {"schema_version": stamp("api"), "evidence_policy": {
                "served": "archived real-data evaluations and the dated catalogue snapshot only",
                "synthetic_demonstration_data": ("not served by this console: the simulator telemetry and "
                                                 "rendered imagery of the legacy demonstration chain are "
                                                 "never mixed with real-data evidence"),
                "live_sources": "none connected; nothing here is real-time"},
            "datasets": [
        {"key": "catalogue", "label": "CelesTrak SATCAT + GCAT snapshot", "evidence_class": "archived real-data snapshot",
         "available": catalogue is not None,
         "records": catalogue["objects"] if catalogue else None,
         "identity": "NORAD ID", "detail": catalogue["artifact"] if catalogue else
         "snapshot not present"},
        {"key": "telemetry", "evidence_class": "archived real-data benchmark (anonymised)", "label": "ESA-ADB telemetry (anonymised)",
         "available": bool(missions),
         "records": sum(m["samples"] for m in missions) if missions else None,
         "identity": "mission + channel (not NORAD)",
         "detail": f"{len(missions)} mission(s) prepared" if missions else "not present"},
        {"key": "debris", "evidence_class": "archived real-data benchmark", "label": "SpotGEO imagery + detections",
         "available": debris["available"],
         "records": None, "identity": "sequence + frame",
         "detail": "test split with saved detections" if debris["available"] else "not present"},
        {"key": "conjunction", "evidence_class": "archived real-data benchmark (anonymised)", "label": "ESA Kelvins CAC (anonymised CDMs)",
         "available": collision is not None,
         "records": collision["events_total"] if collision else None,
         "identity": "positional event index (anonymised)",
         "detail": "held-out split predictions" if collision else "not present"},
        {"key": "health_benchmark", "evidence_class": "archived benchmark-arm scores (not a spacecraft health state)", "label": "ESA-ADB benchmark arms",
         "available": arms is not None,
         "records": int(len(arms)) if arms is not None else None,
         "identity": "benchmark arm (not a spacecraft)",
         "detail": "saved arm metrics" if arms is not None else "not present"},
    ]}


DEMO_OBJECTS = (
    (37607, "primary example: design-derived A/M, natural decay, re-entry before the horizon, lifetime crosses it"),
    (23806, "L17 example: class-prior fragment whose lifetime record is one of the 123 non-coherent ones → abstention"),
    (25544, "operator-controlled example: re-entry abstention with the base rate, no quantiles, no interval"),
    (12, "at-cap example: re-entry quantiles censored at the 1826.25-day cap; lifetime entirely after the horizon"),
)


def _demo_context(store: ArtifactStore) -> dict[str, Any]:
    """Live facts for the guided demonstration; every value is read from the stored outputs, nothing is computed."""
    readiness = _readiness(store)
    overview = _overview(store)
    latest = overview.get("latest_run") or {}
    run_id = latest.get("run_id") if isinstance(latest, dict) else None
    objects = []
    for norad, why in DEMO_OBJECTS:
        rec = _safe(lambda n=norad: store.object_record(n))
        if rec is None:
            objects.append({"norad": norad, "why": why, "available": False})
            continue
        lt, re_, dp, tw = rec["lifetime"], rec["reentry"], rec["decision_priority"], rec["twin_state"]
        objects.append({
            "norad": norad, "why": why, "available": True, "name": rec["name"], "regime": rec["regime"],
            "object_class": rec.get("object_class_label") or rec.get("object_class"),
            "p30": (re_.get("probability_by_horizon") or {}).get("30d"),
            "reentry_relation": (re_.get("horizon_relation") or {}).get("relation"),
            "reentry_status": re_.get("evidence_status"),
            "lifetime_available": lt.get("available"), "lifetime_coherence": (lt.get("horizon_coherence") or {}).get("status"),
            "lifetime_median": lt.get("median_days"), "lifetime_relation": (lt.get("horizon_relation") or {}).get("relation"),
            "subgroup": (lt.get("subgroup_coverage") or {}).get("status"),
            "rank": dp.get("rank"), "ranked_objects": dp.get("ranked_objects"), "priority_score": (dp.get("row") or {}).get("priority_score"),
            "twin_source": tw.get("source"), "twin_equivalence": (tw.get("equivalence") or {}).get("status"),
            "twin_not_comparable": list(((tw.get("equivalence") or {}).get("not_comparable") or {}).keys()),
            "availability": {x["capability"]: x["status"] for x in rec["evidence_availability"]},
        })
    twin = _safe(lambda: store.twin_state_integration()) if readiness["checks"]["twin_state_source"]["selected"] else None
    missions = _safe(store.missions) or []
    arms = _safe(store.health_arms)
    collision = _safe(lambda: store.collision_events(limit=1))
    debris = store.debris_available()
    vision = _safe(store.vision_benchmark_arms) or []
    runs = store.list_runs()
    manifest = _safe(lambda: store.run_manifest(run_id)) if run_id else None
    modules = {k: v.get("status") for k, v in ((manifest or {}).get("modules") or {}).items()}
    return {
        "readiness": readiness, "overview": overview, "run_id": run_id, "modules": modules, "runs_total": len(runs),
        "objects": objects, "twin": twin, "missions": missions, "health_arms": int(len(arms)) if arms is not None else None,
        "collision": collision, "debris": debris, "vision": vision,
        "tables": (manifest or {}).get("tables_written") or [], "datasets": _datasets(store),
        "prospective": overview.get("prospective"),
    }


def _readiness(store: ArtifactStore) -> dict[str, Any]:
    """The console's readiness record: one implementation for GET /api/ready and the overview panel.

    ``ready`` is true when the forecast table is present and the dated-forecast digest verifies (or no digest is
    recorded). Everything else is informational. Nothing here describes a spacecraft.
    """
    checks: dict[str, Any] = {}
    checks["forecast_table_present"] = (store.root / TWIN_SNAPSHOT.format(as_of=DEFAULT_AS_OF)).is_file()
    try:
        prov = store.repository_provenance()
        checks["dated_forecast_digest_state"] = prov.get("dated_forecast_digest_state")
        checks["git_commit"] = prov.get("git_commit")
    except Exception as exc:  # readiness must never raise
        checks["dated_forecast_digest_state"] = f"error: {type(exc).__name__}"
        checks["git_commit"] = None
    latest = None
    try:
        latest = store.latest_run_id()
    except Exception as exc:
        checks["runs_error"] = type(exc).__name__
    checks["complete_run_present"] = latest is not None
    checks["twin_state_reemitted_present"] = (store.root / TWIN_STATE_REEMITTED.format(as_of=DEFAULT_AS_OF)).is_file()
    try:
        sel = store.twin_selection(DEFAULT_AS_OF, DEFAULT_TWIN_SOURCE_POLICY)
        checks["twin_state_source"] = {"selected": sel["selected"], "status": sel["status"], "policy": sel["policy"]}
    except Exception as exc:  # informational only
        checks["twin_state_source"] = {"selected": None, "status": f"error: {type(exc).__name__}", "policy": DEFAULT_TWIN_SOURCE_POLICY}
    ready = bool(checks["forecast_table_present"] and checks["dated_forecast_digest_state"] in ("verified", "absent"))
    failing = [k for k, ok in (("forecast_table_present", checks["forecast_table_present"]),
                               ("dated_forecast_digest_state", checks["dated_forecast_digest_state"] in ("verified", "absent"))) if not ok]
    warnings = []
    if not checks["complete_run_present"]:
        warnings.append("no complete pipeline run is present: object priorities and run views are unavailable until one is produced")
    if not checks["twin_state_reemitted_present"]:
        warnings.append("the re-emitted twin state is absent: twin-state reads fall back to the historical archive and are labelled")
    tw = checks["twin_state_source"]
    if tw.get("status") in ("fallback", "explicit_archived"):
        warnings.append(f"twin-state source is the historical archive ({tw.get('status')}); records carry no per-output provenance")
    elif tw.get("status") == "unavailable" or str(tw.get("status", "")).startswith("error"):
        warnings.append("no twin-state source is selectable")
    return {"ready": ready, "schema_version": stamp("api"), "checks": checks, "failing_checks": failing, "warnings": warnings,
            "latest_run": latest, "schema_versions": dict(_schema.CURRENT), "cache": store.cache_stats(),
            "note": "readiness of the read-only evidence console; it says nothing about any spacecraft"}


def _overview(store: ArtifactStore) -> dict[str, Any]:
    runs = store.list_runs()
    latest = next((r for r in runs if r.complete), None)
    overview: dict[str, Any] = {
        "schema_version": stamp("api"),
        "module_evidence_class": dict(MODULE_EVIDENCE_CLASS),
        "catalogue": _safe(store.catalogue_overview),
        "repository": store.repository_provenance(),
        "runs_total": len(runs),
        "runs_recent": [_run_json(r) for r in runs[:5]],
        "latest_run": _run_json(latest) if latest else None,
        "prospective": store.prospective_status()["overall_status"],
        "findings": [],
        "abstentions": {},
        "module_status": {},
    }
    # Stale-data warning: every number on the console refers to the snapshot date, which is fixed
    # (2026-10-27); the console does not ingest later snapshots, so its age must be stated, not implied.
    as_of = (overview["catalogue"] or {}).get("as_of") or DEFAULT_AS_OF
    today = datetime.now(timezone.utc).date()
    age_days = (today - datetime.fromisoformat(as_of).date()).days
    overview["snapshot_age"] = {"as_of": as_of, "evaluated_on_utc": today.isoformat(),
                                "age_days": age_days, "stale": age_days > 0}
    if age_days > 0:
        overview["findings"].append({
            "level": "STALE",
            "text": (f"The catalogue snapshot is dated {as_of}, {age_days} days before today ({today}). "
                     "Every probability on this console refers to that date; nothing here is a current "
                     "forecast, and no later snapshot has been ingested."),
        })
    if latest is None:
        overview["findings"].append({
            "level": "INFO",
            "text": "No pipeline run is present. Start one from Scenario Analysis.",
        })
        return overview

    manifest = _safe(lambda: store.run_manifest(latest.run_id)) or {}
    modules = manifest.get("modules", {}) or {}
    overview["module_status"] = {name: record.get("status") for name, record in modules.items()}
    for name, record in modules.items():
        if record.get("abstentions"):
            overview["abstentions"][name] = record["abstentions"]

    lifetime = modules.get("lifetime", {})
    if isinstance(lifetime.get("noncoherent_horizon_probabilities"), int) and \
            lifetime["noncoherent_horizon_probabilities"] > 0:
        overview["findings"].append({
            "level": "ABSTAIN",
            "text": (f"{lifetime['noncoherent_horizon_probabilities']} object(s) excluded from "
                     "lifetime results: saved per-horizon calibrated probabilities are not "
                     "monotone across horizons (limitation L17). The twin's final reported "
                     "forecast is unaffected."),
        })
    decision = modules.get("decision_priority", {})
    escalation = decision.get("health_escalation")
    if isinstance(escalation, dict) and escalation.get("status") == "abstain":
        overview["findings"].append({"level": "ABSTAIN",
                                     "text": f"Coupling C4 abstained: {escalation.get('reason')}"})
    failed = [name for name, record in modules.items()
              if record.get("status") in {"failed", "blocked"}]
    if failed:
        overview["findings"].append({
            "level": "FAIL",
            "text": f"Modules not completed in the latest run: {', '.join(sorted(failed))}.",
        })
    if not latest.snapshot_consistent:
        overview["findings"].append({
            "level": "FAIL",
            "text": ("The latest run mixes snapshots "
                     f"({', '.join(latest.as_of_dates)}); it is not a single coherent snapshot."),
        })
    if overview["prospective"] != "READY":
        overview["findings"].append({
            "level": "BLOCKED",
            "text": ("Prospective evaluation of the dated 2026-10-27 forecast is blocked: no "
                     "qualifying later outcome snapshot is available."),
        })
    if overview["repository"].get("dated_forecast_digest_state") == "MISMATCH":
        overview["findings"].append({
            "level": "FAIL",
            "text": "The hashed dated forecast no longer matches its recorded digest.",
        })
    return overview


def _execute_scenario(root: Path, store: ArtifactStore,
                      request: ScenarioRequest) -> dict[str, Any]:
    """Run the supported pipeline into a NEW run directory.

    Execution is delegated to ``scripts/run_pipeline.py``'s ``main`` so that a console run and
    a command-line run produce identical artifacts. The output directory is chosen here and
    is guaranteed not to exist, so no historical run can be overwritten.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"run_{stamp}"
    out = root / "outputs" / "pipeline" / run_id
    if out.exists():
        raise HTTPException(status_code=409, detail="generated run directory already exists")

    argv = ["--as-of", request.as_of, "--out", str(out),
            "--collision-model", request.collision_model, "--twin-source-policy", request.twin_source_policy]
    if request.limit is not None:
        argv += ["--limit", str(request.limit)]
    if request.collision_limit is not None:
        argv += ["--collision-limit", str(request.collision_limit)]
    if request.debris_sequence_limit is not None:
        argv += ["--debris-sequence-limit", str(request.debris_sequence_limit)]
    if request.health_calibrator:
        argv += ["--health-calibrator", request.health_calibrator]
    if request.modules:
        allowed = {spec.name for spec in _module_specs()}
        unknown = sorted(set(request.modules) - allowed)
        if unknown:
            raise HTTPException(status_code=400,
                                detail=f"unknown modules: {', '.join(unknown)}")
        argv += ["--select", *request.modules]

    # The pipeline runs in a child process with exactly the command-line arguments a terminal run would use, so the
    # console's own memory is not inflated by the run (a full in-process run reached 1.1 GB RSS in rehearsal) and a
    # crash in the pipeline cannot take the server down. Output is captured and only its tail is reported.
    import subprocess
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_pipeline.py"), *argv], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=900)
    exit_code = proc.returncode
    manifest = _safe(lambda: store.run_manifest(run_id))
    return {
        "mode": "scenario",
        "run_id": run_id,
        "exit_code": exit_code,
        "successful": bool(manifest and manifest.get("successful")),
        "partial": exit_code != 0,
        "run_url": f"/runs/{run_id}",
        "manifest": manifest,
        "config": (manifest or {}).get("config"),
        "config_sha256": (manifest or {}).get("config_sha256"),
        "assumptions": _scenario_assumptions(request),
        "process": {"isolated": True, "exit_code": exit_code,
                    "stderr_tail": (proc.stderr or "")[-600:] if exit_code != 0 else ""},
        "note": ("a scenario run re-expresses saved artifacts through the shared contracts; it "
                 "does not retrain, rescore or revalidate any scientific result"),
    }


# -------------------------------------------------------------- template filters
def _format_number(value: Any, digits: int = 3) -> str:
    """Render a number, or an explicit dash for an absent one. Never prints 0 for None."""
    if value is None or value == "":
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if number != number:                      # NaN
        return "—"
    if number == int(number) and abs(number) < 1e15:
        return f"{int(number):,}"
    if abs(number) < 1e-4 or abs(number) >= 1e6:
        return f"{number:.3e}"
    return f"{number:,.{digits}f}"


def _format_percent(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


app = create_app()
