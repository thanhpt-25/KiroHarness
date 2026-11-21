# Feature: agent-harness-platform, Property 34: Generator determinism and idempotence
# Validates: agent-harness-platform/R6.3, agent-harness-platform/R6.4
import unittest

from hypothesis import HealthCheck, given, settings

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_gen import manifests
from tests.generator._fixture import SourceRoot, run_cli, snapshot


class GeneratorDeterminism(unittest.TestCase):
    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(manifests())
    def test_two_runs_match_and_a_run_over_its_output_changes_nothing(self, manifest):
        with SourceRoot(manifest) as first, SourceRoot(manifest) as second:
            self.assertEqual(run_cli(first, "sync")[0], 0)
            self.assertEqual(run_cli(second, "sync")[0], 0)
            self.assertEqual(snapshot(first), snapshot(second))
            before = snapshot(first)
            code, out, _err = run_cli(first, "sync")
            self.assertEqual((code, out), (0, ""))
            self.assertEqual(snapshot(first), before)
            self.assertEqual(run_cli(first, "sync", "--check")[0], 0)


if __name__ == "__main__":
    unittest.main()
