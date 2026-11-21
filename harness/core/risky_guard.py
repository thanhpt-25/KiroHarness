"""Risky_Tool_Guard: asks the user before tool calls on the Risky_Tool_List.

Always exits 0. A match, unusable input, or an unusable list produces a
``permissionDecision`` of ``"ask"`` on standard output.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import HookInputError, read_hook_input  # noqa: E402

NAME = "risky-tool-guard"
DEFAULT_LIST = Path(__file__).resolve().parent.parent / "policy" / "risky-tools.conf"
_SPLIT_RE = re.compile(r"\s+\|\s+")


class Match:
    """Base class for the argument condition of a Risky_Tool_List entry."""


@dataclass(frozen=True)
class AnyArgs(Match):
    pass


@dataclass(frozen=True)
class RegexArg(Match):
    field: str  # dotted path into tool_input
    regex: "re.Pattern"


@dataclass(frozen=True)
class HostNotIn(Match):
    field: str
    hosts: frozenset  # lowercase; a host matches itself and its subdomains


@dataclass(frozen=True)
class RiskyEntry:
    tool: str
    reason: str
    match: Match
    line: str  # original line, reported in permissionDecisionReason
    line_no: int


class RiskyListError(Exception):
    def __init__(self, line_no, detail: str):
        prefix = f"line {line_no}: " if line_no else ""
        super().__init__(prefix + detail)
        self.line_no = line_no
        self.detail = detail


def _parse_match(text: str, line_no: int) -> Match:
    if text == "*":
        return AnyArgs()
    kind, _, rest = text.partition(" ")
    rest = rest.strip()
    if kind == "regex":
        field, _, regex = rest.partition(" ")
        regex = regex.strip()
        if not field or not regex:
            raise RiskyListError(line_no, "regex match needs '<field> <python-regex>'")
        try:
            return RegexArg(field, re.compile(regex))
        except re.error as exc:
            raise RiskyListError(line_no, f"regex does not compile: {exc}") from None
    if kind == "host-not-in":
        parts = rest.split()
        if len(parts) < 2:
            raise RiskyListError(line_no, "host-not-in match needs '<field> <host> [<host> ...]'")
        return HostNotIn(parts[0], frozenset(h.lower().rstrip(".") for h in parts[1:]))
    raise RiskyListError(line_no, f"unknown match {text!r}; use *, regex <field> <regex>, or host-not-in <field> <hosts>")


def parse_list(text: str) -> list:
    """Parse ``<tool> | <reason> | <match>`` lines. Raise RiskyListError with the line number."""
    entries = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = _SPLIT_RE.split(line, maxsplit=2)
        if len(parts) != 3 or not all(p.strip() for p in parts):
            raise RiskyListError(line_no, "expected '<tool> | <reason> | <match>'")
        tool, reason, match_text = (p.strip() for p in parts)
        if any(c.isspace() for c in tool):
            raise RiskyListError(line_no, f"tool name {tool!r} must not contain spaces")
        entries.append(RiskyEntry(tool, reason, _parse_match(match_text, line_no), line, line_no))
    if not entries:
        raise RiskyListError(None, "the list contains zero entries")
    return entries


def load_list(path) -> list:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RiskyListError(None, "file not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise RiskyListError(None, f"file could not be read ({exc})") from None
    return parse_list(text)


_MISSING = object()


def _lookup(tool_input: dict, field: str):
    value = tool_input
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def host_allowed(url, hosts) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url.strip())
        host = parts.hostname
    except ValueError:
        return False
    if parts.scheme.lower() not in ("http", "https") or not host:
        return False
    host = host.rstrip(".")
    return any(host == h or host.endswith("." + h) for h in hosts)


def matches(entry: RiskyEntry, tool_name: str, tool_input: dict) -> bool:
    if entry.tool != tool_name:
        return False
    condition = entry.match
    if isinstance(condition, AnyArgs):
        return True
    value = _lookup(tool_input, condition.field)
    if isinstance(condition, RegexArg):
        if value is _MISSING:
            return False
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return condition.regex.search(text) is not None
    if isinstance(condition, HostNotIn):
        return not host_allowed(None if value is _MISSING else value, condition.hosts)
    return False


def decide(entries, tool_name: str, tool_input: dict):
    for entry in entries:
        if matches(entry, tool_name, tool_input):
            return entry
    return None


def ask_json(reason: str) -> str:
    return json.dumps(
        {"hookSpecificOutput": {"permissionDecision": "ask", "permissionDecisionReason": reason}},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def main(stdin, stdout, stderr, list_path=None) -> int:
    list_path = Path(list_path) if list_path else DEFAULT_LIST
    try:
        entries = load_list(list_path)
    except RiskyListError as exc:
        stdout.write(ask_json(f"risky-tool-guard config problem: {list_path}: {exc}") + "\n")
        stderr.write(f"{NAME}: {list_path}: {exc}\n")
        return 0
    try:
        hook_input = read_hook_input(stdin)
        if not hook_input.tool_name:
            raise HookInputError("no tool name field (tool_name or toolName)")
    except HookInputError as exc:
        stdout.write(ask_json(f"hook input could not be parsed: {exc}") + "\n")
        stderr.write(f"{NAME}: parse error: {exc}\n")
        return 0
    entry = decide(entries, hook_input.tool_name, hook_input.tool_input)
    if entry is not None:
        reason = (
            f'Risky tool call: {entry.tool} matched Risky_Tool_List entry "{entry.line}" ({entry.reason})'
        )
        stdout.write(ask_json(reason) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.buffer, sys.stdout, sys.stderr))
