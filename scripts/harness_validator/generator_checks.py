"""Generator checks: MANIFEST, DRIFT, CONTEXT-BUDGET (agent-harness-platform R6.1, R6.4, R7.3)."""

from __future__ import annotations

from harness_cli import plan as plan_mod
from harness_cli import sync as sync_mod

from .manifest import ManifestError
from .report import error, warning


def check_generated(root, manifest_path="harness/manifest.json"):
    """Return ``(findings, notes, generated_paths)``."""
    missing = _missing_matrix_entries(root)
    if missing:
        return missing, [], set()
    try:
        plan = plan_mod.build_plan(str(root))
    except ManifestError as exc:
        return [error(manifest_path, "-", "MANIFEST", problem) for problem in exc.problems], [], set()
    findings = []
    for path, _diff in sync_mod.drift(str(root), plan):
        findings.append(error(path, "-", "DRIFT", "generated file differs from its sources; run scripts/harness sync"))
    notes = []
    for agent, (lines, chars) in sorted(plan_mod.always_on_sizes(plan).items()):
        notes.append(f"Always-on context: {agent} {lines} lines, {chars} characters")
        if lines > plan_mod.BUDGET_LINES or chars > plan_mod.BUDGET_CHARS:
            findings.append(warning("harness/guidance", agent, "CONTEXT-BUDGET",
                                    f"{agent} always-on context is {lines} lines and {chars} characters; keep it under {plan_mod.BUDGET_LINES} lines and {plan_mod.BUDGET_CHARS} characters"))
    return findings, notes, set(plan.files) | {plan_mod.LOCK_PATH}


def _missing_matrix_entries(root) -> list:
    """An enabled Agent needs a Capability_Matrix entry (R9.4)."""
    import json
    import os

    try:
        with open(os.path.join(str(root), "harness/manifest.json"), encoding="utf-8") as handle:
            enabled = [a for a, v in json.load(handle)["agents"].items() if v.get("enabled")]
        with open(os.path.join(str(root), "harness/capabilities.json"), encoding="utf-8") as handle:
            known = json.load(handle)["agents"]
    except (OSError, ValueError, KeyError):
        return []  # missing or unreadable files are reported by their own checks
    return [error("harness/manifest.json", f"agents.{a}", "CAP-MISSING", f"{a} is enabled but has no entry in harness/capabilities.json")
            for a in sorted(enabled) if a not in known]
