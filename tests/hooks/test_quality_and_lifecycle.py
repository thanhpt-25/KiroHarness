"""Quality_Hook, SessionStart, PostTaskExec, and prompt scan tests
(Requirements 6.4, 6.6, 6.7, 6.8, 7.1, 7.3, 7.6, 7.8).

Each test runs the scripts in a temporary copy of the Template with stub lint
and test commands written to scripts/project-commands.env.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._support import TemplateCopy, run_script

PLACEHOLDER = "{{" + "LINT_FILE_COMMAND" + "}}"


def write_commands(root: Path, lint="", test_file="", test=""):
    (root / "scripts" / "project-commands.env").write_text(
        f'LINT_FILE_COMMAND="{lint}"\nTEST_FILE_COMMAND="{test_file}"\nTEST_COMMAND="{test}"\n',
        encoding="utf-8",
    )


def save_event(path: str) -> bytes:
    return json.dumps({"hook_event_name": "PostFileSave", "file_path": path}).encode()


def load_lib(root: Path, name: str):
    lib = str(root / ".kiro/hooks/scripts/lib")
    sys.path.insert(0, lib)
    try:
        for module in ("hookio", "runner", "quality", name):
            sys.modules.pop(module, None)
        return __import__(name)
    finally:
        sys.path.remove(lib)


class QualityHook(unittest.TestCase):
    def setUp(self):
        self._copy = TemplateCopy()
        self.root = self._copy.__enter__()
        self.hook = self.root / ".kiro/hooks/scripts/quality-on-save.sh"

    def tearDown(self):
        self._copy.__exit__(None, None, None)

    def test_not_configured_commands_are_skipped(self):
        write_commands(self.root, lint=PLACEHOLDER)
        result = run_script(self.hook, save_event("src/app_test.go"), cwd=self.root)
        out = result.stdout.decode()
        self.assertEqual(result.returncode, 0, out)
        self.assertIn("skipped LINT_FILE_COMMAND", out)
        self.assertIn("skipped TEST_FILE_COMMAND", out)

    def test_passing_commands_are_named(self):
        write_commands(self.root, lint="true", test_file="true")
        result = run_script(self.hook, save_event("src/app.test.ts"), cwd=self.root)
        out = result.stdout.decode()
        self.assertEqual(result.returncode, 0, out)
        self.assertIn("passed lint (LINT_FILE_COMMAND), test (TEST_FILE_COMMAND) for src/app.test.ts", out)

    def test_non_test_file_runs_lint_only(self):
        write_commands(self.root, lint="true", test_file="false")
        result = run_script(self.hook, save_event("src/app.ts"), cwd=self.root)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("TEST_FILE_COMMAND", result.stdout.decode())

    def test_failure_reports_command_path_and_last_200_lines(self):
        write_commands(self.root, lint="seq 1 500; exit 7; :")
        result = run_script(self.hook, save_event("src/app.py"), cwd=self.root)
        out = result.stdout.decode()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lint (LINT_FILE_COMMAND) failed (exit 7) for src/app.py", out)
        lines = out.splitlines()
        self.assertEqual(lines[1], "301")
        self.assertEqual(lines[-1], "500")
        self.assertIn("failed", result.stderr.decode())

    def test_timeout_stops_the_command(self):
        write_commands(self.root, lint="sleep 30; :")
        quality = load_lib(self.root, "quality")
        stdout, stderr = io.StringIO(), io.StringIO()
        code = quality.main(io.BytesIO(save_event("src/app.py")), stdout, stderr, root=self.root, deadline_seconds=1)
        self.assertEqual(code, 1)
        self.assertIn("timed out after 1s for src/app.py", stdout.getvalue())


class SessionStart(unittest.TestCase):
    def run_in(self, root: Path, env=None):
        return run_script(root / ".kiro/hooks/scripts/session-start.sh", b"{}", cwd=root, env=env)

    def test_reports_branch_and_uncommitted_count_in_a_repository(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        with TemplateCopy() as root:
            git = ["git", "-C", str(root)]
            subprocess.run(git + ["init", "-q", "-b", "trunk"], check=True)
            (root / "new-file.txt").write_text("x")
            result = self.run_in(root)
            out = result.stdout.decode()
            self.assertEqual(result.returncode, 0)
            self.assertIn("Git branch: trunk", out)
            expected = len(subprocess.run(git + ["status", "--porcelain=v1", "--untracked-files=all"], capture_output=True, text=True).stdout.splitlines())
            self.assertIn(f"Uncommitted files: {expected}", out)

    def test_outside_a_repository_reports_unavailable(self):
        with TemplateCopy() as root:
            result = self.run_in(root, env={"GIT_CEILING_DIRECTORIES": str(root.parent)})
            self.assertEqual(result.returncode, 0)
            self.assertIn("Git information unavailable", result.stdout.decode())

    def test_without_git_on_path_reports_unavailable(self):
        with TemplateCopy() as root, tempfile.TemporaryDirectory() as bindir:
            os.symlink(sys.executable, Path(bindir) / "python3")
            for tool in ("dirname", "sh"):
                found = shutil.which(tool)
                if found:
                    os.symlink(found, Path(bindir) / tool)
            result = self.run_in(root, env={"PATH": bindir})
            self.assertEqual(result.returncode, 0)
            self.assertIn("Git information unavailable", result.stdout.decode())


class PostTask(unittest.TestCase):
    def run_hook(self, test_command):
        with TemplateCopy() as root:
            write_commands(root, test=test_command)
            return run_script(root / ".kiro/hooks/scripts/post-task-tests.sh", b"{}", cwd=root)

    def test_passing_tests_exit_0(self):
        result = self.run_hook("true")
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_failing_tests_exit_2_with_output(self):
        result = self.run_hook("echo boom; exit 1")
        self.assertEqual(result.returncode, 2)
        self.assertIn("boom", result.stderr.decode())

    def test_not_configured_exits_0_naming_test_command(self):
        result = self.run_hook("{{" + "TEST_COMMAND" + "}}")
        self.assertEqual(result.returncode, 0)
        self.assertIn("TEST_COMMAND not configured", result.stdout.decode())


class PromptScanConfig(unittest.TestCase):
    def test_unloadable_pattern_file_blocks_and_names_the_file(self):
        with TemplateCopy() as root:
            config = root / "scripts/validator-config.json"
            config.write_text("{broken")
            result = run_script(root / ".kiro/hooks/scripts/prompt-secret-scan.sh", b'{"prompt": "hi"}', cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertIn(str(config), result.stderr.decode())

    def test_clean_prompt_is_allowed(self):
        result = run_script(Path(__file__).resolve().parents[2] / ".kiro/hooks/scripts/prompt-secret-scan.sh", b'{"prompt": "fix the login bug"}')
        self.assertEqual((result.returncode, result.stderr), (0, b""))


if __name__ == "__main__":
    unittest.main()
