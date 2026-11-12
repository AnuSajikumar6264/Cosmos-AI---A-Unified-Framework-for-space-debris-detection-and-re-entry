"""P3-B — twin-state evidence root: explicit source selection, provenance, integrity, equivalence, failure modes,
orchestrator modules, API and console visibility (2026-11-08).

Fixtures are small roots built from slices of the REAL archives (never new observations): the first N records
of the re-emitted and archived twin states plus the matching rows of the forecast table, with digest files and a
re-emission manifest adjusted to the slice. Tampering is applied to copies only.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cosmos.ai import adapters
from cosmos.ai.orchestration import Orchestrator
from cosmos.ai.provenance import ROOT
from cosmos.ai.twin import reader as R
from cosmos.ai.twin.modules import TwinStateUnavailable, twin_state_records
from cosmos.product import store as S
from cosmos.product.api import create_app
from cosmos.product.store import ArtifactStore, InvalidSelection
from scripts.run_pipeline import _module_manifest, _write_tables

AS_OF = "2026-10-27"
REEMITTED = ROOT / S.TWIN_STATE_REEMITTED.format(as_of=AS_OF)
ARCHIVED = ROOT / S.TWIN_STATE_ARCHIVED.format(as_of=AS_OF)
SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=AS_OF)
MANIFEST = ROOT / S.REEMISSION_MANIFEST.format(as_of=AS_OF)
pytestmark = pytest.mark.skipif(not (REEMITTED.is_file() and ARCHIVED.is_file() and SNAPSHOT.is_file() and MANIFEST.is_file()),
                                reason="twin-state archives absent")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _first_lines(path: Path, n: int) -> list[bytes]:
    out = []
    with path.open("rb") as fh:
        for line in fh:
            out.append(line)
            if len(out) == n:
                break
    return out


def make_root(tmp_path: Path, n: int = 40, *, reemitted: bool = True, archived: bool = True, tamper: str | None = None,
              run: bool = True, extra_twin_record: bool = False, drop_table_row: bool = False) -> Path:
    """A root holding slices of the real archives; ``tamper`` applies one controlled defect to the re-emitted copy."""
    root = tmp_path / "root"
    arch_dir = root / f"outputs/twin/as_of_{AS_OF}"; re_dir = root / f"outputs/twin/as_of_{AS_OF}_reemitted_v1"
    arch_dir.mkdir(parents=True); re_dir.mkdir(parents=True)
    re_lines = _first_lines(REEMITTED, n + (1 if extra_twin_record else 0))
    ids = [json.loads(l)["object_id"] for l in re_lines[:n]]
    arch_lines = {}
    with ARCHIVED.open("rb") as fh:
        for line in fh:
            oid = json.loads(line)["object_id"]
            if oid in ids:
                arch_lines[oid] = line
            if len(arch_lines) == n:
                break
    table = pd.read_csv(SNAPSHOT, low_memory=False)
    table = table[table["norad"].astype(int).astype(str).isin(ids)]
    if drop_table_row:
        table = table.iloc[1:]
    with gzip.open(arch_dir / "forecast_table.csv.gz", "wt") as fh:
        table.to_csv(fh, index=False)
    if archived:
        data = b"".join(arch_lines[i] for i in ids)
        (arch_dir / "twins.jsonl").write_bytes(data)
        (arch_dir / "FORECAST_SHA256.txt").write_text(f"{_sha(data)} twins.jsonl\n")
    if reemitted:
        data = b"".join(re_lines)
        if tamper == "malformed":
            parts = data.split(b"\n"); parts[2] = b"{not json"; data = b"\n".join(parts)
        elif tamper == "malformed_first":
            parts = data.split(b"\n"); parts[0] = b"{not json"; data = b"\n".join(parts)
        elif tamper == "duplicate":
            data = data + re_lines[0]
        elif tamper == "schema":
            rec = json.loads(re_lines[0]); rec["schema_version"] = "twin_state/9.0"
            data = json.dumps(rec).encode() + b"\n" + b"".join(re_lines[1:])
        elif tamper == "value":
            rec = json.loads(re_lines[0])
            for o in rec["outputs"]:
                if o["module"] == "reentry" and not o["abstain"]:
                    o["values"]["p_reentry_30d"] = 0.123456
            data = json.dumps(rec).encode() + b"\n" + b"".join(re_lines[1:])
        elif tamper == "provenance":
            rec = json.loads(re_lines[0]); rec["outputs"][0]["provenance"] = None
            data = json.dumps(rec).encode() + b"\n" + b"".join(re_lines[1:])
        elif tamper == "empty":
            data = b""
        (re_dir / "twins.jsonl").write_bytes(data)
        recorded = _sha(data)
        if tamper == "hash":
            (re_dir / "twins.jsonl").write_bytes(data + b'{"object_id": "999999999"}\n')   # file changed after the digest was recorded
        (re_dir / "TWINS_SHA256.txt").write_text(f"{recorded} twins.jsonl\n")
        man = json.loads(MANIFEST.read_text())
        man["output"] = {"directory": str(re_dir.relative_to(root)), "twins_jsonl_sha256": recorded,
                         "records": len(re_lines) + (1 if tamper == "duplicate" else 0)}   # the recorded artifact itself holds the duplicate
        if tamper == "count":
            man["output"]["records"] = len(re_lines) + 7
        if tamper == "model_claim":
            man["model_version"] = {"status": "recorded", "digest": "f" * 64, "reason": None}
        if tamper == "no_manifest":
            man = None
        if man is not None:
            (re_dir / "REEMISSION_MANIFEST.json").write_text(json.dumps(man))
    if run:
        _fixture_run(root)
    return root


def _fixture_run(root: Path, select=("decision_priority",)) -> Path:
    """The real catalogue chain executed on the slice; tables and manifest written like the pipeline does."""
    config = {"root": str(root), "as_of": AS_OF, "limit": None, "collision_limit": None, "debris_sequence_limit": None,
              "health_calibrator": None, "collision_model": "cosmos_gated", "twin_source_policy": "prefer_reemitted"}
    execution = Orchestrator(adapters.default_modules()).run({}, selected=list(select), config=config)
    run_dir = root / "outputs/pipeline/run_20990101T000000Z"; run_dir.mkdir(parents=True, exist_ok=True)
    tables = _write_tables(execution, run_dir)
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "schema_version": "run_manifest/1.2", "as_of": AS_OF, "started_at": execution.started_at, "duration_s": 0.1,
        "requested": list(execution.requested), "config": config, "config_sha256": execution.config_sha256,
        "successful": execution.successful, "git": {"git_commit": None}, "tables_written": tables,
        "modules": _module_manifest(execution), "interpretation": {"not_established": ["FIXTURE run on a slice"]}}, default=str))
    return run_dir


# ====================================================================== 1-2: selection and explicit fallback
def test_valid_1_1_is_selected_as_primary_on_the_real_root():
    sel = R.select_source(ROOT, AS_OF, "prefer_reemitted")
    assert sel["selected"] == "reemitted" and sel["status"] == "primary" and sel["fallback_used"] is False
    c = sel["candidates"]["reemitted"]
    assert c["status"] == "valid" and c["digest_state"] == "verified" and c["schema_version"] == "twin_state/1.1"
    assert c["record_count"] == 31396 and c["record_count_state"] == "matches" and c["provenance_complete"] is True
    assert "archived" not in sel["candidates"] or sel["candidates"]["archived"].get("status") in (None, "valid", "not_evaluated")


def test_explicit_fallback_and_explicit_archived_policy(tmp_path):
    root = make_root(tmp_path, reemitted=False)
    sel = R.select_source(root, AS_OF, "prefer_reemitted")
    assert sel["selected"] == "archived" and sel["status"] == "fallback" and sel["fallback_used"] is True
    assert "not present" in sel["reason"] and "fallback" in sel["reason"]
    assert sel["candidates"]["reemitted"]["status"] == "missing"
    only = R.select_source(root, AS_OF, "reemitted_only")
    assert only["selected"] is None and only["status"] == "unavailable" and "not permitted" in only["reason"]
    assert only["candidates"]["archived"]["status"] == "not_evaluated"
    explicit = R.select_source(root, AS_OF, "archived_only")
    assert explicit["selected"] == "archived" and explicit["status"] == "explicit_archived" and explicit["fallback_used"] is False
    with pytest.raises(ValueError):
        R.select_source(root, AS_OF, "whatever")


# ====================================================================== 3: fallback visible in API and UI
def test_fallback_is_visible_in_api_and_console(tmp_path):
    root = make_root(tmp_path, reemitted=False)
    c = TestClient(create_app(root))
    norad = int(pd.read_csv(gzip.open(root / f"outputs/twin/as_of_{AS_OF}/forecast_table.csv.gz")).norad.iloc[0])
    t = c.get(f"/api/objects/{norad}/twin").json()
    assert t["available"] and t["source"] == "archived" and t["schema_version"] == "twin_state/1.0"
    assert t["fallback"]["used"] is True and "not present" in t["fallback"]["reason"]
    assert t["selection"]["status"] == "fallback" and t["selection"]["candidates"]["reemitted"]["status"] == "missing"
    assert t["provenance_on_outputs"] is False and t["model_version"]["status"] == "unavailable"
    page = html.unescape(c.get(f"/objects/{norad}").text)
    assert "HISTORICAL ARCHIVE · twin_state/1.0 (fallback)" in page and "Source selection" in page and "FALLBACK" in page
    ts = c.get("/api/twin-state").json()
    assert ts["selection_status"] == "fallback" and ts["overall"]["tone"] == "warn" and "FALLBACK" in ts["overall"]["label"]
    assert ts["provenance"]["provenance_on_outputs"] is False and ts["provenance"]["original_or_reemitted"] == "original_archive"
    tpage = c.get("/twin-state").text
    assert "FALLBACK" in tpage and 'status-info">HISTORICAL' not in tpage          # never a green badge for a fallback
    # the explicit archived policy is not called a fallback
    e = c.get("/api/twin-state?policy=archived_only").json()
    assert e["selection_status"] == "explicit_archived" and e["selection"]["fallback_used"] is False and e["overall"]["tone"] == "warn"


# ====================================================================== 4-7: invalid 1.1, missing, hash mismatch, schema
@pytest.mark.parametrize("tamper,needle", [("hash", "differs from the recorded digest"), ("malformed_first", "not valid JSON"),
                                           ("schema", "not supported"), ("count", "recorded in the manifest"),
                                           ("empty", "present but empty")])
def test_invalid_1_1_never_appears_as_a_successful_primary(tmp_path, tamper, needle):
    root = make_root(tmp_path, tamper=tamper, run=False)
    sel = R.select_source(root, AS_OF, "prefer_reemitted")
    c = sel["candidates"]["reemitted"]
    assert c["status"] == "invalid" and any(needle in r for r in c["reasons"]), c["reasons"]
    assert sel["selected"] == "archived" and sel["status"] == "fallback" and needle in sel["reason"]
    strict = R.select_source(root, AS_OF, "reemitted_only")
    assert strict["selected"] is None and strict["status"] == "unavailable" and needle in strict["reason"]
    if tamper == "hash":
        assert c["digest_state"] == "MISMATCH"
    if tamper == "schema":
        assert c["schema_version"] == "twin_state/9.0" and c["schema_supported"] is False
    if tamper == "empty":
        assert c["present"] is True and c["record_count"] == 0 and sel["candidates"]["reemitted"]["status"] != "missing"


def test_mid_file_corruption_is_a_finding_never_a_clean_primary(tmp_path):
    """A malformed record after the first line passes the cheap selection peek but is caught by the streaming
    integrity pass: the overall verdict carries findings, the module reports issues; nothing is repaired."""
    root = make_root(tmp_path, tamper="malformed")
    st = ArtifactStore(root)
    assert st.twin_selection(AS_OF)["status"] == "primary"                    # the artifact IS the recorded one
    ts = st.twin_state_integration()
    assert ts["integrity"]["records_malformed_json"] == 1 and ts["integrity"]["status"] == "issues"
    assert ts["overall"]["status"] == "primary_with_findings" and ts["overall"]["tone"] == "warn" and "integrity issues" in ts["overall"]["reason"]
    assert ts["integrity"]["examples"]["malformed"][0]["line"] == 3
    config = {"root": str(root), "as_of": AS_OF, "limit": None, "twin_source_policy": "prefer_reemitted"}
    ex = Orchestrator(adapters.default_modules()).run({}, selected=["twin_state"], config=config)
    assert ex.modules["twin_state"].outputs["integrity_status"] == "issues" and ex.modules["twin_state"].outputs["records_malformed_json"] == 1
    page = TestClient(create_app(root)).get("/twin-state").text
    assert "FINDINGS" in page and "ISSUES" in page


def test_missing_sources_are_reported_accurately(tmp_path):
    root = make_root(tmp_path, reemitted=False, archived=False, run=False)
    sel = R.select_source(root, AS_OF, "prefer_reemitted")
    assert sel["selected"] is None and sel["status"] == "unavailable"
    assert sel["candidates"]["reemitted"]["status"] == "missing" and sel["candidates"]["archived"]["status"] == "missing"
    assert "_reemitted_v1/twins.jsonl is not present" in sel["reason"] and f"as_of_{AS_OF}/twins.jsonl is not present" in sel["reason"]
    c = TestClient(create_app(root))
    ts = c.get("/api/twin-state").json()
    assert ts["selected_source"] is None and ts["overall"]["label"] == "NO TWIN-STATE SOURCE" and ts["integrity"]["status"] == "unavailable"
    assert ts["equivalence"]["status"] == "unavailable"
    assert "NO TWIN-STATE SOURCE" in c.get("/twin-state").text
    # the orchestrator module fails explicitly; the catalogue chain is untouched by that failure
    config = {"root": str(root), "as_of": AS_OF, "limit": None, "twin_source_policy": "prefer_reemitted"}
    ex = Orchestrator(adapters.default_modules()).run({}, selected=["twin_equivalence", "decision_priority"], config=config)
    assert ex.modules["twin_state"].status == "failed" and "TwinStateUnavailable" in ex.modules["twin_state"].error
    assert ex.modules["twin_equivalence"].status == "blocked"
    assert all(ex.modules[m].status == "success" for m in ("catalogue_state", "lifetime", "reentry", "decision_priority"))


def test_missing_fallback_with_valid_primary_is_fine_and_reported(tmp_path):
    root = make_root(tmp_path, archived=False, run=False)
    sel = R.select_source(root, AS_OF, "prefer_reemitted", evaluate_all=True)
    assert sel["selected"] == "reemitted" and sel["status"] == "primary"
    assert sel["candidates"]["archived"]["status"] == "missing"
    with pytest.raises(TwinStateUnavailable):
        R.select_source(root, AS_OF, "archived_only")["selected"] or (_ for _ in ()).throw(TwinStateUnavailable("x"))


# ====================================================================== 8: duplicates, malformed, value problems in the stream
def test_duplicate_identities_and_malformed_records_are_detected(tmp_path):
    root = make_root(tmp_path, tamper="duplicate", run=False)
    integ = R.validate_archive(root / S.TWIN_STATE_REEMITTED.format(as_of=AS_OF))
    assert integ["records_total"] == 41 and integ["unique_identities"] == 40 and integ["duplicate_identities"] == 1
    assert integ["examples"]["duplicates"][0]["line"] == 41 and integ["status"] == "issues"
    root2 = make_root(tmp_path / "b", tamper="provenance", run=False)
    integ2 = R.validate_archive(root2 / S.TWIN_STATE_REEMITTED.format(as_of=AS_OF))
    assert integ2["records_schema_invalid"] == 1 and "provenance" in integ2["examples"]["schema_invalid"][0]["error"]
    # the module reports the issue in its outputs, keeps the first occurrence in the index, never repairs
    config = {"root": str(root), "as_of": AS_OF, "limit": None, "twin_source_policy": "prefer_reemitted"}
    ex = Orchestrator(adapters.default_modules()).run({}, selected=["twin_state"], config=config)
    outs = ex.modules["twin_state"].outputs
    assert ex.modules["twin_state"].status == "success" and outs["integrity_status"] == "issues"
    assert outs["duplicate_identities"] == 1 and len(outs["record_index"]) == 40 and outs["records_total"] == 41


def test_value_problems_are_flagged_not_filled():
    rec = {"outputs": [{"module": "reentry", "abstain": False, "values": {"p_reentry_30d": float("nan"), "p_reentry_90d": 1.5}}]}
    problems = R.record_value_problems(rec)
    assert "outputs[0].values.p_reentry_30d" in problems and any("out of [0, 1]" in p for p in problems) and "outputs[0].values.p_reentry_1yr" in problems
    assert R.record_value_problems({"outputs": [{"module": "reentry", "abstain": True, "values": {}}]}) == []


# ====================================================================== 9-10: provenance preserved; model version
def test_provenance_fields_are_preserved_exactly_from_the_artifacts():
    st = ArtifactStore(ROOT)
    ts = st.twin_state_integration()
    p = ts["provenance"]; man = json.loads(MANIFEST.read_text())
    assert p["recorded_sha256"] == (ROOT / S.TWIN_STATE_REEMITTED_DIGEST.format(as_of=AS_OF)).read_text().split()[0]
    assert p["computed_sha256"] == p["recorded_sha256"] == man["output"]["twins_jsonl_sha256"] and p["digest_state"] == "verified"
    assert p["transformation_digest_sha256"] == man["transformation_digest_sha256"] and p["code_revision"] == man["code_revision"]
    assert p["method"] == man["method"] and p["record_count"] == 31396 == man["output"]["records"]
    assert p["schema_version"] == "twin_state/1.1" and p["original_or_reemitted"] == "reemitted" and p["provenance_on_outputs"] is True
    assert p["predictions_regenerated"] is False and p["model_executed"] is False
    assert ts["model_version"]["status"] == "unavailable" and ts["overall"]["status"] == "primary_verified"
    assert ts["integrity"]["status"] == "ok" and ts["integrity"]["records_valid"] == 31396


def test_missing_model_provenance_stays_unavailable_and_a_recorded_one_is_only_surfaced_when_present(tmp_path):
    root = make_root(tmp_path, run=False)
    st = ArtifactStore(root)
    sel = st.twin_selection(AS_OF)
    assert sel["candidates"]["reemitted"]["model_version"]["status"] == "unavailable"
    norad = int(json.loads(_first_lines(REEMITTED, 1)[0])["object_id"])
    assert st.twin_record(norad)["model_version"]["status"] == "unavailable"
    root2 = make_root(tmp_path / "b", tamper="model_claim", run=False)
    st2 = ArtifactStore(root2)
    assert st2.twin_record(norad)["model_version"] == {"status": "recorded", "digest": "f" * 64, "label": None, "reason": None, "registry_card": None}
    root3 = make_root(tmp_path / "c", tamper="no_manifest", run=False)
    c3 = R.select_source(root3, AS_OF)["candidates"]["reemitted"]
    assert c3["status"] == "valid" and c3["provenance_complete"] is False and any("absent" in w for w in c3["warnings"])


# ====================================================================== 11-12: equivalence and non-comparable
def test_equivalence_is_equal_on_an_untouched_slice_and_detects_one_changed_value(tmp_path):
    root = make_root(tmp_path)
    st = ArtifactStore(root)
    ts = st.twin_state_integration()
    eq = ts["equivalence"]
    assert eq["status"] == "computed" and eq["records_compared"] == 40 and eq["records_equal"] == 40 and eq["records_different"] == 0
    assert eq["records_missing_in_chain"] == 0 and eq["records_missing_in_twin"] == 0 and eq["equivalent"] is True
    root2 = make_root(tmp_path / "b", tamper="value")
    ts2 = ArtifactStore(root2).twin_state_integration()
    eq2 = ts2["equivalence"]
    assert eq2["records_different"] == 1 and eq2["records_equal"] == 39 and eq2["different_fields"] == {"reentry.p_30d": 1}
    assert eq2["examples"]["different"][0]["differences"]["reentry.p_30d"]["twin"] == 0.123456 and eq2["equivalent"] is False
    assert ts2["overall"]["status"] == "primary_with_findings" and ts2["overall"]["tone"] == "warn"
    norad = int(eq2["examples"]["different"][0]["object_id"])
    rec = ArtifactStore(root2).twin_record(norad)
    assert rec["equivalence"]["status"] == "different" and rec["equivalence"]["fields_different"] == ["reentry.p_30d"]
    page = html.unescape(TestClient(create_app(root2)).get(f"/objects/{norad}").text)
    assert "DIFFERENT" in page and "reentry.p_30d" in page


def test_non_comparable_and_missing_records_are_reported_separately(tmp_path):
    root = make_root(tmp_path, extra_twin_record=True, drop_table_row=True)   # twin has 41 records; chain has 39 objects
    eq = ArtifactStore(root).twin_state_integration()["equivalence"]
    assert eq["twin_records"] == 41 and eq["records_missing_in_chain"] == 2 and eq["records_missing_in_twin"] == 0
    assert eq["records_compared"] == 39 and eq["records_equal"] == 39
    # the real root: operator-controlled objects differ in representation, not in value; reported as not comparable
    st = ArtifactStore(ROOT)
    iss = st.twin_record(25544)["equivalence"]
    assert iss["status"] == "equal" and "reentry.abstained" in iss["not_comparable"] and "operator-controlled" in iss["not_comparable"]["reentry.abstained"]
    assert "reentry.abstained" not in iss["fields_different"]
    full = st.twin_state_integration()["equivalence"]
    assert full["records_not_comparable"] == 0 and any("operator-controlled" in k for k in full["not_comparable_reasons"])
    assert any("lifetime: chain lifetime abstained" in k for k in full["not_comparable_reasons"])
    # the 123 non-coherent lifetimes (L17) are attributed from the run's own table and kept apart from the
    # operator-controlled representation difference; numerical agreement is not presented as semantic agreement
    l17 = {k: n for k, n in full["not_comparable_reasons"].items() if "not monotone across horizons" in k}
    c3 = {k: n for k, n in full["not_comparable_reasons"].items() if "operator-controlled" in k}
    assert l17 and list(l17.values()) == [123] and c3 and list(c3.values()) == [16386]
    assert "lifetime_noncoherent_horizons.csv" in full["chain_tables"]


def test_compare_record_unit_semantics():
    rec = {"object_id": "1", "name": "A", "regime": "natural_decay", "object_class": "R",
           "orbit": {"perigee_km": 1.0, "apogee_km": 2.0, "inc_deg": 3.0}, "physical": {"mass_kg": float("nan")},
           "outputs": [{"module": "reentry", "abstain": False, "values": {"p_reentry_30d": 0.5, "p_reentry_90d": 0.6, "p_reentry_1yr": 0.7, "median_days": 5.0},
                        "uncertainty": {"interval90_days": [9.0, 1.0]}}]}
    chain = {"name": "A", "regime": "natural_decay", "object_class": "R", "perigee_km": 1.0, "apogee_km": 2.0, "inc_deg": 3.0, "mass_kg": None,
             "reentry": {"abstained": False, "p": {"30d": 0.5, "90d": 0.6, "1yr": 0.7}, "quantiles": (1.0, 5.0, 9.0), "quantiles_reason": None}, "lifetime": None}
    res = R.compare_record(rec, chain)
    assert res["status"] == "equal" and res["fields_different"] == [] and "reentry.time_quantiles" in res["not_comparable"]   # NaN == None; non-monotone raw not forced
    assert R.compare_record(rec, None)["status"] == "missing_in_chain"
    chain2 = dict(chain, reentry={"abstained": True, "reason": "no drag forecast"})
    res2 = R.compare_record(rec, chain2)
    assert "reentry.abstained" in res2["fields_different"] and res2["status"] == "different"


# ====================================================================== 13: existing chain untouched (graph + outputs on a slice)
def test_catalogue_chain_graph_and_outputs_are_unchanged_by_the_new_root(tmp_path):
    specs = {m.name: m for m in adapters.default_modules()}
    assert specs["catalogue_state"].depends_on == () and specs["lifetime"].depends_on == ("catalogue_state",)
    assert specs["reentry"].depends_on == ("catalogue_state",) and specs["decision_priority"].depends_on == ("catalogue_state", "lifetime", "reentry")
    assert specs["twin_state"].depends_on == () and "twin_state" not in specs["decision_priority"].depends_on
    assert set(specs) == {"catalogue_state", "lifetime", "reentry", "collision", "health", "debris", "twin_state", "twin_equivalence", "decision_priority"}
    root = make_root(tmp_path, run=False)
    config = {"root": str(root), "as_of": AS_OF, "limit": None, "twin_source_policy": "prefer_reemitted"}
    with_twin = Orchestrator(adapters.default_modules()).run({}, selected=["decision_priority", "twin_equivalence"], config=config)
    without = Orchestrator(adapters.default_modules()).run({}, selected=["decision_priority"], config=config)
    (tmp_path / "a").mkdir(exist_ok=True); (tmp_path / "b").mkdir(exist_ok=True)
    a = _write_tables(with_twin, tmp_path / "a"); b = _write_tables(without, tmp_path / "b")
    assert "twin_equivalence.csv" in a and "twin_equivalence.csv" not in b
    for name in b:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
    eq = with_twin.modules["twin_equivalence"].outputs
    assert eq["records_compared"] == 40 and eq["records_equal"] == 40 and eq["equivalent"] is True
    man = _module_manifest(with_twin)
    assert man["twin_state"]["outputs"]["record_index"] == {"count": 40} and man["twin_state"]["outputs"]["source"] == "reemitted"
    assert man["twin_state"]["lineage"]["model_version"]["status"] == "unavailable"
    assert man["twin_equivalence"]["outputs"]["comparison"] == {"count": 40}
    from cosmos.ai.schema import validate_run_manifest
    assert validate_run_manifest({"schema_version": "run_manifest/1.2", "as_of": AS_OF, "started_at": "x", "modules": man}) == "1.2"


# ====================================================================== console: availability row, policies, caching
def test_availability_row_reflects_whether_the_run_read_the_twin_state(tmp_path):
    root = make_root(tmp_path)
    _fixture_run(root, select=("decision_priority", "twin_equivalence"))
    st = ArtifactStore(root)
    norad = int(pd.read_csv(gzip.open(root / f"outputs/twin/as_of_{AS_OF}/forecast_table.csv.gz")).norad.iloc[0])
    rec = st.object_record(norad)
    row = [x for x in rec["evidence_availability"] if x["capability"] == "versioned twin state"][0]
    assert row["status"] == "implemented" and "additional evidence root" in row["detail"] and "40 of 40" in row["detail"]
    hist = ArtifactStore(ROOT).object_record(37607)
    hrow = [x for x in hist["evidence_availability"] if x["capability"] == "versioned twin state"][0]
    assert hrow["status"] in ("archived_only", "implemented")   # depends on whether the latest real run carries the module
    if hrow["status"] == "archived_only":
        assert "predates the twin_state module" in hrow["detail"]


def test_api_policy_validation_and_integration_cache(tmp_path):
    root = make_root(tmp_path)
    app = create_app(root); c = TestClient(app); st = app.state.store
    assert c.get("/api/twin-state?policy=nonsense").status_code == 422
    with pytest.raises(InvalidSelection):
        st.twin_selection(AS_OF, "nonsense")
    c.get("/api/twin-state"); c.get("/api/twin-state")
    assert st.cache_stats()["twin_integration_miss"] == 1 and st.cache_stats()["twin_integration_hit"] == 1
    # a change to the archive invalidates: append a duplicate line (digest file unchanged -> MISMATCH -> fallback)
    p = root / S.TWIN_STATE_REEMITTED.format(as_of=AS_OF)
    p.write_bytes(p.read_bytes() + _first_lines(REEMITTED, 1)[0])
    ts = c.get("/api/twin-state").json()
    assert st.cache_stats()["twin_integration_miss"] == 2 and ts["selection_status"] == "fallback"
    assert ts["selection"]["candidates"]["reemitted"]["digest_state"] == "MISMATCH"
    r = c.get("/api/ready").json()
    assert r["checks"]["twin_state_source"]["status"] == "fallback"


def test_run_table_cache_returns_copies_and_tracks_file_identity(tmp_path):
    root = make_root(tmp_path)
    st = ArtifactStore(root)
    rid = st.latest_run_id()
    a = st.run_table(rid, "decision_ranking.csv"); a["rank"] = 1
    b = st.run_table(rid, "decision_ranking.csv")
    assert "rank" not in b.columns and st.cache_stats()["frame_hit"] >= 1
    assert st.ranking_with_horizon(rid, limit=5) and st.ranking_with_horizon(rid, limit=5)   # mutating consumer twice
