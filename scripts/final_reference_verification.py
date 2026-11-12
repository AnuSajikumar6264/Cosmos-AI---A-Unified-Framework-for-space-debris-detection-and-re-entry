"""Phase O: verify every reference that could enter the manuscript against a live index.

Each candidate is resolved against Crossref (DOI lookup or bibliographic query), OpenAlex and
arXiv. A candidate is VERIFIED only when a retrieved record matches the claimed authors, year
and venue; otherwise it is CORRECTED, AMBIGUOUS or NOT_FOUND. Nothing is confirmed from memory.

    python scripts/final_reference_verification.py --out outputs/final_literature

Network access is required. A candidate that cannot be resolved must be dropped from the
manuscript, not softened.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cosmos.ai.provenance import ROOT, git_revision  # noqa: E402

UA = "COSMOS-AI-reference-audit/1.0 (academic reference verification)"
PAUSE = 0.7

#: Every reference that is cited in, or feeds, the manuscript's positioning.
#: ``claim`` is what the repository currently asserts; verification compares against it.
CANDIDATES = [
    # --- rows carrying a [D] marker in LITERATURE_COMPARISON_MATRIX.md
    {"key": "R3", "doi": "10.3390/aerospace10030297", "prior": "D",
     "claim": {"first_author": "Salmaso", "year": 2023, "venue": "Aerospace"},
     "used_for": "C-1: >400-object re-entry epoch study; informal distribution-match note"},
    {"key": "clark_mccracken", "query": "Tests of equal forecast accuracy and encompassing for "
                                        "nested models", "prior": "D",
     "claim": {"first_author": "Clark", "year": 2001,
               "title_contains": "equal forecast accuracy"},
     "used_for": "C-2: forecast-comparison methodology for nested models"},
    {"key": "bailey2014", "query": "Rolling window selection for out-of-sample forecasting "
                                   "with time-varying parameters", "prior": "D",
     "claim": {"first_author": "Bailey", "year": 2014,
               "title_contains": "window selection"},
     "used_for": "C-2: rolling-origin selection instability outside the orbital domain"},
    {"key": "inoue_rossi_jin", "query": "Rolling window selection for out-of-sample "
                                        "forecasting with time-varying parameters",
     "prior": "NEW", "claim": {"first_author": "Inoue",
                               "title_contains": "window selection"},
     "used_for": "candidate replacement for the unconfirmed 'Bailey 2014'"},
    {"key": "gulrajani_lopezpaz", "query": "In Search of Lost Domain Generalization",
     "prior": "D", "claim": {"first_author": "Gulrajani", "year": 2020},
     "used_for": "C-2: model selection is the hidden determinant of benchmark ranking"},
    {"key": "wild_time", "query": "Wild-Time: A Benchmark of in-the-Wild Distribution Shift "
                                  "over Time", "prior": "D",
     "claim": {"first_author": "Yao", "year": 2022},
     "used_for": "C-2: temporal distribution-shift benchmark precedent"},
    {"key": "chung2026", "query": "LiveHouse-TS live benchmark time series forecasting",
     "prior": "D", "claim": {"first_author": "Chung", "year": 2026,
                             "title_contains": "LiveHouse"},
     "used_for": "C-2: live time-series benchmark, selection validity"},
    {"key": "hendrickx2024", "query": "Machine learning with a reject option: a survey",
     "prior": "D", "claim": {"first_author": "Hendrickx", "year": 2024},
     "used_for": "closes evidence-graded abstention"},
    {"key": "csur2025_selective", "query": "selective prediction survey ACM Computing Surveys "
                                           "learning to defer", "prior": "D",
     "claim": {"year": 2025, "venue": "ACM Computing Surveys",
               "title_contains": "surve"},
     "used_for": "closes evidence-graded abstention"},
    {"key": "learning_to_defer_survey", "query": "Learning to defer to an expert survey "
                                                 "human-AI decision making", "prior": "NEW",
     "claim": {"title_contains": "defer"},
     "used_for": "candidate replacement for the unconfirmed 'ACM CSUR 2025 survey'"},
    {"key": "selectivenet", "query": "SelectiveNet: A Deep Neural Network with an Integrated "
                                     "Reject Option", "prior": "D",
     "claim": {"first_author": "Geifman", "year": 2019},
     "used_for": "closes evidence-graded abstention"},
    {"key": "conformal_selective_risk", "query": "Conformal risk control", "prior": "D",
     "claim": {"first_author": "Angelopoulos"},
     "used_for": "closes evidence-graded abstention (selective risk control)"},
    # --- explicitly listed as requiring re-verification
    {"key": "spotgeo_dataset", "doi": "10.5281/zenodo.3874325", "prior": "V",
     "claim": {"year": 2020, "venue": "Zenodo"},
     "used_for": "SpotGEO dataset deposit (feature2_debris/spotgeo)"},
    {"key": "spotgeo_challenge", "query": "SpotGEO challenge detecting geostationary objects "
                                          "in optical images Chin", "prior": "NOT_RETRIEVABLE",
     "claim": {"title_contains": "spotgeo"},
     "used_for": "SpotGEO challenge description"},
    {"key": "R31_debriswatch2", "query": "DebrisWatch II faint geosynchronous space debris",
     "prior": "D", "claim": {"title_contains": "debriswatch ii"},
     "used_for": "debris detection prior art"},
    {"key": "debriswatch1", "query": "DebrisWatch I A survey of faint geosynchronous debris",
     "prior": "NEW", "claim": {"first_author": "Blake",
                               "title_contains": "debriswatch i"},
     "used_for": "candidate replacement for the unconfirmed 'DebrisWatch II'"},
    {"key": "gibbs_candes", "query": "Adaptive conformal inference under distribution shift",
     "prior": "D", "claim": {"first_author": "Gibbs", "year": 2021},
     "used_for": "venue attribution needs confirming (commonly cited as NeurIPS)"},
    {"key": "tibshirani_covshift", "query": "Conformal prediction under covariate shift",
     "prior": "D", "claim": {"first_author": "Tibshirani", "year": 2019},
     "used_for": "venue attribution needs confirming (commonly cited as NeurIPS)"},
    {"key": "zaffran_etal", "query": "Adaptive conformal predictions for time series",
     "prior": "D", "claim": {"first_author": "Zaffran", "year": 2022},
     "used_for": "venue attribution needs confirming (commonly cited as ICML)"},
    # --- [P] rows: confirm, do not assume
    {"key": "R15_opssat", "doi": "10.1038/s41597-025-05035-3", "prior": "P",
     "claim": {"first_author": "Ruszczak", "year": 2025, "venue": "Scientific Data"},
     "used_for": "OPS-SAT benchmark; the publication precedent for C-1"},
    {"key": "R22_barber", "doi": "10.1214/23-aos2276", "prior": "P",
     "claim": {"first_author": "Barber", "year": 2023, "venue": "Annals of Statistics"},
     "used_for": "coverage beyond exchangeability; closes temporal calibration-failure"},
    # --- load-bearing [V] rows: re-confirm independently
    {"key": "R1_zhou", "doi": "10.1029/2025JA034593", "prior": "V",
     "claim": {"first_author": "Zhou", "year": 2026, "venue": "Journal of Geophysical Research"},
     "used_for": "C-1: closest recent ML decay paper"},
    {"key": "R2_he", "doi": "10.1155/2024/8887634", "prior": "V",
     "claim": {"first_author": "He", "year": 2024},
     "used_for": "C-1/C-2/C-3: continual learning for decay; undisclosed protocol"},
    {"key": "R21_zou", "doi": "10.1016/j.mlwa.2026.101038", "prior": "V",
     "claim": {"first_author": "Zou", "year": 2026},
     "used_for": "takes cluster-CI + rolling-origin; withdraws temporal calibration claim"},
    {"key": "R20_lu", "doi": "10.1371/journal.pone.0360910", "prior": "V",
     "claim": {"first_author": "Lu", "year": 2026, "venue": "PLoS ONE"},
     "used_for": "closes conformal-on-telemetry multi-horizon"},
    {"key": "R25_henzi", "doi": "10.1111/rssb.12450", "prior": "V",
     "claim": {"first_author": "Henzi", "year": 2021, "venue": "Journal of the Royal Statistical"},
     "used_for": "isotonic distributional regression; dissolves the L17 'discovery'"},
    {"key": "R27_massimi", "doi": "10.1049/rsn2.12547", "prior": "V",
     "claim": {"first_author": "Massimi", "year": 2023},
     "used_for": "debris detection prior art"},
    {"key": "R23_wang_hyndman", "arxiv": "2410.13115", "prior": "V",
     "claim": {"first_author": "Wang", "note": "coverage error increases with horizon"},
     "used_for": "withdraws temporal calibration-failure contribution"},
    {"key": "mldsgp4", "arxiv": "2402.04830", "prior": "V",
     "claim": {"note": "ML-dSGP4"},
     "used_for": "ML_DSGP4_FEASIBILITY.md: comparison not attempted"},
    # --- foundational older works retained in the manuscript
    {"key": "castet_saleh", "query": "Satellite reliability statistical data analysis and "
                                     "modeling Journal of Spacecraft and Rockets", "prior": "D",
     "claim": {"first_author": "Castet", "year": 2009,
               "title_contains": "satellite reliability"},
     "used_for": "censored satellite survival at catalogue scale; foundational estimand"},
    {"key": "castet_saleh_subsystem", "query": "Satellite and satellite subsystems reliability "
                                               "statistical data analysis and modeling",
     "prior": "NEW", "claim": {"first_author": "Castet",
                               "title_contains": "subsystem"},
     "used_for": "alternative Castet & Saleh record if the 2009 JSR paper does not resolve"},
    {"key": "graf1999", "query": "Assessment and comparison of prognostic classification "
                                 "schemes for survival data", "prior": "D",
     "claim": {"first_author": "Graf", "year": 1999},
     "used_for": "censoring-aware scoring (Brier for survival)"},
    {"key": "antolini2005", "query": "A time-dependent discrimination index for survival data",
     "prior": "D", "claim": {"first_author": "Antolini", "year": 2005},
     "used_for": "time-dependent concordance under censoring"},
    {"key": "uno2011", "query": "On the C-statistics for evaluating overall adequacy of risk "
                                "prediction procedures with censored survival data",
     "prior": "D", "claim": {"first_author": "Uno", "year": 2011},
     "used_for": "censoring-robust discrimination"},
    {"key": "sonabend2022", "query": "Avoiding C-hacking when evaluating survival "
                                     "distribution predictions", "prior": "D",
     "claim": {"first_author": "Sonabend", "year": 2022},
     "used_for": "metric-choice pitfalls in survival evaluation"},
    {"key": "hundman2018", "query": "Detecting Spacecraft Anomalies Using LSTMs and "
                                    "Nonparametric Dynamic Thresholding", "prior": "D",
     "claim": {"first_author": "Hundman", "year": 2018},
     "used_for": "SMAP/MSL telemetry benchmark origin"},
    {"key": "caldas_soares", "query": "Machine learning in orbit estimation: a survey",
     "prior": "V", "claim": {"first_author": "Caldas", "year": 2024},
     "used_for": "C-2: frames the open problem as accuracy, not selection"},
    {"key": "herrmann2024", "query": "Unmasking overestimation: a re-evaluation of deep "
                                     "anomaly detection in spacecraft telemetry", "prior": "V",
     "claim": {"first_author": "Herrmann", "year": 2024},
     "used_for": "C-2/C-3: metric validity; calls for pre-split datasets"},
    {"key": "siew2025", "query": "Siew space object behavioral analysis machine learning "
                                 "satellite pattern of life", "prior": "D",
     "claim": {"first_author": "Siew", "year": 2025},
     "used_for": "PHASE_I_NOVELTY_REVIEW positioning"},
    {"key": "taggart_huber", "query": "Point forecasting and forecast evaluation with "
                                      "generalized Huber loss", "prior": "V",
     "claim": {"first_author": "Taggart", "year": 2022,
               "title_contains": "huber"},
     "used_for": "local elicitability; justifies excluding rmse_log10"},
    {"key": "gneiting2011", "query": "Making and Evaluating Point Forecasts", "prior": "NEW",
     "claim": {"first_author": "Gneiting", "year": 2011,
               "title_contains": "point forecasts"},
     "used_for": "the canonical elicitability result: quantiles yes, mean under censoring no"},
]


def _get(url: str, timeout: int = 25):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def crossref_doi(doi: str) -> dict | None:
    try:
        message = _get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"]
    except Exception:
        return None
    parts = (message.get("published") or message.get("issued") or {}).get("date-parts") or [[None]]
    return {"source": "crossref/doi",
            "title": (message.get("title") or [None])[0],
            "authors": [f"{a.get('family', '')}".strip()
                        for a in message.get("author", [])][:12],
            "year": parts[0][0],
            "venue": (message.get("container-title") or [None])[0],
            "type": message.get("type"), "doi": message.get("DOI"),
            "citations": message.get("is-referenced-by-count")}


def crossref_query(query: str) -> list[dict]:
    try:
        items = _get("https://api.crossref.org/works?rows=5&select=DOI,title,author,issued,"
                     "container-title,type,is-referenced-by-count&query.bibliographic="
                     + urllib.parse.quote(query))["message"]["items"]
    except Exception:
        return []
    out = []
    for message in items:
        parts = (message.get("issued") or {}).get("date-parts") or [[None]]
        out.append({"source": "crossref/query",
                    "title": (message.get("title") or [None])[0],
                    "authors": [a.get("family", "") for a in message.get("author", [])][:12],
                    "year": parts[0][0],
                    "venue": (message.get("container-title") or [None])[0],
                    "type": message.get("type"), "doi": message.get("DOI"),
                    "citations": message.get("is-referenced-by-count")})
    return out


def openalex(doi: str | None = None, query: str | None = None) -> list[dict]:
    try:
        if doi:
            url = f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}"
            results = [_get(url)]
        else:
            url = ("https://api.openalex.org/works?per-page=5&search="
                   + urllib.parse.quote(query or ""))
            results = _get(url).get("results", [])
    except Exception:
        return []
    out = []
    for work in results:
        location = (work.get("primary_location") or {}).get("source") or {}
        out.append({"source": "openalex",
                    "title": work.get("display_name"),
                    "authors": [(a.get("author") or {}).get("display_name", "")
                                for a in work.get("authorships", [])][:12],
                    "year": work.get("publication_year"),
                    "venue": location.get("display_name"),
                    "type": work.get("type"), "doi": (work.get("doi") or "").replace(
                        "https://doi.org/", "") or None,
                    "citations": work.get("cited_by_count")})
    return out


def arxiv(identifier: str | None = None, query: str | None = None) -> list[dict]:
    base = "http://export.arxiv.org/api/query?max_results=5&"
    url = base + (f"id_list={identifier}" if identifier
                  else "search_query=" + urllib.parse.quote(f'all:"{query}"'))
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=25) as response:
            xml = response.read().decode("utf-8", "replace")
    except Exception:
        return []
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        published = re.search(r"<published>(\d{4})", entry)
        out.append({"source": "arxiv",
                    "title": re.sub(r"\s+", " ", title.group(1)).strip() if title else None,
                    "authors": [re.sub(r"\s+", " ", n).strip().split()[-1] for n in
                                re.findall(r"<name>(.*?)</name>", entry, re.S)][:12],
                    "year": int(published.group(1)) if published else None,
                    "venue": "arXiv", "type": "preprint",
                    "doi": None, "citations": None})
    return out


def _matches(record: dict, claim: dict) -> tuple[bool, list[str]]:
    """Return (matched, problems).

    A match requires at least one field to have been *checkable and checked*. A claim with
    nothing comparable, or a record whose fields are all null, cannot be called verified --
    silence is not agreement.
    """
    problems, checked = [], 0
    author = claim.get("first_author")
    if author:
        names = " ".join(record.get("authors") or []).lower()
        if not names:
            problems.append("record carries no author list")
        else:
            checked += 1
            if author.lower() not in names:
                problems.append(f"claimed first author '{author}' not among "
                                f"{record.get('authors')}")
    year = claim.get("year")
    if year:
        if record.get("year") is None:
            problems.append("record carries no year")
        else:
            checked += 1
            if abs(int(record["year"]) - int(year)) > 1:
                problems.append(f"claimed year {year}, record says {record['year']}")
    venue = claim.get("venue")
    if venue:
        if not record.get("venue"):
            problems.append("record carries no venue")
        else:
            checked += 1
            if venue.lower()[:18] not in record["venue"].lower():
                problems.append(f"claimed venue '{venue}', record says '{record['venue']}'")
    title = claim.get("title_contains")
    if title:
        if not record.get("title"):
            problems.append("record carries no title")
        else:
            checked += 1
            if title.lower() not in record["title"].lower():
                problems.append(f"expected '{title}' in the title, got '{record['title']}'")
    if checked == 0:
        problems.append("nothing in the claim was checkable against this record")
    return (not problems), problems


def verify(candidate: dict) -> dict:
    claim = candidate.get("claim", {})
    records: list[dict] = []
    if candidate.get("doi"):
        found = crossref_doi(candidate["doi"])
        if found:
            records.append(found)
        time.sleep(PAUSE)
        records += openalex(doi=candidate["doi"])
    elif candidate.get("arxiv"):
        records += arxiv(identifier=candidate["arxiv"])
    else:
        records += crossref_query(candidate["query"])
        time.sleep(PAUSE)
        records += openalex(query=candidate["query"])
        time.sleep(PAUSE)
        records += arxiv(query=candidate["query"])
    time.sleep(PAUSE)

    if not records:
        return {**{k: candidate.get(k) for k in ("key", "doi", "arxiv", "query", "prior",
                                                 "used_for")},
                "status": "NOT_FOUND", "claim": claim, "records": [],
                "problems": ["no record returned by Crossref, OpenAlex or arXiv"]}

    scored = []
    for record in records:
        ok, problems = _matches(record, claim)
        scored.append((ok, len(problems), record, problems))
    scored.sort(key=lambda s: (not s[0], s[1]))
    best_ok, _, best, problems = scored[0]

    if best_ok:
        status = "VERIFIED"
    elif candidate.get("doi") or candidate.get("arxiv"):
        # A direct identifier lookup that disagrees with the claim is a correction, not a miss.
        status = "CORRECTED"
    else:
        status = "AMBIGUOUS"
    return {**{k: candidate.get(k) for k in ("key", "doi", "arxiv", "query", "prior",
                                             "used_for")},
            "status": status, "claim": claim, "problems": problems,
            "best_record": best,
            "records": [s[2] for s in scored[:3]]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--out", default="outputs/final_literature")
    parser.add_argument("--only", default=None, help="comma-separated candidate keys")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = {k.strip() for k in args.only.split(",")} if args.only else None
    todo = [c for c in CANDIDATES if not wanted or c["key"] in wanted]

    print(f"Phase O -- live reference verification ({len(todo)} candidates)\n")
    results = []
    for index, candidate in enumerate(todo, 1):
        result = verify(candidate)
        results.append(result)
        best = result.get("best_record") or {}
        print(f"[{index:2d}/{len(todo)}] {result['status']:10s} {candidate['key']}")
        if best:
            authors = ", ".join((best.get("authors") or [])[:3])
            print(f"           {best.get('year')} · {authors} · {best.get('venue')}")
            print(f"           {str(best.get('title'))[:96]}")
            print(f"           doi={best.get('doi')} citations={best.get('citations')} "
                  f"source={best.get('source')}")
        for problem in result.get("problems", []):
            print(f"           ! {problem}")

    counts = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    print(f"\n=== {counts} ===")

    payload = {"phase": "O", "verified_at": datetime.now(timezone.utc).isoformat(),
               "git": git_revision(root), "counts": counts, "results": results,
               "method": {
                   "indexes": ["Crossref", "OpenAlex", "arXiv"],
                   "rule": "VERIFIED only when a retrieved record matches the claimed first "
                           "author, year (+/-1) and venue prefix; CORRECTED when a direct "
                           "identifier resolves but disagrees with the claim; AMBIGUOUS when a "
                           "bibliographic query returns no matching record; NOT_FOUND when no "
                           "index returns anything.",
                   "policy": "a candidate that is not VERIFIED or CORRECTED must be dropped "
                             "from the manuscript, not softened"}}
    with open(out_dir / "reference_verification.json", "w") as stream:
        json.dump(payload, stream, indent=2, default=str)
    print(f"\nwritten: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
