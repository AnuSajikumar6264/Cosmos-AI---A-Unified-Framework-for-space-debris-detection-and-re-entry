"""P3-A2 — lazy telemetry metadata, provenance caching with explicit invalidation, run and object caching."""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import numpy as np
import pytest

from cosmos.ai.provenance import ROOT
from cosmos.product import store as S
from cosmos.product.store import ArtifactStore, DataUnavailable

MISSIONS = ROOT / "data/feature1_health/external/esa_ad/prepared"
SNAPSHOT = ROOT / S.TWIN_SNAPSHOT.format(as_of=S.DEFAULT_AS_OF)


# ------------------------------------------------------------------ header-only shapes
@pytest.mark.skipif(not (MISSIONS / "mission3.npz").is_file(), reason="ESA-AD prepared archive absent")
def test_npz_header_shape_equals_full_load_shape():
    p = MISSIONS / "mission3.npz"
    t0 = time.perf_counter()
    header = S._npz_member_shape(p, "X")
    header_ms = (time.perf_counter() - t0) * 1000
    with np.load(p, allow_pickle=True) as a:
        full = a["X"].shape
    assert tuple(header) == tuple(full)
    assert header_ms < 200, header_ms


@pytest.mark.skipif(not (MISSIONS / "mission1.npz").is_file(), reason="ESA-AD prepared archive absent")
def test_missions_listing_never_materialises_the_sample_matrix(monkeypatch):
    requested: list[str] = []
    real = np.lib.npyio.NpzFile.__getitem__

    def spy(self, key):
        requested.append(str(key))
        if str(key) == "X":
            raise AssertionError("missions() must not load the X matrix")
        return real(self, key)

    monkeypatch.setattr(np.lib.npyio.NpzFile, "__getitem__", spy)
    meta = getattr(S, "_mission_meta", None) or getattr(ArtifactStore, "_mission_meta")
    meta.cache_clear()
    st = ArtifactStore(ROOT)
    t0 = time.perf_counter()
    missions = st.missions()
    elapsed = time.perf_counter() - t0
    meta.cache_clear()
    assert missions and all(m["samples"] > 0 for m in missions)
    assert "X" not in requested and requested, requested
    assert elapsed < 2.0, elapsed


# ------------------------------------------------------------------ provenance cache
def _twin_root(tmp_path: Path, content: bytes) -> tuple[Path, Path]:
    d = tmp_path / "outputs/twin/as_of_2026-10-27"
    d.mkdir(parents=True)
    target = d / "forecast_table.csv.gz"
    target.write_bytes(content)
    (tmp_path / S.FORECAST_DIGEST).write_text(f"{hashlib.sha256(content).hexdigest()} forecast_table.csv.gz\n")
    return tmp_path, target


def test_repository_provenance_digest_is_cached_and_invalidated_by_content_not_mtime(tmp_path):
    root, target = _twin_root(tmp_path, b"A" * 4096)
    st = ArtifactStore(root)
    assert st.repository_provenance()["dated_forecast_digest_state"] == "verified"
    assert st.repository_provenance()["dated_forecast_digest_state"] == "verified"
    stats = st.cache_stats()
    assert stats["digest_miss"] == 1 and stats["digest_hit"] == 1 and stats["git_miss"] == 1 and stats["git_hit"] == 1
    # tamper: same size, same mtime
    stat = target.stat()
    target.write_bytes(b"A" * 4095 + b"B")
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert st.repository_provenance()["dated_forecast_digest_state"] == "MISMATCH"
    assert st.cache_stats()["digest_miss"] == 2
    target.write_bytes(b"A" * 4096)
    assert st.repository_provenance()["dated_forecast_digest_state"] == "verified"
    assert st.cache_stats()["git_miss"] == 1                   # the git key did not change: one git invocation so far
    st.invalidate_caches()
    st.repository_provenance()
    assert st.cache_stats()["digest_miss"] == 4 and st.cache_stats()["git_miss"] == 2


def test_large_file_fingerprint_detects_a_middle_edit_only_through_full_verification_on_identity_change(tmp_path):
    # files above 1 MB use a sampled fingerprint plus size+mtime+inode; a write that changes mtime invalidates
    root, target = _twin_root(tmp_path, b"\x00" * (2 << 20))
    st = ArtifactStore(root)
    assert st.repository_provenance()["dated_forecast_digest_state"] == "verified"
    data = bytearray(target.read_bytes()); data[1 << 20] = 1
    target.write_bytes(bytes(data))                 # mtime advances: identity changes, digest recomputed
    assert st.repository_provenance()["dated_forecast_digest_state"] == "MISMATCH"


def test_git_cache_key_follows_the_head_file(tmp_path):
    root, _ = _twin_root(tmp_path, b"x")
    head = root / ".git/HEAD"
    head.parent.mkdir()
    head.write_text("ref: refs/heads/p3a\n")
    st = ArtifactStore(root)
    st.repository_provenance(); st.repository_provenance()
    assert st.cache_stats()["git_hit"] == 1
    time.sleep(0.01)
    head.write_text("ref: refs/heads/other\n")
    st.repository_provenance()
    assert st.cache_stats()["git_miss"] == 2


# ------------------------------------------------------------------ prospective status and run listing
def test_prospective_status_is_cached_until_the_snapshot_directory_changes():
    st = ArtifactStore(ROOT)
    a = st.prospective_status(); b = st.prospective_status()
    assert a == b and st.cache_stats()["prospective_hit"] == 1 and st.cache_stats()["prospective_miss"] == 1


def test_run_listing_parses_each_manifest_once():
    st = ArtifactStore(ROOT)
    n = len(st.list_runs())
    misses = st.cache_stats()["json_miss"]
    t0 = time.perf_counter(); st.list_runs(); warm = (time.perf_counter() - t0) * 1000
    assert st.cache_stats()["json_miss"] == misses and misses <= n
    assert warm < 500, warm


# ------------------------------------------------------------------ catalogue index
@pytest.mark.skipif(not SNAPSHOT.is_file(), reason="forecast snapshot absent")
def test_catalogue_index_lookup_matches_the_table_and_rejects_unknown_objects():
    st = ArtifactStore(ROOT)
    table = st.catalogue()
    for norad in (37607, 23806, 25544, 12):
        rec = st.object_record(norad)
        row = table[table["norad"] == norad].iloc[0]
        assert rec["norad"] == norad and rec["name"] == row["Name"]
    with pytest.raises(DataUnavailable):
        st.object_record(999_999_999)
    t0 = time.perf_counter()
    for norad in table["norad"].head(50):
        st.object_record(int(norad))
    assert (time.perf_counter() - t0) < 10
