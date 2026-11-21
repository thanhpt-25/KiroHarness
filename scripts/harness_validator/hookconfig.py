"""Hook_Config_Parser and Hook_Config_Printer for v1 Hook_Files.

The parser enforces exactly the v1 hook schema from Requirement 9.2. Rules that
only the Template applies (unique names, timeouts, regex matchers, file ids)
live in ``hook_rules.py``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

JSON = Any

TRIGGERS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreTaskExec",
    "PostTaskExec",
    "PreCompact",
    "PostCompact",
    "Stop",
    "PostFileCreate",
    "PostFileSave",
    "PostFileDelete",
)
MATCHER_REQUIRED = frozenset(
    {
        "PreToolUse",
        "PermissionRequest",
        "PostToolUse",
        "PostFileCreate",
        "PostFileSave",
        "PostFileDelete",
    }
)
ACTION_TYPES = ("command", "agent")

_TOP_KEYS = ("version", "hooks")
_DEF_KEYS = ("name", "trigger", "matcher", "action", "timeout", "description", "enabled")
_ACTION_KEYS = ("type", "command", "prompt")


@dataclass(frozen=True)
class HookAction:
    type: str
    command: JSON = None  # None means the key is absent
    prompt: JSON = None
    extra: tuple = ()  # ((key, value), ...) sorted by key


@dataclass(frozen=True)
class HookDefinition:
    name: str
    trigger: str
    matcher: Union[str, None]
    action: HookAction
    timeout: JSON = None
    description: JSON = None
    enabled: JSON = None
    extra: tuple = ()


@dataclass(frozen=True)
class HookFile:
    version: str
    hooks: tuple
    extra: tuple = ()  # unknown top-level keys, sorted by key


class HookError(Exception):
    """Base class for every Hook_Config_Parser error."""

    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


class HookReadError(HookError):
    """The Hook_File does not exist or cannot be read."""


class HookParseError(HookError):
    """The Hook_File is not valid UTF-8 JSON. ``line`` and ``column`` are 1-based."""

    def __init__(self, path: str, line: int, column: int, message: str):
        super().__init__(path, f"line {line}, column {column}: {message}")
        self.line = line
        self.column = column
        self.detail = message


class HookSchemaError(HookError):
    """The Hook_File is valid JSON but breaks the v1 schema.

    ``violations`` is a tuple of ``(field_path, message)`` pairs, one per violation.
    """

    def __init__(self, path: str, violations):
        self.violations = tuple(violations)
        text = "; ".join(f"{field}: {msg}" for field, msg in self.violations)
        super().__init__(path, f"v1 schema violations: {text}")


class _DuplicateKey(ValueError):
    def __init__(self, key: str):
        super().__init__(key)
        self.key = key


class _BadConstant(ValueError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


def _reject_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise _DuplicateKey(key)
        seen[key] = value
    return seen


def _reject_constant(name):
    raise _BadConstant(name)


def _position(text: str, index: int) -> tuple:
    index = max(0, min(index, len(text)))
    line = text.count("\n", 0, index) + 1
    column = index - (text.rfind("\n", 0, index) + 1) + 1
    return line, column


def _find_duplicate(text: str, key: str) -> int:
    pattern = re.compile(re.escape(json.dumps(key)) + r"\s*:")
    matches = list(pattern.finditer(text))
    if len(matches) >= 2:
        return matches[1].start()
    # The key may be written with escapes; fall back to the start of the file.
    return 0


def loads_strict(text: str, path: str):
    """Parse JSON text, rejecting duplicate keys and NaN/Infinity.

    Raises HookParseError with a 1-based line and column.
    """
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        return _raise_parse(path, exc.lineno, exc.colno, exc.msg)
    except _DuplicateKey as exc:
        line, col = _position(text, _find_duplicate(text, exc.key))
        return _raise_parse(path, line, col, f"duplicate key {json.dumps(exc.key)}")
    except _BadConstant as exc:
        index = text.find(exc.name)
        line, col = _position(text, index if index >= 0 else 0)
        return _raise_parse(path, line, col, f"{exc.name} is not valid JSON")
    except RecursionError:
        return _raise_parse(path, 1, 1, "JSON nesting is too deep")


def _raise_parse(path, line, col, msg):
    raise HookParseError(path, line, col, msg)


def decode_utf8(data: bytes, path: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        prefix = data[: exc.start]
        line = prefix.count(b"\n") + 1
        last_nl = prefix.rfind(b"\n")
        column = len(prefix[last_nl + 1 :].decode("utf-8", errors="replace")) + 1
        raise HookParseError(path, line, column, "file is not valid UTF-8") from None


def parse_hook_file(path) -> HookFile:
    """Read and parse a Hook_File from disk."""
    path_str = str(path)
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        reason = exc.strerror or exc.__class__.__name__
        raise HookReadError(path_str, f"file could not be read: {reason}") from None
    return parse_hook_bytes(data, path_str)


def parse_hook_bytes(data: bytes, path: str) -> HookFile:
    return parse_hook_text(decode_utf8(data, path), path)


def parse_hook_text(text: str, path: str) -> HookFile:
    """Parse Hook_File text. Raises HookParseError or HookSchemaError."""
    obj = loads_strict(text, path)
    return hook_from_obj(obj, path)


def _sorted_extra(obj: dict, known) -> tuple:
    return tuple(sorted((k, v) for k, v in obj.items() if k not in known))


def hook_from_obj(obj: JSON, path: str) -> HookFile:
    """Validate a decoded JSON value against the v1 schema and build a HookFile."""
    violations = []
    if not isinstance(obj, dict):
        raise HookSchemaError(path, [("$", "top-level value must be a JSON object")])

    version = obj.get("version")
    if "version" not in obj:
        violations.append(("version", 'is required and must be "v1"'))
    elif version != "v1":
        violations.append(("version", f'must be "v1", got {json.dumps(version)}'))

    hooks_value = obj.get("hooks")
    definitions = []
    if "hooks" not in obj:
        violations.append(("hooks", "is required and must be an array"))
    elif not isinstance(hooks_value, list):
        violations.append(("hooks", "must be an array"))
    else:
        for index, item in enumerate(hooks_value):
            definition = _definition(item, f"hooks[{index}]", violations)
            if definition is not None:
                definitions.append(definition)

    if violations:
        raise HookSchemaError(path, violations)
    return HookFile(
        version="v1",
        hooks=tuple(definitions),
        extra=_sorted_extra(obj, _TOP_KEYS),
    )


def _definition(item, prefix, violations):
    if not isinstance(item, dict):
        violations.append((prefix, "Hook_Definition must be a JSON object"))
        return None
    start = len(violations)

    name = item.get("name")
    if "name" not in item:
        violations.append((f"{prefix}.name", "is required"))
    elif not isinstance(name, str) or name == "":
        violations.append((f"{prefix}.name", "must be a non-empty string"))

    label = f'hook "{name}"' if isinstance(name, str) and name else f"hook at {prefix}"
    trigger = item.get("trigger")
    if "trigger" not in item:
        violations.append((f"{prefix}.trigger", f"{label}: trigger is required"))
    elif not isinstance(trigger, str) or trigger not in TRIGGERS:
        violations.append(
            (
                f"{prefix}.trigger",
                f"{label}: trigger {json.dumps(trigger)} must be one of {', '.join(TRIGGERS)}",
            )
        )

    has_matcher = "matcher" in item
    matcher = item.get("matcher")
    if isinstance(trigger, str) and trigger in MATCHER_REQUIRED:
        if not has_matcher:
            violations.append((f"{prefix}.matcher", f"is required for trigger {trigger}"))
        elif not isinstance(matcher, str) or matcher == "":
            violations.append(
                (f"{prefix}.matcher", f"must be a non-empty string for trigger {trigger}")
            )
    elif (
        isinstance(trigger, str)
        and trigger not in TRIGGERS
        and (not has_matcher or not isinstance(matcher, str) or matcher == "")
    ):
        # Keep independent schema findings visible together. The invalid trigger
        # prevents us from determining which matcher rule applies, but the
        # missing matcher remains a useful finding when the input was mutated
        # from a matcher-required trigger.
        violations.append(
            (f"{prefix}.matcher", "matcher is missing or empty while trigger is invalid")
        )
    elif has_matcher and not isinstance(matcher, str):
        violations.append((f"{prefix}.matcher", "must be a string when present"))

    action = None
    action_value = item.get("action")
    if "action" not in item:
        violations.append((f"{prefix}.action", "is required"))
    elif not isinstance(action_value, dict):
        violations.append((f"{prefix}.action", "must be a JSON object"))
    else:
        action_type = action_value.get("type")
        if action_type not in ACTION_TYPES:
            violations.append(
                (
                    f"{prefix}.action.type",
                    f'must be "command" or "agent", got {json.dumps(action_type)}',
                )
            )
        else:
            action = HookAction(
                type=action_type,
                command=action_value.get("command"),
                prompt=action_value.get("prompt"),
                extra=_sorted_extra(action_value, _ACTION_KEYS),
            )

    if len(violations) > start:
        return None
    return HookDefinition(
        name=name,
        trigger=trigger,
        matcher=matcher if has_matcher else None,
        action=action,
        timeout=item.get("timeout"),
        description=item.get("description"),
        enabled=item.get("enabled"),
        extra=_sorted_extra(item, _DEF_KEYS),
    )


# --- Hook_Config_Printer -------------------------------------------------


def _action_dict(action: HookAction) -> dict:
    out = {"type": action.type}
    if action.command is not None:
        out["command"] = action.command
    if action.prompt is not None:
        out["prompt"] = action.prompt
    for key, value in sorted(action.extra):
        out[key] = value
    return out


def _definition_dict(definition: HookDefinition) -> dict:
    out = {"name": definition.name, "trigger": definition.trigger}
    if definition.matcher is not None:
        out["matcher"] = definition.matcher
    out["action"] = _action_dict(definition.action)
    for key in ("timeout", "description", "enabled"):
        value = getattr(definition, key)
        if value is not None:
            out[key] = value
    for key, value in sorted(definition.extra):
        out[key] = value
    return out


def hook_to_obj(hook_file: HookFile) -> dict:
    out = {"version": hook_file.version, "hooks": [_definition_dict(d) for d in hook_file.hooks]}
    for key, value in sorted(hook_file.extra):
        out[key] = value
    return out


def print_hook_file(hook_file: HookFile) -> str:
    """Print a HookFile as v1 JSON: 2-space indent, LF only, one trailing newline."""
    return json.dumps(hook_to_obj(hook_file), indent=2, ensure_ascii=False) + "\n"
