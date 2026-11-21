"""Destructive_Command_Guard: blocks shell commands on the Destructive_Command_List.

Exit 2 blocks the tool call and the reason on standard error reaches the agent.
Exit 0 allows it. Every failure to load the list or read the input blocks.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import HookInputError, read_hook_input  # noqa: E402

NAME = "destructive-command-guard"
MAX_PATTERNS = 200
DEFAULT_LIST = Path(__file__).resolve().parent.parent / "policy" / "destructive-commands.txt"
_SEPARATORS = re.compile(r"&&|\|\||;|\||\n")
_EDGE_CHARS = "'\"`()"


@dataclass(frozen=True)
class Pattern:
    text: str  # original line, trimmed
    tokens: tuple  # normalized tokens


class ListLoadError(Exception):
    def __init__(self, path, reason: str):
        super().__init__(f"could not load list {path}: {reason}")
        self.path = path
        self.reason = reason


def normalize(command: str) -> str:
    """Casefold, collapse whitespace runs to one space, and trim."""
    return " ".join(command.casefold().split())


def split_segments(command: str) -> list:
    """Split on ``&&``, ``||``, ``;``, ``|``, and newlines. Quotes are ignored on purpose."""
    return _SEPARATORS.split(command)


def tokenize(segment: str) -> list:
    tokens = []
    for raw in normalize(segment).split(" "):
        token = raw
        while True:
            stripped = token.strip(_EDGE_CHARS)
            if stripped.startswith("$("):
                stripped = stripped[2:]
            if stripped == token:
                break
            token = stripped
        if token:
            tokens.append(token)
    return tokens


def load_patterns(path) -> list:
    """Read the list: one pattern per line, ``#`` comments and blank lines ignored."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ListLoadError(path, "file not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ListLoadError(path, f"file could not be read ({exc})") from None
    patterns = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = tuple(tokenize(stripped))
        if not tokens:
            continue
        patterns.append(Pattern(stripped, tokens))
    if not patterns:
        raise ListLoadError(path, "the list contains zero patterns")
    if len(patterns) > MAX_PATTERNS:
        raise ListLoadError(path, f"the list has {len(patterns)} patterns; the maximum is {MAX_PATTERNS}")
    return patterns


def match_segment(pattern: Pattern, segment) -> bool:
    """True when the pattern tokens occur in order within the segment tokens."""
    tokens = tokenize(segment) if isinstance(segment, str) else segment
    position = 0
    for token in tokens:
        if position < len(pattern.tokens) and token == pattern.tokens[position]:
            position += 1
            if position == len(pattern.tokens):
                return True
    return False


def check(command: str, patterns) -> object:
    """Return the first matching Pattern, or None."""
    for segment in split_segments(command):
        tokens = tokenize(segment)
        if not tokens:
            continue
        for pattern in patterns:
            if match_segment(pattern, tokens):
                return pattern
    return None


def main(stdin, stderr, list_path=None) -> int:
    list_path = Path(list_path) if list_path else DEFAULT_LIST
    try:
        patterns = load_patterns(list_path)
    except ListLoadError as exc:
        stderr.write(f"{NAME}: {exc}\n")
        return 2
    try:
        hook_input = read_hook_input(stdin)
    except HookInputError as exc:
        stderr.write(f"{NAME}: hook input could not be parsed: {exc}\n")
        return 2
    tool_input = hook_input.tool_input
    if hook_input.tool_name == "control_bash_process" and tool_input.get("action") == "stop":
        return 0
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        stderr.write(f"{NAME}: command field is missing in hook input\n")
        return 2
    matched = check(command, patterns)
    if matched is not None:
        stderr.write(
            f'{NAME}: blocked: matched pattern "{matched.text}"; the command is on the '
            f"Destructive_Command_List ({list_path})\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin.buffer, sys.stderr))
