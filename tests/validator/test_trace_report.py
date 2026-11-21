"""Traceability_Report content: tests, records, skipped tests (agent-harness-platform R14.1, R14.6)."""
# Validates: agent-harness-platform/R14.1, agent-harness-platform/R14.6
import json
import tempfile
import unittest
from pathlib import Path

from tests._support import ROOT  # noqa: F401  (puts scripts/ on sys.path)
from harness_validator import trace_check

REQUIREMENTS = """# R

## Introduction

x

## Glossary

- **A**: b

## Requirements

### Requirement 1: One

**User Story:** As a user, I want x, so that y.

#### Acceptance Criteria

1. THE System SHALL do one.
2. THE System SHALL do two.
3. THE System SHALL do three.
"""
TAG = "# Valid" + "ates: alpha/R1.1, alpha/R1.2, alpha/R9.9\n"
RECORD = "---\ncriteria:\n  - alpha/R1.3\n---\nchecked\n"


def make_repo(tmp):
    root = Path(tmp)
    (root / ".kiro/specs/alpha").mkdir(parents=True)
    (root / ".kiro/specs/alpha/requirements.md").write_text(REQUIREMENTS)
    (root / ".kiro/specs/alpha/tasks.md").write_text("- [ ] 1. T\n  - _Requirements: 1.1_\n")
    (root / "tests").mkdir()
    (root / "tests/test_one.py").write_text(TAG + "import unittest\n")
    rec = root / "docs/verification/agent/1.0/check.md"
    rec.parent.mkdir(parents=True)
    rec.write_text(RECORD)
    return root


class TraceReport(unittest.TestCase):
    def test_report_lists_tests_records_dangling_and_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp)
            results = {"tests.test_one.Case.test_a": ("skipped", "needs a real agent")}
            report = trace_check.build_report(str(root), results)
            self.assertEqual(report["criteria"]["alpha/R1.1"]["tests"][0]["file"], "tests/test_one.py")
            self.assertEqual(report["criteria"]["alpha/R1.3"]["records"], ["docs/verification/agent/1.0/check.md"])
            self.assertEqual(report["criteria"]["alpha/R1.1"]["tasks"], [report["criteria"]["alpha/R1.1"]["tasks"][0]])
            self.assertEqual([d[2] for d in report["dangling"]], ["alpha/R9.9"])
            self.assertEqual(report["skipped"][0]["reason"], "needs a real agent")
            text = trace_check.markdown(report)
            self.assertIn("Dangling tags", text)
            self.assertIn("needs a real agent", text)

    def test_status_is_unknown_without_results_and_failed_wins(self):
        self.assertEqual(trace_check._status({}, "m", None), "unknown")
        both = {"m.C.test_a": ("passed", ""), "m.C.test_b": ("failed", "")}
        self.assertEqual(trace_check._status(both, "m", None), "failed")
        self.assertEqual(trace_check._status({"m.C.test_a": ("skipped", "r")}, "m", None), "skipped")

    def test_load_results_tolerates_missing_and_malformed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(trace_check.load_results(tmp), {})
            (Path(tmp) / "build").mkdir()
            (Path(tmp) / "build/test-results.json").write_text("not json")
            self.assertEqual(trace_check.load_results(tmp), {})
            (Path(tmp) / "build/test-results.json").write_text(json.dumps({"a.b": ["passed", ""]}))
            self.assertEqual(trace_check.load_results(tmp), {"a.b": ("passed", "")})

    def test_missing_directories_give_empty_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(trace_check.scan_criteria(tmp), {})
            self.assertEqual(trace_check.scan_tags(tmp), [])
            self.assertEqual(trace_check.scan_records(tmp), [])
            self.assertEqual(trace_check.read_backlog(tmp), [])


if __name__ == "__main__":
    unittest.main()
