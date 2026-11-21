"""Reference pages match ``--help`` and executable doc examples (agent-harness-platform R16.3, R16.4)."""
# Validates: agent-harness-platform/R16.3, agent-harness-platform/R16.4
import io
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._support import ROOT, TemplateCopy

from harness_cli import main as cli  # noqa: E402

CLI_PAGE = (ROOT / "docs/reference/cli.md").read_text(encoding="utf-8")
FENCE_RE = re.compile(r"^```(\S*)([^\n]*)\n(.*?)^```\s*$", re.M | re.S)
EXAMPLE_KINDS = {"destructive-entry", "manifest-agents"}


def subcommands():
    parser = cli.build_parser()
    action = next(a for a in parser._actions if a.dest == "command")
    return action.choices


def section(command):
    match = re.search(rf"^### harness {re.escape(command)}\n(.*?)(?=^#{{1,3}} |\Z)", CLI_PAGE, re.M | re.S)
    return match.group(1) if match else None


class HelpParity(unittest.TestCase):
    def test_every_command_has_a_section_listing_exactly_its_options(self):
        for name, sub in subcommands().items():
            with self.subTest(command=name):
                text = section(name)
                self.assertIsNotNone(text, f"docs/reference/cli.md has no '### harness {name}' section")
                documented = set(re.findall(r"`(--[a-z][a-z-]*)`", text))
                actual = {o for a in sub._actions for o in a.option_strings if o.startswith("--") and o != "--help"}
                self.assertEqual(documented, actual)
                for option in actual:
                    self.assertIn(option, sub.format_help())

    def test_every_script_is_listed_in_the_reference(self):
        for script in sorted((ROOT / "scripts").glob("*.sh")):
            self.assertIn(f"scripts/{script.name}", CLI_PAGE, script.name)

    def test_real_help_output_names_every_command(self):
        result = subprocess.run([str(ROOT / "scripts/harness"), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        for name in subcommands():
            self.assertIn(name, result.stdout)


def examples():
    for path in sorted((ROOT / "docs").rglob("*.md")):
        for match in FENCE_RE.finditer(path.read_text(encoding="utf-8")):
            attrs = dict(re.findall(r"(\w[\w-]*)=(\S+)", match.group(2)))
            if attrs.get("example") in EXAMPLE_KINDS:
                yield path.relative_to(ROOT).as_posix(), attrs, match.group(3).strip()


def guard(root, command):
    payload = {"hook_event_name": "PreToolUse", "tool_name": "execute_bash", "tool_input": {"command": command}}
    return subprocess.run([str(root / "harness/bin/guard"), "kiro", "pre_tool"], input=json.dumps(payload).encode(),
                          capture_output=True, cwd=root).returncode


class ExecutableExamples(unittest.TestCase):
    def test_reference_docs_carry_examples_of_each_kind(self):
        self.assertEqual({a["example"] for _p, a, _b in examples()}, EXAMPLE_KINDS)

    def test_destructive_entry_blocks_the_command_it_names(self):
        for doc, attrs, body in (e for e in examples() if e[1]["example"] == "destructive-entry"):
            with self.subTest(doc=doc), TemplateCopy() as root:
                self.assertEqual(guard(root, body), 0, "the example command is allowed before the entry exists")
                target = root / attrs["path"]
                target.write_text(target.read_text().rstrip("\n") + "\n" + body + "\n")
                self.assertEqual(guard(root, body), 2)

    def test_manifest_agents_example_syncs_cleanly_in_an_installed_project(self):
        for doc, attrs, body in (e for e in examples() if e[1]["example"] == "manifest-agents"):
            with self.subTest(doc=doc), TemplateCopy() as src, tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                cli.main(["--root", str(src), "init", tmp, "--agents", "kiro"], io.StringIO(), io.StringIO())
                path = root / "harness/manifest.json"
                manifest = json.loads(path.read_text())
                manifest["agents"].update(json.loads(body))
                path.write_text(json.dumps(manifest, indent=2) + "\n")
                for argv in (["sync"], ["sync", "--check"]):
                    code = cli.main(["--root", tmp, *argv], io.StringIO(), io.StringIO())
                    self.assertEqual(code, 0, argv)


if __name__ == "__main__":
    unittest.main()
