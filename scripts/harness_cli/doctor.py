"""``harness doctor`` (agent-harness-platform R17.4): report the environment and the Harness state.

Exit 0 when the required runtime (Python 3.10 or newer, POSIX sh) is present, 1 when it is not, 2 when the
Manifest cannot be read. ``git`` and ``uvx`` are optional and only reported.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

MIN_PYTHON = (3, 10)


def read_version(root) -> str:
    try:
        with open(os.path.join(root, "harness", "VERSION"), encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return "unknown"


def decision_log_status(root, environ) -> str:
    if environ.get("HARNESS_DECISION_LOG") == "0":
        return "disabled (HARNESS_DECISION_LOG=0)"
    path = os.path.join(root, ".harness", "decisions.jsonl")
    if os.path.isfile(path):
        return f"enabled, {os.path.getsize(path)} bytes in .harness/decisions.jsonl"
    return "enabled, no records yet"


def run(root, out, err, which=shutil.which, version_info=None, environ=None) -> int:
    version_info = version_info or sys.version_info
    environ = os.environ if environ is None else environ
    missing = []
    python_ok = tuple(version_info[:2]) >= MIN_PYTHON
    out.write(f"Harness version: {read_version(root)}\n")
    out.write(f"Python: {version_info[0]}.{version_info[1]} ({'ok' if python_ok else 'need 3.10 or newer'})\n")
    if not python_ok:
        missing.append("python 3.10")
    for tool, required in (("sh", True), ("git", False), ("uvx", False)):
        found = which(tool)
        out.write(f"{tool}: {found or 'not found'}{'' if found or not required else ' (required)'}\n")
        if required and not found:
            missing.append(tool)
    try:
        from harness_validator import manifest as manifest_mod
        from . import plan as plan_mod
        from . import sync as sync_mod

        manifest = manifest_mod.load(root)
        with open(os.path.join(root, "harness", "capabilities.json"), encoding="utf-8") as handle:
            caps = json.load(handle)["agents"]
        out.write("Agents:\n")
        for name, spec in manifest["agents"].items():
            if not spec.get("enabled"):
                continue
            protection = caps.get(name, {}).get("protection", {})
            levels = ", ".join(f"{guard}={level}" for guard, level in sorted(protection.items())) or "no protection data"
            out.write(f"  {name}: {levels}\n")
        drift = sync_mod.drift(root, plan_mod.build_plan(root))
        out.write(f"Drift: {'none' if not drift else str(len(drift)) + ' generated file(s) differ; run scripts/harness sync'}\n")
    except Exception as exc:  # report, never crash the diagnostic
        err.write(f"doctor: cannot read the Harness configuration: {exc.__class__.__name__}: {exc}\n")
        return 2
    out.write(f"Decision_Log: {decision_log_status(root, environ)}\n")
    if missing:
        err.write(f"doctor: missing required runtime: {', '.join(missing)}\n")
        return 1
    return 0
