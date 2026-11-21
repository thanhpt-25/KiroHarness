"""Placeholder helpers: extraction, the README placeholder list, and the file scan."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]{0,63})\}\}")

_ITEM_RE = re.compile(
    r"^\s*[-*]\s+`\{\{([A-Z][A-Z0-9_]{0,63})\}\}`\s+—\s+(.*?)\s+—\s+(.*\S)\s*$"
)
_SKIP_DIRS = {".git", "node_modules", ".venv"}
_SNIFF_BYTES = 8192


@dataclass(frozen=True)
class PlaceholderDoc:
    name: str
    files: tuple  # workspace-relative POSIX paths named in the README item
    description: str
    line: int  # 1-based line number in the README


def find_placeholders(text: str) -> set:
    """Return the set of Placeholder names in ``text``."""
    return set(PLACEHOLDER_RE.findall(text))


def readme_placeholder_list(readme_text: str) -> dict:
    """Parse the ``## Placeholders`` section of the Template_README.

    Items have the form ``- `{{<NAME>}}` — <files> — <description>``, where
    ``<files>`` is a comma-separated list of paths, each optionally in backticks.
    """
    docs = {}
    in_section = False
    in_fence = False
    for number, line in enumerate(readme_text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^#{1,2}\s", stripped):
            in_section = re.match(r"^##\s+Placeholders\s*$", stripped) is not None
            continue
        if not in_section:
            continue
        match = _ITEM_RE.match(line)
        if not match:
            continue
        name, files_text, description = match.groups()
        files = tuple(
            part.strip().strip("`").strip()
            for part in files_text.split(",")
            if part.strip().strip("`").strip()
        )
        docs[name] = PlaceholderDoc(name, files, description, number)
    return docs


def _gitignore_rules(root: Path):
    path = root / ".gitignore"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    rules = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        if negate:
            line = line[1:]
        dir_only = line.endswith("/")
        line = line.rstrip("/")
        anchored = "/" in line
        line = line.lstrip("/")
        if line:
            rules.append((line, negate, dir_only, anchored))
    return rules


def _ignored(rel: str, is_dir: bool, rules) -> bool:
    ignored = False
    name = rel.rsplit("/", 1)[-1]
    for pattern, negate, dir_only, anchored in rules:
        if dir_only and not is_dir:
            continue
        target = rel if anchored else name
        if fnmatch.fnmatchcase(target, pattern):
            ignored = not negate
    return ignored


def is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if b"\x00" in data[:_SNIFF_BYTES]:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _git_files(root: Path):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    names = [n for n in result.stdout.decode("utf-8", "replace").split("\0") if n]
    return [root / n for n in names]


def _walk_files(root: Path):
    rules = _gitignore_rules(root)
    found = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        rel_dir = current_path.relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in _SKIP_DIRS and not _ignored(rel_dir + d, True, rules)
        )
        for name in sorted(files):
            if not _ignored(rel_dir + name, False, rules):
                found.append(current_path / name)
    return found


def tracked_text_files(root: Path):
    """Return ``(files, used_fallback)``.

    ``files`` lists the version-controlled text files under ``root`` (from
    ``git ls-files``), or, when git is unavailable or ``root`` is not a git
    repository, the files found by a filesystem walk that skips ``.git/``,
    ``node_modules/``, ``.venv/``, and ``.gitignore`` matches.
    """
    root = Path(root)
    files = _git_files(root)
    used_fallback = files is None
    if used_fallback:
        files = _walk_files(root)
    return [p for p in files if p.is_file() and is_text_file(p)], used_fallback
