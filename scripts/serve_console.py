"""Start the COSMOS-AI Mission Intelligence Console.

    python scripts/serve_console.py                      # http://127.0.0.1:8070
    python scripts/serve_console.py --port 9000
    python scripts/serve_console.py --host 0.0.0.0       # reachable from another machine
    python scripts/serve_console.py --reload             # auto-reload while developing

The console reads saved artifacts and can execute the supported pipeline into a **new**
versioned run directory. It never modifies or overwrites an existing run, never writes to any
dataset, and contains no scientific engine of its own.

The default host is loopback, so the console is not exposed to the network unless asked. It
has no authentication: only pass ``--host 0.0.0.0`` on a trusted network.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8070)
    parser.add_argument("--root", default=None, help="repository root (default: this repo)")
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes")
    parser.add_argument("--log-level", default="info",
                        choices=["critical", "error", "warning", "info", "debug"])
    parser.add_argument("--log-json", action="store_true",
                        help="structured JSON-lines logs (request id, method, path, status, duration; no payloads)")
    args = parser.parse_args(argv)
    if args.log_json:
        from cosmos.product.logging_setup import configure_logging
        configure_logging(json_lines=True, level=args.log_level)

    import uvicorn

    if args.reload:
        # Reload needs an import string rather than an application object.
        if args.root:
            os.environ["COSMOS_CONSOLE_ROOT"] = args.root
        uvicorn.run("cosmos.product.api:app", host=args.host, port=args.port,
                    reload=True, log_level=args.log_level)
        return 0

    from cosmos.product.api import create_app
    from cosmos.ai.provenance import ROOT

    root = args.root or os.environ.get("COSMOS_CONSOLE_ROOT") or ROOT
    app = create_app(root)

    print("COSMOS-AI Mission Intelligence Console")
    print(f"  repository : {root}")
    print(f"  console    : http://{args.host}:{args.port}/")
    print(f"  API docs   : http://{args.host}:{args.port}/docs")
    print("  modes      : historical (read) · scenario (new run) · prospective (blocked)")
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
