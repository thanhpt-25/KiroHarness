"""Steering_File checks: STEER-FM, STEER-FILEMATCH, STEER-AUTO."""

from __future__ import annotations

from . import frontmatter
from .report import error

INCLUSION_MODES = ("always", "fileMatch", "manual", "auto")
NAME_MAX = 64
DESCRIPTION_MAX = 200


def _length_problem(value, limit: int):
    if value is None:
        return "is missing"
    if not isinstance(value, str):
        return "must be a string"
    if value.strip() == "":
        return "must not be empty"
    if len(value) > limit:
        return f"must be at most {limit} characters (got {len(value)})"
    return None


def check_steering(path: str, text: str) -> list:
    findings = []
    split = frontmatter.split_front_matter(text)
    if split is None:
        return [
            error(
                path,
                "front_matter",
                "STEER-FM",
                "missing YAML front matter block delimited by '---' lines",
            )
        ]
    yaml_text, _body = split
    try:
        data = frontmatter.parse_front_matter(yaml_text)
    except frontmatter.FrontMatterError as exc:
        # Line numbers are relative to the file: the opening '---' is line 1.
        return [
            error(
                path,
                f"front_matter (line {exc.line + 1})",
                "STEER-FM",
                f"front matter is not valid in the supported YAML subset: {exc.msg}",
            )
        ]

    inclusion = data.get("inclusion")
    if "inclusion" not in data:
        findings.append(
            error(path, "front_matter.inclusion", "STEER-FM", "inclusion is missing")
        )
        return findings
    if not isinstance(inclusion, str) or inclusion not in INCLUSION_MODES:
        findings.append(
            error(
                path,
                "front_matter.inclusion",
                "STEER-FM",
                f"inclusion {inclusion!r} must be one of {', '.join(INCLUSION_MODES)}",
            )
        )
        return findings

    if inclusion == "fileMatch":
        pattern = data.get("fileMatchPattern")
        problem = None
        if "fileMatchPattern" not in data:
            problem = "fileMatchPattern is missing for inclusion fileMatch"
        elif isinstance(pattern, str):
            if pattern.strip() == "":
                problem = "fileMatchPattern is empty"
        elif isinstance(pattern, list):
            if not pattern:
                problem = "fileMatchPattern is an empty list"
            elif any(p.strip() == "" for p in pattern):
                problem = "fileMatchPattern contains an empty pattern"
        else:
            problem = "fileMatchPattern must be a string or a list of strings"
        if problem:
            findings.append(
                error(path, "front_matter.fileMatchPattern", "STEER-FILEMATCH", problem)
            )

    if inclusion == "auto":
        for key, limit in (("name", NAME_MAX), ("description", DESCRIPTION_MAX)):
            problem = _length_problem(data.get(key), limit)
            if problem:
                findings.append(
                    error(
                        path,
                        f"front_matter.{key}",
                        "STEER-AUTO",
                        f"{key} {problem}; inclusion auto needs a {key} of 1 to {limit} characters",
                    )
                )
    return findings


def steering_meta(text: str):
    """Return the parsed front matter mapping, or None when it is missing or invalid."""
    split = frontmatter.split_front_matter(text)
    if split is None:
        return None
    try:
        return frontmatter.parse_front_matter(split[0])
    except frontmatter.FrontMatterError:
        return None
