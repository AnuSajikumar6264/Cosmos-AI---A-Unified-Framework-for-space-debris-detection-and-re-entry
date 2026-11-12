"""COSMOS-AI Mission Intelligence Console.

A read-mostly product layer over the existing scientific code. It adds no scientific engine:
every number it shows comes from ``cosmos.ai.adapters``, ``cosmos.ai.orchestration`` or a
saved artifact on disk.

Modules:

``store``      read-only accessors over artifacts, with explicit unavailability
``charts``     server-side SVG rendered from real arrays only
``reports``    assessment report generation with full provenance
``api``        FastAPI application and HTTP routes
"""
from __future__ import annotations

__all__ = ["store", "charts", "reports", "api"]
