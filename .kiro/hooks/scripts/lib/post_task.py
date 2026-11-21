"""PostTaskExec hook: run the whole test suite once after a spec task finishes."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import workspace_root  # noqa: E402
from quality import COMMANDS_FILE, is_configured, load_commands  # noqa: E402
from runner import run_with_deadline, tail_lines  # noqa: E402

NAME = "post-task-tests"
DEADLINE_SECONDS = 290.0


def main(stdout, stderr, root=None, deadline_seconds: float = DEADLINE_SECONDS) -> int:
    root = Path(root or workspace_root())
    commands = load_commands(root / COMMANDS_FILE)
    if not is_configured(commands.get("TEST_COMMAND")):
        stdout.write(f"{NAME}: skipped: TEST_COMMAND not configured in {COMMANDS_FILE}\n")
        return 0
    result = run_with_deadline(
        ["sh", str(root / "scripts" / "test.sh")],
        time.monotonic() + deadline_seconds,
        env=dict(os.environ, CI="true"),
        cwd=str(root),
        name="test",
    )
    output = tail_lines(result.output, 200)
    if output and not output.endswith("\n"):
        output += "\n"
    if result.timed_out:
        stderr.write(f"{NAME}: TEST_COMMAND timed out after {int(deadline_seconds)}s\n{output}")
        return 2
    if result.exit_code != 0:
        stderr.write(f"{NAME}: TEST_COMMAND failed (exit {result.exit_code})\n{output}")
        return 2
    stdout.write(f"{NAME}: passed TEST_COMMAND\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdout, sys.stderr))
