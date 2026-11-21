# Feature: kiro-agent-harness-template, Property 5: Parse errors report a 1-based position
import json
import unittest

from hypothesis import assume, given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_hooks import hook_json_texts
from harness_validator.hookconfig import HookParseError, parse_hook_text


def _is_json(text):
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


class ParsePositions(unittest.TestCase):
    def check(self, text):
        with self.assertRaises(HookParseError) as ctx:
            parse_hook_text(text, "bad.json")
        exc = ctx.exception
        self.assertIn("bad.json", str(exc))
        self.assertTrue(1 <= exc.line <= text.count("\n") + 2, (exc.line, text))
        self.assertGreaterEqual(exc.column, 1)

    @given(hook_json_texts(), st.data())
    def test_truncated_text(self, text, data):
        cut = data.draw(st.integers(0, len(text)))
        truncated = text[:cut]
        assume(not _is_json(truncated))
        self.check(truncated)

    @given(hook_json_texts(), st.data(), st.sampled_from(list("{}[],:\"x#@")))
    def test_stray_character(self, text, data, char):
        position = data.draw(st.integers(0, len(text)))
        broken = text[:position] + char + text[position:]
        assume(not _is_json(broken))
        self.check(broken)

    def test_empty_file(self):
        with self.assertRaises(HookParseError) as ctx:
            parse_hook_text("", "bad.json")
        self.assertEqual((ctx.exception.line, ctx.exception.column), (1, 1))


if __name__ == "__main__":
    unittest.main()
