# COSMOS-AI — Release preparation proposal (Phase G, 2026-11-08)

Nothing in this document has been executed: no file is staged, no commit, tag or push was made. Every step below waits for
the owner's explicit approval. Authorship rule: the owner's configured Git identity only; no AI co-author trailer.

## 1. Repository state

| Item | Value |
|---|---|
| Branch · HEAD | `product/mission-intelligence-console` · `938d514` (approved checkpoint of P0–P3-B) |
| Modified tracked files since the checkpoint | 47 (console code and templates, product docs, manuscript and checklist, audit and verifier scripts, one test, thesis sources, 15 regenerated screen captures) |
| New untracked files to include | 32 (demo template, reports, tracker, protocols, K7 draft, scripts, tests, thesis chapters, draft render, audit records, T1 analysis outputs) |
| Deliberately excluded, unchanged from the checkpoint decision | 88 `outputs/pipeline/` run directories, `outputs/run_20261103T155605Z/`, 14 Phase 3 CSV copies, the 78 MB `outputs/twin/as_of_2026-10-27_reemitted_v1/twins.jsonl` |
| Protected artifacts | all research artifacts verify; the figure release manifest reports two of its hashed *documents* changed — `tests/test_figures.py` (commit-aware invariant) and `paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md` (mandated corrections) |

## 2. Two decisions the owner must take before the release commit

1. **Re-issue the figure release manifest.** The manuscript and the figure test are hashed documents of
   `paper/figures/RELEASE_MANIFEST.json` (frozen 2026-11-06 at `78ee339`). After approval, run
   `python scripts/figures/make_release_manifest.py --tests <passed>/<total>` so that the manifest's document hashes and git
   block describe the released state; archive the previous manifest beside it (`RELEASE_MANIFEST_2026-11-06.json`) so the
   earlier freeze stays inspectable. Figures, source data and upstream artifacts are unchanged and will hash identically.
   Until then `scripts/verify_protected_artifacts.py` reports `all_protected_ok: False` naming exactly those two files.
2. **The re-emitted twin state (78 MB).** Either add the LFS pattern `outputs/twin/*_reemitted_*/twins.jsonl` and commit it,
   or keep it out of git and rely on the documented deterministic regeneration (`python -m cosmos.ai.twin.reemit`, sha
   `6bb4871f…`); the launch guide already documents the fallback behaviour when it is absent.

## 3. Proposed commits (in order; show staged files before each)

**Commit A — demonstration interface and documentation (Phases B–C).**
`cosmos/product/**` (api, store, css, 13 templates incl. new `demo.html`), `docs/product/CONSOLE_LAUNCH.md`,
`DEMONSTRATION_PROTOCOL.md`, `DEMO_SCRIPT.md`, `KNOWN_LIMITATIONS.md`, `README.md`, `scripts/rehearse_demo.py`,
`scripts/verify_protected_artifacts.py`, `tests/test_phase_b_console.py`, `tests/test_e2e_demo_journey.py`,
`tests/test_figures.py`, `outputs/product/screens/*`, `docs/research/COSMOS_AI_FINAL_COMPLETION_AUDIT.md`,
`COSMOS_AI_DEMONSTRATION_REPORT.md`, `COSMOS_AI_PROJECT_COMPLETION_TRACKER.md`, the Phase B/C audit records under
`outputs/audit/`.
Message: `Complete the Mission Intelligence Console demonstration: readiness panel, policies, errors, run comparison, guided demo`

**Commit B — scientific validation (Phase D).**
`paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md`, `paper/jint/COSMOS_AI_JINT_SUBMISSION_CHECKLIST.md`,
`scripts/audit_manuscript_claims.py`, `scripts/t1_ranking_utility.py`, `tests/test_t1_ranking_utility.py`,
`docs/research/T1_RANKING_UTILITY_PROTOCOL.md`, `T1_RANKING_UTILITY_RESULTS.md`, `outputs/t1_ranking_utility/*`,
`outputs/audit/manuscript_claim_audit_phase_*.json`, and — only after decision 1 — the re-issued
`paper/figures/RELEASE_MANIFEST.{json,md}` with the archived previous manifest.
Message: `Correct the nine audited manuscript claims; add the exploratory T1 ranking-utility evaluation`

**Commit C — manuscripts and thesis (Phase E).**
`paper/k7_lifetime_benchmark/COSMOS_AI_K7_LIFETIME_BENCHMARK_MANUSCRIPT.md`, `thesis/src/*.md` (two new chapters, seven
updated), `thesis/README.md`, `thesis/tools/render_draft_md.py`, `thesis/build/COSMOS_Thesis_2026-11-08_draft.md`.
Message: `Add the K7 benchmark manuscript draft and extend the thesis with the digital twin and console chapters`

**Commit D — final acceptance (Phase F).** `docs/research/COSMOS_AI_FINAL_ACCEPTANCE_REPORT.md`, the final audit and
performance records, this proposal. Message: `Final acceptance report and release proposal`

## 4. Proposed tag

`v1.0-demonstration-2026-11-08` on commit D, annotated with: suite result, the demonstration run id `run_20261108T121517Z`,
the claim-audit result, the protected-artifact verification record, and the statement that no live data or on-demand
inference is included. Tagging waits for approval; pushing the tag or any branch waits for a separate approval.

## 5. Reproducibility package (documented commands, all read-only except where stated)

```bash
cd /data2/anupa/Final_Year_Project
python scripts/verify_protected_artifacts.py --label release       # research artifacts and twin digests
python scripts/check_console_prerequisites.py                      # environment and required artifacts
python -m pytest tests/ -q                                         # full suite
python scripts/run_pipeline.py --as-of 2026-10-27 --health-calibrator conformal_bh   # writes one new run (≈ 9 s)
python scripts/twin_state_integrity.py --label release             # twin-state selection, integrity, equivalence
python scripts/audit_manuscript_claims.py                          # 147 manuscript checks
python scripts/benchmark_console.py --label release && python scripts/profile_console_cold.py --label release
python scripts/rehearse_demo.py --label release                    # thirteen-stage rehearsal (temporary root for the scenario)
python scripts/check_console_prerequisites.py && python scripts/serve_console.py    # the demonstration
```

Regenerating the re-emitted twin state when absent: `python -m cosmos.ai.twin.reemit` (deterministic, sha `6bb4871f…`).
Rebuilding the thesis DOCX/PDF needs the external toolchain (`thesis/README.md`).

## 6. What remains outside this release

Author-only fields in both manuscripts; the data DOI and licence; the thesis Word/PDF rebuild; prospective validation
(snapshot ≥ 2026-11-26); optional experiments X13 and X6 Stage 2; any GitHub push.

## 7. Release execution log (actual state; appended as each approved step completes)

**2026-11-08 — owner approval.** Decisions 1 and 2 approved with conditions; the four commits approved conditionally,
one at a time, each shown and individually approved; the tag only after all four are verified; no push.

**Decision 1 executed.** `paper/figures/RELEASE_MANIFEST.{json,md}` re-issued (107 entries, 105 unchanged, two changed
documents: the manuscript and `tests/test_figures.py`); the previous frozen manifest preserved byte-identically as
`RELEASE_MANIFEST_2026-11-06.{json,md}`; reason, previous-manifest digest and carried-forward reproducibility verdict recorded
in the new manifest's `reissue` block. Verifier record `outputs/audit/protected_artifacts_reissue_20261108T150616+0000.json`
(`figure_release_manifest {n: 107, bad: []}`). Scheduled for Commit B.

**Decision 2 executed.** `.gitattributes` gained the narrow pattern `outputs/twin/*_reemitted_*/twins.jsonl`; the 78 MB
re-emitted twin state is committed as an LFS pointer (oid `6bb4871f7ded…` = the recorded `TWINS_SHA256`, size 78,616,187);
the archived `outputs/twin/as_of_*/twins.jsonl` stays an ordinary Git object; scientific contents untouched. Git LFS is
documented as a prerequisite in `docs/product/CONSOLE_LAUNCH.md` §0 and `README.md`.

**Commit A created** — `aeefac2bd93244f98f7acb20fb88427bbbe34da8`, parent `938d514a9f91988e37b63d25475899632eb370d0`,
author and committer Anupa Sajikumar, no trailer, exactly the 54 presented files (38 modified, 16 added; +6,477/−530),
excluded sets absent, message as proposed.

**Fresh-clone LFS retrieval and twin-state integrity verification — PASSED**
(`outputs/audit/fresh_clone_lfs_verification_post_commit_a_20261108T153148+0000.json`). Clone of the local repository at
Commit A into an empty directory; `git lfs pull` over the local-path remote (standalone file agent) retrieved 831/831 LFS files
in 6 s; `git lfs fsck` OK. Re-emitted `twins.jsonl` in the clone: 78,616,187 bytes, 31,396 lines, SHA-256 `6bb4871f…` equal to
the recorded digest and to the source tree; archived `twins.jsonl` `19a1fede…` equal to `FORECAST_SHA256.txt`; LFS forecast
table `b15644aa…` equal to the source. The console, imported from the clone and rooted at the clone, selects the re-emitted state
as `primary` with `digest_state = verified` under `prefer_reemitted` and `reemitted_only`, and the archived state as
`explicit_archived` under `archived_only`; streaming validation 31,396/31,396 valid; `GET /api/twin-state` 200, `GET /api/ready`
200 (warning only: no complete pipeline run — run directories are deliberately not committed), `GET /twin-state` 200.

*Environment finding (not a repository defect):* the first checkout of the clone aborted because the global `~/.gitconfig`
points the LFS filter at `/data/anupa/COSMOS_work/.tools/bin/git-lfs`, which no longer exists; the source repository works only
because its own `.git/config` overrides the filter. `git lfs install --local` in the clone fixed it. The global configuration
was not changed; the documented prerequisite (`git lfs install` before cloning) already covers a fresh machine.

**Open issue found at Commit A — approved-head set is exact-match.** `APPROVED_HEADS` in `scripts/verify_protected_artifacts.py`
(used by the verifier's `head_ok` and by `tests/test_figures.py::test_manifest_git_state_is_consistent_with_git`) accepts only
`78ee339` and `938d514`. At HEAD `aeefac2` every content check passes (figure manifest 107/107 with the re-issued manifest in the
working tree, both twin digests, OPS-SAT, ESA-ADB, G5d), but `head_ok` is False and that one test fails
("HEAD aeefac2bd932 is neither the manifest's commit nor an approved checkpoint"; the other 38 figure tests pass). Each further
release commit would fail the same way, and the last commit can never contain its own hash. Recommended fix: accept HEAD when it
is an approved head **or a descendant of one** (`git merge-base --is-ancestor`), in both places; this is the test's own
"committed in a descendant" invariant and keeps the guard against unrelated branches. Owner's decision; the change touches two
files already in Commit A and would go into Commit B or a dedicated commit.

**Not yet done:** Commits B, C, D; post-commit verification; tag; update of the acceptance report §11 to the final state.

**Incident during documentation (2026-11-08 ≈ 19:00 UTC), resolved.** Running `python -m cosmos.ai.data.validate` to document
the dataset check rewrote `data/DATASET_REPORT.{json,md}` (only two `size_on_disk_mb` fields changed, a filesystem-dependent
quantity); `DATASET_REPORT.json` is hashed in the frozen figure release manifest, so the verifier flagged it
(`protected_artifacts_diagnose_20261108T190432+0000.json`, `all_protected_ok: False`). The committed files were restored with
`git checkout -- data/DATASET_REPORT.json data/DATASET_REPORT.md`; verifier `protected_artifacts_post_restore_dataset_report_20261108T190504+0000.json`
is green and the claim audit is unchanged (0 FAIL). The execution guide now states that the validator rewrites these files.

**Commit C created (2026-11-09 01:59 UTC)** — `66f0bc54da30094d5750bd93e877726aab2142f5`, parent `633ad862…`, author and committer
Anupa Sajikumar, no trailer, exactly the 20 presented files (+4,054/−24) with the owner-approved message. Pre-commit checks all
passed: the staged manifest matched the exact index contents of all 107 protected entries (one LFS pointer compared by oid);
verifier `head_ok: True`; the thesis Markdown draft regenerated byte-identically from its sources (1,072 keys, 0 unresolved);
author-only fields in both manuscripts and the thesis front matter remain placeholders (no DOI, licence or declaration invented);
no excluded outputs, no LFS files, no trailer. Post-commit: `tests/test_figures.py` + `tests/test_approved_head.py` 52 passed;
verifier `protected_artifacts_post_commit_c_20261109T015934+0000.json` `all_protected_ok: True`; untracked research outputs
preserved (41 before and after).

**Pushed to GitHub (2026-11-09 06:24 UTC, on the owner's explicit instruction).** Branch
`product/mission-intelligence-console` created on `origin` at `6cbc36e99f5bcdf714cef2fa24aeff686011f4d5`, carrying seven
commits (`938d514` checkpoint, release commits A–D, and the two visual-console commits `bfac16f` and `6cbc36e`). Git LFS
uploaded 10 objects, 86 MB, including the 78 MB re-emitted twin state. `main` and `q1-reentry-rebuild` were left untouched
at `78ee339`; no pull request was opened; **no tag was created** (the annotated tag still awaits the owner's approval).
Every pushed commit carries the owner's identity and no AI co-author trailer (verified across `78ee339..HEAD`).

**Remote fresh-clone retrieval verified (the check that was previously impossible).** A clone of
`https://github.com/AnuSajikumar6264/Cosmos-AI-.git` at that branch retrieved the twin state through `git lfs pull` in
11 s: 78,616,187 bytes, SHA-256 `6bb4871f7ded…`, equal to the recorded `TWINS_SHA256.txt`; 4,997 files checked out,
including the new visual console, the manuscripts, the thesis draft and the screenshot evidence. The clone's first
checkout aborted with `fatal: the remote end hung up unexpectedly` because the machine's global `~/.gitconfig` points the
LFS filter at a binary that no longer exists; `git lfs install --local` followed by `git checkout -f HEAD -- .` completed
it, which is exactly the remedy documented in `docs/product/CONSOLE_LAUNCH.md` §0 and the execution guide's
troubleshooting table.

**Thesis pushed to GitHub (2026-11-09, on the owner's explicit instruction).** Commit `dc3fc99811e9d699cd327a8e5eb747d83e7e74a0`
on `product/mission-intelligence-console`, parent `6cbc36e`, carries the complete M.Tech thesis in the Amrita `ugthesis`
format (`docs/thesis/final/`, 242 files, 18.9 MB, including the 257-page `build/main.pdf`), the rebuilt evidence file, the
ten recorded corrections, the submission checklist and the quality audit, together with the audit records under
`outputs/audit/`. Owner identity on author and committer, no AI co-author trailer; remote head verified equal to local
after the push. Still deliberately excluded as regenerable: `outputs/pipeline`, `outputs/run_20261103T155605Z`, the
`phase3_uncertainty` CSV copies and the console server log. No tag was created and no pull request was opened.

## 8. Release status — single source of truth

Statuses: **COMPLETED** · **COMPLETED WITH LIMITATIONS** · **BLOCKED** · **PENDING USER ACTION**. Inspected against the Git
repository on 2026-11-09 ≈ 02:00 UTC before this update: HEAD `66f0bc54da30094d5750bd93e877726aab2142f5` (release commit C)
← `633ad862…` (commit B) ← `aeefac2bd932…` (commit A) ← `938d514` (approved checkpoint) ← `78ee339` (public `main`); branch
`product/mission-intelligence-console`, no upstream; no tag; Commit D staged for approval; untracked: 89 regenerable pipeline runs,
`outputs/run_20261103T155605Z/`, 14 Phase 3 CSV copies.
Remote `origin` (read-only `git ls-remote`): `main` and `q1-reentry-rebuild` at `78ee339`; the LFS batch API reports the
re-emitted twin-state object `6bb4871f…` **absent** from GitHub (forecast-table object present). Earlier entries of this section
were replaced by this table; the chronological record is §7.

| # | Item | Status | Evidence / what remains |
|---|---|---|---|
| 1 | Decision 1 — figure release manifest re-issued, 2026-11-06 manifest preserved | COMPLETED | final generation 2026-11-08T18:43Z from a clean index at Commit B, 105/107 entries identical to the 2026-11-06 freeze; supersession chain of the same-day intermediate re-issues recorded in the `reissue` block; verifier `outputs/audit/protected_artifacts_post_commit_b_manifest_20261108T184316+0000.json` all green |
| 2 | Decision 2 — 78 MB re-emitted twin state in Git LFS (narrow pattern) | COMPLETED | pointer in Commit A (oid `6bb4871f…`, 78,616,187 B); archived twins.jsonl an ordinary object; documented in `CONSOLE_LAUNCH.md` §0 |
| 3 | Commit A | COMPLETED | `aeefac2bd93244f98f7acb20fb88427bbbe34da8`, 54 files, owner identity, no trailer |
| 4 | Fresh-clone LFS retrieval and twin-state integrity (local remote) | COMPLETED | 831/831 LFS files, fsck OK, sha identical, console reads it as primary/verified; `outputs/audit/fresh_clone_lfs_verification_post_commit_a_20261108T153148+0000.json` |
| 5 | Approved-head predicate (descendant semantics) with regression tests | COMPLETED | `scripts/verify_protected_artifacts.py::head_is_approved`, `tests/test_figures.py`, `tests/test_approved_head.py` (13 tests); in Commit B |
| 6 | Commit B | COMPLETED | `633ad862bf5d7fe2612bb01038aee309bd350a07`, 25 files, owner identity, no trailer; post-commit verifier `all_protected_ok: True` |
| 7 | JINT manuscript final pass | COMPLETED WITH LIMITATIONS | claim audit 147: 139 PASS / 8 NOT_EVALUABLE / 0 FAIL; 16 DOIs + 2 arXiv ids verified; author-only fields (authors, ORCIDs, contributions, funding, competing interests, AI-use disclosure, prior publication, data DOI, licence) and the venue decision remain the author's (checklist §1, §7) |
| 8 | K7 benchmark manuscript | COMPLETED WITH LIMITATIONS | re-verified against the raw archive (16 corrections listed in its Statements), §6.5 ablations and §8 discussion added, references completed from the verified matrix; author-only fields and a data DOI remain |
| 9 | M.Tech thesis sources and Markdown draft | COMPLETED WITH LIMITATIONS | 15 source chapters (18 mandated items covered), draft re-rendered 2026-11-08 with 1,072 evidence keys and 0 unresolved; DOCX/PDF rebuild BLOCKED by the absent toolchain (pandoc 3.11, pandoc-crossref, LibreOffice) — see item 17 |
| 10 | Console demonstration validation (fresh process) | COMPLETED | real server ready in ≈ 1.5 s, 32 routes 200 with correct content types, error paths correct; rehearsal 13/13; four objects verified; scenario via API 2.9 s; `docs/research/COSMOS_AI_FINAL_DEMONSTRATION_VALIDATION_REPORT.md` |
| 11 | Full test suite | COMPLETED | 508 passed, 3 skipped (optional artifacts: baseline snapshot, untrained learned monitor, untrained surrogate), 0 failed; `outputs/audit/pytest_full_20261108_post_commit_b.log` |
| 12 | Performance, both definitions | COMPLETED WITH LIMITATIONS | benchmark sequence: overview 180 ms cold / 37 warm, peak 225 MB (targets met); fresh process: import 534 ms, store steps + first overview ≈ 553 ms, peak 273 MB (targets 400 ms / 250 MB not met; unchanged from Phase F) |
| 13 | Execution documentation | COMPLETED | `docs/product/COSMOS_AI_COMPLETE_EXECUTION_GUIDE.md`, `docs/product/COSMOS_AI_QUICKSTART.md`, `docs/product/EVALUATOR_GUIDE.md`, `CONSOLE_LAUNCH.md` §0 clone/retrieval commands, README links; path and link check passed |
| 14 | Commit C (K7 manuscript, thesis sources and draft, evaluator guide, launch guide, README, the new guides, the regenerated manifest) | COMPLETED | `66f0bc54da30094d5750bd93e877726aab2142f5`, 20 files, owner identity, no trailer; six pre-commit checks passed (§7) |
| 15 | Commit D (acceptance report, this proposal, tracker, validation report, remaining audit and performance records) | PENDING USER ACTION | staged set presented for approval (2026-11-09); message `Final acceptance report, demonstration validation report and release records` |
| 16 | Annotated tag `v1.0-demonstration-2026-11-08` | PENDING USER ACTION | on the final commit; target and annotation shown before creation |
| 17 | Thesis DOCX/PDF | BLOCKED | external toolchain absent on this machine; exact rebuild commands in `thesis/README.md` |
| 18 | Push of branch, tag and LFS objects; remote fresh-clone retrieval test | PENDING USER ACTION | separate approval; until then the twin-state object exists only locally |
| 19 | Prospective (blind) validation | BLOCKED | needs a catalogue snapshot dated ≥ 2026-11-26 and download approval; console mode shows BLOCKED |
| 20 | Training-level reproducibility (2 of 7 learners refit) and X6 Stage 2 | BLOCKED | learner backends `kumo`, `tabm`, `tabicl`, `lightgbm`, `catboost` not installed; install needs approval |
| 21 | GitHub release notes and asset list | PENDING USER ACTION | prepared after the tag is created; publication needs push approval |
