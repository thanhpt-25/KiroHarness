"""VERSION/CHANGELOG, relative links and release gates (agent-harness-platform R16.5, R16.6, R17.1, R17.5)."""
# Validates: agent-harness-platform/R16.5, agent-harness-platform/R16.6, agent-harness-platform/R17.1, agent-harness-platform/R17.5
import tempfile
import unittest
from pathlib import Path

from tests._support import ROOT  # noqa: F401  (puts scripts/ on sys.path)
from harness_validator import release_checks

CHANGELOG = "# Changelog\n\n## [Unreleased]\n\n## [1.2.3] - 2026-01-01\n"


def rules(findings):
    return [f.rule for f in findings]


class Version(unittest.TestCase):
    def make(self, tmp, version, changelog=CHANGELOG):
        root = Path(tmp)
        (root / "harness").mkdir()
        (root / "harness/VERSION").write_text(version)
        if changelog is not None:
            (root / "CHANGELOG.md").write_text(changelog)
        return root

    def test_matching_entry_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(release_checks.check_version(self.make(tmp, "1.2.3\n")), [])

    def test_missing_entry_malformed_version_and_missing_changelog_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rules(release_checks.check_version(self.make(tmp, "1.2.4\n"))), ["VERSION-CHANGELOG"])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rules(release_checks.check_version(self.make(tmp, "v1.2\n"))), ["VERSION-FORMAT"])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rules(release_checks.check_version(self.make(tmp, "1.2.3\n", None))), ["VERSION-CHANGELOG"])

    def test_no_version_file_means_nothing_to_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(release_checks.check_version(tmp), [])


class Links(unittest.TestCase):
    def test_broken_relative_link_is_an_error_but_urls_anchors_and_code_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs/exists.md").write_text("x")
            (root / "README.md").write_text(
                "[ok](docs/exists.md#top) [web](https://example.com/x) [anchor](#here) [bad](docs/missing.md)\n"
                "```\n[in code](nowhere.md)\n```\n")
            findings = release_checks.check_links(root)
            self.assertEqual(rules(findings), ["DOC-LINK"])
            self.assertIn("docs/missing.md", findings[0].message)
            self.assertEqual(findings[0].path, "README.md")

    def test_repository_links_resolve(self):
        self.assertEqual(release_checks.check_links(ROOT), [])


class Gates(unittest.TestCase):
    def test_checklist_naming_every_gate_passes_and_a_gap_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / release_checks.CHECKLIST
            path.parent.mkdir(parents=True)
            path.write_text(" ".join(release_checks.GATES))
            self.assertEqual(release_checks.check_release_gates(tmp), [])
            path.write_text("CI only")
            self.assertEqual(len(release_checks.check_release_gates(tmp)), len(release_checks.GATES) - 1)

    def test_shipped_checklist_names_every_gate(self):
        self.assertEqual(release_checks.check_release_gates(ROOT), [])


if __name__ == "__main__":
    unittest.main()
