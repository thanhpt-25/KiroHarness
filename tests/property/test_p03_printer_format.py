# Feature: kiro-agent-harness-template, Property 3: Hook printer output format and key order
import json
import unittest

from hypothesis import given

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_hooks import hook_files
from harness_validator.hookconfig import parse_hook_text, print_hook_file

DEF_ORDER = ["name", "trigger", "matcher", "action", "timeout", "description", "enabled"]
ACTION_ORDER = ["type", "command", "prompt"]


def expected_keys(order, present, extra):
    return [k for k in order if k in present] + sorted(k for k, _ in extra)


class PrinterFormat(unittest.TestCase):
    @given(hook_files())
    def test_format_and_key_order(self, hook_file):
        text = print_hook_file(hook_file)
        self.assertNotIn("\r", text)
        self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
        previous = 0
        # Split on LF only: splitlines() also breaks on characters such as \x85 inside strings.
        for line in text[:-1].split("\n"):
            indent = len(line) - len(line.lstrip(" "))
            self.assertEqual(indent % 2, 0)
            self.assertLessEqual(indent, previous + 2)
            previous = indent
        parse_hook_text(text, "p.json")

        obj = json.loads(text, object_pairs_hook=lambda pairs: pairs)
        self.assertEqual([k for k, _ in obj][:2], ["version", "hooks"])
        hooks = dict(obj)["hooks"]
        for pairs, definition in zip(hooks, hook_file.hooks):
            keys = [k for k, _ in pairs]
            present = {k for k in DEF_ORDER if getattr(definition, k) is not None}
            self.assertEqual(keys, expected_keys(DEF_ORDER, present, definition.extra))
            if definition.matcher is None:
                self.assertNotIn("matcher", keys)
            action_keys = [k for k, _ in dict(pairs)["action"]]
            action_present = {k for k in ACTION_ORDER if getattr(definition.action, k) is not None}
            self.assertEqual(action_keys, expected_keys(ACTION_ORDER, action_present, definition.action.extra))


if __name__ == "__main__":
    unittest.main()
