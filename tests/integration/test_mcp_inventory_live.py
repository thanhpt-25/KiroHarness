"""Live MCP tools must match the recorded inventories (agent-harness-platform R10.3).

Skipped unless HARNESS_INTEGRATION=1. Starts each server that has a recorded
inventory through uvx (network access needed) and fails, naming the server and
tool, when a tool was added, removed or changed. Never run on fork PRs.
"""
# Validates: agent-harness-platform/R10.3
import io
import json
import os
import unittest

from tests._support import ROOT

from harness_cli import mcp_inventory

ENABLED = os.environ.get("HARNESS_INTEGRATION") == "1"


@unittest.skipUnless(ENABLED, "set HARNESS_INTEGRATION=1 to run MCP integration checks")
class LiveInventory(unittest.TestCase):
    def test_live_tools_match_the_recorded_inventory(self):
        servers = json.loads((ROOT / "harness/manifest.json").read_text())["mcp"]
        recorded = {name: item for name, item in servers.items() if (ROOT / mcp_inventory.inventory_path(name)).is_file()}
        self.assertTrue(recorded, "no inventories recorded; run scripts/harness mcp-inventory first")
        out = io.StringIO()
        status = mcp_inventory.run(ROOT, recorded, None, True, out)
        self.assertEqual(status, 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()
