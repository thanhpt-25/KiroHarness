"""`scripts/harness trace` command (agent-harness-platform R14.1)."""
# Validates: agent-harness-platform/R14.1
import io
import json
import unittest

from tests._support import TemplateCopy

from harness_cli import main as cli  # noqa: E402


class TraceCommand(unittest.TestCase):
    def run_trace(self, root, *extra):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["--root", str(root), "trace", *extra], out, err)
        return code, out.getvalue(), err.getvalue()

    def test_prints_markdown_and_writes_json(self):
        with TemplateCopy() as root:
            code, out, _err = self.run_trace(root)
            self.assertEqual(code, 0, out)
            self.assertIn("# Traceability report", out)
            data = json.loads((root / "build" / "traceability.json").read_text())
            self.assertIn("agent-harness-platform/R14.1", data["criteria"])
            self.assertEqual(data["dangling"], [])

    def test_json_flag_prints_json(self):
        with TemplateCopy() as root:
            code, out, _err = self.run_trace(root, "--json")
            self.assertEqual(code, 0)
            self.assertIn("criteria", json.loads(out))

    def test_uncovered_criterion_gives_exit_1(self):
        with TemplateCopy() as root:
            for test in (root / "tests" / "evals").glob("*.py"):
                test.unlink()
            code, out, _err = self.run_trace(root)
            self.assertEqual(code, 1)
            self.assertIn("Uncovered", out)


if __name__ == "__main__":
    unittest.main()
