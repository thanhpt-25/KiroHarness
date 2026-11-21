"""SessionStart hook: print the git branch and the number of uncommitted files.

Always exits 0. When git is missing, fails, or the directory is not a
repository, prints "Git information unavailable: <reason>".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import HookInputError, read_hook_input, workspace_root  # noqa: E402

GIT_TIMEOUT_SECONDS = 4


class GitUnavailable(Exception):
    pass


def _git(args, cwd) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        raise GitUnavailable("git command not found") from None
    except subprocess.TimeoutExpired:
        raise GitUnavailable(f"git {args[0]} timed out after {GIT_TIMEOUT_SECONDS}s") from None
    except OSError as exc:
        raise GitUnavailable(f"git could not run: {exc}") from None
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise GitUnavailable(detail[0] if detail else f"git {args[0]} exited {result.returncode}")
    return result.stdout.decode("utf-8", "replace")


def git_summary(cwd) -> str:
    try:
        status = _git(["status", "--porcelain=v1", "--untracked-files=all"], cwd)
        try:
            branch = _git(["symbolic-ref", "--short", "-q", "HEAD"], cwd).strip()
            branch_line = f"Git branch: {branch}"
        except GitUnavailable:
            sha = _git(["rev-parse", "--short", "HEAD"], cwd).strip()
            branch_line = f"Git branch: detached HEAD at {sha}"
    except GitUnavailable as exc:
        return f"Git information unavailable: {exc}\n"
    count = sum(1 for line in status.splitlines() if line.strip())
    return f"{branch_line}\nUncommitted files: {count}\n"


def _hook_cwd(stdin) -> Path:
    root = workspace_root()
    if stdin is None or stdin.isatty():
        return root
    try:
        hook_input = read_hook_input(stdin)
    except (HookInputError, OSError):
        return root
    cwd = hook_input.cwd
    return cwd if cwd and cwd.is_dir() else root


def main(stdin, stdout) -> int:
    try:
        stdout.write(git_summary(_hook_cwd(stdin)))
    except Exception as exc:  # informational hook: never fail the session
        stdout.write(f"Git information unavailable: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.buffer, sys.stdout))
