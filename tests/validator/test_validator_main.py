"""Config_Validator entry point (Requirements 5.1, 10.1, 10.11, 10.14)."""
# Validates: kiro-agent-harness-template/R5.1, kiro-agent-harness-template/R10.1, kiro-agent-harness-template/R10.11, kiro-agent-harness-template/R10.14

import ast
import json
import sys
import time
import unittest
from unittest import mock

from tests._support import ROOT, SCRIPTS, TemplateCopy, detail, errors, validate


def rules(findings):
    return {f.rule for f in findings}


class ValidatorMain(unittest.TestCase):
    def test_shipped_template_has_no_errors(self):
        with TemplateCopy() as root:
            findings, files = validate(root)
            self.assertEqual(errors(findings), [], detail("shipped Template", "0 errors", errors(findings)))
            self.assertGreater(files, 20)

    def test_shipped_template_has_no_warnings(self):
        # Validates: agent-harness-platform/R1.3
        # Runs on the checkout itself (not a copy) so the git-based placeholder
        # scan is used; a copy without .git would add a fallback warning.
        if not (ROOT / ".git").exists():
            self.skipTest("needs a git checkout for the git-based placeholder scan")
        findings, _ = validate(ROOT)
        warnings = [f for f in findings if f.severity.value == "warning"]
        self.assertEqual(warnings, [], detail("shipped Template", "0 warnings", warnings))

    def test_missing_mcp_config_is_reported(self):
        with TemplateCopy() as root:
            mcp = root / ".kiro/settings/mcp.json"
            if mcp.exists():
                mcp.unlink()
            findings, _ = validate(root)
            missing = [f for f in findings if f.rule == "MCP-MISSING"]
            self.assertEqual(len(missing), 1)
            self.assertIn(".kiro/settings/mcp.json", missing[0].message)

    def test_risky_tool_not_covered_by_matcher_is_reported(self):
        with TemplateCopy() as root:
            path = root / ".kiro/hooks/risky-tool-guard.json"
            data = json.loads(path.read_text())
            data["hooks"][0]["matcher"] = data["hooks"][0]["matcher"].replace("delete_file|", "")
            path.write_text(json.dumps(data, indent=2))
            findings, _ = validate(root)
            cover = [f for f in findings if f.rule == "RISKY-COVER"]
            self.assertEqual(len(cover), 1, detail("matcher without delete_file", "1 RISKY-COVER error", cover))
            self.assertIn("delete_file", cover[0].message)

    def test_crashing_checker_is_reported_and_the_run_continues(self):
        with TemplateCopy() as root:
            (root / ".kiro/hooks/broken.json").write_text("{not json")
            with mock.patch("harness_validator.steering.check_steering", side_effect=RuntimeError("boom")):
                findings, _ = validate(root)
            internal = [f for f in findings if f.rule == "INTERNAL"]
            self.assertTrue(internal)
            self.assertTrue(all("steering crashed: RuntimeError: boom" in f.message for f in internal))
            self.assertIn("HOOK-JSON", rules(findings))

    def test_validator_imports_only_the_standard_library(self):
        package = SCRIPTS / "harness_validator"
        for path in sorted(package.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module]
                for name in names:
                    top = name.split(".")[0]
                    with self.subTest(file=path.name, module=name):
                        self.assertIn(top, sys.stdlib_module_names)

    def test_large_workspace_finishes_within_10_seconds(self):
        with TemplateCopy() as root:
            steering = root / ".kiro/steering"
            for index in range(150):
                (steering / f"generated-{index}.md").write_text("---\ninclusion: manual\n---\n\n# Generated\n")
            hook = (root / ".kiro/hooks/stop-validate.json").read_text()
            for index in range(40):
                (root / f".kiro/hooks/generated-{index}.json").write_text(hook)
            generated = root / "generated"
            generated.mkdir()
            for index in range(1000):
                (generated / f"file-{index}.txt").write_text("plain text line\n" * 20)
            start = time.monotonic()
            findings, files = validate(root)
            elapsed = time.monotonic() - start
            self.assertGreaterEqual(files, 1190)
            self.assertLess(elapsed, 10.0, detail("200 config files, 1,000 text files", "< 10 s", f"{elapsed:.2f} s"))


if __name__ == "__main__":
    unittest.main()
