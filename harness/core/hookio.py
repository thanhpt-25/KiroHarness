"""Hook input handling shared by every Hook_Script.

Kiro writes the hook context to standard input as JSON. Kiro IDE 1.x uses
snake_case fields (``tool_name``, ``tool_input``); Kiro 0.12 used
``toolName``/``toolArgs``. Both spellings are accepted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

MAX_INPUT_BYTES = 1_048_576


class HookInputError(Exception):
    """The hook input could not be parsed."""


@dataclass(frozen=True)
class HookInput:
    event: object = None  # hook_event_name
    cwd: Path = None  # payload cwd, else workspace root
    tool_name: object = None  # tool_name | toolName
    tool_input: dict = field(default_factory=dict)  # tool_input | toolArgs
    prompt: object = None
    raw: dict = field(default_factory=dict)


def workspace_root() -> Path:
    """The workspace root: the directory that contains ``harness/core/``."""
    return Path(__file__).resolve().parent.parent.parent


def _first_str(raw: dict, *keys):
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str):
            return value
    return None


def parse_hook_input(data: bytes) -> HookInput:
    if not data.strip():
        raise HookInputError("standard input is empty")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HookInputError(f"standard input is not valid UTF-8 (byte {exc.start})") from None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HookInputError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from None
    except RecursionError:
        raise HookInputError("JSON nesting is too deep") from None
    if not isinstance(raw, dict):
        raise HookInputError("top-level JSON value is not an object")

    tool_input = raw["tool_input"] if "tool_input" in raw else raw.get("toolArgs")
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, RecursionError):
            tool_input = {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    cwd_value = raw.get("cwd")
    cwd = Path(cwd_value) if isinstance(cwd_value, str) and cwd_value else workspace_root()
    return HookInput(
        event=raw.get("hook_event_name"),
        cwd=cwd,
        tool_name=_first_str(raw, "tool_name", "toolName"),
        tool_input=tool_input,
        prompt=raw.get("prompt") if isinstance(raw.get("prompt"), str) else None,
        raw=raw,
    )


def read_hook_input(stream, max_bytes: int = MAX_INPUT_BYTES) -> HookInput:
    """Read and parse hook input from a binary stream.

    Raises HookInputError on empty input, input over ``max_bytes``, invalid
    UTF-8, invalid JSON, or a top-level value that is not an object.
    """
    data = stream.read(max_bytes + 1)
    if isinstance(data, str):
        data = data.encode("utf-8", "surrogateescape")
    if len(data) > max_bytes:
        raise HookInputError(f"standard input is larger than {max_bytes} bytes")
    return parse_hook_input(data)
