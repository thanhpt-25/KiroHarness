"""Template rules for Hook_Files, layered on top of the Hook_Config_Parser.

A Hook_File that is not parseable JSON gets one HOOK-JSON finding and no other
checks. A file that parses but breaks the v1 schema gets one HOOK-SCHEMA
finding per violation; the Template rules still run on the parts of the file
whose types allow it, so every violation in the file is reported in one run.
"""

from __future__ import annotations

import re
import shlex
import stat
from pathlib import Path, PurePosixPath

from . import hookconfig
from .report import error, warning

HOOK_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
TIMEOUT_MIN, TIMEOUT_MAX = 1, 300


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def script_path_from_command(command: str):
    """Return the first token ending in ``.sh`` (after an optional ``sh``/``bash``)."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if tokens and tokens[0] in ("sh", "bash", "/bin/sh", "/bin/bash"):
        tokens = tokens[1:]
    for token in tokens:
        if token.endswith(".sh"):
            return token
    return None


def check_hook_id(path: str) -> list:
    stem = PurePosixPath(path).name
    if stem.endswith(".json"):
        stem = stem[: -len(".json")]
    if len(stem) > 64 or not HOOK_ID_RE.match(stem):
        return [
            error(
                path,
                "file name",
                "HOOK-ID",
                f"hook file id {stem!r} must be 1 to 64 characters of a-z and 0-9 "
                "with single dashes between them, not starting or ending with a dash",
            )
        ]
    return []


def check_hook_file(path: str, text, root: Path) -> list:
    """Return every finding for one Hook_File. ``text`` may be ``str`` or ``bytes``."""
    findings = check_hook_id(path)
    try:
        if isinstance(text, bytes):
            text = hookconfig.decode_utf8(text, path)
        obj = hookconfig.loads_strict(text, path)
    except hookconfig.HookParseError as exc:
        findings.append(
            error(path, f"line {exc.line}, column {exc.column}", "HOOK-JSON", f"not parseable JSON: {exc.detail}")
        )
        return findings
    try:
        hookconfig.hook_from_obj(obj, path)
    except hookconfig.HookSchemaError as exc:
        for field, message in exc.violations:
            findings.append(error(path, field, "HOOK-SCHEMA", message))
    if isinstance(obj, dict) and isinstance(obj.get("hooks"), list):
        findings.extend(_template_rules(path, obj["hooks"], root))
    return findings


def _template_rules(path, hooks, root) -> list:
    findings = []
    if not hooks:
        findings.append(error(path, "hooks", "HOOK-RULES", "hooks must contain at least 1 Hook_Definition"))
    seen_names = {}
    for index, item in enumerate(hooks):
        if not isinstance(item, dict):
            continue  # reported by the schema check
        prefix = f"hooks[{index}]"
        name = item.get("name")
        label = f'hook "{name}"' if isinstance(name, str) and name else f"hook at {prefix}"
        if isinstance(name, str) and name:
            if len(name) > NAME_MAX:
                findings.append(error(path, f"{prefix}.name", "HOOK-RULES", f"{label}: name must be at most {NAME_MAX} characters"))
            if name in seen_names:
                findings.append(
                    error(path, f"{prefix}.name", "HOOK-RULES", f"{label}: name duplicates hooks[{seen_names[name]}].name")
                )
            else:
                seen_names[name] = index

        action = item.get("action")
        action_type = action.get("type") if isinstance(action, dict) else None
        if action_type == "command":
            command = action.get("command")
            if not isinstance(command, str) or command.strip() == "":
                findings.append(
                    error(path, f"{prefix}.action.command", "HOOK-RULES", f"{label}: command action needs a non-empty command string")
                )
            else:
                findings.extend(_check_script(path, prefix, label, command, root))
            timeout = item.get("timeout")
            if not _is_int(timeout) or not TIMEOUT_MIN <= timeout <= TIMEOUT_MAX:
                findings.append(
                    error(
                        path,
                        f"{prefix}.timeout",
                        "HOOK-RULES",
                        f"{label}: timeout must be an integer from {TIMEOUT_MIN} to {TIMEOUT_MAX} seconds",
                    )
                )
        elif action_type == "agent":
            prompt = action.get("prompt")
            if not isinstance(prompt, str) or prompt.strip() == "":
                findings.append(
                    error(path, f"{prefix}.action.prompt", "HOOK-RULES", f"{label}: agent action needs a non-empty prompt string")
                )

        matcher = item.get("matcher")
        if isinstance(matcher, str) and matcher != "":
            try:
                re.compile(matcher)
            except re.error as exc:
                findings.append(
                    error(path, f"{prefix}.matcher", "HOOK-RULES", f"{label}: matcher is not a valid regular expression: {exc}")
                )
            if "*" in matcher or "?" in matcher:
                findings.append(
                    warning(
                        path,
                        f"{prefix}.matcher",
                        "HOOK-WILDCARD",
                        f"{label}: matcher contains '*' or '?', which Kiro may read as a wildcard pattern instead of a regex",
                    )
                )
    return findings


def _check_script(path, prefix, label, command, root: Path) -> list:
    script = script_path_from_command(command)
    if script is None:
        return []
    resolved = Path(script) if Path(script).is_absolute() else Path(root) / script
    field = f"{prefix}.action.command"
    if not resolved.is_file():
        return [error(path, field, "HOOK-SCRIPT", f"{label}: Hook_File {path} runs script {script}, which does not exist")]
    try:
        mode = resolved.stat().st_mode
    except OSError as exc:
        return [error(path, field, "HOOK-SCRIPT", f"{label}: Hook_File {path} runs script {script}, which cannot be read: {exc}")]
    if not mode & stat.S_IXUSR:
        return [
            error(
                path,
                field,
                "HOOK-SCRIPT",
                f"{label}: Hook_File {path} runs script {script}, which does not have the owner execute bit set",
            )
        ]
    return []
