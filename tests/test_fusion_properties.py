"""Properties of the noisy-OR decision layer `cosmos.ai.fusion.decide` (Phase 3, 2026-11-06).

Unit-level validation with constructed evidence — no real-data claim. The function is exercised
by the legacy `cosmos.run_pipeline` chain and by tests; the deployed twin adapters do not call it
(they never have joinable evidence to combine), which is recorded in the completion tracker.
"""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from cosmos.ai.fusion import Evidence, decide


def ev(p: float, model: str = "m", status: str = "validated-real", **kw) -> Evidence:
    return Evidence("reentry", model, "c", p, status, **kw)


@pytest.mark.parametrize("ps", [(0.1,), (0.2, 0.3), (0.05, 0.4, 0.5), (0.0, 0.0), (1.0, 0.3)])
def test_combined_probability_is_bounded_by_the_largest_input_and_one(ps):
    d = decide([ev(p, f"m{i}") for i, p in enumerate(ps)], "c", conflict=1.0)
    assert not d.abstain
    assert max(ps) - 1e-12 <= d.probability <= 1.0 + 1e-12
    assert d.probability == pytest.approx(1 - np.prod([1 - p for p in ps]))


def test_monotone_in_every_input():
    base = [0.2, 0.3, 0.4]
    d0 = decide([ev(p, f"m{i}") for i, p in enumerate(base)], "c").probability
    for i in range(3):
        up = list(base)
        up[i] += 0.1
        d1 = decide([ev(p, f"m{k}") for k, p in enumerate(up)], "c").probability
        assert d1 > d0


def test_order_invariant_and_single_item_identity():
    items = [ev(0.2, "a"), ev(0.5, "b"), ev(0.35, "c")]
    probs = {decide(list(perm), "c").probability for perm in itertools.permutations(items)}
    assert len({round(p, 15) for p in probs}) == 1
    assert decide([ev(0.37)], "c").probability == pytest.approx(0.37)


def test_abstains_on_conflict_at_exactly_the_declared_spread():
    # 0.75 - 0.25 is exactly representable, so "spread == conflict" is tested, not a rounding artefact
    assert not decide([ev(0.25, "a"), ev(0.75, "b")], "c", conflict=0.5).abstain    # spread == conflict
    d = decide([ev(0.25, "a"), ev(0.76, "b")], "c", conflict=0.5)
    assert d.abstain and d.probability is None and d.reason.startswith("conflicting")
    assert d.used == ["a", "b"]                                                        # which items conflicted stays visible


def test_conflict_test_is_strict_in_floating_point():
    # documented behaviour: the comparison is `spread > conflict` on floats, so 0.9 - 0.3 (= 0.6000…01)
    # does abstain at conflict = 0.6; callers must not rely on exact-boundary arithmetic
    assert decide([ev(0.3, "a"), ev(0.9, "b")], "c", conflict=0.6).abstain


def test_only_validated_in_domain_matching_evidence_is_used():
    items = [ev(0.3, "ok"),
             ev(0.9, "not_run", status="not-run"),
             ev(0.8, "synthetic_only", status="validated-synthetic"),      # spread 0.5 < default conflict 0.6
             ev(0.9, "ood", in_domain=False),
             ev(0.9, "other_claim").__class__("reentry", "other_claim", "d", 0.9, "validated-real"),
             ev(0.9, "other_object", object_id="X"),
             ev(0.9, "old_window", window=(0, 1))]
    d = decide(items, "c", object_id="Y", window=(5, 6))
    assert d.used == ["ok", "synthetic_only"]
    reasons = dict(d.reported_only)
    assert reasons["not_run"] == "status not-run" and reasons["ood"] == "input out of domain"
    assert reasons["other_claim"] == "different claim" and reasons["other_object"] == "different object"
    assert reasons["old_window"] == "outside the time window"
    assert any("synthetic" in a for a in d.assumptions)             # the weaker validation is declared
    assert d.probability == pytest.approx(1 - 0.7 * 0.2)


def test_insufficient_evidence_abstains_rather_than_guessing():
    d = decide([ev(0.9, status="not-run")], "c")
    assert d.abstain and d.probability is None and d.reason == "insufficient compatible evidence"
    assert decide([ev(0.4)], "c", min_items=2).abstain
