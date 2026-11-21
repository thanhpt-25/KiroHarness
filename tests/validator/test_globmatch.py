"""File_Match_Pattern examples from Requirements 2.3 and 2.4."""

import unittest

from tests._support import detail
from harness_validator.globmatch import glob_match, match_any

TESTING = ["**/*.test.*", "**/*.spec.*", "**/test_*.py", "**/*_test.go"]
CODING = "**/*.{ts,tsx,js,jsx,py,go}"


class GlobExamples(unittest.TestCase):
    def check(self, patterns, path, expected):
        actual = match_any(patterns, path)
        self.assertEqual(actual, expected, detail((patterns, path), expected, actual))

    def test_testing_pattern_matches_test_files(self):
        for path in ("src/app.test.ts", "src/app.spec.js", "tests/test_app.py", "test/app_test.go"):
            with self.subTest(path=path):
                self.check(TESTING, path, True)

    def test_testing_pattern_skips_other_files(self):
        for path in ("src/app.ts", "README.md"):
            with self.subTest(path=path):
                self.check(TESTING, path, False)

    def test_coding_pattern_matches_source_files(self):
        for path in ("src/app.ts", "src/app.tsx", "src/app.js", "src/app.py", "src/app.go"):
            with self.subTest(path=path):
                self.check(CODING, path, True)

    def test_coding_pattern_skips_other_files(self):
        for path in ("README.md", ".env.example", ".kiro/settings/mcp.json"):
            with self.subTest(path=path):
                self.check(CODING, path, False)

    def test_star_does_not_cross_directories(self):
        self.assertFalse(glob_match("src/*.py", "src/pkg/app.py"))
        self.assertTrue(glob_match("src/**/*.py", "src/app.py"))
        self.assertTrue(glob_match("src/**/*.py", "src/a/b/app.py"))
        self.assertFalse(glob_match("?.py", "a/b.py"))


if __name__ == "__main__":
    unittest.main()
