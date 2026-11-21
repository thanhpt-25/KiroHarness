"""Risky_Tool_Guard tests (Requirements 5.2 to 5.8, 11.3, 11.4, 11.8).

Matching calls come from the "# example:" comment above each entry in
risky-tools.conf, read at run time.
"""
# Validates: kiro-agent-harness-template/R5.2, kiro-agent-harness-template/R5.3, kiro-agent-harness-template/R5.4, kiro-agent-harness-template/R5.5, kiro-agent-harness-template/R5.6, kiro-agent-harness-template/R5.7, kiro-agent-harness-template/R5.8, kiro-agent-harness-template/R11.3, kiro-agent-harness-template/R11.4, kiro-agent-harness-template/R11.8

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._support import HOOK_SCRIPTS, POLICY, TemplateCopy, detail, run_script, tool_call

import capabilities  # noqa: E402
import risky_guard  # noqa: E402

SCRIPT = HOOK_SCRIPTS / "risky-tool-guard.sh"
LIST = POLICY / "risky-tools.conf"

NON_MATCHING = [
    ("read_file", {"path": "README.md"}),
    ("execute_bash", {"command": "git status"}),
    ("web_fetch", {"url": "https://docs.aws.amazon.com/lambda/"}),
    ("web_fetch", {"url": "https://api.github.com/repos"}),
    ("fs_write", {"path": "src/app.py", "text": "x"}),
    ("execute_pwsh", {"command": "Get-ChildItem"}),
]


def example_cases(path=LIST):
    """Return ``[(tool, tool_input, entry line), ...]`` from the list's example comments."""
    cases, example = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("# example:"):
            example = json.loads(line[len("# example:"):])
            continue
        if not line or line.startswith("#"):
            continue
        tool = line.split(" | ", 1)[0].strip()
        cases.append((tool, example, line))
        example = None
    return cases


def decision(stdout: bytes):
    text = stdout.decode().strip()
    if not text:
        return None
    return json.loads(text)["hookSpecificOutput"]


class RiskyGuard(unittest.TestCase):
    def test_every_entry_asks_for_its_example(self):
        cases = example_cases()
        self.assertGreater(len(cases), 0)
        caps = capabilities.load_capabilities()
        ran = 0
        for tool, tool_input, line in cases:
            with self.subTest(entry=line):
                self.assertIsNotNone(tool_input, f"entry {line!r} has no # example: comment")
                entry = risky_guard.parse_list(line)[0]
                subject = risky_guard.example_subject(entry, caps, agent="kiro")
                if subject is None:
                    continue  # applies to another Agent only; tests/adapters covers it
                ran += 1
                result = run_script(SCRIPT, tool_call(subject[1], tool_input))
                self.assertEqual(result.returncode, 0)
                output = decision(result.stdout)
                self.assertIsNotNone(output, detail((tool, tool_input), "ask", "no output"))
                self.assertEqual(output["permissionDecision"], "ask")
                self.assertIn(tool, output["permissionDecisionReason"])
        self.assertGreaterEqual(ran, 5)

    def test_matched_entry_line_is_in_the_reason(self):
        result = run_script(SCRIPT, tool_call("delete_file", {"targetFile": "a.txt"}))
        self.assertIn("category:delete | File deletion | *", decision(result.stdout)["permissionDecisionReason"])

    def test_non_matching_calls_produce_no_decision(self):
        self.assertGreaterEqual(len(NON_MATCHING), 5)
        for tool, tool_input in NON_MATCHING:
            with self.subTest(tool=tool, tool_input=tool_input):
                result = run_script(SCRIPT, tool_call(tool, tool_input))
                self.assertEqual(result.returncode, 0)
                self.assertNotIn(b'"ask"', result.stdout, detail((tool, tool_input), "no ask", result.stdout))

    def test_empty_and_invalid_stdin_ask(self):
        for stdin in (b"", b"not json", b'{"tool_input": {}}'):
            with self.subTest(stdin=stdin):
                result = run_script(SCRIPT, stdin)
                self.assertEqual(result.returncode, 0)
                output = decision(result.stdout)
                self.assertEqual(output["permissionDecision"], "ask", detail(stdin, "ask", output))
                self.assertIn("could not be parsed", output["permissionDecisionReason"])
                self.assertIn("parse error", result.stderr.decode())

    def test_malformed_list_asks_and_names_the_file(self):
        with TemplateCopy() as root:
            conf = root / "harness/policy/risky-tools.conf"
            conf.write_text("delete_file has no separators\n")
            result = run_script(root / ".kiro/hooks/scripts/risky-tool-guard.sh", tool_call("read_file", {"path": "a"}), cwd=root)
            self.assertEqual(result.returncode, 0)
            output = decision(result.stdout)
            self.assertEqual(output["permissionDecision"], "ask")
            self.assertIn(str(conf), output["permissionDecisionReason"])
            self.assertIn(str(conf), result.stderr.decode())

    def test_extra_entry_adds_one_generated_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risky-tools.conf"
            text = LIST.read_text(encoding="utf-8")
            path.write_text(text + '\n# example: {"name": "x"}\nmy_tool | Test entry | *\n', encoding="utf-8")
            self.assertEqual(len(example_cases(path)), len(example_cases()) + 1)

    def test_each_check_finishes_within_2_seconds(self):
        start = time.monotonic()
        run_script(SCRIPT, tool_call("web_fetch", {"url": "https://example.com/" + "a" * 5000}))
        self.assertLess(time.monotonic() - start, 2.0)


if __name__ == "__main__":
    unittest.main()
