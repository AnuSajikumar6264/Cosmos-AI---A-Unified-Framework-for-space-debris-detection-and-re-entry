"""Read-only access to COSMOS-AI artifacts for the Mission Intelligence Console.

Every accessor either returns real data read from disk or reports the data as unavailable.
Nothing here generates a measurement, fills a gap, or substitutes one source for another.

Two selectable entity types exist, and they are deliberately **not** joined:

* a **catalogue object**, keyed by NORAD ID, from one CelesTrak/GCAT snapshot;
* a **telemetry channel** of an anonymised ESA-ADB mission.

The ESA-ADB missions and the Kelvins CAC conjunction events are anonymised, so no catalogue
object has telemetry and no conjunction event belongs to a known spacecraft. Asking this
module for telemetry of a NORAD object returns an explicit absence, never a series.
"""
from __future__ import annotations

import hashlib
import time
import json
import re
import zipfile
from datetime import date, datetime, timezone
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..ai import adapters
from ..ai.provenance import ROOT, git_revision, sha256_file
from ..ai.schema import SchemaError, stamp, validate_run_manifest
from ..ai.twin import reader as twin_reader

# ----------------------------------------------------------------- artifact locations
TWIN_SNAPSHOT = adapters.TWIN_SNAPSHOT
PIPELINE_RUNS = "outputs/pipeline"
TELEMETRY_DIR = "data/feature1_health/external/esa_ad/prepared"
SPOTGEO_IMAGES = "data/feature2_debris/spotgeo/raw/extracted/SpotGEOv2"
SPOTGEO_SUBMISSION = adapters.SPOTGEO_SUBMISSION
CONJUNCTION_PREDICTIONS = adapters.CONJUNCTION_PREDICTIONS
TELEMETRY_RESULTS = adapters.TELEMETRY_RESULTS
FORECAST_DIGEST = "outputs/twin/as_of_2026-10-27/FORECAST_SHA256.txt"
#: Twin-state artifacts. The re-emitted file (twin_state/1.1) carries per-output provenance; the archived
#: file (twin_state/1.0) is the historical record and is only ever read as a labelled fallback.
TWIN_STATE_REEMITTED = "outputs/twin/as_of_{as_of}_reemitted_v1/twins.jsonl"
TWIN_STATE_REEMITTED_DIGEST = "outputs/twin/as_of_{as_of}_reemitted_v1/TWINS_SHA256.txt"
REEMISSION_MANIFEST = "outputs/twin/as_of_{as_of}_reemitted_v1/REEMISSION_MANIFEST.json"
#: Twin-state source policies (P3-B): prefer_reemitted (1.1, archived 1.0 as a labelled fallback),
#: reemitted_only (no fallback), archived_only (explicit historical read).
TWIN_SOURCE_POLICIES = twin_reader.POLICIES
DEFAULT_TWIN_SOURCE_POLICY = twin_reader.DEFAULT_POLICY
TWIN_STATE_ARCHIVED = "outputs/twin/as_of_{as_of}/twins.jsonl"
TWIN_STATE_ARCHIVED_DIGEST = "outputs/twin/as_of_{as_of}/FORECAST_SHA256.txt"
_TWIN_LINE_ID = re.compile(rb'^\{"object_id": "(\d+)"')

#: Capability status vocabulary of the evidence-availability strip.
CAPABILITY_STATUSES = ("implemented", "archived_only", "benchmark_only", "blocked", "unavailable")

#: X6 Stage 1 (2026-11-08): observed coverage of the lifetime intervals by area-to-mass source on the
#: archived evaluation origins. Read-only evidence for a reliability cue; never a recalibration.
AM_DESIGN_STAGE1 = "outputs/am_design_stage1/results.json"
#: Exploratory T1 ranking-utility record (decision-priority screen). Absent is a valid state.
RANKING_UTILITY = "outputs/t1_ranking_utility/results.json"

#: Human labels for the area-to-mass source recorded in the forecast table. Absence is "unknown";
#: the console never infers a source.
AM_SOURCE_LABELS = {
    "design": "design-derived (area-to-mass from published design data)",
    "class_prior_sbm": "class prior (area-to-mass drawn from the class's size pool)",
    "class_prior_design": "class prior (area-to-mass drawn from the class's design pool)",
    "unknown": "unknown (not recorded in the snapshot; not inferred)",
}

#: Explicit, verified associations between a module output and a model registry card. There are
#: none today: no fitted model is persisted for any twin module, and no run records which card
#: produced which output, so nothing may be associated.
VERIFIED_MODEL_CARD_ASSOCIATIONS: dict[str, str] = {}

#: What each pipeline module's evidence actually is. Shown on the run page so that independent
#: benchmark roots are never read as an integrated satellite health assessment.
MODULE_EVIDENCE_CLASS = {
    "catalogue_state": "archived dated catalogue snapshot (real CelesTrak/GCAT data)",
    "lifetime": "archived lifetime expert outputs read from the dated forecast table",
    "reentry": "archived dated re-entry forecast read from the forecast table",
    "collision": "archived held-out benchmark predictions on anonymised conjunction events — not linked to any object",
    "health": "archived benchmark-arm detection scores (ESA-ADB) — not a spacecraft health state",
    "debris": "archived classical detections on real SpotGEO frames — no object identity, no time",
    "decision_priority": "ranking computed from the archived re-entry probability and GCAT mass",
    "twin_state": "archived twin-state records read from the selected archive (re-emitted twin_state/1.1 or historical 1.0) — an additional evidence root, nothing regenerated",
    "twin_equivalence": "value comparison of the twin-state records with the catalogue chain of this run — a check, not a prediction",
}

DEFAULT_AS_OF = "2026-10-27"
RUN_ID = re.compile(r"^run_[0-9A-Za-z_\-]+$")
MISSION_ID = re.compile(r"^[123]$")
CHANNEL_ID = re.compile(r"^channel_[0-9]+$")

#: Horizon labels of the dated twin, in days.
HORIZONS = adapters.HORIZON_DAYS

#: Predictive cap of the lifetime/re-entry study, in days (``cosmos.ai.lifetime.physics.CAP_DAYS``).
#: A quantile at the cap means "at least this long", not an estimated lifetime.
CAP_DAYS = 1826.25
_CAP_TOLERANCE = 1e-6


class DataUnavailable(Exception):
    """A requested artifact or record is not present. Carries the reason for display."""

    def __init__(self, message: str, *, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail


class InvalidSelection(Exception):
    """A caller-supplied identifier is malformed or out of range."""


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    started_at: str | None
    as_of: str | None
    successful: bool | None
    git_commit: str | None
    config_sha256: str | None
    module_counts: dict[str, int]
    tables: tuple[str, ...]
    complete: bool
    snapshot_consistent: bool
    as_of_dates: tuple[str, ...]


class ArtifactStore:
    """Read-only view of the repository's artifacts.

    The store never writes. Scenario execution is handled separately by the API, which calls
    the existing orchestrator and writes only into a fresh run directory.
    """

    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root).resolve()
        # Read caches (P3-A). Keys are file identity tuples (size, mtime_ns, inode) plus a content fingerprint,
        # never the modification time alone; see _file_key. invalidate_caches() clears them all.
        self._json_cache: dict[Path, tuple[tuple, str, Any]] = {}
        self._summary_cache: dict[Path, tuple[tuple, Any]] = {}
        self._digest_cache: dict[Path, tuple[tuple, str]] = {}
        self._git_cache: tuple[tuple, dict[str, Any]] | None = None
        self._prospective_cache: tuple[tuple, dict[str, Any]] | None = None
        self._catalogue_index_cache: dict[str, dict[int, int]] = {}
        self._frame_cache: dict[Path, tuple[tuple, Any]] = {}
        self._frame_index_cache: dict[tuple[Path, str], tuple[Any, dict[str, int]]] = {}
        self._column_cache: dict[tuple[str, int], np.ndarray] = {}
        self._twin_selection_cache: dict[tuple, tuple[tuple, dict[str, Any]]] = {}
        self._twin_integration_cache: dict[tuple, tuple[tuple, dict[str, Any]]] = {}
        self.cache_events: dict[str, int] = {"json_hit": 0, "json_miss": 0, "digest_hit": 0, "digest_miss": 0,
                                             "git_hit": 0, "git_miss": 0, "prospective_hit": 0, "prospective_miss": 0,
                                             "frame_hit": 0, "frame_miss": 0, "twin_selection_hit": 0, "twin_selection_miss": 0,
                                             "twin_integration_hit": 0, "twin_integration_miss": 0}

    # ------------------------------------------------------------------- caching
    @staticmethod
    def _file_key(path: Path) -> tuple:
        """Identity of a file for cache keys: size, mtime_ns, inode AND a content fingerprint.

        Small files (<= 1 MB) are fingerprinted by their full SHA-256 on every lookup, so a changed file can
        never reuse a stale entry; large files use the SHA-256 of their first and last 64 KB plus size, which
        detects truncation, appends and header edits at negligible cost.
        """
        st = path.stat()
        h = hashlib.sha256()
        with path.open("rb") as fh:
            if st.st_size <= 1 << 20:
                for chunk in iter(lambda: fh.read(1 << 16), b""):
                    h.update(chunk)
            else:
                h.update(fh.read(1 << 16))
                fh.seek(max(st.st_size - (1 << 16), 0))
                h.update(fh.read(1 << 16))
        return (st.st_size, st.st_mtime_ns, st.st_ino, h.hexdigest())

    #: Parsed JSON documents above this size are not retained (the 5.2 MB historical manifest held ~14 MB of
    #: Python objects for one rarely opened page); they are re-parsed on demand, their summaries stay cached.
    JSON_RETAIN_MAX_BYTES = 1 << 20

    def _cached_json(self, path: Path) -> tuple[Any, str]:
        """Parse a JSON file once per file identity; returns (object, full sha256)."""
        key = self._file_key(path)
        hit = self._json_cache.get(path)
        if hit and hit[0] == key and hit[2] is not None:
            self.cache_events["json_hit"] += 1
            return hit[2], hit[1]
        self.cache_events["json_miss"] += 1
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        digest = hashlib.sha256(raw).hexdigest()
        self._json_cache[path] = (key, digest, obj if len(raw) <= self.JSON_RETAIN_MAX_BYTES else None)
        return obj, digest

    def _cached_digest(self, path: Path) -> str:
        """Full SHA-256 of a file, recomputed whenever its identity (incl. fingerprint) changes."""
        key = self._file_key(path)
        hit = self._digest_cache.get(path)
        if hit and hit[0] == key:
            self.cache_events["digest_hit"] += 1
            return hit[1]
        self.cache_events["digest_miss"] += 1
        digest = sha256_file(path)
        self._digest_cache[path] = (key, digest)
        return digest

    def _git_key(self) -> tuple:
        parts = []
        for rel in (".git/HEAD", ".git/index", ".git/packed-refs"):
            pth = self.root / rel
            parts.append((rel, pth.stat().st_mtime_ns, pth.stat().st_size) if pth.is_file() else (rel, None, None))
        head = self.root / ".git/HEAD"
        if head.is_file():
            ref = head.read_text().strip()
            if ref.startswith("ref: "):
                refp = self.root / ".git" / ref[5:]
                parts.append((ref, refp.stat().st_mtime_ns if refp.is_file() else None))
        return tuple(parts)

    def _cached_git(self) -> dict[str, Any]:
        key = self._git_key()
        if self._git_cache and self._git_cache[0] == key:
            self.cache_events["git_hit"] += 1
            return dict(self._git_cache[1])
        self.cache_events["git_miss"] += 1
        record = git_revision(self.root)
        self._git_cache = (key, record)
        return dict(record)

    def _cached_frame(self, path: Path) -> pd.DataFrame:
        """A run table parsed once per file identity (size, mtime_ns, inode, content fingerprint). Callers get copies."""
        key = self._file_key(path)
        hit = self._frame_cache.get(path)
        if hit and hit[0] == key:
            self.cache_events["frame_hit"] += 1
            return hit[1]
        self.cache_events["frame_miss"] += 1
        frame = pd.read_csv(path)
        self._frame_cache[path] = (key, frame)
        return frame

    def _frame_row(self, path: Path, object_id: str, column: str = "object_id") -> pd.DataFrame:
        """One row of a cached run table by identifier through a per-frame index (built once per frame identity)."""
        frame = self._cached_frame(path)
        hit = self._frame_index_cache.get((path, column))
        if hit is None or hit[0] is not frame:
            index = {str(v): i for i, v in enumerate(frame[column].to_numpy())}
            self._frame_index_cache[(path, column)] = (frame, index)
        else:
            index = hit[1]
        pos = index.get(object_id)
        return frame.iloc[[pos]] if pos is not None else frame.iloc[0:0]

    def _catalogue_rows(self, norad: int, as_of: str) -> pd.DataFrame:
        """The catalogue row of one object through the per-snapshot norad index (empty frame when absent)."""
        table = self.catalogue(as_of)
        index = self._catalogue_index_cache.get(as_of)
        if index is None or len(index) != len(table):
            index = {int(n): i for i, n in enumerate(table["norad"].to_numpy())}
            self._catalogue_index_cache[as_of] = index
        pos = index.get(int(norad))
        return table.iloc[[pos]] if pos is not None else table.iloc[0:0]

    def _file_key_or_none(self, path: Path) -> tuple | None:
        return self._file_key(path) if path.is_file() else None

    def invalidate_caches(self) -> None:
        """Drop every read cache (manifests, digests, git state, prospective status, catalogue index, run tables, twin state)."""
        self._json_cache.clear(); self._summary_cache.clear(); self._digest_cache.clear(); self._git_cache = None
        self._prospective_cache = None; self._catalogue_index_cache.clear(); self._frame_cache.clear()
        self._frame_index_cache.clear(); self._twin_selection_cache.clear(); self._twin_integration_cache.clear()
        self._column_cache.clear()

    def cache_stats(self) -> dict[str, Any]:
        return {**self.cache_events, "json_entries": len(self._json_cache), "digest_entries": len(self._digest_cache),
                "frame_entries": len(self._frame_cache)}

    # ------------------------------------------------------------------ provenance
    def repository_provenance(self) -> dict[str, Any]:
        """Git state and the dated-forecast digest state; both cached by file identity (P3-A2)."""
        record = self._cached_git()
        digest = self.root / FORECAST_DIGEST
        record["dated_forecast_digest_recorded"] = None
        record["dated_forecast_digest_state"] = "absent"
        if digest.is_file():
            text = digest.read_text(encoding="utf-8").strip()
            record["dated_forecast_digest_recorded"] = text
            parts = text.split()
            if len(parts) == 2:
                target = self.root / "outputs/twin/as_of_2026-10-27" / parts[1]
                if target.is_file():
                    record["dated_forecast_digest_state"] = (
                        "verified" if self._cached_digest(target) == parts[0] else "MISMATCH"
                    )
                else:
                    record["dated_forecast_digest_state"] = "file_missing"
        return record

    # ------------------------------------------------------------------------ runs
    def _runs_dir(self) -> Path:
        return self.root / PIPELINE_RUNS

    def list_runs(self) -> list[RunSummary]:
        """All pipeline run directories, newest first. Incomplete runs are included and flagged."""
        base = self._runs_dir()
        if not base.is_dir():
            return []
        summaries = []
        for path in sorted(base.iterdir(), reverse=True):
            if not path.is_dir() or not RUN_ID.match(path.name):
                continue
            summaries.append(self._summarise_run(path))
        return summaries

    def _summarise_run(self, path: Path) -> RunSummary:
        manifest_path = path / "run_manifest.json"
        if manifest_path.is_file():
            key = self._file_key(manifest_path)
            hit = self._summary_cache.get(manifest_path)
            if hit and hit[0] == key:
                return hit[1]
            summary = self._summarise_run_uncached(path)
            self._summary_cache[manifest_path] = (key, summary)
            return summary
        return self._summarise_run_uncached(path)

    def _summarise_run_uncached(self, path: Path) -> RunSummary:
        manifest_path = path / "run_manifest.json"
        if not manifest_path.is_file():
            # A run interrupted before writing its manifest. Reported, never shown as finished.
            return RunSummary(run_id=path.name, started_at=None, as_of=None, successful=None,
                              git_commit=None, config_sha256=None, module_counts={},
                              tables=(), complete=False, snapshot_consistent=True,
                              as_of_dates=())
        try:
            manifest, _digest = self._cached_json(manifest_path)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return RunSummary(run_id=path.name, started_at=None, as_of=None, successful=None,
                              git_commit=None, config_sha256=None, module_counts={},
                              tables=(), complete=False, snapshot_consistent=True, as_of_dates=())
        modules = manifest.get("modules", {}) or {}
        counts: dict[str, int] = {}
        for record in modules.values():
            status = str(record.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
        dates = tuple(sorted({
            record["provenance"]["as_of"]
            for record in modules.values()
            if isinstance(record.get("provenance"), dict) and record["provenance"].get("as_of")
        }))
        return RunSummary(
            run_id=path.name,
            started_at=manifest.get("started_at"),
            as_of=manifest.get("as_of"),
            successful=manifest.get("successful"),
            git_commit=(manifest.get("git") or {}).get("git_commit"),
            config_sha256=manifest.get("config_sha256"),
            module_counts=counts,
            tables=tuple(manifest.get("tables_written") or ()),
            complete=True,
            snapshot_consistent=len(dates) <= 1,
            as_of_dates=dates,
        )

    def run_path(self, run_id: str) -> Path:
        if not RUN_ID.match(run_id or ""):
            raise InvalidSelection(f"malformed run id: {run_id!r}")
        path = self._runs_dir() / run_id
        if not path.is_dir():
            raise DataUnavailable(f"no such pipeline run: {run_id}")
        return path

    def run_manifest(self, run_id: str) -> dict[str, Any]:
        path = self.run_path(run_id) / "run_manifest.json"
        if not path.is_file():
            raise DataUnavailable(
                f"run {run_id} has no run_manifest.json",
                detail="the run did not finish writing its manifest and is incomplete",
            )
        try:
            manifest, _digest = self._cached_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DataUnavailable(f"run {run_id} manifest is not valid JSON", detail=str(exc)) from exc
        try:
            validate_run_manifest(manifest)
        except SchemaError as exc:
            raise DataUnavailable(f"run {run_id} manifest is malformed", detail=str(exc)) from exc
        return manifest

    def run_summary(self, run_id: str) -> RunSummary:
        return self._summarise_run(self.run_path(run_id))

    def latest_run_id(self) -> str | None:
        for summary in self.list_runs():
            if summary.complete:
                return summary.run_id
        return None

    def run_table(self, run_id: str, name: str, limit: int | None = None) -> pd.DataFrame:
        """One CSV written by a run. Tables are never read across runs."""
        if not re.fullmatch(r"[A-Za-z0-9_\-]+\.csv", name or ""):
            raise InvalidSelection(f"malformed table name: {name!r}")
        path = self.run_path(run_id) / name
        if not path.is_file():
            raise DataUnavailable(f"run {run_id} did not write {name}")
        table = self._cached_frame(path)
        return (table.head(limit) if limit else table).copy()

    # ------------------------------------------------------------------ twin state
    @lru_cache(maxsize=4)
    def _twin_index(self, relative: str) -> dict[str, tuple[int, int]]:
        """object_id -> (byte offset, length) of each line of a twins.jsonl, built once per file."""
        path = self.root / relative
        index: dict[str, tuple[int, int]] = {}
        with path.open("rb") as fh:
            offset = 0
            for line in fh:
                m = _TWIN_LINE_ID.match(line)
                oid = m.group(1).decode() if m else str(json.loads(line)["object_id"])
                index[oid] = (offset, len(line))
                offset += len(line)
        return index

    def _twin_line(self, relative: str, object_id: str) -> dict[str, Any] | None:
        loc = self._twin_index(relative).get(object_id)
        if loc is None:
            return None
        with (self.root / relative).open("rb") as fh:
            fh.seek(loc[0])
            return json.loads(fh.read(loc[1]))

    def _twin_candidate_paths(self, as_of: str) -> tuple[Path, ...]:
        paths = []
        for spec in twin_reader.CANDIDATES.values():
            for key in ("artifact", "digest", "manifest"):
                if spec[key]:
                    paths.append(self.root / spec[key].format(as_of=as_of))
        return tuple(paths)

    def twin_selection(self, as_of: str = DEFAULT_AS_OF, policy: str = DEFAULT_TWIN_SOURCE_POLICY,
                       evaluate_all: bool = False) -> dict[str, Any]:
        """Explicit twin-state source selection (P3-B), cached by the identity of every candidate file."""
        if policy not in TWIN_SOURCE_POLICIES:
            raise InvalidSelection(f"unknown twin-source policy {policy!r}; known: {', '.join(TWIN_SOURCE_POLICIES)}")
        ident = tuple(self._file_key_or_none(p) for p in self._twin_candidate_paths(as_of))
        key = (as_of, policy, evaluate_all)
        hit = self._twin_selection_cache.get(key)
        if hit and hit[0] == ident:
            self.cache_events["twin_selection_hit"] += 1
            return json.loads(json.dumps(hit[1]))
        self.cache_events["twin_selection_miss"] += 1
        sel = twin_reader.select_source(self.root, as_of, policy, digest_fn=self._cached_digest, evaluate_all=evaluate_all)
        self._twin_selection_cache[key] = (ident, sel)
        return json.loads(json.dumps(sel))

    def _frame_row_dict(self, path: Path, object_id: str) -> dict[str, Any] | None:
        """One row of a cached run table as a plain dict via the per-frame index, or None when absent."""
        frame = self._cached_frame(path)
        hit = self._frame_index_cache.get((path, "object_id"))
        if hit is None or hit[0] is not frame:
            index = {str(v): i for i, v in enumerate(frame["object_id"].to_numpy())}
            self._frame_index_cache[(path, "object_id")] = (frame, index)
        else:
            index = hit[1]
        pos = index.get(object_id)
        if pos is None:
            return None
        return {c: frame.iat[pos, j] for j, c in enumerate(frame.columns)}

    def _chain_view_for(self, norad: int, as_of: str, run_id: str | None) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """The catalogue chain's view of one object from a run's tables (None when the run lacks the object).

        Scalar lookups through the per-frame indexes; the entry is built by the same helper as the full view.
        """
        meta: dict[str, Any] = {"run_id": run_id, "tables": []}
        if not run_id:
            return None, meta
        object_id = f"NORAD-{int(norad)}"
        cat = self._catalogue_rows(norad, as_of)
        run_dir = self.run_path(run_id)
        present = {name: (run_dir / name).is_file() for name in ("decision_ranking.csv", "reentry_predictions.csv", "lifetime_estimates.csv",
                                                                   "lifetime_noncoherent_horizons.csv")}
        meta["tables"] = [n for n, ok in present.items() if ok]
        if cat.empty or not present["decision_ranking.csv"]:
            return None, meta
        cat_row = {c: cat.iat[0, j] for j, c in enumerate(cat.columns)}
        in_universe = self._frame_row_dict(run_dir / "decision_ranking.csv", object_id) is not None
        re_row = self._frame_row_dict(run_dir / "reentry_predictions.csv", object_id) if present["reentry_predictions.csv"] else None
        li_row = self._frame_row_dict(run_dir / "lifetime_estimates.csv", object_id) if present["lifetime_estimates.csv"] else None
        noncoherent = (present["lifetime_noncoherent_horizons.csv"]
                       and self._frame_row_dict(run_dir / "lifetime_noncoherent_horizons.csv", object_id) is not None)
        view = twin_reader.chain_view_for_object(cat_row, in_universe, re_row, li_row,
                                                 present["reentry_predictions.csv"], present["lifetime_estimates.csv"], noncoherent)
        return view, meta

    def twin_record(self, norad: int, as_of: str = DEFAULT_AS_OF, policy: str = DEFAULT_TWIN_SOURCE_POLICY,
                    run_id: str | None = None) -> dict[str, Any]:
        """The object's twin-state record read from the source chosen by an explicit policy (P3-B).

        ``source`` is "reemitted" (twin_state/1.1, provenance on every output), "archived" (twin_state/1.0,
        historical record, no output provenance — a labelled fallback or an explicit archived read) or None.
        ``selection`` records the policy, the verdict on every candidate and why the source was chosen.
        ``equivalence`` compares the record's shared values with the latest run's catalogue-chain tables.
        """
        from ..ai.schema import validate_twin_record
        object_id = str(int(norad))
        sel = self.twin_selection(as_of, policy)
        selection_view = {k: sel[k] for k in ("policy", "selected", "status", "fallback_used", "fallback_permitted", "reason")}
        selection_view["candidates"] = {
            name: {k: c.get(k) for k in ("status", "artifact", "present", "digest_state", "schema_version", "record_count",
                                         "artifact_provenance_complete", "provenance_on_outputs", "reasons", "warnings")}
            for name, c in sel["candidates"].items()}
        out: dict[str, Any] = {"available": False, "source": None, "fallback": {"used": False, "reason": None},
                               "record": None, "schema_version": None, "artifact": None, "artifact_recorded_sha256": None,
                               "artifact_sha256": None, "digest_state": None, "reemission": None, "selection": selection_view,
                               "equivalence": {"status": "unavailable", "reason": "no twin record"},
                               "model_version": model_version_unavailable(
                                   "no fitted model is persisted; the twin state is re-emitted from the archived forecast")}
        if sel["selected"] is None:
            out["fallback"] = {"used": False, "reason": sel["reason"]}
            return out
        source = sel["selected"]
        cand = sel["candidates"][source]
        relative = cand["artifact"]
        rec = self._twin_line(relative, object_id)
        if rec is None:
            out.update({"source": source, "artifact": relative, "schema_version": cand.get("schema_version"),
                        "fallback": {"used": sel["fallback_used"], "reason": sel["reason"] if sel["fallback_used"] else None},
                        "missing_record": (f"object {object_id} has no record in the selected source {relative}; no other source is "
                                           f"consulted per object under policy {policy}")})
            return out
        try:
            version = validate_twin_record(rec)
        except Exception as exc:  # malformed record: say so, never repair
            out.update({"available": False, "source": source, "artifact": relative,
                        "fallback": {"used": sel["fallback_used"], "reason": sel["reason"] if sel["fallback_used"] else None},
                        "malformed": f"record failed twin_state validation: {exc}"})
            return out
        out.update({"available": True, "source": source, "record": rec, "schema_version": f"twin_state/{version}",
                    "artifact": relative, "artifact_recorded_sha256": cand.get("recorded_sha256"),
                    "artifact_sha256": cand.get("computed_sha256"), "digest_state": cand.get("digest_state"),
                    "record_count": cand.get("record_count"), "original_or_reemitted": cand.get("kind"),
                    "provenance_on_outputs": all(isinstance(o.get("provenance"), dict) for o in rec["outputs"]),
                    "reemitted_from_archive": bool(rec.get("reemitted_from_archive")),
                    "source_record": rec.get("source_record"),
                    "transformation_digest_sha256": cand.get("transformation_digest_sha256")})
        if cand.get("model_version", {}).get("status") == "recorded":
            out["model_version"] = {"status": "recorded", "digest": cand["model_version"]["digest"], "label": None,
                                    "reason": None, "registry_card": None}
        if source == "reemitted":
            man_path = self.root / REEMISSION_MANIFEST.format(as_of=as_of)
            if man_path.is_file():
                man = json.loads(man_path.read_text(encoding="utf-8"))
                out["reemission"] = {k: man.get(k) for k in ("method", "transformation_digest_sha256", "code_revision", "generated_at",
                                                              "predictions_regenerated", "model_executed")}
                out["reemission"]["source"] = man.get("source"); out["reemission"]["archived_state"] = man.get("archived_state")
                out["reemission"]["equivalence_with_archive"] = {k: v for k, v in (man.get("equivalence_with_archive") or {}).items()
                                                                 if k != "first_difference"}
            out["fallback"] = {"used": False, "reason": None}
        else:
            out["fallback"] = {"used": sel["fallback_used"], "reason": sel["reason"] if sel["fallback_used"] else None}
            out["note"] = ("HISTORICAL ARCHIVE (twin_state/1.0): this record predates per-output provenance; values are "
                           "the archived forecast's, lineage is by value only"
                           + ("" if sel["fallback_used"] else " — selected explicitly by policy archived_only"))
        # equivalence of this record's shared values with the latest run's catalogue chain (display only)
        try:
            run_id = run_id or self.latest_run_id()
            chain, meta = self._chain_view_for(norad, as_of, run_id)
            if run_id is None:
                out["equivalence"] = {"status": "unavailable", "reason": "no complete pipeline run to compare against", "run_id": None}
            else:
                cmp = twin_reader.compare_record(rec, chain)
                out["equivalence"] = {**cmp, "run_id": run_id, "chain_tables": meta["tables"]}
        except Exception as exc:  # never let the comparison take the record down; say what happened
            out["equivalence"] = {"status": "unavailable", "reason": f"comparison failed: {type(exc).__name__}: {exc}"}
        return out

    def twin_state_integration(self, as_of: str = DEFAULT_AS_OF, policy: str = DEFAULT_TWIN_SOURCE_POLICY,
                               run_id: str | None = None) -> dict[str, Any]:
        """Whole-archive twin-state integration status: selection, provenance, integrity, equivalence (P3-B).

        Streams the selected archive once (no record is retained); cached by the identity of the candidate
        files and of the run's tables. Nothing is regenerated or repaired; every verdict carries its reason.
        """
        run_id = run_id or self.latest_run_id()
        sel = self.twin_selection(as_of, policy, evaluate_all=True)
        table_paths = tuple(self.run_path(run_id) / n for n in ("decision_ranking.csv", "reentry_predictions.csv", "lifetime_estimates.csv",
                                                                "lifetime_noncoherent_horizons.csv")) if run_id else ()
        ident = tuple(self._file_key_or_none(p) for p in self._twin_candidate_paths(as_of) + table_paths)
        key = (as_of, policy, run_id)
        hit = self._twin_integration_cache.get(key)
        if hit and hit[0] == ident:
            self.cache_events["twin_integration_hit"] += 1
            return json.loads(json.dumps(hit[1]))
        self.cache_events["twin_integration_miss"] += 1
        started = time.perf_counter()
        out: dict[str, Any] = {"schema_version": stamp("api"), "as_of": as_of, "policy": policy, "selection": sel,
                               "selected_source": sel["selected"], "selection_status": sel["status"],
                               "provenance": None, "integrity": None, "equivalence": None,
                               "model_version": model_version_unavailable("no fitted model is persisted; none is inferred"),
                               "note": ("archived evidence only: the twin state is read from a saved archive; no live feed, no "
                                        "prediction regenerated, no model executed at request time")}
        if sel["selected"] is None:
            out["integrity"] = {"status": "unavailable", "reason": sel["reason"]}
            out["equivalence"] = {"status": "unavailable", "reason": "no twin-state source selected"}
            out["overall"] = {"status": "unavailable", "tone": "bad", "label": "NO TWIN-STATE SOURCE", "reason": sel["reason"]}
            out["computed_in_s"] = round(time.perf_counter() - started, 3)
            self._twin_integration_cache[key] = (ident, out)
            return json.loads(json.dumps(out))
        cand = sel["candidates"][sel["selected"]]
        out["provenance"] = {k: cand.get(k) for k in (
            "source", "kind", "artifact", "schema_version", "expected_schema", "recorded_sha256", "computed_sha256", "digest_state",
            "transformation_digest_sha256", "method", "code_revision", "record_count", "recorded_record_count", "record_count_state",
            "predictions_regenerated", "model_executed", "artifact_provenance_complete", "provenance_on_outputs", "provenance_complete",
            "warnings")}
        out["provenance"]["original_or_reemitted"] = cand.get("kind")
        if cand.get("model_version", {}).get("status") == "recorded":
            out["model_version"] = {"status": "recorded", "digest": cand["model_version"]["digest"], "label": None, "reason": None,
                                    "registry_card": None}
        path = self.root / cand["artifact"]
        # chain view of the run (all objects) for the streaming comparison
        chain_view: dict[str, Any] | None = None
        eq_meta: dict[str, Any] = {"run_id": run_id, "chain_tables": []}
        if run_id:
            frames = {}
            for name in ("decision_ranking.csv", "reentry_predictions.csv", "lifetime_estimates.csv", "lifetime_noncoherent_horizons.csv"):
                p = self.run_path(run_id) / name
                frames[name] = self._cached_frame(p) if p.is_file() else None
                if frames[name] is not None:
                    eq_meta["chain_tables"].append(name)
            if frames["decision_ranking.csv"] is not None:
                chain_view = twin_reader.chain_view_from_tables(self.catalogue(as_of), frames["decision_ranking.csv"],
                                                                frames["reentry_predictions.csv"], frames["lifetime_estimates.csv"],
                                                                frames["lifetime_noncoherent_horizons.csv"])
        acc = twin_reader.EquivalenceAccumulator(set(chain_view or {}))

        def on_record(rec, n, offset, length):
            if chain_view is not None:
                acc.add(twin_reader.compare_record(rec, chain_view.get(str(rec.get("object_id")))))

        out["integrity"] = twin_reader.validate_archive(path, on_record=on_record)
        if out["integrity"]["unique_identities"] != cand.get("record_count"):
            out["integrity"]["record_count_note"] = (f"{cand.get('record_count')} lines, {out['integrity']['unique_identities']} unique valid identities")
        if chain_view is None:
            out["equivalence"] = {"status": "unavailable", "run_id": run_id,
                                  "reason": ("no complete pipeline run to compare against" if not run_id else
                                             f"run {run_id} has no decision_ranking.csv (catalogue chain incomplete)")}
        else:
            out["equivalence"] = {**acc.summary(), **eq_meta, "status": "computed"}
        del chain_view
        # overall verdict: never a plain green when the source is a fallback / explicit archive or provenance is incomplete
        integ_ok = out["integrity"]["status"] == "ok"
        eq = out["equivalence"]
        eq_ok = eq.get("status") == "computed" and eq.get("equivalent") is True
        if sel["status"] == "primary" and cand.get("provenance_complete") and integ_ok and eq_ok:
            overall = {"status": "primary_verified", "tone": "ok", "label": "RE-EMITTED · twin_state/1.1 · verified",
                       "reason": "preferred source, digest verified, provenance complete, records valid, equivalent to the catalogue chain"}
        elif sel["status"] == "primary":
            why = []
            if not cand.get("provenance_complete"): why.append("provenance incomplete")
            if not integ_ok: why.append(f"integrity {out['integrity']['status']}")
            if not eq_ok: why.append("equivalence " + (str(eq.get("status")) if eq.get("status") != "computed" else "not established"))
            overall = {"status": "primary_with_findings", "tone": "warn", "label": "RE-EMITTED · twin_state/1.1 · FINDINGS",
                       "reason": "; ".join(why)}
        elif sel["status"] in ("fallback", "explicit_archived"):
            overall = {"status": sel["status"], "tone": "warn",
                       "label": ("HISTORICAL ARCHIVE · twin_state/1.0 · FALLBACK" if sel["status"] == "fallback"
                                 else "HISTORICAL ARCHIVE · twin_state/1.0 · explicit"),
                       "reason": sel["reason"] + "; no per-output provenance in this source"}
        else:
            overall = {"status": "unavailable", "tone": "bad", "label": "NO TWIN-STATE SOURCE", "reason": sel["reason"]}
        out["overall"] = overall
        out["computed_in_s"] = round(time.perf_counter() - started, 3)
        out["computed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._twin_integration_cache[key] = (ident, out)
        return json.loads(json.dumps(out))

    # ------------------------------------------------------------- run comparison (Phase B.6)
    COMPARE_MAX_BYTES = 12 << 20          # tables above this are compared by digest only (byte-identity), never merged

    def compare_runs(self, a: str, b: str) -> dict[str, Any]:
        """Value-level comparison of two runs' tables, by key column, with incomparability stated explicitly.

        Rules: runs with different ``as_of`` are not value-compared (different populations); a table absent from
        either run is reported as not compared with the reason; byte-identical tables are IDENTICAL without
        parsing; otherwise rows are joined on the key column (first column) and every shared column is compared
        (numeric tolerance 1e-9, NaN equals NaN). Nothing is merged across runs or written anywhere.
        """
        import math
        left, right = self.run_manifest(a), self.run_manifest(b)
        lcfg, rcfg = left.get("config") or {}, right.get("config") or {}
        out: dict[str, Any] = {
            "a": a, "b": b, "as_of": [left.get("as_of"), right.get("as_of")],
            "comparable": left.get("as_of") == right.get("as_of"),
            "config_differences": {k: [lcfg.get(k), rcfg.get(k)] for k in sorted(set(lcfg) | set(rcfg)) if lcfg.get(k) != rcfg.get(k)},
            "module_status": [{"module": m, "a": (left.get("modules", {}).get(m) or {}).get("status", "absent"),
                               "b": (right.get("modules", {}).get(m) or {}).get("status", "absent")}
                              for m in sorted(set(left.get("modules", {})) | set(right.get("modules", {})))],
            "tables": {}, "note": None,
        }
        for row in out["module_status"]:
            row["same"] = row["a"] == row["b"]
        if not out["comparable"]:
            out["note"] = ("the runs use different snapshots, so their values describe different populations and are not "
                           "compared; only provenance and module status are shown")
            return out
        names = sorted(set(left.get("tables_written") or []) | set(right.get("tables_written") or []))
        for name in names:
            pa, pb = self.run_path(a) / name, self.run_path(b) / name
            rec: dict[str, Any] = {"table": name, "status": None, "reason": None}
            if not pa.is_file() or not pb.is_file():
                rec["status"] = "not_compared"
                rec["reason"] = f"table absent from run {a if not pa.is_file() else b}"
                out["tables"][name] = rec
                continue
            if self._cached_digest(pa) == self._cached_digest(pb):
                rec.update({"status": "identical", "reason": "byte-identical files (same SHA-256)", "rows": None})
                out["tables"][name] = rec
                continue
            if max(pa.stat().st_size, pb.stat().st_size) > self.COMPARE_MAX_BYTES:
                rec.update({"status": "not_compared", "reason": "files differ and exceed the interactive comparison size; compare offline"})
                out["tables"][name] = rec
                continue
            fa, fb = self._cached_frame(pa), self._cached_frame(pb)
            key = fa.columns[0]
            if key != fb.columns[0]:
                rec.update({"status": "not_compared", "reason": f"key columns differ ({key} vs {fb.columns[0]})"})
                out["tables"][name] = rec
                continue
            ka, kb = fa[key].astype(str), fb[key].astype(str)
            only_a, only_b = sorted(set(ka) - set(kb), key=str), sorted(set(kb) - set(ka), key=str)
            shared_cols = [c for c in fa.columns if c in fb.columns and c != key]
            ia = fa.set_index(ka); ib = fb.set_index(kb)
            common = ia.index.intersection(ib.index)
            la, lb = ia.loc[common, shared_cols], ib.loc[common, shared_cols]
            per_col: dict[str, dict[str, Any]] = {}
            diff_mask = None
            for c in shared_cols:
                va, vb = la[c].to_numpy(), lb[c].to_numpy()
                if la[c].dtype.kind in "fiu" and lb[c].dtype.kind in "fiu":
                    va, vb = va.astype(float), vb.astype(float)
                    both_nan = (va != va) & (vb != vb)
                    close = (abs(va - vb) <= 1e-9 + 1e-9 * abs(vb)) | both_nan
                    max_abs = float(max((abs(x - y) for x, y, k in zip(va, vb, close) if not k and x == x and y == y), default=0.0))
                else:
                    close = (la[c].astype(str).to_numpy() == lb[c].astype(str).to_numpy())
                    max_abs = None
                n_diff = int((~close).sum())
                if n_diff:
                    per_col[c] = {"different": n_diff, "max_abs_difference": max_abs}
                diff_mask = (~close) if diff_mask is None else (diff_mask | ~close)
            n_common = int(len(common)); n_diff_rows = int(diff_mask.sum()) if diff_mask is not None else 0
            examples = []
            if n_diff_rows:
                for kid in common[diff_mask][:10]:
                    row = {"key": str(kid)}
                    for c in per_col:
                        xa, xb = la.at[kid, c], lb.at[kid, c]
                        if isinstance(xa, float) and isinstance(xb, float) and (math.isnan(xa) and math.isnan(xb)):
                            continue
                        if str(xa) != str(xb):
                            row[c] = [None if (isinstance(xa, float) and math.isnan(xa)) else (xa.item() if hasattr(xa, "item") else xa),
                                      None if (isinstance(xb, float) and math.isnan(xb)) else (xb.item() if hasattr(xb, "item") else xb)]
                    examples.append(row)
            rec.update({"status": "differences" if (n_diff_rows or only_a or only_b) else "equal_values",
                        "reason": None, "key": key, "rows_a": int(len(fa)), "rows_b": int(len(fb)), "rows_common": n_common,
                        "only_in_a": len(only_a), "only_in_b": len(only_b), "only_in_a_examples": only_a[:10], "only_in_b_examples": only_b[:10],
                        "rows_equal": n_common - n_diff_rows, "rows_different": n_diff_rows,
                        "columns_compared": shared_cols, "columns_not_shared": sorted(set(fa.columns) ^ set(fb.columns)),
                        "differing_columns": per_col, "examples": examples})
            if name == "decision_ranking.csv" and n_common:
                ra = {k: i + 1 for i, k in enumerate(ka)}; rb = {k: i + 1 for i, k in enumerate(kb)}
                moves = sorted(((abs(ra[k] - rb[k]), k, ra[k], rb[k]) for k in common), reverse=True)
                rec["rank_changes"] = {"objects_moved": sum(1 for m in moves if m[0]), "max_abs_rank_change": moves[0][0] if moves else 0,
                                       "top_movers": [{"key": k, "rank_a": x, "rank_b": y} for d, k, x, y in moves[:10] if d]}
            out["tables"][name] = rec
        return out

    # ------------------------------------------------------------- decision priority
    def priority_for_object(self, run_id: str | None, norad: int) -> dict[str, Any]:
        """The object's decision-priority row of a run, explained from that run's manifest only.

        Nothing is recomputed: the inputs and the score come from the run's ``decision_ranking.csv``; the
        rule and its constants come from the manifest's ``decision_priority.outputs``; when the manifest
        does not record the rule (runs before 2026-11-08), the explanation is reported unavailable.
        """
        object_id = f"NORAD-{int(norad)}"
        out: dict[str, Any] = {"run_id": run_id, "status": "unavailable", "row": None, "rank": None, "ranked_objects": None,
                               "rule": {"status": "unavailable", "reason": "no run"}, "health_escalation": None, "module_status": None,
                               "explanation": None}
        if not run_id:
            out["reason"] = "no complete pipeline run is present"
            return out
        try:
            manifest = self.run_manifest(run_id)
        except DataUnavailable as exc:
            out["reason"] = exc.message
            return out
        module = (manifest.get("modules") or {}).get("decision_priority") or {}
        out["module_status"] = module.get("status", "unknown")
        if module.get("status") != "success":
            out["status"] = "blocked" if module.get("status") == "blocked" else "unavailable"
            out["reason"] = (f"decision_priority was {module.get('status', 'not recorded')} in this run"
                             + (f": {module.get('reason') or module.get('error')}" if module.get("reason") or module.get("error") else ""))
            return out
        outputs = module.get("outputs") or {}
        rule = outputs.get("priority_rule")
        out["rule"] = ({"status": "recorded", **rule} if isinstance(rule, dict) else
                       {"status": "unavailable", "consequence_mass_kg": outputs.get("consequence_mass_kg"),
                        "reason": ("the priority rule itself is not recorded in this run's manifest (only consequence_mass_kg "
                                   "is; runs written before 2026-11-08); the rule is not reconstructed here")})
        esc = module.get("health_escalation") or {}
        out["health_escalation"] = {"status": esc.get("status"), "reason": esc.get("reason")} if esc else None
        try:
            table = self.run_table(run_id, "decision_ranking.csv")
        except DataUnavailable as exc:
            out["reason"] = exc.message
            return out
        hit = table.index[table["object_id"] == object_id]
        out["ranked_objects"] = int(len(table))
        if len(hit) == 0:
            out["reason"] = f"{object_id} is not in this run's ranking (the run may have been limited to fewer objects)"
            return out
        row = {k: (None if (isinstance(v, float) and v != v) else v) for k, v in table.iloc[int(hit[0])].to_dict().items()}
        out.update({"status": "computed", "row": row, "rank": int(hit[0]) + 1})
        if out["rule"]["status"] == "recorded":
            out["explanation"] = (f"rank {out['rank']} of {out['ranked_objects']}: {rule['formula']}; inputs recorded in the run: "
                                  f"p_reentry_30d = {row.get('p_reentry_30d')}, mass_kg = {row.get('mass_kg')} "
                                  f"({'known' if row.get('mass_known') else 'unknown — multiplier never applied'}), "
                                  f"high_consequence = {row.get('high_consequence')} (threshold {rule.get('consequence_mass_kg')} kg, "
                                  f"multiplier {rule.get('consequence_multiplier')}); recorded priority_score = {row.get('priority_score')}. "
                                  f"{rule.get('semantics')}")
        else:
            out["explanation"] = (f"rank {out['rank']} of {out['ranked_objects']}; recorded priority_score = {row.get('priority_score')} from "
                                  f"p_reentry_30d = {row.get('p_reentry_30d')}, mass_kg = {row.get('mass_kg')}, "
                                  f"high_consequence = {row.get('high_consequence')}; the rule is not recorded in this run's manifest")
        return out

    # ------------------------------------------------------------ evidence availability
    def evidence_availability(self, record: dict[str, Any], run_id: str | None) -> list[dict[str, Any]]:
        """Per-capability status for one object: implemented / archived_only / benchmark_only / blocked / unavailable."""
        statuses: dict[str, str] = {}
        modules_rec: dict[str, Any] = {}
        if run_id:
            try:
                modules_rec = dict(self.run_manifest(run_id).get("modules") or {})
                statuses = {k: v.get("status", "unknown") for k, v in modules_rec.items()}
            except DataUnavailable:
                statuses = {}
        def mod(name: str, implemented_detail: str) -> dict[str, Any]:
            st = statuses.get(name)
            if st == "success":
                return {"status": "implemented", "detail": implemented_detail}
            if st in ("blocked", "failed"):
                return {"status": "blocked", "detail": f"module {name} was {st} in run {run_id}"}
            return {"status": "unavailable", "detail": f"module {name} did not run ({st or 'no run'})"}
        lifetime_ok = record["lifetime"]["available"] and record["lifetime"]["horizon_coherence"]["status"] != "incoherent"
        reentry_ok = record["reentry"]["lo90_days"] is not None
        caps = [
            {"capability": "catalogue identity and mean elements", **mod("catalogue_state", "read from the dated snapshot at run time (NORAD-keyed)")},
            {"capability": "lifetime interval and horizon probabilities",
             **(mod("lifetime", "read from the dated snapshot at run time") if lifetime_ok else
                {"status": "unavailable", "detail": "lifetime expert abstained for this object (" + record["lifetime"]["horizon_coherence"]["detail"] + ")"})},
            {"capability": "re-entry probabilities and time quantiles",
             **(mod("reentry", "read from the dated snapshot at run time") if reentry_ok else
                {"status": "unavailable", "detail": record["reentry"].get("evidence_status", "no drag forecast for this object")})},
            {"capability": "decision priority", **mod("decision_priority", "ordering computed at run time from p_30d and GCAT mass")},
            {"capability": "versioned twin state", **_twin_capability(modules_rec, run_id)},
            {"capability": "telemetry anomaly evidence", "status": "benchmark_only",
             "detail": "ESA-ADB benchmark arms exist, but no telemetry is linkable to this object"},
            {"capability": "conjunction / collision risk", "status": "benchmark_only",
             "detail": "Kelvins CAC events are anonymised; none is attributable to this object"},
            {"capability": "debris detections", "status": "benchmark_only",
             "detail": "SpotGEO detections are pixel positions without object identity or time"},
            {"capability": "spacecraft subsystem health", "status": "unavailable",
             "detail": "not determinable: no telemetry is linkable to this object and no score is synthesised"},
            {"capability": "state vector / impact location / footprint", "status": "unavailable",
             "detail": "the catalogue publishes mean elements only; no validated impact location exists"},
        ]
        for c in caps:
            assert c["status"] in CAPABILITY_STATUSES
        return caps

    def ranking_with_horizon(self, run_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """Top rows of a run's decision ranking with an interval-versus-horizon cue, computed at read time.

        The cue joins ``decision_ranking.csv`` with the same run's ``reentry_predictions.csv`` on
        ``object_id`` and classifies the 5-95 % re-entry interval against the 30-day horizon.
        Display only: the ranking order, the priority scores and every prediction value are the run's.
        """
        ranking = self.run_table(run_id, "decision_ranking.csv")
        ranking = ranking.reset_index(drop=True)
        ranking.insert(0, "rank", ranking.index + 1)
        try:
            reentry = self.run_table(run_id, "reentry_predictions.csv")[["object_id", "days_q05", "days_q50", "days_q95"]]
            merged = ranking.head(limit).merge(reentry, on="object_id", how="left")
        except DataUnavailable:
            merged = ranking.head(limit).assign(days_q05=None, days_q50=None, days_q95=None)
        rows = []
        for r in merged.to_dict(orient="records"):
            rel = horizon_relation(_finite(r.get("days_q05")), _finite(r.get("days_q50")), _finite(r.get("days_q95")),
                                   p_horizon=_finite(r.get("p_reentry_30d")))
            rows.append({**{k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items()}, "horizon_relation": rel})
        return rows

    # ------------------------------------------------------------------- catalogue
    @lru_cache(maxsize=2)
    def _catalogue(self, as_of: str) -> pd.DataFrame:
        relative = TWIN_SNAPSHOT.format(as_of=as_of)
        path = self.root / relative
        if not path.is_file():
            raise DataUnavailable(
                f"no catalogue snapshot for {as_of}",
                detail=f"expected {relative}",
            )
        table = pd.read_csv(path)
        table["norad"] = table["norad"].astype(int)
        return table

    @lru_cache(maxsize=1)
    def subgroup_coverage_evidence(self) -> dict[str, Any] | None:
        """The X6 Stage 1 record, or None when it is not present (never substituted)."""
        path = self.root / AM_DESIGN_STAGE1
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @lru_cache(maxsize=1)
    def ranking_utility_evidence(self) -> dict[str, Any] | None:
        """The exploratory T1 ranking-utility record, or None when it is not present.

        Read-only, never substituted, exactly like :meth:`subgroup_coverage_evidence`. The record is
        non-blind by construction (the T1 window was analysed before) and says so in its own fields.
        """
        path = self.root / RANKING_UTILITY
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def catalogue(self, as_of: str = DEFAULT_AS_OF) -> pd.DataFrame:
        return self._catalogue(as_of)

    def catalogue_provenance(self, as_of: str = DEFAULT_AS_OF) -> dict[str, Any]:
        relative = TWIN_SNAPSHOT.format(as_of=as_of)
        path = self.root / relative
        if not path.is_file():
            raise DataUnavailable(f"no catalogue snapshot for {as_of}")
        return {
            "artifact": relative,
            "sha256": sha256_file(path),
            "as_of": as_of,
            "objects": int(len(self.catalogue(as_of))),
            "sources": ["CelesTrak SATCAT snapshot", "GCAT catalogue", "CelesTrak SW-All"],
        }

    def catalogue_overview(self, as_of: str = DEFAULT_AS_OF) -> dict[str, Any]:
        table = self.catalogue(as_of)
        classes = {"P": "payload", "R": "rocket body", "C": "component", "D": "fragment"}
        return {
            "as_of": as_of,
            "objects": int(len(table)),
            "by_regime": {str(k): int(v) for k, v in table["regime"].value_counts().items()},
            "by_class": {classes.get(str(k), str(k)): int(v)
                         for k, v in table["type1"].value_counts().items()},
            "with_mass": int(table["mass"].notna().sum()),
            "with_lifetime_estimate": int(table["median_days_lifetime"].notna().sum()),
            "expected_reentries_30d": float(table["p_30d"].sum(skipna=True)),
            "objects_p30d_above_half": int((table["p_30d"] > 0.5).sum()),
        }

    def search_objects(self, query: str = "", as_of: str = DEFAULT_AS_OF,
                       limit: int = 50) -> list[dict[str, Any]]:
        """Search the catalogue by NORAD ID or object name substring."""
        table = self.catalogue(as_of)
        text = (query or "").strip()
        if not text:
            # No query: show the objects a user most likely wants, highest 30-day probability.
            selected = table.sort_values("p_30d", ascending=False, na_position="last").head(limit)
        elif text.isdigit():
            selected = table[table["norad"].astype(str).str.startswith(text)].head(limit)
        else:
            mask = table["Name"].astype(str).str.contains(re.escape(text), case=False, na=False)
            selected = table[mask].head(limit)
        return [{
            "norad": int(row.norad),
            "name": str(row.Name),
            "object_class": str(row.type1),
            "regime": str(row.regime),
            "perigee_km": _finite(row.perigee),
            "apogee_km": _finite(row.apogee),
            "inclination_deg": _finite(row.inc),
            "p_reentry_30d": _finite(row.p_30d),
        } for row in selected.itertuples(index=False)]

    def object_record(self, norad: int, as_of: str = DEFAULT_AS_OF,
                      twin_policy: str = DEFAULT_TWIN_SOURCE_POLICY) -> dict[str, Any]:
        """Everything the snapshot holds for one catalogue object, with explicit absences."""
        try:
            norad = int(norad)
        except (TypeError, ValueError) as exc:
            raise InvalidSelection(f"NORAD id must be an integer: {norad!r}") from exc
        rows = self._catalogue_rows(norad, as_of)
        if rows.empty:
            raise DataUnavailable(
                f"NORAD {norad} is not in the {as_of} snapshot",
                detail="the object may have decayed, never existed, or lie outside the "
                       "snapshot's perigee < 2000 km selection",
            )
        row = rows.iloc[0]

        # Mean elements only. A state vector is deliberately not derived: the catalogue does
        # not contain one, and computing one would invent information.
        elements = {
            "perigee_altitude_km": _finite(row["perigee"]),
            "apogee_altitude_km": _finite(row["apogee"]),
            "inclination_deg": _finite(row["inc"]),
            "reference_radius_km": 6378.137,
            "element_set": "catalogue mean elements",
            "state_vector": None,
            "state_vector_note": ("not available: the catalogue publishes mean elements, not an "
                                  "instantaneous position and velocity"),
            "epoch_note": "elements as published in the snapshot; canonical-orbit epoch may differ",
            "t0_canonical": _text(row.get("t0_canonical")),
        }
        physical = {
            "mass_kg": _finite(row["mass"]),
            "rcs_m2": _finite(row["rcs_m2"]),
            "area_to_mass_source": _text(row.get("am_source")) or "unknown",
        }
        physical["area_to_mass_source_label"] = AM_SOURCE_LABELS.get(
            physical["area_to_mass_source"], f"{physical['area_to_mass_source']} (unrecognised source code)")
        lifetime = {
            "median_days": _finite(row.get("median_days_lifetime")),
            "lo90_days": _finite(row.get("lifetime_lo90_days")),
            "hi90_days": _finite(row.get("lifetime_hi90_days")),
            "horizon_probabilities": {
                "30d": _finite(row.get("p_lifetime_30d")),
                "90d": _finite(row.get("p_lifetime_90d")),
                "1yr": _finite(row.get("p_lifetime_1yr")),
            },
            "available": _finite(row.get("median_days_lifetime")) is not None,
        }
        lifetime["horizon_coherence"] = _coherence(lifetime["horizon_probabilities"])
        lifetime["interval_quality"] = interval_quality(
            lifetime["lo90_days"], lifetime["median_days"], lifetime["hi90_days"])
        lifetime["subgroup_coverage"] = subgroup_coverage_cue(
            physical["area_to_mass_source"], self.subgroup_coverage_evidence())
        lifetime["horizon_relation"] = horizon_relation(
            lifetime["lo90_days"], lifetime["median_days"], lifetime["hi90_days"],
            p_horizon=lifetime["horizon_probabilities"]["30d"], quantity="lifetime")
        reentry = {
            "probability_by_horizon": {
                "30d": _finite(row.get("p_30d")),
                "90d": _finite(row.get("p_90d")),
                "1yr": _finite(row.get("p_1yr")),
            },
            "median_days": _finite(row.get("median_days")),
            "lo90_days": _finite(row.get("lo90_days")),
            "hi90_days": _finite(row.get("hi90_days")),
            "lo80_days": _finite(row.get("lo80_days")),
            "hi80_days": _finite(row.get("hi80_days")),
            "variants": {
                "physics_prior_30d": _finite(row.get("p_physics_prior_30d")),
                "physics_history_30d": _finite(row.get("p_physics_history_30d")),
                "lifetime_30d": _finite(row.get("p_lifetime_30d")),
            },
            "history_kind": _text(row.get("history_kind")),
            "history_days": _finite(row.get("history_days")),
            "uncertainty_kind": "physics Monte-Carlo quantiles",
            "uncertainty_note": ("Monte-Carlo spread over area-to-mass and space-weather draws; "
                                 "not a conformal interval and not a distribution-free coverage "
                                 "guarantee"),
            "interval_quality": interval_quality(
                _finite(row.get("lo90_days")), _finite(row.get("median_days")),
                _finite(row.get("hi90_days"))),
            "impact_location": None,
            "impact_location_note": ("not available: no validated impact coordinate, ground "
                                     "track or recovered-fragment location exists for this "
                                     "object in this repository"),
        }
        reentry["horizon_relation"] = horizon_relation(
            reentry["lo90_days"], reentry["median_days"], reentry["hi90_days"],
            p_horizon=reentry["probability_by_horizon"]["30d"], quantity="re-entry time")
        latest = self.latest_run_id()
        processing_time = self.run_summary(latest).started_at if latest else None
        regime = str(row["regime"])
        if regime == "operator_controlled":
            reentry["model"] = "previous-window payload base rate (C3 status-aware policy)"
            reentry["evidence_status"] = ("operator-controlled payload: drag physics does not "
                                          "determine re-entry, so no drag forecast is given")
        elif str(row["type1"]) in {"D", "R", "C"}:
            reentry["model"] = "physics expert, area-to-mass conditioned on catalogue history"
            reentry["evidence_status"] = ("quantitatively evaluated on the non-blind T1 window "
                                          "(as-of 2026-08-16); not independently validated")
        else:
            reentry["model"] = "physics expert with class area-to-mass priors"
            reentry["evidence_status"] = ("physics expert only; regime "
                                          f"{regime!r}; not validated for this subgroup")

        record_core = {
            "schema_version": stamp("object_record"),
            "norad": norad,
            "name": str(row["Name"]),
            "freshness": freshness(as_of, _text(row.get("t0_canonical")), processing_time,
                                   artifact_sha256=self.catalogue_provenance(as_of)["sha256"]),
            "object_class": str(row["type1"]),
            "object_class_label": {"P": "payload", "R": "rocket body", "C": "component",
                                   "D": "fragment"}.get(str(row["type1"]), str(row["type1"])),
            "operational_status": _text(row.get("ops_status")),
            "regime": regime,
            "as_of": as_of,
            "launch_tag": _text(row.get("Launch_Tag")),
            "breakup_family": _text(row.get("breakup_family")),
            "launch_family": _text(row.get("launch_family")),
            "space_weather": {"f107_last81": _finite(row.get("f107_last81")),
                              "ap_last81": _finite(row.get("ap_last81"))},
            "elements": elements,
            "physical": physical,
            "lifetime": lifetime,
            "reentry": reentry,
            "telemetry": {
                "available": False,
                "reason": ("no telemetry exists for any catalogue object in this repository: "
                           "the ESA-ADB missions are anonymised and share no identifier with "
                           "the catalogue"),
            },
            "conjunction": {
                "available": False,
                "reason": ("conjunction evidence cannot be attributed to this object: the "
                           "Kelvins CAC events are anonymised"),
            },
            "provenance": {
                **self.catalogue_provenance(as_of),
                "model_version": model_version_unavailable(
                    "the dated forecast was produced by a study run whose fitted models are not "
                    "persisted; every value here is read from the archived table named above"),
            },
        }
        record_core["twin_state"] = self.twin_record(norad, as_of, policy=twin_policy, run_id=latest)
        record_core["decision_priority"] = self.priority_for_object(latest, norad)
        record_core["evidence_availability"] = self.evidence_availability(record_core, latest)
        return record_core

    # -------------------------------------------------------------------- telemetry
    def missions(self) -> list[dict[str, Any]]:
        """ESA-ADB missions whose prepared arrays are present."""
        found = []
        base = self.root / TELEMETRY_DIR
        if not base.is_dir():
            return found
        for mission in ("1", "2", "3"):
            array = base / f"mission{mission}.npz"
            labels = base / f"mission{mission}_labels.csv"
            if not array.is_file():
                continue
            meta = self._mission_meta(mission)
            found.append({
                "mission": mission,
                "label": f"ESA-ADB Mission {mission}",
                "channels": len(meta["channels"]),
                "samples": meta["samples"],
                "cadence": meta["cadence"],
                "start": meta["start"],
                "labelled_intervals": meta["labelled_intervals"],
                "has_labels": labels.is_file(),
                "anonymised": True,
            })
        return found

    @lru_cache(maxsize=4)
    def _mission_meta(self, mission: str) -> dict[str, Any]:
        """Channel names, cadence and extent, read without holding the sample matrix."""
        self._check_mission(mission)
        path = self.root / TELEMETRY_DIR / f"mission{mission}.npz"
        if not path.is_file():
            raise DataUnavailable(f"ESA-ADB mission {mission} array is not present")
        with np.load(path, allow_pickle=True) as archive:
            channels = [str(c) for c in archive["channels"]]
            subsystems = [str(s) for s in archive["subsystems"]]
            target = [bool(t) for t in archive["target"]]
            cadence = str(archive["cadence"])
            start = str(np.datetime_as_string(archive["t0"]))
        # The sample count comes from the .npy header of the X member, read through the zip container; the
        # 448 MB matrix itself is never materialised for a listing (P3-A2).
        samples = int(_npz_member_shape(path, "X")[0])
        labels_path = self.root / TELEMETRY_DIR / f"mission{mission}_labels.csv"
        intervals = int(len(pd.read_csv(labels_path))) if labels_path.is_file() else 0
        return {"channels": channels, "subsystems": subsystems, "target": target,
                "cadence": cadence, "start": start, "samples": samples,
                "labelled_intervals": intervals}

    def _check_mission(self, mission: str) -> None:
        if not MISSION_ID.match(str(mission)):
            raise InvalidSelection(f"unknown ESA-ADB mission: {mission!r}")

    def channels(self, mission: str) -> list[dict[str, Any]]:
        meta = self._mission_meta(str(mission))
        labels = self._mission_labels(str(mission))
        counts = labels["Channel"].value_counts().to_dict() if len(labels) else {}
        return [{
            "channel": channel,
            "subsystem": subsystem,
            "is_target": is_target,
            "labelled_intervals": int(counts.get(channel, 0)),
        } for channel, subsystem, is_target in zip(meta["channels"], meta["subsystems"],
                                                   meta["target"])]

    @lru_cache(maxsize=4)
    def _mission_labels(self, mission: str) -> pd.DataFrame:
        path = self.root / TELEMETRY_DIR / f"mission{mission}_labels.csv"
        if not path.is_file():
            return pd.DataFrame(columns=["ID", "Channel", "StartTime", "EndTime", "Class",
                                         "Category"])
        table = pd.read_csv(path)
        table["StartTime"] = pd.to_datetime(table["StartTime"], errors="coerce")
        table["EndTime"] = pd.to_datetime(table["EndTime"], errors="coerce")
        return table

    @lru_cache(maxsize=1)
    def _mission_column(self, mission: str, index: int) -> np.ndarray:
        """One channel column of the sample matrix, cached per (mission, channel).

        The arrays are deflate-compressed inside the npz, so the whole matrix must be decompressed to read any
        column; it is then discarded and only the column (a few MB) is kept, instead of retaining up to 448 MB per
        mission in the console process (rehearsal 2026-11-08: the channel page lifted RSS from 245 to 660 MB).
        """
        key = (str(mission), int(index))
        hit = self._column_cache.get(key)
        if hit is not None:
            return hit
        self._check_mission(mission)
        path = self.root / TELEMETRY_DIR / f"mission{mission}.npz"
        if not path.is_file():
            raise DataUnavailable(f"ESA-ADB mission {mission} array is not present")
        with np.load(path, allow_pickle=True) as archive:
            column = np.array(archive["X"][:, index], copy=True)      # the matrix is released at the end of the block
        if len(self._column_cache) >= 8:
            self._column_cache.pop(next(iter(self._column_cache)))
        self._column_cache[key] = column
        return column

    def _mission_samples(self, mission: str) -> np.ndarray:
        """The sample matrix. Cached for one mission only: Mission 1 alone is 448 MB."""
        self._check_mission(mission)
        path = self.root / TELEMETRY_DIR / f"mission{mission}.npz"
        if not path.is_file():
            raise DataUnavailable(f"ESA-ADB mission {mission} array is not present")
        with np.load(path, allow_pickle=True) as archive:
            return np.asarray(archive["X"])

    def channel_series(self, mission: str, channel: str,
                       max_points: int = 2000) -> dict[str, Any]:
        """Decimated real telemetry for one channel, with its labelled intervals.

        Decimation takes a strided subsample and reports the stride, so a reader knows the
        chart is a subsample of the real series rather than a smoothed or modelled curve.
        """
        mission = str(mission)
        self._check_mission(mission)
        if not CHANNEL_ID.match(channel or ""):
            raise InvalidSelection(f"malformed channel name: {channel!r}")
        meta = self._mission_meta(mission)
        if channel not in meta["channels"]:
            raise DataUnavailable(
                f"{channel} is not a channel of ESA-ADB mission {mission}",
                detail=f"mission {mission} has {len(meta['channels'])} channels",
            )
        index = meta["channels"].index(channel)
        column = self._mission_column(mission, index)

        if max_points < 10:
            raise InvalidSelection("max_points must be at least 10")
        stride = max(1, int(np.ceil(len(column) / max_points)))
        values = column[::stride]
        finite = np.isfinite(values)

        start = pd.Timestamp(meta["start"])
        # Cadence is stored in a pandas-parsable form ("5min", "2min").
        try:
            step = pd.Timedelta(meta["cadence"])
        except ValueError as exc:
            raise DataUnavailable(
                f"unrecognised cadence for mission {mission}: {meta['cadence']!r}",
                detail="sample timestamps cannot be reconstructed, so no series is returned",
            ) from exc
        times = pd.DatetimeIndex(start + np.arange(len(values)) * stride * step)

        labels = self._mission_labels(mission)
        channel_labels = labels[labels["Channel"].eq(channel)] if len(labels) else labels
        intervals = [{
            "id": _text(row.ID),
            "start": row.StartTime.isoformat() if pd.notna(row.StartTime) else None,
            "end": row.EndTime.isoformat() if pd.notna(row.EndTime) else None,
            "label_class": _text(getattr(row, "Class", None)),
            "category": _text(getattr(row, "Category", None)),
        } for row in channel_labels.itertuples(index=False)]

        return {
            "mission": mission,
            "channel": channel,
            "subsystem": meta["subsystems"][index],
            "is_target": meta["target"][index],
            "cadence": meta["cadence"],
            "start": meta["start"],
            "total_samples": int(len(column)),
            "returned_points": int(len(values)),
            "decimation_stride": stride,
            "missing_samples": int((~np.isfinite(column)).sum()),
            "times": [t.isoformat() for t in times],
            "values": [float(v) if np.isfinite(v) else None for v in values],
            "value_min": float(np.nanmin(column)) if finite.any() else None,
            "value_max": float(np.nanmax(column)) if finite.any() else None,
            "labelled_intervals": intervals,
            "anonymised": True,
            "identity_note": ("ESA-ADB missions are anonymised; this channel belongs to no "
                              "identified spacecraft and cannot be linked to a NORAD object"),
            "score_note": ("labelled intervals are ground-truth annotations from the benchmark, "
                           "not model detections; no per-sample anomaly score is stored in this "
                           "artifact"),
        }

    def health_arms(self, calibrator: str | None = None) -> pd.DataFrame:
        """Saved ESA-ADB benchmark rows: detection performance per arm, not per object."""
        path = self.root / TELEMETRY_RESULTS
        if not path.is_file():
            raise DataUnavailable(f"ESA-ADB benchmark results are not present: {TELEMETRY_RESULTS}")
        table = pd.read_csv(path)
        if calibrator:
            table = table[table["calibrator"].eq(calibrator)]
            if table.empty:
                raise DataUnavailable(f"no ESA-ADB rows for calibrator {calibrator!r}")
        return table

    # ----------------------------------------------------------------------- debris
    @lru_cache(maxsize=1)
    def _spotgeo_detections(self) -> dict[int, dict[int, list[tuple[float, float]]]]:
        path = self.root / SPOTGEO_SUBMISSION
        if not path.is_file():
            raise DataUnavailable(f"SpotGEO detections are not present: {SPOTGEO_SUBMISSION}")
        grouped: dict[int, dict[int, list[tuple[float, float]]]] = {}
        for record in json.loads(path.read_text(encoding="utf-8")):
            sequence = int(record["sequence_id"])
            frame = int(record["frame"])
            coords = [(float(x), float(y)) for x, y in (record.get("object_coords") or ())]
            grouped.setdefault(sequence, {})[frame] = coords
        return grouped

    VISION_SUMMARY = "outputs/benchmarks/vision_spotgeo/summary.csv"
    VISION_SERVED_DETECTOR = ("classical COSMOS front end (difference-of-Gaussians on frame differences); hard detections, "
                              "no confidence — the only detector whose per-detection output is archived as a submission")

    def vision_benchmark_arms(self) -> list[dict[str, Any]]:
        """SpotGEO benchmark scores per detector arm (archived summary table); the console serves only the classical
        front end's detections, so these rows are benchmark results, not the detections shown on the debris screens."""
        path = self.root / self.VISION_SUMMARY
        if not path.is_file():
            raise DataUnavailable(f"SpotGEO benchmark summary is not present: {self.VISION_SUMMARY}")
        frame = self._cached_frame(path)
        rows = []
        for r in frame.to_dict(orient="records"):
            def f(key):
                v = r.get(key)
                return None if v is None or (isinstance(v, float) and v != v) else float(v)
            rows.append({"model": str(r.get("model")), "inputs": str(r.get("inputs")), "train_frac": f("train_frac"),
                         "f1_mean": f("test_f1|mean"), "f1_std": f("test_f1|std"), "precision_mean": f("test_precision|mean"),
                         "recall_mean": f("test_recall|mean"),
                         "served_here": str(r.get("model", "")).lower().startswith("classical")})
        rows.sort(key=lambda x: -(x["f1_mean"] or 0.0))
        return rows

    def debris_available(self) -> dict[str, Any]:
        """Whether the SpotGEO detections artifact is present — by file presence only, without parsing it.

        The overview and datasets listings need availability, not the detections; parsing the submission
        there cost about 375 ms and 74 MB per cold listing (P3-B profile, 2026-11-08). The debris pages still
        parse it, and a present-but-unreadable file is reported there, not here.
        """
        path = self.root / SPOTGEO_SUBMISSION
        present = path.is_file()
        return {"available": present, "artifact": SPOTGEO_SUBMISSION,
                "size_bytes": path.stat().st_size if present else None,
                "detail": "test split with saved detections (artifact present; parsed only on the debris screens)" if present
                else f"not present: {SPOTGEO_SUBMISSION}"}

    def debris_sequences(self, limit: int = 40) -> list[dict[str, Any]]:
        detections = self._spotgeo_detections()
        sequences = sorted(detections)[:limit]
        return [{
            "sequence_id": sequence,
            "frames": len(detections[sequence]),
            "detections": sum(len(c) for c in detections[sequence].values()),
            "images_present": (self.root / SPOTGEO_IMAGES / "test" / str(sequence)).is_dir(),
        } for sequence in sequences]

    def debris_sequence(self, sequence_id: int) -> dict[str, Any]:
        try:
            sequence_id = int(sequence_id)
        except (TypeError, ValueError) as exc:
            raise InvalidSelection(f"sequence id must be an integer: {sequence_id!r}") from exc
        detections = self._spotgeo_detections()
        if sequence_id not in detections:
            raise DataUnavailable(f"SpotGEO sequence {sequence_id} has no saved detections")
        frames = []
        for frame in sorted(detections[sequence_id]):
            image = self.root / SPOTGEO_IMAGES / "test" / str(sequence_id) / f"{frame}.png"
            frames.append({
                "frame": frame,
                "image_available": image.is_file(),
                "image_path": str(image.relative_to(self.root)) if image.is_file() else None,
                "detections": [{"x_px": x, "y_px": y, "confidence": None}
                               for x, y in detections[sequence_id][frame]],
            })
        return {
            "sequence_id": sequence_id,
            "frames": frames,
            "total_detections": sum(len(f["detections"]) for f in frames),
            "detector": "classical COSMOS front end + DoG (saved test submission)",
            "image_size_px": [640, 480],
            "confidence_available": False,
            "confidence_note": ("this front end emits hard detections; the saved submission "
                               "contains no per-detection confidence and none is invented"),
            "timestamp_available": False,
            "timestamp_note": ("SpotGEO sequences carry a frame index, not an absolute UTC "
                              "observation time; no timestamp is invented"),
            "astrometric_calibration": False,
            "evidence_status": ("benchmark evaluation on the SpotGEO test split; no independent "
                               "observing-condition validation"),
        }

    def debris_image_path(self, sequence_id: int, frame: int) -> Path:
        """Filesystem path of one real SpotGEO frame, validated against traversal."""
        try:
            sequence_id, frame = int(sequence_id), int(frame)
        except (TypeError, ValueError) as exc:
            raise InvalidSelection("sequence and frame must be integers") from exc
        if not 1 <= frame <= 5:
            raise InvalidSelection("SpotGEO sequences have frames 1-5")
        path = (self.root / SPOTGEO_IMAGES / "test" / str(sequence_id) / f"{frame}.png").resolve()
        base = (self.root / SPOTGEO_IMAGES).resolve()
        if base not in path.parents:
            raise InvalidSelection("resolved image path escapes the dataset directory")
        if not path.is_file():
            raise DataUnavailable(f"SpotGEO test image {sequence_id}/{frame}.png is not present")
        return path

    # -------------------------------------------------------------------- collision
    def collision_events(self, limit: int = 100,
                         model: str = "cosmos_gated") -> dict[str, Any]:
        """Anonymised CAC conjunction events with physical probability only."""
        path = self.root / CONJUNCTION_PREDICTIONS
        if not path.is_file():
            raise DataUnavailable(f"conjunction predictions are not present: {CONJUNCTION_PREDICTIONS}")
        with np.load(path, allow_pickle=True) as archive:
            key = f"{model}__q"
            available = sorted(name[:-3] for name in archive.files if name.endswith("__q"))
            if key not in archive:
                raise DataUnavailable(
                    f"conjunction model {model!r} has no saved predictions",
                    detail=f"available models: {', '.join(available)}",
                )
            quantiles = np.asarray(archive[key], dtype=float)
            truth = np.asarray(archive["y"], dtype=float)

        rows = []
        for index in range(min(limit, len(quantiles))):
            log_q = np.maximum.accumulate(quantiles[index])
            median_log = float(log_q[adapters.LIFETIME_QUANTILES.index(0.50)])
            at_floor = median_log <= adapters.CONJUNCTION_RISK_FLOOR + 1e-9
            rows.append({
                "event_id": f"CAC-EVENT-{index}",
                "collision_probability": min(1.0, 10.0 ** median_log),
                "log10_probability": median_log,
                "interval_lower": min(1.0, 10.0 ** float(log_q[0])),
                "interval_upper": min(1.0, 10.0 ** float(log_q[-1])),
                "interval_level": 0.90,
                "at_reporting_floor": at_floor,
                "high_risk_threshold_exceeded": median_log >= -6.0,
                "true_final_log10_risk": float(truth[index]),
                # Priority is a decision-layer quantity and is never attached here.
                "operational_priority": None,
            })
        return {
            "model": model,
            "available_models": available,
            "events_total": int(len(quantiles)),
            "events_returned": len(rows),
            "events": rows,
            "quantile_levels": list(adapters.LIFETIME_QUANTILES),
            "reporting_floor_log10": adapters.CONJUNCTION_RISK_FLOOR,
            "identity_linkable": False,
            "identity_note": ("Kelvins CAC events are anonymised: an event cannot be attributed "
                              "to a catalogued object, and no object's health can be joined to it"),
            "priority_note": ("physical collision probability only; operational priority is a "
                              "separate decision-layer quantity and is not derived here"),
            "escalation_available": False,
            "escalation_reason": ("coupling C4 (health-driven escalation) cannot be computed: no "
                                  "dataset links telemetry health to a conjunction event or a "
                                  "catalogued object"),
            "evidence_status": ("evaluated on the official held-out CAC split; not independently "
                                "validated and not a validated collision-avoidance capability"),
        }

    # ------------------------------------------------------------------ prospective
    def prospective_status(self) -> dict[str, Any]:
        """Current BLOCKED/READY state of the dated-forecast evaluation; cached until the snapshot directory changes."""
        from scripts.check_t1_later_snapshot import SNAPSHOT_ROOT, assess
        snap = self.root / SNAPSHOT_ROOT
        key = tuple(sorted((p.name, p.stat().st_mtime_ns) for p in snap.iterdir())) if snap.is_dir() else ("absent",)
        if self._prospective_cache and self._prospective_cache[0] == key:
            self.cache_events["prospective_hit"] += 1
            return dict(self._prospective_cache[1])
        self.cache_events["prospective_miss"] += 1
        result = assess(self.root)
        self._prospective_cache = (key, result)
        return dict(result)


# ------------------------------------------------------------------------- helpers
def _twin_capability(modules_rec: dict[str, Any], run_id: str | None) -> dict[str, Any]:
    """Status of the 'versioned twin state' capability for one run, from the run manifest only (P3-B)."""
    tw = modules_rec.get("twin_state") or {}
    eq = modules_rec.get("twin_equivalence") or {}
    st = tw.get("status")
    if st == "success":
        outs = tw.get("outputs") or {}
        detail = (f"read by the runtime pipeline as an additional evidence root: source {outs.get('source')} "
                  f"({outs.get('schema_version')}), digest {outs.get('digest_state')}, {outs.get('record_count')} records"
                  + (" — FALLBACK to the historical archive" if outs.get("fallback_used") else ""))
        if eq.get("status") == "success":
            eo = eq.get("outputs") or {}
            detail += (f"; run-time equivalence with the catalogue chain: {eo.get('records_equal')} of {eo.get('records_compared')} "
                       f"compared records equal, {eo.get('records_not_comparable')} not comparable, {eo.get('records_different')} different")
        elif eq.get("status"):
            detail += f"; equivalence module {eq.get('status')}"
        return {"status": "implemented", "detail": detail}
    if st in ("blocked", "failed"):
        return {"status": "blocked", "detail": f"module twin_state was {st} in run {run_id}: {tw.get('error') or tw.get('reason') or 'no detail'}"}
    return {"status": "archived_only",
            "detail": ("re-emitted from the archived forecast with provenance; not read by this run"
                       + (" (the run predates the twin_state module)" if run_id else " (no run)"))}


def _npz_member_shape(path: Path, member: str) -> tuple:
    """Shape of one array inside an .npz without reading its data (npy header through the zip container)."""
    with zipfile.ZipFile(path) as zf, zf.open(f"{member}.npy") as fh:
        version = np.lib.format.read_magic(fh)
        header = (np.lib.format.read_array_header_1_0(fh) if version == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        return tuple(header[0])


#: The decision horizon of the ranking, in days (adapters.decision_priority uses p_30d).
DECISION_HORIZON_DAYS = 30.0

_NOT_A_PROBABILITY = ("the interval is the 5-95 % quantile range of the predicted time; it is not a probability of "
                      "survival past the horizon and not a guarantee for this object. The separate 30-day probability "
                      "(p_30d) is the quantity the ranking uses; the interval only shows how spread out the predicted "
                      "time is around the horizon")


def horizon_relation(low: float | None, median: float | None, high: float | None,
                     p_horizon: float | None = None, horizon_days: float = DECISION_HORIZON_DAYS,
                     quantity: str = "re-entry time") -> dict[str, Any]:
    """Where a 5-95 % time interval lies relative to the decision horizon. Display only.

    Relations: ``entirely_before`` (high < horizon), ``entirely_after`` (low > horizon), ``crosses``
    (low <= horizon <= high), ``censored_at_cap`` (every quantile at the study cap), ``unavailable``.
    """
    out: dict[str, Any] = {"horizon_days": horizon_days, "quantity": quantity,
                           "interval": {"lo": low, "median": median, "hi": high}, "p_horizon": p_horizon,
                           "not_a_probability": _NOT_A_PROBABILITY, "display_only": True}
    if low is None or high is None or median is None:
        return {**out, "relation": "unavailable", "label": "NO INTERVAL",
                "explanation": "no 5-95 % interval is available for this quantity"}
    if all(abs(v - CAP_DAYS) <= _CAP_TOLERANCE for v in (low, median, high)):
        return {**out, "relation": "censored_at_cap", "label": "AT CAP",
                "explanation": (f"every quantile sits at the {CAP_DAYS:g}-day study cap, so the interval says only "
                                f"'at least {CAP_DAYS:g} days'; relative to the {horizon_days:g}-day horizon it is after, "
                                "in the censored sense")}
    if high < horizon_days:
        rel, label, expl = "entirely_before", "BEFORE HORIZON", (
            f"both the 5 % and the 95 % quantiles ({low:.1f} and {high:.1f} days) lie before the {horizon_days:g}-day "
            f"decision horizon: under this forecast's own spread, the {quantity} falls before the horizon")
    elif low > horizon_days:
        rel, label, expl = "entirely_after", "AFTER HORIZON", (
            f"both quantiles ({low:.1f} and {high:.1f} days) lie after the {horizon_days:g}-day horizon: under this "
            f"forecast's own spread, the {quantity} falls after the horizon")
    else:
        rel, label, expl = "crosses", "CROSSES HORIZON", (
            f"the interval ({low:.1f} to {high:.1f} days) spans the {horizon_days:g}-day decision horizon: the forecast's "
            f"own spread does not place the {quantity} clearly before or after the horizon, so the point probability "
            "should be read together with this spread rather than as a settled outcome")
    return {**out, "relation": rel, "label": label, "explanation": expl}


def freshness(as_of: str, orbit_epoch: str | None, processing_started_at: str | None,
              artifact_sha256: str | None = None, today: date | None = None) -> dict[str, Any]:
    """Evidence freshness with observation, archive and processing times kept apart.

    Nothing is inferred from file modification times. Staleness is judged only where a threshold is
    defensible: a dated snapshot is current only on its own date. The orbit epoch's age is reported,
    not judged. Missing and inconsistent timestamps are stated as such.
    """
    today = today or datetime.now(timezone.utc).date()
    snapshot = date.fromisoformat(as_of)
    issues: list[str] = []
    epoch_status, epoch_age = "missing", None
    if orbit_epoch:
        try:
            epoch = date.fromisoformat(str(orbit_epoch)[:10])
            epoch_status = "recorded"
            epoch_age = (snapshot - epoch).days
            if epoch > snapshot:
                issues.append(f"orbit canonical epoch {epoch} is after the snapshot date {snapshot}")
        except ValueError:
            epoch_status = "unparseable"
            issues.append(f"orbit canonical epoch {orbit_epoch!r} is not an ISO date")
    processing_status = "recorded" if processing_started_at else "missing"
    if processing_started_at:
        try:
            run_day = datetime.fromisoformat(str(processing_started_at).replace("Z", "+00:00")).date()
            if run_day < snapshot:
                issues.append(f"latest run started on {run_day}, before the snapshot date {snapshot}")
        except ValueError:
            processing_status = "unparseable"
            issues.append(f"run start time {processing_started_at!r} is not an ISO timestamp")
    age = (today - snapshot).days
    return {
        "schema_version": stamp("freshness"),
        "evaluated_on_utc": today.isoformat(),
        "live": False,
        "source_observation": {
            "catalogue_snapshot_date": as_of, "status": "recorded",
            "orbit_canonical_epoch": orbit_epoch, "orbit_epoch_status": epoch_status,
            "orbit_epoch_age_days_at_snapshot": epoch_age,
            "note": ("the canonical epoch is the GCAT representative early-operations orbit epoch, not the element "
                     "epoch of the snapshot; the snapshot date is the CelesTrak SATCAT data date"),
        },
        "archive": {
            "forecast_generation_time": None, "status": "missing",
            "artifact_sha256": artifact_sha256,
            "note": "the dated forecast artifact records no generation timestamp; its identity is its SHA-256",
        },
        "processing": {"latest_run_started_at": processing_started_at, "status": processing_status},
        "staleness": {
            "snapshot_age_days": age, "status": "stale" if age > 0 else ("current" if age == 0 else "inconsistent"),
            "rule": "a dated snapshot is current only on its own date; any later evaluation day makes it stale (threshold 0 days)",
            "orbit_epoch": "no defensible threshold exists for the age of a canonical orbit epoch; it is reported, not judged",
        },
        "consistency": {"status": "inconsistent" if issues or age < 0 else "consistent",
                        "issues": issues + ([f"snapshot date {snapshot} is after the evaluation day {today}"] if age < 0 else [])},
        "note": "archived evidence; nothing here is live or real-time",
    }


def model_version_unavailable(reason: str, label: str | None = None) -> dict[str, Any]:
    """The honest model-version record when no fitted model or model digest exists."""
    return {"status": "unavailable", "digest": None, "label": label, "reason": reason,
            "registry_card": None,
            "registry_note": ("no verified association between this output and a model registry card "
                              "is recorded; none is inferred")}


def registry_association(model_label: str | None) -> str | None:
    """Registry card explicitly verified to have produced an output with this label, else None."""
    return VERIFIED_MODEL_CARD_ASSOCIATIONS.get(model_label or "")


def lineage_for_module(record: dict[str, Any] | None) -> dict[str, Any]:
    """Code / configuration / data-artifact / model lineage of one module record of a run manifest.

    Old manifests carry only ``provenance``; new ones also carry ``lineage``. Every field that is not
    recorded is reported as "unavailable" rather than guessed.
    """
    record = record or {}
    if isinstance(record.get("lineage"), dict):
        return record["lineage"]
    prov = record.get("provenance") or {}
    return {
        "code_version": {"git_commit": prov.get("code_revision") or "unavailable"},
        "configuration_version": {"config_sha256": prov.get("config_digest") or "unavailable"},
        "data_artifacts": dict(prov.get("input_hashes") or {}) or (
            {"derived_from_upstream_outputs": list(prov.get("upstream_outputs") or [])}
            if prov.get("upstream_outputs") else {"unavailable": "no input hash recorded"}),
        "model_version": model_version_unavailable(
            "this run recorded no model digest; its values were read from the archived artifact(s) "
            "listed under data_artifacts" if prov else "no provenance was recorded for this module"),
    }


def subgroup_coverage_cue(am_source: str | None, evidence: dict[str, Any] | None,
                          arm: str = "cosmos_gated") -> dict[str, Any]:
    """Reliability cue for a lifetime interval, from the X6 Stage 1 record (descriptive only).

    ``evidence`` is the parsed ``outputs/am_design_stage1/results.json`` or None when absent. The cue
    reports the observed coverage of the interval construction for the object's own area-to-mass
    subgroup at the archived evaluation origins, against the nominal level. It is a subgroup
    frequency, not this object's probability of being covered, and it says so.
    """
    source = am_source or "unknown"
    cue: dict[str, Any] = {
        "am_source": source,
        "am_source_label": AM_SOURCE_LABELS.get(source, f"{source} (unrecognised source code)"),
        "design_derived": None if source == "unknown" else source == "design",
        "nominal": {"80": 0.80, "90": 0.90},
        "observed": {},
        "under_coverage_flag": False,
        "available": False,
        "evidence": ("observed subgroup-level coverage of the same interval construction (reliability-gated "
                     "fusion + Mondrian conformal calibration) on the archived evaluation origins 2011 and "
                     "2016 (X6 Stage 1, 2026-11-08); descriptive evidence, not a causal explanation"),
        "not_individual": ("the figures are the share of objects of this subgroup whose true lifetime fell "
                           "inside their interval in those evaluations; they are not this object's probability "
                           "of being covered"),
        "scope": ("measured on known-outcome objects of the evaluation origins only; the deployed 2026-10-27 "
                  "snapshot has no outcomes, so its own coverage is unmeasured and nothing is extrapolated "
                  "to it or to other datasets"),
        "reason": None,
        "source": None,
    }
    if source == "unknown":
        cue["reason"] = ("the area-to-mass source is not recorded for this object and is not inferred; no "
                         "subgroup evidence applies")
        return cue
    if not evidence:
        cue["reason"] = ("subgroup coverage evidence (outputs/am_design_stage1/results.json) is not present "
                         "in this checkout; no cue can be shown")
        return cue
    for origin, rec in sorted(evidence.get("origins", {}).items()):
        per_level = {}
        for level in ("80", "90"):
            g = (rec.get("coverage") or {}).get(f"{arm}@{level}", {}).get(source)
            if g:
                per_level[level] = {"coverage": float(g["coverage"]),
                                    "ci95": [float(g["ci95"][0]), float(g["ci95"][1])],
                                    "n": int(g["n"]), "nominal": cue["nominal"][level],
                                    "below_nominal": bool(g["ci95"][1] < cue["nominal"][level])}
        if per_level:
            cue["observed"][origin] = per_level
    cue["available"] = bool(cue["observed"])
    if not cue["available"]:
        cue["reason"] = f"no subgroup evaluation exists for area-to-mass source {source!r}"
        return cue
    cue["source"] = {"artifact": AM_DESIGN_STAGE1, "protocol": evidence.get("protocol"),
                     "generated_at": evidence.get("generated_at")}
    cue["under_coverage_flag"] = bool(cue["design_derived"] and any(
        lv["80"]["below_nominal"] for lv in cue["observed"].values() if "80" in lv))
    return cue


def _finite(value: Any) -> float | None:
    """Float value, or None when absent or non-finite. Never a substituted default."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text or None


def interval_quality(low: float | None, median: float | None,
                     high: float | None) -> dict[str, Any]:
    """Describe what a time interval actually means, so a reader cannot over-read it.

    Three cases must be distinguished, because all three look like a narrow interval:

    ``at_cap``       every Monte-Carlo draw exceeded the study horizon, so the quantiles pile
                     up at the cap. The correct reading is "at least CAP_DAYS", **not** a
                     precise lifetime.
    ``degenerate``   the draws agreed on one value below the cap. The spread is genuinely
                     zero, which reflects integrator discretisation rather than confidence.
    ``spread``       an ordinary interval with non-zero width.
    """
    values = [v for v in (low, median, high) if v is not None]
    if len(values) < 2:
        return {"kind": "unavailable", "censored_at_cap": False, "zero_width": False,
                "label": "no time quantiles available",
                "detail": "the saved forecast holds no time quantiles for this object"}

    at_cap = all(abs(v - CAP_DAYS) <= _CAP_TOLERANCE for v in values)
    zero_width = (low is not None and high is not None and high - low <= 0)
    if at_cap:
        return {
            "kind": "at_cap", "censored_at_cap": True, "zero_width": True,
            "cap_days": CAP_DAYS,
            "label": f"at the {CAP_DAYS:g}-day study cap",
            "detail": ("every Monte-Carlo draw exceeded the study horizon, so the quantiles sit "
                       f"at the cap. Read this as 're-entry not expected within {CAP_DAYS:g} "
                       "days', not as an estimated lifetime of that length."),
        }
    if zero_width:
        return {
            "kind": "degenerate", "censored_at_cap": False, "zero_width": True,
            "label": "zero-width interval",
            "detail": ("all Monte-Carlo draws returned the same value, so the reported spread "
                       "is zero. This reflects the integrator's discretisation, not high "
                       "confidence, and must not be read as a precise prediction."),
        }
    return {
        "kind": "spread", "censored_at_cap": False, "zero_width": False,
        "label": "5-95 % Monte-Carlo spread",
        "detail": ("spread over area-to-mass and space-weather draws; not a conformal interval "
                   "and not a distribution-free coverage guarantee"),
    }


def _coherence(probabilities: dict[str, float | None]) -> dict[str, Any]:
    """Cross-horizon coherence of a per-horizon probability triple (limitation L17)."""
    order = ["30d", "90d", "1yr"]
    values = [probabilities.get(key) for key in order]
    if any(value is None for value in values):
        return {"status": "unavailable",
                "detail": "the learned lifetime expert produced no value for this object"}
    violations = [f"P(<= {order[i]}) = {values[i]:.4f} > P(<= {order[i + 1]}) = {values[i + 1]:.4f}"
                  for i in range(len(values) - 1) if values[i] > values[i + 1]]
    if violations:
        return {
            "status": "incoherent",
            "detail": "; ".join(violations),
            "explanation": ("the saved per-horizon probabilities are calibrated by an "
                            "independent isotonic regressor per horizon, which does not "
                            "constrain probabilities across horizons (limitation L17); the "
                            "twin's final reported forecast is unaffected"),
        }
    return {"status": "coherent",
            "detail": "probabilities are nondecreasing across 30 d, 90 d and 1 yr"}
