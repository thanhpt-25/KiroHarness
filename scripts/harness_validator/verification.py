"""Manual_Check_Record checks: VERIFY-FM, VERIFY-FIELD.

Records live at ``docs/verification/<agent>/<agent-version>/<check>.md`` and
start with front matter that links the check to acceptance criteria
(agent-harness-platform Requirement 3.4 and the Manual_Check_Record glossary
entry). Files directly in ``docs/verification/`` (README, template) are not
records.
"""

from __future__ import annotations

import datetime
import re

from . import frontmatter
from .report import error

VERDICTS = ("pass", "fail", "partial")
CRITERION_RE = re.compile(r"^[a-z0-9][a-z0-9-]*/R\d+\.\d+$")
REQUIRED = ("criteria", "agent", "agent_version", "os", "date", "verdict")


def check_record(path: str, text: str) -> list:
    split = frontmatter.split_front_matter(text)
    if split is None:
        return [error(path, "-", "VERIFY-FM", "Manual_Check_Record must start with a front matter block")]
    try:
        data = frontmatter.parse_front_matter(split[0])
    except frontmatter.FrontMatterError as exc:
        return [error(path, f"line {exc.line}", "VERIFY-FM", f"front matter is not valid: {exc.msg}")]
    findings = []
    for key in REQUIRED:
        if key not in data or data[key] in ("", [], None):
            findings.append(error(path, f"front_matter.{key}", "VERIFY-FIELD", f"{key} is missing or empty"))
    criteria = data.get("criteria")
    if isinstance(criteria, list):
        for item in criteria:
            if not isinstance(item, str) or not CRITERION_RE.match(item):
                findings.append(error(path, "front_matter.criteria", "VERIFY-FIELD",
                                      f"criterion {item!r} must look like <spec>/R<n>.<m>"))
    elif "criteria" in data:
        findings.append(error(path, "front_matter.criteria", "VERIFY-FIELD", "criteria must be a list"))
    verdict = data.get("verdict")
    if verdict is not None and verdict not in VERDICTS:
        findings.append(error(path, "front_matter.verdict", "VERIFY-FIELD", f"verdict must be one of {', '.join(VERDICTS)}"))
    date = data.get("date")
    if isinstance(date, str) and date:
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            findings.append(error(path, "front_matter.date", "VERIFY-FIELD", "date must be YYYY-MM-DD"))
    parts = path.split("/")  # docs/verification/<agent>/<version>/<file>
    if len(parts) >= 5:
        if isinstance(data.get("agent"), str) and data["agent"] != parts[2]:
            findings.append(error(path, "front_matter.agent", "VERIFY-FIELD", f"agent {data['agent']!r} does not match directory {parts[2]!r}"))
        if isinstance(data.get("agent_version"), str) and data["agent_version"] != parts[3]:
            findings.append(error(path, "front_matter.agent_version", "VERIFY-FIELD",
                                  f"agent_version {data['agent_version']!r} does not match directory {parts[3]!r}"))
    return findings
