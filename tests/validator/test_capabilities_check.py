"""Capability_Matrix validator checks (agent-harness-platform R9.1, R9.5)."""
# Validates: agent-harness-platform/R9.1, agent-harness-platform/R9.5
import copy
import datetime
import json
import unittest

from tests._support import ROOT  # noqa: F401
from harness_validator import capabilities_check

TEXT = (ROOT / "harness/capabilities.json").read_text(encoding="utf-8")


class CapabilitiesCheck(unittest.TestCase):
    def test_shipped_matrix_is_clean(self):
        self.assertEqual(capabilities_check.check_capabilities("c", TEXT, datetime.date(2026, 11, 30)), [])

    def test_missing_field_is_an_error(self):
        data = json.loads(TEXT)
        del data["agents"]["kiro"]["tool_map"]
        found = capabilities_check.check_capabilities("c", json.dumps(data))
        self.assertTrue(any(f.rule == "CAP-FIELD" and "tool_map" in f.field for f in found))

    def test_old_verification_warns(self):
        found = capabilities_check.check_capabilities("c", TEXT, datetime.date(2027, 8, 1))
        self.assertTrue(any(f.rule == "CAP-STALE" for f in found))

    def test_invalid_json_is_an_error(self):
        self.assertEqual(capabilities_check.check_capabilities("c", "{")[0].rule, "CAP-FIELD")


if __name__ == "__main__":
    unittest.main()
