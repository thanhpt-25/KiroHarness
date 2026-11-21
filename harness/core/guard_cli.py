"""Combined guard entry point for every Agent.

Usage: ``python3 -I guard_cli.py <agent> <trigger> [--only <guard>,...]`` with the native hook payload
on standard input. The Agent's Adapter decodes the payload into a
Harness_Event, every guard for the trigger evaluates it, the Decisions are
combined (first deny, then first ask, then allow), and the Adapter encodes the
result in the Agent's native format (agent-harness-platform Requirements 4.2 to
4.7). Anything that prevents a decision applies the guard's failure semantics.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import DecodeError, get_adapter, MAX_INPUT_BYTES  # noqa: E402
from capabilities import CapabilityError  # noqa: E402
from event_model import TRIGGERS, combine  # noqa: E402
from guards import guards_for, run_guards  # noqa: E402
from hookio import workspace_root  # noqa: E402
import decision_log  # noqa: E402
from masking import mask_secrets  # noqa: E402
from prompt_scan import PatternLoadError, default_config_path, load_patterns  # noqa: E402

NAME = "harness-guard"


def _masked(stdout: str, stderr: str, root):
    """No matched secret value leaves the guard on stdout or stderr (R11.4)."""
    patterns = _patterns(root)
    if patterns is None:
        return stdout, stderr  # the prompt guard already denies when patterns are unusable
    return mask_secrets(stdout, patterns), mask_secrets(stderr, patterns)


def _patterns(root):
    try:
        return load_patterns(Path(root) / "scripts" / "validator-config.json")
    except PatternLoadError:
        return None


def run(agent: str, trigger: str, raw: bytes, root=None, only=None):
    """Return ``(exit_code, stdout, stderr)`` for one hook invocation."""
    root = Path(root) if root else workspace_root()
    try:
        adapter = get_adapter(agent, root)
    except CapabilityError as exc:
        return 2, "", f"{NAME}: {exc}; blocking because the payload cannot be decoded safely\n"
    if trigger not in TRIGGERS or not guards_for(trigger, only):
        return 0, "", ""
    event, error = None, None
    try:
        event = adapter.decode(raw, trigger)
    except DecodeError as exc:
        error = str(exc)
    decisions = run_guards(trigger, event, error, root, adapter.failure, only)
    out = adapter.encode(combine(decisions), trigger)
    stdout, stderr = _masked(out.stdout, out.stderr, root)
    patterns = _patterns(root)
    if patterns is not None:
        warn = io.StringIO()
        decision_log.record_decisions(root, event, decisions, patterns, warn)
        stderr += warn.getvalue()
    return out.exit_code, stdout, stderr


def main(argv, stdin, stdout, stderr) -> int:
    only = None
    if len(argv) == 4 and argv[2] == "--only":
        only = [name for name in argv[3].split(",") if name]
        argv = argv[:2]
    if len(argv) != 2:
        stderr.write(f"{NAME}: usage: guard_cli.py <agent> <trigger> [--only <guard>,<guard>]\n")
        return 2
    raw = stdin.read(MAX_INPUT_BYTES + 1)
    code, out, err = run(argv[0], argv[1], raw, only=only)
    stdout.write(out)
    stderr.write(err)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdin.buffer, sys.stdout, sys.stderr))
