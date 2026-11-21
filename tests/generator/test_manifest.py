"""Manifest and schema checks (agent-harness-platform R6.1)."""
# Validates: agent-harness-platform/R6.1, agent-harness-platform/R6.2
import copy
import json
import unittest

from tests.generator._fixture import MANIFEST, SourceRoot, run_cli
from harness_validator import manifest as manifest_mod


class ManifestSchema(unittest.TestCase):
    def problems(self, manifest):
        with SourceRoot() as root:
            schema = json.loads((root / "harness/manifest.schema.json").read_text())
            return manifest_mod.schema_problems(manifest, schema)

    def test_shipped_manifest_is_valid(self):
        self.assertEqual(self.problems(MANIFEST), [])

    def test_unknown_agent_is_rejected(self):
        bad = copy.deepcopy(MANIFEST)
        bad["agents"]["emacs"] = {"enabled": True}
        self.assertTrue(any("unknown field emacs" in p for p in self.problems(bad)))

    def test_inexact_mcp_version_is_rejected(self):
        bad = copy.deepcopy(MANIFEST)
        bad["mcp"]["git"]["version"] = "latest"
        self.assertTrue(any("mcp.git.version" in p for p in self.problems(bad)))

    def test_missing_section_is_rejected(self):
        bad = copy.deepcopy(MANIFEST)
        del bad["guards"]
        self.assertIn("manifest: guards is required", self.problems(bad))

    def test_guidance_pattern_without_files_is_rejected(self):
        bad = copy.deepcopy(MANIFEST)
        bad["guidance"] = ["harness/guidance/none-*.md"]
        with SourceRoot(bad) as root:
            with self.assertRaises(manifest_mod.ManifestError) as ctx:
                manifest_mod.load(str(root))
        self.assertIn("matches no file", str(ctx.exception))

    def test_invalid_manifest_exits_2_and_writes_nothing(self):
        bad = copy.deepcopy(MANIFEST)
        bad["harness_version"] = "one"
        with SourceRoot(bad) as root:
            code, _out, err = run_cli(root, "sync")
            self.assertEqual(code, 2)
            self.assertIn("harness_version", err)
            self.assertFalse((root / ".kiro").exists())
            self.assertFalse((root / "harness/generated.lock.json").exists())


if __name__ == "__main__":
    unittest.main()
