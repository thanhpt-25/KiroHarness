"""CI runs the coverage gate and the weekly mutation job (agent-harness-platform R14.3, R14.4)."""
# Validates: agent-harness-platform/R14.3, agent-harness-platform/R14.4
import re
import unittest

from tests._support import ROOT


class QualityGates(unittest.TestCase):
    def test_ci_runs_the_coverage_gate_with_pinned_dev_only_tool(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/coverage.sh", ci)
        script = (ROOT / "scripts/coverage.sh").read_text(encoding="utf-8")
        self.assertIn('"90"', script)
        self.assertIn('"80"', script)
        self.assertRegex((ROOT / "requirements-dev.txt").read_text(), r"(?m)^coverage==\d+\.\d+\.\d+$")

    def test_nightly_workflow_runs_mutation_weekly_with_85_percent_threshold(self):
        nightly = (ROOT / ".github/workflows/nightly.yml").read_text(encoding="utf-8")
        self.assertRegex(nightly, r"cron:\s*\"[^\"]+ \* \* 1\"")
        self.assertIn("scripts/mutation.sh", nightly)
        self.assertIn("85", (ROOT / "scripts/mutation.sh").read_text(encoding="utf-8"))
        self.assertRegex((ROOT / "requirements-mutation.txt").read_text(), r"(?m)^mutmut==\d+\.\d+\.\d+$")

    def test_coverage_measures_the_runtime_and_tooling_packages(self):
        rc = (ROOT / ".coveragerc").read_text(encoding="utf-8")
        for package in ("harness_validator", "harness_cli", "harness/core"):
            self.assertIn(package, rc)
        self.assertTrue(re.search(r"branch\s*=\s*True", rc))


if __name__ == "__main__":
    unittest.main()
