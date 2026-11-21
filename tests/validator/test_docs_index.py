"""docs/README.md links every document, in the four Diataxis sections (agent-harness-platform R16.1, R16.2)."""
# Validates: agent-harness-platform/R16.1, agent-harness-platform/R16.2
import re
import unittest

from tests._support import ROOT

DOCS = ROOT / "docs"
SECTIONS = ("Tutorials", "How-to guides", "Reference", "Explanation")


class DocsIndex(unittest.TestCase):
    def setUp(self):
        self.index = (DOCS / "README.md").read_text(encoding="utf-8")

    def test_four_sections_exist(self):
        for name in SECTIONS:
            self.assertRegex(self.index, rf"(?m)^## {name}", name)

    def test_every_document_is_linked(self):
        linked = {(DOCS / t.split("#", 1)[0]).resolve() for t in re.findall(r"\]\(([^)]+)\)", self.index) if not t.startswith(("http", "#"))}
        for path in sorted(DOCS.rglob("*.md")):
            rel = path.relative_to(DOCS).as_posix()
            if rel == "README.md" or (rel.startswith("adr/") and rel != "adr/README.md") or rel.count("/") >= 3:
                continue  # ADRs are linked from the ADR index; records sit under docs/verification/<agent>/<version>/
            self.assertIn(path.resolve(), linked, f"docs/{rel} is not linked from docs/README.md")

    def test_every_adr_is_in_the_adr_index_and_lists_criteria(self):
        index = (DOCS / "adr/README.md").read_text(encoding="utf-8")
        for path in sorted((DOCS / "adr").glob("[0-9]*.md")):
            self.assertIn(path.name, index, path.name)
            text = path.read_text(encoding="utf-8")
            for field in ("- Status:", "- Date:", "- Criteria:" if int(path.name[:4]) >= 6 else "- Status:"):
                self.assertIn(field, text, path.name)


if __name__ == "__main__":
    unittest.main()
