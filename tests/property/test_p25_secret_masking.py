# Feature: kiro-agent-harness-template, Property 25: Secret findings are masked and Secret_References are ignored
# Validates: kiro-agent-harness-template/R10.6
import json
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import TemplateCopy, validate
from tests.property.test_p19_prompt_scan import PATTERNS, secret_values
from harness_validator.secrets import mask

REFS = st.from_regex(r"\A[A-Z][A-Z0-9_]{0,20}\Z").map(lambda n: "${" + n + "}")
secret = st.sampled_from([pid for pid, _ in PATTERNS if pid != "private-key"]).flatmap(secret_values)


class Mask(unittest.TestCase):
    @given(st.text(max_size=40))
    def test_mask_shape(self, value):
        masked = mask(value)
        keep = min(4, len(value) // 2)
        self.assertEqual(len(masked), len(value))
        self.assertEqual(masked[:keep], value[:keep])
        self.assertEqual(set(masked[keep:]) - {"*"}, set())


class SecretFindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._copy = TemplateCopy()
        cls.root = cls._copy.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._copy.__exit__(None, None, None)

    @given(st.lists(secret, min_size=1, max_size=3), st.lists(REFS, min_size=1, max_size=3))
    def test_secrets_reported_masked_and_references_ignored(self, values, refs):
        hook = {
            "version": "v1",
            "hooks": [
                {"name": f"s{i}", "trigger": "Stop", "action": {"type": "agent", "prompt": "note " + v}}
                for i, v in enumerate(values)
            ] + [
                {"name": f"r{i}", "trigger": "Stop", "action": {"type": "agent", "prompt": "use " + r}}
                for i, r in enumerate(refs)
            ],
        }
        (self.root / ".kiro/hooks/secret-test.json").write_text(json.dumps(hook))
        steering = "---\ninclusion: manual\n---\n\n" + "\n".join(["ref " + r for r in refs] + ["value " + v for v in values]) + "\n"
        (self.root / ".kiro/steering/secret-test.md").write_text(steering)
        findings = [f for f in validate(self.root)[0] if f.rule == "SECRET"]

        hook_fields = {f.field for f in findings if f.path.endswith("secret-test.json")}
        self.assertEqual(hook_fields, {f"hooks[{i}].action.prompt" for i in range(len(values))})
        md_fields = {f.field for f in findings if f.path.endswith("secret-test.md")}
        self.assertEqual(md_fields, {f"line {5 + len(refs) + i}" for i in range(len(values))})
        for f in findings:
            for value in values:
                self.assertNotIn(value, f.message)
            self.assertIn("*", f.message)


if __name__ == "__main__":
    unittest.main()
