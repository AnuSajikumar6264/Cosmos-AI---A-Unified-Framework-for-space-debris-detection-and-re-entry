"""Phase 8 — technical acceptance gate for COSMOS-AI (directive C), run 2026-11-06.

    python scripts/phase8_acceptance_gate.py [--skip-tests]

The gate asks one question: has every feasible technical and scientific phase been completed and
recorded honestly, with frozen artifacts untouched, so that writing may begin? It verifies — it does
not assert — the following, and writes `outputs/audit/phase8_acceptance_gate.json` and
`docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md`:

  integrity   every frozen / archived artifact hashes to its recorded value (ESA-ADB freeze, G5d
              pre-registration, figure release, OPS-SAT archive, twin state, dated forecast)
  git         HEAD unchanged since the directive began, nothing staged, no commits made
  writing     manuscript and thesis files untouched (reference artifacts)
  tests       the whole suite, run now, with zero failures
  tracker     every Phase 0-7 row carries a terminal status; residual IN PROGRESS / NOT STARTED /
              VALIDATION PENDING rows are gate blockers; BLOCKED / NOT EVALUABLE / awaiting-approval
              rows are limitations and are listed
  audit       the latest Phase N system audit verdict and its failures

Verdict: PASS WITH LIMITATIONS when integrity, git, writing and tests all pass and no blocker rows
remain; otherwise FAIL with the blockers named. Nothing is modified except the two outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD_AT_DIRECTIVE = "78ee33962007203bcfc829fc743a663b350373e1"
FORECAST_TABLE_SHA = "b15644aab581cd05f2046a36574c2d522f53d83f55aca618f233c01ad194af86"
DIRECTIVE_C_DAY = datetime(2026, 11, 6, tzinfo=timezone.utc)
TRACKER = ROOT / "docs/research/MASTER_COMPLETION_TRACKER.md"
BLOCKER_WORDS = ("NOT STARTED", "IN PROGRESS", "VALIDATION PENDING")
LIMIT_WORDS = ("BLOCKED", "NOT EVALUABLE", "awaiting approval", "requires approval", "needs approval", "requested")
APPROVAL_ITEMS = [
    ("X3", "ESA-ADB 3b Stage 1 — 2x2 re-selection (F4 x F5), new output dir", "minutes CPU"),
    ("X4", "ESA-ADB 3b Stage 2 — 12 AR(8) OOF fits", "3-4 h"),
    ("X6", "lifetime am_design Stage 2 missingness ablation (design-time)", "per protocol doc"),
    ("X10", "OPS-SAT E6 branch ablation (decides K8)", "hours of training, 5 seeds x branches"),
    ("X13", "ESA-ADB input-perturbation robustness — re-exposes the pre-registered test half", "minutes-hour CPU"),
    ("twin-state", "regenerate twins.jsonl with the current engine into a NEW directory (provenance + forecast reproduction check)", "~1,250 s"),
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Gate:
    def __init__(self):
        self.checks: list[dict] = []

    def add(self, group: str, check: str, status: str, detail: str, measured=None):
        self.checks.append({"group": group, "check": check, "status": status, "detail": detail, "measured": measured})
        mark = {"PASS": "ok  ", "FAIL": "FAIL", "INFO": "info", "LIMIT": "lim "}[status]
        print(f"  {mark} [{group:9s}] {check}: {detail}")


def verify_hashes(entries: list[tuple[str, str]]) -> tuple[int, list[str]]:
    bad = []
    for rel, want in entries:
        p = ROOT / rel
        if not p.is_file() or sha(p) != want:
            bad.append(rel)
    return len(entries), bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-tests", action="store_true")
    a = ap.parse_args(argv)
    g = Gate()
    print("Phase 8 — technical acceptance gate\n")

    # ------------------------------------------------------------------ integrity
    fz = json.loads((ROOT / "research_design/preregistration/freeze.json").read_text())
    n, bad = verify_hashes(list(fz["sha256"].items()))
    g.add("integrity", "ESA-ADB pre-registration freeze", "PASS" if not bad else "FAIL",
          f"{n - len(bad)}/{n} frozen files hash-identical (freeze_id {fz['freeze_id']})", {"bad": bad})
    conf = json.loads((ROOT / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json").read_text())
    # The confirmatory numbers were computed under the ORIGINAL freeze 09a98f5e160e; the freeze was
    # re-issued (681cc7ddec86) after section 9 of the pre-registration was filled from DEVIATIONS.md,
    # so exactly one file — the pre-registration document — is expected to differ from the original.
    fz0 = json.loads((ROOT / f"research_design/preregistration/freeze_{conf['freeze_id']}.json").read_text())
    n0, bad0 = verify_hashes(list(fz0["sha256"].items()))
    expected_diff = {fz0["document"]}
    g.add("integrity", "original confirmatory freeze", "PASS" if set(bad0) == expected_diff else "FAIL",
          f"freeze {conf['freeze_id']} (CONFIRMATORY.json): {n0 - len(bad0)}/{n0} files identical; differing: {sorted(bad0)} "
          f"(expected only the pre-registration document, whose section 9 was filled in afterwards — DEVIATIONS.md 2026-10-24 22:00)",
          {"differing": bad0})
    g5 = json.loads((ROOT / "outputs/g5d_origin2006/prereg_freeze.json").read_text())
    ok = sha(ROOT / g5["preregistration"]) == g5["sha256"]
    g.add("integrity", "G5d pre-registration", "PASS" if ok else "FAIL", f"{g5['preregistration']} hash {'matches' if ok else 'DIFFERS'}")
    man = json.loads((ROOT / "paper/figures/RELEASE_MANIFEST.json").read_text())
    entries = [(f["formats"][k]["path"], f["formats"][k]["sha256"]) for f in man["figures"] for k in f["formats"]]
    entries += [(s["path"], s["sha256"]) for key in ("source_data", "scripts", "documents", "upstream_artifacts") for s in man[key] if s.get("present")]
    n, bad = verify_hashes(entries)
    g.add("integrity", "figure release manifest", "PASS" if not bad else "FAIL",
          f"{n - len(bad)}/{n} files (figures, source data, scripts, documents, upstream artifacts) unchanged", {"bad": bad})
    opssat = ROOT / "outputs/benchmarks/telemetry_opssat"
    lines = [ln.split() for ln in (ROOT / "outputs/audit/opssat_historical_sha256.txt").read_text().splitlines() if ln.strip()]
    n, bad = verify_hashes([(str((opssat / name).relative_to(ROOT)), h) for h, name in lines])
    g.add("integrity", "OPS-SAT historical archive", "PASS" if not bad else "FAIL", f"{n - len(bad)}/{n} archived files unchanged", {"bad": bad})
    twin = ROOT / "outputs/twin/as_of_2026-10-27"
    rec = (twin / "FORECAST_SHA256.txt").read_text().split()[0]
    ok_twins = sha(twin / "twins.jsonl") == rec
    ok_table = sha(twin / "forecast_table.csv.gz") == FORECAST_TABLE_SHA
    g.add("integrity", "dated twin state and forecast", "PASS" if ok_twins and ok_table else "FAIL",
          f"twins.jsonl {'=' if ok_twins else '!='} recorded digest; forecast_table {'=' if ok_table else '!='} run-manifest digest")

    # ------------------------------------------------------------------ git
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    staged = [l for l in subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True).stdout.splitlines() if l]
    porcelain = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True, check=True).stdout.splitlines()
    modified = [l for l in porcelain if l[:2].strip() and not l.startswith("??")]
    untracked = [l for l in porcelain if l.startswith("??")]
    g.add("git", "HEAD unchanged, nothing committed", "PASS" if head == HEAD_AT_DIRECTIVE else "FAIL", f"HEAD {head[:12]} (directive start {HEAD_AT_DIRECTIVE[:12]})")
    g.add("git", "nothing staged", "PASS" if not staged else "FAIL", f"{len(staged)} staged paths", staged[:10])
    g.add("git", "working tree", "INFO", f"{len(modified)} modified tracked files, {len(untracked)} untracked paths — all uncommitted by instruction")

    # ------------------------------------------------------------------ writing preserved
    jint = next(d for d in man["documents"] if d["path"].endswith("COSMOS_AI_JINT_MANUSCRIPT.md"))
    ok = sha(ROOT / jint["path"]) == jint["sha256"]
    g.add("writing", "JINT manuscript untouched", "PASS" if ok else "FAIL", f"{jint['path']} {'=' if ok else '!='} release-manifest hash")
    touched = []
    for p in list((ROOT / "paper").rglob("*manuscript*")) + list((ROOT / "paper").rglob("*thesis*")) + list((ROOT / "docs").rglob("*thesis*")):
        if p.is_file() and datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) >= DIRECTIVE_C_DAY:
            touched.append(str(p.relative_to(ROOT)))
    g.add("writing", "no manuscript/thesis file modified since the directive day", "PASS" if not touched else "FAIL",
          f"{len(touched)} files modified on/after {DIRECTIVE_C_DAY.date()}", touched)

    # ------------------------------------------------------------------ tests
    tests = {"ran": False}
    if not a.skip_tests:
        run = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
        tail = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
        m = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|skipped|error|errors)", tail)}
        tests = {"ran": True, "summary": tail, "passed": m.get("passed", 0), "failed": m.get("failed", 0) + m.get("error", 0) + m.get("errors", 0),
                 "skipped": m.get("skipped", 0), "returncode": run.returncode}
        g.add("tests", "full suite", "PASS" if tests["failed"] == 0 and run.returncode == 0 else "FAIL", tail)
    else:
        g.add("tests", "full suite", "INFO", "skipped by flag")

    # ------------------------------------------------------------------ tracker residuals
    text = TRACKER.read_text()
    part_b = text.split("## Part B")[1].split("## Part C")[0]
    phase, blockers, limits, rows = None, [], [], 0
    for line in part_b.splitlines():
        h = re.match(r"^### Phase (\d)", line)
        if h:
            phase = int(h.group(1))
            continue
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= {"-", " "} or phase is None or phase > 7:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("Task", "Subsystem / task"):
            continue
        rows += 1
        status = cells[1]
        # report the bold status tokens of the cell, not a mid-sentence truncation of its evidence text
        tokens = " / ".join(re.findall(r"\*\*(.+?)\*\*", status)) or status
        if any(w in status for w in BLOCKER_WORDS):
            blockers.append({"phase": phase, "row": cells[0], "status": tokens})
        elif any(w.lower() in status.lower() for w in LIMIT_WORDS) or any(w.lower() in " ".join(cells[2:]).lower() for w in ("awaiting approval", "requires approval", "needs approval")):
            limits.append({"phase": phase, "row": cells[0], "status": tokens})
    g.add("tracker", "Phase 0-7 rows with a non-terminal status", "PASS" if not blockers else "FAIL",
          f"{len(blockers)} of {rows} rows still IN PROGRESS / NOT STARTED / VALIDATION PENDING", blockers)
    g.add("tracker", "rows limited by data, approval or external dependency", "LIMIT", f"{len(limits)} rows", limits)
    for xid, what, cost in APPROVAL_ITEMS:
        g.add("approval", xid, "LIMIT", f"{what} — cost {cost} — NOT RUN, awaiting explicit approval")

    # ------------------------------------------------------------------ Phase N audit
    audits = sorted((ROOT / "outputs/final_audit").glob("*.json"), key=lambda p: p.stat().st_mtime)
    audit = {}
    if audits:
        rec_ = json.loads(audits[-1].read_text())
        finds = rec_.get("findings", rec_.get("checks", []))
        fails = [f for f in finds if f.get("status") == "FAIL"]
        audit = {"file": str(audits[-1].relative_to(ROOT)), "verdict": rec_.get("verdict"), "n": len(finds),
                 "fails": [{"check": f.get("check"), "severity": f.get("severity"), "measured": f.get("measured"), "expected": f.get("expected")} for f in fails]}
        g.add("audit", "latest Phase N system audit", "INFO", f"{rec_.get('verdict')}: {len(finds) - len(fails)} PASS, {len(fails)} FAIL "
              f"({'; '.join(str(f.get('check')) for f in fails)})")

    # ------------------------------------------------------------------ verdict
    hard = [c for c in g.checks if c["status"] == "FAIL"]
    verdict = "FAIL" if hard else "PASS WITH LIMITATIONS"
    out = {"gate": "Phase 8 technical acceptance", "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "verdict": verdict, "hard_failures": hard, "checks": g.checks, "tests": tests, "phase_n_audit": audit,
           "head": head, "approval_items": [{"id": i, "what": w, "cost": c} for i, w, c in APPROVAL_ITEMS],
           "writing_phase": "LOCKED until this gate reads PASS or PASS WITH LIMITATIONS and the user confirms"}
    (ROOT / "outputs/audit/phase8_acceptance_gate.json").write_text(json.dumps(out, indent=1, default=str) + "\n")

    md = [f"# Phase 8 — Technical acceptance gate\n", f"Evaluated {out['evaluated_at']} at HEAD `{head[:12]}` by `scripts/phase8_acceptance_gate.py`. ",
          "Machine record: `outputs/audit/phase8_acceptance_gate.json`. Nothing was modified by the gate.\n",
          f"## Verdict: **{verdict}**\n"]
    if hard:
        md.append("Hard failures:\n" + "\n".join(f"- [{c['group']}] {c['check']}: {c['detail']}" for c in hard) + "\n")
    md.append("## Checks\n\n| Group | Check | Status | Detail |\n|---|---|---|---|")
    for c in g.checks:
        if c["group"] in ("approval",):
            continue
        md.append(f"| {c['group']} | {c['check']} | **{c['status']}** | {c['detail'].replace('|', '/')} |")
    md.append("\n## Limitations carried into the writing phase\n")
    md.append("Rows in the completion tracker whose status is BLOCKED, NOT EVALUABLE or awaiting approval (Phases 0-7):\n")
    md += [f"- Phase {l['phase']}: {l['row']} — {l['status']}" for l in limits]
    md.append("\n## Experiments not run — awaiting explicit approval\n\n| Id | What | Cost |\n|---|---|---|")
    md += [f"| {i} | {w} | {c} |" for i, w, c in APPROVAL_ITEMS]
    if tests.get("ran"):
        md.append(f"\n## Test suite\n\n`{tests['summary']}` (return code {tests['returncode']}).\n")
    if audit:
        md.append(f"## Phase N system audit\n\n`{audit['file']}`: verdict {audit['verdict']}; failures: " +
                  ("; ".join(f"{f['check']} (measured {f['measured']}, expected {f['expected']})" for f in audit["fails"]) or "none") + "\n")
    md.append("## What the gate means\n\nPASS WITH LIMITATIONS: every frozen artifact verifies, no code was committed, the manuscript and thesis files "
              "are untouched, the full suite passes, and every Phase 0-7 row has reached a terminal status. The limitations above are data, "
              "approval or external-dependency boundaries recorded in the tracker; they are to be *stated* in the writing, not resolved by it. "
              "Phase 9 (writing) remains locked until the user confirms this gate.\n")
    (ROOT / "docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md").write_text("\n".join(md))
    print(f"\n=== verdict: {verdict} ===  ({len(hard)} hard failures; {len(limits)} limitation rows; {len(APPROVAL_ITEMS)} approval items)")
    print("written outputs/audit/phase8_acceptance_gate.json, docs/research/PHASE8_TECHNICAL_ACCEPTANCE_GATE.md")
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
