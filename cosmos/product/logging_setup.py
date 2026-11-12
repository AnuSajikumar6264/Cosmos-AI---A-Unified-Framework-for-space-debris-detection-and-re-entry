"""Structured (JSON-lines) logging for the console and the pipeline (P3-A3, 2026-11-08).

    from cosmos.product.logging_setup import configure_logging
    configure_logging(json_lines=True, level="info")

One record per line with fixed fields: ``ts``, ``level``, ``logger``, ``event`` (the message) and any
structured extras passed as ``extra={"fields": {...}}``. Request logs carry ``request_id``, ``method``,
``path``, ``status`` and ``duration_ms`` — never request bodies, response payloads or query values.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

REQUEST_LOGGER = "cosmos.product.request"
APP_LOGGER = "cosmos.product.app"


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
                   "level": record.levelname, "logger": record.name, "event": record.getMessage()}
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update({k: v for k, v in fields.items() if k not in payload})
        if record.exc_info and record.levelno >= logging.ERROR:
            # the traceback stays in the server log only; responses never carry it
            payload["exception"] = self.formatException(record.exc_info).splitlines()[-1]
        return json.dumps(payload, default=str)


def configure_logging(json_lines: bool = True, level: str = "info", stream=None) -> logging.Handler:
    """Install one handler on the cosmos loggers; returns it so tests can attach to it."""
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonLineFormatter() if json_lines else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    for name in ("cosmos", REQUEST_LOGGER, APP_LOGGER):
        logger = logging.getLogger(name)
        logger.handlers = [h for h in logger.handlers if not getattr(h, "_cosmos_structured", False)]
        handler._cosmos_structured = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.propagate = False
    return handler


def log_fields(logger: logging.Logger, level: int, event: str, **fields) -> None:
    logger.log(level, event, extra={"fields": fields})
