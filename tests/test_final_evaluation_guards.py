"""Guards on the final evaluation protocol.

These enforce decisions that are easy to undo silently: the exclusion of a mean-elicited
endpoint, the preservation of historical artifacts, and the integrity of the G5d
pre-registration.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cosmos.ai.provenance import ROOT, sha256_file

#: Analysis scripts whose endpoints must stay locally elicitable under fixed-horizon
#: right-censoring (Taggart et al., arXiv:2603.14835).
ANALYSIS_SCRIPTS = (
    "scripts/phase_e_coupling_ablations.py",
    "scripts/phase_h_uncertainty_audit.py",
    "scripts/phase_g_lifetime_optimization.py",
    "scripts/phase_g_multihorizon_coherence.py",
    "scripts/g5_rolling_origin.py",
    "scripts/g5_censoring_causal_analysis.py",
    "scripts/e12_same_learner_c1.py",
)

#: Mean-elicited quantities that must not be used as an evaluation endpoint for a
#: fixed-horizon right-censored target. `rmse` is elicited by the mean, which Taggart et al.
#: prove is not locally elicitable in this setting.
FORBIDDEN_ENDPOINTS = ("rmse_log10", "rmse")


def test_no_analysis_script_uses_a_mean_elicited_endpoint() -> None:
    """The expectation functional is not locally elicitable under fixed-horizon censoring."""
    offenders = []
    for relative in ANALYSIS_SCRIPTS:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Comments and docstrings may legitimately name the excluded metric.
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            for forbidden in FORBIDDEN_ENDPOINTS:
                if forbidden in line:
                    offenders.append(f"{relative}:{line_number}: {stripped[:80]}")
    assert not offenders, (
        "a mean-elicited endpoint is used in an analysis script; quantile-, interval- or "
        "binary-probability endpoints are required:\n" + "\n".join(offenders))


def test_published_regression_table_is_not_modified() -> None:
    """`rmse_log10` is excluded by non-use, not by editing a historical artifact."""
    for origin in ("2011", "2016"):
        path = (ROOT / "outputs" / "benchmarks" / "reentry_lifetime"
                / f"origin{origin}_uncontrolled" / "regression_test.csv")
        if not path.is_file():
            continue
        header = path.read_text(encoding="utf-8").splitlines()[0]
        # The historical column must still be present: we do not rewrite published outputs.
        assert "rmse_log10" in header, (
            f"the published {origin} regression table was modified; historical artifacts "
            "must be preserved and the endpoint excluded by non-use instead")


def test_preregistration_freeze_still_matches_the_protocol() -> None:
    """A confirmatory experiment's protocol must not change after it was hashed."""
    freeze = ROOT / "outputs" / "g5d_origin2006" / "prereg_freeze.json"
    if not freeze.is_file():
        pytest.skip("G5d pre-registration has not been frozen")
    record = json.loads(freeze.read_text())
    actual = sha256_file(ROOT / record["preregistration"])
    assert actual == record["sha256"], (
        "the G5d pre-registration changed after it was frozen; any result from it is no "
        "longer confirmatory")


def test_g5d_does_not_edit_the_published_lifetime_module() -> None:
    """The new origin must be injected at runtime, never written into run.py."""
    run_py = (ROOT / "cosmos" / "ai" / "lifetime" / "run.py").read_text(encoding="utf-8")
    # The published ORIGINS dict must still contain exactly the two original origins.
    start = run_py.index("ORIGINS = {")
    end = run_py.index("}", start)
    block = run_py[start:end]
    assert '"2016"' in block and '"2011"' in block
    assert '"2006"' not in block, (
        "origin 2006 was written into run.py; it must be injected at runtime so the "
        "published protocol file is unmodified")
