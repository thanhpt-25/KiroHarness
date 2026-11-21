"""Manual_Check_Record front matter checks (agent-harness-platform Requirement 3.4)."""
# Validates: agent-harness-platform/R3.4

import unittest

from tests._support import ROOT, TemplateCopy, detail, errors, validate
from harness_validator import verification  # noqa: E402

GOOD = """---
criteria: [agent-harness-platform/R3.4]
agent: kiro
agent_version: 1.2.3
os: macOS 15.1
date: 2026-11-21
verdict: pass
---

# Check
"""
PATH = "docs/verification/kiro/1.2.3/destructive-guard-blocks.md"


def fields(findings):
    return sorted({f.field for f in findings})


class RecordChecks(unittest.TestCase):
    def test_valid_record_has_no_findings(self):
        self.assertEqual(verification.check_record(PATH, GOOD), [])

    def test_no_front_matter(self):
        f = verification.check_record(PATH, "# no front matter")
        self.assertEqual([x.rule for x in f], ["VERIFY-FM"])

    def test_each_problem_is_reported_with_its_field(self):
        cases = {
            "front_matter.verdict": GOOD.replace("verdict: pass", "verdict: maybe"),
            "front_matter.date": GOOD.replace("2026-11-21", "21/11/2026"),
            "front_matter.criteria": GOOD.replace("[agent-harness-platform/R3.4]", "[R3.4]"),
            "front_matter.agent": GOOD.replace("agent: kiro", "agent: cursor"),
            "front_matter.agent_version": GOOD.replace("agent_version: 1.2.3", "agent_version: 9.9.9"),
            "front_matter.os": GOOD.replace("os: macOS 15.1\n", ""),
        }
        for field, text in cases.items():
            self.assertIn(field, fields(verification.check_record(PATH, text)), detail(field, "reported", text))

    def test_validator_checks_records_in_the_tree_and_ignores_top_level_docs(self):
        with TemplateCopy() as root:
            bad = root / PATH
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text(GOOD.replace("verdict: pass", "verdict: maybe"))
            findings, _ = validate(root)
            self.assertEqual([f.rule for f in errors(findings)], ["VERIFY-FIELD"])
            self.assertTrue((root / "docs/verification/TEMPLATE.md").exists())


if __name__ == "__main__":
    unittest.main()
