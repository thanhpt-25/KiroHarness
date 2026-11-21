# Feature: kiro-agent-harness-template, Property 1: Hook configuration round trip
# Validates: kiro-agent-harness-template/R9.1, kiro-agent-harness-template/R9.8
import unittest

from hypothesis import given

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_hooks import hook_files
from harness_validator.hookconfig import parse_hook_text, print_hook_file


class HookRoundTrip(unittest.TestCase):
    @given(hook_files())
    def test_print_then_parse_returns_an_equal_object(self, hook_file):
        self.assertEqual(parse_hook_text(print_hook_file(hook_file), "p.json"), hook_file)


if __name__ == "__main__":
    unittest.main()
