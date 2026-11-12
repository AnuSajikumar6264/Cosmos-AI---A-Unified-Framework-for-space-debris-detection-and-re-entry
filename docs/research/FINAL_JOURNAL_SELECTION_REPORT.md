# Final journal selection report

Date 2026-11-04 · for the manuscript *"Model-Selection Instability Under Temporal Distribution
Shift in Orbital Lifetime Prediction: A Catalogue-Scale Benchmark and a Reproducibility Failure"*

**Read §1 first. It changes what your top-100 requirement means.**

---

## 1. Your top-100 requirement is weaker than you probably intend

You required *"Scopus-indexed and ranked within the top 100 in at least one accepted subject
category."* I counted the categories from Elsevier's own official Scopus source list
(`ext_list_Sep_2026.xlsx`, downloaded 2026-11-04 — the authoritative, publicly available source
record):

| ASJC | Category | Active journals | Active journals that are *journals* |
|---|---|---|---|
| **1912** | **Space and Planetary Science** | **103** | **96** |
| **3103** | **Astronomy and Astrophysics** | **97** | **90** |
| 2202 | Aerospace Engineering | 164 | 152 |
| 2213 | Safety, Risk, Reliability and Quality | 264 | 248 |
| 1710 | Information Systems | 462 | 443 |
| 3309 | Library and Information Sciences | 295 | 282 |
| 1702 | Artificial Intelligence | 554 | 523 |

**Space and Planetary Science contains 96 active journals. Astronomy and Astrophysics contains
90.** Any journal indexed in either is in the top 100 of that category *automatically*, because
the category does not have 100 journals in it. The requirement is satisfied trivially by a large
share of space journals and tells you nothing about quality.

If what you actually want is a quality bar, use **quartile (Q1) or percentile** in a named
category instead — "Q1 in Aerospace Engineering" is a real constraint; "top 100 in Space and
Planetary Science" is not. I have flagged this rather than quietly satisfying the letter of the
requirement.

## 2. Verification method, and what could not be verified

| Source | Status | What it gave |
|---|---|---|
| **Scopus Source List** (`ext_list_Sep_2026.xlsx`, Elsevier, public) | ✅ retrieved | Official source-record ID, indexing status, coverage years, ASJC categories, publisher, open-access status, and the category sizes in §1 |
| **Scopus Sources web interface** (`scopus.com/sources`) | ❌ **auth-gated** (307 → Elsevier SSO) | — |
| **Scopus source pages** (`scopus.com/sourceid/...`) | ❌ **auth-gated** | — |
| **CiteScore rank per category** | ❌ **not obtainable** — absent from the public source list, and the CiteScore interface requires a subscription | — |
| Publisher pages (ScienceDirect, SpringerLink, Nature) | ❌ 403 / SSO redirect | — |
| OpenAlex | ✅ retrieved | Non-Scopus metrics only — labelled as such below |
| Crossref | ✅ retrieved | Confirmed specific comparable publications |

**Therefore: every Scopus *rank* below is labelled UNVERIFIED.** Per your instruction I have not
substituted SCImago or OpenAlex for a Scopus rank. Indexing status and subject category *are*
officially verified, from Elsevier's own list.

**How to verify the rank yourself** (needs institutional access): sign in at
`scopus.com/sources`, search the source record ID given for each journal below, and read the
CiteScore rank and percentile for the named ASJC category. That is the only official route.

## 3. Recommendation 1 — Advances in Space Research

| | |
|---|---|
| **Official title** | Advances in Space Research |
| **Publisher** | Elsevier Ltd (on behalf of COSPAR) |
| **ISSN / eISSN** | 0273-1177 / 1879-1948 |
| **Scopus source record ID** | **12375** |
| **Scopus status** | **Active**, coverage **1981–2026** |
| **ASJC categories** | **1912 Space and Planetary Science**; 2202 Aerospace Engineering; 1902 Atmospheric Science; 1908 Geophysics; 3103 Astronomy and Astrophysics; 1900 Earth and Planetary Sciences |
| **Top-100 eligibility** | **Satisfied by category size** — ASJC 1912 has 96 active journals (§1). Actual rank: **UNVERIFIED** |
| **Non-Scopus metrics** (OpenAlex, *not* Scopus) | 2-year mean citedness 3.32; h-index 151; 27,917 works |
| **Model** | Subscription with open-access option; **APC USD 2,780** (OpenAlex-reported, confirm with publisher) |

**Why it fits.** Broad scope spanning space debris, orbital dynamics and space-environment
modelling, with a long record of catalogue-scale and methodology papers. It published
**Blake et al., *DebrisWatch I: A survey of faint geosynchronous debris*** (2021,
`10.1016/j.asr.2020.08.008`) — verified — which is a survey-and-measurement paper of comparable
character. COSPAR affiliation makes a public benchmark a natural fit, and the journal is
accustomed to papers whose contribution is data and measurement rather than a new method.

**Risk.** Broad scope means reviewers may not be specialists in forecast evaluation, so the
elicitability argument (§7.3) and the cluster-bootstrap inference may need more exposition.

## 4. Recommendation 2 — CEAS Space Journal

| | |
|---|---|
| **Official title** | CEAS Space Journal |
| **Publisher** | Springer-Verlag Wien (Springer Nature) |
| **ISSN / eISSN** | 1868-2502 / 1868-2510 |
| **Scopus source record ID** | **19700170911** |
| **Scopus status** | **Active**, coverage **2011–2026** |
| **ASJC categories** | **1912 Space and Planetary Science**; 2202 Aerospace Engineering |
| **Top-100 eligibility** | **Satisfied by category size** — ASJC 1912, 96 active journals. Actual rank: **UNVERIFIED** |
| **Non-Scopus metrics** (OpenAlex) | 2-year mean citedness 1.91; h-index 33; 776 works |
| **Model** | Subscription with OA option; **APC USD 3,390** (OpenAlex-reported, confirm) |

**Why it fits — this is the strongest *genre* match.** CEAS Space Journal published
**Herrmann et al., *Unmasking overestimation: a re-evaluation of deep anomaly detection in
spacecraft telemetry*** (2024, `10.1007/s12567-023-00529-5`) — verified. That paper is the direct
precedent for this one: a re-evaluation showing published results overestimated, simple baselines
sometimes superior, and the field in need of high-quality pre-split datasets. Our manuscript
explicitly extends that line into orbital lifetime prediction. **An editor who accepted Herrmann
et al. has already accepted the premise that this kind of paper belongs in the journal** — which
is the single most useful fact in this report for a paper whose central results are negative.

**Risk.** Much smaller and less cited than the alternatives. If your institution or examiners
weight journal metrics, this will look weakest on paper despite being the best scope fit.

## 5. Recommendation 3 — Acta Astronautica

| | |
|---|---|
| **Official title** | Acta Astronautica |
| **Publisher** | Elsevier Ltd (on behalf of the IAA) |
| **ISSN** | 0094-5765 |
| **Scopus source record ID** | **12372** |
| **Scopus status** | **Active**, coverage **1974–2027** |
| **ASJC categories** | **2202 Aerospace Engineering only** |
| **Top-100 eligibility** | **Not automatic.** ASJC 2202 has **152 active journals**, so top-100 requires a genuine rank better than 100/152. Plausible given the journal's standing, but **UNVERIFIED** |
| **Non-Scopus metrics** (OpenAlex) | 2-year mean citedness 4.17; h-index 133; 15,353 works |
| **Model** | Subscription with OA option; **APC USD 3,350** (OpenAlex-reported, confirm) |

**Why it fits.** The leading general astronautics journal and the venue of
**Caldas & Soares, *Machine learning in orbit estimation: A survey*** (2024,
`10.1016/j.actaastro.2024.03.072`) — verified, and cited in our manuscript as the field's own
framing of its open problem. Publishing a paper that answers a question that survey left open, in
the journal that published the survey, is a coherent placement.

**Risk and an important caveat.** It is the only one of the three whose top-100 eligibility is
**not** guaranteed by category size, so it is the one where your requirement genuinely depends on
an unverified rank. Also, as an engineering journal it may expect a methodological advance; a
paper whose contributions are an artifact and a negative result is a harder sell than at CEAS.

## 6. Why not JIRS — your original target

| | |
|---|---|
| **Official title** | **Journal of Intelligent and Robotic Systems: Theory and Applications** |
| **Publisher** | Springer Nature |
| **ISSN / eISSN** | 0921-0296 / 1573-0409 |
| **Scopus source record ID** | **24360** |
| **ASJC categories** | 2210 Mechanical Engineering; 2209 Industrial and Manufacturing Engineering; 2207 Control and Systems Engineering; 1712 Software; **1702 Artificial Intelligence**; 2208 Electrical and Electronic Engineering |

**It has no space, aerospace, astrodynamics, or earth-and-planetary category at all.** Its
categories are mechanical, manufacturing, control, software, AI and electrical engineering. A
catalogue-scale orbital-lifetime benchmark with a negative result about forecast-evaluation
methodology does not sit in any of them.

Two consequences:

1. **Scope mismatch is severe**, and desk rejection is the likely outcome. The paper contains no
   robot, no control system and no intelligent agent.
2. **Top-100 would also be harder, not easier.** Its categories are large — Artificial
   Intelligence alone has 523 active journals — so a top-100 position there requires a far better
   rank than top-100 in a 96-journal space category.

**Recommendation: do not submit this manuscript to JIRS.** You asked me not to force it, and the
official source record confirms the fit is wrong on category grounds, not merely on taste.

## 7. A strategic option worth considering: split the paper

The manuscript currently does two things: it **releases a benchmark** and it **reports a negative
methodological finding plus a reproducibility audit**. Those have different natural homes.

- **Scientific Data** (Nature Research, Scopus source ID **21100451321**, Active, 2014–2026,
  eISSN 2052-4463, Unpaywall Open Access, **APC USD 2,490**) published
  **Ruszczak et al., *The OPS-SAT benchmark for detecting anomalies in satellite telemetry***
  (2025, `10.1038/s41597-025-05035-3`) — verified, and cited in our manuscript as the precedent
  for publishing a domain benchmark. Non-Scopus metrics: 2-year mean citedness 6.05, h-index 215.
  **Caveat:** its ASJC categories are 2613, 1804, 1710, 1706, 3309, 3304 — **no space category**,
  and those categories are large (Information Systems 443, Library and Information Sciences 282),
  so top-100 there needs a real rank and is **UNVERIFIED**. More importantly, its primary article
  type is the **Data Descriptor**, which describes a dataset; our negative selection finding and
  reproducibility audit would not fit that format and would have to be removed.
- The **analysis paper** then goes to CEAS Space Journal or Advances in Space Research, citing the
  deposited benchmark by DOI.

**This also resolves blocker B-2.** The benchmark currently has no public deposit, which is a hard
blocker on submitting it as a benchmark paper anywhere. Depositing it — whether as a Scientific
Data descriptor or a plain Zenodo record — is required regardless of venue.

## 8. Recommendation, stated plainly

**Submit to CEAS Space Journal first.** It is the only venue with a direct, verified precedent for
this exact genre (Herrmann et al. 2024), its ASJC 1912 membership satisfies your top-100
requirement by category size, and an editor there has demonstrably accepted the premise that
negative re-evaluations belong in the journal. The paper's weakest point is the strength of its
claims, and CEAS is the venue least likely to reject it for that reason.

**Advances in Space Research second** — larger, better cited, same automatic top-100 route, broader
reviewer pool.

**Acta Astronautica third**, and only if an unverified aerospace-engineering rank is acceptable to
you, since it is the one candidate whose top-100 status is not guaranteed by category size.

**Before any submission**, resolve blocker B-2: deposit the benchmark and obtain a DOI.

## 9. What is UNVERIFIED, restated

Per your instruction, labelled explicitly:

| Claim | Status |
|---|---|
| All five journals are Scopus-indexed and Active, with the stated categories and coverage | ✅ **OFFICIALLY VERIFIED** from Elsevier's Scopus source list |
| Category sizes in §1 | ✅ **OFFICIALLY VERIFIED** — counted from the same list |
| Comparable publications named in §3–§7 | ✅ **VERIFIED** via Crossref/OpenAlex (DOIs given) |
| **Scopus CiteScore rank or percentile for any journal** | ❌ **UNVERIFIED** — requires a subscription; not in any public source |
| **Whether any journal is top-100 on an actual rank** | ❌ **UNVERIFIED.** For ASJC 1912 and 3103 journals it is satisfied by category size regardless |
| APC amounts | ⚠️ OpenAlex-reported, **not** publisher-confirmed — the publisher pages returned 403/SSO. Confirm before relying on them |
| Aims-and-scope text | ⚠️ **Not retrieved** — all three publisher sites blocked automated access. Scope judgements above rest on the verified comparable publications and the official ASJC categories, not on quoted scope statements. **Read each journal's aims and scope yourself before submitting** |
| Institutional APC funding | ❌ **Not verifiable** from here — depends on your institution's agreements. Check whether your institution has a Springer Nature or Elsevier read-and-publish agreement, which would cover the OA fee at CEAS/ASR/Acta |

## 10. Reproducing this report

```
# the official Scopus source record and category sizes
curl -L -o ext_list.xlsx "https://downloads.ctfassets.net/o78em1y1w4i4/7xtaTxNiNcWRTeZkV86eNy/\
e6b17b29beaf8d18175591a4e8dee0bf/ext_list_Sep_2026.xlsx"
python -I scripts/tmp_scopus/read_scopus.py ext_list.xlsx "acta astronautica" "ceas space journal"
python -I scripts/tmp_scopus/count_asjc.py ext_list.xlsx 2202 1912 3103
```

The reader scripts use only the Python standard library (an xlsx is a zip of XML), so reproducing
this requires no additional packages and does not modify the analysis environment.
