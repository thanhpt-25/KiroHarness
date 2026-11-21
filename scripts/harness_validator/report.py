"""Validation_Report: findings and their rendering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, order=True)
class Finding:
    severity: Severity
    path: str  # workspace-relative POSIX path
    field: str  # e.g. "hooks[2].trigger", "front_matter.inclusion", "line 14"
    rule: str  # rule id, e.g. "HOOK-SCHEMA"
    message: str


def error(path: str, field: str, rule: str, message: str) -> Finding:
    return Finding(Severity.ERROR, path, field, rule, message)


def warning(path: str, field: str, rule: str, message: str) -> Finding:
    return Finding(Severity.WARNING, path, field, rule, message)


def _one_line(text: str) -> str:
    return text.replace("\r", "\\r").replace("\n", "\\n")


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def sort_key(finding: Finding):
    return (finding.path, finding.field, finding.rule, finding.severity.value, finding.message)


def format_finding(finding: Finding) -> str:
    field = finding.field or "-"
    return (
        f"{finding.severity.value.upper():<7} {_one_line(finding.path)}  {_one_line(field)}"
        f"  [{finding.rule}] {_one_line(finding.message)}"
    )


def summary_line(files_checked: int, errors: int, warnings: int) -> str:
    return (
        f"Summary: {_plural(files_checked, 'file')} checked, "
        f"{_plural(errors, 'error')}, {_plural(warnings, 'warning')}"
    )


def render(findings, files_checked: int):
    """Return ``(text, exit_code)``. Exit code is 1 if any finding is an error, else 0."""
    ordered = sorted(findings, key=sort_key)
    errors = sum(1 for f in ordered if f.severity is Severity.ERROR)
    warnings = len(ordered) - errors
    lines = [format_finding(f) for f in ordered]
    lines.append(summary_line(files_checked, errors, warnings))
    return "\n".join(lines) + "\n", (1 if errors else 0)
