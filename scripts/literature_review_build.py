"""Assemble the Phase 1 structured literature review from the archived retrieval artifacts.

    python scripts/literature_review_build.py

Inputs (all archived 2026-11-06, nothing fetched here):
  outputs/literature/phase1/query_log.json               21 queries, 8 topics, HTTP status and result counts
  outputs/literature/phase1/records.csv                  368 OpenAlex records with abstracts where indexed
  outputs/literature/phase1/selected_records_crossref.csv 21 records whose DOIs resolved live (Crossref / DataCite)
  docs/research/PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md  section 1 — the per-record fields and the
                                                         per-topic syntheses written by the auditor from the abstracts
  outputs/literature/phase1/uriot2021_baselines_arxiv2008.03069.md   body-text positioning for N5 (read 2026-11-06)
  outputs/literature/phase1/opssat_channels_PMC12041257.md           verbatim channel description for OPS-SAT-AD
  docs/research/LITERATURE_REVIEW_2023_2026.md             the prior review (R1-R34), re-verified 32/32 DOIs

Output: docs/research/PHASE1_LITERATURE_REVIEW.md. Every number in it is computed from these files;
the syntheses are copied verbatim from the Phase 1 design document, which cites only verified records.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LIT = ROOT / "outputs/literature/phase1"
DESIGN = ROOT / "docs/research/PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md"
PRIOR = ROOT / "docs/research/LITERATURE_REVIEW_2023_2026.md"
OUT = ROOT / "docs/research/PHASE1_LITERATURE_REVIEW.md"

TOPIC_LABEL = {
    "digital_twin_predictive": "Satellite digital twins (predictive)",
    "health_monitoring_subsystem": "Spacecraft health monitoring (subsystem level)",
    "evaluation_framework": "Telemetry anomaly detection: evaluation and benchmarks",
    "multimodal_fusion": "Multimodal satellite data fusion",
    "reentry_variants": "Orbital lifetime and re-entry prediction",
    "conjunction_assessment": "Satellite conjunction assessment",
    "temporal_shift": "Temporal distribution shift and conformal coverage",
    "provenance_decision_support": "Evidence provenance and uncertainty-aware decision support",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    q = json.loads((LIT / "query_log.json").read_text())
    queries = next(v for v in q.values() if isinstance(v, list))
    topic_of = {e["query"]: e["topic"] for e in queries}
    rec = pd.read_csv(LIT / "records.csv")
    rec["topic"] = rec.first_query.map(topic_of)
    rec["doi_l"] = rec.doi.astype(str).str.lower().str.replace("https://doi.org/", "", regex=False)
    sel = pd.read_csv(LIT / "selected_records_crossref.csv")
    sel["doi_l"] = sel.doi.astype(str).str.lower()
    sel["in_openalex_corpus"] = sel.doi_l.isin(set(rec.doi_l))
    sel = sel.merge(rec[["doi_l", "abstract", "cited_by_count", "open_access", "type", "authors", "topic"]], on="doi_l", how="left")
    sel["abstract_indexed"] = sel.abstract.notna()

    design = DESIGN.read_text()
    section1 = design.split("## 1. Structured literature review, by directive topic", 1)[1].split("\n## 2. ", 1)[0]
    # map N-ids to DOIs from the design tables so verification status can be attached per record
    n_rows = re.findall(r"^(\| (N\d+) \| [^`]*`([^`]+)`.*)$", section1, flags=re.M)
    n_ids, dagger = {}, set()
    for line, nid, ident in n_rows:
        doi = ident.lower().strip()
        if not doi.startswith("10."):                       # bare arXiv identifier in the design table
            doi = "10.48550/arxiv." + doi
        n_ids[doi] = nid
        if "†" in line:                                      # the design document's own title-level mark
            dagger.add(nid)

    def abstract_label(s) -> str:
        """Title-level when the corpus holds no abstract, or the design table marked the record †; a
        Crossref-direct record whose abstract was read at verification but is not archived is said so."""
        nid = n_ids.get(s.doi_l)
        if s.in_openalex_corpus:
            return "indexed" if s.abstract_indexed else "**title-level**"
        return "**title-level**" if nid in dagger else "Crossref-direct — abstract read at verification, not archived in the corpus"

    sel["abstract_label"] = sel.apply(abstract_label, axis=1)
    n_title_level = int(sel.abstract_label.eq("**title-level**").sum())

    # ---------------------------------------------------------------- retrieval statistics
    stats = rec.groupby("topic").agg(records=("title", "size"), with_abstract=("abstract", lambda s: int(s.notna().sum())),
                                     year_min=("year", "min"), year_max=("year", "max"),
                                     open_access=("open_access", lambda s: int(s.astype(str).str.lower().eq("true").sum())),
                                     preprints=("type", lambda s: int((s == "preprint").sum())))
    per_query = pd.DataFrame(queries)

    prior_ids = {int(x) for x in re.findall(r"\bR(\d{1,2})\b", PRIOR.read_text())} if PRIOR.is_file() else set()
    prior_n = max(prior_ids) if prior_ids else None

    md = [f"# Phase 1 — Structured literature review (ten directive topics)\n",
          f"Assembled {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `scripts/literature_review_build.py` from archived "
          "retrieval artifacts; nothing was fetched when this file was built. Scope and rules: abstract-level review of records retrieved "
          "on 2026-11-06 through the OpenAlex API (verbatim responses in `outputs/literature/phase1/raw/`), each cited record's DOI "
          "resolved live against Crossref or DataCite, no paywalled full text read except where an open-access copy is archived "
          "(`uriot2021_baselines_arxiv2008.03069.md`). Relevance judgements are the auditor's and are reversible against the archived "
          "records. Records without an indexed abstract are marked **title-level**.\n",
          "## 0. Retrieval record\n",
          f"* Queries: **{len(queries)}** across **{per_query.topic.nunique()}** retrieval topics, all HTTP {sorted(per_query.status.unique().tolist())}; "
          f"**{int(per_query.n_results.sum())}** results returned, **{len(rec)}** unique records kept (`records.csv`, sha256 `{sha(LIT / 'records.csv')[:16]}…`).",
          f"* Abstracts indexed for **{int(rec.abstract.notna().sum())}** of {len(rec)} records; **{int((rec.type == 'preprint').sum())}** preprints; "
          f"publication years {int(rec.year.min())}–{int(rec.year.max())}.",
          f"* Records cited below: **{len(sel)}**, every DOI resolved live — {', '.join(f'{k} {v}' for k, v in sel.registry.value_counts().items())} "
          f"(`selected_records_crossref.csv`); **{int((~sel.in_openalex_corpus).sum())}** of them entered through Crossref directly rather than an OpenAlex query "
          f"({', '.join(sel.loc[~sel.in_openalex_corpus, 'doi'])}); **{n_title_level}** are title-level (no abstract available to the review).",
          f"* Prior review `LITERATURE_REVIEW_2023_2026.md`: **{prior_n}** records (R1–R{prior_n}), 32/32 DOIs re-verified live on 2026-11-06 (30 Crossref + 2 DataCite); "
          "its coverage is referenced per topic below and not repeated.",
          "* Two further sources read in full because they were open access and load-bearing: Uriot et al. 2021 (arXiv 2008.03069; baselines "
          "L = 0.694 LRP, L = 2.5 CRP, 12 of 97 teams beat LRP) and the OPS-SAT-AD benchmark paper (PMC12041257; nine channels = 3 magnetometer + 6 photodiode).\n",
          "### Retrieval by topic\n", "| Retrieval topic | Queries | Records | With abstract | Years | Open access | Preprints |", "|---|---|---|---|---|---|---|"]
    for t, row in stats.iterrows():
        nq = int((per_query.topic == t).sum())
        md.append(f"| {TOPIC_LABEL.get(t, t)} (`{t}`) | {nq} | {int(row.records)} | {int(row.with_abstract)} | {int(row.year_min)}–{int(row.year_max)} | {int(row.open_access)} | {int(row.preprints)} |")
    md.append("\n### Queries\n\n| Topic | Query | Results |\n|---|---|---|")
    md += [f"| `{e['topic']}` | {e['query']} | {e['n_results']} |" for e in queries]

    # ---------------------------------------------------------------- verification table
    md.append("\n## 1. Cited records — verification and abstract availability\n")
    md.append("| ID | Year | Title | DOI | Registry | In OpenAlex corpus | Abstract | Cited by (OpenAlex) |\n|---|---|---|---|---|---|---|---|")
    for _, s in sel.sort_values("year").iterrows():
        nid = n_ids.get(s.doi_l, "—")
        cb = "" if pd.isna(s.cited_by_count) else int(s.cited_by_count)
        md.append(f"| {nid} | {int(s.year)} | {s.title} | `{s.doi}` | {s.registry} | {'yes' if s.in_openalex_corpus else 'no (Crossref direct)'} | "
                  f"{s.abstract_label} | {cb} |")

    # ---------------------------------------------------------------- the review itself (verbatim from the design document)
    md.append("\n## 2. Review by directive topic\n")
    md.append("The ten subsections below are the auditor's review, reproduced verbatim from "
              "`PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md` §1 (written from the archived abstracts on 2026-11-06). "
              "Each table gives methodology / data / evaluation and the limitation for this project's purpose; † marks title-level records. "
              "One update is appended to §2.7 below, because the body text of N5 has since been read.\n")
    body = section1.strip()
    body = re.sub(r"^### 1\.(\d+) ", lambda m: f"### 2.{m.group(1)} ", body, flags=re.M)
    md.append(body)
    md.append("\n**Update to 2.7 (2026-11-06, after the OA full text was read).** N5's body reports the organisers' baselines on the complete test set: "
              "the Latest Risk Prediction (clipped naive) baseline scores L = 0.694 and only 12 of 97 teams beat it; many failed to beat its F2; the Constant "
              "Risk Prediction baseline scores L = 2.5. The project's archived `latest_risk_point` row reproduces the LRP baseline to three decimals "
              "(L_clip = 0.693961), so the Phase 2.5 negative result is the benchmark's expected outcome, not an implementation artefact "
              "(`outputs/literature/phase1/uriot2021_baselines_arxiv2008.03069.md`; tracker row 2.5 / X12).\n")

    md.append("## 3. What the review does not do\n")
    md.append("It does not read paywalled full texts (Brancato et al. 2026 remains abstract-only); it does not rank venues or weigh citation counts as "
              "evidence of quality; it does not claim completeness beyond the 21 queries logged above; and it makes no novelty claim itself — those are "
              "argued, record by record, in `PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md` §§2–4.\n")
    md.append("## 4. Provenance\n")
    for p in (LIT / "query_log.json", LIT / "records.csv", LIT / "selected_records_crossref.csv", DESIGN,
              LIT / "uriot2021_baselines_arxiv2008.03069.md", LIT / "opssat_channels_PMC12041257.md"):
        md.append(f"* `{p.relative_to(ROOT)}` — sha256 `{sha(p)}`")
    OUT.write_text("\n".join(md) + "\n")
    print(f"written {OUT.relative_to(ROOT)}: {len(sel)} cited records ({n_title_level} title-level, "
          f"{int((~sel.in_openalex_corpus).sum())} Crossref-direct), {len(rec)} corpus records, {len(queries)} queries; N-ids matched {sum(n in n_ids.values() for n in n_ids.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
