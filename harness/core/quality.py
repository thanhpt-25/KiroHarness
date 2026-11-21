"""Quality_Hook (PostFileSave): lint the saved file and run it when it is a test file."""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import HookInputError, read_hook_input, workspace_root  # noqa: E402
from runner import run_with_deadline, tail_lines  # noqa: E402

NAME = "quality-on-save"
DEADLINE_SECONDS = 110.0
COMMANDS_FILE = "scripts/project-commands.env"
CONF_FILE = Path(__file__).resolve().parent.parent.parent / ".kiro" / "hooks" / "scripts" / "quality-hook.conf"
DEFAULT_TEST_FILE_REGEX = r"(^|/)(test_[^/]+\.py|[^/]+_test\.go|[^/]+\.(test|spec)\.[jt]sx?)$"
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]{0,63}\}\}")
_LINE_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=(?:"(.*)"|(.*))\s*$')


def load_commands(path) -> dict:
    """Parse ``KEY="value"`` lines. The file is never sourced or expanded."""
    commands = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return commands
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if match:
            value = match.group(2) if match.group(2) is not None else (match.group(3) or "").strip()
            commands[match.group(1)] = value
    return commands


def is_configured(value) -> bool:
    """True when the value has a non-whitespace character and no unreplaced placeholder."""
    return (
        isinstance(value, str)
        and value.strip() != ""
        and _PLACEHOLDER_RE.search(value) is None
    )


def test_file_regex(path=CONF_FILE) -> "re.Pattern":
    for name, value in load_commands(path).items():
        if name == "TEST_FILE_REGEX" and value:
            try:
                return re.compile(value)
            except re.error:
                break
    return re.compile(DEFAULT_TEST_FILE_REGEX)


def saved_path(hook_input, root=None):
    """The saved file, workspace-relative when it lies inside the workspace."""
    raw = hook_input.raw
    tool_input = hook_input.tool_input
    files = raw.get("files")
    candidates = [
        raw.get("file_path"),
        raw.get("path"),
        tool_input.get("path"),
        tool_input.get("file_path"),
        files[0] if isinstance(files, list) and files else None,
    ]
    value = next((c for c in candidates if isinstance(c, str) and c.strip()), None)
    if value is None:
        return None
    path = Path(value)
    root = Path(root or workspace_root()).resolve()
    if path.is_absolute():
        try:
            return path.resolve().relative_to(root)
        except (ValueError, OSError):
            return path
    return path


def _emit(stdout, stderr, message: str, also_stderr: bool) -> None:
    stdout.write(message)
    if also_stderr:
        stderr.write(message)


def main(stdin, stdout, stderr, root=None, deadline_seconds: float = DEADLINE_SECONDS) -> int:
    root = Path(root or workspace_root())
    deadline = time.monotonic() + deadline_seconds
    try:
        hook_input = read_hook_input(stdin)
    except HookInputError as exc:
        stdout.write(f"{NAME}: hook input could not be parsed ({exc}); skipped\n")
        return 0
    path = saved_path(hook_input, root)
    if path is None:
        stdout.write(f"{NAME}: no saved file path in hook input; skipped\n")
        return 0
    path_text = path.as_posix()
    commands = load_commands(root / COMMANDS_FILE)
    env = dict(os.environ, CI="true")

    planned = [("lint", "LINT_FILE_COMMAND", "lint.sh")]
    if test_file_regex(root / ".kiro/hooks/scripts/quality-hook.conf").search(path_text):
        planned.append(("test", "TEST_FILE_COMMAND", "test.sh"))

    passed, failed = [], False
    for label, key, script in planned:
        if not is_configured(commands.get(key)):
            stdout.write(f"{NAME}: skipped {key}: not configured in {COMMANDS_FILE}\n")
            continue
        result = run_with_deadline(
            ["sh", str(root / "scripts" / script), path_text],
            deadline,
            env=env,
            cwd=str(root),
            name=label,
        )
        if result.timed_out:
            failed = True
            _emit(stdout, stderr, f"{NAME}: {label} ({key}) timed out after {int(deadline_seconds)}s for {path_text}\n", True)
        elif result.exit_code != 0:
            failed = True
            output = tail_lines(result.output, 200)
            if output and not output.endswith("\n"):
                output += "\n"
            _emit(
                stdout,
                stderr,
                f"{NAME}: {label} ({key}) failed (exit {result.exit_code}) for {path_text}\n{output}",
                True,
            )
        else:
            passed.append(f"{label} ({key})")
    if failed:
        return 1
    if passed:
        stdout.write(f"{NAME}: passed {', '.join(passed)} for {path_text}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.buffer, sys.stdout, sys.stderr))
