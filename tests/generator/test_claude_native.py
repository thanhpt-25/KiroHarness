"""Claude Code native files: hooks, permissions, .mcp.json (agent-harness-platform R8.1 to R8.3, R10.1)."""
# Validates: agent-harness-platform/R8.1, agent-harness-platform/R8.2, agent-harness-platform/R8.3, agent-harness-platform/R10.1
import copy
import json
import subprocess
import unittest

from tests._support import ROOT, TemplateCopy
from tests.generator._fixture import MANIFEST, SourceRoot, run_cli, with_agents
from harness_cli import permissions

CLAUDE = with_agents(claude_code=True)


def generated(manifest=CLAUDE):
    with SourceRoot(manifest) as root:
        assert run_cli(root, "sync")[0] == 0
        return json.loads((root / ".claude/settings.json").read_text()), json.loads((root / ".mcp.json").read_text())


class ClaudeNative(unittest.TestCase):
    def test_hooks_cover_tools_prompt_session_and_stop(self):
        settings, _mcp = generated()
        hooks = settings["hooks"]
        self.assertEqual(sorted(hooks), ["PreToolUse", "SessionStart", "Stop", "UserPromptSubmit"])
        matcher = hooks["PreToolUse"][0]["matcher"]
        for tool in ("Bash", "PowerShell", "Write", "Edit", "Read", "WebFetch", "mcp__.*"):
            self.assertIn(tool, matcher)
        self.assertIn("guard claude-code pre_tool", hooks["PreToolUse"][0]["hooks"][0]["command"])
        self.assertNotIn("--only", hooks["PreToolUse"][0]["hooks"][0]["command"])
        self.assertIn("guard claude-code prompt_submit", hooks["UserPromptSubmit"][0]["hooks"][0]["command"])

    def test_disabled_guards_narrow_or_drop_hooks(self):
        manifest = copy.deepcopy(CLAUDE)
        manifest["guards"]["risky"]["enabled"] = False
        manifest["guards"]["protected_paths"]["enabled"] = False
        manifest["guards"]["prompt_secrets"]["enabled"] = False
        manifest["quality"]["stop_validate"] = False
        hooks = generated(manifest)[0]["hooks"]
        self.assertIn("--only destructive-command-guard", hooks["PreToolUse"][0]["hooks"][0]["command"])
        self.assertNotIn("UserPromptSubmit", hooks)
        self.assertNotIn("Stop", hooks)
        manifest["guards"]["destructive"]["enabled"] = False
        self.assertNotIn("PreToolUse", generated(manifest)[0]["hooks"])

    def test_every_static_policy_entry_is_a_permission_rule(self):
        settings, _ = generated()
        perms = settings["permissions"]
        for line in (ROOT / "harness/policy/destructive-commands.txt").read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "*" not in line:
                with self.subTest(deny=line):
                    self.assertIn(f"Bash({line} *)", perms["deny"])
        for rule in ("Bash(terraform apply *)", "Bash(npm publish *)", "Bash(rm *)", "PowerShell(Remove-Item *)",
                     "mcp__git__git_reset", "mcp__git__git_commit", "mcp__git__git_checkout"):
            self.assertIn(rule, perms["ask"])
        self.assertIn("mcp__git__git_status", perms["allow"])
        self.assertNotIn("mcp__git__git_reset", perms["allow"])

    def test_policy_entries_without_a_static_form_are_reported_not_dropped(self):
        with SourceRoot(CLAUDE) as root:
            _code, _out, err = run_cli(root, "sync", "--check")
        self.assertIn("rm -rf *", err)
        self.assertIn("host-not-in", err)

    def test_static_prefix_extraction(self):
        self.assertEqual(permissions.static_prefixes(r"(?i)\b(helm (install|upgrade)|npm publish)\b"), ["helm install", "helm upgrade", "npm publish"])
        self.assertEqual(permissions.static_prefixes(r"(?i)(^|[;&|\s])rm\s"), ["rm"])
        self.assertEqual(permissions.static_prefixes(r"foo.*bar"), [])

    def test_mcp_json_keeps_pins_and_secret_references_of_the_kiro_config(self):
        _settings, mcp = generated()
        kiro = json.loads((ROOT / ".kiro/settings/mcp.json").read_text())["mcpServers"]
        self.assertEqual(sorted(mcp["mcpServers"]), sorted(kiro))
        for name, server in mcp["mcpServers"].items():
            self.assertEqual(server["args"], kiro[name]["args"])
            self.assertEqual(server.get("env"), kiro[name].get("env"))
            self.assertEqual(server["command"], kiro[name]["command"])

    def test_disabled_server_is_listed_in_settings(self):
        manifest = copy.deepcopy(CLAUDE)
        manifest["mcp"]["fetch"]["disabled"] = True
        settings, mcp = generated(manifest)
        self.assertEqual(settings["disabledMcpjsonServers"], ["fetch"])
        self.assertIn("fetch", mcp["mcpServers"])


class ClaudeScripts(unittest.TestCase):
    def test_stop_validate_blocks_with_output_when_validation_fails_and_never_loops(self):
        with TemplateCopy() as root:
            (root / "scripts/validate.sh").write_text("echo 'FAILED: boom'\nexit 1\n")
            run = lambda stdin: subprocess.run(["sh", str(root / "harness/bin/stop-validate")], input=stdin, capture_output=True, cwd=root)
            result = run(b'{"hook_event_name":"Stop","stop_hook_active":false}')
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"FAILED: boom", result.stderr)
            self.assertEqual(run(b'{"hook_event_name":"Stop","stop_hook_active": true}').returncode, 0)
            (root / "scripts/validate.sh").write_text("exit 0\n")
            self.assertEqual(run(b"{}").returncode, 0)

    def test_session_start_prints_git_context(self):
        result = subprocess.run(["sh", str(ROOT / "harness/bin/session-start")], input=b"{}", capture_output=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
