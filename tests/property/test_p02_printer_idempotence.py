# Feature: kiro-agent-harness-template, Property 2: Hook printer idempotence
import unittest

from hypothesis import given

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_hooks import hook_json_texts
from harness_validator.hookconfig import parse_hook_text, print_hook_file


class PrinterIdempotence(unittest.TestCase):
    @given(hook_json_texts())
    def test_second_print_is_byte_identical(self, text):
        output_a = print_hook_file(parse_hook_text(text, "p.json"))
        output_b = print_hook_file(parse_hook_text(output_a, "p.json"))
        self.assertEqual(output_a.encode("utf-8"), output_b.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
