# Feature: agent-harness-platform, Property 37: Hand-edit protection
# Validates: agent-harness-platform/R6.6
import json
import unittest

from hypothesis import HealthCheck, given, settings, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.generator._fixture import SourceRoot, run_cli, snapshot, with_agents

MANIFEST = with_agents(claude_code=True, cursor=True, copilot=True)


class HandEditProtection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._source = SourceRoot(MANIFEST)
        cls.root = cls._source.__enter__()
        assert run_cli(cls.root, "sync")[0] == 0
        cls.lock_paths = sorted(json.loads((cls.root / "harness/generated.lock.json").read_text())["files"])

    @classmethod
    def tearDownClass(cls):
        cls._source.__exit__(None, None, None)

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow], max_examples=60)
    @given(st.data(), st.text(min_size=1, max_size=20).filter(lambda t: "\r" not in t))
    def test_sync_without_force_refuses_and_names_the_edited_file(self, data, extra):
        rel = data.draw(st.sampled_from(self.lock_paths))
        target = self.root / rel
        original = target.read_bytes()
        edited = original + extra.encode("utf-8")
        target.write_bytes(edited)
        try:
            before = snapshot(self.root)
            code, _out, err = run_cli(self.root, "sync")
            self.assertEqual(code, 1)
            self.assertIn(rel, err)
            self.assertEqual(snapshot(self.root), before)
        finally:
            target.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
