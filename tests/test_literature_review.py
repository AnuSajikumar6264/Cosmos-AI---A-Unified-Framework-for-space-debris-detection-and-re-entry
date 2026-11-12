"""The Phase 1 literature review cites only live-verified records (2026-11-06).

Guards against a fabricated or unverified reference entering the review: every DOI the review
cites must be in `selected_records_crossref.csv` (resolved live, HTTP 200), every verified record
must be cited, and a record is marked title-level exactly when the archived corpus holds no
abstract for it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/research/PHASE1_LITERATURE_REVIEW.md"
LIT = ROOT / "outputs/literature/phase1"
pytestmark = pytest.mark.skipif(not REVIEW.is_file(), reason="review not built")

DOI = re.compile(r"`(10\.\d{4,9}/[^`\s]+)`")
ARXIV_BARE = re.compile(r"arXiv `(\d{4}\.\d{4,5})`")


def test_every_cited_doi_is_live_verified_and_every_verified_record_is_cited():
    text = REVIEW.read_text()
    cited = {d.lower().rstrip(".,;") for d in DOI.findall(text)}
    cited |= {f"10.48550/arxiv.{a}" for a in ARXIV_BARE.findall(text)}
    verified = set(pd.read_csv(LIT / "selected_records_crossref.csv").doi.str.lower())
    # Identifiers mentioned as *competitor context* in the design text (section 1.3 "prior coverage"),
    # not cited as review records; NOVELTY_NOTE.md verified them separately — Kotowski (arXiv 2406.17826,
    # DataCite), TC-CAD (Zenodo, DataCite), Brancato (Crossref DOI, abstract only). Keep the set explicit
    # so any new identifier appearing in the review without live verification fails this test.
    context_only = {"10.1016/j.ast.2026.113957", "10.5281/zenodo.23322711", "10.48550/arxiv.2406.17826"}
    unverified = cited - verified - context_only
    assert not unverified, f"DOIs cited without live verification: {sorted(unverified)}"
    assert verified <= cited, f"verified records not cited: {sorted(verified - cited)}"
    sel = pd.read_csv(LIT / "selected_records_crossref.csv")
    assert (sel.http == 200).all() and set(sel.registry) <= {"crossref", "datacite"}


def test_title_level_marks_match_abstract_availability():
    """Title-level <=> the corpus holds no abstract for a record in it, or the design table marked a
    Crossref-direct record with its own dagger; a Crossref-direct record whose abstract was read at
    verification is labelled as not archived, never as indexed."""
    text = REVIEW.read_text()
    table = text.split("## 1. Cited records")[1].split("## 2. Review")[0]
    rec = pd.read_csv(LIT / "records.csv")
    rec["doi_l"] = rec.doi.astype(str).str.lower().str.replace("https://doi.org/", "", regex=False)
    in_corpus = set(rec.doi_l)
    has_abstract = set(rec.loc[rec.abstract.notna(), "doi_l"])
    design = (ROOT / "docs/research/PHASE1_NOVELTY_AND_EXPERIMENTAL_DESIGN.md").read_text()
    dagger_dois = set()
    for line in design.splitlines():
        m = re.match(r"^\| (N\d+) \| [^`]*`([^`]+)`", line)
        if m and "†" in line:
            ident = m.group(2).lower()
            dagger_dois.add(ident if ident.startswith("10.") else f"10.48550/arxiv.{ident}")
    rows = [ln for ln in table.splitlines() if ln.startswith("| ") and "`10." in ln]
    assert len(rows) == 21
    for ln in rows:
        doi = DOI.search(ln).group(1).lower()
        marked_title_level = "**title-level**" in ln
        if doi in in_corpus:
            assert marked_title_level == (doi not in has_abstract), (doi, ln[:80])
            assert "indexed" in ln or marked_title_level
        else:
            assert marked_title_level == (doi in dagger_dois), (doi, ln[:80])
            assert marked_title_level or "not archived" in ln


def test_review_states_scope_and_provenance():
    text = REVIEW.read_text()
    for phrase in ("abstract-level", "resolved live", "does not read paywalled", "## 4. Provenance", "sha256"):
        assert phrase in text, phrase
    assert "L = 0.694" in text and "12 of 97" in text          # the one body-text reading, from the OA copy
