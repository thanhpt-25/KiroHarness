"""`harness sync` behavior (agent-harness-platform R6.2 to R6.7, R7.1 to R7.3, R7.5)."""
# Validates: agent-harness-platform/R6.2, agent-harness-platform/R6.4, agent-harness-platform/R6.5, agent-harness-platform/R6.6, agent-harness-platform/R6.7, agent-harness-platform/R7.1, agent-harness-platform/R7.2, agent-harness-platform/R7.3, agent-harness-platform/R7.5
import copy
import json
import unittest

from tests.generator._fixture import MANIFEST, SourceRoot, run_cli, snapshot, with_agents
from harness_cli import plan as plan_mod

ALL = with_agents(claude_code=True, cursor=True, copilot=True)


class Sync(unittest.TestCase):
    def test_kiro_only_writes_kiro_files_and_a_lock(self):
        with SourceRoot() as root:
            code, _out, _err = run_cli(root, "sync")
            self.assertEqual(code, 0)
            files = set(snapshot(root)) - {"harness/manifest.json", "harness/manifest.schema.json"}
            self.assertTrue(all(f.startswith((".kiro/", "harness/")) for f in files), files)
            self.assertIn(".kiro/settings/mcp.json", files)
            self.assertNotIn("AGENTS.md", files)
            lock = json.loads((root / "harness/generated.lock.json").read_text())
            self.assertIn(".kiro/steering/security.md", lock["files"])
            self.assertEqual(len(lock["files"][".kiro/steering/security.md"]["sha256"]), 64)

    def test_second_sync_changes_nothing_and_check_is_clean(self):
        with SourceRoot(ALL) as root:
            run_cli(root, "sync")
            before = snapshot(root)
            code, out, _err = run_cli(root, "sync")
            self.assertEqual((code, out), (0, ""))
            self.assertEqual(snapshot(root), before)
            self.assertEqual(run_cli(root, "sync", "--check")[0], 0)

    def test_check_reports_drift_with_a_diff_and_writes_nothing(self):
        with SourceRoot() as root:
            run_cli(root, "sync")
            guidance = root / "harness/guidance/product.md"
            guidance.write_text(guidance.read_text() + "\nExtra line.\n")
            before = snapshot(root)
            code, out, _err = run_cli(root, "sync", "--check")
            self.assertEqual(code, 1)
            self.assertIn("drift: .kiro/steering/product.md", out)
            self.assertIn("+Extra line.", out)
            self.assertEqual(snapshot(root), before)

    def test_source_change_propagates_when_outputs_are_unedited(self):
        with SourceRoot() as root:
            run_cli(root, "sync")
            guidance = root / "harness/guidance/product.md"
            guidance.write_text(guidance.read_text() + "\nExtra line.\n")
            self.assertEqual(run_cli(root, "sync")[0], 0)
            self.assertIn("Extra line.", (root / ".kiro/steering/product.md").read_text())

    def test_hand_edited_file_is_refused_unless_forced(self):
        with SourceRoot() as root:
            run_cli(root, "sync")
            target = root / ".kiro/steering/security.md"
            target.write_text(target.read_text() + "hand edit\n")
            code, _out, err = run_cli(root, "sync")
            self.assertEqual(code, 1)
            self.assertIn(".kiro/steering/security.md", err)
            self.assertIn("hand edit", target.read_text())
            code, _out, _err = run_cli(root, "sync", "--force")
            self.assertEqual(code, 0)
            self.assertNotIn("hand edit", target.read_text())

    def test_existing_unlocked_file_with_other_content_is_not_overwritten(self):
        with SourceRoot() as root:
            (root / ".kiro/settings").mkdir(parents=True)
            (root / ".kiro/settings/mcp.json").write_text("{}\n")
            code, _out, err = run_cli(root, "sync")
            self.assertEqual(code, 1)
            self.assertIn(".kiro/settings/mcp.json", err)

    def test_disabled_guard_and_agent_leave_no_file(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["guards"]["risky"]["enabled"] = False
        with SourceRoot(manifest) as root:
            run_cli(root, "sync")
            self.assertFalse((root / ".kiro/hooks/risky-tool-guard.json").exists())
            self.assertTrue((root / ".kiro/hooks/destructive-command-guard.json").exists())
            self.assertFalse((root / "CLAUDE.md").exists())

    def test_disabling_an_agent_removes_its_unedited_files(self):
        with SourceRoot(ALL) as root:
            run_cli(root, "sync")
            self.assertTrue((root / "CLAUDE.md").exists())
            SourceRoot.write_manifest(root, MANIFEST)
            self.assertEqual(run_cli(root, "sync", "--check")[0], 1)
            self.assertEqual(run_cli(root, "sync")[0], 0)
            for gone in ("CLAUDE.md", "AGENTS.md", ".cursor/rules/security.mdc", ".github/copilot-instructions.md"):
                self.assertFalse((root / gone).exists(), gone)
            self.assertEqual(run_cli(root, "sync", "--check")[0], 0)

    def test_every_commentable_file_carries_a_header_naming_sources(self):
        with SourceRoot(ALL) as root:
            run_cli(root, "sync")
            for rel in ("AGENTS.md", "CLAUDE.md", ".cursor/rules/security.mdc", ".github/copilot-instructions.md", ".claude/rules/testing.md"):
                text = (root / rel).read_text()
                self.assertIn("Generated by scripts/harness sync from", text, rel)
                self.assertIn("(harness 0.5.0)", text, rel)

    def test_agents_md_holds_always_guidance_and_links_the_rest(self):
        with SourceRoot(ALL) as root:
            run_cli(root, "sync")
            text = (root / "AGENTS.md").read_text()
            self.assertIn("# Security Rules", text)
            self.assertNotIn("# Testing Standards", text)
            self.assertIn("(harness/guidance/release-checklist.md)", text)
            self.assertIn("(harness/guidance/testing.md)", text)
            self.assertNotIn("inclusion:", text)

    def test_claude_md_imports_agents_md(self):
        with SourceRoot(ALL) as root:
            run_cli(root, "sync")
            self.assertIn("\n@AGENTS.md\n", (root / "CLAUDE.md").read_text())

    def test_untrusted_content_rule_reaches_every_agents_always_on_context(self):
        with SourceRoot(ALL) as root:
            plan = plan_mod.build_plan(str(root))
            seen = set()
            for planned in plan.files.values():
                if "Untrusted Tool Output" in planned.content and "data, not instructions" in planned.content:
                    seen |= set(planned.always_for)
            for agent in ("kiro", "claude-code", "cursor", "copilot"):
                self.assertIn(agent, seen)

    def test_fallback_and_unverified_formats_warn(self):
        with SourceRoot(ALL) as root:
            _code, _out, err = run_cli(root, "sync", "--check")
            self.assertIn("warning: claude-code: guidance 'api-design'", err)
            self.assertIn("warning: copilot: guidance 'api-design'", err)
            self.assertIn("warning: cursor: output format is not verified", err)

    def test_context_budget_sizes_and_warning(self):
        with SourceRoot() as root:
            sizes = plan_mod.always_on_sizes(plan_mod.build_plan(str(root)))
            lines, chars = sizes["kiro"]
            self.assertLess(lines, plan_mod.BUDGET_LINES)
            self.assertLess(chars, plan_mod.BUDGET_CHARS)
        from harness_validator import generator_checks

        with SourceRoot() as root:
            (root / "harness/guidance/product.md").write_text("---\ninclusion: always\n---\n\n# Big\n\n" + "x " * 7000 + "\n")
            findings, notes, _gen = generator_checks.check_generated(root)
            self.assertTrue(any(f.rule == "CONTEXT-BUDGET" and f.severity.value == "warning" for f in findings))
            self.assertTrue(any(n.startswith("Always-on context: kiro") for n in notes))

    def test_validator_reports_drift_as_an_error(self):
        from harness_validator import generator_checks

        with SourceRoot() as root:
            run_cli(root, "sync")
            self.assertEqual([f for f in generator_checks.check_generated(root)[0] if f.rule == "DRIFT"], [])
            (root / ".kiro/steering/tech.md").write_text("changed\n")
            drift = [f for f in generator_checks.check_generated(root)[0] if f.rule == "DRIFT"]
            self.assertEqual([f.path for f in drift], [".kiro/steering/tech.md"])


if __name__ == "__main__":
    unittest.main()
