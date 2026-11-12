# COSMOS-AI — Demonstration readiness report (Phases B and C of the completion mandate, 2026-11-08)

Repository `/data2/anupa/Final_Year_Project`, HEAD `938d514` (approved checkpoint), working tree carrying the Phase B/C
changes listed in `COSMOS_AI_PROJECT_COMPLETION_TRACKER.md`. This report records what the evaluator will experience and
the evidence that each stage works on the real stored outputs. Nothing is live; nothing is inferred at request time.

## 1. Launch

```bash
cd /data2/anupa/Final_Year_Project
python scripts/check_console_prerequisites.py && python scripts/serve_console.py      # http://127.0.0.1:8070/  → /demo
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8070/api/ready               # 200
```

Readiness is one record (`_readiness`) served by `GET /api/ready` and rendered by the overview's System readiness panel.
Fresh-process import of the application takes about 0.55 s; the first overview about 0.45 s; the first Twin State page
about 1.5 s (archive streamed once, then cached). A navigation progress bar appears after 250 ms of waiting.

## 2. The thirteen stages (guided page `/demo`; presenter script `docs/product/DEMO_SCRIPT.md`)

| Stage | Screen | Evidence shown | Verified by |
|---|---|---|---|
| 1 Launch | `/api/ready` | artifacts present, digests verified, twin source primary | journey test 01, rehearsal |
| 2 Overview | `/` | readiness panel, latest run, nine module statuses, STALE finding, datasets strip | test 02, D-tests |
| 3 Selection | `/objects` | search by NORAD or name; the four objects with live rank and abstentions on `/demo` | test 03 |
| 4 Orbital intelligence | `/objects/37607`, `/objects/23806` | elements, lifetime interval (6.9–95.3 d, crosses horizon), subgroup cue, L17 abstention | tests 04–05, D4–D6 |
| 5 Re-entry | `/objects/37607`, `/objects/25544`, `/objects/12` | p(30 d) 1.0 before horizon; operator-controlled abstention with base rate; censored at cap | tests 04–05, D9 |
| 6 Health / telemetry | `/telemetry`, channel | anonymised missions, benchmark arms, methodology block; object page "not determinable" | test 06, D14 |
| 7 Collision | `/risk` | 2,167 events, quantiles, C4 abstention, methodology block | test 07 |
| 8 Debris | `/debris`, `/debris/1` | classical front end detections on real frames; benchmark table with the learned detectors marked "scores only" | test 08 |
| 9 Decision support | `/objects/37607`, ranking | rank 2 of 31,396, rule from the manifest, score 2.0, C4 abstain, horizon cue | test 09, D10 |
| 10 Twin state | `/twin-state`, policies | primary verified; 31,396 / 31,396 equal; not-compared reasons (16,386 · 16,386 · 123); archived read amber | test 10, D2–D3, P3-B suite |
| 11 Scenario | `/scenario` | presets, policy, validation, child-process execution, config digest, assumptions | test 11 (fixture root), `test_product` 05 |
| 12 Pipeline evidence | `/runs`, run page, `/compare`, report download | lineage per module, tables, value comparison, redacted report | test 12, D12 |
| 13 Summary | `/demo#stage-13` | established findings and what is outside the validated scope | test 13 |

## 3. Rehearsal (fresh process, `scripts/rehearse_demo.py --label phase_c_v2`, record `outputs/audit/demo_rehearsal_phase_c_v2_20261108T141652+0000.json`)

| Stage | Result | Latency | RSS after |
|---|---|---|---|
| 1 Launch and readiness | ok | 327 ms | 146 MB |
| 2 System overview | ok | 365 ms | 188 MB |
| 3 Satellite selection (incl. first `/demo` with twin-state summary) | ok | 1,690 ms | 243 MB |
| 4 Orbital intelligence (three object pages) | ok | 129 ms | 250 MB |
| 5 Re-entry prediction | ok | 52 ms | 250 MB |
| 6 Telemetry and channel page | ok | 1,231 ms | 243 MB (was 660 MB before the column cache) |
| 7 Collision | ok | 41 ms | 243 MB |
| 8 Debris, sequence, frame image | ok | 393 ms | 305 MB |
| 9 Decision support | ok | 55 ms | 323 MB |
| 10 Twin state (both policies) | ok | 1,231 ms | 312 MB |
| 11 Scenario, fast preset, temporary root, child process | ok | 4,398 ms | 312 MB (was 1,160 MB in-process) |
| 12 Pipeline evidence, compare, report | ok | 242 ms | 329 MB |
| 13 Final summary | ok | 91 ms | 329 MB |
| Total | all 13 ok | 10.2 s | end 329 MB |

HTML captures of the fourteen screens regenerated with `scripts/capture_console_screens.py` into `outputs/product/screens/`
(real server responses with inlined styles; no PNG screenshots: no headless browser is installed).

## 4. Automated evidence

| Suite | Result |
|---|---|
| `tests/test_e2e_demo_journey.py` | 15 passed |
| `tests/test_phase_b_console.py` | 22 passed |
| `tests/test_demo_workflow.py` D1–D14 | 14 passed |
| Related suites run together (product, observability, P3-B, wording, staleness, launch) | 113 passed |
| Full suite after Phase B/C | **492 passed, 3 skipped**, exit 0 (`outputs/audit/pytest_full_20261108_phase_b_v2.log`) |

## 5. Known limitations of the demonstration

* No PNG screenshots or visual regression (headless browser not installed; HTML captures instead).
* The first Twin State and the first telemetry channel view each take about 1.2–1.5 s; subsequent views are cached.
* The scenario executes synchronously in a child process (≈ 4–9 s); the page shows a loading state, not progress.
* The demonstration objects' facts are read from the latest run `run_20261108T121517Z`; a different latest run would change ranks.
* Decision-support effectiveness against outcomes is not demonstrated because no outcome window has been scored (Phase D).
* The protected-artifact verifier reports `tests/test_figures.py` as changed against the frozen figure release manifest: the
  test's git-state invariant had to become commit-aware after the approved checkpoint. Re-issuing the release manifest
  needs the owner's approval; the manuscript corrections of Phase D will require the same re-issue.
