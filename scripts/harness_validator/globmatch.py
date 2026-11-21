"""Minimatch-style glob matching for File_Match_Patterns.

Rules: ``**/`` matches zero or more path segments, ``**`` alone matches
anything, ``*`` and ``?`` do not match ``/``, ``{a,b}`` expands alternatives
(nesting allowed), and ``[...]`` is a character class (``[!...]`` negates).
Paths are workspace-relative POSIX paths.
"""

from __future__ import annotations

import functools
import re


class GlobError(ValueError):
    pass


def _find_closing_brace(pattern: str, start: int) -> int:
    depth = 0
    i = start
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_alternatives(body: str) -> list:
    parts, depth, current, i = [], 0, [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            current.append(body[i : i + 2])
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts


def _translate(pattern: str) -> str:
    out = []
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "*":
            if pattern.startswith("**", i):
                at_segment_start = i == 0 or pattern[i - 1] == "/"
                j = i + 2
                if at_segment_start and j < n and pattern[j] == "/":
                    out.append("(?:[^/]*/)*")  # **/ : zero or more segments
                    i = j + 1
                    continue
                if at_segment_start and j == n:
                    out.append(".*")  # trailing ** : anything
                    i = j
                    continue
                out.append("[^/]*")  # ** inside a segment behaves like *
                i = j
                continue
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        elif ch == "{":
            close = _find_closing_brace(pattern, i)
            if close == -1:
                out.append(re.escape(ch))
                i += 1
                continue
            alternatives = _split_alternatives(pattern[i + 1 : close])
            if len(alternatives) < 2:
                out.append(re.escape(pattern[i : close + 1]))
            else:
                out.append("(?:" + "|".join(_translate(a) for a in alternatives) + ")")
            i = close + 1
        elif ch == "[":
            close = pattern.find("]", i + 2)
            if close == -1:
                out.append(re.escape(ch))
                i += 1
                continue
            body = pattern[i + 1 : close]
            negate = body.startswith(("!", "^"))
            if negate:
                body = body[1:]
            body = body.replace("\\", "\\\\").replace("/", "")
            out.append(("[^/" if negate else "[") + body + "]")
            i = close + 1
        elif ch == "\\" and i + 1 < n:
            out.append(re.escape(pattern[i + 1]))
            i += 2
        else:
            out.append(re.escape(ch))
            i += 1
    return "".join(out)


@functools.lru_cache(maxsize=256)
def compile_glob(pattern: str) -> "re.Pattern":
    try:
        return re.compile(r"\A" + _translate(pattern) + r"\Z", re.DOTALL)
    except re.error as exc:
        raise GlobError(f"invalid glob {pattern!r}: {exc}") from None


def glob_match(pattern: str, path: str) -> bool:
    """Return True when the workspace-relative POSIX ``path`` matches ``pattern``."""
    path = path.replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    return compile_glob(pattern).match(path) is not None


def match_any(patterns, path: str) -> bool:
    if isinstance(patterns, str):
        patterns = [patterns]
    return any(glob_match(p, path) for p in patterns)
