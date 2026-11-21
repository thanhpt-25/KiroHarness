"""Adapters: decode native hook payloads to Harness_Events and encode Decisions.

Kiro and Claude Code both send JSON on stdin with ``tool_name``/``tool_input``,
so one table-driven Adapter serves both; the per-Agent differences (tool IDs,
payload field names for the command, path, and URL, and the output contract)
come from harness/capabilities.json (Requirements 4.2 and 4.3).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from capabilities import agent_entry, classify, load_capabilities  # noqa: E402
from event_model import Decision, HarnessEvent  # noqa: E402
from hookio import HookInputError, parse_hook_input  # noqa: E402

MAX_INPUT_BYTES = 1_048_576
FAILURE_KIND = {"destructive-command-guard": "deny", "prompt-secret-scan": "deny", "protected-path-guard": "deny"}


class DecodeError(Exception):
    pass


@dataclass(frozen=True)
class Output:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def failure_kind(guard: str) -> str:
    """The Decision kind for a guard that cannot decide (Requirement 4.4): deny, except risky asks."""
    return FAILURE_KIND.get(guard, "ask")


def _string_field(tool_input: dict, key):
    value = tool_input.get(key) if isinstance(key, str) else None
    return value if isinstance(value, str) else None


class Adapter:
    def __init__(self, agent: str, entry: dict):
        self.agent = agent
        self.entry = entry
        self.event_names = {v: k for k, v in entry.get("events", {}).items()}

    # -- decode ----------------------------------------------------------
    def decode(self, raw: bytes, trigger: str) -> HarnessEvent:
        if len(raw) > MAX_INPUT_BYTES:
            raise DecodeError(f"{self.agent}: standard input is larger than {MAX_INPUT_BYTES} bytes")
        try:
            hook_input = parse_hook_input(raw)
        except HookInputError as exc:
            raise DecodeError(f"{self.agent}: {exc}") from None
        native = hook_input.event
        if isinstance(native, str) and native in self.event_names and self.event_names[native] != trigger:
            raise DecodeError(f"{self.agent}: payload is for {native}, expected {self.entry['events'].get(trigger, trigger)}")
        category, mapping = classify(self.entry, hook_input.tool_name)
        tool_input = hook_input.tool_input
        paths = tuple(p for p in (_string_field(tool_input, f) for f in mapping.get("paths", [])) if p)
        return HarnessEvent(
            agent=self.agent,
            trigger=trigger,
            tool_id=hook_input.tool_name,
            category=category,
            command=_string_field(tool_input, mapping.get("command")),
            paths=paths,
            url=_string_field(tool_input, mapping.get("url")),
            prompt=hook_input.prompt,
            tool_input=tool_input,
            cwd=str(hook_input.cwd) if hook_input.cwd else None,
        )

    # -- encode ----------------------------------------------------------
    def encode(self, decision: Decision, trigger: str) -> Output:
        spec = self.entry["output"]
        if decision.kind == "allow":
            return Output(0)
        message = decision.reason if decision.reason.startswith(decision.guard) else f"{decision.guard}: {decision.reason}"
        if decision.kind == "deny":
            return Output(spec["deny"]["exit"], "", message + "\n")
        payload = {}
        if spec["ask"].get("include_event_name"):
            payload["hookEventName"] = self.entry["events"].get(trigger, trigger)
        payload["permissionDecision"] = "ask"
        payload["permissionDecisionReason"] = decision.reason
        text = json.dumps({"hookSpecificOutput": payload}, ensure_ascii=False, separators=(",", ":"))
        return Output(spec["ask"]["exit"], text + "\n", decision.stderr)

    def failure(self, guard: str, message: str) -> Decision:
        return Decision(failure_kind(guard), guard, message, None, message if failure_kind(guard) == "ask" else "")

    # -- native payload builder (tests, evals, fixtures) -----------------
    def build_native_payload(self, event: HarnessEvent) -> bytes:
        raw = {
            "hook_event_name": self.entry["events"].get(event.trigger, event.trigger),
            "cwd": event.cwd or "/WORKSPACE",
        }
        if event.tool_id is not None:
            raw["tool_name"] = event.tool_id
            raw["tool_input"] = event.tool_input
        if event.prompt is not None:
            raw["prompt"] = event.prompt
        return json.dumps(raw, ensure_ascii=False).encode("utf-8")


def get_adapter(agent: str, root=None) -> Adapter:
    """Build the Adapter for ``agent``. Raises CapabilityError if the matrix lacks it."""
    return Adapter(agent, agent_entry(load_capabilities(root), agent))
