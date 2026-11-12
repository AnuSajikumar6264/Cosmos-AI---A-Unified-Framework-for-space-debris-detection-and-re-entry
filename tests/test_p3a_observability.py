"""P3-A3 — readiness, structured logging, traceback-free errors, report redaction, diagnostics."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai import schema
from cosmos.ai.provenance import ROOT
from cosmos.product import reports
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.logging_setup import APP_LOGGER, REQUEST_LOGGER, configure_logging
from cosmos.product.store import ArtifactStore

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")


@pytest.fixture()
def logbuf():
    buf = io.StringIO()
    handler = configure_logging(json_lines=True, level="info", stream=buf)
    yield buf
    for name in ("cosmos", REQUEST_LOGGER, APP_LOGGER):
        logging.getLogger(name).removeHandler(handler)


# ------------------------------------------------------------------ readiness
@needs_snapshot
def test_ready_is_200_on_the_real_root_and_names_no_absolute_path():
    r = TestClient(create_app(ROOT)).get("/api/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["checks"]["forecast_table_present"] and body["checks"]["dated_forecast_digest_state"] == "verified"
    assert body["schema_versions"]["run_manifest"] == "1.2" and body["schema_version"] == schema.stamp("api")
    assert str(ROOT) not in r.text and socket.gethostname() not in r.text
    assert "spacecraft" in body["note"]


def test_ready_is_503_on_an_empty_root(tmp_path):
    r = TestClient(create_app(tmp_path)).get("/api/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["ready"] is False and body["checks"]["forecast_table_present"] is False
    assert body["checks"]["complete_run_present"] is False


def test_ready_is_503_when_the_dated_digest_mismatches(tmp_path):
    d = tmp_path / "outputs/twin/as_of_2026-10-27"; d.mkdir(parents=True)
    (d / "forecast_table.csv.gz").write_bytes(b"not the archived table")
    (tmp_path / S.FORECAST_DIGEST).write_text("0" * 64 + " forecast_table.csv.gz\n")
    r = TestClient(create_app(tmp_path)).get("/api/ready")
    assert r.status_code == 503 and r.json()["checks"]["dated_forecast_digest_state"] == "MISMATCH"


# ------------------------------------------------------------------ structured logs and request ids
def test_each_request_gets_an_id_and_one_structured_log_line(logbuf, tmp_path):
    c = TestClient(create_app(tmp_path))
    r = c.get("/api/health")
    assert r.status_code == 200 and re.fullmatch(r"[0-9a-f]{16}", r.headers["x-request-id"])
    r2 = c.get("/api/health", headers={"X-Request-ID": "client-supplied-id"})
    assert r2.headers["x-request-id"] == "client-supplied-id"
    lines = [json.loads(l) for l in logbuf.getvalue().splitlines()]
    reqs = [l for l in lines if l["logger"] == REQUEST_LOGGER]
    assert len(reqs) == 2
    for l in reqs:
        assert set(l) >= {"ts", "level", "logger", "event", "request_id", "method", "path", "status", "duration_ms"}
        assert l["method"] == "GET" and l["path"] == "/api/health" and l["status"] == 200
    assert reqs[1]["request_id"] == "client-supplied-id"


# ------------------------------------------------------------------ generic 500 without traceback
@needs_snapshot
def test_unexpected_errors_return_a_generic_500_and_log_the_traceback_server_side(logbuf, monkeypatch):
    def boom(self, *a, **k):
        raise RuntimeError("secret-internal-detail /very/private/path")
    monkeypatch.setattr(ArtifactStore, "object_record", boom)
    c = TestClient(create_app(ROOT), raise_server_exceptions=False)
    r = c.get("/api/objects/37607")
    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal" and re.fullmatch(r"[0-9a-f]{16}", body["request_id"])
    assert "secret-internal-detail" not in r.text and "Traceback" not in r.text and "/very/private" not in r.text
    h = c.get("/objects/37607", headers={"accept": "text/html"})
    assert h.status_code == 500 and "secret-internal-detail" not in h.text and "Traceback" not in h.text
    assert body["request_id"] in r.text
    # the id is also a response header on both 500 forms (P3-A final validation, 2026-11-08)
    assert r.headers["x-request-id"] == body["request_id"]
    assert re.fullmatch(r"[0-9a-f]{16}", h.headers["x-request-id"]) and h.headers["x-request-id"] in h.text
    errs = [json.loads(l) for l in logbuf.getvalue().splitlines() if '"ERROR"' in l]
    app_errs = [l for l in errs if l["logger"] == APP_LOGGER]
    assert app_errs and "secret-internal-detail" in app_errs[0]["traceback"] and app_errs[0]["error_type"] == "RuntimeError"
    assert app_errs[0]["request_id"] == body["request_id"]


@needs_snapshot
def test_request_id_header_on_success_on_unexpected_error_and_on_not_ready(monkeypatch, tmp_path):
    ok = TestClient(create_app(ROOT)).get("/api/overview")
    assert ok.status_code == 200 and re.fullmatch(r"[0-9a-f]{16}", ok.headers["x-request-id"])
    echoed = TestClient(create_app(ROOT)).get("/api/overview", headers={"X-Request-ID": "trace-123"})
    assert echoed.headers["x-request-id"] == "trace-123"

    def boom(self, *a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(ArtifactStore, "object_record", boom)
    err = TestClient(create_app(ROOT), raise_server_exceptions=False).get("/api/objects/37607", headers={"X-Request-ID": "trace-500"})
    assert err.status_code == 500 and err.headers["x-request-id"] == "trace-500" == err.json()["request_id"]
    assert "boom" not in err.text and "Traceback" not in err.text
    not_ready = TestClient(create_app(tmp_path)).get("/api/ready")
    assert not_ready.status_code == 503 and re.fullmatch(r"[0-9a-f]{16}", not_ready.headers["x-request-id"])


def test_known_errors_keep_their_specific_status_codes(tmp_path):
    c = TestClient(create_app(tmp_path))
    assert c.get("/api/objects/37607").status_code == 404           # DataUnavailable, not 500
    assert c.get("/api/runs/not..a..run").status_code in (400, 404)  # InvalidSelection or absent


# ------------------------------------------------------------------ report redaction
def test_redact_removes_path_and_host_but_keeps_every_hash_and_commit():
    sha = hashlib.sha256(b"x").hexdigest()
    doc = {"provenance": {"repository": str(ROOT), "git_commit": "78ee33962007203bcfc829fc743a663b350373e1",
                          "forecast_table_sha256": sha, "config_sha256": sha},
           "environment": {"host": socket.gethostname(), "note": f"copied from {ROOT}/outputs"},
           "values": [{"p": 0.1, "path": f"{ROOT}/x.csv"}], "run_id": "run_20261108T072802Z"}
    red = reports.redact(doc, root=ROOT)
    text = json.dumps(red)
    assert str(ROOT) not in text and socket.gethostname() not in text
    assert red["provenance"]["git_commit"] == doc["provenance"]["git_commit"]
    assert red["provenance"]["forecast_table_sha256"] == sha and red["provenance"]["config_sha256"] == sha
    assert red["run_id"] == doc["run_id"] and red["values"][0]["p"] == 0.1
    assert red["redaction"]["applied"] is True
    assert {"provenance.repository", "environment.host", "environment.note", "values[].path"} <= set(red["redaction"]["redacted_fields"])
    assert doc["provenance"]["repository"] == str(ROOT)              # input not mutated


@needs_snapshot
def test_download_is_redacted_by_default_and_api_report_is_not():
    c = TestClient(create_app(ROOT))
    dl = c.get("/reports/object/37607/download")
    assert dl.status_code == 200 and "attachment" in dl.headers["content-disposition"]
    assert str(ROOT) not in dl.text and socket.gethostname() not in dl.text and "Redacted export" in dl.text
    raw = c.get("/reports/object/37607/download?redact=false").text
    assert "Redacted export" not in raw                              # the unredacted form is still available on request
    full = c.get("/api/reports/object/37607").json()
    assert full["provenance"]["repository"] == str(ROOT)             # the JSON document is where the path lives
    red = c.get("/api/reports/object/37607?redact=true").json()
    assert "redaction" not in full and red["redaction"]["applied"]
    hashes = lambda d: sorted(set(re.findall(r"\b[0-9a-f]{40,64}\b", json.dumps(d))))
    assert hashes(full) == hashes(red) and len(hashes(full)) >= 3
    assert red["provenance"]["repository"] == "<repository root (redacted)>"
    assert full["provenance"]["git_commit"] == red["provenance"]["git_commit"]


# ------------------------------------------------------------------ launch flags and diagnostics
def test_serve_console_exposes_the_json_log_flag():
    out = subprocess.run([sys.executable, "scripts/serve_console.py", "--help"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0 and "--log-json" in out.stdout


def test_diagnose_script_imports_and_declares_its_output():
    text = (ROOT / "scripts/diagnose_console.py").read_text()
    assert "console_diagnostics_" in text and "/api/ready" in text
    compile(text, "diagnose_console.py", "exec")
