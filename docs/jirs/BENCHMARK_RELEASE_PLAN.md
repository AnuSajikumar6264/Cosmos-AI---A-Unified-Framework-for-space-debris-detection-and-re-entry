# Benchmark release plan

Date 2026-11-04 · **NOTHING HAS BEEN RELEASED. No DOI exists. This is a plan requiring your
approval and your accounts.**

Resolves blocker **R8**. A paper whose contribution is an artifact cannot be submitted while the
artifact is unobtainable.

---

## 1. What exists now

| | |
|---|---|
| GitHub repository | `https://github.com/AnuSajikumar6264/Cosmos-AI-` — exists, LFS-tracked, last commit `78ee339` |
| Archival deposit | **none** |
| DOI | **none** |
| Release tag | **none** |
| Source-code licence | **none found in the repository** |
| Dataset licence | **none stated for derived products** |

**You must confirm whether the GitHub repository is currently public or private before any data
availability statement is written.** I have not assumed either.

## 2. Recommended split: GitHub for code, Zenodo for the citable artifact

| Component | Where | Why |
|---|---|---|
| Source code, pipelines, audit harnesses, tests | **GitHub**, with a tagged release | Versioned, browsable, issue-tracked |
| Derived cohort, per-object predictions, leaderboards, result JSONs, figures, pre-registration documents and hash seals | **Zenodo** deposit linked to the GitHub release | Immutable, citable, DOI-bearing, survives repository changes |
| Raw third-party catalogue and benchmark files | **neither** — point to the upstream providers | Redistribution rights not established; see §4 |
| Model checkpoints | **Zenodo, selectively** — see §5 | Vendor and licence constraints |

Zenodo's GitHub integration mints a DOI per release and gives a concept DOI for all versions,
which is what a manuscript should cite.

## 3. Recommended licences — for your decision

| Artifact | Recommendation | Reasoning |
|---|---|---|
| Source code | **MIT** or **Apache-2.0** | Permissive, standard for research code. **Apache-2.0** if you want an explicit patent grant |
| Derived data, predictions, leaderboards | **CC-BY-4.0** | Standard for research data; requires attribution |
| Documentation and manuscript drafts | **CC-BY-4.0** | Consistent with the data |

**Licence conflict to check before release.** `requirements-ai.txt` declares
`ultralytics==8.4.185`, which is **AGPL-3.0**, with the in-repo comment "baseline use only".
AGPL-3.0 is strongly copyleft. If any released code path imports `ultralytics`, a permissive
licence on the whole repository may be inconsistent. **Action: confirm the YOLO baseline is
isolated from the released code paths, or isolate it, or document the licence boundary
explicitly.** I flag this rather than resolve it — it is a legal determination.

## 4. Redistribution rights — must be verified before release

| Source | Used for | Status | Action required |
|---|---|---|---|
| **GCAT** (Jonathan McDowell) | cohort definition | Terms recorded in the manifest | **Re-read the terms at release date**; confirm derived-product redistribution |
| **CelesTrak** SATCAT + `SW-All` | outcome labels, space weather | Terms recorded | Same |
| **ESA-ADB** | anomaly benchmark | DOI + licence + code licence recorded | Confirm the licence permits redistribution of derived results |
| **OPS-SAT AD** | anomaly benchmark | DOI + paper DOI + licence recorded | Same |
| **ESA Kelvins CAC** | conjunction | DOI + licence recorded | Challenge data often carry use restrictions — **verify explicitly** |
| **SpotGEO** | debris | DOI + licence + source URLs recorded | Same |
| **SMAP/MSL** | telemetry | Paper DOI + source + licence recorded | Same |
| **SPARK** | not used | **never obtained** (access-gated) | **Nothing to release.** Correctly documented |

**Policy: redistribute derived products only — cohorts, predictions, metrics, figures. Do not
redistribute upstream raw files.** Provide retrieval scripts and the recorded snapshot dates so a
reader can rebuild inputs from the providers under those providers' terms.

## 5. Model checkpoints — selective release

| Learner | Release? | Reason |
|---|---|---|
| `xgboost`, `mlp` (lifetime); all OPS-SAT deep arms | **Yes, if available** | Permissive backends; small (≤ 74k params) |
| `lightgbm`, `catboost`, `tabm`, `tabicl` | Only if checkpoints exist and licences permit | Backends undeclared; verify each |
| **`kumo`** | **No** | Depends on `sdm.models.KumoTabular`, a **commercial vendor library**. Releasing a derived model may breach the vendor's terms. **Do not release without written vendor permission.** Disclose the constraint in the paper instead |

**Never release third-party model weights or restricted data without written permission.** This
applies to the Chronos foundation-model weights (redistribute nothing; cite and pin the version)
and to anything derived from the vendor library.

## 6. Release package structure

```
cosmos-ai-benchmark-v1.0.0/
  README.md                     # what this is, how to cite, DOI
  LICENSE                       # code licence
  LICENSE-DATA                  # CC-BY-4.0 for data
  REPRODUCE.md                  # gap R7: single entry point
  CITATION.cff
  MANIFEST.sha256               # checksums for every released file (gap R6)
  ENVIRONMENT.md                # what is and is not refittable, per module
  data/
    cohort/                     # derived lifetime cohort + manifest
    splits/                     # explicit split definitions per origin
    retrieval/                  # scripts to rebuild upstream inputs
  predictions/
    lifetime/origin{2006,2011,2016}/   # per-object quantiles, all arms
    telemetry_opssat/                   # fragment scores (gap R4)
    conjunction/ debris/
  results/                      # leaderboards, result JSONs, coverage tables
  preregistration/              # protocols + hash seals + deviation logs
  figures/                      # all figures + generating scripts
  code/                         # tagged source snapshot
```

## 7. Release checklist — sequenced

**Pre-release (blocking)**
- [ ] Confirm GitHub repository visibility (public/private)
- [ ] Choose and add a code licence; resolve the AGPL/`ultralytics` boundary (§3)
- [ ] Choose and add a data licence
- [ ] Re-verify redistribution terms for all seven upstream sources (§4)
- [ ] Obtain vendor guidance on `kumo`, or exclude it from any checkpoint release
- [ ] Confirm no restricted or personal data is present (SPARK was never obtained)

**Build**
- [ ] Persist the OPS-SAT score archive during experiment E1 (gap R4)
- [ ] Generate `MANIFEST.sha256` covering every released file, including the origin-2006
      prediction archive (gap R6)
- [ ] Write `REPRODUCE.md` with a driver script (gap R7)
- [ ] Write `ENVIRONMENT.md` stating per-module refittability honestly (telemetry: yes; lifetime:
      no) — must not claim the lifetime models are refittable
- [ ] Add inherited-terms note to the derived-dataset manifest (gap R1)
- [ ] Wire `provenance.run_metadata()` into run entry points so future runs self-document (gap R2)
- [ ] Declare the five missing backends with an explicit **forward-pin** comment stating these are
      not the versions that produced the published results (gap R3)

**Deposit**
- [ ] Tag a GitHub release `v1.0.0`
- [ ] Create the Zenodo deposit; obtain the concept DOI and the version DOI
- [ ] Insert the DOI into the manuscript's data-availability statement, replacing the
      `[PENDING EVIDENCE]` marker
- [ ] Verify every manuscript artifact path resolves inside the released package

## 8. Draft data availability statement — hold until the DOI exists

> The COSMOS-AI orbital-lifetime and spacecraft-telemetry benchmarks, including derived cohorts,
> explicit temporal split definitions, per-object and per-fragment model predictions for every
> arm, leaderboards, result files, figures, pre-registration documents with their hash seals, and
> the audit harnesses that re-derive every reported value, are archived at Zenodo under DOI
> `[DOI PENDING]` and mirrored at `https://github.com/AnuSajikumar6264/Cosmos-AI-` under release
> `[TAG PENDING]`. Derived products are released under CC-BY-4.0 and source code under
> `[LICENCE PENDING]`.
>
> The benchmarks derive from publicly available sources: GCAT, the CelesTrak satellite catalogue
> and space-weather indices (snapshot 2026-10-27), the ESA-ADB and OPS-SAT anomaly benchmarks, the
> ESA Kelvins CAC conjunction challenge data, and the SpotGEO dataset. We redistribute derived
> products only; retrieval scripts and recorded snapshot dates allow upstream inputs to be
> rebuilt under the providers' own terms. No restricted or personal data are included. Model
> checkpoints are released where the backend licence permits; the `kumo` arm depends on a
> commercial vendor library and its checkpoint is **not** released.

**Do not publish any form of this statement, and do not cite a DOI, until the deposit exists and
you have approved it.** No DOI has been invented here.

## 9. Honest note on sequencing

Release and experiments interact: **E1 should be run before the deposit is built**, because it
produces the missing OPS-SAT score archive (gap R4) that the package should contain. Depositing
first would mean depositing a package with a known hole in it.
