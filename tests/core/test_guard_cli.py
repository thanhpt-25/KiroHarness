"""The combined guard entry point through the real wrapper, for each Agent (Requirements 4.3 to 4.7, 5.3)."""
# Validates: agent-harness-platform/R4.3, agent-harness-platform/R4.4, agent-harness-platform/R4.7, agent-harness-platform/R5.1, agent-harness-platform/R5.3, agent-harness-platform/R5.5

import json
import os
import unittest

from tests._support import ROOT, TemplateCopy, detail, run_script

import adapters  # noqa: E402
import risky_guard  # noqa: E402
from capabilities import load_capabilities  # noqa: E402

GUARD = ROOT / "harness" / "bin" / "guard"


def guard(agent, trigger, payload, root=None, env=None):
    import subprocess

    script = (root or ROOT) / "harness" / "bin" / "guard"
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    done = subprocess.run(["sh", str(script), agent, trigger], input=data, capture_output=True, cwd=str(root or ROOT), timeout=30,
                          env={**os.environ, **(env or {})})
    return done.returncode, done.stdout.decode(), done.stderr.decode()


def native(agent, tool_id, tool_input):
    caps = load_capabilities()
    adapter = adapters.Adapter(agent, caps["agents"][agent])
    event = adapters.HarnessEvent(agent=agent, trigger="pre_tool", tool_id=tool_id, tool_input=tool_input)
    return adapter.build_native_payload(event)


SHELL = {"kiro": "execute_bash", "claude-code": "Bash"}


class CombinedGuard(unittest.TestCase):
    def test_destructive_command_is_denied_for_every_agent(self):
        for agent, tool in SHELL.items():
            code, out, err = guard(agent, "pre_tool", native(agent, tool, {"command": "git push --force origin main"}))
            self.assertEqual((code, out), (2, ""), detail(agent, "deny", (code, out, err)))
            self.assertIn("destructive-command-guard: blocked", err)

    def test_risky_command_asks_for_every_agent(self):
        for agent, tool in SHELL.items():
            code, out, _err = guard(agent, "pre_tool", native(agent, tool, {"command": "terraform apply"}))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask", detail(agent, "ask", out))

    def test_safe_command_is_allowed_with_no_output(self):
        for agent, tool in SHELL.items():
            self.assertEqual(guard(agent, "pre_tool", native(agent, tool, {"command": "ls -la"})), (0, "", ""))

    def test_every_policy_entry_example_asks_for_every_agent_it_applies_to(self):
        caps = load_capabilities()
        entries = risky_guard.parse_list((ROOT / "harness/policy/risky-tools.conf").read_text())
        lines = (ROOT / "harness/policy/risky-tools.conf").read_text().splitlines()
        checked = set()
        for entry in entries:
            example = json.loads(lines[entry.line_no - 2].split("# example:", 1)[1])
            for agent in [a for a, e in caps["agents"].items() if e.get("hooks", True)]:
                subject = risky_guard.example_subject(entry, caps, agent=agent)
                if subject is None:
                    continue
                code, out, _ = guard(agent, "pre_tool", native(agent, subject[1], example))
                # Shell deletion examples such as "rm build/output.log" are also on the destructive list? They are not.
                self.assertEqual(code, 0, detail((agent, entry.line), "exit 0", code))
                self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask", detail((agent, entry.line), "ask", out))
                checked.add(agent)
        self.assertEqual(checked, {a for a, e in caps["agents"].items() if e.get("hooks", True)})

    def test_malformed_input_applies_failure_semantics(self):
        for agent in SHELL:
            for raw in (b"", b"not json", b"[]"):
                code, out, err = guard(agent, "pre_tool", raw)
                # destructive denies (exit 2) and wins over the risky guard's ask
                self.assertEqual((code, out), (2, ""), detail((agent, raw), "exit 2", (code, out, err)))

    def test_missing_policy_files_fail_safe(self):
        with TemplateCopy() as root:
            (root / "harness/policy/destructive-commands.txt").unlink()
            code, _out, err = guard("claude-code", "pre_tool", native("claude-code", "Bash", {"command": "ls"}), root)
            self.assertEqual(code, 2)
            self.assertIn("destructive-command-guard", err)
        with TemplateCopy() as root:
            (root / "harness/policy/risky-tools.conf").write_text("broken\n")
            code, out, _err = guard("claude-code", "pre_tool", native("claude-code", "Bash", {"command": "ls"}), root)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_unknown_agent_blocks(self):
        code, _out, err = guard("nonesuch", "pre_tool", b"{}")
        self.assertEqual(code, 2)
        self.assertIn("nonesuch", err)

    def test_prompt_secret_is_denied_and_clean_prompt_allowed(self):
        secret = "AKIA" + "ABCDEFGHIJKLMNOP"
        for agent in SHELL:
            event = "UserPromptSubmit"
            code, _out, err = guard(agent, "prompt_submit", {"hook_event_name": event, "prompt": f"use {secret}"})
            self.assertEqual(code, 2)
            self.assertNotIn(secret, err)
            self.assertEqual(guard(agent, "prompt_submit", {"hook_event_name": event, "prompt": "hello"}), (0, "", ""))

    def test_kiro_combined_path_agrees_with_the_existing_wrappers(self):
        wrappers = ROOT / ".kiro/hooks/scripts"
        cases = [("execute_bash", {"command": "git push --force"}), ("execute_bash", {"command": "ls"}),
                 ("delete_file", {"targetFile": "a"}), ("web_fetch", {"url": "https://example.com"}),
                 ("control_bash_process", {"action": "stop", "terminalId": "1"})]
        from tests._support import tool_call

        for tool, tool_input in cases:
            old_destructive = run_script(wrappers / "destructive-guard.sh", tool_call(tool, tool_input)).returncode if tool.startswith(("execute", "control")) else 0
            old_risky = run_script(wrappers / "risky-tool-guard.sh", tool_call(tool, tool_input)).stdout.decode().strip()
            code, out, _ = guard("kiro", "pre_tool", native("kiro", tool, tool_input))
            if old_destructive == 2:
                self.assertEqual(code, 2, detail((tool, tool_input), "deny", code))
            elif old_risky:
                self.assertEqual((code, json.loads(out)["hookSpecificOutput"]["permissionDecision"]), (0, "ask"), detail((tool, tool_input), "ask", out))
            else:
                self.assertEqual((code, out), (0, ""), detail((tool, tool_input), "allow", (code, out)))


if __name__ == "__main__":
    unittest.main()
