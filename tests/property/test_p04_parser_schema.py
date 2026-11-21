# Feature: kiro-agent-harness-template, Property 4: Parser schema acceptance and complete violation listing
import copy
import json
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator.hookconfig import HookSchemaError, parse_hook_text

BASE = {
    "version": "v1",
    "hooks": [
        {"name": f"h{i}", "trigger": t, "matcher": "^x$", "action": {"type": "command", "command": "c"}}
        for i, t in enumerate(["PreToolUse", "Stop", "PostFileSave", "SessionStart", "PostToolUse", "Stop"])
    ],
}


def _set(path, value):
    def apply(doc):
        target = doc
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    return apply


def _delete(path):
    def apply(doc):
        target = doc
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]
    return apply


def schema_mutations():
    """(location, field path, mutation). Each location is used by at most one mutation."""
    mutations = [("version", "version", _set(["version"], "v2"))]
    for i in range(6):
        p = f"hooks[{i}]"
        mutations += [
            (f"{i}.name", f"{p}.name", _set(["hooks", i, "name"], "")),
            (f"{i}.name", f"{p}.name", _set(["hooks", i, "name"], 7)),
            (f"{i}.type", f"{p}.action.type", _set(["hooks", i, "action", "type"], "script")),
        ]
    mutations += [
        ("0.trigger", "hooks[0].trigger", _set(["hooks", 0, "trigger"], "pretooluse")),
        ("1.trigger", "hooks[1].trigger", _set(["hooks", 1, "trigger"], "OnStop")),
        ("2.matcher", "hooks[2].matcher", _delete(["hooks", 2, "matcher"])),
        ("4.matcher", "hooks[4].matcher", _set(["hooks", 4, "matcher"], "")),
        ("3.matcher", "hooks[3].matcher", _set(["hooks", 3, "matcher"], ["x"])),
        ("5.matcher", "hooks[5].matcher", _set(["hooks", 5, "matcher"], 3)),
    ]
    return mutations


MUTATIONS = schema_mutations()


@st.composite
def mutated(draw):
    chosen = draw(st.lists(st.sampled_from(range(len(MUTATIONS))), unique=True, max_size=6))
    used, applied = set(), []
    doc = copy.deepcopy(BASE)
    for index in chosen:
        location, field, apply = MUTATIONS[index]
        if location in used:
            continue
        used.add(location)
        apply(doc)
        applied.append(field)
    return doc, applied


class ParserSchema(unittest.TestCase):
    @given(mutated())
    def test_accepts_iff_no_mutation_and_lists_every_violation(self, case):
        doc, applied = case
        text = json.dumps(doc)
        if not applied:
            self.assertEqual(len(parse_hook_text(text, "f.json").hooks), 6)
            return
        with self.assertRaises(HookSchemaError) as ctx:
            parse_hook_text(text, "f.json")
        self.assertEqual(ctx.exception.path, "f.json")
        fields = {field for field, _ in ctx.exception.violations}
        self.assertTrue(set(applied) <= fields, (applied, ctx.exception.violations))

    @given(st.one_of(st.lists(st.integers()), st.text(), st.integers(), st.none()))
    def test_non_object_top_level_is_rejected(self, value):
        with self.assertRaises(HookSchemaError):
            parse_hook_text(json.dumps(value), "f.json")

    @given(st.one_of(st.dictionaries(st.text(), st.integers()), st.text(), st.integers()))
    def test_non_array_hooks_is_rejected(self, value):
        with self.assertRaises(HookSchemaError) as ctx:
            parse_hook_text(json.dumps({"version": "v1", "hooks": value}), "f.json")
        self.assertIn("hooks", {f for f, _ in ctx.exception.violations})


if __name__ == "__main__":
    unittest.main()
