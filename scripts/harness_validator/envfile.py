"""Parsing for the Env_Example_File (``.env.example``)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_ASSIGN_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


@dataclass
class EnvVar:
    name: str
    lines: list = field(default_factory=list)  # 1-based line numbers, one per occurrence
    comments: list = field(default_factory=list)  # comment lines directly above any occurrence
    values: list = field(default_factory=list)


@dataclass
class EnvExample:
    variables: dict = field(default_factory=dict)  # name -> EnvVar

    def __contains__(self, name) -> bool:
        return name in self.variables


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def parse_env_example(text: str) -> EnvExample:
    """Return each variable with its line numbers and the comment lines directly above it."""
    result = EnvExample()
    pending_comments = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if line.startswith("#"):
            pending_comments.append(line.lstrip("#").strip())
            continue
        if not line:
            pending_comments = []
            continue
        match = _ASSIGN_RE.match(raw)
        if not match:
            pending_comments = []
            continue
        name, value = match.group(1), match.group(2)
        var = result.variables.setdefault(name, EnvVar(name))
        var.lines.append(number)
        var.comments.extend(pending_comments)
        var.values.append(_unquote(value))
        pending_comments = []
    return result
