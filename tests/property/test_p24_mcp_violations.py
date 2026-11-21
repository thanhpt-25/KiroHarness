# Feature: kiro-agent-harness-template, Property 24: Every MCP violation is reported
# Validates: kiro-agent-harness-template/R8.9, kiro-agent-harness-template/R10.7
import json
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property._mcp_helpers import CONFIG, PATH, entry
from tests import _support  # noqa: F401
from harness_validator import mcp
from harness_validator.report import render

SERVERS = ["s0", "s1", "s2", "s3", "s4"]
LITERAL = "plain-literal-value"


def violations():
    out = []
    for server in SERVERS:
        out += [
            (server, f"mcpServers.{server}.env.SERVICE_TOKEN", "MCP-SECRET-REF", lambda e: e.update(env={"SERVICE_TOKEN": LITERAL})),
            (server, f"mcpServers.{server}.args[0]", "MCP-PIN", lambda e: e.update(args=["some-mcp-server@latest"])),
            (server, f"mcpServers.{server}.args[0]", "MCP-PIN", lambda e: e.update(args=["some-mcp-server"])),
            (server, f"mcpServers.{server}.autoApprove[0]", "MCP-AUTOAPPROVE", lambda e: e.update(autoApprove=["git_commit"])),
            (server, f"mcpServers.{server}.disabled", "MCP-DISABLED", lambda e: e.pop("disabled")),
            (server, f"mcpServers.{server}.disabled", "MCP-DISABLED", lambda e: e.update(disabled="false")),
            (server, f"mcpServers.{server}.disabled", "MCP-DISABLED", lambda e: e.update(disabled=0)),
        ]
    return out


VIOLATIONS = violations()


@st.composite
def cases(draw):
    chosen = draw(st.lists(st.sampled_from(range(len(VIOLATIONS))), unique=True, max_size=5))
    used, applied = set(), []
    for index in chosen:
        server, field, rule, apply = VIOLATIONS[index]
        if server in used:
            continue
        used.add(server)
        applied.append(VIOLATIONS[index])
    return applied


class McpViolations(unittest.TestCase):
    @given(cases())
    def test_one_error_per_violation(self, applied):
        servers = {name: entry(autoApprove=["git_status"]) for name in SERVERS}
        for server, _, _, apply in applied:
            apply(servers[server])
        findings = mcp.check_mcp(PATH, json.dumps({"mcpServers": servers}), None, CONFIG)
        errors = [f for f in findings if f.severity.value == "error"]
        self.assertEqual(len(errors), len(applied), errors)
        self.assertEqual({(f.field, f.rule) for f in errors}, {(field, rule) for _, field, rule, _ in applied})
        self.assertTrue(all(f.path == PATH for f in errors))
        self.assertTrue(all(LITERAL not in f.message for f in errors))
        self.assertEqual(render(findings, 1)[1], 1 if applied else 0)


if __name__ == "__main__":
    unittest.main()
