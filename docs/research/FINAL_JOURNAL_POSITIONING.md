# Final journal positioning

Date: 2026-11-04. **Recommendation: the evidence supports option A (a focused benchmark and
experimental study), but option A is a weak scope fit for the stated target journal. This
tension is the most important strategic finding in this document and is not resolvable by
rewording.**

## 1. Journal verification — what I could and could not confirm

| Item | Status | Source |
|---|---|---|
| Journal exists, publisher, ISSNs | **VERIFIED** | OpenAlex source record: *Journal of Intelligent & Robotic Systems*, ISSN-L `0921-0296`, also `1573-0409`, host organisation "Springer Science+Business Media", type `journal` |
| Open-access status | **VERIFIED** | `is_oa: false`, `is_in_doaj: false` |
| Scale and impact proxies | **VERIFIED** | `works_count: 4344`; `cited_by_count: 102518`; 2-year mean citedness **5.414**; h-index **120**; i10-index 2380 |
| **Scopus source record / category rank** | **NOT VERIFIABLE** | SCImago returned HTTP 403 (previous attempt); Scopus requires a subscription; no free API exposes category rank |
| **"Top 100 in an accepted subject category"** | **NOT VERIFIED — cannot be confirmed here** | see above |
| Aims and scope (authoritative text) | **NOT VERIFIABLE** | `link.springer.com/journal/10846/aims-and-scope` returns HTTP 303 to an `idp.springer.com` authorisation endpoint; the page is gated |
| Author instructions | **NOT VERIFIABLE** | same gating |

**Required user action.** The publication requirement — Scopus-indexed and ranked within the
top 100 of at least one accepted subject category — **must be checked by you** against Scopus
and/or SCImago using institutional access. The OpenAlex metrics above are real but are *not*
Scopus data and do not establish a category rank. **No Q1 or top-100 claim is made in this
document or anywhere in the repository.**

## 2. What the evidence actually supports

| Option | Evidence state | Verdict |
|---|---|---|
| **A** — focused catalogue-scale benchmark and experimental study | Supported. 31,396-object catalogue; two published origins plus a third unexamined origin under test (G5d); five findings verified against artifacts this session | **Defensible** |
| **B** — intelligent satellite monitoring and decision-support framework | **Refuted by the project's own experiments.** Phase E: no coupling reproduces. E12: C1 not reproducible. Phase H/G5: nominal coverage not attained in 3 of 4 deployed cells. Phase I: the abstention/evidence-grading contribution is already done ([49][52][53][54][55]) | **Not defensible** |
| **C** — combined systems-and-benchmark | Inherits B's refutation for its systems half | **Not defensible as a contribution**; the system may appear as infrastructure supporting A |

### Findings verified against artifacts this session

| Finding | Verified value |
|---|---|
| Spearman(tune-A, test) at both origins | **+0.0000** at 2011 and 2016 |
| `physics_only` rank | **17/17 at origin 2016**, **1/17 at origin 2011** |
| Slice pairs with inverted ranking | **23.64 %** (reported as 24 %) |
| `no_physics` sign reversal at one origin, both significant | `mlp@2016` **+0.006611** (p_adj 0.0163); `tabm@2016` **−0.004962** (p_adj <0.0001) |
| Loss concentration below the cap | **4.13×** (origin 2011), **6.60×** (origin 2016) |

## 3. The scope problem, stated plainly

JIRS is a journal about intelligent and robotic systems. Option A is a **benchmark and
negative-results study in orbital-lifetime forecasting** — a space-situational-awareness and
statistical-methodology contribution. Its core findings are about *model selection transfer*
and *interval calibration*, not about intelligent or autonomous systems.

The uncomfortable structure of the situation:

- The paper that **fits the journal** (option B, an intelligent monitoring and decision-support
  framework) is the one our own experiments **refute**.
- The paper we can **defend** (option A) has only a tenuous connection to the journal's scope.

Writing option A and framing it as "intelligent systems" because the Mission Intelligence
Console exists would be exactly the manufactured broadening the mandate forbids. The console is
real and works, but Phase I established that evidence-graded abstention is not a novel
contribution, and Phase E established that its cross-domain integration does not improve
prediction. It is infrastructure, not a contribution.

## 4. Recommendation

**Primary recommendation: do not submit option A to JIRS.** Submit it to a venue whose scope it
actually matches, and treat JIRS as a later target only if the additional contribution in §5
is obtained.

Better-fitting venue classes for option A (scope judgement; **rankings not verified**):

| Class | Rationale | Verification needed |
|---|---|---|
| Space-safety / astrodynamics journals (e.g. *Acta Astronautica*, *Advances in Space Research*, *Journal of Space Safety Engineering*) | the re-entry and debris literature this work sits in ([1][62]–[67]) publishes there | scope, indexing, rank — all unverified |
| Dataset / benchmark tracks | option A is a benchmark artifact plus negative results | — |
| Statistics-in-application venues | the calibration and selection-transfer findings are statistical | — |

I have **not** verified the scope, indexing or ranking of any of these. That check is yours to
make, with the same caveat as §1.

## 5. What would be needed to make a JIRS submission defensible

The mandate asks explicitly, so: a JIRS-appropriate paper would need a contribution about the
*intelligent-systems* behaviour itself, evaluated as such. Concretely, one of —

1. **A decision-quality evaluation.** Demonstrate that evidence-aware abstention improves an
   *operator decision outcome* (e.g. review burden at fixed recall, or time-to-escalation)
   against a non-abstaining baseline, on a dataset with decision outcomes. This is the natural
   JIRS framing. **Blocked today:** no decision-outcome dataset exists, and [55] already
   demonstrates budgeted deferral on ESA-ADB, so novelty would need to exceed it.
2. **A closed-loop autonomy result.** Show the system's abstention and provenance machinery
   changing a downstream automated action measurably. **Blocked:** no actuation loop exists, and
   building one would be a new project.
3. **A human-in-the-loop study.** Measure operator performance with and without the evidence
   grading. **Blocked:** requires participants and ethics approval; not initiated.

All three are blocked by data or scope, not by effort. **I am not recommending that any be
manufactured.**

## 6. Honest bottom line

The project's defensible output is a **benchmark release plus a reproducible failure analysis**.
That is publishable, and this session verified every headline number against its artifact. It is
**not** an intelligent-systems contribution, and the target journal should change rather than
the framing.

If the requirement to publish specifically in JIRS is fixed, then the honest statement is that
**the current evidence does not support a JIRS submission**, and §5 names what would.

## 7. Status

| Gate | Status |
|---|---|
| Journal existence, publisher, ISSNs, metrics | **PASS** (OpenAlex) |
| Scopus indexing and category rank | **NOT_EVALUABLE** — requires your institutional access |
| Aims-and-scope text retrieved | **FAIL** — Springer page auth-gated |
| Evidence supports a defensible paper | **PASS** — option A |
| Evidence supports the framework paper | **FAIL** — refuted by our own experiments |
| Option A fits JIRS scope | **FAIL** — weak fit; venue change recommended |
| Additional contribution identified for JIRS | **PASS** — §5, all currently blocked |
