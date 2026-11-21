"""Template hook rules (Requirements 3.1, 3.4, 10.5)."""
# Validates: kiro-agent-harness-template/R3.1, kiro-agent-harness-template/R3.4, kiro-agent-harness-template/R10.5

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests._support import detail
from harness_validator.hook_rules import check_hook_file, check_hook_id


def command_hook(command="sh scripts/check.sh", timeout=5, matcher="^(execute_bash)$"):
    return json.dumps(
        {
            "version": "v1",
            "hooks": [
                {
                    "name": "check",
                    "trigger": "PreToolUse",
                    "matcher": matcher,
                    "action": {"type": "command", "command": command},
                    "timeout": timeout,
                }
            ],
        }
    )


class HookRules(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        self.script = self.root / "scripts" / "check.sh"
        self.script.write_text("#!/bin/sh\nexit 0\n")
        os.chmod(self.script, 0o755)

    def tearDown(self):
        self._tmp.cleanup()

    def rules(self, text, path=".kiro/hooks/check.json"):
        return {(f.rule, f.field, f.severity.value) for f in check_hook_file(path, text, self.root)}

    def test_valid_hook_has_no_findings(self):
        self.assertEqual(self.rules(command_hook()), set())

    def test_missing_script_is_reported(self):
        self.script.unlink()
        findings = check_hook_file(".kiro/hooks/check.json", command_hook(), self.root)
        self.assertEqual([f.rule for f in findings], ["HOOK-SCRIPT"])
        self.assertIn(".kiro/hooks/check.json", findings[0].message)
        self.assertIn("scripts/check.sh", findings[0].message)

    def test_non_executable_script_is_reported(self):
        os.chmod(self.script, 0o644)
        self.assertIn(("HOOK-SCRIPT", "hooks[0].action.command", "error"), self.rules(command_hook()))

    def test_wildcard_matcher_is_a_warning(self):
        self.assertEqual(self.rules(command_hook(matcher="execute_.*")), {("HOOK-WILDCARD", "hooks[0].matcher", "warning")})

    def test_boolean_and_float_timeouts_are_rejected(self):
        for timeout in (True, 5.0, 0, 301, "5"):
            with self.subTest(timeout=timeout):
                self.assertIn(("HOOK-RULES", "hooks[0].timeout", "error"), self.rules(command_hook(timeout=timeout)))

    def test_hook_id_boundaries(self):
        cases = {
            "a": True,
            "quality-on-save": True,
            "a" * 64: True,
            "a" * 65: False,
            "-leading": False,
            "trailing-": False,
            "double--dash": False,
            "Upper": False,
            "under_score": False,
        }
        for stem, valid in cases.items():
            with self.subTest(stem=stem):
                actual = not check_hook_id(f".kiro/hooks/{stem}.json")
                self.assertEqual(actual, valid, detail(stem, valid, actual))

    def test_invalid_regex_matcher_is_reported(self):
        self.assertIn(("HOOK-RULES", "hooks[0].matcher", "error"), self.rules(command_hook(matcher="^(a")))

    def test_parse_error_skips_other_checks(self):
        findings = check_hook_file(".kiro/hooks/check.json", "{not json", self.root)
        self.assertEqual([f.rule for f in findings], ["HOOK-JSON"])


if __name__ == "__main__":
    unittest.main()
