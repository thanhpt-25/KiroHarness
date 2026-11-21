"""Protected-path matching and shell read detection (agent-harness-platform R11.1, R11.2, R11.5).

Pure functions over a parsed list; ``guards.py`` wraps them into the guard.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

NAME = "protected-path-guard"
DEFAULT_LIST = Path(__file__).resolve().parent.parent / "policy" / "protected-paths.txt"
READ_COMMANDS = frozenset({"cat", "less", "more", "head", "tail", "cp", "base64", "xxd", "source", ".", "tac", "nl", "od",
                           "strings", "hexdump", "grep", "awk", "sed"})
_SEGMENT_SPLIT = re.compile(r"[;&|\n`()]|\$\(")


class ProtectedListError(Exception):
    pass


@dataclass(frozen=True)
class Rule:
    text: str  # original line
    pattern: str
    negated: bool


def parse_list(text: str) -> list:
    rules = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:].strip() if negated else line
        if not pattern.strip("/"):
            raise ProtectedListError(f"line {line!r} has no pattern")
        rules.append(Rule(line, pattern, negated))
    if not rules:
        raise ProtectedListError("the list contains zero patterns")
    return rules


def load_list(path) -> list:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ProtectedListError(f"{path} not found") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise ProtectedListError(f"{path} could not be read ({exc})") from None
    try:
        return parse_list(text)
    except ProtectedListError as exc:
        raise ProtectedListError(f"{path}: {exc}") from None


def components(path: str) -> list:
    """Lowercase path segments with ``.`` removed and ``..`` resolved lexically."""
    out = []
    for part in path.replace("\\", "/").casefold().split("/"):
        if part in ("", "."):
            continue
        if part == ".." and out and out[-1] != "..":
            out.pop()
        else:
            out.append(part)
    return out


def _matches(rule: Rule, comps: list) -> bool:
    pattern = rule.pattern.casefold()
    dir_only = pattern.endswith("/")
    parts = [p for p in pattern.split("/") if p]
    if len(parts) == 1:
        targets = comps if dir_only else comps[-1:]
        return any(fnmatchcase(c, parts[0]) for c in targets)
    n = len(parts)
    return any(all(fnmatchcase(comps[i + j], parts[j]) for j in range(n)) for i in range(len(comps) - n + 1))


def protecting_rule(rules, path: str):
    """The last matching rule when it protects ``path``; None when the path is not protected."""
    comps = components(path)
    state = None
    for rule in rules:
        if _matches(rule, comps):
            state = None if rule.negated else rule
    return state


def _words(segment: str) -> list:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def shell_read_target(command: str, rules):
    """``(path, rule)`` for the first protected path a read command in ``command`` names; else None."""
    for segment in _SEGMENT_SPLIT.split(command):
        words = _words(segment)
        names = {w.rsplit("/", 1)[-1] for w in words}
        if not names & READ_COMMANDS:
            continue
        for word in words:
            for candidate in {word.lstrip("<>"), word.split("=", 1)[-1].lstrip("<>")}:
                if candidate and not candidate.startswith("-"):
                    rule = protecting_rule(rules, candidate)
                    if rule is not None:
                        return candidate, rule
    return None
