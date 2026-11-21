"""Capability_Matrix checks: CAP-FIELD, CAP-STALE (agent-harness-platform R9.1, R9.5)."""

from __future__ import annotations

import datetime
import json

from .report import error, warning

REQUIRED = ("label", "status", "events", "output", "tool_map", "tool_prefix_map", "mcp", "protection", "gaps")
STATUSES = ("documented", "verified", "unverified")
STALE_DAYS = 180


def check_capabilities(path: str, text: str, today: datetime.date | None = None) -> list:
    today = today or datetime.date.today()
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [error(path, "-", "CAP-FIELD", f"not valid JSON: {exc}")]
    agents = data.get("agents")
    if not isinstance(agents, dict) or not agents:
        return [error(path, "agents", "CAP-FIELD", "agents must be a non-empty object")]
    findings = []
    for name, entry in agents.items():
        for key in REQUIRED:
            if key not in entry:
                findings.append(error(path, f"agents.{name}.{key}", "CAP-FIELD", f"{key} is missing"))
        if entry.get("status") not in STATUSES:
            findings.append(error(path, f"agents.{name}.status", "CAP-FIELD", f"status must be one of {', '.join(STATUSES)}"))
        stamp = (entry.get("verified") or {}).get("date")
        if stamp:
            try:
                age = (today - datetime.date.fromisoformat(stamp)).days
            except ValueError:
                findings.append(error(path, f"agents.{name}.verified.date", "CAP-FIELD", f"{stamp!r} is not an ISO date"))
            else:
                if age > STALE_DAYS:
                    findings.append(warning(path, f"agents.{name}.verified.date", "CAP-STALE",
                                            f"verification is {age} days old (limit {STALE_DAYS}); re-run the manual checks"))
    return findings
