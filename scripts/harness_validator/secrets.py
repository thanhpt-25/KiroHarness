"""Secret detection helpers and the Config_Validator configuration."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SECRET_REF_RE = re.compile(r"^\$\{[A-Z][A-Z0-9_]{0,63}\}$")
SECRET_REF_SPAN_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]{0,63})\}")


class ConfigError(Exception):
    """The validator configuration file is missing or malformed."""


@dataclass(frozen=True)
class SecretPattern:
    id: str
    regex: "re.Pattern"


@dataclass(frozen=True)
class SecretHit:
    pattern_id: str
    start: int
    end: int
    value: str


@dataclass(frozen=True)
class ValidatorConfig:
    secret_patterns: tuple
    read_only_allowlist: frozenset
    known_mutating_tools: frozenset
    mcp_minimum_versions: dict


def _string_list(data, key, path):
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{path}: {key} must be a list of strings")
    return value


def compile_patterns(items, path="validator config") -> tuple:
    if not isinstance(items, list) or not items:
        raise ConfigError(f"{path}: secret_patterns must be a non-empty list")
    patterns = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(
            item.get("regex"), str
        ):
            raise ConfigError(f"{path}: secret_patterns[{index}] needs string id and regex")
        try:
            patterns.append(SecretPattern(item["id"], re.compile(item["regex"])))
        except re.error as exc:
            raise ConfigError(f"{path}: secret_patterns[{index}] does not compile: {exc}") from None
    return tuple(patterns)


def load_validator_config(path) -> ValidatorConfig:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"{path}: could not be read: {exc.strerror or exc}") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{path}: not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top-level value must be an object")
    minimums = data.get("mcp_minimum_versions", {})
    if not isinstance(minimums, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in minimums.items()
    ):
        raise ConfigError(f"{path}: mcp_minimum_versions must map package names to versions")
    return ValidatorConfig(
        secret_patterns=compile_patterns(data.get("secret_patterns"), str(path)),
        read_only_allowlist=frozenset(_string_list(data, "read_only_allowlist", path)),
        known_mutating_tools=frozenset(_string_list(data, "known_mutating_tools", path)),
        mcp_minimum_versions=dict(minimums),
    )


def is_secret_reference(value) -> bool:
    return isinstance(value, str) and SECRET_REF_RE.match(value) is not None


def find_secrets(value: str, patterns) -> list:
    """Return every secret-pattern hit in ``value`` that is not a Secret_Reference."""
    if SECRET_REF_RE.match(value):
        return []
    ref_spans = [m.span() for m in SECRET_REF_SPAN_RE.finditer(value)]
    hits = []
    for pattern in patterns:
        for match in pattern.regex.finditer(value):
            start, end = match.span()
            if start == end:
                continue
            if any(s <= start and end <= e for s, e in ref_spans):
                continue
            hits.append(SecretHit(pattern.id, start, end, match.group(0)))
    return hits


def mask(value: str) -> str:
    """Keep the first ``min(4, len(value) // 2)`` characters; replace the rest with ``*``."""
    keep = min(4, len(value) // 2)
    return value[:keep] + "*" * (len(value) - keep)


def walk_json_strings(obj, prefix: str = ""):
    """Yield ``(field path, value)`` for every string value in a decoded JSON document."""
    if isinstance(obj, str):
        yield prefix or "$", obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from walk_json_strings(value, path)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk_json_strings(value, f"{prefix}[{index}]")
