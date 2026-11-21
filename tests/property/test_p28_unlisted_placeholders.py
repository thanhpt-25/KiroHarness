# Feature: kiro-agent-harness-template, Property 28: Unlisted placeholders are reported with every file
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator.__main__ import Run, check_placeholders

NAMES = ["ALPHA", "BETA_2", "GAMMA", "DELTA_X"]
FILES = ["docs/a.md", "docs/b.txt", "src/c.py", ".kiro/steering/d.md"]


def reference(contents, listed):
    """Map each unlisted name to the sorted files that contain it, outside README.md."""
    found = {}
    for path, text in contents.items():
        for name in set(re.findall(r"\{\{([A-Z][A-Z0-9_]{0,63})\}\}", text)):
            found.setdefault(name, set()).add(path)
    return {name: sorted(paths) for name, paths in found.items() if name not in listed}


@st.composite
def workspaces(draw):
    contents = {}
    for path in FILES:
        names = draw(st.lists(st.sampled_from(NAMES), max_size=3))
        contents[path] = "text " + " ".join("{{" + n + "}}" for n in names) + "\n"
    listed = draw(st.sets(st.sampled_from(NAMES)))
    readme_only = draw(st.sampled_from(NAMES))
    return contents, listed, readme_only


class UnlistedPlaceholders(unittest.TestCase):
    @given(workspaces())
    def test_one_error_per_unlisted_name_naming_every_file(self, case):
        contents, listed, readme_only = case
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, text in contents.items():
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                (root / path).write_text(text)
            items = "\n".join(f"- `{{{{{n}}}}}` — docs/a.md — value" for n in sorted(listed))
            (root / "README.md").write_text(f"# T\n\nUses {{{{{readme_only}}}}}.\n\n## Placeholders\n\n{items}\n")
            findings = [f for f in check_placeholders(Run(root)) if f.rule == "PLACEHOLDER"]
        expected = reference(contents, listed)
        self.assertEqual(len(findings), len(expected))
        for finding in findings:
            name = finding.field.strip("{}")
            self.assertIn(name, expected)
            self.assertIn(", ".join(expected[name]), finding.message)


if __name__ == "__main__":
    unittest.main()
