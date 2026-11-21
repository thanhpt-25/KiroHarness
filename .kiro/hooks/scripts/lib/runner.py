"""Run a child process with a deadline and kill its whole process group on timeout."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass

KILL_GRACE_SECONDS = 2.0


@dataclass(frozen=True)
class RunResult:
    name: str
    exit_code: object  # int, or None when timed out
    output: str  # combined stdout and stderr
    timed_out: bool


def _signal_group(proc, sig) -> None:
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def run_with_deadline(argv, deadline: float, env=None, cwd=None, name=None) -> RunResult:
    """Run ``argv`` until it exits or ``time.monotonic()`` reaches ``deadline``.

    On the deadline the process group gets SIGTERM, then SIGKILL after 2 seconds.
    """
    name = name or str(argv[0])
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=cwd,
            start_new_session=True,
        )
    except OSError as exc:
        return RunResult(name, 127, f"could not start {argv[0]}: {exc}\n", False)
    remaining = max(0.0, deadline - time.monotonic())
    try:
        out, _ = proc.communicate(timeout=remaining)
        return RunResult(name, proc.returncode, out.decode("utf-8", "replace"), False)
    except subprocess.TimeoutExpired:
        pass
    _signal_group(proc, signal.SIGTERM)
    try:
        out, _ = proc.communicate(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        _signal_group(proc, signal.SIGKILL)
        out, _ = proc.communicate()
    _signal_group(proc, signal.SIGKILL)  # stray children that ignored SIGTERM
    return RunResult(name, None, (out or b"").decode("utf-8", "replace"), True)


_LINE_RE = re.compile(r"[^\n]*\n|[^\n]+\Z")


def tail_lines(text: str, n: int = 200) -> str:
    """Return the last ``n`` lines of ``text`` unchanged (``\\n`` or ``\\r\\n`` endings)."""
    if n <= 0:
        return ""
    lines = _LINE_RE.findall(text)
    return "".join(lines[-n:])
