"""Scenario replay and Bypass_Corpus (agent-harness-platform R14.1 to R14.5)."""
# Validates: agent-harness-platform/R15.1, agent-harness-platform/R15.2, agent-harness-platform/R15.3, agent-harness-platform/R15.4
import json
import sys
import unittest

from tests._support import ROOT

sys.path.insert(0, str(ROOT / "evals"))
import run  # noqa: E402


class Evals(unittest.TestCase):
    def test_at_least_20_scenarios_with_valid_fields(self):
        items = run.scenarios()
        self.assertGreaterEqual(len(items), 20)
        ids = [s["id"] for s in items]
        self.assertEqual(len(ids), len(set(ids)))
        for s in items:
            self.assertIn(s["expect"], ("deny", "ask", "allow"), s["id"])
            self.assertIn(s["trigger"], ("pre_tool", "prompt_submit"), s["id"])

    def test_every_scenario_matches_on_every_hook_agent(self):
        rows = run.replay()
        self.assertEqual({r["agent"] for r in rows}, set(run.agents()))
        self.assertEqual([r for r in rows if not r["ok"]], [])

    def test_bypass_corpus_has_50_items_and_documented_classes(self):
        items = json.loads((ROOT / "evals" / "bypass-corpus.json").read_text())
        self.assertGreaterEqual(len(items), 50)
        self.assertEqual({i["class"] for i in items}, {"must-block", "known-gap", "safe"})
        self.assertEqual([i["id"] for i in items], sorted({i["id"] for i in items}))

    def test_corpus_outcomes_have_not_changed(self):
        self.assertEqual([r for r in run.corpus_rows() if not r["ok"]], [])

    def test_customizing_guide_states_limits_and_lists_gap_categories(self):
        text = (ROOT / "docs" / "CUSTOMIZING.md").read_text(encoding="utf-8")
        self.assertIn("pattern-based safety net, not a sandbox", text)
        self.assertIn("OS-level isolation", text)
        for category in ("Quote splitting", "Encoded pipelines", "Other interpreters", "Shell globs", "mkfs"):
            self.assertIn(category, text)


if __name__ == "__main__":
    unittest.main()
