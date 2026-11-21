"""Hook_Config_Parser read errors (Requirements 9.3, 9.5)."""

import os
import tempfile
import unittest
from pathlib import Path

from tests._support import detail  # noqa: F401  (sets sys.path)
from harness_validator import hookconfig

VALID = '{"version": "v1", "hooks": [{"name": "a", "trigger": "Stop", "action": {"type": "agent", "prompt": "p"}}]}'


class ParserReadErrors(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        for path in self.dir.iterdir():
            os.chmod(path, 0o644)
        self._tmp.cleanup()

    def test_missing_file_is_a_read_error_naming_the_path(self):
        path = self.dir / "missing.json"
        with self.assertRaises(hookconfig.HookReadError) as ctx:
            hookconfig.parse_hook_file(path)
        self.assertIn(str(path), str(ctx.exception))
        self.assertIn("could not be read", str(ctx.exception))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can read any file")
    def test_unreadable_file_is_a_read_error(self):
        path = self.dir / "locked.json"
        path.write_text(VALID, encoding="utf-8")
        os.chmod(path, 0)
        with self.assertRaises(hookconfig.HookReadError) as ctx:
            hookconfig.parse_hook_file(path)
        self.assertIn(str(path), str(ctx.exception))

    def test_invalid_utf8_reports_line_and_column(self):
        path = self.dir / "bad.json"
        path.write_bytes(b'{\n  "version": "v\xff1"}')
        with self.assertRaises(hookconfig.HookParseError) as ctx:
            hookconfig.parse_hook_file(path)
        self.assertEqual((ctx.exception.line, ctx.exception.column), (2, 16))
        self.assertIn("UTF-8", str(ctx.exception))

    def test_duplicate_keys_are_a_parse_error(self):
        text = '{"version": "v1",\n "version": "v1", "hooks": []}'
        with self.assertRaises(hookconfig.HookParseError) as ctx:
            hookconfig.parse_hook_text(text, "dup.json")
        self.assertIn("duplicate key", str(ctx.exception))
        self.assertEqual(ctx.exception.line, 2)

    def test_empty_file_reports_line_1_column_1(self):
        with self.assertRaises(hookconfig.HookParseError) as ctx:
            hookconfig.parse_hook_text("", "empty.json")
        self.assertEqual((ctx.exception.line, ctx.exception.column), (1, 1))

    def test_valid_file_parses(self):
        path = self.dir / "ok.json"
        path.write_text(VALID, encoding="utf-8")
        hook_file = hookconfig.parse_hook_file(path)
        self.assertEqual(len(hook_file.hooks), 1)
        self.assertIsNone(hook_file.hooks[0].matcher)


if __name__ == "__main__":
    unittest.main()
