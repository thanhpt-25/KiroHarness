"""Decision_Log (agent-harness-platform R12.1 to R12.5, R11.4)."""
# Validates: agent-harness-platform/R12.1, agent-harness-platform/R12.2, agent-harness-platform/R12.3, agent-harness-platform/R12.4, agent-harness-platform/R12.5
import io
import json
import os
import unittest

from tests._support import ROOT, TemplateCopy
from tests.core.test_guard_cli import guard, native

import decision_log
import guard_cli
from event_model import Decision, HarnessEvent
from prompt_scan import load_patterns

ON = {"HARNESS_DECISION_LOG": "1"}
PATTERNS = load_patterns(ROOT / "scripts/validator-config.json")


def records(root):
    return decision_log.read_records(root)


class Logging(unittest.TestCase):
    def test_one_record_per_guard_decision_with_the_required_fields(self):
        with TemplateCopy() as root:
            code, _out, _err = guard("claude-code", "pre_tool", native("claude-code", "Bash", {"command": "git push --force origin main"}), root, ON)
            self.assertEqual(code, 2)
            found = records(root)
            self.assertEqual([r["guard"] for r in found], ["destructive-command-guard", "protected-path-guard", "risky-tool-guard"])
            first = found[0]
            self.assertEqual((first["agent"], first["trigger"], first["category"], first["tool"], first["decision"]),
                             ("claude-code", "pre_tool", "shell", "Bash", "deny"))
            self.assertEqual(first["matched"], "git push --force")
            self.assertEqual(first["summary"], "git push --force origin main")
            self.assertRegex(first["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_log_is_git_ignored(self):
        self.assertIn(".harness/", (ROOT / ".gitignore").read_text().splitlines())

    def test_secrets_are_masked_and_long_summaries_truncated(self):
        secret = "github_pat_" + "0" * 60
        with TemplateCopy() as root:
            guard("kiro", "pre_tool", native("kiro", "execute_bash", {"command": f"echo {secret} " + "x" * 400}), root, ON)
            text = (root / ".harness/decisions.jsonl").read_text()
            self.assertNotIn(secret, text)
            self.assertIn("gith" + "*" * 56, text)
            self.assertTrue(all(len(r["summary"]) <= 200 for r in records(root)))

    def test_prompt_text_is_never_logged(self):
        with TemplateCopy() as root:
            payload = {"hook_event_name": "UserPromptSubmit", "prompt": "plain private prompt text"}
            guard("claude-code", "prompt_submit", payload, root, ON)
            self.assertNotIn("private prompt", (root / ".harness/decisions.jsonl").read_text())

    def test_opt_out_writes_nothing(self):
        event = HarnessEvent(agent="kiro", trigger="pre_tool", tool_id="x", category="other")
        with TemplateCopy() as root:
            decision_log.record_decisions(root, event, [Decision("allow", "g")], PATTERNS, io.StringIO(), env={"HARNESS_DECISION_LOG": "0"})
            self.assertFalse((root / ".harness").exists())

    def test_rotation_keeps_at_most_three_files(self):
        with TemplateCopy() as root:
            event = HarnessEvent(agent="kiro", trigger="pre_tool", tool_id="x", category="other")
            for n in range(6):
                decision_log.append(root, [decision_log.build_record(event, Decision("allow", f"g{n}"), PATTERNS)], max_bytes=10)
            names = sorted(p.name for p in (root / ".harness").iterdir())
            self.assertEqual(names, ["decisions.jsonl", "decisions.jsonl.1", "decisions.jsonl.2", "decisions.jsonl.3"])
            self.assertEqual(json.loads((root / ".harness/decisions.jsonl").read_text())["guard"], "g5")

    def test_unwritable_log_warns_once_and_keeps_the_decision(self):
        with TemplateCopy() as root:
            (root / ".harness").write_text("a file where the directory should be")
            code, out, err = guard("claude-code", "pre_tool", native("claude-code", "Bash", {"command": "git push --force x"}), root, ON)
            self.assertEqual((code, out), (2, ""))
            self.assertEqual(err.count("decision-log: could not write"), 1)
            self.assertIn("destructive-command-guard: blocked", err)

    def test_summary_counts_and_top_entries(self):
        recs = [{"guard": "g", "decision": "deny", "matched": "m1"}] * 3 + [{"guard": "g", "decision": "allow", "matched": ""}, {"guard": "h", "decision": "ask", "matched": "m2"}]
        text = decision_log.summarize(recs)
        self.assertIn("g: allow 1, deny 3", text)
        self.assertIn("h: ask 1", text)
        self.assertIn("    3  g: m1", text)
        self.assertIn("Decisions: 5", text)

    def test_log_summary_command(self):
        from tests.generator._fixture import run_cli

        with TemplateCopy() as root:
            guard("kiro", "pre_tool", native("kiro", "execute_bash", {"command": "git push --force x"}), root, ON)
            code, out, _err = run_cli(root, "log", "--summary")
            self.assertEqual(code, 0)
            self.assertIn("destructive-command-guard: deny 1", out)


if __name__ == "__main__":
    unittest.main()
