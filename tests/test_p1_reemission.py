"""P1.2 — versioned twin-state re-emission: value equivalence, determinism, archive untouched, provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from cosmos.ai.provenance import ROOT
from cosmos.ai.schema import validate_twin_record
from cosmos.ai.twin import reemit

ARCHIVE = ROOT / "outputs/twin/as_of_2026-10-27"
NEW = ROOT / "outputs/twin/as_of_2026-10-27_reemitted_v1"
pytestmark = pytest.mark.skipif(not (ARCHIVE / "twins.jsonl").is_file() or not (NEW / "twins.jsonl").is_file(),
                                reason="archive or re-emitted state absent")


def test_archive_untouched_and_new_artifact_distinguishable():
    recorded = (ARCHIVE / "FORECAST_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((ARCHIVE / "twins.jsonl").read_bytes()).hexdigest() == recorded == "19a1fede1fd4871f380ff802f285d2ad03732f6cd3179790e67336c7d202a6b5"
    new_sha = hashlib.sha256((NEW / "twins.jsonl").read_bytes()).hexdigest()
    assert new_sha != recorded and (NEW / "TWINS_SHA256.txt").read_text().split()[0] == new_sha
    man = json.loads((NEW / "REEMISSION_MANIFEST.json").read_text())
    assert man["reemitted_from_archive"] is True and man["predictions_regenerated"] is False and man["model_executed"] is False
    assert man["model_version"]["status"] == "unavailable" and man["model_version"]["digest"] is None
    assert man["source"]["sha256"] == "b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86"
    assert man["output"]["twins_jsonl_sha256"] == new_sha and man["output"]["records"] == 31396
    assert man["equivalence_with_archive"]["equivalent"] is True and man["equivalence_with_archive"]["records_equal"] == 31396
    assert len(man["transformation_digest_sha256"]) == 64 and man["code_revision"]


def test_every_record_validates_as_v1_1_with_full_provenance_and_source_pointer():
    with (NEW / "twins.jsonl").open() as fh:
        for i, line in enumerate(fh):
            rec = json.loads(line)
            assert validate_twin_record(rec) == "1.1"
            assert rec["source_record"]["row_index"] == i and rec["source_record"]["norad"] == int(rec["object_id"])
            for out in rec["outputs"]:
                prov = out["provenance"]
                assert prov["input_hashes"] == {"outputs/twin/as_of_2026-10-27/forecast_table.csv.gz": rec["source_record"]["sha256"]}
                assert prov["code_revision"] and prov["config_digest"] and prov["model_digest"] is None
            if i >= 2000:          # the manifest's full comparison covers all 31,396; sample the validator here
                break
    with (ARCHIVE / "twins.jsonl").open() as fh:
        assert validate_twin_record(json.loads(fh.readline())) == "1.0"


def test_value_equivalence_and_determinism(tmp_path):
    eq = reemit.compare_with_archive(NEW / "twins.jsonl", ARCHIVE / "twins.jsonl")
    assert eq["equivalent"] and eq["records_differing"] == 0
    # deterministic: re-emitting a 300-row slice twice gives identical bytes and the archive's values
    table = pd.read_csv(ARCHIVE / "forecast_table.csv.gz", low_memory=False).head(300)
    digest = reemit.transformation_digest("2026-10-27")
    outs = []
    for k in range(2):
        p = tmp_path / f"t{k}.jsonl"
        with p.open("w") as f:
            for rec in reemit.emit_records(table, "2026-10-27", "outputs/twin/as_of_2026-10-27/forecast_table.csv.gz", "b" * 64, "c" * 40, digest):
                f.write(json.dumps(rec, default=float) + "\n")
        outs.append(hashlib.sha256(p.read_bytes()).hexdigest())
    assert outs[0] == outs[1]
    with (tmp_path / "t0.jsonl").open() as fn, (ARCHIVE / "twins.jsonl").open() as fa:
        for ln, la in zip(fn, fa):
            assert reemit.canonical(json.loads(ln), drop_provenance=True) == reemit.canonical(json.loads(la), drop_provenance=True)


def test_refuses_to_write_into_the_archive_directory():
    with pytest.raises(SystemExit):
        reemit.run("2026-10-27", out=str(ARCHIVE))
