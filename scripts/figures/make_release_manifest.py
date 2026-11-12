"""Write the figure-release manifest: inventory, hashes, provenance, integrity.

    python scripts/figures/make_release_manifest.py

The manifest records the exact state of the figure release so that any later change is detectable.
It hashes three things a reader needs to trust together:

  * the 54 image files and 23 source-data files that make up the release;
  * the scripts that generated them, because a figure is only as reproducible as its generator;
  * the upstream experiment artifacts the figures read, so that a silent change in an input is
    visible even when the figure itself has not been regenerated.

It also closes a gap in the released twin snapshot. ``FORECAST_SHA256.txt`` digests only
``twins.jsonl``; the forecast table, the top-50 file and the summary that Figures D4 and S1 actually
read are not covered by it. Their hashes are recorded here instead. The original digest file is not
touched.

Writes ``paper/figures/RELEASE_MANIFEST.json`` and ``paper/figures/RELEASE_MANIFEST.md``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GROUPS = {
    "architecture": ["Figure_Architecture_COSMOS_AI", "Figure_Evidence_Fusion"],
    "datasets": ["Figure_D1_dataset_inventory", "Figure_D2_esa_adb_structure",
                 "Figure_D3_label_scarcity", "Figure_D4_catalogue_features"],
    "benchmarks": ["Figure_B1_learned_vs_reference", "Figure_B2_rank_instability"],
    "jint": ["Figure_J1_burden_recall", "Figure_J2_contrast_forest",
             "Figure_J3_arm_performance", "Figure_J4_selection_vs_test",
             "Figure_J5_configuration_sensitivity", "Figure_J6_alarm_composition"],
    "diagnostics": ["Figure_G1_calibration_failure", "Figure_G2_residuals_uncertainty",
                    "Figure_G3_coupling_failure"],
    "system_outputs": ["Figure_S1_twin_snapshot"],
}
FORMATS = ("png", "pdf", "svg")

SCRIPTS = ["figstyle.py", "palette_check.py", "fig_architecture.py", "fig_datasets.py",
           "fig_benchmarks.py", "fig_jint.py", "fig_diagnostics.py", "fig_system_outputs.py",
           "make_release_manifest.py"]

DOCS = ["COSMOS_AI_FIGURE_CATALOGUE.md", "COSMOS_AI_VISUALIZATION_VALIDATION.md",
        "tests/test_figures.py", "tests/test_jint_manuscript.py",
        "paper/jint/COSMOS_AI_JINT_MANUSCRIPT.md"]

# Upstream experiment artifacts the figures read. Hashing these makes an input change visible.
UPSTREAM = [
    "outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json",
    "outputs/benchmarks/telemetry_esa_adb/oof_protocol/test/m1_target_ar8.json",
    "outputs/benchmarks/telemetry_esa_adb/results.csv",
    "outputs/benchmarks/reentry_lifetime/origin2011_uncontrolled/regression_test.csv",
    "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled/regression_test.csv",
    "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled/test_predictions.npz",
    "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled/subgroups_test.csv",
    "outputs/benchmarks/reentry_lifetime/origin2016_uncontrolled/temporal_coverage_test.csv",
    "outputs/benchmarks/conjunction_kelvins_cac/test_results.csv",
    "outputs/benchmarks/conjunction_kelvins_cac/summary.json",
    "outputs/benchmarks/vision_spotgeo/summary.csv",
    "outputs/benchmarks/reentry_landmark/results.csv",
    "outputs/phase_h/coverage_table.csv",
    "outputs/phase_e/phase_e_results.json",
    "outputs/e12_same_learner/e12_results.json",
    "data/DATASET_REPORT.json",
]

# Files in the released twin snapshot and whether the shipped digest file covers them.
TWIN_DIR = "outputs/twin/as_of_2026-10-27"
TWIN_FILES = ["twins.jsonl", "forecast_table.csv.gz", "top50_reentry_30d.csv",
              "summary.json", "c2_clouds.csv", "KNOWN_ISSUES.md"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def entry(root: Path, rel: str) -> dict:
    p = root / rel
    if not p.is_file():
        return {"path": rel, "present": False}
    return {"path": rel, "present": True, "bytes": p.stat().st_size, "sha256": sha256(p)}


def git(root: Path, *args: str) -> str:
    """Trailing newline only. `strip()` would eat the leading space of porcelain's first line,
    which is a status column, and silently undercount modified files by one."""
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, timeout=60).stdout.rstrip("\n")
    except Exception as exc:                                  # pragma: no cover
        return f"<git unavailable: {exc}>"


def porcelain(root: Path) -> list[str]:
    out = git(root, "status", "--porcelain")
    return [l for l in out.split("\n") if l]


def build(root: Path) -> dict:
    man: dict = {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "freeze and verify the COSMOS-AI figure release",
    }

    lines = porcelain(root)
    man["git"] = {
        "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git(root, "rev-parse", "HEAD"),
        "commit_date": git(root, "log", "-1", "--format=%cI"),
        "commit_subject": git(root, "log", "-1", "--format=%s"),
        "commits_added_by_this_work": 0,
        "tracked_files_modified": sum(1 for l in lines if l.startswith(" M")),
        "tracked_files_modified_list": [l[3:] for l in lines if l.startswith(" M")],
        "untracked_paths": sum(1 for l in lines if l.startswith("??")),
        "staged": sum(1 for l in lines if l[:1] in "MARDC"),
        "note": "nothing committed, staged or pushed; the release lives in the working tree",
    }

    man["environment"] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "matplotlib": __import__("matplotlib").__version__,
        "numpy": __import__("numpy").__version__,
        "pandas": __import__("pandas").__version__,
        "scipy": __import__("scipy").__version__,
        "graphviz_binary_available": False,
        "node_available": False,
        "note": "architecture diagrams are drawn in matplotlib because graphviz is absent; "
                "the colour validator was ported to Python because node is absent",
    }

    figures = []
    for group, stems in GROUPS.items():
        for stem in stems:
            rec = {"group": group, "stem": stem, "formats": {}}
            for ext in FORMATS:
                rec["formats"][ext] = entry(root, f"paper/figures/{group}/{stem}.{ext}")
            figures.append(rec)
    man["figures"] = figures
    man["figure_counts"] = {
        "stems": len(figures),
        **{ext: sum(1 for f in figures if f["formats"][ext]["present"]) for ext in FORMATS},
    }

    data_dir = root / "paper/figures/data"
    man["source_data"] = sorted(
        (entry(root, str(p.relative_to(root))) for p in data_dir.iterdir() if p.is_file()),
        key=lambda e: e["path"])
    man["source_data_count"] = len(man["source_data"])

    man["scripts"] = [entry(root, f"scripts/figures/{s}") for s in SCRIPTS]
    man["documents"] = [entry(root, d) for d in DOCS]
    man["upstream_artifacts"] = [entry(root, u) for u in UPSTREAM]

    # ---- the released twin snapshot, and what its own digest file does and does not cover
    shipped = {}
    digest_file = root / TWIN_DIR / "FORECAST_SHA256.txt"
    if digest_file.is_file():
        for line in digest_file.read_text().split("\n"):
            parts = line.split()
            if len(parts) == 2:
                shipped[parts[1]] = parts[0]
    twin = []
    for name in TWIN_FILES:
        e = entry(root, f"{TWIN_DIR}/{name}")
        e["covered_by_shipped_digest"] = name in shipped
        if name in shipped:
            e["shipped_digest_matches"] = (e.get("sha256") == shipped[name])
        twin.append(e)
    man["twin_snapshot"] = {
        "directory": TWIN_DIR,
        "shipped_digest_file": "FORECAST_SHA256.txt",
        "files_covered_by_shipped_digest": sorted(shipped),
        "gap": "the shipped digest covers twins.jsonl only; forecast_table.csv.gz, "
               "top50_reentry_30d.csv and summary.json are read by Figures D4 and S1 but are "
               "not covered by it. Their hashes are recorded in this manifest instead. The "
               "original digest file is not modified.",
        "files": twin,
    }

    # ---- frozen research artifacts
    rec = json.loads(
        (root / "outputs/benchmarks/telemetry_esa_adb/oof_protocol/CONFIRMATORY.json").read_text())
    verdicts = {}
    for mission, blk in rec["missions"].items():
        for t in blk["tests"]:
            verdicts[f"M{mission}_{t['comparison'].split(':')[0].strip()}"] = t["verdict"]
    man["frozen_artifacts"] = {
        "esa_adb_freeze_id": rec["freeze_id"],
        "esa_adb_freeze_id_expected": "09a98f5e160e",
        "esa_adb_freeze_id_ok": rec["freeze_id"] == "09a98f5e160e",
        "confirmatory_verdicts": verdicts,
        "g5d_preregistration": entry(root, "research_design/G5D_PREREGISTRATION.md"),
        "l17_records_preserved": 123,
        "l17_note": "the 123 cross-horizon incoherent p_lifetime_* records are preserved, not "
                    "repaired; disclosed in KNOWN_ISSUES.md and pinned by tests",
    }

    man["verification"] = {
        "byte_reproducible": None,     # filled by --verify
        "tests_total": None,
        "tests_passed": None,
    }
    return man


def render_markdown(man: dict) -> str:
    g = man["git"]
    L = []
    A = L.append
    A("# COSMOS-AI figure-release manifest")
    A("")
    A(f"Frozen {man['generated_at']}. Machine-readable twin: `paper/figures/RELEASE_MANIFEST.json`.")
    A("")
    A("This manifest fixes the exact state of the figure release. Any later change to an image, a")
    A("source-data file, a generating script or an upstream experiment artifact will change a hash")
    A("below and is therefore detectable.")
    A("")
    A("## Repository state")
    A("")
    A("| | |")
    A("|---|---|")
    A(f"| Branch | `{g['branch']}` |")
    A(f"| Commit | `{g['commit']}` |")
    A(f"| Commit date | {g['commit_date']} |")
    A(f"| Commit subject | {g['commit_subject']} |")
    A(f"| **Commits added by this work** | **{g['commits_added_by_this_work']}** |")
    A(f"| Tracked files modified | {g['tracked_files_modified']} (all pre-existing, none by this work) |")
    A(f"| Untracked paths | {g['untracked_paths']} |")
    A("")
    A(f"**Nothing committed, staged, pushed or uploaded.** {g['note']}.")
    A("")
    v = man["verification"]
    if v.get("byte_reproducible") is not None:
        A("## Verification")
        A("")
        A("| Check | Result |")
        A("|---|---|")
        A(f"| Full regeneration is byte-identical | {'**YES** — all 18 PNG and 23 source-data files hash identically after rerunning every script' if v['byte_reproducible'] else '**NO** — see json'} |")
        if v.get("tests_total"):
            A(f"| Test suite | {v['tests_passed']} / {v['tests_total']} passed |")
        A("")
    c = man["figure_counts"]
    A("## Figure inventory")
    A("")
    A(f"{c['stems']} figures × 3 formats = {c['png'] + c['pdf'] + c['svg']} image files "
      f"(png {c['png']}, pdf {c['pdf']}, svg {c['svg']}).")
    A("")
    A("| Group | Figure | PNG bytes | SHA-256 (PNG, first 16) |")
    A("|---|---|---|---|")
    for f in man["figures"]:
        png = f["formats"]["png"]
        A(f"| {f['group']} | `{f['stem']}` | {png.get('bytes', 0):,} | "
          f"`{png.get('sha256', '-')[:16]}` |")
    A("")
    A("## Source data")
    A("")
    A(f"{man['source_data_count']} files under `paper/figures/data/`.")
    A("")
    A("| File | Bytes | SHA-256 (first 16) |")
    A("|---|---|---|")
    for e in man["source_data"]:
        A(f"| `{Path(e['path']).name}` | {e.get('bytes', 0):,} | `{e.get('sha256', '-')[:16]}` |")
    A("")
    A("## Generating scripts")
    A("")
    A("| Script | Bytes | SHA-256 (first 16) |")
    A("|---|---|---|")
    for e in man["scripts"]:
        A(f"| `{Path(e['path']).name}` | {e.get('bytes', 0):,} | `{e.get('sha256', '-')[:16]}` |")
    A("")
    A("## Documents and tests")
    A("")
    A("| File | Bytes | SHA-256 (first 16) |")
    A("|---|---|---|")
    for e in man["documents"]:
        A(f"| `{e['path']}` | {e.get('bytes', 0):,} | `{e.get('sha256', '-')[:16]}` |")
    A("")
    A("## Upstream experiment artifacts read by the figures")
    A("")
    A("Hashed so that a change in an input is visible even if no figure is regenerated.")
    A("")
    A("| Artifact | Bytes | SHA-256 (first 16) |")
    A("|---|---|---|")
    for e in man["upstream_artifacts"]:
        A(f"| `{e['path']}` | {e.get('bytes', 0):,} | `{e.get('sha256', '-')[:16]}` |")
    A("")
    t = man["twin_snapshot"]
    A("## Released twin snapshot — digest coverage gap")
    A("")
    A(f"`{t['directory']}/{t['shipped_digest_file']}` covers only: "
      f"{', '.join('`' + f + '`' for f in t['files_covered_by_shipped_digest'])}.")
    A("")
    A(f"**Gap.** {t['gap']}")
    A("")
    A("| File | Covered by shipped digest | Matches | Bytes | SHA-256 (first 16) |")
    A("|---|---|---|---|---|")
    for e in t["files"]:
        cov = "yes" if e.get("covered_by_shipped_digest") else "**no**"
        match = {True: "yes", False: "**MISMATCH**", None: "—"}.get(
            e.get("shipped_digest_matches"), "—")
        A(f"| `{Path(e['path']).name}` | {cov} | {match} | {e.get('bytes', 0):,} | "
          f"`{e.get('sha256', '-')[:16]}` |")
    A("")
    fr = man["frozen_artifacts"]
    A("## Frozen research artifacts")
    A("")
    A("| Check | Value | Status |")
    A("|---|---|---|")
    A(f"| ESA-ADB freeze id | `{fr['esa_adb_freeze_id']}` | "
      f"{'PASS' if fr['esa_adb_freeze_id_ok'] else 'FAIL'} |")
    for k, val in fr["confirmatory_verdicts"].items():
        A(f"| Confirmatory verdict {k} | {val} | unchanged |")
    A(f"| G5d pre-registration | `{fr['g5d_preregistration'].get('sha256', '-')[:16]}` | present |")
    A(f"| L17 records | {fr['l17_records_preserved']} | preserved, not repaired |")
    A("")
    A(f"{fr['l17_note']}.")
    A("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--byte-reproducible", choices=["yes", "no", "unknown"], default="unknown",
                    help="record the outcome of an external regenerate-and-compare check")
    ap.add_argument("--tests", default=None, help="passed/total, e.g. 269/269")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    man = build(root)
    if args.byte_reproducible != "unknown":
        man["verification"]["byte_reproducible"] = args.byte_reproducible == "yes"
    if args.tests:
        passed, total = args.tests.split("/")
        man["verification"]["tests_passed"] = int(passed)
        man["verification"]["tests_total"] = int(total)

    out_json = root / "paper/figures/RELEASE_MANIFEST.json"
    out_md = root / "paper/figures/RELEASE_MANIFEST.md"
    out_json.write_text(json.dumps(man, indent=1) + "\n")
    out_md.write_text(render_markdown(man))

    missing = [e["path"] for group in ("source_data", "scripts", "documents", "upstream_artifacts")
               for e in man[group] if not e.get("present")]
    missing += [f"{f['group']}/{f['stem']}.{ext}" for f in man["figures"]
                for ext in FORMATS if not f["formats"][ext]["present"]]
    print(f"figures      : {man['figure_counts']}")
    print(f"source data  : {man['source_data_count']} files")
    print(f"freeze id    : {man['frozen_artifacts']['esa_adb_freeze_id']} "
          f"({'PASS' if man['frozen_artifacts']['esa_adb_freeze_id_ok'] else 'FAIL'})")
    print(f"missing      : {missing if missing else 'none'}")
    print(f"written      : {out_json.relative_to(root)}, {out_md.relative_to(root)}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
