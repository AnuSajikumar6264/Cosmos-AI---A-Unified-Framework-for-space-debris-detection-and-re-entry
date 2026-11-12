"""P0.3 — scientific wording: K8 qualified, read-only evidence twin stated, archived vs synthetic distinct."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cosmos.ai import registry
from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.api import create_app

SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)
needs_snapshot = pytest.mark.skipif(not SNAPSHOT.is_file(), reason="snapshot absent")
UNQUALIFIED = re.compile(r"(late[- ]fusion|fusion)\s+(improves|contributes|provides|delivers)", re.I)


def test_registry_cards_make_no_unqualified_fusion_claim_and_qualify_the_hybrid_card():
    cards = registry.cards()
    texts = {c.name: " ".join([c.task, c.inputs, c.outputs, c.uncertainty, *c.limitations]) for c in cards}
    for name, text in texts.items():
        assert not UNQUALIFIED.search(text), (name, UNQUALIFIED.search(text).group(0))
    hybrid = next(c for c in cards if c.name == "opssat_hybrid")
    joined = " ".join(hybrid.limitations)
    assert "NOT better calibrated than the feature-MLP branch" in joined
    assert "not reproduced" in joined and "No calibration or stability contribution of the fusion" in joined
    for name in ("opssat_hybrid", "opssat_cnn", "opssat_fcnn", "opssat_xgboost"):
        card = next(c for c in cards if c.name == name)
        assert any("not a spacecraft health assessment" in lim for lim in card.limitations), name


def test_console_text_has_no_live_or_integrated_health_claims():
    root = ROOT / "cosmos/product/templates"
    # positive claims only: a negated sentence ("No live telemetry feed is connected") is the truthful one
    forbidden = re.compile(r"((?<!No )(?<!no )live telemetry feed is connected|real-time inference|integrated satellite health assessment is|predictions? (are|is) computed live)", re.I)
    for tpl in root.glob("*.html"):
        text = tpl.read_text()
        assert not forbidden.search(text), (tpl.name, forbidden.search(text).group(0))


@needs_snapshot
def test_overview_states_read_only_evidence_twin_and_distinguishes_synthetic_data():
    client = TestClient(create_app(ROOT))
    page = client.get("/").text
    assert "read-only evidence twin" in page and "no model runs at prediction time" in page
    assert "synthetic demonstration data" in page and "never mixed with real-data evidence" in page
    assert "independent benchmark roots" in page and "not combined into a satellite health assessment" in page
    ds = client.get("/api/datasets").json()
    assert all(d.get("evidence_class", "").startswith("archived") for d in ds["datasets"])
    assert "not served by this console" in ds["evidence_policy"]["synthetic_demonstration_data"]
    assert "none connected" in ds["evidence_policy"]["live_sources"]
    health = next(d for d in ds["datasets"] if d["key"] == "health_benchmark")
    assert "not a spacecraft health state" in health["evidence_class"]


def test_module_evidence_classes_cover_every_pipeline_module():
    from cosmos.ai import adapters
    names = {spec.name for spec in adapters.default_modules()}
    assert names == set(S.MODULE_EVIDENCE_CLASS)
    assert "not a spacecraft health state" in S.MODULE_EVIDENCE_CLASS["health"]
    assert "not linked to any object" in S.MODULE_EVIDENCE_CLASS["collision"]
