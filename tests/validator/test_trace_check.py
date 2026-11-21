"""Trace check in the validator (agent-harness-platform R14.2)."""
# Validates: agent-harness-platform/R14.2
import unittest

from tests._support import ROOT, TemplateCopy

from harness_validator import trace_check  # noqa: E402


class TraceCheck(unittest.TestCase):
    def test_repository_has_no_trace_errors(self):
        self.assertEqual([f for f in trace_check.check(str(ROOT)) if f.severity == "error"], [])

    def test_uncovered_criterion_outside_backlog_is_an_error(self):
        with TemplateCopy() as root:
            backlog = root / trace_check.BACKLOG
            lines = backlog.read_text().splitlines()
            backlog.write_text("\n".join(l for l in lines if not l.endswith("/R1.4")) + "\n")
            codes = [(f.rule, f.message) for f in trace_check.check(str(root))]
            self.assertTrue(any(c == "TRACE-UNCOVERED" and "/R1.4" in m for c, m in codes), codes)

    def test_dangling_tag_is_an_error(self):
        with TemplateCopy() as root:
            (root / "tests" / "validator" / "test_dangling.py").write_text("# Valid" + "ates: agent-harness-platform/R99.9\n")
            codes = [f.rule for f in trace_check.check(str(root))]
            self.assertIn("TRACE-DANGLING", codes)


if __name__ == "__main__":
    unittest.main()
