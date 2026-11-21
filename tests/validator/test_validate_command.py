"""Validation_Command behavior (Requirements 11.5, 11.6, 11.7)."""

import re
import unittest

from tests._support import TemplateCopy, run_script

FAILING_SUITE = '''
import unittest
from tests._support import detail


class Fixture(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(True)

    def test_fails(self):
        self.assertEqual(1 + 1, 3, detail("1 + 1", 3, 1 + 1))

    def test_also_passes_after_the_failure(self):
        self.assertTrue(True)
'''

PASSING_SUITE = '''
import unittest


class Fixture(unittest.TestCase):
    def test_passes(self):
        self.assertTrue(True)
'''


def run_validate(root, suite_text):
    suite = root / "tests" / "fixture_suite"
    suite.mkdir()
    (suite / "__init__.py").write_text("")
    (suite / "test_fixture.py").write_text(suite_text)
    return run_script(
        root / "scripts" / "validate.sh",
        env={"HARNESS_TEST_DIRS": "tests/fixture_suite"},
        cwd=root,
        timeout=120,
    )


class ValidationCommand(unittest.TestCase):
    def test_failures_and_validator_errors_are_reported_and_every_test_runs(self):
        with TemplateCopy() as root:
            (root / ".kiro/hooks/bad-hook.json").write_text('{"version": "v2", "hooks": []}')
            result = run_validate(root, FAILING_SUITE)
            out = result.stdout.decode()
            self.assertNotEqual(result.returncode, 0, out)
            self.assertIn("Tests: 2 passed, 1 failed", out)
            self.assertIn("FAIL: tests.fixture_suite.test_fixture.Fixture.test_fails", out)
            self.assertIn("input: '1 + 1'", out)
            self.assertIn("expected: 3", out)
            self.assertIn("actual: 2", out)
            self.assertRegex(out, r"ERROR\s+\.kiro/hooks/bad-hook\.json\s+version\s+\[HOOK-SCHEMA\]")

    def test_clean_run_exits_0_with_summary(self):
        with TemplateCopy() as root:
            result = run_validate(root, PASSING_SUITE)
            out = result.stdout.decode()
            self.assertEqual(result.returncode, 0, out)
            self.assertRegex(out, r"Validation: \d+ files checked, \d+ warnings; Tests: 1 passed, 0 failed")
            match = re.search(r"Summary: (\d+) files checked, 0 errors", out)
            self.assertIsNotNone(match, out)


if __name__ == "__main__":
    unittest.main()
