"""Harness_Event, Decision, and Adapter behavior (agent-harness-platform Requirement 4)."""
# Validates: agent-harness-platform/R4.1, agent-harness-platform/R4.2, agent-harness-platform/R4.3, agent-harness-platform/R4.4, agent-harness-platform/R4.5, agent-harness-platform/R4.7

import json
import unittest

from tests._support import detail

import adapters  # noqa: E402
import event_model  # noqa: E402
from event_model import Decision, HarnessEvent, combine  # noqa: E402


def decode(agent, trigger, payload):
    return adapters.get_adapter(agent).decode(json.dumps(payload).encode(), trigger)


class EventModel(unittest.TestCase):
    def test_unknown_trigger_and_category_are_rejected(self):
        with self.assertRaises(ValueError):
            HarnessEvent(agent="kiro", trigger="nope")
        with self.assertRaises(ValueError):
            HarnessEvent(agent="kiro", trigger="pre_tool", category="nope")
        with self.assertRaises(ValueError):
            Decision("maybe", "g")

    def test_combine_first_deny_then_first_ask_then_allow(self):
        a, b = Decision("ask", "risky", "r"), Decision("deny", "destructive", "d")
        self.assertIs(combine([a, b]), b)
        self.assertIs(combine([a, Decision("allow", "x")]), a)
        self.assertEqual(combine([Decision("allow", "x")]).kind, "allow")
        self.assertEqual(combine([]).kind, "allow")


class Decode(unittest.TestCase):
    def test_kiro_shell_payload(self):
        event = decode("kiro", "pre_tool", {"hook_event_name": "PreToolUse", "cwd": "/w", "tool_name": "execute_bash",
                                            "tool_input": {"command": "ls"}})
        self.assertEqual((event.category, event.command, event.tool_id), ("shell", "ls", "execute_bash"))

    def test_kiro_camel_case_payload_is_accepted(self):
        event = decode("kiro", "pre_tool", {"toolName": "delete_file", "toolArgs": {"targetFile": "a.py"}})
        self.assertEqual((event.category, event.paths), ("delete", ("a.py",)))

    def test_claude_code_tools_map_to_categories(self):
        cases = {
            "Bash": ({"command": "ls"}, "shell"),
            "Read": ({"file_path": "/w/a"}, "read"),
            "Write": ({"file_path": "/w/a", "content": "x"}, "write"),
            "WebFetch": ({"url": "https://x.dev", "prompt": "p"}, "web"),
            "mcp__git__git_status": ({}, "mcp"),
        }
        for tool, (tool_input, category) in cases.items():
            event = decode("claude-code", "pre_tool", {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})
            self.assertEqual(event.category, category, detail(tool, category, event.category))

    def test_unmapped_tool_is_other_and_keeps_its_input(self):
        event = decode("claude-code", "pre_tool", {"hook_event_name": "PreToolUse", "tool_name": "NewTool", "tool_input": {"command": "x"}})
        self.assertEqual(event.category, "other")
        self.assertEqual(event.tool_input, {"command": "x"})

    def test_prompt_event(self):
        event = decode("claude-code", "prompt_submit", {"hook_event_name": "UserPromptSubmit", "prompt": "hello"})
        self.assertEqual((event.prompt, event.tool_id, event.category), ("hello", None, None))

    def test_wrong_event_name_and_bad_input_raise_decode_error(self):
        adapter = adapters.get_adapter("claude-code")
        for raw in (b"", b"not json", b"[]", json.dumps({"hook_event_name": "UserPromptSubmit"}).encode()):
            with self.assertRaises(adapters.DecodeError, msg=raw):
                adapter.decode(raw, "pre_tool")
        with self.assertRaises(adapters.DecodeError):
            adapter.decode(b"x" * (adapters.MAX_INPUT_BYTES + 1), "pre_tool")


class Encode(unittest.TestCase):
    def test_kiro_and_claude_code_ask_formats(self):
        ask = Decision("ask", "risky-tool-guard", "why")
        kiro = adapters.get_adapter("kiro").encode(ask, "pre_tool")
        claude = adapters.get_adapter("claude-code").encode(ask, "pre_tool")
        self.assertEqual(json.loads(kiro.stdout), {"hookSpecificOutput": {"permissionDecision": "ask", "permissionDecisionReason": "why"}})
        self.assertEqual(json.loads(claude.stdout)["hookSpecificOutput"],
                         {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "why"})
        self.assertEqual((kiro.exit_code, claude.exit_code), (0, 0))

    def test_deny_exits_2_with_the_guard_name_on_stderr_and_allow_is_silent(self):
        for agent in ("kiro", "claude-code"):
            adapter = adapters.get_adapter(agent)
            denied = adapter.encode(Decision("deny", "g", "because"), "pre_tool")
            self.assertEqual((denied.exit_code, denied.stdout, denied.stderr), (2, "", "g: because\n"))
            self.assertEqual(adapter.encode(Decision("allow", "g"), "pre_tool"), adapters.Output(0))

    def test_failure_decisions_follow_guard_semantics(self):
        adapter = adapters.get_adapter("kiro")
        self.assertEqual(adapter.failure("destructive-command-guard", "x").kind, "deny")
        self.assertEqual(adapter.failure("prompt-secret-scan", "x").kind, "deny")
        self.assertEqual(adapter.failure("risky-tool-guard", "x").kind, "ask")
        self.assertEqual(adapter.failure("some-new-guard", "x").kind, "ask")


if __name__ == "__main__":
    unittest.main()
