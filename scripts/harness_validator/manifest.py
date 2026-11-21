"""Manifest schema checker (agent-harness-platform R6.1).

A small standard-library JSON Schema subset: type, const, enum, pattern,
required, properties, additionalProperties, items, minItems and ``$ref`` to a
name in the schema's ``definitions``. Semantic checks (guidance globs resolve
to files) follow the structural ones.
"""

from __future__ import annotations

import glob
import json
import os
import re

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int}


class ManifestError(Exception):
    """The Manifest is not valid; ``problems`` lists every finding."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def _check(value, schema, root, path, problems):
    if "$ref" in schema:
        schema = root["definitions"][schema["$ref"]]
    if "const" in schema and value != schema["const"]:
        problems.append(f"{path}: must be {schema['const']!r}")
        return
    kind = schema.get("type")
    if kind:
        expected = TYPES[kind]
        if not isinstance(value, expected) or (kind == "integer" and isinstance(value, bool)):
            problems.append(f"{path}: must be {kind}")
            return
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: must be one of {', '.join(map(str, schema['enum']))}")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        problems.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                problems.append(f"{path}: {key} is required")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                _check(item, props[key], root, f"{path}.{key}", problems)
            elif extra is False:
                problems.append(f"{path}: unknown field {key}")
            elif isinstance(extra, dict):
                _check(item, extra, root, f"{path}.{key}", problems)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            problems.append(f"{path}: needs at least {schema['minItems']} item(s)")
        for index, item in enumerate(value):
            if "items" in schema:
                _check(item, schema["items"], root, f"{path}[{index}]", problems)


def schema_problems(manifest, schema) -> list:
    problems: list = []
    _check(manifest, schema, schema, "manifest", problems)
    return problems


def guidance_files(root, manifest) -> list:
    """Sorted repo-relative guidance paths matched by the Manifest patterns."""
    found = set()
    for pattern in manifest.get("guidance", []):
        for hit in glob.glob(os.path.join(root, pattern)):
            if os.path.isfile(hit):
                found.add(os.path.relpath(hit, root).replace(os.sep, "/"))
    return sorted(found)


def load(root):
    """Return the validated Manifest; raise ManifestError listing every problem."""
    try:
        with open(os.path.join(root, "harness/manifest.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        with open(os.path.join(root, "harness/manifest.schema.json"), encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ManifestError([f"cannot read the Manifest or its schema: {exc}"])
    problems = schema_problems(manifest, schema)
    if not problems:
        for pattern in manifest["guidance"]:
            if not any(os.path.isfile(h) for h in glob.glob(os.path.join(root, pattern))):
                problems.append(f"manifest.guidance: {pattern} matches no file")
    if problems:
        raise ManifestError(problems)
    return manifest
