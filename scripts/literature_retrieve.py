"""Reproducible literature retrieval for Phase 1 of the completion directive.

    python scripts/literature_retrieve.py                      # all topics
    python scripts/literature_retrieve.py --topics fusion,conjunction

Queries the OpenAlex works API live for each topic query, stores the **raw JSON response** per query
under ``outputs/literature/phase1/raw/`` so every record is auditable, and writes one de-duplicated
table ``outputs/literature/phase1/records.csv`` with title, authors, venue, year, DOI, type,
citation count and the abstract reconstructed from OpenAlex's inverted index.

Nothing in the output comes from memory: a record exists only if the API returned it on this run.
Relevance is NOT judged here; that is done by reading the records and is written up separately.
The queries are restricted to 2023 onwards because the prior review (`LITERATURE_REVIEW_2023_2026.md`)
already covers the foundational works and the five topics it addressed; this pass targets the
directive topics that review left uncovered or thin.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/literature/phase1"
MAILTO = "cosmos-ai-literature-audit@example.org"
API = "https://api.openalex.org/works"
SELECT = ("id,doi,title,display_name,publication_year,publication_date,type,"
          "cited_by_count,primary_location,authorships,abstract_inverted_index,"
          "open_access,referenced_works_count")

# Directive topics with no or thin coverage in the existing review, plus confirmatory probes on
# the covered ones so the two passes can be reconciled. Each query is deliberately specific.
TOPICS: dict[str, list[str]] = {
    "digital_twin_predictive": [
        "satellite digital twin health monitoring prediction",
        "spacecraft digital twin anomaly detection telemetry",
        "digital twin space situational awareness orbit",
    ],
    "multimodal_fusion": [
        "multimodal data fusion satellite telemetry imagery",
        "space situational awareness sensor fusion machine learning",
        "evidence fusion spacecraft health orbital data",
    ],
    "conjunction_assessment": [
        "spacecraft conjunction assessment machine learning collision probability",
        "collision avoidance conjunction data message prediction",
        "Kelvins collision avoidance challenge CDM",
    ],
    "provenance_decision_support": [
        "data provenance machine learning pipeline reproducibility",
        "uncertainty-aware decision support abstention selective prediction",
        "evidence provenance digital twin trustworthiness",
    ],
    "temporal_shift": [
        "distribution shift time series anomaly detection evaluation",
        "temporal distribution shift conformal prediction coverage",
        "concept drift spacecraft telemetry",
    ],
    "health_monitoring_subsystem": [
        "satellite power subsystem health monitoring machine learning",
        "spacecraft thermal attitude control anomaly detection telemetry",
    ],
    "reentry_variants": [
        "uncontrolled reentry prediction uncertainty atmospheric density",
        "orbital decay prediction ballistic coefficient solar activity",
    ],
    "evaluation_framework": [
        "benchmark evaluation framework satellite monitoring anomaly detection metrics",
        "event-wise metrics anomaly detection time series evaluation",
    ],
}


def reconstruct_abstract(inv: dict | None, limit: int = 700) -> str:
    if not inv:
        return ""
    pos: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    text = " ".join(w for _, w in sorted(pos))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def fetch(query: str, per_page: int = 20, retries: int = 3) -> dict:
    params = {
        "search": query,
        "filter": "from_publication_date:2023-01-01,type:article|preprint|book-chapter",
        "per-page": str(per_page),
        "sort": "relevance_score:desc",
        "select": SELECT,
        "mailto": MAILTO,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=40) as resp:
                return {"url": url, "status": resp.status,
                        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "body": json.loads(resp.read().decode("utf-8"))}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    return {"url": url, "status": None, "error": repr(last),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "body": None}


def venue(w: dict) -> str:
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    return src.get("display_name") or ""


def authors(w: dict, n: int = 6) -> str:
    names = []
    for a in (w.get("authorships") or [])[:n]:
        au = a.get("author") or {}
        if au.get("display_name"):
            names.append(au["display_name"])
    more = len(w.get("authorships") or []) - n
    return "; ".join(names) + (f"; +{more}" if more > 0 else "")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:70]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topics", default=None, help="comma-separated subset of topic keys")
    ap.add_argument("--per-page", type=int, default=20)
    args = ap.parse_args(argv)

    raw_dir = OUT / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    want = set(args.topics.split(",")) if args.topics else set(TOPICS)

    records: dict[str, dict] = {}
    log = []
    for topic, queries in TOPICS.items():
        if topic not in want:
            continue
        for q in queries:
            res = fetch(q, args.per_page)
            path = raw_dir / f"{topic}__{slug(q)}.json"
            path.write_text(json.dumps(res, indent=1))
            body = res.get("body") or {}
            works = body.get("results", []) if body else []
            log.append({"topic": topic, "query": q, "status": res.get("status"),
                        "n_results": len(works), "raw_file": str(path.relative_to(ROOT)),
                        "error": res.get("error")})
            for w in works:
                wid = w.get("id")
                if not wid:
                    continue
                if wid in records:
                    records[wid]["topics"] = sorted(set(records[wid]["topics"].split("|")) | {topic})
                    records[wid]["topics"] = "|".join(records[wid]["topics"])
                    continue
                records[wid] = {
                    "openalex_id": wid,
                    "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "title": w.get("display_name") or w.get("title") or "",
                    "authors": authors(w),
                    "venue": venue(w),
                    "year": w.get("publication_year"),
                    "date": w.get("publication_date"),
                    "type": w.get("type"),
                    "cited_by_count": w.get("cited_by_count"),
                    "open_access": (w.get("open_access") or {}).get("is_oa"),
                    "topics": topic,
                    "first_query": q,
                    "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
                }
            time.sleep(0.25)   # polite pool

    rows = sorted(records.values(), key=lambda r: (r["topics"], -(r["cited_by_count"] or 0)))
    out_csv = OUT / "records.csv"
    with out_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["openalex_id"])
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "query_log.json").write_text(json.dumps(
        {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "api": API, "filter": "from_publication_date:2023-01-01,type:article|preprint|book-chapter",
         "queries": log}, indent=1))

    print(f"topics: {len(want)}   queries: {len(log)}   unique records: {len(rows)}")
    for topic in TOPICS:
        if topic in want:
            n = sum(1 for r in rows if topic in r["topics"].split("|"))
            errs = sum(1 for l in log if l["topic"] == topic and l["error"])
            print(f"  {topic:30s} records={n:3d}  query_errors={errs}")
    print(f"written: {out_csv.relative_to(ROOT)}, {(OUT / 'query_log.json').relative_to(ROOT)}, "
          f"{len(log)} raw files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
