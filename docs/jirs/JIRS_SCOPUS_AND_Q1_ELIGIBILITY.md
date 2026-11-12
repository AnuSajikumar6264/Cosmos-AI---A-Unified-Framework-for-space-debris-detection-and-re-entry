# JIRS Scopus and Q1 eligibility verification (Phase 8 / Part 10)

Date 2026-11-04

**Summary: Scopus indexing, source ID, status, coverage and subject categories are OFFICIALLY
VERIFIED. CiteScore, rank, percentile and quartile are UNVERIFIED — the official sources are
subscription-gated and I will not substitute third-party rankings as proof.**

---

## 1. Officially verified record

Source: **Elsevier's official Scopus source title list**, `ext_list_Sep_2026.xlsx`, downloaded
2026-11-04 from Elsevier's publicly documented location. This is the authoritative public Scopus
source record.

| Field | Value | Status |
|---|---|---|
| **Official Scopus source title** | **Journal of Intelligent and Robotic Systems: Theory and Applications** | ✅ **VERIFIED** |
| **Scopus Source ID** | **24360** | ✅ **VERIFIED** |
| ISSN | 0921-0296 | ✅ VERIFIED (matches your value) |
| eISSN | 1573-0409 | ✅ VERIFIED (matches your value) |
| **Active or discontinued** | **Active** | ✅ **VERIFIED** |
| **Coverage years** | **1988–2026** | ✅ **VERIFIED** |
| Publisher | Springer Nature | ✅ VERIFIED (matches your value) |
| Source type | Journal | ✅ VERIFIED |
| Articles in press | not flagged | ✅ VERIFIED |
| Open-access status | not flagged as open access | ✅ VERIFIED |

Note: the official Scopus title uses "**and**", not "&". Submission metadata and the reference
list should use the official form.

### 1.1 Subject categories (ASJC) — officially verified

| ASJC | Category | Active journals in category | Active *journals* only |
|---|---|---|---|
| 2210 | Mechanical Engineering | 719 | 663 |
| 2209 | Industrial and Manufacturing Engineering | 411 | 361 |
| **2207** | **Control and Systems Engineering** | **340** | **306** |
| 1712 | Software | 394 | 380 |
| 1702 | Artificial Intelligence | 554 | 523 |
| 2208 | Electrical and Electronic Engineering | 871 | 820 |

All six counts computed from the same official source list.

**There is no space, aerospace, astrodynamics, planetary or earth-science category.** The nearest
is Control and Systems Engineering.

## 2. Your absolute top-100 requirement

You require an absolute Scopus rank within the first 100 positions in at least one relevant
category. Against the verified category sizes:

| Category | Active journals | Top-100 means | Required percentile |
|---|---|---|---|
| **Control and Systems Engineering** | **306** | top 100 of 306 | **top 32.7 %** |
| Software | 380 | top 100 of 380 | top 26.3 % |
| Industrial and Manufacturing Engineering | 361 | top 100 of 361 | top 27.7 % |
| Artificial Intelligence | 523 | top 100 of 523 | **top 19.1 %** |
| Mechanical Engineering | 663 | top 100 of 663 | top 15.1 % |
| Electrical and Electronic Engineering | 820 | top 100 of 820 | top 12.2 % |

**The easiest route is Control and Systems Engineering: JIRS needs to sit in the top ~33 % of 306
journals.** Whether it does is **UNVERIFIED** (see §4).

**Context worth having.** This is a materially harder bar than the one we discussed for space
journals. Space and Planetary Science has only 96 active journals, so top-100 there is automatic.
JIRS's smallest category has 306, so the requirement is a genuine constraint — **your requirement
is stricter at JIRS than it would have been at a space venue, not looser.**

## 3. The four ranking systems — kept distinct, as you asked

These are **not interchangeable** and are computed by different organisations from different data.

| System | Operator | Metric basis | Quartile definition | Relationship to your requirement |
|---|---|---|---|---|
| **Scopus CiteScore quartile** | Elsevier | CiteScore: citations over a 4-year window ÷ documents, same window | Q1 = top 25 % of journals in the ASJC category by CiteScore rank | **Q1 ≠ top-100.** In Control & Systems Eng (306) Q1 = top ~76, so **Q1 is stricter** than top-100. In AI (523) Q1 = top ~131, so **top-100 is stricter** than Q1 |
| **Scopus absolute category rank** | Elsevier | CiteScore rank position | — | **This is your stated requirement** |
| **SCImago Journal Rank (SJR) quartile** | SCImago (third party, uses Scopus data) | SJR: prestige-weighted citations | Q1 = top 25 % by SJR within a SCImago category | **Not Scopus's own quartile.** SCImago categories do not always match ASJC exactly. You instructed me not to rely on this as proof |
| **Journal Impact Factor quartile** | Clarivate | JIF: Web of Science citations, 2-year window | Q1 = top 25 % by JIF within a **JCR** category | **Different database and different categories entirely.** A JIF Q1 says nothing about a Scopus rank |

**Consequence:** a claim that "JIRS is Q1" is ambiguous until you say *which* system. The three
quartile systems can and do disagree for the same journal.

## 4. What could NOT be verified, and why

| Target | Attempt | Outcome |
|---|---|---|
| CiteScore value | `scopus.com/sources` | **❌ auth-gated** — HTTP 307 to Elsevier SSO (`id.elsevier.com/as/authorization.oauth2`) |
| CiteScore rank and total in category | Scopus source page `scopus.com/sourceid/24360` | **❌ auth-gated** — same redirect |
| CiteScore percentile | Scopus Sources interface | **❌ auth-gated** |
| Official CiteScore quartile | Scopus Sources interface | **❌ auth-gated** |
| CiteScore columns in the public source list | `ext_list_Sep_2026.xlsx` | **❌ not present** — the public list carries indexing status, coverage, ASJC codes, publisher and OA status, but **no citation metrics** |
| JIRS aims and scope, author instructions | `link.springer.com/journal/10846` | **❌ SSO redirect** |

**Therefore every rank, percentile, CiteScore and quartile figure for JIRS is formally
UNVERIFIED in this report.** I have not substituted SCImago or OpenAlex for any of them.

## 5. Non-Scopus context — explicitly labelled, not evidence

Provided only so you are not flying blind. **This is OpenAlex data and is NOT a Scopus metric. It
must not be cited as a Scopus rank, CiteScore or quartile.**

| OpenAlex field | Value |
|---|---|
| Display name | Journal of Intelligent & Robotic Systems |
| Host organisation | Springer Science+Business Media |
| Works count | 4,344 |
| Cited-by count | 102,518 |
| **2-year mean citedness** | **5.41** |
| h-index | 120 |
| i10-index | 2,380 |
| Open access | No |
| APC (OpenAlex-reported, **not** publisher-confirmed) | **USD 3,090** |
| Leading topics | Robotic Path Planning; Robotic Mechanisms and Dynamics; Control and Dynamics of Mobile Robots; Robotics and Sensor-Based Localization; Adaptive Control of Nonlinear Systems; Aerospace Engineering and Control Systems; Robot Manipulation and Learning; Reinforcement Learning in Robotics |

A 2-year mean citedness of 5.41 is substantial for an engineering journal, and makes a top-33 %
position in Control and Systems Engineering **plausible**. **Plausible is not verified**, and I am
not going to convert this into a quartile claim.

## 6. How to verify this yourself — the only official route

1. Sign in to Scopus with your institutional credentials at `https://www.scopus.com/sources`.
2. Search source ID **24360** (or ISSN 0921-0296).
3. On the source page, read for each ASJC category: **CiteScore**, **CiteScore year**, **rank**
   (the "#X of Y" figure), **percentile**, and **quartile**.
4. Record the figure for **2207 Control and Systems Engineering** first — it is the category where
   your top-100 requirement is most attainable.
5. If you also want a defensible Q1 claim, note **which system** the quartile comes from and cite
   it as such — "Scopus CiteScore Q1 in Control and Systems Engineering (CiteScore 20XX)" rather
   than an unqualified "Q1".

Springer's own journal page typically displays the CiteScore and Impact Factor publicly; it was
not retrievable here, but it may be in a browser.

## 7. Assessment

| Question | Answer |
|---|---|
| Is JIRS Scopus-indexed? | **Yes — verified.** Source ID 24360, Active, 1988–2026 |
| Is it in a relevant subject category? | **Yes for intelligent systems** (Control and Systems Engineering; Artificial Intelligence). **No for space, aerospace or astrodynamics** — no such category |
| Does it meet your absolute top-100 requirement? | **UNVERIFIED.** The best route is top 100 of 306 in Control and Systems Engineering (top 32.7 %) |
| Does it qualify as Q1? | **UNVERIFIED, and ambiguous until you specify the system.** Scopus CiteScore Q1, SJR Q1 and JIF Q1 are three different claims |
| Is the venue scientifically appropriate for this work? | **This is the real problem, and it is independent of the ranking.** See below |

## 8. The point that matters more than the ranking

JIRS's eligibility on your metric is probably satisfiable and currently unverified. **That is not
the binding constraint.**

The binding constraint is scope. Of the complete set of **282 JIRS records published from 2023
onward**, 56.4 % are explicitly robotics and **2.1 % are space-related** — six papers in three
years. JIRS has no space or aerospace ASJC category. A journal can be Q1 and still be the wrong
venue, and a rank in Control and Systems Engineering will not help a manuscript that an editor
reads as space science.

**Verifying JIRS's quartile will not change whether this manuscript should be submitted to JIRS.
Reframing the manuscript might.** That is the subject of the revision plan, and it is where the
remaining effort should go.
