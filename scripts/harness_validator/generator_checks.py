"""Generator checks: MANIFEST, DRIFT, CONTEXT-BUDGET (agent-harness-platform R6.1, R6.4, R7.3)."""

from __future__ import annotations

from harness_cli import plan as plan_mod
from harness_cli import sync as sync_mod

from .manifest import ManifestError
from .report import error, warning


def check_generated(root, manifest_path="harness/manifest.json"):
    """Return ``(findings, notes, generated_paths)``."""
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
