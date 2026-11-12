"""P0.4 — the documented launch path is checkable and truthful."""
from __future__ import annotations

from pathlib import Path

from cosmos.ai.provenance import ROOT


def test_prerequisite_checker_separates_required_optional_and_backends():
    from scripts.check_console_prerequisites import collect, REQUIRED_PACKAGES, OPTIONAL_BACKENDS
    r = collect(ROOT)
    assert set(r["required_packages"]) == set(REQUIRED_PACKAGES)
    assert set(r["optional_backends"]) == set(OPTIONAL_BACKENDS)
    assert all(v["needed_to_serve_console"] is False for v in r["optional_backends"].values())
    assert set(r["required_artifacts"]) == {"forecast table", "forecast digest file"}
    assert r["expected_url"] == "http://127.0.0.1:8070/" and "serve_console.py" in r["launch_command"]
    assert "nothing is real-time" in r["no_live_sources"]
    # launchability depends only on the required class
    required_ok = r["python"]["ok"] and all(v["present"] for v in r["required_packages"].values()) and all(v["present"] for v in r["required_artifacts"].values())
    assert r["launchable"] is required_ok


def test_launch_document_names_the_command_url_and_troubleshooting():
    doc = (ROOT / "docs/product/CONSOLE_LAUNCH.md").read_text()
    for needle in ("python scripts/check_console_prerequisites.py", "python scripts/serve_console.py", "http://127.0.0.1:8070/",
                   "Required", "Optional artifacts", "Optional backends", "never needed to serve the console", "Do not install them silently",
                   "## 4. Troubleshooting", "runs no model at request time"):
        assert needle in doc, needle
    guide = (ROOT / "docs/product/PRODUCT_USER_GUIDE.md").read_text()
    assert "check_console_prerequisites.py" in guide and "CONSOLE_LAUNCH.md" in guide


def test_serve_console_defaults_match_the_documented_url():
    text = (ROOT / "scripts/serve_console.py").read_text()
    assert 'default="127.0.0.1"' in text and "default=8070" in text
