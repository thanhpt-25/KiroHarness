"""Derive Claude Code ``permissions`` rules from the Policy_Files (agent-harness-platform R8.2).

Only entries with a static form become rules: a literal command prefix for the
shell tools, or an exact tool name. Everything else (host allowlists, regexes
that are not a list of literal prefixes) stays enforced by the hook alone and is
returned in ``skipped`` so the gap is visible, never silent.
"""

from __future__ import annotations

import os
import re
from fnmatch import fnmatchcase

LITERAL = re.compile(r"^[A-Za-z0-9_./:=~-]+( [A-Za-z0-9_./:=~-]+)*$")


def _lines(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#")]
    except FileNotFoundError:
        return []


def _expand(text: str) -> list:
    """Expand one level-nested ``(a|b)`` groups into alternatives; [] when not static."""
    start = text.find("(")
    if start < 0:
        return [text]
    depth, end = 0, None
    for index in range(start, len(text)):
        depth += (text[index] == "(") - (text[index] == ")")
        if depth == 0:
            end = index
            break
    if end is None:
        return []
    parts, level, current = [], 0, ""
    for char in text[start + 1 : end]:
        if char == "|" and level == 0:
            parts.append(current)
            current = ""
            continue
        level += (char == "(") - (char == ")")
        current += char
    parts.append(current)
    out = []
    for part in parts:
        for tail in _expand(text[end + 1 :]):
            for mid in _expand(part):
                out.append(text[:start] + mid + tail)
    return out


def static_prefixes(regex: str) -> list:
    """Literal command prefixes a policy regex always blocks or asks about; [] if none."""
    text = regex.strip()
    text = re.sub(r"^\(\?i\)", "", text)
    for lead in (r"(^|[;&|\s])", r"\b"):
        if text.startswith(lead):
            text = text[len(lead):]
            break
    for trail in (r"\b", r"\s"):
        if text.endswith(trail):
            text = text[: -len(trail)]
            break
    text = text.replace(r"\s+", " ").replace(r"\s", " ")
    alternatives = _expand(text)
    if not alternatives or not all(LITERAL.match(a) for a in alternatives):
        return []
    return alternatives


def derive(root, agent_entry, mcp: dict) -> dict:
    """Return ``{"allow": [...], "ask": [...], "deny": [...], "skipped": [...]}`` (sorted, unique)."""
    shell_tools = sorted(t for t, m in agent_entry["tool_map"].items() if m.get("category") == "shell")
    by_category: dict = {}
    for tool, mapping in agent_entry["tool_map"].items():
        by_category.setdefault(mapping.get("category"), []).append(tool)
    deny, ask, allow, skipped = set(), set(), set(), []
    for line in _lines(os.path.join(root, "harness/policy/destructive-commands.txt")):
        if LITERAL.match(line):
            deny.update(f"{tool}({line} *)" for tool in shell_tools)
        else:
            skipped.append(f"destructive-commands.txt: {line}")
    for line in _lines(os.path.join(root, "harness/policy/risky-tools.conf")):
        tool_col, reason, match = (part.strip() for part in line.split("|", 2))
        agent, _, name = tool_col.partition(":")
        if agent == "category":
            if match == "*":
                tools = by_category.get(name, [])
                ask.update(tools)
                if not tools:
                    skipped.append(f"risky-tools.conf: {tool_col} has no tool in this agent")
            elif match.startswith("regex ") and name == "shell":
                _kw, _field, regex = match.split(None, 2)
                prefixes = static_prefixes(regex)
                if prefixes:
                    ask.update(f"{tool}({p} *)" for p in prefixes for tool in shell_tools)
                else:
                    skipped.append(f"risky-tools.conf: {reason} (regex has no static prefix)")
            else:
                skipped.append(f"risky-tools.conf: {reason} ({match.split()[0]} has no permission rule)")
        elif agent == "claude-code" and match == "*":
            ask.add(name)
        elif ":" in tool_col and agent != "kiro":
            skipped.append(f"risky-tools.conf: {tool_col} is not a claude-code tool")
    protected = [l for l in _lines(os.path.join(root, "harness/policy/protected-paths.txt"))]
    negated = [l[1:].strip() for l in protected if l.startswith("!")]
    for line in protected:
        if line.startswith("!"):
            continue
        if any(fnmatchcase(n.casefold(), line.rstrip("/").casefold()) for n in negated):
            skipped.append(f"protected-paths.txt: {line} (a ! line re-includes some of its paths)")
            continue
        target = f"**/{line.rstrip('/')}/**" if line.endswith("/") else f"**/{line}"
        deny.update({f"Read({target})", f"Edit({target})"})
    for server, item in mcp.items():
        allow.update(f"mcp__{server}__{tool}" for tool in item["auto_approve"])
    return {"allow": sorted(allow), "ask": sorted(ask), "deny": sorted(deny), "skipped": skipped}
