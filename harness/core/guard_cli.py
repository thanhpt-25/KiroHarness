"""Combined guard entry point for every Agent.

Usage: ``python3 -I guard_cli.py <agent> <trigger>`` with the native hook payload
on standard input. The Agent's Adapter decodes the payload into a
Harness_Event, every guard for the trigger evaluates it, the Decisions are
combined (first deny, then first ask, then allow), and the Adapter encodes the
result in the Agent's native format (agent-harness-platform Requirements 4.2 to
4.7). Anything that prevents a decision applies the guard's failure semantics.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import DecodeError, get_adapter, MAX_INPUT_BYTES  # noqa: E402
from capabilities import CapabilityError  # noqa: E402
from event_model import TRIGGERS, combine  # noqa: E402
from guards import guards_for, run_guards  # noqa: E402
from hookio import workspace_root  # noqa: E402

NAME = "harness-guard"


def run(agent: str, trigger: str, raw: bytes, root=None):
    """Return ``(exit_code, stdout, stderr)`` for one hook invocation."""
    root = Path(root) if root else workspace_root()
    try:
        adapter = get_adapter(agent, root)
    except CapabilityError as exc:
        return 2, "", f"{NAME}: {exc}; blocking because the payload cannot be decoded safely\n"
    if trigger not in TRIGGERS or not guards_for(trigger):
        return 0, "", ""
    event, error = None, None
    try:
        event = adapter.decode(raw, trigger)
    except DecodeError as exc:
        error = str(exc)
    decisions = run_guards(trigger, event, error, root, adapter.failure)
    out = adapter.encode(combine(decisions), trigger)
    return out.exit_code, out.stdout, out.stderr


def main(argv, stdin, stdout, stderr) -> int:
    if len(argv) != 2:
        stderr.write(f"{NAME}: usage: guard_cli.py <agent> <trigger>\n")
        return 2
    raw = stdin.read(MAX_INPUT_BYTES + 1)
    code, out, err = run(argv[0], argv[1], raw)
    stdout.write(out)
    stderr.write(err)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdin.buffer, sys.stdout, sys.stderr))
