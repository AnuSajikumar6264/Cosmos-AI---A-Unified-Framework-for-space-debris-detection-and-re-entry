"""Regression tests for the approved-head predicate of ``scripts/verify_protected_artifacts.py``.

Owner-approved correction (2026-11-08): the protected-artifact verifier and the figure-release git-state test accept
HEAD when it *is* an approved checkpoint or *descends* from one (``git merge-base --is-ancestor``), because the
release commits are approved one at a time and a commit can never carry its own hash. The predicate must keep
rejecting unrelated branches, orphan commits and unknown or malformed references, and the content checks must keep
rejecting modified protected artifacts and wrong hashes. The scratch-repository tests below exercise the predicate
without touching the project repository.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.phase8_acceptance_gate import HEAD_AT_DIRECTIVE, sha, verify_hashes
from scripts.verify_protected_artifacts import APPROVED_HEADS, ROOT, head_is_approved


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture()
def scratch_repo(tmp_path: Path) -> dict[str, object]:
    """A tiny repository: A -> B -> C on main, an unrelated orphan commit D, and an approved set {A}."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True,
                                    env={**__import__("os").environ, **env}).stdout.strip()
    run("init", "-q", "-b", "main")
    hashes = []
    for name in ("A", "B", "C"):
        (repo / f"{name}.txt").write_text(name)
        run("add", f"{name}.txt")
        run("commit", "-q", "-m", name)
        hashes.append(run("rev-parse", "HEAD"))
    run("checkout", "-q", "--orphan", "unrelated")
    run("rm", "-rfq", ".")
    (repo / "D.txt").write_text("D")
    run("add", "D.txt")
    run("commit", "-q", "-m", "D")
    orphan = run("rev-parse", "HEAD")
    run("checkout", "-q", "main")
    return {"repo": repo, "A": hashes[0], "B": hashes[1], "C": hashes[2], "D": orphan}


def test_approved_checkpoint_is_accepted_as_itself(scratch_repo):
    r = scratch_repo
    assert head_is_approved(r["A"], {r["A"]}, r["repo"]) == (True, r["A"])


def test_descendants_of_an_approved_checkpoint_are_accepted(scratch_repo):
    r = scratch_repo
    for h in (r["B"], r["C"]):
        ok, base = head_is_approved(h, {r["A"]}, r["repo"])
        assert ok and base == r["A"], h


def test_ancestor_of_the_approved_checkpoint_is_rejected(scratch_repo):
    r = scratch_repo
    # B is approved; A is its parent, not its descendant
    assert head_is_approved(r["A"], {r["B"]}, r["repo"]) == (False, None)


def test_unrelated_orphan_commit_is_rejected(scratch_repo):
    r = scratch_repo
    assert head_is_approved(r["D"], {r["A"], r["B"]}, r["repo"]) == (False, None)


@pytest.mark.parametrize("bad", ["", "not-a-ref", "HEAD", "0" * 40, "deadbeef", "abc"])
def test_unknown_or_malformed_references_are_rejected(scratch_repo, bad):
    r = scratch_repo
    assert head_is_approved(bad, {r["A"]}, r["repo"]) == (False, None)


def test_project_head_descends_from_an_approved_checkpoint():
    head = _git(ROOT, "rev-parse", "HEAD")
    ok, base = head_is_approved(head)
    assert ok, f"HEAD {head[:12]} is neither an approved checkpoint nor a descendant of one"
    assert base in APPROVED_HEADS
    assert subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", base, head]).returncode == 0


def test_project_commit_before_the_directive_start_is_rejected():
    parent = _git(ROOT, "rev-parse", f"{HEAD_AT_DIRECTIVE}^")
    assert head_is_approved(parent) == (False, None)


def test_content_checks_still_reject_modified_artifacts_and_wrong_hashes(tmp_path):
    """The predicate relaxation must not touch the hash checks: a changed file or a wrong digest is still reported."""
    f = tmp_path / "artifact.bin"
    f.write_bytes(b"protected")
    good = sha(f)
    n, bad = verify_hashes([(str(f), good)])
    assert (n, bad) == (1, [])
    f.write_bytes(b"protected-but-modified")
    assert verify_hashes([(str(f), good)]) == (1, [str(f)])
    assert verify_hashes([(str(f), "0" * 64)]) == (1, [str(f)])
    assert verify_hashes([(str(tmp_path / "missing.bin"), good)]) == (1, [str(tmp_path / "missing.bin")])
