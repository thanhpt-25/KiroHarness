"""CI workflow policy checks (agent-harness-platform Requirement 2).

The workflows are read as text with small regular expressions, because the
test suite is standard-library only and has no YAML parser.
"""

import re
import unittest

from tests._support import ROOT, detail

WORKFLOWS = ROOT / ".github" / "workflows"
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)(.*)$")
PINNED = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s*#\s*v\d+(\.\d+)*\s*$")


def workflow_files():
    return sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))


class CiWorkflows(unittest.TestCase):
    def test_ci_and_integration_workflows_exist(self):
        # Validates: agent-harness-platform/R2.1, agent-harness-platform/R2.4
        names = {p.name for p in workflow_files()}
        self.assertTrue({"ci.yml", "integration.yml"} <= names, detail(WORKFLOWS, "ci.yml and integration.yml", names))

    def test_actions_are_pinned_by_full_sha_with_version_comment(self):
        # Validates: agent-harness-platform/R2.2
        for path in workflow_files():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = USES.match(line)
                if not match:
                    continue
                ref, rest = match.group(1), match.group(2)
                where = f"{path.name}:{number}"
                self.assertRegex(ref, PINNED, detail(where, "owner/repo@<40-hex SHA>", ref))
                self.assertRegex(rest, VERSION_COMMENT, detail(where, "trailing '# vX.Y.Z' comment", rest))

    def test_token_permissions_are_read_only(self):
        # Validates: agent-harness-platform/R2.2
        for path in workflow_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            top = [i for i, line in enumerate(lines) if line == "permissions:"]
            self.assertEqual(len(top), 1, detail(path.name, "one top-level permissions block", top))
            block = []
            for line in lines[top[0] + 1:]:
                if not line.startswith("  "):
                    break
                block.append(line.strip())
            self.assertEqual(block, ["contents: read"], detail(path.name, "contents: read only", block))
            for number, line in enumerate(lines, 1):
                if line.startswith(" ") and line.strip() == "permissions:":
                    previous = lines[number - 2].strip() if number > 1 else ""
                    self.assertTrue(previous.startswith("#"),
                                    detail(f"{path.name}:{number}", "job permissions with a justification comment", previous))

    def test_ci_runs_validation_and_properties_on_the_matrix(self):
        # Validates: agent-harness-platform/R2.1, agent-harness-platform/R2.3
        text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
        for needle in ("push:", "pull_request:", "self-hosted",
                       "scripts/validate.sh", "scripts/test-properties.sh", "HYPOTHESIS_PROFILE: ci"):
            self.assertIn(needle, text, detail("ci.yml", needle, "missing"))

    def test_integration_never_runs_on_pull_requests(self):
        # Validates: agent-harness-platform/R2.4
        text = (WORKFLOWS / "integration.yml").read_text(encoding="utf-8")
        on_block = text.split("\non:\n", 1)[1].split("\n\n", 1)[0]
        self.assertNotIn("pull_request", on_block, detail("integration.yml on:", "no pull_request trigger", on_block))
        self.assertIn("workflow_dispatch:", on_block)
        self.assertIn("schedule:", on_block)
        self.assertIn("HARNESS_INTEGRATION", text)


if __name__ == "__main__":
    unittest.main()
