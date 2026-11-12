"""Phase 4 — shared twin state: consistency with the forecast table, traceable values, schema drift.

The archived `twins.jsonl` (31,396 records, digest in FORECAST_SHA256.txt) is the twin state the
console and the adapters are built on. These tests check that it is internally consistent with the
forecast table it was derived from and with the regime rule, that every attached output is
traceable to a table column by value, and that a snapshot whose schema has drifted is refused with
the missing columns named and only dependants blocked. Interface checks on real artifacts; not a
scientific validation.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cosmos.ai import adapters
from cosmos.ai.orchestration import Orchestrator
from cosmos.ai.twin.state import classify_regime

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-10-27"
TWIN_DIR = ROOT / f"outputs/twin/as_of_{AS_OF}"
pytestmark = pytest.mark.skipif(not (TWIN_DIR / "twins.jsonl").is_file(), reason="archived twin state absent")

H = {"30d": "p_30d", "90d": "p_90d", "1yr": "p_1yr"}


@pytest.fixture(scope="module")
def twins() -> list[dict]:
    with (TWIN_DIR / "twins.jsonl").open() as fh:
        return [json.loads(line) for line in fh]


@pytest.fixture(scope="module")
def table() -> pd.DataFrame:
    return pd.read_csv(TWIN_DIR / "forecast_table.csv.gz", low_memory=False).set_index("norad")


def test_state_digest_matches_the_recorded_one():
    recorded = (TWIN_DIR / "FORECAST_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((TWIN_DIR / "twins.jsonl").read_bytes()).hexdigest() == recorded


def test_one_twin_per_table_row_same_date_and_regime_rule(twins, table):
    assert len(twins) == len(table) == 31396
    assert {int(t["object_id"]) for t in twins} == set(table.index)
    assert all(t["as_of"] == AS_OF for t in twins)
    for t in twins:
        assert t["regime"] == classify_regime(t["object_class"], t["operational_status"])
        assert t["regime"] == table.at[int(t["object_id"]), "regime"]


def test_attached_outputs_follow_the_regime_and_are_traceable_to_table_values(twins, table):
    pattern = {}
    for t in twins:
        row = table.loc[int(t["object_id"])]
        kinds = tuple(sorted((o["module"], o["abstain"]) for o in t["outputs"]))
        pattern[kinds] = pattern.get(kinds, 0) + 1
        for o in t["outputs"]:
            v = o["values"]
            if o["module"] == "reentry":
                for k, col in H.items():                                  # reported forecast, exactly
                    assert v[f"p_reentry_{k}"] == pytest.approx(row[col], abs=0, rel=0) or v[f"p_reentry_{k}"] == row[col]
                if o["abstain"]:
                    assert t["regime"] == "operator_controlled" and o["reason"]
                    assert "drag_only_p_reentry_30d" in v and v["drag_only_p_reentry_30d"] == row["p_physics_prior_30d"]
                else:
                    assert o["uncertainty"]["interval90_days"] == [row["lo90_days"], row["hi90_days"]]
                    assert v["median_days"] == row["median_days"]
            elif o["module"] == "reentry-comparison":                    # the lifetime variant, side by side
                assert t["object_class"] in ("D", "R", "C") and not o["abstain"]
                for k in H:
                    assert v[f"p_reentry_{k}"] == row[f"p_lifetime_{k}"]
                assert o["uncertainty"]["interval_kind"] == "Mondrian CQR"
            else:
                raise AssertionError(f"unexpected module in twin state: {o['module']}")
    assert pattern == {(("reentry", True),): 16386,
                       (("reentry", False), ("reentry-comparison", False)): 13238,
                       (("reentry", False),): 1772}


def test_archived_state_predates_per_output_provenance(twins):
    """Version finding (2026-11-06): the current `engine.run` attaches an OutputProvenance to every
    ModuleOutput, but the archived twins.jsonl carries `provenance: null` on all 44,634 outputs — it was
    written by an earlier engine revision. Traceability of the archived state is therefore by value
    (previous test), not by recorded lineage. Pinned so a regenerated state that *does* carry
    provenance is noticed as a different artifact, not silently equated with this one."""
    n = sum(len(t["outputs"]) for t in twins)
    assert n == 44634
    assert all(o.get("provenance") is None for t in twins for o in t["outputs"])


def test_known_issue_l17_is_visible_in_state_only_through_the_values(twins):
    """The 123 incoherent lifetime records carry abstain=false in the archived state (KNOWN_ISSUES.md);
    the adapter layer, not the state, is what abstains. Pin that the count is what the disclosure says."""
    bad = 0
    for t in twins:
        for o in t["outputs"]:
            if o["module"] == "reentry-comparison":
                p = [o["values"][f"p_reentry_{k}"] for k in ("30d", "90d", "1yr")]
                if p[0] > p[1] + 1e-12 or p[1] > p[2] + 1e-12:
                    bad += 1
                    assert o["abstain"] is False and o["reason"] == ""
    assert bad == 123


@pytest.mark.skipif(not (TWIN_DIR / "forecast_table.csv.gz").is_file(), reason="snapshot absent")
def test_schema_drift_is_refused_with_the_missing_columns_named(tmp_path):
    """A snapshot that is present but lacks a required column must fail its readers explicitly,
    name the columns, and block only the modules that depend on them."""
    src = TWIN_DIR / "forecast_table.csv.gz"
    rel = adapters.TWIN_SNAPSHOT.format(as_of=AS_OF)
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True)
    small = pd.read_csv(src, low_memory=False, nrows=200).drop(columns=["p_lifetime_30d", "hi90_days"])
    with gzip.open(dest, "wt") as fh:
        small.to_csv(fh, index=False)
    # the independent artifacts stay available so independent modules can still run
    for relative in (adapters.CONJUNCTION_PREDICTIONS, adapters.CONJUNCTION_SUMMARY, adapters.TELEMETRY_RESULTS):
        if (ROOT / relative).is_file():
            (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, tmp_path / relative)
    result = Orchestrator(adapters.default_modules()).run(
        {}, selected=("decision_priority", "collision", "health"),
        config={"as_of": AS_OF, "root": str(tmp_path), "limit": 50, "collision_limit": 20, "health_calibrator": "conformal_bh"})
    assert not result.successful
    # the first reader of the snapshot fails and names the columns; everything downstream is blocked
    # with the failed module named, and nothing is substituted
    cat = result.modules["catalogue_state"]
    assert cat.status == "failed" and cat.outputs == {}
    assert "missing columns" in cat.error and "p_lifetime_30d" in cat.error and "hi90_days" in cat.error
    for name in ("lifetime", "reentry", "decision_priority"):
        assert result.modules[name].status == "blocked", name
        assert "catalogue_state" in result.modules[name].reason
        assert result.modules[name].outputs == {}
    if (ROOT / adapters.CONJUNCTION_PREDICTIONS).is_file():
        assert result.modules["collision"].status == "success"
    if (ROOT / adapters.TELEMETRY_RESULTS).is_file():
        assert result.modules["health"].status == "success"
    # nothing was written into the temporary root by the failed modules
    assert not list((tmp_path / "outputs").rglob("*.csv")) or all("benchmarks" in str(p) for p in (tmp_path / "outputs").rglob("*.csv"))


def test_wrong_date_snapshot_is_not_accepted_as_the_requested_one(tmp_path):
    """Asking for a date whose snapshot does not exist must fail, never fall back to another date."""
    (tmp_path / "outputs/twin/as_of_2026-10-27").mkdir(parents=True)
    shutil.copy(TWIN_DIR / "forecast_table.csv.gz", tmp_path / "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz")
    result = Orchestrator(adapters.default_modules()).run(
        {}, selected=("reentry",), config={"as_of": "2026-11-06", "root": str(tmp_path), "limit": 10})
    cat = result.modules["catalogue_state"]
    assert cat.status == "failed" and "as_of_2026-11-06" in cat.error and cat.outputs == {}
    assert result.modules["reentry"].status == "blocked" and result.modules["reentry"].outputs == {}
    assert np.all([m.status != "success" for n, m in result.modules.items() if n in ("catalogue_state", "reentry")])
