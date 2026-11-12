# JIRS final submission roadmap (Phase 9)

Date 2026-11-04 · target: Journal of Intelligent and Robotic Systems: Theory and Applications
(Scopus source ID 24360)

**Nothing in this roadmap has been executed. It begins with a decision only you can make.**

---

## Stage 0 — Your decisions (blocking everything)

| # | Decision | Why it is yours | Default if you say nothing |
|---|---|---|---|
| D1 | **Approve the reframing (Option R1)** — lead with model-selection reliability in spacecraft intelligent systems, evidenced by anomaly detection and lifetime prediction | It changes the paper's subject. Without it the submission is a scope rejection | Blocked |
| D2 | **Approve experiments E1–E3, E5** (essential + near-free) | Compute and time | Blocked |
| D3 | **Decide whether to claim decision support**, i.e. whether to run E4 | Determines whether the paper has a decision-support contribution at all | Do not claim |
| D4 | **Approve the benchmark release**: repository visibility, code licence, data licence | Legal and account decisions | Blocked |
| D5 | **Resolve the AGPL boundary** — `ultralytics==8.4.185` is AGPL-3.0 against a permissive repository licence | Legal determination | Blocked |
| D6 | **Vendor position on `kumo`** (`sdm.models.KumoTabular`) — may a derived checkpoint be released? | Contractual | Do not release |
| D7 | **Confirm authorship, affiliations, funding, conflicts, prior-publication overlap** | Only you know these | Blocked |
| D8 | **Read JIRS's AI-disclosure policy and write the disclosure** | This project used substantial AI assistance; the disclosure must be accurate and is yours to make | Blocked |

## Stage 1 — Near-free statistical hardening (hours, no fitting)

| Step | Action | Output |
|---|---|---|
| 1.1 | **E3** — cluster-bootstrap reference distribution for the ranking-instability criterion, replacing the uniform-permutation null | Defuses the strongest statistical objection (R3 major concern 4) |
| 1.2 | **E5** — selection regret at every origin, from archives | Converts ρ into an operational cost (R3 missing experiment) |
| 1.3 | Per-arm bootstrap intervals and paired tests on the main lifetime leaderboard | Closes R3 major concern 3 |
| 1.4 | Bootstrap CI + exact permutation p-value for every reported ρ | Closes R1 major concern 2 and gap S1 |

**Run Stage 1 first regardless of other decisions.** It is cheap, it strengthens the statistics
immediately, and E5's regret magnitudes will indicate how compelling E2 is likely to be before any
GPU time is committed.

## Stage 2 — The essential experiments

| Step | Action | Cost | Gate |
|---|---|---|---|
| 2.1 | **E1** — time-blocked significance test for the OPS-SAT detector; **persist the score archive** | 2–6 GPU-h | D2 |
| 2.2 | **Pre-register E2** — ladder of selection→test temporal gaps, arm set, statistic, decision rule, minimum rungs. **Hash-seal before any fitting** using the existing `check_preregistration` machinery | hours | D2 |
| 2.3 | **E2** — execute the pre-registered ladder | 6–20 GPU-h | 2.2 sealed |
| 2.4 | **E6** — fusion-branch ablation for the `hybrid` detector | low | optional |
| 2.5 | **E7** — robustness under induced missing data (connects directly to JIRS [J3]) | low–moderate | optional |
| 2.6 | **E4** — decision-layer evaluation, **pre-registered before scoring** | 1–2 days analysis | D3 |

**Do not proceed to Stage 4 until 2.3 has completed**, whatever its outcome. If E2 fails to support
the monotonicity hypothesis, that is a legitimate result and the paper reports it — but the paper
cannot be *written around* a contribution that has not been established.

## Stage 3 — Release and artifact (resolves the blocker)

| Step | Action |
|---|---|
| 3.1 | Wire `provenance.run_metadata()` into run entry points (forward-only) |
| 3.2 | Declare the five missing backends with an explicit forward-pin comment |
| 3.3 | Generate `MANIFEST.sha256` over every released file, including the origin-2006 archive |
| 3.4 | Write `REPRODUCE.md` and `ENVIRONMENT.md` (per-module honesty: telemetry refittable, lifetime not) |
| 3.5 | Add the inherited-terms note to the derived-dataset manifest |
| 3.6 | Re-verify redistribution rights for all seven upstream sources **at release date** |
| 3.7 | Tag a GitHub release; create the Zenodo deposit; **obtain the DOI** |
| 3.8 | Insert the DOI into the manuscript; clear the `[PENDING EVIDENCE]` marker |

**Run 3.1–3.6 after E1**, so the deposit contains the score archive rather than a known hole.

## Stage 4 — Manuscript rewrite

Per `JIRS_MANUSCRIPT_REVISION_PLAN.md` §3. Roughly 60 % of the text changes. Key items:

- New title and abstract leading with reliability, not the benchmark.
- Keywords mapped to Control and Systems Engineering / AI.
- Introduction motivated from assurance of machine-learned components, citing [J1].
- **At least five JIRS citations** — currently zero.
- Formalise the selection-transfer statistic and selection regret.
- Results restructured to lead with E2, then E1's anomaly-detection result, then the lifetime
  negative, then collision risk, reproducibility and the integration negative.
- Three new figures: system architecture (showing where uncertainty stops), the temporal ladder,
  the OPS-SAT comparison with compute.
- **Every power disclosure, self-correction and prohibited claim preserved** — see revision plan §5.

## Stage 5 — Pre-submission verification

| Step | Action |
|---|---|
| 5.1 | Re-run `scripts/final_system_audit.py`; extend it to cover the new claims |
| 5.2 | Re-run the full test suite |
| 5.3 | Verify every manuscript number against its artifact, including the new ones |
| 5.4 | Verify every reference resolves; confirm the JIRS citations |
| 5.5 | Confirm all `[PENDING EVIDENCE]` markers are resolved or still accurate |
| 5.6 | Independent adversarial read, as in the prior round — it found 25 real issues last time |
| 5.7 | Claim-inflation pass: the most likely failure mode is a verb creeping up a tier |
| 5.8 | Format to JIRS requirements; confirm article type and length |
| 5.9 | Complete the AI disclosure, authorship, funding and conflict statements |

## Stage 6 — Phase F, if it unblocks

On or after **2026-11-26** the 30-day horizon of the registered 2026-10-27 forecast becomes
scoreable. If it does: verify the snapshot's provenance, confirm eligibility, run **only** the
pre-registered evaluation, and report the outcome **including a negative one**. Do not hold the
submission for it, and do not substitute a retrospective fold.

## Dependency graph

```
D1,D2 ──► Stage 1 (E3,E5) ──┐
                            ├──► Stage 2.1 (E1) ──► Stage 3 (release+DOI) ──┐
D2 ────► Stage 2.2 (seal) ──┴──► Stage 2.3 (E2) ─────────────────────────────┼──► Stage 4 ──► Stage 5 ──► SUBMIT
D3 ────► Stage 2.6 (E4) ─────────────────────────────────────────────────────┘
D4,D5,D6 ──► Stage 3
D7,D8 ─────────────────────────────────────────────────────────────────────────► Stage 5.9
```

## Effort estimate

| Stage | Effort | Calendar |
|---|---|---|
| 0 decisions | your time | — |
| 1 statistical hardening | hours | 1 day |
| 2 experiments | 8–26 GPU-h + 2–3 days analysis | 1 week |
| 2.6 E4 if claimed | 1–2 days | +2 days |
| 3 release | 1 day + your licence decisions | 1–2 days |
| 4 rewrite | substantial | 1–2 weeks |
| 5 verification | 2–3 days | 3 days |
| **Total** | — | **approximately 3–4 weeks of focused work** |

## Exact next action

**Read `JIRS_Q1_READINESS_REPORT.md`, then tell me whether you approve D1 (the reframing) and D2
(experiments E1–E3, E5).**

If you approve D2 alone, I will begin with **E3 and E5** — the two analyses that need no fitting,
touch no frozen artifact, and will sharpen the statistics within hours.

If you decline the reframing and want the current manuscript submitted to JIRS as it stands, I will
do the formatting and administrative work — but I would be doing so against my assessment, and the
simulated review's predicted outcome is desk rejection on scope.
