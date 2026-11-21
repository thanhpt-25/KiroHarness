"""``harness init``, ``upgrade`` and ``doctor`` (agent-harness-platform R17.2, R17.3, R17.4)."""
# Validates: agent-harness-platform/R17.2, agent-harness-platform/R17.3, agent-harness-platform/R17.4
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._support import ROOT, TemplateCopy

from harness_cli import doctor, install  # noqa: E402
from harness_cli import main as cli  # noqa: E402


def run_cli(root, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--root", str(root), *argv], out, err)
    return code, out.getvalue(), err.getvalue()


class Init(unittest.TestCase):
    def test_installs_selected_agents_only_and_validates(self):
        with TemplateCopy() as src, tempfile.TemporaryDirectory() as tmp:
            code, out, err = run_cli(src, "init", tmp, "--agents", "kiro,claude-code")
            self.assertEqual(code, 0, out + err)
            target = Path(tmp)
            agents = json.loads((target / "harness/manifest.json").read_text())["agents"]
            self.assertEqual({n for n, a in agents.items() if a["enabled"]}, {"kiro", "claude-code"})
            self.assertTrue((target / ".claude/settings.json").is_file())
            self.assertTrue((target / ".kiro/steering/security.md").is_file())
            self.assertFalse((target / ".cursor").exists())
            self.assertTrue((target / "harness/release.lock.json").is_file())
            self.assertIn("Summary:", out)

    def test_works_inside_an_existing_git_repository(self):
        with TemplateCopy() as src, tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            code, out, err = run_cli(src, "init", tmp)
            self.assertEqual(code, 0, out + err)

    def test_refuses_to_overwrite_without_force(self):
        with TemplateCopy() as src, tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_cli(src, "init", tmp)[0], 0)
            (Path(tmp) / "harness/policy/protected-paths.txt").write_text("custom\n")
            code, _out, err = run_cli(src, "init", tmp)
            self.assertEqual(code, 1)
            self.assertIn("refusing to overwrite", err)
            self.assertEqual((Path(tmp) / "harness/policy/protected-paths.txt").read_text(), "custom\n")
            self.assertEqual(run_cli(src, "init", tmp, "--force")[0], 0)

    def test_unknown_agent_is_a_usage_error(self):
        with TemplateCopy() as src, tempfile.TemporaryDirectory() as tmp:
            code, _out, err = run_cli(src, "init", tmp, "--agents", "emacs")
            self.assertEqual(code, 2)
            self.assertIn("unknown: emacs", err)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class Upgrade(unittest.TestCase):
    def setUp(self):
        self.old, self.new, self.tmp = TemplateCopy(), TemplateCopy(), tempfile.TemporaryDirectory()
        self.src_old, self.src_new = self.old.__enter__(), self.new.__enter__()
        self.target = Path(self.tmp.name)
        self.assertEqual(run_cli(self.src_old, "init", self.tmp.name)[0], 0)

    def tearDown(self):
        self.tmp.cleanup()
        self.new.__exit__(None, None, None)
        self.old.__exit__(None, None, None)

    def upstream(self, rel, text):
        (self.src_new / rel).write_text(text)

    def test_unedited_customizable_and_owned_files_are_updated(self):
        self.upstream("harness/policy/egress-allowlist.txt", "example.org\n")
        self.upstream("scripts/lint.sh", "#!/bin/sh\necho new\n")
        code, out, err = run_cli(self.src_new, "upgrade", "--from", str(self.src_new), "--target", str(self.target))
        self.assertEqual(code, 0, out + err)
        self.assertEqual((self.target / "harness/policy/egress-allowlist.txt").read_text(), "example.org\n")
        self.assertIn("echo new", (self.target / "scripts/lint.sh").read_text())

    def test_local_edit_is_kept_when_upstream_is_unchanged(self):
        path = self.target / "harness/policy/egress-allowlist.txt"
        path.write_text("mine.example\n")
        code, out, _err = run_cli(self.src_new, "upgrade", "--from", str(self.src_new), "--target", str(self.target))
        self.assertEqual(code, 0)
        self.assertEqual(path.read_text(), "mine.example\n")
        self.assertIn("1 kept", out)

    def test_edit_on_both_sides_is_a_conflict_and_the_file_is_left_alone(self):
        path = self.target / "harness/policy/egress-allowlist.txt"
        path.write_text("mine.example\n")
        self.upstream("harness/policy/egress-allowlist.txt", "theirs.example\n")
        code, out, _err = run_cli(self.src_new, "upgrade", "--from", str(self.src_new), "--target", str(self.target))
        self.assertEqual(code, 1)
        self.assertEqual(path.read_text(), "mine.example\n")
        self.assertIn("conflict: harness/policy/egress-allowlist.txt", out)
        self.assertIn("-mine.example", out)
        self.assertIn("+theirs.example", out)

    def test_manifest_selection_is_never_replaced(self):
        manifest = (self.target / "harness/manifest.json").read_text()
        self.upstream("harness/manifest.json", "{}")
        code, _out, _err = run_cli(self.src_new, "upgrade", "--from", str(self.src_new), "--target", str(self.target))
        self.assertEqual(code, 0)
        self.assertEqual((self.target / "harness/manifest.json").read_text(), manifest)

    def test_target_without_manifest_is_refused(self):
        with tempfile.TemporaryDirectory() as empty:
            code, _out, err = run_cli(self.src_new, "upgrade", "--from", str(self.src_new), "--target", empty)
            self.assertEqual(code, 2)
            self.assertIn("harness init", err)


class Doctor(unittest.TestCase):
    def test_reports_the_checkout(self):
        code, out, _err = run_cli(ROOT, "doctor")
        self.assertEqual(code, 0)
        for text in ("Harness version:", "Python:", "Agents:", "kiro:", "Drift: none", "Decision_Log:"):
            self.assertIn(text, out)

    def test_missing_sh_is_a_required_runtime_failure(self):
        out, err = io.StringIO(), io.StringIO()
        code = doctor.run(str(ROOT), out, err, which=lambda name: None)
        self.assertEqual(code, 1)
        self.assertIn("missing required runtime: sh", err.getvalue())
        self.assertIn("uvx: not found", out.getvalue())

    def test_old_python_is_a_required_runtime_failure(self):
        out, err = io.StringIO(), io.StringIO()
        code = doctor.run(str(ROOT), out, err, version_info=(3, 8, 0))
        self.assertEqual(code, 1)
        self.assertIn("python 3.10", err.getvalue())

    def test_unreadable_configuration_is_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(doctor.run(tmp, out, err), 2)

    def test_decision_log_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("no records", doctor.decision_log_status(tmp, {}))
            self.assertIn("disabled", doctor.decision_log_status(tmp, {"HARNESS_DECISION_LOG": "0"}))
            (Path(tmp) / ".harness").mkdir()
            (Path(tmp) / ".harness/decisions.jsonl").write_text("{}\n")
            self.assertIn("3 bytes", doctor.decision_log_status(tmp, {}))


if __name__ == "__main__":
    unittest.main()
