# Feature: kiro-agent-harness-template, Property 22: autoApprove classification
import re
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property._mcp_helpers import CONFIG, check, entry

VERBS = re.compile(r"(?i)(write|create|delete|remove|commit|add|reset|checkout|push|exec|run|shell|move|rename)")
tools = st.one_of(
    st.sampled_from(sorted(CONFIG.read_only_allowlist)),
    st.sampled_from(sorted(CONFIG.known_mutating_tools)),
    st.sampled_from(["write_file", "delete_item", "run_query", "list_tables", "describe", "get_page", "fetch"]),
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=12),
)


class AutoApprove(unittest.TestCase):
    @given(tools)
    def test_classification(self, tool):
        findings = [f for f in check({"srv": entry(autoApprove=[tool])}) if f.rule.startswith("MCP-AUTOAPPROVE")]
        if tool in CONFIG.read_only_allowlist:
            self.assertEqual(findings, [])
        elif tool in CONFIG.known_mutating_tools or VERBS.search(tool):
            self.assertEqual([(f.rule, f.severity.value) for f in findings], [("MCP-AUTOAPPROVE", "error")])
        else:
            self.assertEqual([(f.rule, f.severity.value) for f in findings], [("MCP-AUTOAPPROVE-UNKNOWN", "warning")])
            self.assertIn('"srv"', findings[0].message)
            self.assertIn(tool, findings[0].message)


if __name__ == "__main__":
    unittest.main()
