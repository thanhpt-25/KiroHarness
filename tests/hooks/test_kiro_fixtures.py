"""Run every enabled Hook_Script against the recorded Kiro payloads.

Payloads live in tests/fixtures/payloads/kiro/<kiro-version>/<Trigger>/<name>.json.
A sibling <name>.expect.json maps a hook name to the outcome
(``{"exit": 2}`` or ``{"exit": 0, "decision": "ask"}``). ``/WORKSPACE`` in a
payload stands for the workspace root. The test discovers every version
directory, so importing payloads recorded from a real Kiro build adds cases
without changing this file.

(agent-harness-platform Requirements 3.2 and 3.3)
"""
# Validates: agent-harness-platform/R3.2, agent-harness-platform/R3.3, agent-harness-platform/R3.5, agent-harness-platform/R3.6, agent-harness-platform/R9.2

import json
import unittest

from tests._support import HOOK_SCRIPTS, ROOT, TemplateCopy, detail, run_script

FIXTURES = ROOT / "tests" / "fixtures" / "payloads" / "kiro"
WORKSPACE_TOKEN = "/WORKSPACE"


def enabled_hooks():
    """``{hook name: (trigger, matcher or None, wrapper path)}`` for enabled hooks that run a script."""
    result = {}
    for path in sorted((ROOT / ".kiro" / "hooks").glob("*.json")):
        for hook in json.loads(path.read_text(encoding="utf-8"))["hooks"]:
            action = hook["action"]
            if hook.get("enabled") is False or action["type"] != "command":
                continue
            script = action["command"].split()[-1]
            result[hook["name"]] = (hook["trigger"], hook.get("matcher"), ROOT / script)
    return result


def payload_cases():
    cases = []
    for version in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        for payload in sorted(version.glob("*/*.json")):
            if payload.name.endswith(".expect.json"):
                continue
            cases.append((version.name, payload))
    return cases


class KiroFixtures(unittest.TestCase):
    def test_every_enabled_trigger_has_a_fixture(self):
        # Validates: agent-harness-platform/R3.2
        triggers = {trigger for trigger, _m, _s in enabled_hooks().values()}
        recorded = {p.parent.name for _v, p in payload_cases()}
        self.assertEqual(sorted(triggers - recorded), [],
                         detail("enabled hook triggers", "a fixture for each", sorted(triggers - recorded)))

    def test_verified_range_is_stated_and_gaps_recorded(self):
        # Validates: agent-harness-platform/R3.5, agent-harness-platform/R3.6
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        kiro = json.loads((root / "harness" / "capabilities.json").read_text(encoding="utf-8"))["agents"]["kiro"]
        lo, hi = kiro["verified"]["min"], kiro["verified"]["max"]
        for rel in ("harness/guidance/tech.md", "README.md"):
            text = (root / rel).read_text(encoding="utf-8")
            self.assertIn(f"minimum {lo}", text, detail(rel, f"minimum {lo}", "missing"))
            self.assertIn(f"maximum {hi}", text, detail(rel, f"maximum {hi}", "missing"))
        self.assertTrue(kiro["gaps"], detail("kiro gaps", "recorded gaps", "empty"))
        status = (root / "docs" / "IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Kiro 1.5.11", status, detail("IMPLEMENTATION_STATUS.md", "Kiro 1.5.11 gaps", "missing"))

    def test_every_payload_has_expectations_for_the_hooks_that_receive_it(self):
        # Validates: agent-harness-platform/R3.3
        for version, payload in payload_cases():
            expect = payload.with_name(payload.stem + ".expect.json")
            self.assertTrue(expect.exists(), detail(f"{version}/{payload.name}", "an .expect.json file", "missing"))

    def test_hooks_produce_the_expected_outcome_for_each_payload(self):
        # Validates: agent-harness-platform/R3.3
        hooks = enabled_hooks()
        ran = 0
        for version, payload in payload_cases():
            trigger = payload.parent.name
            expectations = json.loads(payload.with_name(payload.stem + ".expect.json").read_text(encoding="utf-8"))
            for name, expected in expectations.items():
                self.assertIn(name, hooks, detail(f"{version}/{payload.name}", "an enabled hook", name))
                hook_trigger, _matcher, script = hooks[name]
                self.assertEqual(hook_trigger, trigger, detail(name, f"trigger {hook_trigger}", f"fixture in {trigger}"))
                with TemplateCopy() as root:
                    text = payload.read_text(encoding="utf-8").replace(WORKSPACE_TOKEN, str(root))
                    result = run_script(root / script.relative_to(ROOT), text.encode("utf-8"), cwd=root)
                label = f"{name} <- {version}/{trigger}/{payload.name}"
                self.assertEqual(result.returncode, expected["exit"],
                                 detail(label, f"exit {expected['exit']}", f"exit {result.returncode}; stderr={result.stderr!r}"))
                if "decision" in expected:
                    out = result.stdout.decode("utf-8").strip()
                    decision = json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else None
                    self.assertEqual(decision, expected["decision"], detail(label, expected["decision"], decision))
                ran += 1
        self.assertGreater(ran, 0)


if __name__ == "__main__":
    unittest.main()
