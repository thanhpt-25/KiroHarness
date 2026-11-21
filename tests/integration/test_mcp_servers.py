"""MCP server integration checks (Requirements 8.1, 8.5, 8.8).

Skipped unless HARNESS_INTEGRATION=1. Starts each pinned server through uvx
(network access needed on first run), lists its tools, and checks that every
autoApprove name exists. For the git server it calls git_status and checks the
repository it reports.
"""

import json
import os
import shutil
import subprocess
import unittest

from tests._support import ROOT

ENABLED = os.environ.get("HARNESS_INTEGRATION") == "1"
TIMEOUT = 120


class McpSession:
    def __init__(self, entry):
        env = dict(os.environ, **{k: v for k, v in entry.get("env", {}).items() if "${" not in v})
        self.proc = subprocess.Popen(
            [entry["command"], *entry["args"]],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=str(ROOT), env=env, text=True,
        )
        self.next_id = 0

    def request(self, method, params=None):
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"server closed the connection during {method}")
            message = json.loads(line)
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]

    def _send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def start(self):
        self.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                    "clientInfo": {"name": "harness-tests", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def close(self):
        self.proc.kill()
        self.proc.wait(timeout=10)


@unittest.skipUnless(ENABLED, "set HARNESS_INTEGRATION=1 to run MCP integration checks")
@unittest.skipIf(shutil.which("uvx") is None, "uvx is not installed")
class McpServers(unittest.TestCase):
    servers = json.loads((ROOT / ".kiro/settings/mcp.json").read_text())["mcpServers"] if ENABLED else {}

    def open(self, name):
        session = McpSession(self.servers[name]).start()
        self.addCleanup(session.close)
        return session

    def test_auto_approved_tools_exist(self):
        for name, entry in self.servers.items():
            if entry.get("disabled"):
                continue
            with self.subTest(server=name):
                tools = {t["name"] for t in self.open(name).request("tools/list")["tools"]}
                self.assertTrue(tools)
                self.assertEqual(set(entry.get("autoApprove", [])) - tools, set())

    def test_git_server_reports_the_workspace_repository(self):
        if not (ROOT / ".git").exists():
            self.skipTest("the Template is not a git repository")
        result = self.open("git").request("tools/call", {"name": "git_status", "arguments": {"repo_path": "."}})
        self.assertFalse(result.get("isError"), result)
        outside = self.open("git").request("tools/call", {"name": "git_status", "arguments": {"repo_path": "/"}})
        self.assertTrue(outside.get("isError") or "outside" in json.dumps(outside).lower(), outside)


if __name__ == "__main__":
    unittest.main()
