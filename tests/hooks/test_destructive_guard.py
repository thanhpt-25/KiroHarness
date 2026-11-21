"""Destructive_Command_Guard tests (Requirements 4.4, 4.7, 4.8, 11.1, 11.2, 11.8).

Test cases for the blocked commands are built from destructive-commands.txt at
run time, so a new entry is tested without changing this file.
"""
# Validates: kiro-agent-harness-template/R4.4, kiro-agent-harness-template/R4.7, kiro-agent-harness-template/R4.8, kiro-agent-harness-template/R11.1, kiro-agent-harness-template/R11.2, kiro-agent-harness-template/R11.8
# Validates: kiro-agent-harness-template/R4.4, kiro-agent-harness-template/R4.7, kiro-agent-harness-template/R4.8, kiro-agent-harness-template/R11.1, kiro-agent-harness-template/R11.2, kiro-agent-harness-template/R11.8

import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._support import HOOK_SCRIPTS, detail, run_script, tool_call

SCRIPT = HOOK_SCRIPTS / "destructive-guard.sh"
LIST = HOOK_SCRIPTS / "destructive-commands.txt"

SAFE_COMMANDS = [
    "rm -rf ./build",
    "git push origin main",
    "git reset --soft HEAD~1",
    "git status",
    "ls -la",
    "npm test",
    "git clean -n",
    "git branch feature-x",
    "python3 -m pytest -q",
    "echo hello && git log --oneline -5",
    "cat README.md | grep Setup",
    "mkdir -p dist; cp a.txt dist/",
]


def list_entries(path=LIST):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


class DestructiveGuard(unittest.TestCase):
    def guard(self, stdin: bytes, script=SCRIPT):
        return run_script(script, stdin)

    def test_every_list_entry_is_blocked(self):
        entries = list_entries()
        self.assertGreater(len(entries), 0)
        for entry in entries:
            with self.subTest(entry=entry):
                command = f"cd /tmp && {entry}"
                result = self.guard(tool_call("execute_bash", {"command": command}))
                self.assertEqual(result.returncode, 2, detail(command, "exit 2", f"exit {result.returncode}"))
                self.assertIn(entry, result.stderr.decode())
                self.assertIn("Destructive_Command_List", result.stderr.decode())

    def test_safe_commands_are_allowed(self):
        self.assertGreaterEqual(len(SAFE_COMMANDS), 10)
        for command in SAFE_COMMANDS:
            with self.subTest(command=command):
                result = self.guard(tool_call("execute_bash", {"command": command}))
                actual = (result.returncode, result.stderr.decode())
                self.assertEqual(actual, (0, ""), detail(command, "exit 0, empty stderr", actual))

    def test_empty_stdin_fails_closed(self):
        result = self.guard(b"")
        self.assertEqual(result.returncode, 2, detail("", "exit 2", result.returncode))
        self.assertIn("could not be parsed", result.stderr.decode())

    def test_invalid_json_fails_closed(self):
        result = self.guard(b"not json")
        self.assertEqual(result.returncode, 2, detail("not json", "exit 2", result.returncode))
        self.assertIn("could not be parsed", result.stderr.decode())

    def test_missing_command_fails_closed(self):
        result = self.guard(tool_call("execute_bash", {"cwd": "/tmp"}))
        self.assertEqual(result.returncode, 2)
        self.assertIn("command field is missing", result.stderr.decode())

    def test_background_process_stop_is_allowed(self):
        result = self.guard(tool_call("control_bash_process", {"action": "stop", "terminalId": "3"}))
        self.assertEqual((result.returncode, result.stderr), (0, b""))

    def test_missing_list_blocks_and_names_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp) / "scripts"
            shutil.copytree(HOOK_SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
            (scripts / "destructive-commands.txt").unlink()
            result = run_script(scripts / "destructive-guard.sh", tool_call("execute_bash", {"command": "ls"}))
            self.assertEqual(result.returncode, 2)
            self.assertIn(str(scripts / "destructive-commands.txt"), result.stderr.decode())
            self.assertIn("could not load list", result.stderr.decode())

    def test_long_command_against_200_patterns_finishes_within_2_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp) / "scripts"
            shutil.copytree(HOOK_SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
            patterns = [f"tool{i} --flag{i} target{i}" for i in range(200)]
            (scripts / "destructive-commands.txt").write_text("\n".join(patterns) + "\n")
            command = ("echo word " * 1000)[:10000]
            start = time.monotonic()
            result = run_script(scripts / "destructive-guard.sh", tool_call("execute_bash", {"command": command}))
            elapsed = time.monotonic() - start
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertLess(elapsed, 2.0, detail("10,000-character command", "< 2 s", f"{elapsed:.2f} s"))


if __name__ == "__main__":
    unittest.main()
