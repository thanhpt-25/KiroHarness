"""MCP tool inventories and validator checks (agent-harness-platform R10.2 to R10.4, R10.6)."""
# Validates: agent-harness-platform/R10.2, agent-harness-platform/R10.3, agent-harness-platform/R10.4, agent-harness-platform/R10.6
import copy
import io
import json
import sys
import unittest

from tests._support import ROOT, TemplateCopy, errors, validate
from tests.generator._fixture import MANIFEST, SourceRoot, with_agents
from harness_cli import mcp_inventory

FAKE = [sys.executable, str(ROOT / "tests/fixtures/mcp/fake_server.py")]
ITEM = {"package": "fake", "version": "1.0.0", "args": [], "disabled": False, "auto_approve": ["read_x"]}


def fake_fetch(extra_env=None):
    def fetch(command, env=None, cwd=None, timeout=20):
        return mcp_inventory.fetch_tools(FAKE, env=extra_env, cwd=cwd, timeout=20)
    return fetch


class Inventory(unittest.TestCase):
    def test_hash_covers_name_description_and_schema(self):
        base = {"name": "a", "description": "d", "inputSchema": {"type": "object"}}
        self.assertEqual(mcp_inventory.tool_hash(base), mcp_inventory.tool_hash(dict(reversed(list(base.items())))))
        for field, value in (("name", "b"), ("description", "e"), ("inputSchema", {"type": "string"})):
            self.assertNotEqual(mcp_inventory.tool_hash(base), mcp_inventory.tool_hash(dict(base, **{field: value})))

    def test_write_then_check_then_detect_changes(self):
        with SourceRoot() as root:
            servers = {"fake": ITEM}
            out = io.StringIO()
            self.assertEqual(mcp_inventory.run(root, servers, None, False, out, fake_fetch()), 0)
            recorded = json.loads((root / "harness/mcp/fake.tools.json").read_text())
            self.assertEqual(sorted(recorded["tools"]), ["read_x", "write_x"])
            self.assertEqual(mcp_inventory.run(root, servers, None, True, io.StringIO(), fake_fetch()), 0)
            changed = json.dumps([{"name": "read_x", "description": "Changed", "inputSchema": {"type": "object"}},
                                  {"name": "new_tool", "description": "n", "inputSchema": {}}])
            out = io.StringIO()
            self.assertEqual(mcp_inventory.run(root, servers, None, True, out, fake_fetch({"FAKE_TOOLS": changed})), 1)
            self.assertIn("fake: tool changed: read_x", out.getvalue())
            self.assertIn("fake: tool added: new_tool", out.getvalue())
            self.assertIn("fake: tool removed: write_x", out.getvalue())

    def test_unstartable_server_is_reported(self):
        out = io.StringIO()
        def boom(command, env=None, cwd=None, timeout=1):
            raise FileNotFoundError("uvx")
        self.assertEqual(mcp_inventory.run("/nonexistent", {"fake": ITEM}, None, True, out, boom), 1)
        self.assertIn("could not list tools", out.getvalue())


class ValidatorChecks(unittest.TestCase):
    def test_auto_approve_outside_inventory_is_an_error(self):
        with TemplateCopy() as root:
            (root / "harness/mcp").mkdir()
            (root / "harness/mcp/git.tools.json").write_text(json.dumps({"server": "git", "version": "2026.11.18", "tools": {"git_status": "x"}}))
            found = [f for f in errors(validate(root)[0]) if f.rule == "MCP-INVENTORY"]
            self.assertTrue(any("git_log" in f.message for f in found), found)
            self.assertFalse(any("git_status" in f.message for f in found))

    def test_stale_inventory_version_is_an_error(self):
        with TemplateCopy() as root:
            (root / "harness/mcp").mkdir()
            (root / "harness/mcp/fetch.tools.json").write_text(json.dumps({"server": "fetch", "version": "0.0.1", "tools": {}}))
            self.assertTrue(any(f.rule == "MCP-INVENTORY" and f.field == "version" for f in errors(validate(root)[0])))

    def test_rendered_claude_mcp_file_is_checked_for_minimum_version(self):
        manifest = with_agents(claude_code=True)
        manifest = copy.deepcopy(manifest)
        manifest["mcp"]["git"]["version"] = "2025.1.1"
        with TemplateCopy() as root:
            (root / "harness/manifest.json").write_text(json.dumps(manifest, indent=2))
            from harness_cli.main import main

            main(["--root", str(root), "sync", "--force"], io.StringIO(), io.StringIO())
            found = [f for f in errors(validate(root)[0]) if f.path in (".mcp.json", ".kiro/settings/mcp.json") and f.rule.startswith("MCP-")]
            self.assertTrue({".mcp.json", ".kiro/settings/mcp.json"} <= {f.path for f in found}, found)

    def test_enabled_agent_without_a_matrix_entry_is_an_error(self):
        from harness_validator import generator_checks

        with SourceRoot(with_agents(claude_code=True)) as root:
            data = json.loads((root / "harness/capabilities.json").read_text())
            del data["agents"]["claude-code"]
            (root / "harness/capabilities.json").write_text(json.dumps(data))
            findings = generator_checks.check_generated(root)[0]
            self.assertTrue(any(f.rule == "CAP-MISSING" and "claude-code" in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
