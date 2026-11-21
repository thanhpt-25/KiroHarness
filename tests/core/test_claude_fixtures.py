"""Claude Code payloads through the real ``harness/bin/guard`` wrapper (agent-harness-platform R8.4)."""
# Validates: agent-harness-platform/R8.4
import json
import unittest

from tests._support import ROOT, TemplateCopy, detail, run_script

FIXTURES = ROOT / "tests/fixtures/payloads/claude-code"
TRIGGERS = {"PreToolUse": "pre_tool", "UserPromptSubmit": "prompt_submit"}


def cases():
    for version in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        for payload in sorted(version.glob("*/*.json")):
            if not payload.name.endswith(".expect.json") and payload.parent.name in TRIGGERS:
                yield version.name, payload


class ClaudeFixtures(unittest.TestCase):
    def test_wrapper_gives_the_expected_outcome_for_every_payload(self):
        count = 0
        with TemplateCopy() as root:
            for version, payload in cases():
                expect = json.loads(payload.with_name(payload.stem + ".expect.json").read_text())
                raw = payload.read_text().replace("/WORKSPACE", str(root)).encode()
                trigger = TRIGGERS[payload.parent.name]
                with self.subTest(case=f"{version}/{payload.parent.name}/{payload.stem}"):
                    result = run_script(root / "harness/bin/guard", raw, args=["claude-code", trigger], cwd=root)
                    count += 1
                    self.assertEqual(result.returncode, expect["exit"], detail(payload.name, expect, (result.returncode, result.stderr)))
                    if "stderr" in expect:
                        self.assertIn(expect["stderr"], result.stderr.decode())
                    out = result.stdout.decode().strip()
                    if expect.get("decision"):
                        data = json.loads(out)["hookSpecificOutput"]
                        self.assertEqual(data["permissionDecision"], expect["decision"])
                        self.assertEqual(data["hookEventName"], payload.parent.name)
                    elif expect["exit"] == 0:
                        self.assertEqual(out, "")
        self.assertGreaterEqual(count, 13)


if __name__ == "__main__":
    unittest.main()
