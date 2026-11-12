"""The exploratory T1 ranking-utility record (Phase D.3): outputs exist, are labelled exploratory and non-blind, follow the
declared protocol, and are internally consistent. The analysis itself (minutes of bootstrap) is not re-run here."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cosmos.ai.provenance import ROOT

OUT = ROOT / "outputs/t1_ranking_utility"
pytestmark = pytest.mark.skipif(not (OUT / "results.json").is_file(), reason="T1 ranking-utility record absent")


def test_record_is_labelled_exploratory_and_traces_its_input_and_rule():
    r = json.loads((OUT / "results.json").read_text())
    assert r["exploratory"] is True and r["blind"] is False and "analysed before" in r["why_not_blind"]
    assert r["protocol"] == "docs/research/T1_RANKING_UTILITY_PROTOCOL.md" and (ROOT / r["protocol"]).is_file()
    assert r["input"]["path"].endswith("t1_objects.csv.gz") and len(r["input"]["sha256"]) == 64
    assert r["rule"]["consequence_mass_kg"] == 500.0 and r["rule"]["multiplier"] == 2.0 and "p_30d" in r["rule"]["formula"]


def test_metrics_are_consistent_and_bounded():
    r = json.loads((OUT / "results.json").read_text())
    csv = pd.read_csv(OUT / "precision_at_k.csv")
    assert set(csv.columns) >= {"population", "horizon", "ranking", "k", "hits", "precision", "recall"}
    assert ((csv.precision >= 0) & (csv.precision <= 1)).all() and ((csv.recall >= 0) & (csv.recall <= 1)).all()
    for pop_name, pop in r["populations"].items():
        for horizon in ("y_30d", "y_72d"):
            h = pop[horizon]
            assert h["events"] > 0 and 0 < h["base_rate"] < 0.05
            for name, rows in h["rankings"].items():
                for row in rows:
                    assert 0.0 <= row["precision"] <= 1.0
                    if "hits" in row:
                        assert row["hits"] == round(row["precision"] * row["k"]) and row["recall"] == pytest.approx(row["hits"] / h["events"])
            # every learned/physics ranking beats the base rate at k = 25 on this window; perigee is the physics-free floor
            assert h["rankings"]["deployed_rule"][1]["precision"] > h["base_rate"]
            for key, d in h["paired_cluster_bootstrap"].items():
                assert d["k"] in (25, 50)
                if not d["identical_top_k"]:
                    assert d["ci95"][0] <= d["difference"] <= d["ci95"][1]


def test_the_rule_never_claims_operational_effectiveness():
    text = (ROOT / "docs/research/T1_RANKING_UTILITY_PROTOCOL.md").read_text()
    assert "No claim of operational effectiveness" in text and "non-blind" in text
