# Feature: agent-harness-platform, Property 40: Decision_Log failures never change the Decision
# Validates: agent-harness-platform/R12.3
import json
import os
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import TemplateCopy
from tests.property.strategies_core import native_payloads
import guard_cli


class LogFailure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._copy = TemplateCopy()
        cls.root = cls._copy.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._copy.__exit__(None, None, None)

    @given(native_payloads())
    def test_unwritable_log_gives_the_same_exit_and_output(self, case):
        agent, trigger, raw = case
        harness_dir = self.root / ".harness"
        if harness_dir.is_dir():
            for f in harness_dir.iterdir():
                f.unlink()
            harness_dir.rmdir()
        baseline = guard_cli.run(agent, trigger, raw, self.root)  # logging off (test default)
        harness_dir.write_text("blocks the log directory")
        os.environ["HARNESS_DECISION_LOG"] = "1"
        try:
            code, out, err = guard_cli.run(agent, trigger, raw, self.root)
        finally:
            os.environ["HARNESS_DECISION_LOG"] = "0"
            harness_dir.unlink()
        self.assertEqual((code, out), baseline[:2])
        self.assertEqual(err.count("decision-log: could not write"), 1)
        self.assertEqual(err.replace(err[err.index("decision-log:"):], ""), baseline[2])


if __name__ == "__main__":
    unittest.main()
