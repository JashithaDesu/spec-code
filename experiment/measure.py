"""Compute the metrics for one task x condition from git tags (see PROTOCOL.md).

Usage:  python experiment/measure.py T1 A
Needs the tags start-T1-A, first-T1-A and done-T1-A. Prints the values to copy into log.csv.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files that count as written by the developer (or the AI) in each condition.
AUTHORED = {"A": ["src/logic"], "B": ["code_first"]}
SPEC_FILES = ["spec", "requirements"]
TARGET = {"A": "spec", "B": "codefirst"}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def changed_lines(start, end, paths):
    out = git("diff", "--numstat", start, end, "--", *paths)
    total = 0
    for line in out.splitlines():
        added, removed, _ = line.split("\t", 2)
        if added != "-":
            total += int(added) + int(removed)
    return total


def code_lines(tag, paths):
    files = [f for f in git("ls-tree", "-r", "--name-only", tag, "--", *paths).splitlines()
             if f.endswith(".py")]
    count = 0
    for f in files:
        for line in git("show", f"{tag}:{f}").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                count += 1
    return count


def run_tests(tag, target, test_path="tests"):
    """Check out the tag in a temporary worktree and run the acceptance tests there."""
    with tempfile.TemporaryDirectory() as tmp:
        worktree = Path(tmp) / "wt"
        git("worktree", "add", "--detach", str(worktree), tag)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-q", "-p", "no:cacheprovider"],
                cwd=worktree, capture_output=True, text=True,
                env={**__import__("os").environ, "TARGET": target})
        finally:
            git("worktree", "remove", "--force", str(worktree))
    out = result.stdout + result.stderr
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    failed = sum(int(m) for m in re.findall(r"(\d+) (?:failed|error)", out))
    return passed, failed


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in AUTHORED:
        print(__doc__)
        return 2
    task, cond = sys.argv[1], sys.argv[2]
    start, first, done = (f"{stage}-{task}-{cond}" for stage in ("start", "first", "done"))

    first_passed, first_failed = run_tests(first, TARGET[cond])
    done_passed, done_failed = run_tests(done, TARGET[cond])
    _, contract_failed = run_tests(done, TARGET[cond], "tests/test_contract.py")

    rows = {
        "first_run_passed": first_passed,
        "first_run_failed": first_failed,
        "done_passed": done_passed,
        "done_failed": done_failed,
        "rework_lines": changed_lines(first, done, AUTHORED[cond]),
        "hand_written_lines": code_lines(done, AUTHORED[cond]),
        "spec_lines_changed": changed_lines(start, done, SPEC_FILES),
        "contract_test": "pass" if contract_failed == 0 else "fail",
    }
    print(f"Metrics for {task}-{cond}:")
    for key, value in rows.items():
        print(f"  {key:20} {value}")
    print("\nCSV fields: " + ",".join(str(v) for v in rows.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
