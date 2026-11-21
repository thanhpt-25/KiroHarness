# Feature: kiro-agent-harness-template, Property 6: Every hook rule violation is reported with its field path
# Validates: kiro-agent-harness-template/R3.1, kiro-agent-harness-template/R3.2, kiro-agent-harness-template/R3.3, kiro-agent-harness-template/R3.4, kiro-agent-harness-template/R3.5, kiro-agent-harness-template/R3.6, kiro-agent-harness-template/R3.7, kiro-agent-harness-template/R3.8, kiro-agent-harness-template/R10.4, kiro-agent-harness-template/R10.13
import json
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import TemplateCopy, errors, validate

HOOK_FILE = ".kiro/hooks/rules-under-test.json"


def base_hooks():
    command = {"type": "command", "command": "sh .kiro/hooks/scripts/session-start.sh"}
    return [
        {"name": "h0", "trigger": "PreToolUse", "matcher": "^(execute_bash)$", "action": dict(command), "timeout": 5},
        {"name": "h1", "trigger": "Stop", "action": {"type": "agent", "prompt": "check"}},
        {"name": "h2", "trigger": "PostFileSave", "matcher": "\\.py$", "action": dict(command), "timeout": 30},
        {"name": "h3", "trigger": "SessionStart", "action": dict(command), "timeout": 10},
        {"name": "h4", "trigger": "PostToolUse", "matcher": "^(fs_write)$", "action": {"type": "agent", "prompt": "p"}},
    ]


def _def(index, key, value):
    def apply(doc):
        doc["hooks"][index][key] = value
    return apply


def _del(index, key):
    def apply(doc):
        doc["hooks"][index].pop(key, None)
    return apply


def _action(index, key, value):
    def apply(doc):
        if value is None:
            doc["hooks"][index]["action"].pop(key, None)
        else:
            doc["hooks"][index]["action"][key] = value
    return apply


def rule_mutations():
    """(location, field path, rule, mutation, name used in the message or None)."""
    m = []
    for i in (0, 2, 3):
        p = f"hooks[{i}]"
        m += [
            (f"{i}.command", f"{p}.action.command", "HOOK-RULES", _action(i, "command", None), None),
            (f"{i}.command", f"{p}.action.command", "HOOK-RULES", _action(i, "command", "  "), None),
            (f"{i}.timeout", f"{p}.timeout", "HOOK-RULES", _def(i, "timeout", 0), None),
            (f"{i}.timeout", f"{p}.timeout", "HOOK-RULES", _def(i, "timeout", 301), None),
            (f"{i}.timeout", f"{p}.timeout", "HOOK-RULES", _def(i, "timeout", True), None),
            (f"{i}.timeout", f"{p}.timeout", "HOOK-RULES", _def(i, "timeout", 5.5), None),
            (f"{i}.timeout", f"{p}.timeout", "HOOK-RULES", _del(i, "timeout"), None),
        ]
    for i in (1, 4):
        m.append((f"{i}.prompt", f"hooks[{i}].action.prompt", "HOOK-RULES", _action(i, "prompt", ""), None))
    for i in range(5):
        p = f"hooks[{i}]"
        m += [
            (f"{i}.name", f"{p}.name", "HOOK-SCHEMA", _def(i, "name", ""), None),
            (f"{i}.name", f"{p}.name", "HOOK-RULES", _def(i, "name", "n" * 65), None),
            (f"{i}.trigger", f"{p}.trigger", "HOOK-SCHEMA", _def(i, "trigger", "OnSave"), f"h{i}"),
        ]
    m.append(("1.name", "hooks[1].name", "HOOK-RULES", _def(1, "name", "h0"), None))
    for i in (0, 2, 4):
        p = f"hooks[{i}]"
        m += [
            (f"{i}.matcher", f"{p}.matcher", "HOOK-SCHEMA", _del(i, "matcher"), None),
            (f"{i}.matcher", f"{p}.matcher", "HOOK-SCHEMA", _def(i, "matcher", ""), None),
            (f"{i}.matcher", f"{p}.matcher", "HOOK-RULES", _def(i, "matcher", "^(unclosed"), None),
        ]
    m.append(("version", "version", "HOOK-SCHEMA", lambda doc: doc.__setitem__("version", "v0"), None))
    m.append(("hooks", "hooks", "HOOK-RULES", lambda doc: doc.__setitem__("hooks", []), None))
    m.append(("file", "file name", "HOOK-ID", None, None))
    return m


MUTATIONS = rule_mutations()


@st.composite
def mutation_sets(draw):
    chosen = draw(st.lists(st.sampled_from(range(len(MUTATIONS))), unique=True, max_size=5))
    used, out = set(), []
    for index in chosen:
        mutation = MUTATIONS[index]
        location = mutation[0]
        clashes = location in used or ("hooks" in used and location not in ("version", "file")) or (
            location == "hooks" and any(u not in ("version", "file") for u in used)
        )
        # Name changes break the trigger message check for the same Hook_Definition.
        if location.endswith(".trigger") and location.replace("trigger", "name") in used:
            clashes = True
        if location.endswith(".name") and location.replace("name", "trigger") in used:
            clashes = True
        if location == "1.name" and "0.name" in used or location == "0.name" and "1.name" in used:
            clashes = True
        if clashes:
            continue
        used.add(location)
        out.append(mutation)
    return out


class HookRuleViolations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._copy = TemplateCopy()
        cls.root = cls._copy.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._copy.__exit__(None, None, None)

    @given(mutation_sets())
    def test_each_violation_is_reported(self, mutations):
        # setUp runs once per test method, not once per example, so clean here.
        for name in ("rules-under-test.json", "Rules_Under-Test.json"):
            (self.root / ".kiro/hooks" / name).unlink(missing_ok=True)
        doc = {"version": "v1", "hooks": base_hooks()}
        path = HOOK_FILE
        for _, _, _, apply, _ in mutations:
            if apply is None:
                path = ".kiro/hooks/Rules_Under-Test.json"
            else:
                apply(doc)
        (self.root / path).write_text(json.dumps(doc, indent=2))
        findings = [f for f in errors(validate(self.root)[0]) if f.path == path]
        reported = {(f.field, f.rule) for f in findings}
        for _, field, rule, _, name in mutations:
            self.assertIn((field, rule), reported, (mutations, findings))
            if name:
                messages = [f.message for f in findings if f.field == field]
                self.assertTrue(any(f'"{name}"' in m for m in messages), messages)
        if not mutations:
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
