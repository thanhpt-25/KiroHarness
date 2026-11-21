"""Spec_Linter and new-spec (agent-harness-platform R13.1 to R13.6)."""
# Validates: agent-harness-platform/R13.1, agent-harness-platform/R13.2, agent-harness-platform/R13.3, agent-harness-platform/R13.4, agent-harness-platform/R13.5, agent-harness-platform/R13.6
import unittest

from tests._support import ROOT, TemplateCopy, errors, validate
from tests.generator._fixture import run_cli
from harness_validator import spec_lint

def good_files():
    from harness_cli import specs

    return {"requirements.md": specs.REQUIREMENTS.format(title="Thing", name="thing"), "design.md": specs.DESIGN.format(title="Thing", name="thing"),
            "tasks.md": specs.TASKS}


def rules(findings):
    return sorted(f.rule for f in findings)


class Lint(unittest.TestCase):
    def test_skeleton_passes(self):
        self.assertEqual(spec_lint.check_spec("thing", good_files()), [])

    def test_missing_files_are_errors(self):
        files = good_files()
        files["design.md"] = None
        files["tasks.md"] = None
        self.assertEqual(rules(spec_lint.check_spec("thing", files)), ["SPEC-FILES", "SPEC-FILES"])

    def test_missing_introduction_glossary_story_and_ears(self):
        files = good_files()
        files["requirements.md"] = ("# R\n\n## Requirements\n\n### Requirement 1: X\n\n**User Story:** I want a thing.\n\n#### Acceptance Criteria\n\n"
                                    "1. The thing does stuff.\n2. WHEN x, THE y SHALL z.\n")
        found = spec_lint.check_spec("thing", files)
        self.assertEqual(rules(found), ["SPEC-EARS", "SPEC-REQ", "SPEC-REQ", "SPEC-STORY", "SPEC-UNREF"])

    def test_missing_design_sections(self):
        files = good_files()
        files["design.md"] = "# D\n\n## Overview\n\ntext\n"
        found = [f for f in spec_lint.check_spec("thing", files) if f.rule == "SPEC-DESIGN"]
        self.assertEqual(len(found), 5)

    def test_task_references_errors_and_unreferenced_warnings(self):
        files = good_files()
        files["tasks.md"] = "- [ ] 1. x\n  - _Requirements: 1.2, 9.9_\n"
        found = spec_lint.check_spec("thing", files)
        self.assertEqual([(f.rule, f.severity.value) for f in found], [("SPEC-TASKREF", "error"), ("SPEC-TASKREF", "error"), ("SPEC-UNREF", "warning")])

    def test_both_shipped_specs_and_the_example_pass_without_findings(self):
        found = [f for f in validate(ROOT)[0] if f.rule.startswith("SPEC-")]
        self.assertEqual(found, [])

    def test_validator_checks_every_spec_directory(self):
        with TemplateCopy() as root:
            (root / ".kiro/specs/example-feature/tasks.md").unlink()
            self.assertTrue(any(f.rule == "SPEC-FILES" for f in errors(validate(root)[0])))


class NewSpec(unittest.TestCase):
    def test_creates_a_passing_skeleton_and_refuses_to_overwrite(self):
        with TemplateCopy() as root:
            code, out, _err = run_cli(root, "new-spec", "payment-flow")
            self.assertEqual(code, 0, out)
            spec = root / ".kiro/specs/payment-flow"
            self.assertEqual(sorted(p.name for p in spec.iterdir()), [".config.kiro", "design.md", "requirements.md", "tasks.md"])
            self.assertEqual([f for f in validate(root)[0] if f.rule.startswith("SPEC-")], [])
            before = (spec / "tasks.md").read_text()
            (spec / "tasks.md").write_text(before + "edited\n")
            code, _out, err = run_cli(root, "new-spec", "payment-flow")
            self.assertEqual(code, 1)
            self.assertIn("already exists", err)
            self.assertIn("edited", (spec / "tasks.md").read_text())

    def test_rejects_bad_names(self):
        with TemplateCopy() as root:
            self.assertEqual(run_cli(root, "new-spec", "../evil")[0], 2)

    def test_spec_workflow_guidance_is_a_manual_source(self):
        text = (ROOT / "harness/guidance/spec-workflow.md").read_text()
        self.assertIn("inclusion: manual", text)
        self.assertIn("scripts/harness new-spec", text)


if __name__ == "__main__":
    unittest.main()
