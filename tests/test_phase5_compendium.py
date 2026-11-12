"""Pins the Phase 5 ablation compendium (2026-11-06): artifact hashes and the shape of the verdicts.

The compendium re-reads archived ablations; what is pinned is that every cited artifact is the one
on disk and that the mixed, origin-dependent verdicts stay visible — gated fusion is not uniformly
better than either expert, the gate helps only where the learner is weak, and a feature group that
helps at one origin hurts at another.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/phase5_ablations"
pytestmark = pytest.mark.skipif(not (OUT / "compendium.json").is_file(), reason="compendium not generated")


@pytest.fixture(scope="module")
def comp() -> dict:
    return json.loads((OUT / "compendium.json").read_text())


def _sources(node, acc):
    if isinstance(node, dict):
        if "artifact" in node and "sha256" in node:
            acc.append(node)
        for v in node.values():
            _sources(v, acc)
    elif isinstance(node, list):
        for v in node:
            _sources(v, acc)
    return acc


def test_every_cited_artifact_is_present_and_unchanged(comp):
    assert comp["nothing_rerun"] is True
    cited = _sources(comp["sections"], [])
    assert len(cited) >= 12
    for c in cited:
        p = ROOT / c["artifact"]
        if c["present"]:
            assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == c["sha256"], c["artifact"]
        else:
            assert not p.is_file(), c["artifact"]            # recorded as absent must still be absent


def test_fusion_verdict_is_mixed_across_origins(comp):
    a = comp["sections"]["A_fusion_physics_vs_learned"]["origins"]
    arms = {o: v["arms"] for o, v in a.items()}
    # 2011 and 2006: the gated fusion does NOT beat the physics expert alone
    assert arms["2011"]["cosmos_gated"]["pinball"] > arms["2011"]["physics_only"]["pinball"]
    assert arms["2006"]["cosmos_gated"]["pinball"] > arms["2006"]["physics_only"]["pinball"]
    # 2016: it does, significantly, yet loses to the best learners alone
    p16 = a["2016"]["paired_vs_cosmos_gated"]
    assert p16["physics_only"]["gated_minus_other"] < 0 and p16["physics_only"]["significant"]
    assert p16["tabicl"]["gated_minus_other"] > 0 and p16["tabicl"]["significant"]
    assert a["2006"]["paired_vs_cosmos_gated"] == {} and a["2006"]["pairwise_source"]["present"] is False


def test_gate_helps_only_where_the_learner_is_weak(comp):
    b = comp["sections"]["B_reliability_gate_per_learner"]["origins"]
    g11, g16 = b["2011"]["learners"], b["2016"]["learners"]
    assert all(v["gain_significant"] and v["gain"] >= 0 for v in g11.values())
    assert not any(v["gain_significant"] for v in g16.values())
    assert sum(v["gain"] < 0 for v in g16.values()) >= 5
    assert b["2006"]["status"].startswith("NOT ARCHIVED")


def test_feature_group_effects_flip_sign_between_origins(comp):
    c = comp["sections"]["C_feature_group_ablations"]["origins"]
    e11, e16 = c["2011"]["effects"], c["2016"]["effects"]
    assert e11["no_physics"]["delta_pinball"] > 0 and e11["no_physics"]["significant"]
    assert e16["no_physics"]["delta_pinball"] < 0 and e16["no_physics"]["significant"]
    assert "LEAK" in e11["plus_rcs_2026"]["note"] and "LEAK" in e16["plus_rcs_2026"]["note"]


def test_vision_and_blocked_sections_are_recorded(comp):
    f = comp["sections"]["F_vision_input_channels"]["f1"]
    assert f["raw_highpass_only"] >= f["both_mean_3_seeds"] - 0.01 > f["diff_registered_only"] + 0.05
    h = comp["sections"]["H_not_evaluable_or_awaiting_approval"]
    assert len(h) >= 4 and all(("NOT" in v or "AWAITING" in v) for v in h.values())
    e = comp["sections"]["E_telemetry_alarm_layers"]
    assert "A0" in e["protocol"] and "OOF" in e["protocol"] and len(e["by_scorer"]) == 56
