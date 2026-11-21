# Feature: agent-harness-platform, Property 32: Guard combination order
# Validates: agent-harness-platform/R4.7
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from event_model import Decision, combine

decisions = st.lists(
    st.builds(Decision, st.sampled_from(["allow", "ask", "deny"]), st.sampled_from(["g1", "g2", "g3", "g4"]), st.text(max_size=10)),
    min_size=1, max_size=6,
)


class Combination(unittest.TestCase):
    @given(decisions)
    def test_first_deny_else_first_ask_else_allow(self, items):
        denies = [d for d in items if d.kind == "deny"]
        asks = [d for d in items if d.kind == "ask"]
        expected = denies[0] if denies else asks[0] if asks else items[0]
        result = combine(items)
        self.assertIs(result, expected)
        self.assertEqual(result.guard, expected.guard)


if __name__ == "__main__":
    unittest.main()
