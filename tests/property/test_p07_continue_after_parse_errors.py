# Feature: kiro-agent-harness-template, Property 7: Validation reports all files and continues past parse failures
# Validates: kiro-agent-harness-template/R3.9, kiro-agent-harness-template/R10.1, kiro-agent-harness-template/R10.12
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import TemplateCopy, errors, validate

HOOKS = [
    ".kiro/hooks/destructive-command-guard.json", ".kiro/hooks/quality-on-save.json",
    ".kiro/hooks/session-start-context.json", ".kiro/hooks/stop-validate.json",
]
STEERING = [".kiro/steering/product.md", ".kiro/steering/testing.md", ".kiro/steering/api-design.md"]
MCP = ".kiro/settings/mcp.json"
FILES = HOOKS + STEERING + [MCP]


def corrupt(root, path):
    if path.endswith(".md"):
        (root / path).write_text("---\ninclusion: always\nnested:\n  key: value\n---\n# Broken\n")
    else:
        (root / path).write_text('{"version": "v1", "hooks": [')


def inject(root, path):
    """Inject one rule violation and return the field it breaks."""
    target = root / path
    if path.endswith(".md"):
        target.write_text(target.read_text().replace("inclusion: ", "inclusion: sometimes-", 1))
        return "front_matter.inclusion"
    if path == MCP:
        data = json.loads(target.read_text())
        del data["mcpServers"]["fetch"]["disabled"]
        target.write_text(json.dumps(data))
        return "mcpServers.fetch.disabled"
    data = json.loads(target.read_text())
    data["hooks"][0]["trigger"] = "NotATrigger"
    target.write_text(json.dumps(data))
    return "hooks[0].trigger"


class ContinueAfterParseErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._copy = TemplateCopy()
        cls.pristine = cls._copy.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._copy.__exit__(None, None, None)

    @given(st.lists(st.sampled_from(["keep", "corrupt", "inject"]), min_size=len(FILES), max_size=len(FILES)))
    def test_one_parse_error_per_corrupted_file_and_every_injection_reported(self, plan):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "t"
            shutil.copytree(self.pristine, root, symlinks=True)
            if not (root / MCP).exists():
                self.skipTest(".kiro/settings/mcp.json is missing from the Template")
            expected = {}
            for path, action in zip(FILES, plan):
                if action == "corrupt":
                    corrupt(root, path)
                elif action == "inject":
                    expected[path] = inject(root, path)
            findings = errors(validate(root)[0])
        for path, action in zip(FILES, plan):
            mine = [f for f in findings if f.path == path]
            if action == "corrupt":
                self.assertEqual(len(mine), 1, mine)
                self.assertIn(mine[0].rule, {"HOOK-JSON", "MCP-JSON", "STEER-FM"})
            elif action == "inject":
                self.assertIn(expected[path], {f.field for f in mine}, mine)


if __name__ == "__main__":
    unittest.main()
