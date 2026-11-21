"""Each numbered design property 29-44 has exactly one test_pNN_*.py with a Validates tag."""
# Validates: agent-harness-platform/R13.5
import re
import unittest

from tests._support import ROOT as REPO


class PropertyConvention(unittest.TestCase):
    def test_one_file_per_property(self):
        files = [p.name for p in (REPO / "tests" / "property").glob("test_p*.py")]
        for n in range(29, 45):
            matches = [f for f in files if re.match(rf"test_p{n}_", f)]
            self.assertEqual(len(matches), 1, f"property {n}: {matches}")
            text = (REPO / "tests" / "property" / matches[0]).read_text(encoding="utf-8")
            self.assertIn("# Validates:", text, matches[0])


if __name__ == "__main__":
    unittest.main()
