# Feature: kiro-agent-harness-template, Property 26: Report rendering and exit code
# Validates: kiro-agent-harness-template/R10.9, kiro-agent-harness-template/R10.10
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator.report import Finding, Severity, render, sort_key

words = st.text(alphabet="abcxyz./[]_-0123", min_size=1, max_size=12)
findings = st.lists(
    st.builds(Finding, st.sampled_from(list(Severity)), words, words, words.map(str.upper), st.text(max_size=20)),
    max_size=15,
)


class ReportRender(unittest.TestCase):
    @given(findings, st.integers(0, 10_000))
    def test_render(self, items, files):
        text, code = render(items, files)
        errors = sum(f.severity is Severity.ERROR for f in items)
        warnings = len(items) - errors
        self.assertEqual(code, 1 if errors else 0)
        # Split on LF only: splitlines() also breaks on characters such as \x1e.
        lines = text[:-1].split("\n")
        self.assertEqual(len(lines), len(items) + 1)
        for line, finding in zip(lines, sorted(items, key=sort_key)):
            self.assertTrue(line.startswith(finding.severity.value.upper()))
            for part in (finding.path, finding.field, f"[{finding.rule}]"):
                self.assertIn(part, line)
            self.assertIn(finding.message.replace("\n", "\\n").replace("\r", "\\r"), line)
        summary = lines[-1]
        self.assertTrue(summary.startswith(f"Summary: {files} file"))
        self.assertIn(f"{errors} error", summary)
        self.assertIn(f"{warnings} warning", summary)


if __name__ == "__main__":
    unittest.main()
