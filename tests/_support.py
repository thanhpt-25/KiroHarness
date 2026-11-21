"""Shared paths and helpers for the Template tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
HOOK_SCRIPTS = ROOT / ".kiro" / "hooks" / "scripts"
CORE = ROOT / "harness" / "core"
LIB = CORE  # historical name
POLICY = ROOT / "harness" / "policy"

for _path in (str(SCRIPTS), str(CORE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Tests must not write the developer's Decision_Log; tests that check logging set the variable to 1.
os.environ.setdefault("HARNESS_DECISION_LOG", "0")
_COPY_IGNORE = shutil.ignore_patterns(".git", ".venv", ".hypothesis", ".harness", "__pycache__", "*.pyc", ".DS_Store")


def detail(input_value, expected, actual) -> str:
    """Assertion message in the format scripts/validate.sh prints for failures."""
    return f"input: {input_value!r}\nexpected: {expected}\nactual: {actual}"


def run_script(script, stdin: bytes = b"", env=None, cwd=None, timeout: float = 30, args=()):
    """Run a shell script with ``sh`` and return the CompletedProcess (bytes)."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["sh", str(script), *args],
        input=stdin,
        capture_output=True,
        env=full_env,
        cwd=str(cwd or ROOT),
        timeout=timeout,
    )


def tool_call(tool_name: str, tool_input) -> bytes:
    return json.dumps(
        {"hook_event_name": "PreToolUse", "cwd": str(ROOT), "tool_name": tool_name, "tool_input": tool_input}
    ).encode("utf-8")


def copy_template(destination: Path) -> Path:
    """Copy the Template (without caches and virtualenvs) to ``destination``."""
    shutil.copytree(ROOT, destination, ignore=_COPY_IGNORE, symlinks=True)
    return destination


class TemplateCopy:
    """Context manager: a temporary copy of the Template."""

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        return copy_template(Path(self._tmp.name) / "template")

    def __exit__(self, *exc):
        self._tmp.cleanup()
        return False


def validate(root):
    """Run the Config_Validator in-process. Return ``(findings, files_checked)``."""
    from harness_validator.__main__ import validate as _validate

    return _validate(root)


def errors(findings):
    return [f for f in findings if f.severity.value == "error"]
